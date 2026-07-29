"""add_error_code_to_activity_logs

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-21 00:00:00.000000

Adds error_code column for diagnostic error tracking.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('activity_logs', sa.Column('error_code', sa.String(50), nullable=True))
    op.create_index('ix_actlog_error_code', 'activity_logs', ['error_code'])


def downgrade() -> None:
    op.drop_index('ix_actlog_error_code', table_name='activity_logs')
    op.drop_column('activity_logs', 'error_code')
