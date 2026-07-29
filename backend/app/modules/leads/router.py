from uuid import UUID
from typing import Optional
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.core.auth.tenant import get_current_tenant_user, require_roles
from app.models.employee import Employee, RoleEnum
from app.models.lead import LeadPipelineStatus, LeadPriority, LeadSource
from app.modules.leads.schemas import (
    LeadCreate, LeadUpdate,
    LeadResponse, LeadDetail,
    LeadActivityCreate, LeadActivityResponse,
    LeadConvertRequest, LeadFilters, LeadStats,
    ContactedPopupRequest, SuccessWONRequest,
    LeadMessageCreate, LeadMessageResponse,
)
from app.modules.leads import service

router = APIRouter(prefix="/api/leads", tags=["Leads"])


# ─────────────────────────────────────────────────────────────
# CRUD
# ─────────────────────────────────────────────────────────────

@router.post("/", response_model=LeadResponse, status_code=201)
def create_lead(
    data: LeadCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.sales)),
):
    """Create a new lead. Admin and Sales only."""
    return service.create_lead(db, data, current_user)


@router.get("/", response_model=dict)
def list_leads(
    # Filters as query params
    status: Optional[LeadPipelineStatus] = Query(None),
    priority: Optional[LeadPriority]     = Query(None),
    source: Optional[LeadSource]         = Query(None),
    assigned_to_id: Optional[UUID]       = Query(None),
    city: Optional[str]                  = Query(None),
    next_followup_before: Optional[date] = Query(None),
    search: Optional[str]                = Query(None),
    is_favorite: Optional[bool]          = Query(None),
    is_wholesale: Optional[bool]         = Query(None),
    page: int                            = Query(1, ge=1),
    page_size: int                       = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """List leads with filters and pagination. All roles."""
    filters = LeadFilters(
        status=status,
        priority=priority,
        source=source,
        assigned_to_id=assigned_to_id,
        city=city,
        next_followup_before=next_followup_before,
        search=search,
        is_favorite=is_favorite,
        is_wholesale=is_wholesale,
        page=page,
        page_size=page_size,
    )
    return service.list_leads(db, filters, current_user)


@router.get("/stats", response_model=LeadStats)
def get_lead_stats(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Pipeline stats and dashboard numbers. All roles."""
    return service.get_lead_stats(db, current_user)


# ─── STATIC routes — MUST be before /{lead_id} ───────────────────────────────

@router.get("/reminders/today", response_model=dict)
def get_today_reminders(
    target_date: Optional[date] = Query(None, description="Default: today"),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Get all leads with reminders scheduled for today (or target_date). All roles."""
    leads = service.get_reminded_leads(db, current_user, target_date)
    return {
        "count": len(leads),
        "leads": leads,
    }


@router.get("/lost_leads/list", response_model=dict)
def list_lost_leads(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Get leads in 'not_interested' status for recovery campaigns. All roles."""
    return service.get_lost_leads(db, current_user, page, page_size)


# ─── Parametric routes — AFTER all static routes ─────────────────────────────

@router.get("/{lead_id}", response_model=LeadDetail)
def get_lead(
    lead_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Get full lead detail with activity history. All roles."""
    return service.get_lead(db, str(lead_id), current_user)


@router.patch("/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: UUID,
    data: LeadUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(
        require_roles(RoleEnum.admin, RoleEnum.sales, RoleEnum.marketing)
    ),
):
    """Update lead fields. Admin, Sales, Marketing."""
    return service.update_lead(db, str(lead_id), data, current_user)


@router.delete("/{lead_id}", response_model=dict)
def delete_lead(
    lead_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin)),
):
    """Soft-delete a lead. Admin only."""
    return service.delete_lead(db, str(lead_id), current_user)


@router.patch("/{lead_id}/wabis-labels", response_model=dict)
def update_lead_wabis_labels(
    lead_id: UUID,
    data: dict,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(
        require_roles(RoleEnum.admin, RoleEnum.sales, RoleEnum.marketing)
    ),
):
    """Update WABIS labels on a lead. Admin, Sales, Marketing."""
    return service.update_lead_wabis_labels(db, str(lead_id), data.get('labels', []), current_user)


# ─────────────────────────────────────────────────────────────
# Activity Log
# ─────────────────────────────────────────────────────────────

@router.post("/{lead_id}/activities", response_model=LeadActivityResponse, status_code=201)
def add_activity(
    lead_id: UUID,
    data: LeadActivityCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(
        require_roles(RoleEnum.admin, RoleEnum.sales, RoleEnum.support)
    ),
):
    """Log a call, note, WhatsApp, or status change. Admin, Sales, Support."""
    return service.add_activity(db, str(lead_id), data, current_user)


# ─────────────────────────────────────────────────────────────
# Convert → Customer
# ─────────────────────────────────────────────────────────────

@router.post("/{lead_id}/convert", status_code=201)
def convert_lead(
    lead_id: UUID,
    data: Optional[LeadConvertRequest] = None,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(
        require_roles(RoleEnum.admin, RoleEnum.sales)
    ),
):
    """
    Convert a lead into a Customer record.
    Sets lead status = won, creates Customer, links them.
    Admin and Sales only.
    """
    customer = service.convert_lead_to_customer(db, str(lead_id), data or LeadConvertRequest(), current_user)
    return {
        "message": "Lead successfully converted to customer",
        "customer_id": str(customer.id),
        "customer_code": customer.unique_customer_code,
    }


# ─────────────────────────────────────────────────────────────
# Linked Orders
# ─────────────────────────────────────────────────────────────

@router.get("/{lead_id}/orders", response_model=list)
def get_lead_orders(
    lead_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Return all orders linked to this lead. All roles."""
    return service.get_lead_orders(db, str(lead_id), current_user)


# ─────────────────────────────────────────────────────────────
# PHASE 1: Contacted Popup & Workflow Endpoints
# ─────────────────────────────────────────────────────────────

@router.post("/{lead_id}/contacted", response_model=dict, status_code=200)
def mark_contacted(
    lead_id: UUID,
    data: ContactedPopupRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(
        require_roles(RoleEnum.admin, RoleEnum.sales, RoleEnum.support)
    ),
):
    """
    Mark lead as contacted with mandatory note.
    Actions:
    - "save_close": Move to contacted status
    - "remind_later": Schedule reminder for date
    - "not_interested": Move to not_interested (lost leads)
    Admin, Sales, Support only.
    """
    lead = service.mark_contacted(db, str(lead_id), data, current_user)
    return {
        "message": "Lead marked as contacted",
        "lead": LeadResponse.model_validate(lead),
    }


@router.post("/{lead_id}/success_won", response_model=dict, status_code=201)
def finalize_success_won(
    lead_id: UUID,
    data: SuccessWONRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(
        require_roles(RoleEnum.admin, RoleEnum.sales)
    ),
):
    """
    Convert lead to successful customer and create order.
    Moves lead to "success" status, creates Customer record and Order.
    Admin and Sales only.
    """
    result = service.finalize_success_won(
        db,
        str(lead_id),
        order_items=data.order_items,
        payment_method=data.payment_method,
        discount=data.discount or Decimal("0.00"),
        advance_amount=getattr(data, 'advance_amount', Decimal("0.00")) or Decimal("0.00"),
        notes=data.notes,
        shipping_partner_id=data.shipping_partner_id,
        courier_name=data.courier_name,
        courier_code=data.courier_code,
        india_post_customer_id=data.india_post_customer_id,
        current_user=current_user,
    )
    return {
        "message": "Lead successfully converted to customer and order created",
        "lead_id": str(result["lead"].id),
        "customer_id": str(result["customer"].id),
        "order_id": str(result["order"].id),
        "order_number": result["order"].order_number,
    }


@router.get("/{lead_id}/messages", response_model=dict)
def get_whatsapp_messages(
    lead_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Get WhatsApp message history for a lead. All roles."""
    messages = service.get_whatsapp_messages(db, str(lead_id), current_user, limit)
    return {
        "count": len(messages),
        "messages": messages,
    }


@router.post("/{lead_id}/messages", response_model=dict, status_code=201)
def store_whatsapp_message(
    lead_id: UUID,
    data: LeadMessageCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Store incoming/outgoing WhatsApp message for a lead. All roles."""
    message = service.store_whatsapp_message(db, str(lead_id), data, current_user)
    return {
        "message": "Message stored successfully",
        "message_id": str(message.id),
        "created_at": message.created_at.isoformat(),
    }

