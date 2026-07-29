"""add courier material cost to pc period snapshots

Revision ID: r1s2t3u4v5w6
Revises: q0r1s2t3u4v5
Create Date: 2026-05-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "r1s2t3u4v5w6"
down_revision = "q0r1s2t3u4v5"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    if not _column_exists("pc_period_snapshots", "courier_material_cost"):
        op.add_column(
            "pc_period_snapshots",
            sa.Column("courier_material_cost", sa.Numeric(14, 2), nullable=False, server_default="0"),
        )
        op.alter_column("pc_period_snapshots", "courier_material_cost", server_default=None)


def downgrade() -> None:
    if _column_exists("pc_period_snapshots", "courier_material_cost"):
        op.drop_column("pc_period_snapshots", "courier_material_cost")