"""leads_redesign_phase1_schema - Add new fields for Leads redesign

Revision ID: f3e4a5b6c7d8
Revises: f2a3b4c5d6e7
Create Date: 2026-02-21 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f3e4a5b6c7d8'
down_revision: Union[str, Sequence[str], None] = 'f2a3b4c5d6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add fields for Leads redesign"""
    
    # Add new columns to leads table
    op.add_column('leads', 
        sa.Column('remind_date', sa.Date(), nullable=True)
    )
    op.add_column('leads',
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.add_column('leads',
        sa.Column('contacted_count', sa.Integer(), nullable=False, server_default='0')
    )
    op.add_column('leads',
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false')
    )
    op.add_column('leads',
        sa.Column('note_last', sa.Text(), nullable=True)
    )
    
    # Add foreign key constraint for order_id
    op.create_foreign_key(
        'fk_leads_order_id',
        'leads', 'orders',
        ['order_id'], ['id']
    )
    
    # Add indexes for performance
    op.create_index('ix_leads_remind_date', 'leads', ['remind_date'])
    op.create_index('ix_leads_is_archived', 'leads', ['is_archived'])
    op.create_index('ix_leads_order_id', 'leads', ['order_id'])
    op.create_index('ix_leads_status_remind', 'leads', ['status', 'remind_date'])


def downgrade() -> None:
    """Downgrade schema - Remove new fields"""
    
    # Drop indexes
    op.drop_index('ix_leads_status_remind', 'leads')
    op.drop_index('ix_leads_order_id', 'leads')
    op.drop_index('ix_leads_is_archived', 'leads')
    op.drop_index('ix_leads_remind_date', 'leads')
    
    # Drop foreign key
    op.drop_constraint('fk_leads_order_id', 'leads', type_='foreignkey')
    
    # Drop columns
    op.drop_column('leads', 'note_last')
    op.drop_column('leads', 'is_archived')
    op.drop_column('leads', 'contacted_count')
    op.drop_column('leads', 'order_id')
    op.drop_column('leads', 'remind_date')
