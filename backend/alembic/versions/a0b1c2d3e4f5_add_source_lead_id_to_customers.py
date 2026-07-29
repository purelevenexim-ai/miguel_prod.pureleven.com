"""add source_lead_id to customers for tracking lead conversions

Revision ID: a0b1c2d3e4f5
Revises: z3a4b5c6d7e8
Create Date: 2026-03-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'a0b1c2d3e4f5'
down_revision = 'z3a4b5c6d7e8'
branch_labels = None
depends_on = None


def upgrade():
    # Add source_lead_id column to customers table
    op.add_column('customers', sa.Column('source_lead_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_customers_source_lead_id',
        'customers', 'leads',
        ['source_lead_id'], ['id']
    )


def downgrade():
    # Drop foreign key and column
    op.drop_constraint('fk_customers_source_lead_id', 'customers', type_='foreignkey')
    op.drop_column('customers', 'source_lead_id')
