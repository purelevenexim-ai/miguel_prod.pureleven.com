"""Add customer message automation tables

Revision ID: v1w2x3y4z5a6
Revises: u1v2w3x4y5z6
Create Date: 2026-05-23
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "v1w2x3y4z5a6"
down_revision = "u1v2w3x4y5z6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "message_automation_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("website_url", sa.String(length=500), nullable=True),
        sa.Column("google_review_url", sa.Text(), nullable=True),
        sa.Column("business_whatsapp_phone", sa.String(length=30), nullable=True),
        sa.Column("review_campaign_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.UniqueConstraint("tenant_id", name="uq_message_automation_settings_tenant"),
    )
    op.create_index("ix_message_automation_settings_tenant", "message_automation_settings", ["tenant_id"])

    op.create_table(
        "customer_message_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("phone_e164", sa.String(length=30), nullable=False),
        sa.Column("whatsapp_opted_out", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("email_opted_out", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("automation_paused", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("pause_reason", sa.Text(), nullable=True),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.UniqueConstraint("tenant_id", "phone_e164", name="uq_customer_message_pref_tenant_phone"),
    )
    op.create_index("ix_customer_message_pref_tenant", "customer_message_preferences", ["tenant_id"])
    op.create_index("ix_customer_message_pref_customer", "customer_message_preferences", ["customer_id"])
    op.create_index("ix_customer_message_pref_phone", "customer_message_preferences", ["phone_e164"])

    op.create_table(
        "message_automation_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("template_key", sa.String(length=80), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("recipient_phone_e164", sa.String(length=30), nullable=True),
        sa.Column("recipient_email", sa.String(length=255), nullable=True),
        sa.Column("recipient_name", sa.String(length=255), nullable=True),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("dedupe_key", sa.String(length=255), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("provider_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.UniqueConstraint("tenant_id", "dedupe_key", name="uq_message_task_tenant_dedupe"),
    )
    op.create_index("ix_message_task_due", "message_automation_tasks", ["status", "scheduled_at"])
    op.create_index("ix_message_task_tenant", "message_automation_tasks", ["tenant_id"])
    op.create_index("ix_message_task_customer", "message_automation_tasks", ["customer_id"])
    op.create_index("ix_message_task_order", "message_automation_tasks", ["order_id"])
    op.create_index("ix_message_task_template", "message_automation_tasks", ["template_key"])


def downgrade() -> None:
    op.drop_index("ix_message_task_template", table_name="message_automation_tasks")
    op.drop_index("ix_message_task_order", table_name="message_automation_tasks")
    op.drop_index("ix_message_task_customer", table_name="message_automation_tasks")
    op.drop_index("ix_message_task_tenant", table_name="message_automation_tasks")
    op.drop_index("ix_message_task_due", table_name="message_automation_tasks")
    op.drop_table("message_automation_tasks")

    op.drop_index("ix_customer_message_pref_phone", table_name="customer_message_preferences")
    op.drop_index("ix_customer_message_pref_customer", table_name="customer_message_preferences")
    op.drop_index("ix_customer_message_pref_tenant", table_name="customer_message_preferences")
    op.drop_table("customer_message_preferences")

    op.drop_index("ix_message_automation_settings_tenant", table_name="message_automation_settings")
    op.drop_table("message_automation_settings")
