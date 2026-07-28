import enum
import uuid
from sqlalchemy import (
    Column, String, Boolean, Text, Date, DateTime,
    Enum, ForeignKey, Integer, Numeric, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


# ─────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────

class LeadPipelineStatus(str, enum.Enum):
    # ────────────────────────────────────────────────────────────
    # REDESIGN PHASE 3: Simplified, user-defined workflow
    # ────────────────────────────────────────────────────────────
    created       = "created"        # Always at top: manual entry or unconfirmed order
    new_lead      = "new_lead"       # Fresh leads from WhatsApp API, abandoned carts, marketing
    contacted     = "contacted"      # Staff reached out (mandatory note popup with 3 outcomes)
    remind_later  = "remind_later"   # Follow-up scheduled for specific date (top priority)
    success_won   = "success_won"    # Customer purchased, order finalized, moved to Customers
    lost_lead     = "lost_lead"      # Not interested (recovery campaign candidate)


class LeadPriority(str, enum.Enum):
    low    = "low"
    medium = "medium"
    high   = "high"


class LeadSource(str, enum.Enum):
    manual      = "manual"
    meta        = "meta"
    whatsapp    = "whatsapp"
    google_form = "google_form"
    website     = "website"
    shopify     = "shopify"
    referral    = "referral"
    cold_call   = "cold_call"


class LeadActivityType(str, enum.Enum):
    call             = "call"
    whatsapp         = "whatsapp"
    sms              = "sms"
    email            = "email"
    visit            = "visit"
    note             = "note"
    status_change    = "status_change"
    # REDESIGN PHASE 1: New activity types
    contacted_popup  = "contacted_popup"    # When staff marks lead as "contacted" with note
    recovery_campaign = "recovery_campaign"  # When lost lead is selected for recovery
    message_received = "message_received"    # When incoming WhatsApp/SMS message received


# ─────────────────────────────────────────────────────────────
# Lead (Core Table)
# ─────────────────────────────────────────────────────────────

class Lead(Base):
    __tablename__ = "leads"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id      = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    lead_number    = Column(String(20), nullable=False)   # LEAD-00001

    # ── Contact Info ─────────────────────────────────────────
    name           = Column(String(255), nullable=False)
    phone          = Column(String(20), nullable=False)
    alternate_phone = Column(String(20), nullable=True)
    email          = Column(String(255), nullable=True)
    company_name   = Column(String(255), nullable=True)

    # ── Address ──────────────────────────────────────────────
    city           = Column(String(100), nullable=True)
    state          = Column(String(100), nullable=True)
    country        = Column(String(100), default="India")

    # ── Classification ───────────────────────────────────────
    source         = Column(Enum(LeadSource), nullable=True, default=LeadSource.manual)
    priority       = Column(Enum(LeadPriority), nullable=False, default=LeadPriority.medium)
    status         = Column(Enum(LeadPipelineStatus), nullable=False, default=LeadPipelineStatus.new_lead)

    # ── Value ────────────────────────────────────────────────
    estimated_value = Column(Numeric(12, 2), nullable=True)   # expected deal value in INR
    product_interest = Column(String(500), nullable=True)     # what product/service they want

    # ── Ownership ────────────────────────────────────────────
    assigned_to_id    = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True)
    created_by_id     = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)

    # ── Conversion ───────────────────────────────────────────
    # If this lead was converted to a Customer, link it
    converted_customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    converted_at          = Column(DateTime(timezone=True), nullable=True)
    converted_by_id       = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True)

    # ── PHASE 5 New: Link to existing customer (for returning customers) ──
    customer_id           = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)

    # ── Follow-up ────────────────────────────────────────────
    last_contacted_at  = Column(DateTime(timezone=True), nullable=True)
    next_followup_date = Column(Date, nullable=True)
    
    # ── REDESIGN PHASE 3 ─────────────────────────────────────
    # For REMIND_LATER status: when should this lead show at top of dashboard?
    remind_later_date  = Column(Date, nullable=True)
    # Last note from CONTACTED popup (mandatory when status = contacted)
    note_last          = Column(Text, nullable=True)
    # Link to unconfirmed order (if created from order page)
    order_id           = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True)
    # Track conversion
    contacted_count    = Column(Integer, default=0, nullable=False)
    is_archived        = Column(Boolean, default=False, nullable=False)

    # ── WABIS Integration ───────────────────────────────────
    wabis_labels       = Column(JSONB, nullable=True)   # labels from WABIS webhook (merged)

    # ── Quick Categorization (Favorites, Wholesale) ─────────
    is_favorite        = Column(Boolean, default=False, nullable=False)
    is_wholesale       = Column(Boolean, default=False, nullable=False)

    # ── Misc ─────────────────────────────────────────────────
    notes              = Column(Text, nullable=True)
    is_active          = Column(Boolean, default=True, nullable=False)

    # ── Timestamps ───────────────────────────────────────────
    created_at         = Column(DateTime(timezone=True), server_default=func.now())
    updated_at         = Column(DateTime(timezone=True), onupdate=func.now())

    # ── Relationships ─────────────────────────────────────────
    activities         = relationship("LeadActivity", back_populates="lead", cascade="all, delete-orphan")
    messages           = relationship("LeadMessage", back_populates="lead", cascade="all, delete-orphan")

    # ── Indexes + Constraints ─────────────────────────────────
    __table_args__ = (
        UniqueConstraint("tenant_id", "lead_number", name="uq_lead_number_tenant"),
        Index("ix_leads_tenant_id",             "tenant_id"),
        Index("ix_leads_phone",                 "phone"),
        Index("ix_leads_status",                "status"),
        Index("ix_leads_priority",              "priority"),
        Index("ix_leads_assigned_to",           "assigned_to_id"),
        Index("ix_leads_next_followup",         "next_followup_date"),
        Index("ix_leads_created_at",            "created_at"),
        Index("ix_leads_converted_customer",    "converted_customer_id"),
        Index("ix_leads_remind_later_date",     "remind_later_date"),
        Index("ix_leads_is_archived",           "is_archived"),
        Index("ix_leads_order_id",              "order_id"),
        Index("ix_leads_status_remind",         "status", "remind_later_date"),
    )


# ─────────────────────────────────────────────────────────────
# Lead Activity Log (Audit Trail)
# ─────────────────────────────────────────────────────────────

class LeadActivity(Base):
    __tablename__ = "lead_activities"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id        = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    lead_id          = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False)
    employee_id      = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)

    activity_type    = Column(Enum(LeadActivityType), nullable=False)
    note             = Column(Text, nullable=True)

    # Status snapshot at time of activity
    old_status       = Column(String(50), nullable=True)
    new_status       = Column(String(50), nullable=True)

    created_at       = Column(DateTime(timezone=True), server_default=func.now())

    # ── Relationships ─────────────────────────────────────────
    lead             = relationship("Lead", back_populates="activities")

    # ── Indexes ──────────────────────────────────────────────
    __table_args__ = (
        Index("ix_lead_activities_lead_id",    "lead_id"),
        Index("ix_lead_activities_tenant_lead", "tenant_id", "lead_id"),
        Index("ix_lead_activities_created_at", "created_at"),
    )


# ─────────────────────────────────────────────────────────────
# Lead Message (WhatsApp Chat History)
# ─────────────────────────────────────────────────────────────

class LeadMessage(Base):
    __tablename__ = "lead_messages"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id           = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    lead_id             = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False)
    
    direction           = Column(String(20), nullable=False)  # 'inbound', 'outbound'
    message_body        = Column(Text, nullable=False)
    whatsapp_message_id = Column(String(100), nullable=True)  # External ID from WhatsApp API
    
    created_at          = Column(DateTime(timezone=True), server_default=func.now())

    # ── Relationships ─────────────────────────────────────────
    lead                = relationship("Lead", back_populates="messages")

    # ── Indexes ───────────────────────────────────────────────
    __table_args__ = (
        Index("ix_lead_messages_lead_id", "lead_id"),
        Index("ix_lead_messages_lead_direction", "lead_id", "direction"),
        Index("ix_lead_messages_created_at", "created_at"),
        Index("ix_lead_messages_tenant_id", "tenant_id"),
    )
