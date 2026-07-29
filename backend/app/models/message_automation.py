import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class MessageAutomationSetting(Base):
    __tablename__ = "message_automation_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    is_enabled = Column(Boolean, nullable=False, default=True)
    website_url = Column(String(500), nullable=True)
    google_review_url = Column(Text, nullable=True)
    business_whatsapp_phone = Column(String(30), nullable=True)
    meta_template_asset_id = Column(String(100), nullable=True)
    template_bindings = Column(JSONB, nullable=True)
    template_header_media_urls = Column(JSONB, nullable=True)
    review_campaign_started_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_message_automation_settings_tenant"),
        Index("ix_message_automation_settings_tenant", "tenant_id"),
    )


class CustomerMessagePreference(Base):
    __tablename__ = "customer_message_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)

    phone_e164 = Column(String(30), nullable=False)
    whatsapp_opted_out = Column(Boolean, nullable=False, default=False)
    email_opted_out = Column(Boolean, nullable=False, default=False)
    automation_paused = Column(Boolean, nullable=False, default=False)
    pause_reason = Column(Text, nullable=True)
    paused_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    customer = relationship("Customer")

    __table_args__ = (
        UniqueConstraint("tenant_id", "phone_e164", name="uq_customer_message_pref_tenant_phone"),
        Index("ix_customer_message_pref_tenant", "tenant_id"),
        Index("ix_customer_message_pref_customer", "customer_id"),
        Index("ix_customer_message_pref_phone", "phone_e164"),
    )


class MessageAutomationTask(Base):
    __tablename__ = "message_automation_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True)

    channel = Column(String(20), nullable=False)
    template_key = Column(String(80), nullable=False)
    event_type = Column(String(80), nullable=False)
    status = Column(String(20), nullable=False, default="pending")

    recipient_phone_e164 = Column(String(30), nullable=True)
    recipient_email = Column(String(255), nullable=True)
    recipient_name = Column(String(255), nullable=True)
    subject = Column(String(255), nullable=True)
    body = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=True)

    dedupe_key = Column(String(255), nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    provider_message_id = Column(String(255), nullable=True)
    provider_response = Column(JSONB, nullable=True)
    error_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    customer = relationship("Customer")
    order = relationship("Order")

    __table_args__ = (
        UniqueConstraint("tenant_id", "dedupe_key", name="uq_message_task_tenant_dedupe"),
        Index("ix_message_task_due", "status", "scheduled_at"),
        Index("ix_message_task_tenant", "tenant_id"),
        Index("ix_message_task_customer", "customer_id"),
        Index("ix_message_task_order", "order_id"),
        Index("ix_message_task_template", "template_key"),
    )
