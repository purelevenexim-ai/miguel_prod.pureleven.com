"""merge_heads_before_shipping_config

Revision ID: 34b2c24ed0c6
Revises: 4fa5a68e4260, u8v9w0x1y2z3
Create Date: 2026-02-24 15:46:18.491198

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '34b2c24ed0c6'
down_revision: Union[str, Sequence[str], None] = ('4fa5a68e4260', 'u8v9w0x1y2z3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
