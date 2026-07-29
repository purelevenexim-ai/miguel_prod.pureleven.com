"""merge variation_attributes and taxonomy heads

Revision ID: e6395f592ebb
Revises: d4e5f6a7b8c9, t1u2v3w4x5y6
Create Date: 2026-05-02 14:39:21.346774

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6395f592ebb'
down_revision: Union[str, Sequence[str], None] = ('d4e5f6a7b8c9', 't1u2v3w4x5y6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
