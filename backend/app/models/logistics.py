"""
Logistics Intelligence Models — Phase 2
Risk Engine, Customer Scoring, Blacklist, COD Transactions, NDR Handling
"""
import enum
import uuid
from sqlalchemy import (
    Column, String, Boolean, Text, Date, DateTime, Integer, Numeric,
    Enum, ForeignKey, UniqueConstraint, Index, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


# ─────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────

class RiskLevel(str, enum.Enum):
    low    = "low"       # Safe, proceed
    medium = "medium"    # Caution, may need review
    high   = "high"      # High risk, review or block
    blocked = "blocked"  # Hard blocked


class NdrReason(str, enum.Enum):
    not_at_home         = "not_at_home"
    refused             = "refused"
    address_incorrect   = "address_incorrect"
    unreachable         = "unreachable"
    out_of_delivery_area = "out_of_delivery_area"
    fake_attempt        = "fake_attempt"
    customer_not_found  = "customer_not_found"
    other               = "other"


class NdrStatus(str, enum.Enum):
    pending         = "pending"       # NDR raised, action needed
    reattempt       = "reattempt"     # Reattempt scheduled
    reattempted     = "reattempted"   # Reattempt was done
    rto_initiated   = "rto_initiated" # Return to origin started
    rto_delivered   = "rto_delivered" # Returned to warehouse
    resolved        = "resolved"      # Delivered on reattempt


class CodConfirmStatus(str, enum.Enum):
    pending    = "pending"     # Awaiting confirmation
    confirmed  = "confirmed"   # Customer confirmed
    rejected   = "rejected"    # Customer rejected
    timeout    = "timeout"     # No response in time
    skipped    = "skipped"     # Confirmation not required


# ─────────────────────────────────────────────────────────────
# RTO Zones — Pincode Risk Scoring
# ─────────────────────────────────────────────────────────────

class RtoZone(Base):
    """
    Pincode-level RTO risk data.
    Updated periodically from delivery data.
    Used to score incoming orders.
    """
    __tablename__ = "rto_zones"

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    pincode       = Column(String(10), nullable=False)
    city          = Column(String(100), nullable=True)
    state         = Column(String(100), nullable=True)
    delivery_zone = Column(String(10), nullable=True)   # A/B/C/D (Delhivery zones)

    # Risk metrics
    total_shipments  = Column(Integer, default=0, nullable=False)
    rto_count        = Column(Integer, default=0, nullable=False)
    ndr_count        = Column(Integer, default=0, nullable=False)
    delivered_count  = Column(Integer, default=0, nullable=False)

    # Calculated risk
    rto_percentage   = Column(Numeric(5, 2), default=0.0, nullable=False)
    risk_level       = Column(Enum(RiskLevel), default=RiskLevel.low, nullable=False)
    risk_score       = Column(Numeric(5, 2), default=0.0, nullable=False)  # 0-100

    # Metadata
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "pincode", name="uq_rto_zone_pincode_tenant"),
        Index("ix_rto_zones_tenant_id", "tenant_id"),
        Index("ix_rto_zones_pincode", "pincode"),
        Index("ix_rto_zones_risk_level", "risk_level"),
    )


# ─────────────────────────────────────────────────────────────
# Customer Delivery Scores — Behavioral Tracking
# ─────────────────────────────────────────────────────────────

class CustomerDeliveryScore(Base):
    """
    Per-customer delivery history and risk scoring.
    Updated after every delivery outcome.
    """
    __tablename__ = "customer_delivery_scores"

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    # Customer identifiers (from Shopify order)
    customer_phone = Column(String(20), nullable=False)
    customer_email = Column(String(255), nullable=True)
    customer_name  = Column(String(255), nullable=True)

    # Delivery history counters
    total_orders      = Column(Integer, default=0, nullable=False)
    delivered_orders  = Column(Integer, default=0, nullable=False)
    rto_orders        = Column(Integer, default=0, nullable=False)
    ndr_orders        = Column(Integer, default=0, nullable=False)
    cancelled_orders  = Column(Integer, default=0, nullable=False)

    # COD specific
    cod_orders         = Column(Integer, default=0, nullable=False)
    cod_confirmed      = Column(Integer, default=0, nullable=False)
    cod_rejected       = Column(Integer, default=0, nullable=False)
    cod_timeout        = Column(Integer, default=0, nullable=False)

    # Calculated score (0–100, higher = safer)
    delivery_score = Column(Numeric(5, 2), default=50.0, nullable=False)
    risk_level     = Column(Enum(RiskLevel), default=RiskLevel.low, nullable=False)

    last_order_at  = Column(DateTime(timezone=True), nullable=True)
    last_updated   = Column(DateTime(timezone=True), server_default=func.now())
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "customer_phone", name="uq_customer_score_phone"),
        Index("ix_customer_scores_tenant_id", "tenant_id"),
        Index("ix_customer_scores_phone", "customer_phone"),
        Index("ix_customer_scores_risk_level", "risk_level"),
    )


# ─────────────────────────────────────────────────────────────
# Blacklisted Customers
# ─────────────────────────────────────────────────────────────

class BlacklistedCustomer(Base):
    """
    Customers blocked from placing orders.
    Can be manual (by admin) or auto (by risk engine).
    """
    __tablename__ = "blacklisted_customers"

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    # Identifiers
    customer_phone = Column(String(20), nullable=False)
    customer_email = Column(String(255), nullable=True)
    customer_name  = Column(String(255), nullable=True)

    # Reason
    reason         = Column(Text, nullable=False)   # Human-readable reason
    blacklist_type = Column(String(20), default="manual", nullable=False)  # manual | auto

    # Duration
    is_permanent    = Column(Boolean, default=False, nullable=False)
    expires_at      = Column(DateTime(timezone=True), nullable=True)  # null = permanent
    is_active       = Column(Boolean, default=True, nullable=False)

    # Who blocked
    blocked_by      = Column(String(255), nullable=True)   # admin email or "system"

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("ix_blacklist_tenant_id", "tenant_id"),
        Index("ix_blacklist_phone", "customer_phone"),
        Index("ix_blacklist_active", "is_active"),
    )


# ─────────────────────────────────────────────────────────────
# COD Transactions — Confirmation Workflow
# ─────────────────────────────────────────────────────────────

class CodTransaction(Base):
    """
    COD (Cash on Delivery) confirmation tracking.
    Sends WhatsApp/SMS before creating shipment.
    Customer must confirm via reply.
    """
    __tablename__ = "cod_transactions"

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    shopify_order_id = Column(UUID(as_uuid=True), ForeignKey("shopify_orders.id"), nullable=False)

    # COD details
    amount         = Column(Numeric(12, 2), nullable=False)
    currency       = Column(String(10), default="INR", nullable=False)
    customer_phone = Column(String(20), nullable=False)
    customer_name  = Column(String(255), nullable=True)

    # Confirmation status
    status            = Column(Enum(CodConfirmStatus), default=CodConfirmStatus.pending, nullable=False)
    confirmation_code = Column(String(20), nullable=True)   # OTP or confirmation phrase
    confirmed_at      = Column(DateTime(timezone=True), nullable=True)
    rejected_at       = Column(DateTime(timezone=True), nullable=True)
    expires_at        = Column(DateTime(timezone=True), nullable=True)  # Timeout

    # Notification tracking
    whatsapp_message_id = Column(String(255), nullable=True)
    sms_message_id      = Column(String(255), nullable=True)
    sent_at             = Column(DateTime(timezone=True), nullable=True)
    reminder_sent_at    = Column(DateTime(timezone=True), nullable=True)
    reminder_count      = Column(Integer, default=0, nullable=False)

    # Raw response
    response_data = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("ix_cod_transactions_tenant_id", "tenant_id"),
        Index("ix_cod_transactions_order_id", "shopify_order_id"),
        Index("ix_cod_transactions_status", "status"),
    )


# ─────────────────────────────────────────────────────────────
# NDR (Non-Delivery Report) Records
# ─────────────────────────────────────────────────────────────

class NdrRecord(Base):
    """
    Non-Delivery Report events from couriers.
    Tracks failed delivery attempts and resolution actions.
    """
    __tablename__ = "ndr_records"

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    shopify_order_id = Column(UUID(as_uuid=True), ForeignKey("shopify_orders.id"), nullable=False)

    # Shipment info
    tracking_number  = Column(String(100), nullable=False)
    courier_name     = Column(String(100), nullable=False)

    # NDR details
    ndr_date        = Column(DateTime(timezone=True), nullable=False)
    reason          = Column(Enum(NdrReason), default=NdrReason.other, nullable=False)
    reason_detail   = Column(Text, nullable=True)   # Courier's raw reason text
    attempt_number  = Column(Integer, default=1, nullable=False)

    # Action taken
    status          = Column(Enum(NdrStatus), default=NdrStatus.pending, nullable=False)
    action_taken    = Column(String(100), nullable=True)   # "reattempt" | "rto" | "resolved"
    action_date     = Column(DateTime(timezone=True), nullable=True)
    resolution_note = Column(Text, nullable=True)

    # Customer contact
    customer_phone    = Column(String(20), nullable=True)
    customer_notified = Column(Boolean, default=False, nullable=False)
    notified_at       = Column(DateTime(timezone=True), nullable=True)

    # Raw courier data
    raw_ndr_data = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("ix_ndr_records_tenant_id", "tenant_id"),
        Index("ix_ndr_records_order_id", "shopify_order_id"),
        Index("ix_ndr_records_status", "status"),
        Index("ix_ndr_records_tracking", "tracking_number"),
    )


# ─────────────────────────────────────────────────────────────
# Notification Logs — All outbound messages
# ─────────────────────────────────────────────────────────────

class NotificationLog(Base):
    """
    Audit trail of all outbound notifications (WhatsApp, SMS, Email).
    Used for debugging and reporting.
    """
    __tablename__ = "notification_logs"

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    shopify_order_id = Column(UUID(as_uuid=True), ForeignKey("shopify_orders.id"), nullable=True)

    # Channel
    channel      = Column(String(20), nullable=False)   # whatsapp | sms | email
    recipient    = Column(String(255), nullable=False)  # phone or email
    message_type = Column(String(50), nullable=False)   # order_created | tracking_update | cod_confirmation | ndr_alert

    # Content
    message_body  = Column(Text, nullable=True)
    template_name = Column(String(100), nullable=True)

    # Delivery status
    status        = Column(String(20), default="pending", nullable=False)   # pending | sent | delivered | failed
    provider_id   = Column(String(255), nullable=True)   # Message ID from provider
    sent_at       = Column(DateTime(timezone=True), nullable=True)
    delivered_at  = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    # Raw response
    provider_response = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_notification_logs_tenant_id", "tenant_id"),
        Index("ix_notification_logs_order_id", "shopify_order_id"),
        Index("ix_notification_logs_status", "status"),
        Index("ix_notification_logs_channel", "channel"),
    )


# ─────────────────────────────────────────────────────────────
# Order Risk Assessment — Snapshot per order
# ─────────────────────────────────────────────────────────────

class OrderRiskAssessment(Base):
    """
    Risk assessment snapshot for each Shopify order.
    Computed at order creation time.
    Used to decide: auto-approve | review | block
    """
    __tablename__ = "order_risk_assessments"

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    shopify_order_id = Column(UUID(as_uuid=True), ForeignKey("shopify_orders.id"), nullable=False, unique=True)

    # Overall risk
    overall_risk_level = Column(Enum(RiskLevel), default=RiskLevel.low, nullable=False)
    overall_risk_score = Column(Numeric(5, 2), default=0.0, nullable=False)  # 0-100
    decision           = Column(String(20), default="approve", nullable=False)  # approve | review | block

    # Component scores
    customer_risk_score  = Column(Numeric(5, 2), default=0.0)  # Based on history
    pincode_risk_score   = Column(Numeric(5, 2), default=0.0)  # Based on RTO zone
    order_value_score    = Column(Numeric(5, 2), default=0.0)  # Based on amount
    cod_risk_score       = Column(Numeric(5, 2), default=0.0)  # COD-specific risk

    # Risk flags (individual triggers)
    is_customer_blacklisted = Column(Boolean, default=False)
    is_high_rto_zone        = Column(Boolean, default=False)
    is_high_value_order     = Column(Boolean, default=False)
    is_cod_order            = Column(Boolean, default=False)
    is_new_customer         = Column(Boolean, default=False)
    has_multiple_rto        = Column(Boolean, default=False)
    has_cod_rejections      = Column(Boolean, default=False)

    # Reason explanation
    risk_reasons = Column(JSON, nullable=True)   # ["High RTO pincode", "First-time buyer", ...]

    # Who reviewed (if manual review)
    reviewed_by   = Column(String(255), nullable=True)
    reviewed_at   = Column(DateTime(timezone=True), nullable=True)
    review_note   = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("ix_risk_assessments_tenant_id", "tenant_id"),
        Index("ix_risk_assessments_order_id", "shopify_order_id"),
        Index("ix_risk_assessments_decision", "decision"),
        Index("ix_risk_assessments_risk_level", "overall_risk_level"),
    )
