"""Add trigger_event column to wa_campaign_types

Revision ID: o2p3q4r5s6t7
Revises: n1o2p3q4r5s6
Create Date: 2026-02-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "o2p3q4r5s6t7"
down_revision: Union[str, Sequence[str], None] = "n1o2p3q4r5s6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the enum type first
    trigger_event_enum = sa.Enum(
        "manual", "order_confirmed", "order_packed", "order_shipped", "order_delivered",
        name="watriggerevent",
    )
    trigger_event_enum.create(op.get_bind(), checkfirst=True)

    # Add column with default 'manual'
    op.add_column(
        "wa_campaign_types",
        sa.Column(
            "trigger_event",
            trigger_event_enum,
            nullable=False,
            server_default="manual",
        ),
    )


def downgrade() -> None:
    op.drop_column("wa_campaign_types", "trigger_event")
    sa.Enum(name="watriggerevent").drop(op.get_bind(), checkfirst=True)
