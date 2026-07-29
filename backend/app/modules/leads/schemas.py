from __future__ import annotations
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, field_validator

from app.models.lead import LeadPipelineStatus, LeadPriority, LeadSource, LeadActivityType


# ─────────────────────────────────────────────────────────────
# Lead Create / Update
# ─────────────────────────────────────────────────────────────

class LeadCreate(BaseModel):
    name: str
    phone: str
    alternate_phone: Optional[str] = None
    email: Optional[str] = None
    company_name: Optional[str] = None

    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "India"

    source: Optional[LeadSource] = LeadSource.manual
    priority: Optional[LeadPriority] = LeadPriority.medium
    status: Optional[LeadPipelineStatus] = LeadPipelineStatus.new_lead

    estimated_value: Optional[Decimal] = None
    product_interest: Optional[str] = None

    assigned_to_id: Optional[UUID] = None
    next_followup_date: Optional[date] = None
    notes: Optional[str] = None
    
    # PHASE 1 & 4: New fields
    order_id: Optional[UUID] = None
    customer_id: Optional[UUID] = None
    remind_later_date: Optional[date] = None
    is_archived: Optional[bool] = False
    is_favorite: Optional[bool] = False
    is_wholesale: Optional[bool] = False


class LeadUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    alternate_phone: Optional[str] = None
    email: Optional[str] = None
    company_name: Optional[str] = None

    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None

    source: Optional[LeadSource] = None
    priority: Optional[LeadPriority] = None
    status: Optional[LeadPipelineStatus] = None

    estimated_value: Optional[Decimal] = None
    product_interest: Optional[str] = None

    assigned_to_id: Optional[UUID] = None
    next_followup_date: Optional[date] = None
    notes: Optional[str] = None
    
    # PHASE 1 & 4: New fields
    order_id: Optional[UUID] = None
    customer_id: Optional[UUID] = None
    remind_later_date: Optional[date] = None
    is_archived: Optional[bool] = None
    is_favorite: Optional[bool] = None
    is_wholesale: Optional[bool] = None
    note_last: Optional[str] = None


# ─────────────────────────────────────────────────────────────
# Lead Responses
# ─────────────────────────────────────────────────────────────

class LeadResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    tenant_id: UUID
    lead_number: str

    name: str
    phone: str
    alternate_phone: Optional[str]
    email: Optional[str]
    company_name: Optional[str]

    city: Optional[str]
    state: Optional[str]
    country: Optional[str]

    source: Optional[LeadSource]
    priority: LeadPriority
    status: LeadPipelineStatus

    estimated_value: Optional[Decimal]
    product_interest: Optional[str]

    assigned_to_id: Optional[UUID]
    created_by_id: UUID

    converted_customer_id: Optional[UUID]
    converted_at: Optional[datetime]

    last_contacted_at: Optional[datetime]
    next_followup_date: Optional[date]
    
    # PHASE 1 & 4: New fields
    order_id: Optional[UUID]
    customer_id: Optional[UUID]
    remind_later_date: Optional[date]
    contacted_count: int
    is_archived: bool
    is_favorite: bool
    is_wholesale: bool
    note_last: Optional[str]

    # ── WABIS Integration ──────────────────────────
    wabis_labels: Optional[list[str]] = None

    notes: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]


class LeadDetail(LeadResponse):
    """Full lead with activity history."""
    activities: list[LeadActivityResponse] = []


# ─────────────────────────────────────────────────────────────
# Lead Activity
# ─────────────────────────────────────────────────────────────

class LeadActivityCreate(BaseModel):
    activity_type: LeadActivityType
    note: Optional[str] = None
    new_status: Optional[LeadPipelineStatus] = None


class LeadActivityResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    lead_id: UUID
    employee_id: UUID
    activity_type: LeadActivityType
    note: Optional[str]
    old_status: Optional[LeadPipelineStatus]
    new_status: Optional[LeadPipelineStatus]
    created_at: datetime


# ─────────────────────────────────────────────────────────────
# Lead Conversion
# ─────────────────────────────────────────────────────────────

class LeadConvertRequest(BaseModel):
    """
    Convert a lead to a Customer.
    Optionally override fields; defaults to lead's existing data.
    """
    customer_type: Optional[str] = None          # home_cook / wholesaler / retailer / mill
    payment_mode_preference: Optional[str] = None
    notes: Optional[str] = None


# ─────────────────────────────────────────────────────────────
# Lead Filters (for GET /api/leads/)
# ─────────────────────────────────────────────────────────────

class LeadFilters(BaseModel):
    status: Optional[LeadPipelineStatus] = None
    priority: Optional[LeadPriority] = None
    source: Optional[LeadSource] = None
    assigned_to_id: Optional[UUID] = None
    city: Optional[str] = None
    next_followup_before: Optional[date] = None   # leads due on or before this date
    search: Optional[str] = None                  # name / phone / company search
    is_favorite: Optional[bool] = None
    is_wholesale: Optional[bool] = None
    page: int = 1
    page_size: int = 20


# ─────────────────────────────────────────────────────────────
# Lead Stats
# ─────────────────────────────────────────────────────────────

class LeadStats(BaseModel):
    total: int
    by_status: dict
    by_priority: dict
    by_source: dict
    overdue_followups: int
    converted_this_month: int
    won_this_month: int
    total_pipeline_value: Optional[Decimal]


# ─────────────────────────────────────────────────────────────
# PHASE 1: Contacted Popup & Workflow Schemas
# ─────────────────────────────────────────────────────────────

class ContactedPopupRequest(BaseModel):
    """
    Mark lead as contacted with mandatory notes.
    Staff chooses: save & close, remind later, or mark as lost lead.
    """
    note: str  # Mandatory note field (min 1 char)
    action: str  # "save_close" | "remind_later" | "not_interested"
    remind_later_date: Optional[date] = None  # Required if action == "remind_later"

    @field_validator("note")
    @classmethod
    def validate_note(cls, v):
        if not v or len(v.strip()) < 1:
            raise ValueError("Note cannot be empty")
        return v.strip()

    @field_validator("remind_later_date")
    @classmethod
    def validate_remind_later_date(cls, v, info):
        if info.data.get("action") == "remind_later" and v is None:
            raise ValueError("remind_later_date required when action is 'remind_later'")
        return v


class SuccessWONRequest(BaseModel):
    """
    Convert lead to successful customer and create order.
    Includes order data (items, payment method, discount, etc).
    """
    order_items: list[dict]  # [{product_id: UUID, quantity: float, unit: str}]
    payment_method: str      # "cash" | "upi" | "bank_transfer" | "cheque" | "credit" | "partial_cod"
    discount: Optional[Decimal] = Decimal("0.00")
    advance_amount: Optional[Decimal] = Decimal("0.00")   # Partial COD advance payment
    notes: Optional[str] = None
    delivery_date: Optional[date] = None
    shipping_partner_id: Optional[UUID] = None
    courier_name: Optional[str] = None
    courier_code: Optional[str] = None
    india_post_customer_id: Optional[str] = None


class LeadMessageCreate(BaseModel):
    """
    Store incoming/outgoing WhatsApp message for lead.
    Direction: inbound (from customer) | outbound (staff reply)
    """
    message_body: str
    direction: str  # "inbound" | "outbound"
    whatsapp_message_id: Optional[str] = None  # Meta Business message ID for tracking


class LeadMessageResponse(BaseModel):
    """Response model for stored WhatsApp messages."""
    model_config = {"from_attributes": True}

    id: UUID
    lead_id: UUID
    tenant_id: UUID
    message_body: str
    direction: str
    whatsapp_message_id: Optional[str]
    created_at: datetime


class LostLeadResponse(BaseModel):
    """Lead in lost/not_interested status for recovery campaigns."""
    model_config = {"from_attributes": True}

    id: UUID
    lead_number: str
    name: str
    phone: str
    company_name: Optional[str]
    status: LeadPipelineStatus
    last_contacted_at: Optional[datetime]
    notes: Optional[str]
    days_since_contact: Optional[int]


class ReminderLeadResponse(BaseModel):
    """Lead with reminder scheduled for today/future date."""
    model_config = {"from_attributes": True}

    id: UUID
    lead_number: str
    name: str
    phone: str
    company_name: Optional[str]
    status: LeadPipelineStatus
    remind_later_date: Optional[date]
    assigned_to_id: Optional[UUID]
    last_contacted_at: Optional[datetime]
    notes: Optional[str]


# ── Forward ref resolution ────────────────────────────────────
LeadDetail.model_rebuild()
