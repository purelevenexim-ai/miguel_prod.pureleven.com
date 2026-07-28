from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, field_validator
from app.models.invoice import InvoiceStatus


class InvoiceItemCreate(BaseModel):
    product_id:   Optional[UUID] = None
    product_name: str
    hsn_code:     Optional[str] = None
    quantity:     Decimal
    unit_price:   Decimal
    tax_percent:  Decimal = Decimal("0")

    @field_validator("quantity", "unit_price")
    @classmethod
    def positive(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Must be non-negative")
        return v


class InvoiceCreate(BaseModel):
    order_id:         Optional[UUID] = None
    customer_id:      UUID
    invoice_date:     date
    billing_address:  Optional[str] = None
    shipping_address: Optional[str] = None
    customer_gst:     Optional[str] = None
    customer_state:   Optional[str] = None   # for GST type determination
    supply_state:     Optional[str] = None   # tenant's state
    notes:            Optional[str] = None
    items:            list[InvoiceItemCreate]

    @field_validator("items")
    @classmethod
    def items_nonempty(cls, v):
        if not v:
            raise ValueError("At least one item required")
        return v


class InvoiceUpdate(BaseModel):
    billing_address:  Optional[str] = None
    shipping_address: Optional[str] = None
    customer_gst:     Optional[str] = None
    customer_state:   Optional[str] = None
    supply_state:     Optional[str] = None
    notes:            Optional[str] = None


class InvoiceItemResponse(BaseModel):
    model_config = {"from_attributes": True}
    id:             UUID
    product_id:     Optional[UUID]
    product_name:   str
    hsn_code:       Optional[str]
    quantity:       Decimal
    unit_price:     Decimal
    taxable_amount: Decimal
    tax_percent:    Decimal
    cgst_percent:   Decimal
    sgst_percent:   Decimal
    igst_percent:   Decimal
    cgst_amount:    Decimal
    sgst_amount:    Decimal
    igst_amount:    Decimal
    tax_amount:     Decimal
    line_total:     Decimal


class InvoiceResponse(BaseModel):
    model_config = {"from_attributes": True}
    id:               UUID
    tenant_id:        UUID
    invoice_number:   str
    financial_year:   str
    invoice_date:     date
    order_id:         Optional[UUID]
    customer_id:      UUID
    billing_address:  Optional[str]
    shipping_address: Optional[str]
    customer_gst:     Optional[str]
    customer_state:   Optional[str]
    supply_state:     Optional[str]
    total_taxable:    Decimal
    cgst_amount:      Decimal
    sgst_amount:      Decimal
    igst_amount:      Decimal
    total_tax:        Decimal
    grand_total:      Decimal
    status:           InvoiceStatus
    notes:            Optional[str]
    created_by_id:    UUID
    created_at:       datetime
    updated_at:       Optional[datetime]


class InvoiceDetail(InvoiceResponse):
    items: list[InvoiceItemResponse] = []
