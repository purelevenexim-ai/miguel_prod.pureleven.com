"""Merge ml_pack branch and leads phase1+2 branch

Revision ID: i6h7i8j9k0l1
Revises: a3b4c5d6e7f8, h5g6c7d8e9f0
Create Date: 2026-02-22 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'i6h7i8j9k0l1'
down_revision: Union[str, Sequence[str], None] = ('a3b4c5d6e7f8', 'h5g6c7d8e9f0')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge migration — no schema changes."""
    pass


def downgrade() -> None:
    """Merge migration — no schema changes."""
    pass
