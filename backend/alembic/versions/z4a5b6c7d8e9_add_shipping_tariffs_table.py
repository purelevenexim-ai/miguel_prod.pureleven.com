"""add shipping_tariffs table

Revision ID: z4a5b6c7d8e9
Revises: e6395f592ebb, z3a4b5c6d7e8
Create Date: 2026-03-02 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from typing import Sequence, Union

revision = 'z4a5b6c7d8e9'
down_revision: Union[str, Sequence[str], None] = ('e6395f592ebb', 'z3a4b5c6d7e8')
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'shipping_tariffs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('sku_code', sa.String(100), nullable=False),
        sa.Column('shipping_cost', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('rto_handling_charge', sa.Numeric(10, 2), nullable=False, server_default='50'),
        sa.Column('file_uploaded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'product_id', 'sku_code', name='uq_shipping_tariff_product_sku'),
    )
    op.create_index('ix_shipping_tariffs_tenant_id', 'shipping_tariffs', ['tenant_id'], unique=False)
    op.create_index('ix_shipping_tariffs_product_id', 'shipping_tariffs', ['product_id'], unique=False)
    op.create_index('ix_shipping_tariffs_sku_code', 'shipping_tariffs', ['sku_code'], unique=False)
    op.create_index('ix_shipping_tariffs_tenant_sku', 'shipping_tariffs', ['tenant_id', 'sku_code'], unique=False)
    op.create_index('ix_shipping_tariffs_uploaded_at', 'shipping_tariffs', ['file_uploaded_at'], unique=False)


def downgrade():
    op.drop_index('ix_shipping_tariffs_uploaded_at', table_name='shipping_tariffs')
    op.drop_index('ix_shipping_tariffs_tenant_sku', table_name='shipping_tariffs')
    op.drop_index('ix_shipping_tariffs_sku_code', table_name='shipping_tariffs')
    op.drop_index('ix_shipping_tariffs_product_id', table_name='shipping_tariffs')
    op.drop_index('ix_shipping_tariffs_tenant_id', table_name='shipping_tariffs')
    op.drop_table('shipping_tariffs')
