from __future__ import annotations
from typing import Optional, Literal
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, field_validator

from app.models.order import (
    OrderStatus, PaymentStatus, PaymentMethod, OrderItemUnit
)


# ─────────────────────────────────────────────────────────────
# Order Item
# ─────────────────────────────────────────────────────────────

class OrderItemCreate(BaseModel):
    product_name: str
    sku: Optional[str] = None
    quantity: Decimal
    unit: OrderItemUnit = OrderItemUnit.piece
    unit_price: Decimal
    discount_pct: Optional[Decimal] = Decimal("0")
    notes: Optional[str] = None

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Quantity must be greater than zero")
        return v

    @field_validator("unit_price")
    @classmethod
    def price_non_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Unit price cannot be negative")
        return v


class OrderItemResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    order_id: UUID
    product_name: str
    sku: Optional[str]
    quantity: Decimal
    unit: OrderItemUnit
    unit_price: Decimal
    discount_pct: Decimal
    line_total: Decimal
    notes: Optional[str]
    created_at: datetime


# ─────────────────────────────────────────────────────────────
# Order Create / Update
# ─────────────────────────────────────────────────────────────

class OrderCreate(BaseModel):
    # Customer — either existing ID or name+phone for auto-create/lookup
    customer_id: Optional[UUID] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_phone2: Optional[str] = None   # alternate phone

    # Order intent: confirmed (default) or not_confirmed → goes to Leads
    order_intent: Literal["confirmed", "not_confirmed"] = "confirmed"
    not_confirmed_reason: Optional[str] = None
    followup_date: Optional[date] = None    # for lead follow-up scheduling

    items: list[OrderItemCreate]

    payment_method: Optional[PaymentMethod] = None

    # Delivery / Address
    address_raw: Optional[str] = None          # raw paste (WhatsApp text)
    delivery_name: Optional[str] = None        # recipient name
    address_name2: Optional[str] = None        # second name
    delivery_address: Optional[str] = None
    delivery_city: Optional[str] = None
    delivery_district: Optional[str] = None
    delivery_state: Optional[str] = None
    delivery_pincode: Optional[str] = None
    expected_delivery: Optional[date] = None

    # Tracking
    tracking_number: Optional[str] = None
    courier_name: Optional[str] = None
    courier_code: Optional[str] = None
    shipping_partner_id: Optional[UUID] = None    # Link to DeliveryPartner (NEW)

    # India Post specific
    shipping_service: Optional[str] = None    # speed_post | parcel
    india_post_customer_id: Optional[str] = None

    # Override amounts
    discount_amount: Optional[Decimal] = Decimal("0")
    tax_amount: Optional[Decimal] = Decimal("0")
    shipping_charge: Optional[Decimal] = Decimal("0")
    
    # Partial COD: advance payment amount (only for partial_cod payment method)
    advance_amount: Optional[Decimal] = Decimal("0")

    assigned_to_id: Optional[UUID] = None
    notes: Optional[str] = None
    order_source: Optional[str] = "manual"
    gst_invoice: Optional[bool] = True  # True = GST bill; False = non-GST bill for this order
    lead_id: Optional[UUID] = None      # Link this order to an existing lead (Phase 5)

    @field_validator("items")
    @classmethod
    def items_not_empty(cls, v):
        if not v:
            raise ValueError("Order must have at least one item")
        return v


class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None           # manual status override
    order_number: Optional[str] = None             # allow renaming order number
    payment_method: Optional[PaymentMethod] = None
    payment_status: Optional[PaymentStatus] = None   # manual override allowed
    delivery_name: Optional[str] = None
    address_name2: Optional[str] = None
    delivery_address: Optional[str] = None
    delivery_city: Optional[str] = None
    delivery_district: Optional[str] = None
    delivery_state: Optional[str] = None
    delivery_pincode: Optional[str] = None
    delivery_phone2: Optional[str] = None
    expected_delivery: Optional[date] = None
    tracking_number: Optional[str] = None
    courier_name: Optional[str] = None
    courier_code: Optional[str] = None
    shipping_partner_id: Optional[UUID] = None    # Link to DeliveryPartner
    shipping_service: Optional[str] = None
    india_post_customer_id: Optional[str] = None
    discount_amount: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    shipping_charge: Optional[Decimal] = None
    advance_amount: Optional[Decimal] = None      # Partial COD advance payment
    amount_paid: Optional[Decimal] = None         # Manual payment amount edit (draft orders)
    amount_due: Optional[Decimal] = None          # Manual amount due edit (draft orders)
    assigned_to_id: Optional[UUID] = None
    notes: Optional[str] = None
    items: Optional[list] = None                  # Replace order items (list of OrderItemCreate dicts)


# ─────────────────────────────────────────────────────────────
# Order Responses
# ─────────────────────────────────────────────────────────────

class OrderResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    tenant_id: UUID
    order_number: str
    customer_id: UUID
    status: OrderStatus
    payment_status: PaymentStatus
    payment_method: Optional[PaymentMethod]
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    shipping_charge: Decimal
    total_amount: Decimal
    amount_paid: Decimal
    amount_due: Decimal
    # Partial COD tracking
    advance_amount: Decimal = Decimal("0")   # Advance paid upfront
    cod_amount: Decimal = Decimal("0")       # Remaining payable on delivery
    # Delivery / Address
    delivery_name: Optional[str] = None
    address_name2: Optional[str] = None
    delivery_phone2: Optional[str] = None
    delivery_address: Optional[str]
    delivery_city: Optional[str]
    delivery_district: Optional[str] = None
    delivery_state: Optional[str]
    delivery_pincode: Optional[str]
    expected_delivery: Optional[date]
    delivered_at: Optional[datetime]
    tracking_number: Optional[str]
    courier_name: Optional[str]
    courier_code: Optional[str] = None
    tracking_status_text: Optional[str] = None
    tracking_last_location: Optional[str] = None
    tracking_last_event_at: Optional[datetime] = None
    tracking_synced_at: Optional[datetime] = None
    tracking_events_json: Optional[list | dict] = None
    return_status: Optional[str] = None
    actual_shipping_cost: Optional[Decimal] = None
    shipping_partner_id: Optional[UUID] = None
    shipping_service: Optional[str] = None
    india_post_customer_id: Optional[str] = None
    not_confirmed_reason: Optional[str] = None
    lead_id: Optional[UUID] = None
    order_source: Optional[str] = None
    wa_confirmed_sent: bool = False
    wa_shipped_sent: bool = False
    whatsapp_journey: Optional[dict] = None
    assigned_to_id: Optional[UUID]
    created_by_id: UUID
    notes: Optional[str]
    is_active: bool
    printed_count: int = 0
    gst_invoice: bool = True
    items_summary: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime]


class OrderDetail(OrderResponse):
    """Full order with line items, payments, and status history."""
    items: list[OrderItemResponse] = []
    payments: list[OrderPaymentResponse] = []
    status_history: list[OrderStatusHistoryResponse] = []


# ─────────────────────────────────────────────────────────────
# Status Change
# ─────────────────────────────────────────────────────────────

class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    note: Optional[str] = None
    tracking_number: Optional[str] = None
    courier_name: Optional[str] = None


# ─────────────────────────────────────────────────────────────
# Payment Recording
# ─────────────────────────────────────────────────────────────

class OrderPaymentCreate(BaseModel):
    amount: Decimal
    method: PaymentMethod
    reference: Optional[str] = None
    note: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v):
        if v <= 0:
            raise ValueError("Payment amount must be greater than zero")
        return v


class OrderPaymentResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    order_id: UUID
    employee_id: UUID
    amount: Decimal
    method: PaymentMethod
    reference: Optional[str]
    note: Optional[str]
    paid_at: datetime


# ─────────────────────────────────────────────────────────────
# Status History
# ─────────────────────────────────────────────────────────────

class OrderStatusHistoryResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    order_id: UUID
    employee_id: UUID
    old_status: Optional[OrderStatus]
    new_status: OrderStatus
    note: Optional[str]
    created_at: datetime


# ─────────────────────────────────────────────────────────────
# Filters + Stats
# ─────────────────────────────────────────────────────────────

class OrderFilters(BaseModel):
    status: Optional[OrderStatus] = None
    payment_status: Optional[PaymentStatus] = None
    customer_id: Optional[UUID] = None
    assigned_to_id: Optional[UUID] = None
    search: Optional[str] = None          # order_number search
    created_after: Optional[date] = None
    created_before: Optional[date] = None
    is_active: Optional[bool] = True      # default: show active only; None = show all
    page: int = 1
    page_size: int = 20


class OrderStats(BaseModel):
    total_orders: int
    by_status: dict
    by_payment_status: dict
    total_revenue: Optional[Decimal]      # sum of total_amount for delivered
    total_outstanding: Optional[Decimal]  # sum of amount_due for active orders
    orders_this_month: int
    revenue_this_month: Optional[Decimal]
    cod_pending_count: int                # COD + Partial COD orders that need courier collection


# ── Forward ref resolution ─────────────────────────────────────
OrderDetail.model_rebuild()
