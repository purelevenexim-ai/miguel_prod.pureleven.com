import enum
import uuid
from sqlalchemy import (
    Column, String, Boolean, Text, Date, DateTime,
    Enum, ForeignKey, Integer, UniqueConstraint, Index, Numeric
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


# ─────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────

class LeadStatus(str, enum.Enum):
    new           = "new"
    called        = "called"
    interested    = "interested"
    not_interested = "not_interested"
    lead          = "lead"
    converted     = "converted"
    lost          = "lost"


class InterestStatus(str, enum.Enum):
    hot  = "hot"
    warm = "warm"
    cold = "cold"


class CustomerType(str, enum.Enum):
    retail      = "retail"
    wholesale   = "wholesale"
    distributor = "distributor"
    home_cook   = "home_cook"   # legacy
    wholesaler  = "wholesaler"  # legacy
    retailer    = "retailer"    # legacy
    mill        = "mill"        # legacy


class PaymentMode(str, enum.Enum):
    prepaid            = "prepaid"
    cod                = "cod"
    pay_after_delivery = "pay_after_delivery"


class SourceType(str, enum.Enum):
    manual      = "manual"
    meta_ads    = "meta_ads"
    whatsapp    = "whatsapp"
    google_form = "google_form"
    website     = "website"
    meta        = "meta"   # legacy


class InteractionType(str, enum.Enum):
    call      = "call"
    whatsapp  = "whatsapp"
    sms       = "sms"
    visit     = "visit"
    note      = "note"


# ─────────────────────────────────────────────────────────────
# Customer (Master Table)
# ─────────────────────────────────────────────────────────────

class Customer(Base):
    __tablename__ = "customers"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id             = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    unique_customer_code  = Column(String(20), nullable=False)

    # Basic Info
    name                  = Column(String(255), nullable=False)
    phone                 = Column(String(20), nullable=False)
    alternate_phone       = Column(String(20), nullable=True)
    email                 = Column(String(255), nullable=True)
    gstin                 = Column(String(15), nullable=True)   # GST Identification Number (B2B)
    shopify_customer_id   = Column(String(50), nullable=True)   # Shopify's own customer ID for reliable linking

    # Address
    address               = Column(Text, nullable=True)
    pincode               = Column(String(10), nullable=True)
    city                  = Column(String(100), nullable=True)
    state                 = Column(String(100), nullable=True)
    country               = Column(String(100), default="India")

    # Classification
    customer_type         = Column(Enum(CustomerType), nullable=True)
    payment_mode_preference = Column(Enum(PaymentMode), nullable=True)
    source                = Column(Enum(SourceType), nullable=True, default=SourceType.manual)

    # Lead & Interest
    lead_status           = Column(Enum(LeadStatus), nullable=False, default=LeadStatus.new)
    interest_status       = Column(Enum(InterestStatus), nullable=True)

    # Ownership
    assigned_employee_id  = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True)
    created_by_employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)

    # ── Lead Conversion Tracking ────────────────────────────
    # If this customer was converted from a lead, track the source lead
    # This allows viewing the lead's activity history from customer view
    source_lead_id        = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)

    # Follow-up
    last_contacted_at     = Column(DateTime(timezone=True), nullable=True)
    next_followup_date    = Column(Date, nullable=True)

    # Misc
    notes                 = Column(Text, nullable=True)
    is_active             = Column(Boolean, default=True, nullable=False)

    # ── Engagement Tracking (updated on order events) ────────
    first_order_date      = Column(DateTime(timezone=True), nullable=True)
    last_order_date       = Column(DateTime(timezone=True), nullable=True)
    last_seen_at          = Column(DateTime(timezone=True), nullable=True)
    total_orders          = Column(Integer, default=0, nullable=False)
    average_order_value   = Column(Numeric(12, 2), nullable=True)
    abandoned_carts       = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at            = Column(DateTime(timezone=True), server_default=func.now())
    updated_at            = Column(DateTime(timezone=True), onupdate=func.now())

    # ── Relationships ─────────────────────────────────────────
    products              = relationship("CustomerProduct", back_populates="customer", cascade="all, delete-orphan")
    interactions          = relationship("CustomerInteraction", back_populates="customer", cascade="all, delete-orphan")
    tags                  = relationship("CustomerTagMap", back_populates="customer", cascade="all, delete-orphan")
    # Back-references to orders — allows customer.orders and customer.shopify_orders
    orders                = relationship("Order", back_populates="customer", foreign_keys="[Order.customer_id]", lazy="dynamic")
    shopify_orders        = relationship("ShopifyOrder", back_populates="customer", foreign_keys="[ShopifyOrder.customer_id]", lazy="dynamic")

    # ── Indexes ───────────────────────────────────────────────
    __table_args__ = (
        UniqueConstraint("tenant_id", "unique_customer_code", name="uq_customer_code_tenant"),
        Index("ix_customers_tenant_id",        "tenant_id"),
        Index("ix_customers_phone",            "phone"),
        Index("ix_customers_tenant_phone_unique", "tenant_id", "phone"),
        Index("ix_customers_shopify_customer_id", "shopify_customer_id"),
        Index("ix_customers_lead_status",      "lead_status"),
        Index("ix_customers_interest_status",  "interest_status"),
        Index("ix_customers_next_followup",    "next_followup_date"),
        Index("ix_customers_created_at",       "created_at"),
        Index("ix_customers_city",             "city"),
    )


# ─────────────────────────────────────────────────────────────
# Customer Product Interests
# ─────────────────────────────────────────────────────────────

class CustomerProduct(Base):
    __tablename__ = "customer_products"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id            = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    customer_id          = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)

    product_name         = Column(String(255), nullable=False)
    quantity_interested  = Column(Integer, nullable=True)
    note                 = Column(Text, nullable=True)

    created_at           = Column(DateTime(timezone=True), server_default=func.now())

    # ── Relationships ─────────────────────────────────────────
    customer             = relationship("Customer", back_populates="products")


# ─────────────────────────────────────────────────────────────
# Customer Interactions (Audit Trail)
# ─────────────────────────────────────────────────────────────

class CustomerInteraction(Base):
    __tablename__ = "customer_interactions"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id            = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    customer_id          = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    employee_id          = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)

    interaction_type     = Column(Enum(InteractionType), nullable=False)
    message_content      = Column(Text, nullable=True)

    # Status snapshot at time of interaction
    old_status           = Column(Enum(LeadStatus), nullable=True)
    new_status           = Column(Enum(LeadStatus), nullable=True)

    created_at           = Column(DateTime(timezone=True), server_default=func.now())

    # ── Relationships ─────────────────────────────────────────
    customer             = relationship("Customer", back_populates="interactions")


# ─────────────────────────────────────────────────────────────
# Customer Tags
# ─────────────────────────────────────────────────────────────

class CustomerTag(Base):
    __tablename__ = "customer_tags"

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name      = Column(String(100), nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_tag_name_tenant"),
    )

    # ── Relationships ─────────────────────────────────────────
    customers = relationship("CustomerTagMap", back_populates="tag")


class CustomerTagMap(Base):
    __tablename__ = "customer_tag_map"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id   = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    tag_id      = Column(UUID(as_uuid=True), ForeignKey("customer_tags.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint("customer_id", "tag_id", name="uq_customer_tag"),
    )

    # ── Relationships ─────────────────────────────────────────
    customer = relationship("Customer", back_populates="tags")
    tag      = relationship("CustomerTag", back_populates="customers")
