"""orders_fulfillment_engine

Adds courier tables, India Post customer IDs, extended order fields
for the full fulfillment engine.

Revision ID: f1a2b3c4d5e6
Revises: 947175c241e7
Create Date: 2026-02-21 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = '947175c241e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Couriers table ─────────────────────────────────────────
    op.create_table(
        'couriers',
        sa.Column('id',         sa.UUID(),                    nullable=False),
        sa.Column('tenant_id',  sa.UUID(),                    nullable=False),
        sa.Column('name',       sa.String(length=100),        nullable=False),
        sa.Column('code',       sa.String(length=50),         nullable=False),   # e.g. INDIA_POST, BLUEDART
        sa.Column('is_active',  sa.Boolean(),                 nullable=False, server_default='true'),
        sa.Column('is_default', sa.Boolean(),                 nullable=False, server_default='false'),
        sa.Column('notes',      sa.Text(),                    nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),   server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'code', name='uq_courier_code_tenant'),
    )
    op.create_index('ix_couriers_tenant_id', 'couriers', ['tenant_id'])

    # ── India Post Customer IDs ────────────────────────────────
    op.create_table(
        'india_post_customer_ids',
        sa.Column('id',           sa.UUID(),                  nullable=False),
        sa.Column('tenant_id',    sa.UUID(),                  nullable=False),
        sa.Column('customer_id',  sa.String(length=50),       nullable=False),   # post office issued ID
        sa.Column('label',        sa.String(length=100),      nullable=True),    # e.g. "Mumbai Office"
        sa.Column('is_default',   sa.Boolean(),               nullable=False, server_default='false'),
        sa.Column('is_active',    sa.Boolean(),               nullable=False, server_default='true'),
        sa.Column('created_at',   sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'customer_id', name='uq_ip_customer_id_tenant'),
    )
    op.create_index('ix_india_post_cids_tenant_id', 'india_post_customer_ids', ['tenant_id'])

    # ── Extend orders table ────────────────────────────────────
    # Address fields for parsed paste
    op.add_column('orders', sa.Column('address_raw',        sa.Text(),          nullable=True))
    op.add_column('orders', sa.Column('address_name2',      sa.String(255),     nullable=True))   # second name if found
    op.add_column('orders', sa.Column('delivery_name',      sa.String(255),     nullable=True))   # primary recipient name
    op.add_column('orders', sa.Column('delivery_phone2',    sa.String(20),      nullable=True))   # alternate phone from parse
    op.add_column('orders', sa.Column('delivery_district',  sa.String(100),     nullable=True))

    # Shipping fields
    op.add_column('orders', sa.Column('shipping_service',         sa.String(50),  nullable=True))   # speed_post | parcel
    op.add_column('orders', sa.Column('india_post_customer_id',   sa.String(50),  nullable=True))   # selected IP cust ID
    op.add_column('orders', sa.Column('courier_id',               sa.UUID(),      nullable=True))
    op.add_column('orders', sa.Column('courier_code',             sa.String(50),  nullable=True))   # snapshot at order time

    # Status extension
    op.add_column('orders', sa.Column('not_confirmed_reason',     sa.Text(),      nullable=True))
    op.add_column('orders', sa.Column('order_source',             sa.String(50),  nullable=True, server_default='manual'))

    # Lead linkage (if not confirmed → lead created)
    op.add_column('orders', sa.Column('lead_id',                  sa.UUID(),      nullable=True))

    # WhatsApp sent flags
    op.add_column('orders', sa.Column('wa_confirmed_sent',        sa.Boolean(),   nullable=False, server_default='false'))
    op.add_column('orders', sa.Column('wa_shipped_sent',          sa.Boolean(),   nullable=False, server_default='false'))

    # Add FK for courier_id (nullable, so safe)
    op.create_foreign_key('fk_orders_courier_id', 'orders', 'couriers', ['courier_id'], ['id'])
    op.create_foreign_key('fk_orders_lead_id', 'orders', 'leads', ['lead_id'], ['id'])

    # Index on phone for global search support
    op.create_index('ix_orders_lead_id', 'orders', ['lead_id'])


def downgrade() -> None:
    op.drop_constraint('fk_orders_lead_id', 'orders', type_='foreignkey')
    op.drop_constraint('fk_orders_courier_id', 'orders', type_='foreignkey')
    op.drop_index('ix_orders_lead_id', 'orders')
    for col in [
        'address_raw', 'address_name2', 'delivery_name', 'delivery_phone2', 'delivery_district',
        'shipping_service', 'india_post_customer_id', 'courier_id', 'courier_code',
        'not_confirmed_reason', 'order_source', 'lead_id', 'wa_confirmed_sent', 'wa_shipped_sent',
    ]:
        op.drop_column('orders', col)
    op.drop_index('ix_india_post_cids_tenant_id', 'india_post_customer_ids')
    op.drop_table('india_post_customer_ids')
    op.drop_index('ix_couriers_tenant_id', 'couriers')
    op.drop_table('couriers')
