from __future__ import annotations
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.auth.tenant import get_current_tenant_user as get_current_user, require_roles
from app.database.session import get_db
from app.models.employee import RoleEnum
from app.models.invoice import InvoiceStatus
from app.modules.invoices.schemas import (
    InvoiceCreate,
    InvoiceDetail,
    InvoiceResponse,
    InvoiceUpdate,
)
from app.modules.invoices import service

router = APIRouter(prefix="/api/invoices", tags=["Invoices"])


@router.post("/", response_model=InvoiceDetail, status_code=201)
def create_invoice(
    data: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(RoleEnum.admin, RoleEnum.sales, RoleEnum.operations)),
):
    return service.create_invoice(db, data, current_user)


@router.get("/", response_model=list[InvoiceResponse])
def list_invoices(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    customer_id: Optional[UUID] = Query(None),
    invoice_status: Optional[InvoiceStatus] = Query(None),
    financial_year: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return service.list_invoices(
        db, current_user,
        skip=skip, limit=limit,
        customer_id=customer_id,
        invoice_status=invoice_status,
        financial_year=financial_year,
    )


@router.get("/{invoice_id}", response_model=InvoiceDetail)
def get_invoice(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return service.get_invoice(db, invoice_id, current_user)


@router.patch("/{invoice_id}", response_model=InvoiceDetail)
def update_invoice(
    invoice_id: UUID,
    data: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(RoleEnum.admin, RoleEnum.sales, RoleEnum.operations)),
):
    return service.update_invoice(db, invoice_id, data, current_user)


@router.post("/{invoice_id}/finalize", response_model=InvoiceDetail)
def finalize_invoice(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(RoleEnum.admin, RoleEnum.operations)),
):
    return service.finalize_invoice(db, invoice_id, current_user)


@router.post("/{invoice_id}/cancel", response_model=InvoiceDetail)
def cancel_invoice(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(RoleEnum.admin)),
):
    return service.cancel_invoice(db, invoice_id, current_user)


@router.get("/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: UUID,
    invoice_type: str = Query("tax_invoice"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Generate and download invoice as A4 PDF."""
    pdf_bytes = service.generate_invoice_pdf(db, invoice_id, current_user, invoice_type=invoice_type)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=invoice-{invoice_id}.pdf"},
    )


@router.get("/order/{order_id}/quick-pdf")
def quick_order_invoice_pdf(
    order_id: UUID,
    invoice_type: str = Query("tax_invoice"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Generate invoice PDF directly from order ID without pre-creating an invoice record."""
    pdf_bytes = service.generate_order_invoice_pdf(db, order_id, current_user, invoice_type=invoice_type)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=invoice-order-{order_id}.pdf"},
    )
