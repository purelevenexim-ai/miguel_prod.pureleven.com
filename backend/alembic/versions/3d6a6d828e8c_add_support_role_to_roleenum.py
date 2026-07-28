"""add_support_role_to_roleenum

Revision ID: 3d6a6d828e8c
Revises: d95234c14e2b
Create Date: 2026-02-20 13:37:12.492781

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3d6a6d828e8c'
down_revision: Union[str, Sequence[str], None] = 'd95234c14e2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add 'support' value to roleenum in PostgreSQL."""
    op.execute("ALTER TYPE roleenum ADD VALUE IF NOT EXISTS 'support'")


def downgrade() -> None:
    """
    PostgreSQL does not support removing enum values directly.
    To downgrade, the enum must be recreated — handle manually if needed.
    """
    pass
