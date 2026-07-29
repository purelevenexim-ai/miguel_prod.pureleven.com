"""Add message tracking table (defer table renames to future migration)

Revision ID: r5s6t7u8v9w0
Revises: q4r5s6t7u8v9
Create Date: 2026-02-23

Changes:
  - Create whatsapp_api_message_log table for tracking sent messages
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'r5s6t7u8v9w0'
down_revision = 'q4r5s6t7u8v9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create whatsapp_api_message_log table for message tracking
    op.create_table(
        'whatsapp_api_message_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subscriber_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('message_template_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('message_text', sa.Text(), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivery_status', sa.String(50), server_default='pending', nullable=False),
        sa.Column('failure_reason', sa.String(255), nullable=True),
        sa.Column('sent_by_employee_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['subscriber_id'], ['wa_subscribers.id']),
        sa.ForeignKeyConstraint(['sent_by_employee_id'], ['employees.id']),
        sa.ForeignKeyConstraint(['campaign_id'], ['wa_campaigns.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Create indexes on the new table
    op.create_index('ix_whatsapp_api_message_log_subscriber', 'whatsapp_api_message_log', ['subscriber_id'])
    op.create_index('ix_whatsapp_api_message_log_tenant', 'whatsapp_api_message_log', ['tenant_id'])
    op.create_index('ix_whatsapp_api_message_log_sent_at', 'whatsapp_api_message_log', ['sent_at'])


def downgrade() -> None:
    # Drop the new table
    op.drop_index('ix_whatsapp_api_message_log_sent_at')
    op.drop_index('ix_whatsapp_api_message_log_tenant')
    op.drop_index('ix_whatsapp_api_message_log_subscriber')
    op.drop_table('whatsapp_api_message_log')
