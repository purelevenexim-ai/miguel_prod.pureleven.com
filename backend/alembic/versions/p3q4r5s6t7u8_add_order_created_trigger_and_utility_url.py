"""Add order_created to watriggerevent enum and utility_workflow_url to wa_campaign_types

Revision ID: p3q4r5s6t7u8
Revises: o2p3q4r5s6t7
Create Date: 2026-02-23 05:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "p3q4r5s6t7u8"
down_revision: Union[str, Sequence[str], None] = "o2p3q4r5s6t7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add the new enum value 'order_created' to watriggerevent
    #    PostgreSQL requires ALTER TYPE … ADD VALUE (cannot be done inside a transaction block)
    op.execute("ALTER TYPE watriggerevent ADD VALUE IF NOT EXISTS 'order_created'")

    # 2. Add utility_workflow_url column to wa_campaign_types
    op.add_column(
        "wa_campaign_types",
        sa.Column("utility_workflow_url", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    # Dropping an enum value in PostgreSQL is not directly supported;
    # just drop the column to reverse the column addition.
    op.drop_column("wa_campaign_types", "utility_workflow_url")
    # Note: 'order_created' enum value cannot be removed from the type
    # without recreating the enum — left in place for safety.
