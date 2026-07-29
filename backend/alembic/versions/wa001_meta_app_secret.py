"""Add meta_app_secret to wa_settings for webhook signature verification

Revision ID: wa001_meta_app_secret
Revises: rtg001_customer_retarget
Create Date: 2026-07-29 11:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "wa001_meta_app_secret"
down_revision = "rtg001_customer_retarget"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "wa_settings",
        sa.Column("meta_app_secret", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("wa_settings", "meta_app_secret")
