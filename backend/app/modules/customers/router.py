"""
Customers Router
-----------------
IMPORTANT: Static routes (/stats, /with-orders) MUST come before
           parametric routes (/{customer_id}) to avoid FastAPI routing conflicts.
All endpoints are tenant-scoped.
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID
from datetime import date
from io import BytesIO
from pydantic import BaseModel

from app.database.session import get_db
from app.models.employee import Employee, RoleEnum
from app.models.customer import LeadStatus, InterestStatus, SourceType
from app.core.auth.tenant import get_current_tenant_user, require_roles
from app.modules.customers.schemas import (
    CustomerCreate, CustomerUpdate, CustomerResponse,
    CustomerDetail, CustomerProductCreate, CustomerProductResponse,
    InteractionCreate, InteractionResponse,
)
from app.modules.customers import service

router = APIRouter(prefix="/api/customers", tags=["Customers"])


# ── Create ────────────────────────────────────────────────────

@router.post("/", response_model=CustomerResponse, status_code=201)
def create_customer(
    data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.sales)),
):
    return service.create_customer(db, data, current_user)


# ── Legacy list (lead-centric) ───────────────────────────────

@router.get("/")
def list_customers(
    lead_status:          Optional[LeadStatus]     = Query(None),
    interest_status:      Optional[InterestStatus] = Query(None),
    source:               Optional[SourceType]     = Query(None),
    city:                 Optional[str]            = Query(None),
    assigned_employee_id: Optional[UUID]           = Query(None),
    date_from:            Optional[date]           = Query(None),
    date_to:              Optional[date]           = Query(None),
    page:                 int                      = Query(1, ge=1),
    limit:                int                      = Query(50, ge=1, le=200),
    db:                   Session                  = Depends(get_db),
    current_user:         Employee                 = Depends(get_current_tenant_user),
):
    return service.list_customers(
        db, current_user,
        lead_status=lead_status, interest_status=interest_status,
        source=source, city=city,
        assigned_employee_id=assigned_employee_id,
        date_from=date_from, date_to=date_to,
        page=page, limit=limit,
    )


# ─── STATIC routes — MUST be before /{customer_id} ───────────

@router.get("/stats")
def customer_stats(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    return service.get_customer_stats(db, current_user)


@router.get("/with-orders")
def list_customers_with_orders(
    search:    Optional[str]  = Query(None),
    state:     Optional[str]  = Query(None),
    is_active: Optional[bool] = Query(None),
    page:      int            = Query(1, ge=1),
    limit:     int            = Query(50, ge=1, le=200),
    db:        Session        = Depends(get_db),
    current_user: Employee    = Depends(get_current_tenant_user),
):
    return service.list_customers_with_orders(
        db, current_user,
        search=search, state=state, is_active=is_active,
        page=page, limit=limit,
    )


# ── Bulk-print Labels (mass select) ──────────────────────────

class BulkPrintRequest(BaseModel):
    items: List[dict]   # [{customer_id, order_id}, ...]

@router.post("/bulk-labels")
def bulk_print_labels(
    data: BulkPrintRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(
        require_roles(RoleEnum.admin, RoleEnum.operations, RoleEnum.sales)
    ),
):
    pdf_bytes = service.generate_bulk_labels(db, data.items, current_user)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": "inline; filename=bulk_labels.pdf",
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@router.post("/bulk-invoices")
def bulk_print_invoices(
    data: BulkPrintRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(
        require_roles(RoleEnum.admin, RoleEnum.operations, RoleEnum.sales)
    ),
):
    return service.generate_bulk_invoices(db, data.items, current_user)


# ─── Parametric routes — AFTER all static routes ─────────────

@router.get("/{customer_id}", response_model=CustomerDetail)
def get_customer(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    return service.get_customer(db, customer_id, current_user)


@router.patch("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: UUID,
    data: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(
        require_roles(RoleEnum.admin, RoleEnum.sales, RoleEnum.marketing)
    ),
):
    return service.update_customer(db, customer_id, data, current_user)


@router.delete("/{customer_id}")
def delete_customer(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin)),
):
    return service.delete_customer(db, customer_id, current_user)


@router.patch("/{customer_id}/toggle-status")
def toggle_customer_status(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.sales)),
):
    return service.toggle_customer_status(db, customer_id, current_user)


@router.get("/{customer_id}/orders")
def get_customer_orders(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    return service.get_customer_orders(db, customer_id, current_user)


@router.get("/{customer_id}/orders/{order_id}/label")
def print_customer_label(
    customer_id: UUID,
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(
        require_roles(RoleEnum.admin, RoleEnum.operations, RoleEnum.sales)
    ),
):
    pdf_bytes = service.generate_customer_label(db, customer_id, order_id, current_user)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": "inline; filename=label.pdf",
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@router.get("/{customer_id}/orders/{order_id}/invoice")
def print_customer_invoice(
    customer_id: UUID,
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(
        require_roles(RoleEnum.admin, RoleEnum.operations, RoleEnum.sales)
    ),
):
    return service.generate_customer_invoice(db, customer_id, order_id, current_user)


@router.post("/{customer_id}/interactions", response_model=InteractionResponse, status_code=201)
def add_interaction(
    customer_id: UUID,
    data: InteractionCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(
        require_roles(RoleEnum.admin, RoleEnum.sales, RoleEnum.support)
    ),
):
    return service.add_interaction(db, customer_id, data, current_user)


# ── WhatsApp Chat ─────────────────────────────────────────────

class WhatsAppSendRequest(BaseModel):
    message: str
    order_id: Optional[UUID] = None

@router.get("/{customer_id}/whatsapp")
def get_whatsapp_history(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    return service.get_whatsapp_history(db, customer_id, current_user)

@router.post("/{customer_id}/whatsapp", status_code=201)
def send_whatsapp(
    customer_id: UUID,
    data: WhatsAppSendRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(
        require_roles(RoleEnum.admin, RoleEnum.sales, RoleEnum.support, RoleEnum.marketing)
    ),
):
    return service.log_whatsapp_message(db, customer_id, data.message, data.order_id, current_user)

@router.get("/{customer_id}/whatsapp/compose")
def compose_whatsapp(
    customer_id: UUID,
    order_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    return service.compose_whatsapp_for_customer(db, customer_id, order_id, current_user)


@router.post("/{customer_id}/products", response_model=CustomerProductResponse, status_code=201)
def add_product_interest(
    customer_id: UUID,
    data: CustomerProductCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(
        require_roles(RoleEnum.admin, RoleEnum.sales)
    ),
):
    return service.add_product_interest(db, customer_id, data, current_user)
