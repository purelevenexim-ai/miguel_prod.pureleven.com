"""leads_phase2_whatsapp_api - Add whatsapp_message_id dedup index to lead_messages

Revision ID: h5g6c7d8e9f0
Revises: g4f5b6c7d8e9
Create Date: 2026-02-21 12:00:00.000000

Changes:
  - lead_messages: add index on whatsapp_message_id for fast dedup lookups
  - lead_messages: add index on (tenant_id, lead_id) composite for chat queries

No new tables. Phase 2 = application-only (WhatsApp API client + webhook handler).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'h5g6c7d8e9f0'
down_revision: Union[str, Sequence[str], None] = 'g4f5b6c7d8e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add dedup and composite indexes to lead_messages table."""

    # Dedup index: check if a message with this whatsapp_message_id was already stored
    op.create_index(
        'ix_lead_messages_whatsapp_id',
        'lead_messages',
        ['whatsapp_message_id'],
        postgresql_where=sa.text('whatsapp_message_id IS NOT NULL'),
    )

    # Composite index: tenant + lead for chat widget queries
    op.create_index(
        'ix_lead_messages_tenant_lead',
        'lead_messages',
        ['tenant_id', 'lead_id'],
    )


def downgrade() -> None:
    """Remove Phase 2 indexes from lead_messages."""
    op.drop_index('ix_lead_messages_tenant_lead', 'lead_messages')
    op.drop_index('ix_lead_messages_whatsapp_id', 'lead_messages')
