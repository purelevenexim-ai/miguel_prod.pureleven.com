"""
Inventory Model
----------------
Movement-based stock engine.

All stock changes are recorded as movements.
Current stock = SUM(quantity_change) per product per tenant.

inventory_summary is a cache table updated on every movement.
It is NEVER updated directly by application code —
only through the inventory service helpers.
"""

import enum
import uuid
from sqlalchemy import (
    Column, String, Text, DateTime,
    Enum, ForeignKey, Numeric, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class MovementType(str, enum.Enum):
    purchase    = "purchase"      # PO received → stock in
    sale        = "sale"          # Order confirmed/shipped → stock out
    adjustment  = "adjustment"    # Manual correction (positive or negative)
    return_in   = "return_in"     # Customer return → stock in
    return_out  = "return_out"    # Return to vendor → stock out
    opening     = "opening"       # Initial opening stock entry


class InventoryMovement(Base):
    """
    Immutable ledger of all stock changes.
    quantity_change > 0 = stock in, < 0 = stock out.
    Never update or delete rows — only append.
    """
    __tablename__ = "inventory_movements"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id       = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    product_id      = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)

    movement_type   = Column(Enum(MovementType), nullable=False)
    quantity_change = Column(Numeric(12, 3), nullable=False)  # + or -

    # ── Reference (nullable — manual adjustments have no ref) ─
    reference_id    = Column(UUID(as_uuid=True), nullable=True)  # PO id or Order id
    reference_type  = Column(String(30), nullable=True)          # "purchase_order" | "order"

    note            = Column(Text, nullable=True)
    created_by_id   = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    # ── Relationships ─────────────────────────────────────────
    product         = relationship("Product", foreign_keys=[product_id])

    __table_args__ = (
        Index("ix_inventory_movements_tenant_product", "tenant_id", "product_id"),
        Index("ix_inventory_movements_type",           "movement_type"),
        Index("ix_inventory_movements_reference_id",   "reference_id"),
        Index("ix_inventory_movements_created_at",     "created_at"),
    )


class InventorySummary(Base):
    """
    Cached current stock per product per tenant.
    Updated atomically whenever a movement is recorded.
    READ this for fast stock checks.
    WRITE only through inventory service, never directly.
    """
    __tablename__ = "inventory_summary"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id       = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    product_id      = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)

    current_stock   = Column(Numeric(14, 3), nullable=False, default=0)
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # ── Relationships ─────────────────────────────────────────
    product         = relationship("Product", foreign_keys=[product_id])

    __table_args__ = (
        UniqueConstraint("tenant_id", "product_id", name="uq_inventory_summary_product"),
        Index("ix_inventory_summary_tenant_id", "tenant_id"),
    )
