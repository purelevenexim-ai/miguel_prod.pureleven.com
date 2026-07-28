"""
WhatsApp Engine — Pydantic Schemas
=====================================
All request/response models for the wa_engine module.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator, model_validator

from app.models.wa_engine import (
    WaProvider, WaPostbackAction, WaStatusEnum, WaTriggerEvent,
    WaCampaignStatus, WaRecipientStatus,
    WaMessageDirection, WaMessageType, WaMessageStatus,
)


# ─────────────────────────────────────────────────────────────
# Settings
# ─────────────────────────────────────────────────────────────

class WaSettingsSave(BaseModel):
    provider:        WaProvider = WaProvider.wabis
    display_name:    Optional[str] = None
    phone_number:    Optional[str] = None

    # WABIS
    wabis_bot_id:          Optional[str] = None
    wabis_phone_number_id: Optional[str] = None
    wabis_api_token:       Optional[str] = None
    wabis_access_token:    Optional[str] = None
    wabis_api_base_url:    Optional[str] = "https://admin.workpex.com"

    # Meta
    meta_phone_number_id:       Optional[str] = None
    meta_access_token:          Optional[str] = None
    meta_api_version:           Optional[str] = "v19.0"
    meta_webhook_verify_token:  Optional[str] = None

    # Auto-reply
    auto_reply_enabled: bool = False
    auto_reply_message: Optional[str] = None


class WaSettingsResponse(BaseModel):
    model_config = {"from_attributes": True}

    id:              UUID
    tenant_id:       UUID
    provider:        WaProvider
    display_name:    Optional[str]
    phone_number:    Optional[str]

    # WABIS (tokens masked in response)
    wabis_bot_id:          Optional[str]
    wabis_phone_number_id: Optional[str]
    wabis_api_base_url:    Optional[str]
    wabis_token_set:       bool = False   # True if access_token is non-empty
    wabis_api_token_set:   bool = False   # True if apiToken is non-empty

    # Meta (IDs masked)
    meta_phone_number_id_masked: Optional[str] = None
    meta_api_version:            Optional[str]
    meta_token_set:              bool = False
    meta_webhook_verify_token:   Optional[str]

    # Inbound webhook info
    inbound_secret: str
    inbound_webhook_url: Optional[str] = None   # populated by router

    auto_reply_enabled: bool
    auto_reply_message: Optional[str]
    is_active: bool
    updated_at: Optional[datetime]


class WaSettingsTestResponse(BaseModel):
    success: bool
    message: str
    detail:  Optional[str] = None


# ─────────────────────────────────────────────────────────────
# Postback Rules
# ─────────────────────────────────────────────────────────────

class WaPostbackRuleCreate(BaseModel):
    postback_id:   str
    display_name:  Optional[str] = None
    action:        WaPostbackAction = WaPostbackAction.create_lead
    lead_source:   Optional[str] = "wabis"
    lead_label:    Optional[str] = None
    lead_status:   Optional[str] = "new_lead"
    lead_priority: Optional[str] = "medium"
    extra_config:  Optional[Dict[str, Any]] = None

    @field_validator("postback_id")
    @classmethod
    def postback_id_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("postback_id cannot be empty")
        return v


class WaPostbackRuleUpdate(BaseModel):
    display_name:  Optional[str] = None
    action:        Optional[WaPostbackAction] = None
    lead_source:   Optional[str] = None
    lead_label:    Optional[str] = None
    lead_status:   Optional[str] = None
    lead_priority: Optional[str] = None
    extra_config:  Optional[Dict[str, Any]] = None
    is_active:     Optional[bool] = None


class WaPostbackRuleResponse(BaseModel):
    model_config = {"from_attributes": True}

    id:           UUID
    tenant_id:    UUID
    postback_id:  str
    display_name: Optional[str]
    action:       WaPostbackAction
    lead_source:  Optional[str]
    lead_label:   Optional[str]
    lead_status:  Optional[str]
    lead_priority: Optional[str]
    extra_config: Optional[Dict[str, Any]]
    is_active:    bool
    created_at:   datetime
    updated_at:   Optional[datetime]


# ─────────────────────────────────────────────────────────────
# Campaign Types
# ─────────────────────────────────────────────────────────────

class WaCampaignTypeCreate(BaseModel):
    name:                str
    description:         Optional[str] = None
    icon:                Optional[str] = None      # emoji
    category:            Optional[str] = None      # transactional|marketing|utility
    trigger_event:       WaTriggerEvent = WaTriggerEvent.manual
    wabis_workflow_url:  Optional[str] = None
    utility_workflow_url: Optional[str] = None     # fallback URL for outside-24h window
    payload_template:    Optional[Dict[str, Any]] = None
    meta_template_name:  Optional[str] = None
    meta_template_lang:  Optional[str] = "en"

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name cannot be empty")
        return v


class WaCampaignTypeUpdate(BaseModel):
    name:                Optional[str] = None
    description:         Optional[str] = None
    icon:                Optional[str] = None
    category:            Optional[str] = None
    trigger_event:       Optional[WaTriggerEvent] = None
    wabis_workflow_url:  Optional[str] = None
    utility_workflow_url: Optional[str] = None
    payload_template:    Optional[Dict[str, Any]] = None
    meta_template_name:  Optional[str] = None
    meta_template_lang:  Optional[str] = None
    is_active:           Optional[bool] = None


class WaCampaignTypeResponse(BaseModel):
    model_config = {"from_attributes": True}

    id:                  UUID
    tenant_id:           UUID
    name:                str
    description:         Optional[str]
    icon:                Optional[str]
    category:            Optional[str]
    trigger_event:       WaTriggerEvent
    wabis_workflow_url:  Optional[str]
    utility_workflow_url: Optional[str] = None
    payload_template:    Optional[Dict[str, Any]]
    meta_template_name:  Optional[str]
    meta_template_lang:  Optional[str]
    is_active:           bool
    created_at:          datetime
    updated_at:          Optional[datetime]


# ─────────────────────────────────────────────────────────────
# Subscribers
# ─────────────────────────────────────────────────────────────

class WaSubscriberResponse(BaseModel):
    model_config = {"from_attributes": True}

    id:               UUID
    tenant_id:        UUID
    subscriber_id:    str
    phone_number:     str
    name:             Optional[str]
    wabis_labels:     Optional[List[str]]
    last_postback_id: Optional[str]
    lead_id:          Optional[UUID]
    is_opted_out:     bool
    first_seen_at:    datetime
    last_seen_at:     Optional[datetime]

    # Populated by router
    lead_name:        Optional[str] = None
    wa_status:        Optional[str] = None


# ─────────────────────────────────────────────────────────────
# Conversations
# ─────────────────────────────────────────────────────────────

class WaConversationResponse(BaseModel):
    model_config = {"from_attributes": True}

    id:                     UUID
    tenant_id:              UUID
    subscriber_id:          UUID
    lead_id:                Optional[UUID]
    last_message_at:        Optional[datetime]
    last_message_direction: Optional[WaMessageDirection]
    unread_count:           int
    created_at:             datetime

    # Populated by service
    subscriber_name:        Optional[str] = None
    subscriber_phone:       Optional[str] = None
    lead_name:              Optional[str] = None
    wa_status:              Optional[str] = None
    last_message_preview:   Optional[str] = None


# ─────────────────────────────────────────────────────────────
# Messages
# ─────────────────────────────────────────────────────────────

class WaMessageSend(BaseModel):
    message:      str
    message_type: WaMessageType = WaMessageType.text

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty")
        if len(v) > 4096:
            raise ValueError("Message must be ≤ 4096 characters")
        return v


class WaMessageResponse(BaseModel):
    model_config = {"from_attributes": True}

    id:                  UUID
    tenant_id:           UUID
    conversation_id:     UUID
    provider_message_id: Optional[str]
    direction:           WaMessageDirection
    message_type:        WaMessageType
    content:             Optional[str]
    media_url:           Optional[str]
    status:              WaMessageStatus
    sent_at:             datetime
    delivered_at:        Optional[datetime]
    read_at:             Optional[datetime]
    failed_reason:       Optional[str]
    sent_by_employee_id: Optional[UUID]


# ─────────────────────────────────────────────────────────────
# WhatsApp Status
# ─────────────────────────────────────────────────────────────

class WaStatusUpdate(BaseModel):
    status:      WaStatusEnum
    note:        Optional[str] = None
    assigned_to: Optional[UUID] = None


class WaStatusResponse(BaseModel):
    model_config = {"from_attributes": True}

    id:            UUID
    tenant_id:     UUID
    subscriber_id: UUID
    lead_id:       Optional[UUID]
    status:        WaStatusEnum
    assigned_to_employee_id: Optional[UUID]
    note:          Optional[str]
    updated_by_employee_id:  Optional[UUID]
    created_at:    datetime
    updated_at:    Optional[datetime]

    # Populated by service
    subscriber_name:  Optional[str] = None
    subscriber_phone: Optional[str] = None
    assigned_to_name: Optional[str] = None


# ─────────────────────────────────────────────────────────────
# Campaigns
# ─────────────────────────────────────────────────────────────

class WaCampaignCreate(BaseModel):
    name:                     str
    campaign_type_id:         Optional[UUID] = None
    audience_filter:          Optional[Dict[str, Any]] = None
    workflow_url_override:    Optional[str] = None
    payload_template_override: Optional[Dict[str, Any]] = None
    scheduled_at:             Optional[datetime] = None

    # Recipient list: subscriber UUIDs or lead UUIDs
    # At least one must be provided when creating with recipients
    recipient_subscriber_ids: Optional[List[UUID]] = None
    recipient_lead_ids:       Optional[List[UUID]] = None
    # Or: arbitrary phone list for outreach
    recipient_phones:         Optional[List[Dict[str, str]]] = None  # [{phone, name}]

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Campaign name cannot be empty")
        return v

    @model_validator(mode="after")
    def needs_workflow(self) -> "WaCampaignCreate":
        if not self.campaign_type_id and not self.workflow_url_override:
            raise ValueError(
                "Either campaign_type_id or workflow_url_override must be provided"
            )
        return self


class WaCampaignResponse(BaseModel):
    model_config = {"from_attributes": True}

    id:               UUID
    tenant_id:        UUID
    name:             str
    campaign_type_id: Optional[UUID]
    status:           WaCampaignStatus
    total_recipients: int
    sent_count:       int
    failed_count:     int
    skipped_count:    int
    scheduled_at:     Optional[datetime]
    started_at:       Optional[datetime]
    completed_at:     Optional[datetime]
    created_at:       datetime
    updated_at:       Optional[datetime]

    # Populated by service
    campaign_type_name: Optional[str] = None
    workflow_url_used:  Optional[str] = None


class WaCampaignDetail(WaCampaignResponse):
    recipients: List[WaCampaignRecipientResponse] = []


class WaCampaignRecipientResponse(BaseModel):
    model_config = {"from_attributes": True}

    id:               UUID
    campaign_id:      UUID
    subscriber_id:    Optional[UUID]
    lead_id:          Optional[UUID]
    wa_phone:         str
    contact_name:     Optional[str]
    status:           WaRecipientStatus
    error_reason:     Optional[str]
    sent_at:          Optional[datetime]


# ─────────────────────────────────────────────────────────────
# Send Notification (outbound via WABIS workflow URL)
# ─────────────────────────────────────────────────────────────

class SendNotificationRequest(BaseModel):
    """Send a single outbound WhatsApp message via a campaign type's workflow URL."""
    phone:             str
    campaign_type_id:  Optional[UUID] = None
    workflow_url:      Optional[str] = None    # override if no campaign_type_id
    variables:         Optional[Dict[str, Any]] = None  # payload variables

    @field_validator("phone")
    @classmethod
    def phone_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("phone cannot be empty")
        return v

    @model_validator(mode="after")
    def needs_workflow_or_type(self) -> "SendNotificationRequest":
        if not self.campaign_type_id and not self.workflow_url:
            raise ValueError(
                "Either campaign_type_id or workflow_url must be provided"
            )
        return self


class SendNotificationResponse(BaseModel):
    success:  bool
    message:  str
    details:  Optional[Dict[str, Any]] = None


# ─────────────────────────────────────────────────────────────
# Inbound webhook payload (from WABIS)
# ─────────────────────────────────────────────────────────────

class WabisInboundPayload(BaseModel):
    """
    WABIS Out-bound Webhook payload structure.
    Based on the fields shown in the WABIS/BotSailor Out-bound Webhook UI.
    All fields are Optional since WABIS only sends enabled ones.
    """
    subscriber_id:   Optional[str] = None
    subscriber_name: Optional[str] = None
    phone_number:    Optional[str] = None
    postback_id:     Optional[str] = None
    postback_title:  Optional[str] = None
    labels:          Optional[Any] = None    # can be list or comma-string
    message:         Optional[str] = None    # user input text (if USER_INPUT_FLOW)
    location:        Optional[Any] = None
    date_of_birth:   Optional[str] = None


# ─────────────────────────────────────────────────────────────
# Direct Send  (chat inbox → WABIS /api/v1/whatsapp/send)
# ─────────────────────────────────────────────────────────────

class WaSendDirectRequest(BaseModel):
    """Send a plain-text or media message directly to a phone number via WABIS API."""
    phone_number: str                        # e.g. "919876543210"
    message_text: str                        # text to send (or caption for media)
    message:      Optional[str] = None       # fallback for message_text (deprecated)
    message_type: str = "text"               # "text", "image", "document", "voice_note"
    media_url:    Optional[str] = None       # base64 or URL for media files
    lead_id:      Optional[UUID] = None      # optional — to log as lead activity
    customer_id:  Optional[UUID] = None      # optional — to link to customer

    class Config:
        json_schema_extra = {
            "example": {
                "phone_number": "919876543210",
                "message_text": "Hello! This is a test message",
                "message_type": "text",
                "lead_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class WaSendDirectResponse(BaseModel):
    success:           bool
    message:           str
    wa_message_id:     Optional[str] = None
    subscriber_id:     Optional[str] = None
    raw_response:      Optional[Any] = None


# ─────────────────────────────────────────────────────────────
# Trigger Bot Flow
# ─────────────────────────────────────────────────────────────

class WaTriggerBotRequest(BaseModel):
    """Trigger a WABIS bot flow for a specific phone number."""
    phone_number:      str    # E.164 without + e.g. "919876543210"
    bot_flow_unique_id: str   # from WABIS bot flow settings

    # Some WABIS versions wrap differently — keep raw fallback
    model_config = {"extra": "allow"}
