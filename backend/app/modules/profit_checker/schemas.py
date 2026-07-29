"""
Profit Checker Schemas
-----------------------
Request and response models for the Profit Checker API.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


# ─────────────────────────────────────────────────────────────
# Groups
# ─────────────────────────────────────────────────────────────

class GroupCreatePayload(BaseModel):
    name: str
    sort_order: Optional[int] = None


class GroupItemPayload(BaseModel):
    name: str
    allocation_type: str = "monthly"   # monthly | per_order | per_unit
    product_id: Optional[UUID] = None
    items_per_trigger: Optional[Decimal] = None
    sort_order: Optional[int] = None


class GroupItemOut(BaseModel):
    id: UUID
    group_id: UUID
    name: str
    allocation_type: str
    product_id: Optional[UUID]
    items_per_trigger: Optional[Decimal]
    is_active: bool
    sort_order: int

    class Config:
        from_attributes = True


class GroupOut(BaseModel):
    id: UUID
    name: str
    group_type: str
    sub_type: Optional[str]          # 'packing_material' | 'courier_material' | None
    sort_order: int
    is_system: bool
    is_active: bool
    items: list[GroupItemOut] = []

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────
# Entries
# ─────────────────────────────────────────────────────────────

class EntryPayload(BaseModel):
    group_id: UUID
    item_id: Optional[UUID] = None
    month: str                             # "YYYY-MM"
    description: str                       # was 'label'
    amount: Optional[Decimal] = None       # computed from qty × unit_cost if omitted
    quantity: Optional[Decimal] = None
    unit_cost: Optional[Decimal] = None
    product_id: Optional[UUID] = None      # linked catalog product for purchase entries only
    applicable_categories: Optional[list[str]] = None
    consumption_rate: Optional[Decimal] = None  # units/product-sold (packing) or units/order (courier)
    reference_po_id: Optional[UUID] = None
    note: Optional[str] = None


class EntryOut(BaseModel):
    id: UUID
    group_id: UUID
    item_id: Optional[UUID]
    month: str
    description: str
    amount: Decimal
    quantity: Optional[Decimal]
    unit_cost: Optional[Decimal]
    product_id: Optional[UUID]
    applicable_categories: Optional[list[str]]
    consumption_rate: Optional[Decimal]
    reference_po_id: Optional[UUID]
    note: Optional[str]

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────
# Product Maps
# ─────────────────────────────────────────────────────────────

class ProductMapPayload(BaseModel):
    source_product_id: UUID
    target_product_id: UUID
    conversion_ratio: Optional[Decimal] = Decimal("1.0")


class ProductMapOut(BaseModel):
    id: UUID
    source_product_id: UUID
    target_product_id: UUID
    conversion_ratio: Decimal
    is_active: bool

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────
# Period Snapshot
# ─────────────────────────────────────────────────────────────

class PeriodSnapshotOut(BaseModel):
    id: UUID
    period: str
    period_type: str
    sales_revenue: Decimal
    order_count: int
    cogs: Decimal
    packaging_cost: Decimal
    courier_material_cost: Decimal
    shipping_cost: Decimal = Decimal("0")
    gateway_fee: Decimal = Decimal("0")
    rto_loss: Decimal = Decimal("0")
    salary_ops_cost: Decimal
    ads_marketing_cost: Decimal
    other_cost: Decimal
    total_expense: Decimal
    opening_stock_value: Decimal
    closing_stock_value: Decimal
    purchases_value: Decimal
    gross_profit: Decimal
    net_profit: Decimal
    margin_pct: Decimal
    group_totals: Optional[dict]
    is_locked: bool

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────
# Alerts
# ─────────────────────────────────────────────────────────────

class AlertOut(BaseModel):
    id: UUID
    alert_type: str
    reference_id: Optional[UUID]
    month: str
    message: str
    severity: str
    is_dismissed: bool
    dismissed_at: Optional[str] = None   # ISO string, None if not dismissed

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────
# Cost suggestions
# ─────────────────────────────────────────────────────────────

class CostSuggestionRow(BaseModel):
    product_id: str
    product_code: str
    name: str
    current_cost_price: float
    wac_cost: float
    diff_pct: float
