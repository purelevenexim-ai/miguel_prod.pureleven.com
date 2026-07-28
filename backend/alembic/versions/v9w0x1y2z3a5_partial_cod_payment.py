"""Add Partial COD payment support and advance payment tracking

Revision ID: v9w0x1y2z3a5
Revises: v9w0x1y2z3a4
Create Date: 2026-02-25 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'v9w0x1y2z3a5'
down_revision = 'v9w0x1y2z3a4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add partial_cod payment method and advance/cod amount tracking"""
    
    # 1. Add new columns to orders table for Partial COD support
    op.add_column('orders', sa.Column('advance_amount', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'))
    op.add_column('orders', sa.Column('cod_amount', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'))
    
    # 2. Add index on advance_amount for queries filtering by partial COD orders
    op.create_index('ix_orders_advance_amount', 'orders', ['advance_amount'])
    
    # 3. Update payment_method enum to include partial_cod
    # Note: PostgreSQL enum modification requires direct SQL
    op.execute("ALTER TYPE paymentmethod ADD VALUE 'partial_cod' BEFORE 'credit'")


def downgrade() -> None:
    """Revert partial COD payment support"""
    
    # 1. Drop the index
    op.drop_index('ix_orders_advance_amount', 'orders')
    
    # 2. Drop the new columns
    op.drop_column('orders', 'cod_amount')
    op.drop_column('orders', 'advance_amount')
    
    # 3. Remove partial_cod from enum
    # Note: PostgreSQL doesn't allow removing enum values, so we leave it
    # (commented out to prevent migration failure)
    # op.execute("ALTER TYPE paymentmethod DROP VALUE 'partial_cod'")
