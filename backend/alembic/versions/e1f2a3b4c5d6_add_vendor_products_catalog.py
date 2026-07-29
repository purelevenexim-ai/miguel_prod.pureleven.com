"""add_vendor_products_catalog

Revision ID: e1f2a3b4c5d6
Revises: b2c3d4e5f6a7
Create Date: 2026-02-21 12:00:00.000000

Adds vendor_products table for procurement intelligence:
- Per-vendor product pricing catalog
- Transport method, lead time, min order qty
- Reorder planning fields
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'e1f2a3b4c5d6'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    # ── vendor_products: per-vendor product pricing catalog ──────────────────
    op.create_table(
        'vendor_products',
        sa.Column('id',            postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id',     postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('vendor_id',     postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id',    postgresql.UUID(as_uuid=True), nullable=False),

        # Pricing
        sa.Column('unit_price',       sa.Numeric(12, 2), nullable=False),
        sa.Column('gst_percent',      sa.Numeric(5, 2),  nullable=False, server_default='0'),
        sa.Column('transport_charge', sa.Numeric(10, 2), nullable=True),
        sa.Column('transport_method', sa.String(50),     nullable=True),   # lorry/courier/own/rail

        # Quantities & Lead Time
        sa.Column('min_order_qty',    sa.Numeric(12, 3), nullable=True),
        sa.Column('max_load_qty',     sa.Numeric(12, 3), nullable=True),
        sa.Column('lead_time_days',   sa.Integer(),       nullable=True),

        # Reorder planning
        sa.Column('reorder_cycle_days', sa.Integer(),   nullable=True),  # avg days between purchases
        sa.Column('notes',              sa.Text(),       nullable=True),
        sa.Column('is_preferred',       sa.Boolean(),    nullable=False, server_default='false'),
        sa.Column('price_updated_at',   sa.DateTime(timezone=True), nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),

        sa.ForeignKeyConstraint(['tenant_id'],  ['tenants.id']),
        sa.ForeignKeyConstraint(['vendor_id'],  ['vendors.id']),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('vendor_id', 'product_id', name='uq_vendor_product'),
    )

    # Indexes for fast lookups
    op.create_index('ix_vendor_products_tenant_id',  'vendor_products', ['tenant_id'])
    op.create_index('ix_vendor_products_vendor_id',  'vendor_products', ['vendor_id'])
    op.create_index('ix_vendor_products_product_id', 'vendor_products', ['product_id'])

    # ── vendor extra fields: type, whatsapp, phone2, lead_time, notes ────────
    op.add_column('vendors', sa.Column('vendor_type',    sa.String(50),  nullable=True))
    op.add_column('vendors', sa.Column('phone2',         sa.String(20),  nullable=True))
    op.add_column('vendors', sa.Column('whatsapp',       sa.String(20),  nullable=True))
    op.add_column('vendors', sa.Column('is_preferred',   sa.Boolean(),   nullable=False, server_default='false'))
    op.add_column('vendors', sa.Column('notes',          sa.Text(),      nullable=True))
    op.add_column('vendors', sa.Column('avg_lead_days',  sa.Integer(),   nullable=True))


def downgrade() -> None:
    op.drop_index('ix_vendor_products_product_id', 'vendor_products')
    op.drop_index('ix_vendor_products_vendor_id',  'vendor_products')
    op.drop_index('ix_vendor_products_tenant_id',  'vendor_products')
    op.drop_table('vendor_products')

    op.drop_column('vendors', 'avg_lead_days')
    op.drop_column('vendors', 'notes')
    op.drop_column('vendors', 'is_preferred')
    op.drop_column('vendors', 'whatsapp')
    op.drop_column('vendors', 'phone2')
    op.drop_column('vendors', 'vendor_type')
