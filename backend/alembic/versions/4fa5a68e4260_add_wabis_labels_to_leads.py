"""add_wabis_labels_to_leads

Revision ID: 4fa5a68e4260
Revises: t7u8v9w0x1y2
Create Date: 2026-02-23 13:55:15.735193

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4fa5a68e4260'
down_revision: Union[str, Sequence[str], None] = 't7u8v9w0x1y2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('leads', sa.Column('wabis_labels', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('leads', 'wabis_labels')
