import uuid
from sqlalchemy import (
    Column, String, Boolean, JSON, DateTime, ForeignKey, Numeric, Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


# ─────────────────────────────────────────────────────────────
#  SHOPIFY STORES
# ─────────────────────────────────────────────────────────────

class ShopifyStore(Base):
    __tablename__ = "shopify_stores"
    # store_url must be unique PER TENANT (same store can't be added twice by same tenant,
    # but different tenants can have the same store URL — multi-tenant safe)
    __table_args__ = (
        UniqueConstraint("tenant_id", "store_url", name="uq_shopify_stores_tenant_url"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    # Identity
    store_name = Column(String(255), nullable=False)
    store_url  = Column(String(255), nullable=False)   # e.g. purelevenexim.myshopify.com  (NOT globally unique)
    is_primary = Column(Boolean, default=False, nullable=False)

    # Credentials — stored encrypted via CredentialService
    api_access_token  = Column(Text, nullable=False)   # shpat_…
    api_client_id     = Column(String(255), nullable=True)
    api_client_secret = Column(Text, nullable=True)    # shpss_…

    # Config
    api_version    = Column(String(20), default="2024-01")
    webhook_secret = Column(Text, nullable=True)
    webhook_topics = Column(JSON, nullable=True)

    # Status
    is_active            = Column(Boolean, default=True, nullable=False)
    is_connected         = Column(Boolean, default=False, nullable=False)
    last_connection_test = Column(DateTime(timezone=True), nullable=True)
    last_sync            = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", backref="shopify_stores")


# ─────────────────────────────────────────────────────────────
#  DELIVERY PARTNERS
# ─────────────────────────────────────────────────────────────

class DeliveryPartner(Base):
    __tablename__ = "delivery_partners"

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    # Identity
    partner_type = Column(String(50),  nullable=False)   # delhivery | bluedart | dtdc | india_post | amazon
    display_name = Column(String(255), nullable=False)
    is_primary   = Column(Boolean, default=False, nullable=False)

    # Credentials — encrypted
    api_key    = Column(Text, nullable=True)   # Optional - can be left blank if not needed
    api_secret = Column(Text, nullable=True)
    client_name = Column(String(255), nullable=True)   # purelevenexim
    client_id   = Column(String(255), nullable=True)
    
    # Customer IDs for different service types (for India Post Parcel, etc.)
    # Format: [{"id": "12345", "name": "Indian Post Parcel"}, {"id": "67890", "name": "Indian Post Prepaid"}]
    customer_ids = Column(JSON, nullable=True, default=list)

    # API endpoints
    api_base_url = Column(String(255), nullable=True)
    api_version  = Column(String(20),  nullable=True)

    # Pickup / warehouse
    pickup_location_code = Column(String(100), nullable=True)   # 685561
    warehouse_name       = Column(String(255), nullable=True)
    warehouse_address    = Column(Text, nullable=True)
    warehouse_phone      = Column(String(20), nullable=True)

    # Supported shipment modes
    supported_shipment_types = Column(JSON, nullable=True)    # ["surface","express"]
    default_shipment_type    = Column(String(50), default="surface")

    # Status
    is_active            = Column(Boolean, default=True,  nullable=False)
    is_connected         = Column(Boolean, default=False, nullable=False)
    last_connection_test = Column(DateTime(timezone=True), nullable=True)

    # Pricing (optional)
    base_charge          = Column(Numeric(10, 2), nullable=True)
    weight_rate_per_kg   = Column(Numeric(10, 2), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", backref="delivery_partners")


# ─────────────────────────────────────────────────────────────
#  NOTIFICATION CHANNELS
# ─────────────────────────────────────────────────────────────

class NotificationChannel(Base):
    __tablename__ = "notification_channels"

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    # Type / provider
    channel_type = Column(String(50), nullable=False)   # whatsapp | sms | email
    provider     = Column(String(50), nullable=True)    # meta | twilio | sendgrid
    is_primary   = Column(Boolean, default=False, nullable=False)

    # Credentials — encrypted
    api_key      = Column(Text, nullable=False)
    api_secret   = Column(Text, nullable=True)
    access_token = Column(Text, nullable=True)

    # WhatsApp-specific
    phone_number        = Column(String(25), nullable=True)
    business_account_id = Column(String(255), nullable=True)
    phone_number_id     = Column(String(255), nullable=True)

    # Email-specific
    sender_email = Column(String(255), nullable=True)

    # Status
    is_active            = Column(Boolean, default=True,  nullable=False)
    is_connected         = Column(Boolean, default=False, nullable=False)
    last_connection_test = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", backref="notification_channels")


# ─────────────────────────────────────────────────────────────
#  SHIPPING BUSINESS RULES  (one row per tenant)
# ─────────────────────────────────────────────────────────────

class ShippingBusinessRules(Base):
    __tablename__ = "shipping_business_rules"

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, unique=True)

    # Order value controls
    max_order_value = Column(Numeric(15, 2), default=50000)
    max_cod_amount  = Column(Numeric(15, 2), default=10000)

    # RTO thresholds (percentage)
    high_rto_threshold   = Column(Numeric(5, 2), default=15.0)
    medium_rto_threshold = Column(Numeric(5, 2), default=8.0)

    # Auto-blacklisting
    auto_blacklist_rto_count   = Column(String(10), default="5")
    auto_blacklist_ndr_count   = Column(String(10), default="5")
    auto_blacklist_fraud_score = Column(Numeric(5, 2), default=80.0)
    blacklist_duration_days    = Column(String(10), nullable=True)

    # COD management
    require_cod_confirmation          = Column(Boolean, default=True)
    cod_confirmation_timeout_minutes  = Column(String(10), default="30")
    auto_create_reattempt_on_ndr      = Column(Boolean, default=False)
    max_ndr_reattempts                = Column(String(5), default="2")

    # Shipment creation policy
    auto_create_on_order_created     = Column(Boolean, default=True)
    auto_create_on_payment_confirmed = Column(Boolean, default=False)
    require_manual_approval          = Column(Boolean, default=False)

    # Tracking sync
    tracking_sync_interval_minutes = Column(String(5), default="15")

    # Customer notifications
    send_delivery_confirmation = Column(Boolean, default=True)
    send_rto_alerts            = Column(Boolean, default=True)
    send_ndr_alerts            = Column(Boolean, default=True)
    notify_via_whatsapp        = Column(Boolean, default=True)
    notify_via_sms             = Column(Boolean, default=False)
    notify_via_email           = Column(Boolean, default=False)

    # Admin alerts
    admin_alert_on_rto             = Column(Boolean, default=True)
    admin_alert_on_ndr             = Column(Boolean, default=True)
    admin_alert_on_high_value_order = Column(Boolean, default=True)
    admin_emails                   = Column(JSON, nullable=True)   # ["admin@example.com"]

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", backref="shipping_business_rules")
