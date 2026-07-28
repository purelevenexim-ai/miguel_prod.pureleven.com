"""
Tenant Settings API
-------------------
GET  /api/tenant/settings  → returns current tenant's branding + billing config
PATCH /api/tenant/settings → update tenant settings (admin only)
GET  /api/tenant/label-template  → returns label template JSON
PATCH /api/tenant/label-template → update label template (admin only)
GET  /api/tenant/invoice-template → returns invoice template JSON
PATCH /api/tenant/invoice-template → update invoice template (admin only)
POST /api/tenant/upload-image → upload logo/header/footer image (admin only)
"""
from __future__ import annotations
import os, uuid, base64
from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.auth.tenant import get_current_tenant_user, require_roles
from app.database.session import get_db
from app.models.employee import RoleEnum
from app.models.tenant import Tenant

router = APIRouter(prefix="/api/tenant", tags=["Tenant Settings"])

# ── Image upload constants ────────────────────────────────
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_IMAGE_SIZE = 512 * 1024  # 512 KB


class TenantSettingsResponse(BaseModel):
    id: str
    company_name: str
    slug: str
    logo_url: Optional[str] = None
    slogan: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    gstin: Optional[str] = None
    gst_state: Optional[str] = None
    gst_address: Optional[str] = None
    gst_city: Optional[str] = None
    gst_pincode: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account: Optional[str] = None
    bank_ifsc: Optional[str] = None
    bank_branch: Optional[str] = None
    upi_id: Optional[str] = None
    invoice_prefix: Optional[str] = "INV"
    proforma_prefix: Optional[str] = "PRF"
    bill_prefix: Optional[str] = "BILL"
    label_show_logo: Optional[bool] = True
    label_show_slogan: Optional[bool] = True
    label_show_barcode: Optional[bool] = False
    label_footer_note: Optional[str] = None
    label_template: Optional[Any] = None
    invoice_template: Optional[Any] = None


class TenantSettingsUpdate(BaseModel):
    company_name: Optional[str] = None
    logo_url: Optional[str] = None
    slogan: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    gstin: Optional[str] = None
    gst_state: Optional[str] = None
    gst_address: Optional[str] = None
    gst_city: Optional[str] = None
    gst_pincode: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account: Optional[str] = None
    bank_ifsc: Optional[str] = None
    bank_branch: Optional[str] = None
    upi_id: Optional[str] = None
    invoice_prefix: Optional[str] = None
    proforma_prefix: Optional[str] = None
    bill_prefix: Optional[str] = None
    label_show_logo: Optional[bool] = None
    label_show_slogan: Optional[bool] = None
    label_show_barcode: Optional[bool] = None
    label_footer_note: Optional[str] = None


def _tenant_to_dict(t: Tenant) -> dict:
    return {
        "id": str(t.id),
        "company_name": t.company_name,
        "slug": t.slug,
        "logo_url": getattr(t, "logo_url", None),
        "slogan": getattr(t, "slogan", None),
        "phone": getattr(t, "phone", None) or getattr(t, "contact_phone", None),
        "email": getattr(t, "email", None) or getattr(t, "owner_email", None),
        "address_line1": getattr(t, "address_line1", None),
        "address_line2": getattr(t, "address_line2", None),
        "gstin": getattr(t, "gstin", None),
        "gst_state": getattr(t, "gst_state", None),
        "gst_address": getattr(t, "gst_address", None),
        "gst_city": getattr(t, "gst_city", None),
        "gst_pincode": getattr(t, "gst_pincode", None),
        "bank_name": getattr(t, "bank_name", None),
        "bank_account": getattr(t, "bank_account", None),
        "bank_ifsc": getattr(t, "bank_ifsc", None),
        "bank_branch": getattr(t, "bank_branch", None),
        "upi_id": getattr(t, "upi_id", None),
        "invoice_prefix": getattr(t, "invoice_prefix", None) or "INV",
        "proforma_prefix": getattr(t, "proforma_prefix", None) or "PRF",
        "bill_prefix": getattr(t, "bill_prefix", None) or "BILL",
        "label_show_logo": getattr(t, "label_show_logo", True),
        "label_show_slogan": getattr(t, "label_show_slogan", True),
        "label_show_barcode": getattr(t, "label_show_barcode", False),
        "label_footer_note": getattr(t, "label_footer_note", None),
        "label_template": getattr(t, "label_template", None),
        "invoice_template": getattr(t, "invoice_template", None),
    }


@router.get("/settings", response_model=dict)
def get_tenant_settings(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_tenant_user),
):
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return _tenant_to_dict(tenant)


@router.patch("/settings", response_model=dict)
def update_tenant_settings(
    data: TenantSettingsUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(RoleEnum.admin)),
):
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(tenant, field):
            setattr(tenant, field, value)

    db.commit()
    db.refresh(tenant)
    return _tenant_to_dict(tenant)


# ── Label Template ─────────────────────────────────────────
class TemplatePayload(BaseModel):
    template: Any = None


@router.get("/label-template", response_model=dict)
def get_label_template(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_tenant_user),
):
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {"template": getattr(tenant, "label_template", None)}


@router.patch("/label-template", response_model=dict)
def update_label_template(
    data: TemplatePayload,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(RoleEnum.admin)),
):
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant.label_template = data.template
    db.commit()
    db.refresh(tenant)
    return {"template": tenant.label_template}


# ── Invoice Template ───────────────────────────────────────
@router.get("/invoice-template", response_model=dict)
def get_invoice_template(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_tenant_user),
):
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {"template": getattr(tenant, "invoice_template", None)}


@router.patch("/invoice-template", response_model=dict)
def update_invoice_template(
    data: TemplatePayload,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(RoleEnum.admin)),
):
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant.invoice_template = data.template
    db.commit()
    db.refresh(tenant)
    return {"template": tenant.invoice_template}


# ── Image Upload (logo / header / footer) ─────────────────
@router.post("/upload-image", response_model=dict)
async def upload_tenant_image(
    file: UploadFile = File(...),
    image_type: str = Form("logo"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(RoleEnum.admin)),
):
    """
    Upload an image for tenant branding.
    - image_type: 'logo' | 'header' | 'footer'
    - Only JPG/PNG allowed
    - Max size: 512 KB
    Returns data-URI (base64) for embedding in templates.
    """
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if image_type not in ("logo", "header", "footer"):
        raise HTTPException(status_code=400, detail="image_type must be 'logo', 'header', or 'footer'")

    # Validate content type
    ct = (file.content_type or "").lower()
    if ct not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail=f"Only JPG/PNG images are allowed. Got: {ct}")

    # Validate extension
    fname = (file.filename or "").lower()
    ext = os.path.splitext(fname)[1]
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Only .jpg / .png files are allowed. Got: {ext}")

    # Read and validate size
    data = await file.read()
    if len(data) > MAX_IMAGE_SIZE:
        size_kb = len(data) / 1024
        raise HTTPException(
            status_code=400,
            detail=f"Image too large ({size_kb:.0f} KB). Maximum allowed is {MAX_IMAGE_SIZE // 1024} KB."
        )
    if len(data) < 100:
        raise HTTPException(status_code=400, detail="File appears to be empty or corrupt.")

    # Convert to data URI for storage in template JSON
    mime = "image/png" if ext == ".png" else "image/jpeg"
    b64 = base64.b64encode(data).decode("ascii")
    data_uri = f"data:{mime};base64,{b64}"

    # If it's a logo, also save to logo_url field
    if image_type == "logo":
        tenant.logo_url = data_uri
        db.commit()
        db.refresh(tenant)

    return {
        "url": data_uri,
        "image_type": image_type,
        "size_kb": round(len(data) / 1024, 1),
        "filename": file.filename,
    }
