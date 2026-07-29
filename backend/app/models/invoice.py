"""
GST Invoice Model
------------------
Tax-compliant invoice engine.

Invoices are SEPARATE from orders:
  - Not every order is an invoice (drafts, proformas)
  - Invoices are immutable once finalized
  - GST split: CGST+SGST (intra-state) or IGST (inter-state)
  - Invoice numbers reset per financial year (April–March)

invoice_counters: per-tenant per-FY sequential number store.
"""

import enum
import uuid
from sqlalchemy import (
    Column, String, Text, Date, DateTime,
    Enum, ForeignKey, Numeric, Integer, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class InvoiceStatus(str, enum.Enum):
    draft       = "draft"        # editable
    finalized   = "finalized"    # locked — immutable
    cancelled   = "cancelled"    # void (credit note issued separately)


class Invoice(Base):
    __tablename__ = "invoices"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id           = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    # ── Numbering ────────────────────────────────────────────
    invoice_number      = Column(String(30), nullable=False)   # INV-2025-00001
    financial_year      = Column(String(10), nullable=False)   # "2025-26"
    invoice_date        = Column(Date, nullable=False)

    # ── Links ────────────────────────────────────────────────
    order_id            = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True)
    customer_id         = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)

    # ── Addresses ────────────────────────────────────────────
    billing_address     = Column(Text, nullable=True)
    shipping_address    = Column(Text, nullable=True)

    # ── Customer GST (for B2B) ────────────────────────────────
    customer_gst        = Column(String(20), nullable=True)
    customer_state      = Column(String(100), nullable=True)
    supply_state        = Column(String(100), nullable=True)  # tenant's state for GST split logic

    # ── Amounts ──────────────────────────────────────────────
    total_taxable       = Column(Numeric(14, 2), nullable=False, default=0)  # sum of taxable line totals
    cgst_amount         = Column(Numeric(14, 2), nullable=False, default=0)
    sgst_amount         = Column(Numeric(14, 2), nullable=False, default=0)
    igst_amount         = Column(Numeric(14, 2), nullable=False, default=0)
    total_tax           = Column(Numeric(14, 2), nullable=False, default=0)  # cgst+sgst or igst
    grand_total         = Column(Numeric(14, 2), nullable=False, default=0)  # taxable + total_tax

    # ── Status ───────────────────────────────────────────────
    status              = Column(
        Enum(InvoiceStatus),
        nullable=False,
        default=InvoiceStatus.draft,
    )

    # ── Misc ─────────────────────────────────────────────────
    notes               = Column(Text, nullable=True)
    created_by_id       = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), onupdate=func.now())

    # ── Relationships ─────────────────────────────────────────
    items               = relationship(
        "InvoiceItem",
        back_populates="invoice",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "invoice_number", name="uq_invoice_number_tenant"),
        Index("ix_invoices_tenant_id",       "tenant_id"),
        Index("ix_invoices_customer_id",     "customer_id"),
        Index("ix_invoices_order_id",        "order_id"),
        Index("ix_invoices_invoice_date",    "invoice_date"),
        Index("ix_invoices_financial_year",  "financial_year"),
        Index("ix_invoices_status",          "status"),
    )


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id       = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    invoice_id      = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False)

    # ── Product Info (snapshotted at invoice time — immutable) ─
    product_id      = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    product_name    = Column(String(255), nullable=False)   # snapshot
    hsn_code        = Column(String(20), nullable=True)     # HSN/SAC code

    # ── Quantity & Price ──────────────────────────────────────
    quantity        = Column(Numeric(12, 3), nullable=False)
    unit_price      = Column(Numeric(12, 2), nullable=False)
    taxable_amount  = Column(Numeric(14, 2), nullable=False)  # qty * unit_price

    # ── GST (stored per item — frozen at finalization) ────────
    tax_percent     = Column(Numeric(5, 2), nullable=False, default=0)
    cgst_percent    = Column(Numeric(5, 2), nullable=False, default=0)
    sgst_percent    = Column(Numeric(5, 2), nullable=False, default=0)
    igst_percent    = Column(Numeric(5, 2), nullable=False, default=0)
    cgst_amount     = Column(Numeric(12, 2), nullable=False, default=0)
    sgst_amount     = Column(Numeric(12, 2), nullable=False, default=0)
    igst_amount     = Column(Numeric(12, 2), nullable=False, default=0)
    tax_amount      = Column(Numeric(12, 2), nullable=False, default=0)  # total GST on line
    line_total      = Column(Numeric(14, 2), nullable=False)             # taxable + tax

    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    # ── Relationships ─────────────────────────────────────────
    invoice         = relationship("Invoice", back_populates="items")
    product         = relationship("Product", foreign_keys=[product_id])


class InvoiceCounter(Base):
    """
    Per-tenant per-financial-year invoice sequence.
    Atomic increment ensures no gaps or duplicates.
    Financial year format: "2025-26" (April–March cycle).
    """
    __tablename__ = "invoice_counters"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id       = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    financial_year  = Column(String(10), nullable=False)   # "2025-26"
    last_number     = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("tenant_id", "financial_year", name="uq_invoice_counter_tenant_fy"),
    )
