"""Add customer_id to shopify_orders table

Revision ID: d7c401eb3598
Revises: logistics_001_initial
Create Date: 2026-02-25 14:04:32.066085

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd7c401eb3598'
down_revision: Union[str, Sequence[str], None] = 'logistics_001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add customer_id column to shopify_orders."""
    # Add customer_id column as nullable FK to customers
    op.add_column('shopify_orders', sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_shopify_orders_customer_id',
        'shopify_orders',
        'customers',
        ['customer_id'],
        ['id']
    )
    
    # Add index for performance
    op.create_index(
        op.f('ix_shopify_orders_customer_id'),
        'shopify_orders',
        ['customer_id'],
        unique=False
    )


def downgrade() -> None:
    """Downgrade schema - remove customer_id from shopify_orders."""
    op.drop_index(op.f('ix_shopify_orders_customer_id'), table_name='shopify_orders')
    op.drop_constraint('fk_shopify_orders_customer_id', 'shopify_orders', type_='foreignkey')
    op.drop_column('shopify_orders', 'customer_id')
