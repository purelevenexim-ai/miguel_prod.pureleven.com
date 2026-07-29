"""Add wa_outbound_webhooks table

Revision ID: s6t7u8v9w0x1
Revises: r5s6t7u8v9w0
Create Date: 2026-02-23 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "s6t7u8v9w0x1"
down_revision = "r5s6t7u8v9w0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "wa_outbound_webhooks",
        sa.Column("id",             postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id",      postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name",           sa.String(255), nullable=False),
        sa.Column("url",            sa.Text,        nullable=False),
        sa.Column("is_active",      sa.Boolean,     nullable=False, server_default="true"),
        sa.Column("trigger_events", postgresql.JSONB, nullable=False,
                  server_default='["new_message","postback"]'),
        sa.Column("data_fields",    postgresql.JSONB, nullable=False,
                  server_default='["subscriber_id","name","phone","wabis_status","labels","postback_id"]'),
        sa.Column("postback_filter",postgresql.JSONB, nullable=True),
        sa.Column("secret",         sa.String(100), nullable=True),
        sa.Column("last_fired_at",  sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status_code", sa.Integer,  nullable=True),
        sa.Column("total_fired",    sa.Integer,     nullable=False, server_default="0"),
        sa.Column("total_failed",   sa.Integer,     nullable=False, server_default="0"),
        sa.Column("created_at",     sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at",     sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_wa_outbound_webhooks_tenant",
                    "wa_outbound_webhooks", ["tenant_id"])
    op.create_index("ix_wa_outbound_webhooks_active",
                    "wa_outbound_webhooks", ["tenant_id", "is_active"])


def downgrade():
    op.drop_index("ix_wa_outbound_webhooks_active",  table_name="wa_outbound_webhooks")
    op.drop_index("ix_wa_outbound_webhooks_tenant",  table_name="wa_outbound_webhooks")
    op.drop_table("wa_outbound_webhooks")
