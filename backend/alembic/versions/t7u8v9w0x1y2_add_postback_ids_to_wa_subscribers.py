"""add postback_ids to wa_subscribers

Revision ID: t7u8v9w0x1y2
Revises: s6t7u8v9w0x1
Create Date: 2026-02-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = 't7u8v9w0x1y2'
down_revision = 's6t7u8v9w0x1'
branch_labels = None
depends_on = None


def upgrade():
    # Add postback_ids column (JSONB array of all postbacks ever seen)
    op.add_column(
        'wa_subscribers',
        sa.Column('postback_ids', JSONB, nullable=True),
    )
    # Back-fill: seed postback_ids from last_postback_id for existing rows
    op.execute("""
        UPDATE wa_subscribers
        SET postback_ids = CASE
            WHEN last_postback_id IS NOT NULL THEN jsonb_build_array(last_postback_id)
            ELSE '[]'::jsonb
        END
        WHERE postback_ids IS NULL
    """)


def downgrade():
    op.drop_column('wa_subscribers', 'postback_ids')
