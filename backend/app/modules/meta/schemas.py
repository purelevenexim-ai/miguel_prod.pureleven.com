"""
Meta Ads — Schemas
-------------------
Request/response shapes for the Meta Ads Integration module.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


# ─────────────────────────────────────────────────────────────
# Integration CRUD
# ─────────────────────────────────────────────────────────────

class MetaIntegrationCreate(BaseModel):
    page_id:             str
    page_name:           Optional[str] = None
    form_id:             Optional[str] = None
    access_token:        str
    default_assignee_id: Optional[UUID] = None
    is_active:           bool = True

    @field_validator("page_id")
    @classmethod
    def page_id_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("page_id cannot be blank")
        return v.strip()

    @field_validator("access_token")
    @classmethod
    def token_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("access_token cannot be blank")
        return v.strip()


class MetaIntegrationUpdate(BaseModel):
    page_name:           Optional[str]  = None
    form_id:             Optional[str]  = None
    access_token:        Optional[str]  = None
    default_assignee_id: Optional[UUID] = None
    is_active:           Optional[bool] = None


class MetaIntegrationResponse(BaseModel):
    model_config = {"from_attributes": True}

    id:                  UUID
    tenant_id:           UUID
    page_id:             str
    page_name:           Optional[str]
    form_id:             Optional[str]
    # Never expose access_token in responses
    default_assignee_id: Optional[UUID]
    is_active:           bool
    created_at:          datetime
    updated_at:          Optional[datetime]


# ─────────────────────────────────────────────────────────────
# Webhook
# ─────────────────────────────────────────────────────────────

class WebhookVerifyParams(BaseModel):
    """Query params Meta sends for hub challenge verification."""
    hub_mode:      str
    hub_challenge: str
    hub_verify_token: str


class MetaLeadField(BaseModel):
    """One field from a Meta lead gen form submission."""
    name:  str
    values: list[str]


class MetaLeadValue(BaseModel):
    """Parsed lead value (field_data from Meta payload)."""
    field_data: list[MetaLeadField]
    leadgen_id: str
    created_time: Optional[int] = None
    form_id:      Optional[str] = None
    page_id:      Optional[str] = None
    ad_id:        Optional[str] = None
    adset_id:     Optional[str] = None


class MetaWebhookEntry(BaseModel):
    id:      str           # page id
    changes: list[dict]


class MetaWebhookPayload(BaseModel):
    object: str
    entry:  list[MetaWebhookEntry]


# ─────────────────────────────────────────────────────────────
# Webhook Log
# ─────────────────────────────────────────────────────────────

class WebhookLogResponse(BaseModel):
    model_config = {"from_attributes": True}

    id:          UUID
    page_id:     Optional[str]
    leadgen_id:  Optional[str]
    form_id:     Optional[str]
    processed:   bool
    lead_id:     Optional[UUID]
    error:       Optional[str]
    received_at: datetime
