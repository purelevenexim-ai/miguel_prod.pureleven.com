from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel
from app.models.inventory import MovementType


class StockAdjustmentRequest(BaseModel):
    product_id:      UUID
    quantity_change: Decimal   # positive = add, negative = remove
    note:            Optional[str] = None


class InventoryMovementResponse(BaseModel):
    model_config = {"from_attributes": True}
    id:              UUID
    product_id:      UUID
    movement_type:   MovementType
    quantity_change: Decimal
    reference_id:    Optional[UUID]
    reference_type:  Optional[str]
    note:            Optional[str]
    created_at:      datetime


class InventorySummaryResponse(BaseModel):
    model_config = {"from_attributes": True}
    product_id:    UUID
    current_stock: Decimal
    updated_at:    datetime
