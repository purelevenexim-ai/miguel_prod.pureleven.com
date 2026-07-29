"""Add WhatsApp Engine tables (wa_engine)

Revision ID: n1o2p3q4r5s6
Revises: m0n1o2p3q4r5
Create Date: 2026-02-25 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "n1o2p3q4r5s6"
down_revision = "m0n1o2p3q4r5"
branch_labels = None
depends_on = None

# ------------------------------------------------------------------
# Helpers — we manage PG enums with raw SQL (idempotent).
# All enum columns in create_table use sa.VARCHAR so SQLAlchemy
# never fires a CREATE TYPE event; PG enforces the type via the
# column type we set with ALTER COLUMN after table creation.
# ------------------------------------------------------------------

_ENUMS = {
    "waprovider":          ("wabis", "meta"),
    "wamessagedirection":  ("inbound", "outbound"),
    "wamessagetype":       ("text", "image", "document", "audio", "video", "template", "unknown"),
    "wamessagestatus":     ("pending", "sent", "delivered", "read", "failed"),
    "wapostbackaction":    ("create_lead", "update_status", "add_label", "ignore"),
    "wastatusenum": (
        "new_message", "replied", "follow_up", "no_response",
        "hot", "cold", "blocked", "converted",
        "order_confirmed", "order_packed", "order_shipped",
        "out_for_delivery", "delivered",
    ),
    "wacampaignstatus":  ("draft", "running", "completed", "failed", "cancelled"),
    "warecipientstatus": ("pending", "sent", "failed", "skipped"),
}

# (table, column, enum_type, server_default)
_ENUM_COLUMNS = [
    ("wa_settings",            "provider",                  "waprovider",         "wabis"),
    ("wa_postback_rules",      "action",                    "wapostbackaction",    "create_lead"),
    ("wa_conversations",       "last_message_direction",    "wamessagedirection",  None),
    ("wa_messages",            "direction",                 "wamessagedirection",  None),
    ("wa_messages",            "message_type",              "wamessagetype",       "text"),
    ("wa_messages",            "status",                    "wamessagestatus",     "pending"),
    ("wa_status",              "status",                    "wastatusenum",        "new_message"),
    ("wa_status_history",      "old_status",                "wastatusenum",        None),
    ("wa_status_history",      "new_status",                "wastatusenum",        None),
    ("wa_campaigns",           "status",                    "wacampaignstatus",    "draft"),
    ("wa_campaign_recipients", "status",                    "warecipientstatus",   "pending"),
]


def _create_enums():
    for name, values in _ENUMS.items():
        vals = ", ".join(f"'{v}'" for v in values)
        op.execute(
            f"DO $$ BEGIN "
            f"  CREATE TYPE {name} AS ENUM ({vals}); "
            f"EXCEPTION WHEN duplicate_object THEN null; END $$;"
        )


def _cast_enum_columns():
    """ALTER each String column to its proper PG enum type.
    Must DROP DEFAULT first, ALTER TYPE, then re-apply DEFAULT.
    """
    for table, col, enum_type, default in _ENUM_COLUMNS:
        # 1. drop existing default (if any) so ALTER TYPE succeeds
        op.execute(f'ALTER TABLE {table} ALTER COLUMN "{col}" DROP DEFAULT;')
        # 2. cast to enum
        using = f'"{col}"::text::{enum_type}'
        op.execute(
            f'ALTER TABLE {table} ALTER COLUMN "{col}" TYPE {enum_type} USING {using};'
        )
        # 3. restore default
        if default is not None:
            op.execute(
                f"ALTER TABLE {table} ALTER COLUMN \"{col}\" SET DEFAULT '{default}'::{enum_type};"
            )


def _drop_enums():
    for name in reversed(list(_ENUMS)):
        op.execute(f"DROP TYPE IF EXISTS {name} CASCADE")


def upgrade() -> None:
    _create_enums()

    # All enum columns declared as String/Text; after tables are created
    # we ALTER COLUMN to cast them to the proper enum type.

    op.create_table(
        "wa_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("provider", sa.String(20), nullable=False, server_default="wabis"),
        sa.Column("display_name", sa.String(120)),
        sa.Column("phone_number", sa.String(30)),
        sa.Column("wabis_bot_id", sa.String(120)),
        sa.Column("wabis_access_token", sa.Text),
        sa.Column("wabis_api_base_url", sa.String(255), server_default="https://admin.workpex.com"),
        sa.Column("meta_phone_number_id", sa.String(120)),
        sa.Column("meta_access_token", sa.Text),
        sa.Column("meta_api_version", sa.String(20), server_default="v19.0"),
        sa.Column("meta_webhook_verify_token", sa.String(120)),
        sa.Column("inbound_secret", sa.String(64), nullable=False,
                  server_default=sa.text("gen_random_uuid()::text")),
        sa.Column("auto_reply_enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("auto_reply_message", sa.Text),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True)),
    )

    op.create_table(
        "wa_postback_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("postback_id", sa.String(120), nullable=False),
        sa.Column("display_name", sa.String(255)),
        sa.Column("action", sa.String(30), nullable=False, server_default="create_lead"),
        sa.Column("lead_source", sa.String(120), server_default="wabis"),
        sa.Column("lead_label", sa.String(120)),
        sa.Column("lead_status", sa.String(120), server_default="new_lead"),
        sa.Column("lead_priority", sa.String(60), server_default="medium"),
        sa.Column("extra_config", postgresql.JSONB),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True)),
        sa.UniqueConstraint("tenant_id", "postback_id", name="uq_wa_postback_tenant"),
    )
    op.create_index("ix_wa_postback_rules_tenant", "wa_postback_rules", ["tenant_id"])

    op.create_table(
        "wa_campaign_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("icon", sa.String(20)),
        sa.Column("category", sa.String(60)),
        sa.Column("wabis_workflow_url", sa.Text),
        sa.Column("payload_template", postgresql.JSONB),
        sa.Column("meta_template_name", sa.String(120)),
        sa.Column("meta_template_lang", sa.String(20), server_default="en"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_by_employee_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("employees.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True)),
    )
    op.create_index("ix_wa_campaign_types_tenant", "wa_campaign_types", ["tenant_id"])

    op.create_table(
        "wa_subscribers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subscriber_id", sa.String(120), nullable=False),
        sa.Column("phone_number", sa.String(30), nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("wabis_labels", postgresql.JSONB),
        sa.Column("last_postback_id", sa.String(120)),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("leads.id", ondelete="SET NULL")),
        sa.Column("is_opted_out", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("first_seen_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("last_seen_at", sa.TIMESTAMP(timezone=True)),
        sa.UniqueConstraint("tenant_id", "subscriber_id", name="uq_wa_subscriber_tenant"),
    )
    op.create_index("ix_wa_subscribers_tenant", "wa_subscribers", ["tenant_id"])
    op.create_index("ix_wa_subscribers_phone",  "wa_subscribers", ["phone_number"])
    op.create_index("ix_wa_subscribers_lead",   "wa_subscribers", ["lead_id"])

    op.create_table(
        "wa_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subscriber_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("wa_subscribers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("leads.id", ondelete="SET NULL")),
        sa.Column("last_message_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("last_message_direction", sa.String(10)),
        sa.Column("unread_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "subscriber_id", name="uq_wa_conversation_tenant"),
    )
    op.create_index("ix_wa_conversations_tenant",   "wa_conversations", ["tenant_id"])
    op.create_index("ix_wa_conversations_last_msg", "wa_conversations", ["last_message_at"])

    op.create_table(
        "wa_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("wa_conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_message_id", sa.String(255)),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("message_type", sa.String(20), nullable=False, server_default="text"),
        sa.Column("content", sa.Text),
        sa.Column("media_url", sa.Text),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("sent_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("delivered_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("read_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("failed_reason", sa.Text),
        sa.Column("sent_by_employee_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("employees.id", ondelete="SET NULL")),
        sa.Column("raw_payload", postgresql.JSONB),
    )
    op.create_index("ix_wa_messages_conv",   "wa_messages", ["conversation_id"])
    op.create_index("ix_wa_messages_tenant", "wa_messages", ["tenant_id"])
    op.create_index("ix_wa_messages_sent",   "wa_messages", ["sent_at"])

    op.create_table(
        "wa_status",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subscriber_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("wa_subscribers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("leads.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(30), nullable=False, server_default="new_message"),
        sa.Column("assigned_to_employee_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("employees.id", ondelete="SET NULL")),
        sa.Column("note", sa.Text),
        sa.Column("updated_by_employee_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("employees.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True)),
        sa.UniqueConstraint("tenant_id", "subscriber_id", name="uq_wa_status_tenant"),
    )
    op.create_index("ix_wa_status_tenant", "wa_status", ["tenant_id"])
    op.create_index("ix_wa_status_lead",   "wa_status", ["lead_id"])

    op.create_table(
        "wa_status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("wa_status_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("wa_status.id", ondelete="CASCADE"), nullable=False),
        sa.Column("old_status", sa.String(30)),
        sa.Column("new_status", sa.String(30), nullable=False),
        sa.Column("changed_by_employee_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("employees.id", ondelete="SET NULL")),
        sa.Column("note", sa.Text),
        sa.Column("changed_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_wa_status_history_status_id", "wa_status_history", ["wa_status_id"])
    op.create_index("ix_wa_status_history_tenant",    "wa_status_history", ["tenant_id"])

    op.create_table(
        "wa_campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("campaign_type_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("wa_campaign_types.id", ondelete="SET NULL")),
        sa.Column("audience_filter", postgresql.JSONB),
        sa.Column("workflow_url_override", sa.Text),
        sa.Column("payload_template_override", postgresql.JSONB),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("total_recipients", sa.Integer, nullable=False, server_default="0"),
        sa.Column("sent_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("scheduled_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_by_employee_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("employees.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True)),
    )
    op.create_index("ix_wa_campaigns_tenant", "wa_campaigns", ["tenant_id"])
    op.create_index("ix_wa_campaigns_status", "wa_campaigns", ["status"])

    op.create_table(
        "wa_campaign_recipients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("wa_campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subscriber_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("wa_subscribers.id", ondelete="SET NULL")),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("leads.id", ondelete="SET NULL")),
        sa.Column("wa_phone", sa.String(30), nullable=False),
        sa.Column("contact_name", sa.String(255)),
        sa.Column("payload_sent", postgresql.JSONB),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("provider_response", postgresql.JSONB),
        sa.Column("error_reason", sa.Text),
        sa.Column("sent_at", sa.TIMESTAMP(timezone=True)),
    )
    op.create_index("ix_wa_campaign_recipients_campaign", "wa_campaign_recipients", ["campaign_id"])
    op.create_index("ix_wa_campaign_recipients_tenant",   "wa_campaign_recipients", ["tenant_id"])
    op.create_index("ix_wa_campaign_recipients_status",   "wa_campaign_recipients", ["status"])

    # Now cast all String columns to their proper PG enum types
    _cast_enum_columns()


def downgrade() -> None:
    op.drop_table("wa_campaign_recipients")
    op.drop_table("wa_campaigns")
    op.drop_table("wa_status_history")
    op.drop_table("wa_status")
    op.drop_table("wa_messages")
    op.drop_table("wa_conversations")
    op.drop_table("wa_subscribers")
    op.drop_table("wa_campaign_types")
    op.drop_table("wa_postback_rules")
    op.drop_table("wa_settings")
    _drop_enums()
