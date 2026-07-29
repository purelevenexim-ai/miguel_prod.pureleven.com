"""
Purchase Order Model
---------------------
Tracks procurement of goods from vendors.
On "received" → triggers inventory stock-in movements.
"""

import enum
import uuid
from sqlalchemy import (
    Column, String, Text, Date, DateTime,
    Enum, ForeignKey, Numeric, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class PurchaseOrderStatus(str, enum.Enum):
    draft       = "draft"
    sent        = "sent"        # sent to vendor
    received    = "received"    # goods received → triggers stock-in
    cancelled   = "cancelled"


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id       = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    po_number       = Column(String(20), nullable=False)   # PO-00001

    # ── Vendor ───────────────────────────────────────────────
    vendor_id       = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False)

    # ── Status ───────────────────────────────────────────────
    status          = Column(
        Enum(PurchaseOrderStatus),
        nullable=False,
        default=PurchaseOrderStatus.draft,
    )

    # ── Amounts ──────────────────────────────────────────────
    total_amount    = Column(Numeric(14, 2), nullable=False, default=0)  # sum of line totals
    tax_amount      = Column(Numeric(14, 2), nullable=False, default=0)  # total GST
    grand_total     = Column(Numeric(14, 2), nullable=False, default=0)  # total_amount + tax_amount

    # ── Dates ────────────────────────────────────────────────
    expected_delivery_date = Column(Date, nullable=True)
    received_at     = Column(DateTime(timezone=True), nullable=True)

    # ── Misc ─────────────────────────────────────────────────
    notes           = Column(Text, nullable=True)

    # ── Ownership ────────────────────────────────────────────
    created_by_id   = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)

    # ── Timestamps ───────────────────────────────────────────
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    # ── Relationships ─────────────────────────────────────────
    items           = relationship(
        "PurchaseOrderItem",
        back_populates="purchase_order",
        cascade="all, delete-orphan",
    )
    vendor          = relationship("Vendor", foreign_keys=[vendor_id])

    __table_args__ = (
        UniqueConstraint("tenant_id", "po_number", name="uq_po_number_tenant"),
        Index("ix_purchase_orders_tenant_id",  "tenant_id"),
        Index("ix_purchase_orders_vendor_id",  "vendor_id"),
        Index("ix_purchase_orders_status",     "status"),
    )


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id           = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    purchase_order_id   = Column(UUID(as_uuid=True), ForeignKey("purchase_orders.id"), nullable=False)
    product_id          = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)

    quantity            = Column(Numeric(12, 3), nullable=False)  # supports fractional
    unit_cost           = Column(Numeric(12, 2), nullable=False)
    tax_percent         = Column(Numeric(5, 2), nullable=False, default=0)
    tax_amount          = Column(Numeric(12, 2), nullable=False, default=0)
    line_total          = Column(Numeric(14, 2), nullable=False)   # qty * unit_cost + tax

    created_at          = Column(DateTime(timezone=True), server_default=func.now())

    # ── Relationships ─────────────────────────────────────────
    purchase_order      = relationship("PurchaseOrder", back_populates="items")
    product             = relationship("Product", foreign_keys=[product_id])
