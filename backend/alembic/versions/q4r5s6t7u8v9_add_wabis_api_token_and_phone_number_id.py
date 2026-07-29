"""add wabis_api_token and wabis_phone_number_id to wa_settings

Revision ID: q4r5s6t7u8v9
Revises: p3q4r5s6t7u8
Create Date: 2026-02-23

Adds:
  - wabis_phone_number_id  (String 100)  — WhatsApp phone_number_id for WABIS /api/v1/ send
  - wabis_api_token        (Text)        — WABIS developer apiToken for /api/v1/* endpoints
"""

from alembic import op
import sqlalchemy as sa

revision = 'q4r5s6t7u8v9'
down_revision = 'p3q4r5s6t7u8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "wa_settings",
        sa.Column("wabis_phone_number_id", sa.String(100), nullable=True,
                  comment="WhatsApp phone_number_id from WABIS account settings"),
    )
    op.add_column(
        "wa_settings",
        sa.Column("wabis_api_token", sa.Text(), nullable=True,
                  comment="WABIS developer apiToken for /api/v1/* endpoints"),
    )


def downgrade() -> None:
    op.drop_column("wa_settings", "wabis_api_token")
    op.drop_column("wa_settings", "wabis_phone_number_id")
