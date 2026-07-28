"""add contacted_popup, recovery_campaign, message_received to leadactivitytype enum

Revision ID: x1y2z3a4b5c6
Revises: w0x1y2z3a4b5
Create Date: 2026-03-03
"""
from alembic import op

# revision identifiers
revision = 'x1y2z3a4b5c6'
down_revision = 'w0x1y2z3a4b5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL enum values cannot be removed once added,
    # so IF NOT EXISTS guards are used for idempotency.
    op.execute("ALTER TYPE leadactivitytype ADD VALUE IF NOT EXISTS 'contacted_popup'")
    op.execute("ALTER TYPE leadactivitytype ADD VALUE IF NOT EXISTS 'recovery_campaign'")
    op.execute("ALTER TYPE leadactivitytype ADD VALUE IF NOT EXISTS 'message_received'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values.
    # To truly downgrade, you'd need to recreate the type.
    pass
