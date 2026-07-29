"""Internal API endpoints for machine-to-machine calls (AI engine → CRM).

Secured by x-api-key header. Never expose these routes on a public API gateway.
"""

from __future__ import annotations

import os
from app.core.config import settings as _settings
import re
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from fastapi import Depends

INTERNAL_API_KEY = _settings.INTERNAL_API_KEY or os.getenv("INTERNAL_API_KEY", "")

router = APIRouter(prefix="/api/internal", tags=["internal"])

PURELEVEN_TENANT_SLUG = "pureleven"


def _verify_key(x_api_key: Optional[str]) -> None:
    if not INTERNAL_API_KEY:
        raise HTTPException(status_code=503, detail="Internal API not configured")
    if x_api_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")


def _phone_digits(value: Optional[str]) -> str:
    return re.sub(r"\D", "", value or "")


def _phone_variants(phone: str) -> list[str]:
    digits = _phone_digits(phone)
    variants: set[str] = {digits}
    if digits.startswith("91") and len(digits) == 12:
        variants.add(digits[2:])
    elif len(digits) == 10:
        variants.add("91" + digits)
    return list(variants)


@router.get("/delivery/by-phone")
def get_delivery_by_phone(
    phone: str,
    x_api_key: Optional[str] = Header(None, alias="x-api-key"),
    db: Session = Depends(get_db),
):
    """Return the latest order + tracking info for a customer phone number.

    Used by the AI engine's delivery_lookup_service to auto-reply to customers
    asking about order / delivery status.

    Response shape:
      {found: bool, customer: {name} | null, order: {...} | null}
    """
    from sqlalchemy import text

    _verify_key(x_api_key)

    variants = _phone_variants(phone)
    if not variants:
        return {"found": False, "customer": None, "order": None}

    # Resolve tenant
    tenant_row = db.execute(
        text("SELECT id FROM tenants WHERE slug = :slug LIMIT 1"),
        {"slug": PURELEVEN_TENANT_SLUG},
    ).fetchone()
    if not tenant_row:
        raise HTTPException(status_code=500, detail="Tenant not found")
    tenant_id = str(tenant_row[0])

    # Find customer by phone (any variant)
    placeholders = ", ".join(f":p{i}" for i in range(len(variants)))
    params: dict = {"tenant_id": tenant_id}
    for i, v in enumerate(variants):
        params[f"p{i}"] = v

    customer_row = db.execute(
        text(f"""
            SELECT id, name FROM customers
            WHERE tenant_id = :tenant_id
              AND phone IN ({placeholders})
            ORDER BY created_at DESC
            LIMIT 1
        """),
        params,
    ).fetchone()

    if not customer_row:
        return {"found": False, "customer": None, "order": None}

    customer_id = str(customer_row[0])
    customer_name = customer_row[1] or ""

    # Fetch most recent order for this customer
    order_row = db.execute(
        text("""
            SELECT
                o.id,
                o.order_number,
                o.status,
                o.tracking_number,
                o.courier_name,
                o.tracking_status_text,
                o.tracking_last_location,
                o.tracking_last_event_at,
                o.tracking_events_json,
                o.created_at
            FROM orders o
            WHERE o.customer_id = :customer_id
              AND o.tenant_id = :tenant_id
            ORDER BY o.created_at DESC
            LIMIT 1
        """),
        {"customer_id": customer_id, "tenant_id": tenant_id},
    ).fetchone()

    if not order_row:
        return {"found": True, "customer": {"name": customer_name}, "order": None}

    (
        order_id,
        order_number,
        order_status,
        tracking_number,
        courier_name,
        tracking_status_text,
        tracking_last_location,
        tracking_last_event_at,
        tracking_events_json,
        created_at,
    ) = order_row

    # Summarise line items
    item_rows = db.execute(
        text("""
            SELECT product_name, quantity, unit
            FROM order_items
            WHERE order_id = :order_id
            ORDER BY id
            LIMIT 5
        """),
        {"order_id": str(order_id)},
    ).fetchall()

    items_summary = ", ".join(
        f"{r[0]} x{int(r[1]) if r[1] == int(r[1]) else r[1]}"
        for r in item_rows
    ) if item_rows else ""

    # Last 3 tracking events
    events = []
    raw_events = tracking_events_json or []
    if isinstance(raw_events, str):
        import json as _json
        try:
            raw_events = _json.loads(raw_events)
        except Exception:
            raw_events = []
    for ev in raw_events[-3:]:
        events.append({
            "status": ev.get("status") or ev.get("description", ""),
            "location": ev.get("location", ""),
            "time": str(ev.get("time") or ev.get("timestamp", "")),
        })

    return {
        "found": True,
        "customer": {"name": customer_name},
        "order": {
            "order_ref": order_number or str(order_id)[:8],
            "status": str(order_status) if order_status else "unknown",
            "tracking_number": tracking_number or "",
            "courier_name": courier_name or "",
            "tracking_status": tracking_status_text or "",
            "tracking_location": tracking_last_location or "",
            "tracking_at": (
                tracking_last_event_at.isoformat()
                if tracking_last_event_at else ""
            ),
            "tracking_events": events,
            "items_summary": items_summary,
            "created_at": created_at.isoformat() if created_at else "",
        },
    }
