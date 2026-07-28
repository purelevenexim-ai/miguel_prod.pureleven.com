from pydantic import BaseModel, EmailStr
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date

from app.models.customer import (
    LeadStatus, InterestStatus, CustomerType,
    PaymentMode, SourceType, InteractionType
)


# ─────────────────────────────────────────────────────────────
# Customer Schemas
# ─────────────────────────────────────────────────────────────

class CustomerCreate(BaseModel):
    name:                    str
    phone:                   str
    alternate_phone:         Optional[str]   = None
    email:                   Optional[EmailStr] = None
    address:                 Optional[str]   = None
    pincode:                 Optional[str]   = None
    city:                    Optional[str]   = None
    state:                   Optional[str]   = None
    country:                 Optional[str]   = "India"
    customer_type:           Optional[CustomerType]    = None
    payment_mode_preference: Optional[PaymentMode]     = None
    source:                  Optional[SourceType]      = SourceType.manual
    lead_status:             Optional[LeadStatus]      = LeadStatus.new
    interest_status:         Optional[InterestStatus]  = None
    assigned_employee_id:    Optional[UUID]            = None
    next_followup_date:      Optional[date]            = None
    notes:                   Optional[str]             = None


class CustomerUpdate(BaseModel):
    name:                    Optional[str]             = None
    phone:                   Optional[str]             = None
    alternate_phone:         Optional[str]             = None
    email:                   Optional[EmailStr]        = None
    address:                 Optional[str]             = None
    pincode:                 Optional[str]             = None
    city:                    Optional[str]             = None
    state:                   Optional[str]             = None
    country:                 Optional[str]             = None
    customer_type:           Optional[CustomerType]    = None
    payment_mode_preference: Optional[PaymentMode]     = None
    source:                  Optional[SourceType]      = None
    lead_status:             Optional[LeadStatus]      = None
    interest_status:         Optional[InterestStatus]  = None
    assigned_employee_id:    Optional[UUID]            = None
    next_followup_date:      Optional[date]            = None
    notes:                   Optional[str]             = None


class CustomerResponse(BaseModel):
    id:                      UUID
    tenant_id:               UUID
    unique_customer_code:    str
    name:                    str
    phone:                   str
    alternate_phone:         Optional[str]
    email:                   Optional[str]
    address:                 Optional[str]
    pincode:                 Optional[str]
    city:                    Optional[str]
    state:                   Optional[str]
    country:                 Optional[str]
    customer_type:           Optional[CustomerType]
    payment_mode_preference: Optional[PaymentMode]
    source:                  Optional[SourceType]
    lead_status:             LeadStatus
    interest_status:         Optional[InterestStatus]
    assigned_employee_id:    Optional[UUID]
    created_by_employee_id:  UUID
    last_contacted_at:       Optional[datetime]
    next_followup_date:      Optional[date]
    notes:                   Optional[str]
    is_active:               bool
    created_at:              Optional[datetime]
    updated_at:              Optional[datetime]

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────
# Product Interest Schemas
# ─────────────────────────────────────────────────────────────

class CustomerProductCreate(BaseModel):
    product_name:        str
    quantity_interested: Optional[int]  = None
    note:                Optional[str]  = None


class CustomerProductResponse(BaseModel):
    id:                  UUID
    customer_id:         UUID
    product_name:        str
    quantity_interested: Optional[int]
    note:                Optional[str]
    created_at:          Optional[datetime]

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────
# Interaction Schemas
# ─────────────────────────────────────────────────────────────

class InteractionCreate(BaseModel):
    interaction_type: InteractionType
    message_content:  Optional[str]   = None
    new_status:       Optional[LeadStatus] = None


class InteractionResponse(BaseModel):
    id:               UUID
    customer_id:      UUID
    employee_id:      UUID
    interaction_type: InteractionType
    message_content:  Optional[str]
    old_status:       Optional[LeadStatus]
    new_status:       Optional[LeadStatus]
    created_at:       Optional[datetime]

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────
# Customer Detail (Full Profile)
# ─────────────────────────────────────────────────────────────

class CustomerDetail(CustomerResponse):
    products:     List[CustomerProductResponse] = []
    interactions: List[InteractionResponse]     = []


# ─────────────────────────────────────────────────────────────
# Tag Schemas
# ─────────────────────────────────────────────────────────────

class TagCreate(BaseModel):
    name: str


class TagResponse(BaseModel):
    id:   UUID
    name: str

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────
# Filter Params (for list endpoint)
# ─────────────────────────────────────────────────────────────

class CustomerFilters(BaseModel):
    lead_status:          Optional[LeadStatus]      = None
    interest_status:      Optional[InterestStatus]  = None
    source:               Optional[SourceType]       = None
    city:                 Optional[str]              = None
    assigned_employee_id: Optional[UUID]             = None
    date_from:            Optional[date]             = None
    date_to:              Optional[date]             = None
    page:                 int                        = 1
    limit:                int                        = 50
