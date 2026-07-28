"""
Labels & WhatsApp Router
-------------------------
POST  /api/labels/generate               → PDF StreamingResponse (admin + operations)
GET   /api/labels/orders/{id}/whatsapp   → Single WhatsApp message (all roles)
POST  /api/labels/whatsapp/bulk          → Bulk WhatsApp messages (all roles)
"""

from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.core.auth.tenant import get_current_tenant_user, require_roles
from app.models.employee import Employee, RoleEnum
from app.modules.labels.schemas import (
    LabelRequest,
    WhatsAppMessageResponse,
    WhatsAppBulkResponse,
)
from app.modules.labels import service

router = APIRouter(prefix="/api/labels", tags=["Labels"])


# ─────────────────────────────────────────────────────────────
# PDF Label Generation
# ─────────────────────────────────────────────────────────────

@router.post("/generate")
def generate_labels(
    data: LabelRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(
        require_roles(RoleEnum.admin, RoleEnum.operations)
    ),
):
    """
    Generate a 4×6 PDF shipping label sheet for the given order IDs.
    Only admin and operations roles may generate labels.
    Increments printed_count on each matched order.
    """
    pdf_bytes, meta = service.generate_labels(
        db=db,
        order_ids=data.order_ids,
        current_user=current_user,
    )
    headers = {
        "X-Orders-Printed": str(meta.orders_printed),
        "X-Orders-Skipped": str(meta.skipped),
        "Content-Disposition": "attachment; filename=labels.pdf",
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers=headers,
    )


# ─────────────────────────────────────────────────────────────
# WhatsApp Message Composition
# ─────────────────────────────────────────────────────────────

@router.get("/orders/{order_id}/whatsapp", response_model=WhatsAppMessageResponse)
def whatsapp_single(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """
    Get a WhatsApp message payload for a single order.
    Returns the composed message text, template name, and wa.me URL.
    """
    return service.get_whatsapp_message(
        db=db,
        order_id=order_id,
        current_user=current_user,
    )


@router.post("/whatsapp/bulk", response_model=WhatsAppBulkResponse)
def whatsapp_bulk(
    data: LabelRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """
    Get WhatsApp message payloads for multiple orders at once.
    Orders not belonging to the current tenant are silently skipped.
    """
    return service.get_whatsapp_bulk(
        db=db,
        order_ids=data.order_ids,
        current_user=current_user,
    )
