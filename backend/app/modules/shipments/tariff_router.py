"""
tariff_router.py
────────────────
Safe 2-step shipment tariff upload workflow:

  POST /api/tariff-upload/stage
      Parse XLSX → run matcher → write to tariff_upload_staging → return batch summary.
      NEVER touches the orders table.

  GET  /api/tariff-upload/batch/{batch_id}
      Return all staging rows for a batch, grouped by confidence.

  POST /api/tariff-upload/batch/{batch_id}/approve
      Mark rows approved (body: {"row_ids": [...]} or {"all_high": true}).

  POST /api/tariff-upload/batch/{batch_id}/reject
      Mark rows rejected with a reason.

  POST /api/tariff-upload/batch/{batch_id}/apply
      Write ONLY approved rows to orders.shipping_charge / tracking_number.
      Stale-order guard: if an order was modified after upload, row is skipped with error.
"""
from __future__ import annotations

import io
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import openpyxl
import re as _re
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.auth.tenant import get_current_tenant_user
from app.database.session import get_db
from app.models.employee import Employee
from app.models.order import Order
from app.models.tariff_upload_staging import TariffUploadStaging
from app.modules.shipments.tariff_matcher import (
    XlsxRow,
    OrderSnapshot,
    match_rows,
)
from app.modules.shipments.router import (
    _detect_tracking_col_by_content,
    _detect_shipping_col_by_content,
    _parse_money_value,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tariff-upload", tags=["Tariff Upload"])


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _find_col(headers: list[str], candidates: list[str]) -> Optional[int]:
    """Return the first header index that matches any candidate (case-insensitive)."""
    for i, h in enumerate(headers):
        if h in candidates:
            return i
    return None


def _parse_xlsx(file_content: bytes) -> list[XlsxRow]:
    """
    Parse an India Post XLSX dispatch report into a list of XlsxRow.
    Auto-detects columns using headers first, then content scanning.
    """
    wb = openpyxl.load_workbook(io.BytesIO(file_content), read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if len(rows) < 2:
        raise HTTPException(status_code=400, detail="XLSX has no data rows (need at least 1 header + 1 data row)")

    headers = [str(h or "").strip().lower() for h in rows[0]]
    num_cols = len(headers)

    # ── Column detection ──────────────────────────────────────────────────
    track_col = _find_col(headers, [
        "article-number", "article-no", "article number", "article no", "article no.",
        "article_number", "tracking number", "tracking no", "tracking no.", "tracking_number",
        "awb", "awb number", "awb no", "barcode", "consignment no", "consignment no.",
        "consignment number", "tracking id", "shipment no", "shipment number",
        "booking no", "booking no.", "booking number", "speed post no", "reg no",
        "registered no", "parcel no", "parcel number", "article",
    ])
    if track_col is None:
        track_col = _detect_tracking_col_by_content(rows, num_cols)

    cust_col = _find_col(headers, [
        "receiver-name", "sender-name", "receiver name", "sender name",
        "customer name", "customer", "name", "customer_name",
        "recipient", "addressee", "consignee", "addressee name",
        "to name", "beneficiary", "party name",
    ])

    order_ref_col = _find_col(headers, [
        "order number", "order no", "order no.", "order_number", "ordernumber",
        "order name", "order id", "order ref", "reference", "po number",
    ])

    amount_col = _find_col(headers, [
        "shipping", "shipping charge", "shipping charges", "shipping amount",
        "postage", "postage charges", "postage amount",
        "charge", "charges", "amount", "tariff", "freight", "rate",
        "article charge", "article charges", "total charges",
    ])
    if amount_col is None:
        exclude = {c for c in [track_col, cust_col, order_ref_col] if c is not None}
        amount_col = _detect_shipping_col_by_content(rows, num_cols, exclude_cols=exclude)

    pincode_col = _find_col(headers, [
        "pincode", "pin code", "pin", "zip", "zip code", "postal code",
        "to pin", "to pincode", "to-pin", "to-pincode",
        "destination pin", "destination pincode",
        "delivery pin", "delivery pincode",
        "receiver pin", "receiver pincode", "to zip", "receiver zip",
    ])

    weight_col = _find_col(headers, [
        "weight", "weight (grams)", "weight(grams)", "weight_grams", "wt",
        "weight g", "article weight", "wt (g)", "wt(g)",
    ])

    status_col = _find_col(headers, [
        "event-description", "event-code", "event description", "event code",
        "delivery status", "status", "delivered", "shipment status",
        "current status", "delivery", "event", "current event",
        "latest status", "remarks", "delivery remarks",
        "status description", "scan event", "scan status",
    ])

    logger.info(
        "[tariff-stage] cols: track=%s cust=%s order_ref=%s amount=%s weight=%s status=%s",
        track_col, cust_col, order_ref_col, amount_col, weight_col, status_col,
    )

    xlsx_rows: list[XlsxRow] = []
    for row_num, row in enumerate(rows[1:], start=2):  # 1-indexed, skip header
        def _cell(col: Optional[int]):
            if col is None or col >= len(row):
                return None
            return row[col]

        tracking   = str(_cell(track_col) or "").strip() or None
        cust_name  = str(_cell(cust_col) or "").strip() or None
        order_ref  = str(_cell(order_ref_col) or "").strip() or None
        amount     = _parse_money_value(_cell(amount_col))
        weight_raw = _cell(weight_col)
        weight     = float(weight_raw) if weight_raw not in (None, "") else None
        status_txt = str(_cell(status_col) or "").strip() or None
        pincode    = _re.sub(r"[^0-9]", "", str(_cell(pincode_col) or "").strip()) or None

        # Skip completely empty rows
        if not tracking and not cust_name and not order_ref and amount is None:
            continue

        xlsx_rows.append(XlsxRow(
            row_num=row_num,
            tracking=tracking,
            order_ref=order_ref,
            customer_name=cust_name,
            amount=amount,
            weight=weight,
            status_text=status_txt,
            pincode=pincode,
        ))

    return xlsx_rows


def _load_order_snapshots(db: Session, tenant_id: uuid.UUID) -> list[OrderSnapshot]:
    """Load all non-cancelled/delivered orders for the tenant as lightweight snapshots."""
    orders = (
        db.query(
            Order.id,
            Order.order_number,
            Order.tracking_number,
            Order.delivery_name,
            Order.delivery_pincode,
            Order.shipping_charge,
        )
        .filter(Order.tenant_id == tenant_id)
        .all()
    )
    return [
        OrderSnapshot(
            order_id=r.id,
            order_number=r.order_number,
            tracking_number=r.tracking_number,
            delivery_name=r.delivery_name,
            delivery_pincode=r.delivery_pincode,
            shipping_charge=float(r.shipping_charge or 0),
        )
        for r in orders
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/stage")
async def stage_tariff_upload(
    file: List[UploadFile] = File(...),
    upload_mode: str = Form("tariff"),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """
    Step 1 of 2.  Parse one or more XLSX files → validate/match → store in staging.
    All files are merged into a single batch_id for unified review.
    DOES NOT touch the orders table.

    Parameters:
      upload_mode: "tariff" (full matching) | "tracking" (validate) | "delivery" (validate)
    """
    upload_mode = (upload_mode or "tariff").strip().lower()
    if upload_mode not in ("tariff", "tracking", "delivery"):
        upload_mode = "tariff"

    # Parse all uploaded files and merge rows into one batch
    xlsx_rows: list = []
    file_results: list[dict] = []
    for f in file:
        content = await f.read()
        if not content:
            file_results.append({"file": f.filename, "status": "empty", "rows": 0})
            continue
        try:
            parsed = _parse_xlsx(content)
            xlsx_rows.extend(parsed)
            file_results.append({"file": f.filename, "status": "ok", "rows": len(parsed)})
        except HTTPException as exc:
            file_results.append({"file": f.filename, "status": "error", "detail": exc.detail, "rows": 0})
        except Exception as exc:
            logger.error("[tariff-stage] parse error %s: %s", f.filename, exc)
            file_results.append({"file": f.filename, "status": "error", "detail": str(exc), "rows": 0})

    if not xlsx_rows:
        failed = [r for r in file_results if r["status"] != "ok"]
        detail = "No usable data rows found in uploaded file(s)."
        if failed:
            detail += " " + "; ".join(f"{r['file']}: {r.get('detail', r['status'])}" for r in failed)
        raise HTTPException(status_code=400, detail=detail)

    tenant_id  = current_user.tenant_id
    batch_id   = uuid.uuid4()
    emp_id     = current_user.id

    # Match rows against orders (mode-aware)
    snapshots   = _load_order_snapshots(db, tenant_id)
    staging_rows = match_rows(xlsx_rows, snapshots, mode=upload_mode)

    # === VALIDATION: Reject rows with missing current tariff (for tariff mode) ===
    rows_skipped_missing_tariff = []
    rows_warnings_high_impact = []
    valid_staging_rows = []
    
    for sr in staging_rows:
        # For tariff upload mode: reject rows where order has no current shipping tariff
        if upload_mode == "tariff" and sr.current_shipping is None and sr.order_id is not None:
            rows_skipped_missing_tariff.append({
                "xlsx_row_num": sr.xlsx_row_num,
                "tracking": sr.xlsx_tracking,
                "customer": sr.xlsx_customer_name,
                "order_id": sr.order_id,
                "reason": "Order has no current tariff in system — cannot validate tariff change. Skipped."
            })
            continue
        
        # For tariff mode: flag rows with significant tariff changes (>50% reduction or >200% increase)
        if upload_mode == "tariff" and sr.order_id is not None and sr.current_shipping is not None and sr.proposed_shipping is not None:
            current = float(sr.current_shipping)
            proposed = float(sr.proposed_shipping)
            
            if current > 0:
                change_pct = ((proposed - current) / current) * 100
                if change_pct < -50:  # More than 50% reduction
                    rows_warnings_high_impact.append({
                        "xlsx_row_num": sr.xlsx_row_num,
                        "tracking": sr.xlsx_tracking,
                        "order_id": sr.order_id,
                        "current_tariff": current,
                        "proposed_tariff": proposed,
                        "change_pct": round(change_pct, 1),
                        "severity": "REDUCTION",
                        "reason": f"Significant tariff reduction: ₹{current:.2f} → ₹{proposed:.2f} ({change_pct:.1f}%)"
                    })
                elif change_pct > 200:  # More than 200% increase
                    rows_warnings_high_impact.append({
                        "xlsx_row_num": sr.xlsx_row_num,
                        "tracking": sr.xlsx_tracking,
                        "order_id": sr.order_id,
                        "current_tariff": current,
                        "proposed_tariff": proposed,
                        "change_pct": round(change_pct, 1),
                        "severity": "INCREASE",
                        "reason": f"Significant tariff increase: ₹{current:.2f} → ₹{proposed:.2f} ({change_pct:.1f}%)"
                    })
        
        valid_staging_rows.append(sr)
    
    # Log rejection summary
    if rows_skipped_missing_tariff:
        logger.warning(
            "[tariff-stage] Rejected %d rows with missing current tariff",
            len(rows_skipped_missing_tariff)
        )
    
    if rows_warnings_high_impact:
        logger.warning(
            "[tariff-stage] Found %d rows with significant tariff changes (flagged for review)",
            len(rows_warnings_high_impact)
        )

    # Bulk-insert staging rows
    db_rows = []
    for sr in valid_staging_rows:
        db_row = TariffUploadStaging(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            upload_batch_id=batch_id,
            uploaded_by=emp_id,
            xlsx_row_num=sr.xlsx_row_num,
            xlsx_tracking=sr.xlsx_tracking,
            xlsx_order_ref=sr.xlsx_order_ref,
            xlsx_customer_name=sr.xlsx_customer_name,
            xlsx_amount=sr.xlsx_amount,
            xlsx_weight=sr.xlsx_weight,
            xlsx_status_text=sr.xlsx_status_text,
            order_id=sr.order_id,
            order_number=sr.order_number,
            match_method=sr.match_method,
            confidence=sr.confidence,
            tracking_valid=sr.tracking_valid,
            amount_valid=sr.amount_valid,
            amount_suspicious=sr.amount_suspicious,
            current_tracking=sr.current_tracking,
            proposed_tracking=sr.proposed_tracking,
            current_shipping=sr.current_shipping,
            proposed_shipping=sr.proposed_shipping,
            review_status="pending",
        )
        db.add(db_row)
        db_rows.append(db_row)

    db.commit()

    # Build summary
    high     = sum(1 for r in valid_staging_rows if r.confidence == "high")
    medium   = sum(1 for r in valid_staging_rows if r.confidence == "medium")
    low      = sum(1 for r in valid_staging_rows if r.confidence == "low")
    unmatched = sum(1 for r in valid_staging_rows if r.confidence == "none")
    suspicious = sum(1 for r in valid_staging_rows if r.amount_suspicious)

    return {
        "batch_id": str(batch_id),
        "upload_mode": upload_mode,
        "file_results": file_results,
        "total_rows_accepted": len(valid_staging_rows),
        "total_rows_rejected": len(rows_skipped_missing_tariff),
        "total_rows_warnings": len(rows_warnings_high_impact),
        "rejected_rows": rows_skipped_missing_tariff,
        "warning_rows": rows_warnings_high_impact,
        "summary": {
            "high":       high,
            "medium":     medium,
            "low":        low,
            "unmatched":  unmatched,
            "suspicious": suspicious,
        },
        "message": (
            f"Accepted {len(valid_staging_rows)} rows: {high} high confidence, "
            f"{medium} medium, {low} low, {unmatched} unmatched. "
            f"Rejected {len(rows_skipped_missing_tariff)} rows with missing current tariff. "
            f"Flagged {len(rows_warnings_high_impact)} rows with significant tariff changes. "
            f"Review before applying."
        ),
    }


@router.get("/batch/{batch_id}")
def get_batch(
    batch_id: str,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Return all staging rows for a batch grouped by confidence level."""
    try:
        batch_uuid = uuid.UUID(batch_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid batch_id")

    rows = (
        db.query(TariffUploadStaging)
        .filter(
            TariffUploadStaging.tenant_id == current_user.tenant_id,
            TariffUploadStaging.upload_batch_id == batch_uuid,
        )
        .order_by(TariffUploadStaging.xlsx_row_num)
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Batch not found")

    grouped: dict[str, list] = {"high": [], "medium": [], "low": [], "none": []}
    for r in rows:
        grouped.setdefault(r.confidence, []).append(r.to_dict())

    return {
        "batch_id": batch_id,
        "total": len(rows),
        "pending":  sum(1 for r in rows if r.review_status == "pending"),
        "approved": sum(1 for r in rows if r.review_status == "approved"),
        "rejected": sum(1 for r in rows if r.review_status == "rejected"),
        "applied":  sum(1 for r in rows if r.review_status == "applied"),
        "rows_by_confidence": grouped,
    }


@router.post("/batch/{batch_id}/approve")
def approve_rows(
    batch_id: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """
    Approve rows for application.

    Body options (mutually exclusive, first wins):
      { "all_high": true }              — approve all high-confidence pending rows
      { "row_ids": ["uuid1", ...] }     — approve specific rows by id
    """
    try:
        batch_uuid = uuid.UUID(batch_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid batch_id")

    now = datetime.now(timezone.utc)
    tenant_id = current_user.tenant_id

    base_q = db.query(TariffUploadStaging).filter(
        TariffUploadStaging.tenant_id == tenant_id,
        TariffUploadStaging.upload_batch_id == batch_uuid,
        TariffUploadStaging.review_status == "pending",
    )

    all_high = body.get("all_high", False)
    row_ids  = body.get("row_ids", [])

    if all_high:
        rows = base_q.filter(TariffUploadStaging.confidence == "high").all()
    elif row_ids:
        try:
            id_list = [uuid.UUID(r) for r in row_ids]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid row_id in list")
        rows = base_q.filter(TariffUploadStaging.id.in_(id_list)).all()
    else:
        raise HTTPException(status_code=400, detail="Provide 'all_high': true or 'row_ids': [...]")

    if not rows:
        raise HTTPException(status_code=404, detail="No matching pending rows found in this batch")

    for r in rows:
        r.review_status = "approved"
        r.reviewed_by   = current_user.id
        r.reviewed_at   = now
        r.updated_at    = now

    db.commit()
    return {"approved": len(rows)}


@router.post("/batch/{batch_id}/reject")
def reject_rows(
    batch_id: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """
    Reject rows.

    Body: { "row_ids": ["uuid1", ...], "reason": "optional text" }
    """
    try:
        batch_uuid = uuid.UUID(batch_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid batch_id")

    row_ids = body.get("row_ids", [])
    reason  = body.get("reason", "") or ""
    if not row_ids:
        raise HTTPException(status_code=400, detail="Provide 'row_ids': [...]")

    try:
        id_list = [uuid.UUID(r) for r in row_ids]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid row_id in list")

    now = datetime.now(timezone.utc)
    rows = (
        db.query(TariffUploadStaging)
        .filter(
            TariffUploadStaging.tenant_id == current_user.tenant_id,
            TariffUploadStaging.upload_batch_id == batch_uuid,
            TariffUploadStaging.id.in_(id_list),
        )
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="No matching rows found")

    for r in rows:
        r.review_status    = "rejected"
        r.reviewed_by      = current_user.id
        r.reviewed_at      = now
        r.rejection_reason = reason or None
        r.updated_at       = now

    db.commit()
    return {"rejected": len(rows)}


@router.post("/batch/{batch_id}/apply")
def apply_batch(
    batch_id: str,
    skip_review: bool = False,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """
    Step 2 of 2.  Write approved rows to orders.

    For each approved row:
      1. Stale-order guard: fetch the order; if its updated_at is newer than the
         staging row's created_at, skip and record apply_error.
      2. Write orders.shipping_charge = proposed_shipping
         Write orders.tracking_number = proposed_tracking  (if set)
      3. Mark row as applied.

    Parameters:
      skip_review: if True, auto-approve all pending rows before applying
                   (intended for tracking/delivery quick-apply mode)

    Returns counts of applied / skipped rows.
    """
    # Auto-approve all pending rows if skip_review is True
    if skip_review:
        now = datetime.now(timezone.utc)
        try:
            batch_uuid = uuid.UUID(batch_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid batch_id")

        pending_rows = (
            db.query(TariffUploadStaging)
            .filter(
                TariffUploadStaging.tenant_id == current_user.tenant_id,
                TariffUploadStaging.upload_batch_id == batch_uuid,
                TariffUploadStaging.review_status == "pending",
            )
            .all()
        )
        for r in pending_rows:
            r.review_status = "approved"
            r.reviewed_by   = current_user.id
            r.reviewed_at   = now
            r.updated_at    = now
        db.commit()
        logger.info("[apply] auto-approved %d pending rows (skip_review=True)", len(pending_rows))
    try:
        batch_uuid = uuid.UUID(batch_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid batch_id")

    tenant_id = current_user.tenant_id
    approved_rows = (
        db.query(TariffUploadStaging)
        .filter(
            TariffUploadStaging.tenant_id == tenant_id,
            TariffUploadStaging.upload_batch_id == batch_uuid,
            TariffUploadStaging.review_status == "approved",
        )
        .all()
    )

    if not approved_rows:
        raise HTTPException(
            status_code=400,
            detail="No approved rows in this batch. Approve rows first.",
        )

    now = datetime.now(timezone.utc)
    applied = 0
    skipped = 0
    errors  = []

    for staging_row in approved_rows:
        if not staging_row.order_id:
            staging_row.review_status = "apply_error"
            staging_row.apply_error   = "No order_id — cannot apply"
            staging_row.updated_at    = now
            skipped += 1
            continue

        order = db.query(Order).filter(
            Order.id        == staging_row.order_id,
            Order.tenant_id == tenant_id,
        ).with_for_update().first()

        if not order:
            staging_row.review_status = "apply_error"
            staging_row.apply_error   = "Order not found"
            staging_row.updated_at    = now
            skipped += 1
            errors.append({"row": staging_row.xlsx_row_num, "error": "Order not found"})
            continue

        # Stale-order guard
        order_updated = order.updated_at
        staging_created = staging_row.created_at
        if order_updated and staging_created:
            # Make both offset-aware for comparison
            if order_updated.tzinfo is None:
                order_updated = order_updated.replace(tzinfo=timezone.utc)
            if staging_created.tzinfo is None:
                staging_created = staging_created.replace(tzinfo=timezone.utc)
            if order_updated > staging_created:
                msg = (
                    f"Order was modified after this upload "
                    f"(order updated: {order_updated.isoformat()}, "
                    f"upload: {staging_created.isoformat()}). Skipped."
                )
                staging_row.review_status = "apply_error"
                staging_row.apply_error   = msg
                staging_row.updated_at    = now
                skipped += 1
                errors.append({"row": staging_row.xlsx_row_num, "error": msg})
                continue

        # Write to order
        if staging_row.proposed_shipping is not None:
            order.shipping_charge = staging_row.proposed_shipping
        if staging_row.proposed_tracking:
            order.tracking_number = staging_row.proposed_tracking
        order.updated_at = now

        staging_row.review_status = "applied"
        staging_row.applied_at    = now
        staging_row.updated_at    = now
        applied += 1

    db.commit()

    return {
        "applied":  applied,
        "skipped":  skipped,
        "errors":   errors,
        "message":  f"Applied {applied} rows. {skipped} skipped (see 'errors' for details).",
    }


@router.get("/batches")
def list_batches(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """
    Return a summary of every upload batch from the last `days` days (default 30).
    Each batch entry shows row counts by confidence and review status so the user
    can audit past uploads without re-opening each one.
    """
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, min(days, 365)))

    # Load only the columns we need for aggregation
    rows = (
        db.query(
            TariffUploadStaging.upload_batch_id,
            TariffUploadStaging.uploaded_by,
            TariffUploadStaging.created_at,
            TariffUploadStaging.confidence,
            TariffUploadStaging.review_status,
            TariffUploadStaging.xlsx_row_num,
        )
        .filter(
            TariffUploadStaging.tenant_id == current_user.tenant_id,
            TariffUploadStaging.created_at >= cutoff,
        )
        .all()
    )

    batches: dict[str, dict] = {}
    for r in rows:
        bid = str(r.upload_batch_id)
        if bid not in batches:
            batches[bid] = {
                "batch_id":    bid,
                "uploaded_at": r.created_at,
                "uploaded_by": str(r.uploaded_by) if r.uploaded_by else None,
                "total":       0,
                "high":        0,
                "medium":      0,
                "low":         0,
                "unmatched":   0,
                "pending":     0,
                "approved":    0,
                "rejected":    0,
                "applied":     0,
                "apply_error": 0,
            }
        b = batches[bid]
        b["total"] += 1

        conf = r.confidence if r.confidence in ("high", "medium", "low") else "unmatched"
        b[conf] += 1

        status = r.review_status if r.review_status in ("pending", "approved", "rejected", "applied", "apply_error") else "pending"
        b[status] += 1

        # Keep the earliest created_at as the canonical upload time
        if r.created_at and r.created_at < b["uploaded_at"]:
            b["uploaded_at"] = r.created_at

    result = sorted(
        batches.values(),
        key=lambda x: x["uploaded_at"] or datetime.min,
        reverse=True,
    )
    for b in result:
        if b["uploaded_at"]:
            b["uploaded_at"] = b["uploaded_at"].isoformat()

    return {"batches": result, "days": days}
