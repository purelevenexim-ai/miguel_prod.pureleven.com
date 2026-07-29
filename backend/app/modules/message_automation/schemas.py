from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MessageAutomationSettingsUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    website_url: Optional[str] = None
    google_review_url: Optional[str] = None
    business_whatsapp_phone: Optional[str] = None
    meta_template_asset_id: Optional[str] = None
    template_bindings: Optional[dict[str, Optional[str]]] = None
    template_header_media_urls: Optional[dict[str, Optional[str]]] = None


class MessageAutomationSettingsResponse(BaseModel):
    id: str
    tenant_id: str
    is_enabled: bool
    website_url: str
    google_review_url: str
    business_whatsapp_phone: str
    meta_template_asset_id: Optional[str] = None
    template_bindings: dict[str, Optional[str]] = Field(default_factory=dict)
    template_header_media_urls: dict[str, Optional[str]] = Field(default_factory=dict)
    whatsapp_link: str
    review_campaign_started_at: Optional[str] = None
    updated_at: Optional[str] = None


class AvailableWhatsAppTemplateResponse(BaseModel):
    name: str
    status: str
    category: Optional[str] = None
    language: Optional[str] = None
    source: str
    app_visible: bool = False
    has_media_header: bool = False
    header_format: Optional[str] = None
    parameter_format: str = "NONE"
    body_parameters: list[str] = Field(default_factory=list)
    button_parameters: list[str] = Field(default_factory=list)
    template_health: str = "ok"
    template_health_summary: Optional[str] = None
    template_health_warnings: list[str] = Field(default_factory=list)


class OrderWhatsAppLogResponse(BaseModel):
    id: str
    order_id: Optional[str] = None
    order_number: Optional[str] = None
    order_status: Optional[str] = None
    channel: str
    template_key: str
    event_type: str
    status: str
    recipient_name: Optional[str] = None
    recipient_phone_e164: Optional[str] = None
    provider_message_id: Optional[str] = None
    provider_template_name: Optional[str] = None
    scheduled_at: Optional[str] = None
    sent_at: Optional[str] = None
    created_at: Optional[str] = None
    attempts: int = 0
    duplicate_count: int = 1
    status_label: str
    status_detail: Optional[str] = None
    action_required: bool = False
    error_reason: Optional[str] = None
    issue_summary: Optional[str] = None


class CustomerMessageCancelRequest(BaseModel):
    customer_id: Optional[UUID] = None
    phone: Optional[str] = None
    whatsapp: bool = True
    email: bool = True
    reason: Optional[str] = None


class CustomerMessageResumeRequest(BaseModel):
    customer_id: Optional[UUID] = None
    phone: Optional[str] = None


class BootstrapExistingCustomersRequest(BaseModel):
    include_phones: list[str] = Field(default_factory=list)
    process_now: bool = False
    process_limit: int = 500


class ProcessDueRequest(BaseModel):
    limit: int = Field(default=100, ge=1, le=2000)


class ReleaseTasksRequest(BaseModel):
    template_keys: list[str] = Field(default_factory=list)
    statuses: list[str] = Field(default_factory=lambda: ["pending", "failed"])
    release_pending_only: bool = False


class RetryOrderWhatsAppTaskRequest(BaseModel):
    template_key: str


class RetryPendingOrderWhatsAppTasksRequest(BaseModel):
    days: int = Field(default=7, ge=1, le=30)
    limit: int = Field(default=200, ge=1, le=500)
    template_keys: list[str] = Field(default_factory=list)
    task_ids: list[UUID] = Field(default_factory=list)


class HistoricalReviewRequestBatchRequest(BaseModel):
    older_than_days: int = Field(default=7, ge=7, le=365)
    batch_limit: int = Field(default=50, ge=1, le=200)
    resume_cursor: Optional[str] = None
    confirmation_phrase: Optional[str] = None


class MetaTemplatePayloadResponse(BaseModel):
    template_key: str
    template_name: str
    category: str
    language: str
    parameter_format: str
    components: list[dict[str, Any]]
    sample_variables: dict[str, Any] = Field(default_factory=dict)


class MessageTaskResponse(BaseModel):
    id: str
    tenant_id: str
    customer_id: Optional[str]
    order_id: Optional[str]
    channel: str
    template_key: str
    event_type: str
    status: str
    recipient_phone_e164: Optional[str]
    recipient_email: Optional[str]
    recipient_name: Optional[str]
    subject: Optional[str]
    scheduled_at: Optional[str]
    sent_at: Optional[str]
    attempts: int
    error_reason: Optional[str]


class TemplateResponse(BaseModel):
    key: str
    channel: str
    title: str
    category: str
    subject: Optional[str]
    body: str
    meta_template_name: Optional[str]
    meta_category: Optional[str]
    language: str


class GenericAutomationResponse(BaseModel):
    success: bool
    details: dict[str, Any] = Field(default_factory=dict)
