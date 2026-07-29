"""
Shopify Order Models - Auto-synced from Shopify store
Includes shipping tracking with Delhivery & Indian Post
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

class ShopifyOrderStatus(str, enum.Enum):
    """Shopify order statuses"""
    unconfirmed = "unconfirmed"
    confirmed = "confirmed"
    awaiting_shipment = "awaiting_shipment"
    pending_fulfillment = "pending_fulfillment"
    partially_fulfilled = "partially_fulfilled"
    fulfilled = "fulfilled"
    cancelled = "cancelled"
    returned = "returned"


class ShopifyFulfillmentStatus(str, enum.Enum):
    """Shopify fulfillment statuses — mirrors Shopify's fulfillment_status field.
    NOTE: Shopify returns null for unfulfilled orders; we store as 'unfulfilled'."""
    unfulfilled = "unfulfilled"       # null in Shopify = not yet shipped
    partial = "partial"               # partially fulfilled
    in_transit = "in_transit"
    out_for_delivery = "out_for_delivery"
    fulfilled = "fulfilled"           # fully shipped
    delivered = "delivered"
    failure = "failure"
    cancelled = "cancelled"
    # Legacy values kept for backwards compat with existing DB rows
    unconfirmed = "unconfirmed"
    confirmed = "confirmed"
    scheduled = "scheduled"
    pending = "pending"


class ShippingPartner(str, enum.Enum):
    """Shipping/Delivery partners we support"""
    delhivery = "delhivery"
    india_post = "india_post"
    bluedart = "bluedart"
    amazon = "amazon"
    manual = "manual"


class TrackingStatus(str, enum.Enum):
    """Tracking status from courier"""
    pending = "pending"           # Awaiting pickup
    picked_up = "picked_up"        # Picked up from warehouse
    in_transit = "in_transit"      # In transit
    out_for_delivery = "out_for_delivery"  # Out for delivery today
    delivered = "delivered"        # Successfully delivered
    failed = "failed"              # Delivery failed
    returned = "returned"          # Returned to sender
    cancelled = "cancelled"        # Shipment cancelled
    exception = "exception"        # Exception / Issue


# ─────────────────────────────────────────────────────────────
# Shopify Order (synced from Shopify)
# ─────────────────────────────────────────────────────────────

class ShopifyOrder(Base):
    """
    Orders synced from Shopify via webhook/API.
    Each Shopify order is linked to one Tenant's ShopifyStore.
    """
    __tablename__ = "shopify_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    shopify_store_id = Column(UUID(as_uuid=True), ForeignKey("shopify_stores.id"), nullable=False)
    
    # ── Customer Link (auto-created when tracking is assigned) ──
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)

    # ── Shopify Identity ──────────────────────────────────────
    shopify_order_id = Column(String(50), nullable=False)  # Shopify order ID (e.g., #1234567890)
    shopify_order_number = Column(String(50), nullable=False)  # Order number
    shopify_order_name = Column(String(50), nullable=False)  # Order name (e.g., #1001, #1002)
    
    # ── Shopify Status (synced) ───────────────────────────────
    shopify_status = Column(Enum(ShopifyOrderStatus), nullable=False, default=ShopifyOrderStatus.unconfirmed)
    shopify_fulfillment_status = Column(Enum(ShopifyFulfillmentStatus), nullable=False, default=ShopifyFulfillmentStatus.unfulfilled)
    shopify_financial_status = Column(String(50), nullable=True)  # authorized, pending, paid, refunded, voided, partially_refunded, partially_paid
    
    # ── Customer Info (from Shopify) ──────────────────────────
    customer_name = Column(String(255), nullable=False)
    customer_email = Column(String(255), nullable=True)
    customer_phone = Column(String(20), nullable=True)

    # ── Billing Address ───────────────────────────────────────
    billing_name = Column(String(255), nullable=True)
    billing_address_line1 = Column(String(255), nullable=True)
    billing_address_line2 = Column(String(255), nullable=True)
    billing_city = Column(String(100), nullable=True)
    billing_state = Column(String(100), nullable=True)
    billing_zip = Column(String(20), nullable=True)
    billing_country = Column(String(100), nullable=True)

    # ── Shipping Address (primary for shipping) ───────────────
    shipping_name = Column(String(255), nullable=False)
    shipping_address_line1 = Column(String(255), nullable=False)
    shipping_address_line2 = Column(String(255), nullable=True)
    shipping_city = Column(String(100), nullable=False)
    shipping_state = Column(String(100), nullable=False)
    shipping_zip = Column(String(20), nullable=False)
    shipping_country = Column(String(100), nullable=False)
    shipping_phone = Column(String(20), nullable=True)

    # ── Order Amounts (in store currency) ──────────────────────
    currency = Column(String(10), nullable=False, default="INR")
    subtotal = Column(Numeric(12, 2), nullable=False)
    taxes = Column(Numeric(12, 2), nullable=False, default=0)
    discounts = Column(Numeric(12, 2), nullable=False, default=0)
    shipping_cost = Column(Numeric(12, 2), nullable=False, default=0)
    total_price = Column(Numeric(12, 2), nullable=False)

    # ── Items Summary ─────────────────────────────────────────
    line_items_count = Column(Integer, nullable=False, default=0)
    line_items_json = Column(JSON, nullable=True)  # Full items array from Shopify

    # ── Shipping & Tracking (to be filled) ────────────────────
    shipping_partner = Column(Enum(ShippingPartner), nullable=True)  # delhivery | india_post | etc
    tracking_number = Column(String(100), nullable=True)
    tracking_url = Column(Text, nullable=True)
    
    # ── Timeline ──────────────────────────────────────────────
    created_at_shopify = Column(DateTime(timezone=True), nullable=False)  # When created in Shopify
    updated_at_shopify = Column(DateTime(timezone=True), nullable=False)  # Last update from Shopify
    expected_delivery_date = Column(Date, nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)

    # ── Local metadata ────────────────────────────────────────
    notes = Column(Text, nullable=True)
    raw_shopify_data = Column(JSON, nullable=True)  # Full Shopify webhook payload (for debugging)

    # ── Sync status ───────────────────────────────────────────
    synced_at = Column(DateTime(timezone=True), server_default=func.now())
    last_tracking_update = Column(DateTime(timezone=True), nullable=True)

    # ── Timestamps ────────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # ── Relationships ──────────────────────────────────────────
    # Note: ShopifyStore not included as relationship to avoid circular imports
    # Access via shopify_store_id foreign key if needed
    customer = relationship("Customer", back_populates="shopify_orders", foreign_keys="[ShopifyOrder.customer_id]")
    shipping_info = relationship("ShippingInfo", back_populates="shopify_order", uselist=False, cascade="all, delete-orphan")
    tracking_events = relationship("TrackingEvent", back_populates="shopify_order", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("shopify_store_id", "shopify_order_id", name="uq_shopify_order_per_store"),
        Index("ix_shopify_orders_tenant_id", "tenant_id"),
        Index("ix_shopify_orders_store_id", "shopify_store_id"),
        Index("ix_shopify_orders_customer_id", "customer_id"),
        Index("ix_shopify_orders_status", "shopify_status"),
        Index("ix_shopify_orders_created_at_shopify", "created_at_shopify"),
        Index("ix_shopify_orders_tracking_number", "tracking_number"),
    )


# ─────────────────────────────────────────────────────────────
# Shipping Info (Delhivery/India Post tracking)
# ─────────────────────────────────────────────────────────────

class ShippingInfo(Base):
    """
    Shipping & tracking info for a Shopify order.
    Links to Delhivery or India Post or other courier.
    """
    __tablename__ = "shipping_info"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    shopify_order_id = Column(UUID(as_uuid=True), ForeignKey("shopify_orders.id"), nullable=False, unique=True)

    # ── Courier Info ──────────────────────────────────────────
    shipping_partner = Column(Enum(ShippingPartner), nullable=False)  # delhivery | india_post
    courier_name = Column(String(100), nullable=False)  # Display name
    courier_code = Column(String(50), nullable=True)

    # ── Tracking Details ──────────────────────────────────────
    tracking_number = Column(String(100), nullable=False)  # Delhivery/IP tracking ID
    tracking_url = Column(Text, nullable=True)
    tracking_status = Column(Enum(TrackingStatus), nullable=False, default=TrackingStatus.pending)

    # ── Shipment Info ─────────────────────────────────────────
    shipment_date = Column(Date, nullable=True)
    actual_weight = Column(Numeric(8, 2), nullable=True)  # kg
    dimensions = Column(String(100), nullable=True)  # L×W×H in cm
    
    # ── Charges (from courier) ────────────────────────────────
    base_charge = Column(Numeric(10, 2), nullable=True)
    fuel_surcharge = Column(Numeric(10, 2), nullable=True, default=0)
    handling_charge = Column(Numeric(10, 2), nullable=True, default=0)
    total_charge = Column(Numeric(10, 2), nullable=True)

    # ── Courier API Response (raw) ────────────────────────────
    courier_api_response = Column(JSON, nullable=True)  # Full API response from Delhivery/IP

    # ── Status ────────────────────────────────────────────────
    is_delivered = Column(Boolean, default=False, nullable=False)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    delivery_attempt_count = Column(Integer, default=0, nullable=False)

    last_tracking_update = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # ── Relationships ──────────────────────────────────────────
    shopify_order = relationship("ShopifyOrder", back_populates="shipping_info")

    __table_args__ = (
        Index("ix_shipping_info_tenant_id", "tenant_id"),
        Index("ix_shipping_info_tracking_number", "tracking_number"),
        Index("ix_shipping_info_shipping_partner", "shipping_partner"),
    )


# ─────────────────────────────────────────────────────────────
# Tracking Events (audit trail from courier)
# ─────────────────────────────────────────────────────────────

class TrackingEvent(Base):
    """
    Individual tracking updates from Delhivery/India Post.
    Cumulative history of all tracking updates for an order.
    """
    __tablename__ = "tracking_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    shopify_order_id = Column(UUID(as_uuid=True), ForeignKey("shopify_orders.id"), nullable=False)

    # ── Event Details ─────────────────────────────────────────
    event_status = Column(Enum(TrackingStatus), nullable=False)
    event_time = Column(DateTime(timezone=True), nullable=False)
    
    location = Column(String(255), nullable=True)  # City/location where event occurred
    location_code = Column(String(50), nullable=True)  # Hub code from courier
    
    description = Column(Text, nullable=True)  # "Out for delivery" | "In transit to MUMBAI" etc
    detail = Column(Text, nullable=True)  # Additional details from courier

    # ── Courier Details ───────────────────────────────────────
    courier_event_id = Column(String(100), nullable=True)  # Unique event ID from courier
    courier_name = Column(String(100), nullable=True)

    # ── Raw Data ──────────────────────────────────────────────
    raw_tracking_data = Column(JSON, nullable=True)  # Full event data from API

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ── Relationships ──────────────────────────────────────────
    shopify_order = relationship("ShopifyOrder", back_populates="tracking_events")

    __table_args__ = (
        Index("ix_tracking_events_tenant_id", "tenant_id"),
        Index("ix_tracking_events_shopify_order_id", "shopify_order_id"),
        Index("ix_tracking_events_event_status", "event_status"),
        Index("ix_tracking_events_event_time", "event_time"),
    )
