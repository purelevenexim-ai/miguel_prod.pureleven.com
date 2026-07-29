"""Add message automation header media urls

Revision ID: z1a2b3c4d5e6
Revises: y7z8a9b0c1d2
Create Date: 2026-05-23 16:15:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "z1a2b3c4d5e6"
down_revision = "y7z8a9b0c1d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "message_automation_settings",
        sa.Column("template_header_media_urls", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("message_automation_settings", "template_header_media_urls")