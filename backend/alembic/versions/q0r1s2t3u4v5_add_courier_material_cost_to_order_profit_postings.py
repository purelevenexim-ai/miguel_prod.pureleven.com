"""add courier material cost to order profit postings

Revision ID: q0r1s2t3u4v5
Revises: p9q0r1s2t3u4
Create Date: 2026-05-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "q0r1s2t3u4v5"
down_revision = "p9q0r1s2t3u4"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    if not _column_exists("order_profit_postings", "courier_material_cost"):
        op.add_column(
            "order_profit_postings",
            sa.Column("courier_material_cost", sa.Numeric(12, 2), nullable=False, server_default="0"),
        )
        op.alter_column("order_profit_postings", "courier_material_cost", server_default=None)


def downgrade() -> None:
    if _column_exists("order_profit_postings", "courier_material_cost"):
        op.drop_column("order_profit_postings", "courier_material_cost")