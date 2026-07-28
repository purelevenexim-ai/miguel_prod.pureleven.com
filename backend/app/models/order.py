import enum
import uuid
from sqlalchemy import (
    Column, String, Boolean, Text, Date, DateTime,
    Enum, ForeignKey, Integer, Numeric, UniqueConstraint, Index, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


# ─────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────

class OrderStatus(str, enum.Enum):
    draft           = "draft"
    confirmed       = "confirmed"
    processing      = "processing"
    packed          = "packed"
    shipped         = "shipped"
    out_for_delivery = "out_for_delivery"
    delivered       = "delivered"
    cancelled       = "cancelled"
    returned        = "returned"


class PaymentStatus(str, enum.Enum):
    pending     = "pending"
    partial     = "partial"
    paid        = "paid"
    refunded    = "refunded"
    failed      = "failed"


class PaymentMethod(str, enum.Enum):
    cash                = "cash"
    upi                 = "upi"
    bank_transfer       = "bank_transfer"
    cheque              = "cheque"
    cod                 = "cod"
    partial_cod         = "partial_cod"      # Partial advance paid + COD for balance (NEW)
    credit              = "credit"           # pay later / credit account


class OrderItemUnit(str, enum.Enum):
    kg      = "kg"
    gram    = "gram"
    litre   = "litre"
    ml      = "ml"
    piece   = "piece"
    bag     = "bag"
    box     = "box"
    carton  = "carton"
    bundle  = "bundle"
    pack    = "pack"


# ─────────────────────────────────────────────────────────────
# Order (Master Table)
# ─────────────────────────────────────────────────────────────

class Order(Base):
    __tablename__ = "orders"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id       = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    order_number    = Column(String(30), nullable=False)    # PLX-260221-001

    # ── Customer ──────────────────────────────────────────────
    customer_id     = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)

    # ── Status ────────────────────────────────────────────────
    status          = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.draft)
    payment_status  = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.pending)
    payment_method  = Column(Enum(PaymentMethod), nullable=True)

    # ── Amounts ───────────────────────────────────────────────
    subtotal        = Column(Numeric(12, 2), nullable=False, default=0)   # sum of line items
    discount_amount = Column(Numeric(12, 2), nullable=False, default=0)
    tax_amount      = Column(Numeric(12, 2), nullable=False, default=0)
    shipping_charge = Column(Numeric(12, 2), nullable=False, default=0)
    total_amount    = Column(Numeric(12, 2), nullable=False, default=0)   # final payable
    amount_paid     = Column(Numeric(12, 2), nullable=False, default=0)
    amount_due      = Column(Numeric(12, 2), nullable=False, default=0)   # total - paid

    # ── Partial COD (Issue: Partial Payment) ────────────────────
    advance_amount  = Column(Numeric(12, 2), nullable=False, default=0)   # advance paid upfront
    cod_amount      = Column(Numeric(12, 2), nullable=False, default=0)   # payable on delivery

    # ── Delivery ──────────────────────────────────────────────
    delivery_address    = Column(Text, nullable=True)
    delivery_city       = Column(String(100), nullable=True)
    delivery_state      = Column(String(100), nullable=True)
    delivery_pincode    = Column(String(10), nullable=True)
    expected_delivery   = Column(Date, nullable=True)
    delivered_at        = Column(DateTime(timezone=True), nullable=True)

    # ── Tracking ──────────────────────────────────────────────
    tracking_number     = Column(String(100), nullable=True)
    courier_name        = Column(String(100), nullable=True)

    # ── Courier tracking metadata ─────────────────────────────
    tracking_status_text    = Column(String(120), nullable=True)
    tracking_last_location  = Column(String(255), nullable=True)
    tracking_last_event_at  = Column(DateTime(timezone=True), nullable=True)
    tracking_synced_at      = Column(DateTime(timezone=True), nullable=True)
    tracking_events_json    = Column(JSON, nullable=True)
    tracking_raw_response   = Column(JSON, nullable=True)
    return_status           = Column(String(120), nullable=True)
    actual_shipping_cost    = Column(Numeric(12, 2), nullable=True)

    # ── Fulfillment Engine — Address / Delivery ────────────────
    address_raw         = Column(Text, nullable=True)           # pasted raw text before parse
    address_name2       = Column(String(255), nullable=True)    # second name if 2 names found
    delivery_name       = Column(String(255), nullable=True)    # recipient name (primary)
    delivery_phone2     = Column(String(20), nullable=True)     # alternate phone
    delivery_district   = Column(String(100), nullable=True)

    # ── Shipping / India Post ──────────────────────────────────
    shipping_service        = Column(String(50), nullable=True)    # speed_post | parcel
    india_post_customer_id  = Column(String(50), nullable=True)    # selected IP customer ID
    shipping_partner_id     = Column(UUID(as_uuid=True), ForeignKey("delivery_partners.id"), nullable=True)  # Link to DeliveryPartner (NEW)
    courier_id              = Column(UUID(as_uuid=True), ForeignKey("couriers.id"), nullable=True)
    courier_code            = Column(String(50), nullable=True)    # snapshot

    # ── Not-Confirmed / Lead link ──────────────────────────────
    not_confirmed_reason    = Column(Text, nullable=True)
    order_source            = Column(String(50), nullable=True, default="manual")
    gst_invoice             = Column(Boolean, nullable=False, default=True)   # True = GST bill, False = non-GST bill
    lead_id                 = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)

    # ── WhatsApp flags ─────────────────────────────────────────
    wa_confirmed_sent   = Column(Boolean, nullable=False, default=False)
    wa_shipped_sent     = Column(Boolean, nullable=False, default=False)

    # ── Label / Print ─────────────────────────────────────────
    printed_count       = Column(Integer, nullable=False, default=0)   # times label was printed

    # ── Ownership ─────────────────────────────────────────────
    assigned_to_id      = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True)
    created_by_id       = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)

    # ── Misc ──────────────────────────────────────────────────
    notes               = Column(Text, nullable=True)
    is_active           = Column(Boolean, default=True, nullable=False)

    # ── Timestamps ────────────────────────────────────────────
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), onupdate=func.now())

    # ── Relationships ──────────────────────────────────────────
    items               = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments            = relationship("OrderPayment", back_populates="order", cascade="all, delete-orphan")
    status_history      = relationship("OrderStatusHistory", back_populates="order", cascade="all, delete-orphan")
    customer            = relationship("Customer", back_populates="orders", foreign_keys=[customer_id], lazy="select")

    @property
    def items_summary(self) -> str:
        if not self.items:
            return ""
        parts = []
        for item in self.items[:3]:
            parts.append(f"{item.product_name} x{item.quantity}")
        if len(self.items) > 3:
            parts.append(f"+{len(self.items)-3} more")
        return ", ".join(parts)

    @property
    def customer_name(self) -> str:
        if self.customer:
            return self.customer.name
        return self.delivery_name or ""

    @property
    def customer_phone(self) -> str:
        """Primary phone: from linked Customer record, or fallback to delivery_phone2."""
        if self.customer and self.customer.phone:
            return self.customer.phone
        return self.delivery_phone2 or ""

    # ── Indexes + Constraints ──────────────────────────────────
    __table_args__ = (
        UniqueConstraint("tenant_id", "order_number", name="uq_order_number_tenant"),
        Index("ix_orders_tenant_id",       "tenant_id"),
        Index("ix_orders_customer_id",     "customer_id"),
        Index("ix_orders_status",          "status"),
        Index("ix_orders_payment_status",  "payment_status"),
        Index("ix_orders_created_at",      "created_at"),
        Index("ix_orders_expected_delivery", "expected_delivery"),
        Index("ix_orders_lead_id",         "lead_id"),
    )


# ─────────────────────────────────────────────────────────────
# Courier Configuration (tenant-managed)
# ─────────────────────────────────────────────────────────────

class Courier(Base):
    __tablename__ = "couriers"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id   = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name        = Column(String(100), nullable=False)
    code        = Column(String(50), nullable=False)   # INDIA_POST, BLUEDART, DELHIVERY, etc.
    is_active   = Column(Boolean, nullable=False, default=True)
    is_default  = Column(Boolean, nullable=False, default=False)
    notes       = Column(Text, nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_courier_code_tenant"),
        Index("ix_couriers_tenant_id", "tenant_id"),
    )


# ─────────────────────────────────────────────────────────────
# India Post Customer IDs (tenant-managed, multiple per tenant)
# ─────────────────────────────────────────────────────────────

class IndiaPostCustomerId(Base):
    __tablename__ = "india_post_customer_ids"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id   = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    customer_id = Column(String(50), nullable=False)   # post-office issued code
    label       = Column(String(100), nullable=True)   # e.g. "Mumbai - Speed Post"
    is_default  = Column(Boolean, nullable=False, default=False)
    is_active   = Column(Boolean, nullable=False, default=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "customer_id", name="uq_ip_customer_id_tenant"),
        Index("ix_india_post_cids_tenant_id", "tenant_id"),
    )


# ─────────────────────────────────────────────────────────────
# Order Line Items
# ─────────────────────────────────────────────────────────────

class OrderItem(Base):
    __tablename__ = "order_items"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id       = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    order_id        = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)

    product_name    = Column(String(255), nullable=False)
    sku             = Column(String(100), nullable=True)      # optional product code
    quantity        = Column(Numeric(10, 3), nullable=False)  # supports fractional (e.g. 2.5 kg)
    unit            = Column(Enum(OrderItemUnit), nullable=False, default=OrderItemUnit.piece)
    unit_price      = Column(Numeric(12, 2), nullable=False)
    discount_pct    = Column(Numeric(5, 2), nullable=False, default=0)  # per-item discount %
    line_total      = Column(Numeric(12, 2), nullable=False)  # qty * unit_price * (1 - discount)

    notes           = Column(Text, nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    # ── Relationships ──────────────────────────────────────────
    order           = relationship("Order", back_populates="items")


# ─────────────────────────────────────────────────────────────
# Order Payments (supports partial payments)
# ─────────────────────────────────────────────────────────────

class OrderPayment(Base):
    __tablename__ = "order_payments"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id       = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    order_id        = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    employee_id     = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)

    amount          = Column(Numeric(12, 2), nullable=False)
    method          = Column(Enum(PaymentMethod), nullable=False)
    reference       = Column(String(200), nullable=True)    # UPI txn ID, cheque no., etc.
    note            = Column(Text, nullable=True)

    paid_at         = Column(DateTime(timezone=True), server_default=func.now())

    # ── Relationships ──────────────────────────────────────────
    order           = relationship("Order", back_populates="payments")


# ─────────────────────────────────────────────────────────────
# Order Status History (full audit trail)
# ─────────────────────────────────────────────────────────────

class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id       = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    order_id        = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    employee_id     = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)

    old_status      = Column(Enum(OrderStatus), nullable=True)
    new_status      = Column(Enum(OrderStatus), nullable=False)
    note            = Column(Text, nullable=True)

    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    # ── Relationships ──────────────────────────────────────────
    order           = relationship("Order", back_populates="status_history")
