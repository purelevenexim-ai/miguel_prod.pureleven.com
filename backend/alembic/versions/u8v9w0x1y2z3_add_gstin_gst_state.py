"""add gstin to customers and gst_state to tenants

Revision ID: u8v9w0x1y2z3
Revises: t7u8v9w0x1y2
Create Date: 2026-02-23

"""
from alembic import op
import sqlalchemy as sa

revision = 'u8v9w0x1y2z3'
down_revision = 't7u8v9w0x1y2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add GSTIN to customers (nullable — B2C customers won't have it)
    op.add_column('customers', sa.Column('gstin', sa.String(15), nullable=True))
    # Add GST state to tenants (for CGST/SGST vs IGST split)
    op.add_column('tenants', sa.Column('gst_state', sa.String(100), nullable=True))
    # Add GSTIN to tenants (own GSTIN for invoice header)
    op.add_column('tenants', sa.Column('gstin', sa.String(15), nullable=True))
    # Add company address fields to tenants (for GST filing)
    op.add_column('tenants', sa.Column('gst_address', sa.Text(), nullable=True))
    op.add_column('tenants', sa.Column('gst_city', sa.String(100), nullable=True))
    op.add_column('tenants', sa.Column('gst_pincode', sa.String(10), nullable=True))


def downgrade() -> None:
    op.drop_column('customers', 'gstin')
    op.drop_column('tenants', 'gst_state')
    op.drop_column('tenants', 'gstin')
    op.drop_column('tenants', 'gst_address')
    op.drop_column('tenants', 'gst_city')
    op.drop_column('tenants', 'gst_pincode')
