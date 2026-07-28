from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, field_validator
from app.models.purchase import PurchaseOrderStatus


class PurchaseItemCreate(BaseModel):
    product_id:  UUID
    quantity:    Decimal
    unit_cost:   Decimal
    tax_percent: Decimal = Decimal("0")

    @field_validator("quantity", "unit_cost")
    @classmethod
    def positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Must be positive")
        return v


class PurchaseItemResponse(BaseModel):
    model_config = {"from_attributes": True}
    id:                UUID
    product_id:        UUID
    quantity:          Decimal
    unit_cost:         Decimal
    tax_percent:       Decimal
    tax_amount:        Decimal
    line_total:        Decimal


class PurchaseOrderCreate(BaseModel):
    vendor_id:              UUID
    items:                  list[PurchaseItemCreate]
    expected_delivery_date: Optional[date] = None
    notes:                  Optional[str]  = None

    @field_validator("items")
    @classmethod
    def items_nonempty(cls, v):
        if not v:
            raise ValueError("At least one item required")
        return v


class PurchaseOrderUpdate(BaseModel):
    expected_delivery_date: Optional[date] = None
    notes:                  Optional[str]  = None


class PurchaseOrderResponse(BaseModel):
    model_config = {"from_attributes": True}
    id:                     UUID
    tenant_id:              UUID
    po_number:              str
    vendor_id:              UUID
    status:                 PurchaseOrderStatus
    total_amount:           Decimal
    tax_amount:             Decimal
    grand_total:            Decimal
    expected_delivery_date: Optional[date]
    received_at:            Optional[datetime]
    notes:                  Optional[str]
    created_by_id:          UUID
    created_at:             datetime
    updated_at:             Optional[datetime]


class PurchaseOrderDetail(PurchaseOrderResponse):
    items: list[PurchaseItemResponse] = []
