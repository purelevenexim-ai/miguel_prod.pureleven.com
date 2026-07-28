from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, field_validator


# ─────────────────────────────────────────────────────────────────────────────
# Vendor Product (Pricing Catalog)
# ─────────────────────────────────────────────────────────────────────────────

class VendorProductCreate(BaseModel):
    product_id:          UUID
    unit_price:          Decimal
    gst_percent:         Decimal = Decimal("0")
    transport_charge:    Optional[Decimal] = None
    transport_method:    Optional[str]     = None
    min_order_qty:       Optional[Decimal] = None
    max_load_qty:        Optional[Decimal] = None
    lead_time_days:      Optional[int]     = None
    reorder_cycle_days:  Optional[int]     = None
    notes:               Optional[str]     = None
    is_preferred:        bool              = False

    @field_validator("unit_price")
    @classmethod
    def price_positive(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("unit_price must be non-negative")
        return v


class VendorProductUpdate(BaseModel):
    unit_price:          Optional[Decimal] = None
    gst_percent:         Optional[Decimal] = None
    transport_charge:    Optional[Decimal] = None
    transport_method:    Optional[str]     = None
    min_order_qty:       Optional[Decimal] = None
    max_load_qty:        Optional[Decimal] = None
    lead_time_days:      Optional[int]     = None
    reorder_cycle_days:  Optional[int]     = None
    notes:               Optional[str]     = None
    is_preferred:        Optional[bool]    = None


class VendorProductResponse(BaseModel):
    model_config = {"from_attributes": True}

    id:                  UUID
    vendor_id:           UUID
    product_id:          UUID
    unit_price:          Decimal
    gst_percent:         Decimal
    transport_charge:    Optional[Decimal]
    transport_method:    Optional[str]
    min_order_qty:       Optional[Decimal]
    max_load_qty:        Optional[Decimal]
    lead_time_days:      Optional[int]
    reorder_cycle_days:  Optional[int]
    notes:               Optional[str]
    is_preferred:        bool
    price_updated_at:    Optional[datetime]
    created_at:          datetime
    updated_at:          Optional[datetime]

    # Enriched (set in service)
    product_name:        Optional[str]     = None
    product_code:        Optional[str]     = None
    product_unit:        Optional[str]     = None
    landed_cost:         Optional[Decimal] = None


# ─────────────────────────────────────────────────────────────────────────────
# Vendor
# ─────────────────────────────────────────────────────────────────────────────

class VendorCreate(BaseModel):
    company_name:        str
    contact_person:      Optional[str] = None
    phone:               Optional[str] = None
    phone2:              Optional[str] = None
    whatsapp:            Optional[str] = None
    email:               Optional[str] = None
    address:             Optional[str] = None
    city:                Optional[str] = None
    state:               Optional[str] = None
    pincode:             Optional[str] = None
    gst_number:          Optional[str] = None
    pan_number:          Optional[str] = None
    bank_account_name:   Optional[str] = None
    bank_account_number: Optional[str] = None
    ifsc_code:           Optional[str] = None
    vendor_type:         Optional[str] = None
    avg_lead_days:       Optional[int] = None
    payment_terms_days:  Optional[int] = None
    credit_limit:        Optional[Decimal] = None
    vendor_rating:       Optional[int] = None
    notes:               Optional[str] = None
    is_preferred:        bool          = False

    @field_validator("company_name")
    @classmethod
    def name_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("company_name cannot be blank")
        return v.strip()


class VendorUpdate(BaseModel):
    company_name:        Optional[str]  = None
    contact_person:      Optional[str]  = None
    phone:               Optional[str]  = None
    phone2:              Optional[str]  = None
    whatsapp:            Optional[str]  = None
    email:               Optional[str]  = None
    address:             Optional[str]  = None
    city:                Optional[str]  = None
    state:               Optional[str]  = None
    pincode:             Optional[str]  = None
    gst_number:          Optional[str]  = None
    pan_number:          Optional[str]  = None
    bank_account_name:   Optional[str]  = None
    bank_account_number: Optional[str]  = None
    ifsc_code:           Optional[str]  = None
    is_active:           Optional[bool] = None
    vendor_type:         Optional[str]  = None
    avg_lead_days:       Optional[int]  = None
    payment_terms_days:  Optional[int]  = None
    credit_limit:        Optional[Decimal] = None
    vendor_rating:       Optional[int]  = None
    notes:               Optional[str]  = None
    is_preferred:        Optional[bool] = None


class VendorResponse(BaseModel):
    model_config = {"from_attributes": True}

    id:                  UUID
    tenant_id:           UUID
    vendor_code:         str
    company_name:        str
    contact_person:      Optional[str]
    phone:               Optional[str]
    phone2:              Optional[str]
    whatsapp:            Optional[str]
    email:               Optional[str]
    address:             Optional[str]
    city:                Optional[str]
    state:               Optional[str]
    pincode:             Optional[str]
    gst_number:          Optional[str]
    pan_number:          Optional[str]
    bank_account_name:   Optional[str]
    bank_account_number: Optional[str]
    ifsc_code:           Optional[str]
    vendor_type:         Optional[str]
    avg_lead_days:       Optional[int]
    payment_terms_days:  Optional[int]
    credit_limit:        Optional[Decimal]
    vendor_rating:       Optional[int]
    notes:               Optional[str]
    is_active:           bool
    is_preferred:        bool
    created_at:          datetime
    updated_at:          Optional[datetime]


class VendorDetail(VendorResponse):
    """Full vendor with product pricing catalog."""
    products: list[VendorProductResponse] = []


# ─────────────────────────────────────────────────────────────────────────────
# Product Sourcing (who sells this product?)
# ─────────────────────────────────────────────────────────────────────────────

class ProductSourcingEntry(BaseModel):
    vendor_id:           UUID
    vendor_code:         str
    company_name:        str
    city:                Optional[str]
    state:               Optional[str]
    phone:               Optional[str]
    whatsapp:            Optional[str]
    is_preferred:        bool
    unit_price:          Decimal
    gst_percent:         Decimal
    transport_charge:    Optional[Decimal]
    transport_method:    Optional[str]
    lead_time_days:      Optional[int]
    reorder_cycle_days:  Optional[int]
    landed_cost:         Optional[Decimal]
    price_updated_at:    Optional[datetime]
