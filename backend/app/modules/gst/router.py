"""
GST & Accounting Reports Router
---------------------------------
Prefix: /api/gst
All tenant roles can view.  Admin/operations can save profile.

Endpoints:
  GET  /api/gst/profile            → tenant GST profile
  POST /api/gst/profile            → save/update GST profile
  GET  /api/gst/gstr1              → GSTR-1 detailed rows
  GET  /api/gst/hsn-summary        → HSN-wise summary
  GET  /api/gst/tax-summary        → GSTR-3B tax summary
  GET  /api/gst/export/gstr1       → CSV download
  GET  /api/gst/export/hsn         → CSV download
  GET  /api/gst/export/tax         → CSV download
  GET  /api/gst/export/accounting  → CSV download (Tally/Zoho)
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.auth.tenant import get_current_tenant_user, require_roles
from app.models.employee import RoleEnum
from app.modules.gst import service

router = APIRouter(prefix="/api/gst", tags=["GST"])

_all_roles = require_roles(
    RoleEnum.admin, RoleEnum.operations, RoleEnum.sales,
    RoleEnum.support, RoleEnum.marketing,
)
_mgmt = require_roles(RoleEnum.admin, RoleEnum.operations)


# ── Shared filter params ───────────────────────────────────────

def _filters(
    date_from: date = Query(..., description="Start date YYYY-MM-DD"),
    date_to:   date = Query(..., description="End date YYYY-MM-DD"),
    state:     Optional[str]   = Query(None),
    b2b:       Optional[str]   = Query(None, description="'b2b' | 'b2c' | None"),
    min_amount: Optional[float] = Query(None),
    max_amount: Optional[float] = Query(None),
):
    return {
        "date_from": date_from, "date_to": date_to,
        "state_filter": state, "b2b_filter": b2b,
        "min_amount": min_amount, "max_amount": max_amount,
    }


# ─────────────────────────────────────────────────────────────
# GSTIN Validation
# ─────────────────────────────────────────────────────────────

@router.get("/validate-gstin/{gstin}")
def validate_gstin(
    gstin: str,
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    """Validate GSTIN format and extract state information."""
    from app.modules.gst.gstin_validator import validate_gstin as v_gstin
    is_valid, error_msg, details = v_gstin(gstin)
    if not is_valid:
        return {"valid": False, "error": error_msg}
    return {"valid": True, "details": details}


# ─────────────────────────────────────────────────────────────
# Profile
# ─────────────────────────────────────────────────────────────

@router.get("/profile")
def get_profile(
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    return service.get_gst_profile(db, current_user)


@router.post("/profile")
def save_profile(
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(_mgmt),
):
    return service.save_gst_profile(db, current_user, data)


# ─────────────────────────────────────────────────────────────
# GSTR-1 Detailed
# ─────────────────────────────────────────────────────────────

@router.get("/gstr1")
def gstr1(
    filters: dict = Depends(_filters),
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    return service.get_gstr1(db, current_user, **filters)


# ─────────────────────────────────────────────────────────────
# HSN Summary
# ─────────────────────────────────────────────────────────────

@router.get("/hsn-summary")
def hsn_summary(
    filters: dict = Depends(_filters),
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    return service.get_hsn_summary(db, current_user, **filters)


# ─────────────────────────────────────────────────────────────
# Tax Summary (GSTR-3B)
# ─────────────────────────────────────────────────────────────

@router.get("/tax-summary")
def tax_summary(
    filters: dict = Depends(_filters),
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    return service.get_tax_summary(db, current_user, **filters)


# ─────────────────────────────────────────────────────────────
# CSV Exports
# ─────────────────────────────────────────────────────────────

def _csv_response(content: str, filename: str) -> StreamingResponse:
    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/gstr1")
def export_gstr1(
    filters: dict = Depends(_filters),
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    data = service.get_gstr1(db, current_user, **filters)
    csv_content = service.export_gstr1_csv(data)
    fname = f"GSTR1_{filters['date_from']}_{filters['date_to']}.csv"
    return _csv_response(csv_content, fname)


@router.get("/export/hsn")
def export_hsn(
    filters: dict = Depends(_filters),
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    data = service.get_hsn_summary(db, current_user, **filters)
    csv_content = service.export_hsn_csv(data)
    fname = f"HSN_Summary_{filters['date_from']}_{filters['date_to']}.csv"
    return _csv_response(csv_content, fname)


@router.get("/export/tax")
def export_tax(
    filters: dict = Depends(_filters),
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    data = service.get_tax_summary(db, current_user, **filters)
    csv_content = service.export_tax_summary_csv(data)
    fname = f"Tax_Summary_{filters['date_from']}_{filters['date_to']}.csv"
    return _csv_response(csv_content, fname)


@router.get("/export/accounting")
def export_accounting(
    filters: dict = Depends(_filters),
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    data = service.get_gstr1(db, current_user, **filters)
    csv_content = service.export_accounting_csv(data)
    fname = f"Accounting_{filters['date_from']}_{filters['date_to']}.csv"
    return _csv_response(csv_content, fname)
