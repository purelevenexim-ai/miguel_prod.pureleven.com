"""Add new enum values to leadpipelinestatus

Revision ID: j7k8l9m0n1o2
Revises: i6h7i8j9k0l1
Create Date: 2026-02-22 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'j7k8l9m0n1o2'
down_revision: Union[str, Sequence[str], None] = 'i6h7i8j9k0l1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add new pipeline status values to the leadpipelinestatus enum."""
    # PostgreSQL ALTER TYPE ADD VALUE must be run outside a transaction block.
    # We use op.execute with autocommit connection.
    conn = op.get_bind()

    # Helper: check if value already exists before adding
    def add_enum_value_if_missing(enum_name: str, value: str) -> None:
        result = conn.execute(
            sa.text(
                "SELECT 1 FROM pg_enum "
                "JOIN pg_type ON pg_enum.enumtypid = pg_type.oid "
                "WHERE pg_type.typname = :etype AND pg_enum.enumlabel = :eval"
            ),
            {"etype": enum_name, "eval": value}
        ).fetchone()
        if result is None:
            # Must be committed before next ADD VALUE in same session
            conn.execute(sa.text(f"ALTER TYPE {enum_name} ADD VALUE '{value}'"))

    add_enum_value_if_missing('leadpipelinestatus', 'new_lead')
    add_enum_value_if_missing('leadpipelinestatus', 'created')
    add_enum_value_if_missing('leadpipelinestatus', 'success')
    add_enum_value_if_missing('leadpipelinestatus', 'not_interested')
    add_enum_value_if_missing('leadpipelinestatus', 'follow_up')


def downgrade() -> None:
    """Cannot remove enum values in PostgreSQL without recreating the type.
    This downgrade is intentionally a no-op for safety.
    """
    pass
