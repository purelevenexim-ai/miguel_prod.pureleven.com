"""
Meta Ads Integration Model
---------------------------
Stores per-tenant Meta (Facebook/Instagram) page integrations.
Each tenant admin registers one or more Meta pages.
When a lead arrives via webhook, it is matched to a tenant by page_id.
"""

import enum
import uuid
from sqlalchemy import (
    Column, String, Boolean, Text, DateTime,
    Enum, ForeignKey, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class MetaIntegration(Base):
    __tablename__ = "meta_integrations"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id    = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    # ── Meta Identifiers ─────────────────────────────────────
    page_id      = Column(String(100), nullable=False)    # Meta Page ID (numeric string)
    page_name    = Column(String(255), nullable=True)     # Human-readable label
    form_id      = Column(String(100), nullable=True)     # Specific form filter (optional)
    access_token = Column(Text, nullable=False)           # Page access token (long-lived)

    # ── Lead Assignment ──────────────────────────────────────
    # Which employee new Meta leads are assigned to (set by tenant admin)
    default_assignee_id = Column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True
    )

    # ── Status ───────────────────────────────────────────────
    is_active    = Column(Boolean, nullable=False, default=True)

    # ── Audit ────────────────────────────────────────────────
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # ── Relationships ────────────────────────────────────────
    default_assignee = relationship("Employee", foreign_keys=[default_assignee_id])

    __table_args__ = (
        # One page_id per tenant (a page can only be registered once per tenant)
        Index("ix_meta_integrations_tenant_id", "tenant_id"),
        Index("ix_meta_integrations_page_id", "page_id"),
    )


class MetaWebhookLog(Base):
    """
    Raw webhook event log — store every incoming Meta webhook payload.
    Useful for debugging duplicate events, replaying failed ingestions.
    """
    __tablename__ = "meta_webhook_logs"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id      = Column(String(100), nullable=True)
    leadgen_id   = Column(String(100), nullable=True)   # Meta's lead ID (dedup key)
    form_id      = Column(String(100), nullable=True)
    raw_payload  = Column(Text, nullable=True)           # Full JSON blob
    processed    = Column(Boolean, default=False)
    lead_id      = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)
    error        = Column(Text, nullable=True)
    received_at  = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_meta_webhook_logs_leadgen_id", "leadgen_id"),
        Index("ix_meta_webhook_logs_page_id", "page_id"),
    )
