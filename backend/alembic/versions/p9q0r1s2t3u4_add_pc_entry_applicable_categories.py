"""add applicable categories to profit checker entries

Revision ID: p9q0r1s2t3u4
Revises: c3d4e5f6g7h8
Create Date: 2026-05-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "p9q0r1s2t3u4"
down_revision = "c3d4e5f6g7h8"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    if not _column_exists("pc_entries", "applicable_categories"):
        op.add_column(
            "pc_entries",
            sa.Column("applicable_categories", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )


def downgrade() -> None:
    if _column_exists("pc_entries", "applicable_categories"):
        op.drop_column("pc_entries", "applicable_categories")