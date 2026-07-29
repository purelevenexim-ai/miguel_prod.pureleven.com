"""Add message automation template bindings and Meta asset id

Revision ID: y7z8a9b0c1d2
Revises: v1w2x3y4z5a6
Create Date: 2026-05-23
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "y7z8a9b0c1d2"
down_revision = "v1w2x3y4z5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "message_automation_settings",
        sa.Column("meta_template_asset_id", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "message_automation_settings",
        sa.Column("template_bindings", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("message_automation_settings", "template_bindings")
    op.drop_column("message_automation_settings", "meta_template_asset_id")