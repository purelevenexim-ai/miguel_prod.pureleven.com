"""
WhatsApp Business — Pydantic Schemas
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, field_validator


# ─────────────────────────────────────────────────────────────
# Send Message
# ─────────────────────────────────────────────────────────────

class SendMessageRequest(BaseModel):
    lead_id: UUID
    message: str

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty")
        if len(v) > 4096:
            raise ValueError("Message must be 4096 characters or fewer")
        return v


class SendMessageResponse(BaseModel):
    model_config = {"from_attributes": True}

    success: bool
    message_id: Optional[str] = None
    wa_message_id: Optional[str] = None   # Meta's message ID
    error: Optional[str] = None


# ─────────────────────────────────────────────────────────────
# Config / Status
# ─────────────────────────────────────────────────────────────

class WhatsAppConfigResponse(BaseModel):
    is_configured: bool
    phone_number_id: Optional[str] = None   # Masked: shows last 4 digits only
    auto_reply_enabled: bool
    auto_reply_message: str
    api_version: str
    webhook_verify_token_set: bool


# ─────────────────────────────────────────────────────────────
# Webhook ingest result
# ─────────────────────────────────────────────────────────────

class WebhookIngestResult(BaseModel):
    messages_processed: int = 0
    leads_matched: int = 0
    leads_created: int = 0
    auto_replies_sent: int = 0
    errors: list[str] = []
