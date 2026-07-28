"""leads_redesign_create_lead_messages - Create lead_messages table for WhatsApp history

Revision ID: g4f5b6c7d8e9
Revises: f3e4a5b6c7d8
Create Date: 2026-02-21 10:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'g4f5b6c7d8e9'
down_revision: Union[str, Sequence[str], None] = 'f3e4a5b6c7d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Create lead_messages table"""
    
    op.create_table('lead_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('direction', sa.String(20), nullable=False),  # 'inbound', 'outbound'
        sa.Column('message_body', sa.Text(), nullable=False),
        sa.Column('whatsapp_message_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add indexes for performance
    op.create_index('ix_lead_messages_lead_id', 'lead_messages', ['lead_id'])
    op.create_index('ix_lead_messages_lead_direction', 'lead_messages', ['lead_id', 'direction'])
    op.create_index('ix_lead_messages_created_at', 'lead_messages', ['created_at'])
    op.create_index('ix_lead_messages_tenant_id', 'lead_messages', ['tenant_id'])


def downgrade() -> None:
    """Downgrade schema - Drop lead_messages table"""
    
    op.drop_index('ix_lead_messages_tenant_id', 'lead_messages')
    op.drop_index('ix_lead_messages_created_at', 'lead_messages')
    op.drop_index('ix_lead_messages_lead_direction', 'lead_messages')
    op.drop_index('ix_lead_messages_lead_id', 'lead_messages')
    op.drop_table('lead_messages')
