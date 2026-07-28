"""
WhatsApp Engine — SQLAlchemy Models
=====================================
Multi-tenant, provider-agnostic WhatsApp integration.

Tables:
  wa_settings            – per-tenant provider config (WABIS or META)
  wa_postback_rules      – configurable postback → lead action mapping
  wa_campaign_types      – fully user-defined campaign types (order, pack, ship, custom…)
  wa_subscribers         – WABIS subscriber records (separate from leads)
  wa_conversations       – one thread per subscriber
  wa_messages            – every message in/out
  wa_status              – WhatsApp-specific pipeline (SEPARATE from Lead.status)
  wa_campaigns           – blast / notification campaigns
  wa_campaign_recipients – per-recipient delivery tracking

Design rules:
  - Every table carries tenant_id for strict multi-tenant isolation
  - WhatsApp status is a completely separate entity from Lead.status
  - Nothing is hardcoded: providers, campaign types, postback rules are all DB rows
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey,
    Index, Integer, Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


# ─────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────

class WaProvider(str, enum.Enum):
    wabis    = "wabis"    # BotSailor / WABIS webhook-based
    meta     = "meta"     # Meta Cloud API direct


class WaMessageDirection(str, enum.Enum):
    inbound  = "inbound"
    outbound = "outbound"


class WaMessageType(str, enum.Enum):
    text     = "text"
    image    = "image"
    document = "document"
    audio    = "audio"
    video    = "video"
    template = "template"
    unknown  = "unknown"


class WaMessageStatus(str, enum.Enum):
    pending   = "pending"
    sent      = "sent"
    delivered = "delivered"
    read      = "read"
    failed    = "failed"


class WaPostbackAction(str, enum.Enum):
    create_lead   = "create_lead"    # auto-create a new lead
    update_status = "update_status"  # update existing lead status
    add_label     = "add_label"      # add a label to existing lead
    ignore        = "ignore"         # do nothing, just log


class WaStatusEnum(str, enum.Enum):
    """
    WhatsApp-specific CRM pipeline.
    Completely independent from LeadPipelineStatus.
    Connected only via tenant_id + lead_id.
    """
    new_message     = "new_message"
    replied         = "replied"
    follow_up       = "follow_up"
    no_response     = "no_response"
    hot             = "hot"
    cold            = "cold"
    blocked         = "blocked"
    converted       = "converted"
    order_confirmed = "order_confirmed"
    order_packed    = "order_packed"
    order_shipped   = "order_shipped"
    out_for_delivery = "out_for_delivery"
    delivered       = "delivered"


class WaCampaignStatus(str, enum.Enum):
    draft     = "draft"
    running   = "running"
    completed = "completed"
    failed    = "failed"
    cancelled = "cancelled"


class WaTriggerEvent(str, enum.Enum):
    """
    Predefined trigger events that auto-fire outbound WhatsApp messages.
    These map to business events in the order lifecycle + marketing.
    """
    manual          = "manual"           # manually triggered (marketing blast)
    order_created   = "order_created"    # new confirmed order created → sends label/confirmation
    order_confirmed = "order_confirmed"  # order status → confirmed (status change)
    order_packed    = "order_packed"     # order status → packed
    order_shipped   = "order_shipped"    # order status → shipped (tracking added)
    order_delivered  = "order_delivered" # order status → delivered


class WaRecipientStatus(str, enum.Enum):
    pending = "pending"
    sent    = "sent"
    failed  = "failed"
    skipped = "skipped"


# ─────────────────────────────────────────────────────────────
# 1. wa_settings — per-tenant provider configuration
# ─────────────────────────────────────────────────────────────

class WaSettings(Base):
    __tablename__ = "wa_settings"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id    = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    # Provider
    provider     = Column(Enum(WaProvider, create_type=False), nullable=False, default=WaProvider.wabis)
    display_name = Column(String(255), nullable=True)   # e.g. "Pureleven Exim WhatsApp"
    phone_number = Column(String(20),  nullable=True)   # display only

    # ── WABIS / BotSailor fields ──────────────────────────────
    wabis_bot_id          = Column(String(100),  nullable=True)
    wabis_phone_number_id = Column(String(100),  nullable=True)   # WhatsApp phone_number_id for direct send
    wabis_api_token       = Column(Text,         nullable=True)   # apiToken for /api/v1/* endpoints
    wabis_access_token    = Column(Text,         nullable=True)   # store as-is; encrypt in prod
    wabis_api_base_url    = Column(String(500),  nullable=True,
                                   default="https://admin.workpex.com")

    # ── Meta Cloud API fields ─────────────────────────────────
    meta_phone_number_id  = Column(String(100),  nullable=True)
    meta_access_token     = Column(Text,         nullable=True)
    meta_api_version      = Column(String(20),   nullable=True, default="v19.0")
    meta_webhook_verify_token = Column(String(255), nullable=True)

    # ── Shared inbound webhook security ───────────────────────
    # Unique secret per tenant — generated on first save
    # Tenant pastes: POST /api/wa/inbound/{tenant_id}
    # with header X-Webhook-Secret: inbound_secret
    inbound_secret = Column(String(100), nullable=False,
                             default=lambda: str(uuid.uuid4()))

    # ── Auto-reply ────────────────────────────────────────────
    auto_reply_enabled = Column(Boolean, default=False, nullable=False)
    auto_reply_message = Column(Text, nullable=True)

    # ── Status ────────────────────────────────────────────────
    is_active  = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_wa_settings_tenant"),
        Index("ix_wa_settings_tenant_id", "tenant_id"),
    )


# ─────────────────────────────────────────────────────────────
# 2. wa_postback_rules — configurable postback → action mapping
# ─────────────────────────────────────────────────────────────

class WaPostbackRule(Base):
    """
    Tenant-configurable: when WABIS fires a postback with a specific
    postback_id, perform an action (create lead, update status, etc.)

    Example:
      postback_id  = "68ebb3af11e6c"
      display_name = "വിലാസം നൽകുക"
      action       = "create_lead"
      lead_source  = "wabis"
      lead_label   = "Order Flow"
    """
    __tablename__ = "wa_postback_rules"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id    = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    postback_id   = Column(String(255), nullable=False)   # exact match from WABIS payload
    display_name  = Column(String(255), nullable=True)    # human label for UI

    action        = Column(Enum(WaPostbackAction, create_type=False), nullable=False,
                           default=WaPostbackAction.create_lead)

    # Used when action = create_lead or update_status
    lead_source   = Column(String(100), nullable=True)    # e.g. "wabis", "whatsapp"
    lead_label    = Column(String(255), nullable=True)    # label tag to apply
    lead_status   = Column(String(50),  nullable=True)    # e.g. "new_lead"
    lead_priority = Column(String(20),  nullable=True)    # e.g. "medium"

    # Additional metadata (JSON) for future extensibility
    extra_config  = Column(JSONB, nullable=True)

    is_active  = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "postback_id", name="uq_wa_postback_tenant"),
        Index("ix_wa_postback_rules_tenant_id", "tenant_id"),
    )


# ─────────────────────────────────────────────────────────────
# 3. wa_campaign_types — fully user-defined campaign types
# ─────────────────────────────────────────────────────────────

class WaCampaignType(Base):
    """
    Tenant-configurable campaign types.
    Each type maps to a WABIS Webhook Workflow URL and a message template.

    Examples an employee might create:
      - name="Order Confirmed", wabis_workflow_url="https://admin.workpex.com/wabis/abc123"
      - name="Order Packed",    wabis_workflow_url="https://admin.workpex.com/wabis/def456"
      - name="Shipped",         wabis_workflow_url="https://admin.workpex.com/wabis/ghi789"
      - name="Cardamom Promo",  wabis_workflow_url="https://admin.workpex.com/wabis/promo1"
    """
    __tablename__ = "wa_campaign_types"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id   = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    name        = Column(String(255), nullable=False)    # user-defined, e.g. "Order Packed"
    description = Column(Text, nullable=True)
    icon        = Column(String(10), nullable=True)      # emoji for UI, e.g. "📦"
    category    = Column(String(50), nullable=True)      # grouping: transactional|marketing|utility

    # Auto-trigger event: when this business event fires, this template is used
    trigger_event = Column(Enum(WaTriggerEvent, create_type=False),
                           nullable=False, default=WaTriggerEvent.manual)

    # WABIS outbound: which Webhook Workflow URL to POST to
    wabis_workflow_url = Column(Text, nullable=True)

    # Fallback URL used when the customer is outside the 24-hour messaging window.
    # WABIS utility/template messages can reach users outside the window.
    utility_workflow_url = Column(Text, nullable=True)

    # Variable mapping: template for the JSON payload sent to WABIS
    # e.g. {"customer_name": "{{name}}", "order_id": "{{order_number}}"}
    payload_template   = Column(JSONB, nullable=True)

    # Meta: which approved template to use
    meta_template_name = Column(String(255), nullable=True)
    meta_template_lang = Column(String(20),  nullable=True, default="en")

    is_active   = Column(Boolean, default=True, nullable=False)
    created_by_employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    campaigns = relationship("WaCampaign", back_populates="campaign_type")

    __table_args__ = (
        Index("ix_wa_campaign_types_tenant_id", "tenant_id"),
    )


# ─────────────────────────────────────────────────────────────
# 4. wa_subscribers — WABIS subscriber records
# ─────────────────────────────────────────────────────────────

class WaSubscriber(Base):
    """
    Stores the WABIS subscriber identity separately from CRM leads.
    A subscriber is created/updated every time WABIS fires an inbound webhook.
    May be linked to a Lead via lead_id once lead creation happens.
    """
    __tablename__ = "wa_subscribers"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id     = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    # From WABIS payload
    subscriber_id = Column(String(255), nullable=False)  # WABIS subscriber_id
    phone_number  = Column(String(30),  nullable=False)  # E.164 or raw as sent by WABIS
    name          = Column(String(255), nullable=True)   # subscriber_name from WABIS

    # WABIS labels (JSON array: ["label1", "label2"]) — accumulated across all triggers
    wabis_labels  = Column(JSONB, nullable=True)

    # Postback tracking
    last_postback_id = Column(String(255), nullable=True)   # most recent postback seen
    postback_ids     = Column(JSONB, nullable=True)          # all postback IDs ever seen (for send-back)

    # Link to CRM Lead (nullable — not every subscriber becomes a lead)
    lead_id       = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)

    is_opted_out  = Column(Boolean, default=False, nullable=False)
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at  = Column(DateTime(timezone=True), server_default=func.now(),
                           onupdate=func.now())

    # Relationships
    conversations = relationship("WaConversation", back_populates="subscriber")
    wa_status     = relationship("WaStatus", back_populates="subscriber",
                                  uselist=False)
    message_logs  = relationship("WaMessageLog", back_populates="subscriber",
                                  cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tenant_id", "subscriber_id", name="uq_wa_subscriber_tenant"),
        Index("ix_wa_subscribers_tenant_id",    "tenant_id"),
        Index("ix_wa_subscribers_phone",        "phone_number"),
        Index("ix_wa_subscribers_lead_id",      "lead_id"),
    )


# ─────────────────────────────────────────────────────────────
# 5. wa_conversations — one thread per subscriber
# ─────────────────────────────────────────────────────────────

class WaConversation(Base):
    __tablename__ = "wa_conversations"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id     = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    subscriber_id = Column(UUID(as_uuid=True), ForeignKey("wa_subscribers.id"), nullable=False)
    lead_id       = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)

    last_message_at       = Column(DateTime(timezone=True), nullable=True)
    last_message_direction = Column(Enum(WaMessageDirection, create_type=False), nullable=True)
    unread_count          = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    subscriber = relationship("WaSubscriber", back_populates="conversations")
    messages   = relationship("WaMessage", back_populates="conversation",
                               order_by="WaMessage.sent_at")

    __table_args__ = (
        UniqueConstraint("tenant_id", "subscriber_id", name="uq_wa_conv_subscriber"),
        Index("ix_wa_conversations_tenant_id",    "tenant_id"),
        Index("ix_wa_conversations_subscriber_id","subscriber_id"),
        Index("ix_wa_conversations_lead_id",      "lead_id"),
        Index("ix_wa_conversations_last_msg",     "tenant_id", "last_message_at"),
    )


# ─────────────────────────────────────────────────────────────
# 6. wa_messages — every message in/out
# ─────────────────────────────────────────────────────────────

class WaMessage(Base):
    __tablename__ = "wa_messages"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id           = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    conversation_id     = Column(UUID(as_uuid=True), ForeignKey("wa_conversations.id"),
                                  nullable=False)

    provider_message_id = Column(String(255), nullable=True)   # WABIS/Meta msg ID for dedup
    direction           = Column(Enum(WaMessageDirection, create_type=False), nullable=False)
    message_type        = Column(Enum(WaMessageType, create_type=False), nullable=False,
                                  default=WaMessageType.text)
    content             = Column(Text, nullable=True)
    media_url           = Column(Text, nullable=True)           # for image/doc/audio/video

    status              = Column(Enum(WaMessageStatus, create_type=False), nullable=False,
                                  default=WaMessageStatus.pending)
    sent_at             = Column(DateTime(timezone=True), server_default=func.now())
    delivered_at        = Column(DateTime(timezone=True), nullable=True)
    read_at             = Column(DateTime(timezone=True), nullable=True)
    failed_reason       = Column(Text, nullable=True)

    sent_by_employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True)

    # Raw payload from WABIS for debugging (nullable)
    raw_payload         = Column(JSONB, nullable=True)

    # Relationships
    conversation = relationship("WaConversation", back_populates="messages")

    __table_args__ = (
        Index("ix_wa_messages_tenant_id",        "tenant_id"),
        Index("ix_wa_messages_conversation_id",  "conversation_id"),
        Index("ix_wa_messages_provider_msg_id",  "provider_message_id"),
        Index("ix_wa_messages_sent_at",          "sent_at"),
    )


# ─────────────────────────────────────────────────────────────
# 7. wa_status — WhatsApp CRM pipeline (SEPARATE entity)
# ─────────────────────────────────────────────────────────────

class WaStatus(Base):
    """
    WhatsApp-specific pipeline status.
    Completely separate from Lead.status.
    Connected to leads via tenant_id + lead_id.
    One row per subscriber (upserted on every status change).
    Full history tracked via wa_status_history.
    """
    __tablename__ = "wa_status"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id     = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    subscriber_id = Column(UUID(as_uuid=True), ForeignKey("wa_subscribers.id"), nullable=False)
    lead_id       = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)

    status        = Column(Enum(WaStatusEnum, create_type=False), nullable=False,
                           default=WaStatusEnum.new_message)
    assigned_to_employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"),
                                      nullable=True)
    note          = Column(Text, nullable=True)
    updated_by_employee_id  = Column(UUID(as_uuid=True), ForeignKey("employees.id"),
                                      nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                        onupdate=func.now())

    # Relationships
    subscriber = relationship("WaSubscriber", back_populates="wa_status")
    history    = relationship("WaStatusHistory", back_populates="wa_status",
                               order_by="WaStatusHistory.changed_at.desc()")

    __table_args__ = (
        UniqueConstraint("tenant_id", "subscriber_id", name="uq_wa_status_subscriber"),
        Index("ix_wa_status_tenant_id",    "tenant_id"),
        Index("ix_wa_status_subscriber_id","subscriber_id"),
        Index("ix_wa_status_lead_id",      "lead_id"),
        Index("ix_wa_status_status",       "status"),
    )


class WaStatusHistory(Base):
    """Audit trail of every WhatsApp status change."""
    __tablename__ = "wa_status_history"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id     = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    wa_status_id  = Column(UUID(as_uuid=True), ForeignKey("wa_status.id"), nullable=False)

    old_status    = Column(Enum(WaStatusEnum, create_type=False), nullable=True)
    new_status    = Column(Enum(WaStatusEnum, create_type=False), nullable=False)
    changed_by_employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"),
                                     nullable=True)
    note          = Column(Text, nullable=True)
    changed_at    = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    wa_status = relationship("WaStatus", back_populates="history")

    __table_args__ = (
        Index("ix_wa_status_history_wa_status_id", "wa_status_id"),
        Index("ix_wa_status_history_tenant_id",    "tenant_id"),
    )


# ─────────────────────────────────────────────────────────────
# 8. wa_campaigns — blast / notification campaigns
# ─────────────────────────────────────────────────────────────

class WaCampaign(Base):
    __tablename__ = "wa_campaigns"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id        = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    name             = Column(String(255), nullable=False)
    campaign_type_id = Column(UUID(as_uuid=True), ForeignKey("wa_campaign_types.id"),
                               nullable=True)   # nullable: custom one-off campaigns

    # Audience filter snapshot (JSON) — stored for re-run / audit
    audience_filter  = Column(JSONB, nullable=True)
    # One-off workflow URL override (if not using campaign_type)
    workflow_url_override = Column(Text, nullable=True)
    # Payload template override
    payload_template_override = Column(JSONB, nullable=True)

    status           = Column(Enum(WaCampaignStatus, create_type=False), nullable=False,
                               default=WaCampaignStatus.draft)

    # Counters (updated as recipients are processed)
    total_recipients = Column(Integer, default=0, nullable=False)
    sent_count       = Column(Integer, default=0, nullable=False)
    failed_count     = Column(Integer, default=0, nullable=False)
    skipped_count    = Column(Integer, default=0, nullable=False)

    scheduled_at     = Column(DateTime(timezone=True), nullable=True)
    started_at       = Column(DateTime(timezone=True), nullable=True)
    completed_at     = Column(DateTime(timezone=True), nullable=True)

    created_by_employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"),
                                     nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    campaign_type = relationship("WaCampaignType", back_populates="campaigns")
    recipients    = relationship("WaCampaignRecipient", back_populates="campaign",
                                  cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_wa_campaigns_tenant_id", "tenant_id"),
        Index("ix_wa_campaigns_status",    "status"),
    )


# ─────────────────────────────────────────────────────────────
# 9a. wa_message_log — message delivery tracking
# ─────────────────────────────────────────────────────────────

class WaMessageLog(Base):
    """
    Tracks every message sent to each WhatsApp contact.
    Used for delivery status, read receipts, and message history.
    """
    __tablename__ = "whatsapp_api_message_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    subscriber_id = Column(UUID(as_uuid=True), ForeignKey("wa_subscribers.id"), nullable=False)
    
    # Message content
    message_template_id = Column(UUID(as_uuid=True), nullable=True)
    message_text = Column(Text, nullable=False)
    
    # Delivery tracking
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    delivery_status = Column(String(50), default="pending", nullable=False)
    # Values: pending, sent, delivered, read, failed
    failure_reason = Column(String(255), nullable=True)
    
    # References
    sent_by_employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("wa_campaigns.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    subscriber = relationship("WaSubscriber", back_populates="message_logs")
    
    __table_args__ = (
        Index("ix_wa_message_log_subscriber", "subscriber_id"),
        Index("ix_wa_message_log_tenant", "tenant_id"),
        Index("ix_wa_message_log_sent_at", "sent_at"),
    )


# ─────────────────────────────────────────────────────────────
# 10. wa_campaign_recipients — per-recipient delivery tracking
# ─────────────────────────────────────────────────────────────

class WaCampaignRecipient(Base):
    __tablename__ = "wa_campaign_recipients"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("wa_campaigns.id"), nullable=False)
    tenant_id   = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    # Recipient identity
    subscriber_id = Column(UUID(as_uuid=True), ForeignKey("wa_subscribers.id"), nullable=True)
    lead_id       = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)
    wa_phone      = Column(String(30), nullable=False)
    contact_name  = Column(String(255), nullable=True)

    # The exact payload that was sent to WABIS (JSON)
    payload_sent  = Column(JSONB, nullable=True)

    status        = Column(Enum(WaRecipientStatus, create_type=False), nullable=False,
                           default=WaRecipientStatus.pending)
    provider_response = Column(JSONB, nullable=True)   # raw WABIS response
    error_reason  = Column(Text, nullable=True)
    sent_at       = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    campaign = relationship("WaCampaign", back_populates="recipients")

    __table_args__ = (
        Index("ix_wa_campaign_recipients_campaign_id", "campaign_id"),
        Index("ix_wa_campaign_recipients_tenant_id",   "tenant_id"),
        Index("ix_wa_campaign_recipients_status",      "status"),
    )


# ─────────────────────────────────────────────────────────────
# 11. wa_outbound_webhooks — user-configured outbound webhooks
#     that POST subscriber data to an external URL on events
# ─────────────────────────────────────────────────────────────

class WaOutboundWebhook(Base):
    """
    Tenant-configured outbound webhooks.
    When a WABIS subscriber event fires (new message, status change, postback),
    Miguel POSTs selected subscriber fields to these URLs.

    Fields selected by the user are stored as a JSON list of strings, e.g.:
      ["subscriber_id", "name", "phone", "wabis_status", "labels", "postback_id"]
    """
    __tablename__ = "wa_outbound_webhooks"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id   = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    name        = Column(String(255), nullable=False)          # user label, e.g. "CRM Sync"
    url         = Column(Text, nullable=False)                 # destination URL
    is_active   = Column(Boolean, default=True, nullable=False)

    # Events that trigger this webhook
    # JSON list of strings: ["new_message","status_change","postback","opt_out"]
    trigger_events = Column(JSONB, nullable=False,
                            default=lambda: ["new_message", "postback"])

    # Fields to include in the POST payload
    # JSON list of strings from: subscriber_id, name, phone, email,
    #   wabis_status, labels, postback_id, postback_title,
    #   date_of_birth, location, input_flow_data, wa_status_code
    data_fields = Column(JSONB, nullable=False, default=lambda: [
        "subscriber_id", "name", "phone", "wabis_status", "labels", "postback_id"
    ])

    # Optional: only fire for specific postback IDs (empty = all)
    postback_filter = Column(JSONB, nullable=True)   # list of postback_id strings

    # Secret header sent with every call (X-Miguel-Secret)
    secret      = Column(String(100), nullable=True,
                         default=lambda: str(uuid.uuid4()).replace("-", "")[:32])

    # Stats
    last_fired_at      = Column(DateTime(timezone=True), nullable=True)
    last_status_code   = Column(Integer, nullable=True)
    total_fired        = Column(Integer, default=0, nullable=False)
    total_failed       = Column(Integer, default=0, nullable=False)

    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("ix_wa_outbound_webhooks_tenant", "tenant_id"),
        Index("ix_wa_outbound_webhooks_active",  "tenant_id", "is_active"),
    )

