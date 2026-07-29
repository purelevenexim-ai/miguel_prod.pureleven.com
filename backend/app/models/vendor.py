"""
Vendor Model
-------------
Suppliers from whom the tenant purchases goods.
Foundational for Purchase Orders → Inventory flow.
"""

import uuid
from sqlalchemy import (
    Column, String, Boolean, Text, DateTime, Integer, SmallInteger,
    ForeignKey, Numeric, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class Vendor(Base):
    __tablename__ = "vendors"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id       = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    vendor_code     = Column(String(20), nullable=False)   # VEND-00001

    # ── Identity ─────────────────────────────────────────────
    company_name    = Column(String(255), nullable=False)
    contact_person  = Column(String(255), nullable=True)
    phone           = Column(String(20), nullable=True)
    email           = Column(String(255), nullable=True)

    # ── Address ──────────────────────────────────────────────
    address         = Column(Text, nullable=True)
    city            = Column(String(100), nullable=True)
    state           = Column(String(100), nullable=True)
    pincode         = Column(String(10), nullable=True)

    # ── Tax Identity ─────────────────────────────────────────
    gst_number      = Column(String(20), nullable=True)
    pan_number      = Column(String(15), nullable=True)

    # ── Banking ──────────────────────────────────────────────
    bank_account_name   = Column(String(255), nullable=True)
    bank_account_number = Column(String(30), nullable=True)
    ifsc_code           = Column(String(15), nullable=True)

    # ── Status ───────────────────────────────────────────────
    is_active       = Column(Boolean, nullable=False, default=True)
    is_preferred    = Column(Boolean, nullable=False, default=False)

    # ── Extra Contact ─────────────────────────────────────────
    phone2          = Column(String(20), nullable=True)
    whatsapp        = Column(String(20), nullable=True)

    # ── Business Profile ──────────────────────────────────────
    vendor_type          = Column(String(50), nullable=True)    # Trader / Mill / Farmer / Distributor / Manufacturer / Agent
    avg_lead_days        = Column(Integer, nullable=True)        # avg delivery lead time in days
    payment_terms_days   = Column(Integer, nullable=True)        # e.g. 30 = Net-30 credit days
    credit_limit         = Column(Numeric(14, 2), nullable=True) # max outstanding credit allowed
    vendor_rating        = Column(SmallInteger(), nullable=True)     # 1–5 star rating
    notes                = Column(Text, nullable=True)

    # ── Timestamps ───────────────────────────────────────────
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    # ── Relationships ─────────────────────────────────────────
    vendor_products = relationship(
        "VendorProduct",
        back_populates="vendor",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "vendor_code", name="uq_vendor_code_tenant"),
        Index("ix_vendors_tenant_id",    "tenant_id"),
        Index("ix_vendors_company_name", "company_name"),
        Index("ix_vendors_gst_number",   "gst_number"),
    )


class VendorProduct(Base):
    """
    Vendor Product Pricing Catalog.
    Tracks what each vendor sells, at what price, with logistics details.
    """
    __tablename__ = "vendor_products"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id       = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    vendor_id       = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False)
    product_id      = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)

    # ── Pricing ───────────────────────────────────────────────
    unit_price         = Column(Numeric(12, 2), nullable=False)
    gst_percent        = Column(Numeric(5, 2),  nullable=False, default=0)
    transport_charge   = Column(Numeric(10, 2), nullable=True)
    transport_method   = Column(String(50),     nullable=True)   # lorry/courier/own/rail

    # ── Quantities & Lead Time ────────────────────────────────
    min_order_qty    = Column(Numeric(12, 3), nullable=True)
    max_load_qty     = Column(Numeric(12, 3), nullable=True)
    lead_time_days   = Column(Integer,        nullable=True)

    # ── Reorder Planning ──────────────────────────────────────
    reorder_cycle_days = Column(Integer, nullable=True)   # how often to reorder (days)
    notes              = Column(Text,    nullable=True)
    is_preferred       = Column(Boolean, nullable=False, default=False)
    price_updated_at   = Column(DateTime(timezone=True), nullable=True)

    # ── Timestamps ────────────────────────────────────────────
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    # ── Relationships ─────────────────────────────────────────
    vendor  = relationship("Vendor",  back_populates="vendor_products", foreign_keys=[vendor_id])
    product = relationship("Product", foreign_keys=[product_id])

    __table_args__ = (
        UniqueConstraint("vendor_id", "product_id", name="uq_vendor_product"),
        Index("ix_vendor_products_tenant_id",  "tenant_id"),
        Index("ix_vendor_products_vendor_id",  "vendor_id"),
        Index("ix_vendor_products_product_id", "product_id"),
    )
