"""Add Shopify Order and Shipping Tables

Revision ID: shopify_orders_001
Revises: <previous_migration>
Create Date: 2026-02-25 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

revision = 'shopify_orders_001'
down_revision = 'c0e793280887'
branch_labels = None
depends_on = None


def upgrade():
    # ── ShopifyOrder table ────────────────────────────────────
    op.create_table(
        'shopify_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('shopify_store_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('shopify_order_id', sa.String(50), nullable=False),
        sa.Column('shopify_order_number', sa.String(50), nullable=False),
        sa.Column('shopify_order_name', sa.String(50), nullable=False),
        sa.Column('shopify_status', sa.String(50), nullable=False),
        sa.Column('shopify_fulfillment_status', sa.String(50), nullable=False),
        sa.Column('shopify_financial_status', sa.String(50), nullable=True),
        sa.Column('customer_name', sa.String(255), nullable=False),
        sa.Column('customer_email', sa.String(255), nullable=True),
        sa.Column('customer_phone', sa.String(20), nullable=True),
        sa.Column('billing_name', sa.String(255), nullable=True),
        sa.Column('billing_address_line1', sa.String(255), nullable=True),
        sa.Column('billing_address_line2', sa.String(255), nullable=True),
        sa.Column('billing_city', sa.String(100), nullable=True),
        sa.Column('billing_state', sa.String(100), nullable=True),
        sa.Column('billing_zip', sa.String(20), nullable=True),
        sa.Column('billing_country', sa.String(100), nullable=True),
        sa.Column('shipping_name', sa.String(255), nullable=False),
        sa.Column('shipping_address_line1', sa.String(255), nullable=False),
        sa.Column('shipping_address_line2', sa.String(255), nullable=True),
        sa.Column('shipping_city', sa.String(100), nullable=False),
        sa.Column('shipping_state', sa.String(100), nullable=False),
        sa.Column('shipping_zip', sa.String(20), nullable=False),
        sa.Column('shipping_country', sa.String(100), nullable=False),
        sa.Column('shipping_phone', sa.String(20), nullable=True),
        sa.Column('currency', sa.String(10), nullable=False, server_default='INR'),
        sa.Column('subtotal', sa.Numeric(12, 2), nullable=False),
        sa.Column('taxes', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('discounts', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('shipping_cost', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('total_price', sa.Numeric(12, 2), nullable=False),
        sa.Column('line_items_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('line_items_json', postgresql.JSON, nullable=True),
        sa.Column('shipping_partner', sa.String(50), nullable=True),
        sa.Column('tracking_number', sa.String(100), nullable=True),
        sa.Column('tracking_url', sa.Text, nullable=True),
        sa.Column('created_at_shopify', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at_shopify', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expected_delivery_date', sa.Date, nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('raw_shopify_data', postgresql.JSON, nullable=True),
        sa.Column('synced_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_tracking_update', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['shopify_store_id'], ['shopify_stores.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('shopify_store_id', 'shopify_order_id', name='uq_shopify_order_per_store'),
    )
    op.create_index('ix_shopify_orders_tenant_id', 'shopify_orders', ['tenant_id'])
    op.create_index('ix_shopify_orders_store_id', 'shopify_orders', ['shopify_store_id'])
    op.create_index('ix_shopify_orders_status', 'shopify_orders', ['shopify_status'])
    op.create_index('ix_shopify_orders_created_at_shopify', 'shopify_orders', ['created_at_shopify'])
    op.create_index('ix_shopify_orders_tracking_number', 'shopify_orders', ['tracking_number'])

    # ── ShippingInfo table ────────────────────────────────────
    op.create_table(
        'shipping_info',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('shopify_order_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('shipping_partner', sa.String(50), nullable=False),
        sa.Column('courier_name', sa.String(100), nullable=False),
        sa.Column('courier_code', sa.String(50), nullable=True),
        sa.Column('tracking_number', sa.String(100), nullable=False),
        sa.Column('tracking_url', sa.Text, nullable=True),
        sa.Column('tracking_status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('shipment_date', sa.Date, nullable=True),
        sa.Column('actual_weight', sa.Numeric(8, 2), nullable=True),
        sa.Column('dimensions', sa.String(100), nullable=True),
        sa.Column('base_charge', sa.Numeric(10, 2), nullable=True),
        sa.Column('fuel_surcharge', sa.Numeric(10, 2), nullable=True, server_default='0'),
        sa.Column('handling_charge', sa.Numeric(10, 2), nullable=True, server_default='0'),
        sa.Column('total_charge', sa.Numeric(10, 2), nullable=True),
        sa.Column('courier_api_response', postgresql.JSON, nullable=True),
        sa.Column('is_delivered', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivery_attempt_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('last_tracking_update', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['shopify_order_id'], ['shopify_orders.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_shipping_info_tenant_id', 'shipping_info', ['tenant_id'])
    op.create_index('ix_shipping_info_tracking_number', 'shipping_info', ['tracking_number'])
    op.create_index('ix_shipping_info_shipping_partner', 'shipping_info', ['shipping_partner'])

    # ── TrackingEvent table ───────────────────────────────────
    op.create_table(
        'tracking_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('shopify_order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_status', sa.String(50), nullable=False),
        sa.Column('event_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('location_code', sa.String(50), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('detail', sa.Text, nullable=True),
        sa.Column('courier_event_id', sa.String(100), nullable=True),
        sa.Column('courier_name', sa.String(100), nullable=True),
        sa.Column('raw_tracking_data', postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['shopify_order_id'], ['shopify_orders.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_tracking_events_tenant_id', 'tracking_events', ['tenant_id'])
    op.create_index('ix_tracking_events_shopify_order_id', 'tracking_events', ['shopify_order_id'])
    op.create_index('ix_tracking_events_event_status', 'tracking_events', ['event_status'])
    op.create_index('ix_tracking_events_event_time', 'tracking_events', ['event_time'])


def downgrade():
    op.drop_index('ix_tracking_events_event_time', table_name='tracking_events')
    op.drop_index('ix_tracking_events_event_status', table_name='tracking_events')
    op.drop_index('ix_tracking_events_shopify_order_id', table_name='tracking_events')
    op.drop_index('ix_tracking_events_tenant_id', table_name='tracking_events')
    op.drop_table('tracking_events')
    
    op.drop_index('ix_shipping_info_shipping_partner', table_name='shipping_info')
    op.drop_index('ix_shipping_info_tracking_number', table_name='shipping_info')
    op.drop_index('ix_shipping_info_tenant_id', table_name='shipping_info')
    op.drop_table('shipping_info')
    
    op.drop_index('ix_shopify_orders_tracking_number', table_name='shopify_orders')
    op.drop_index('ix_shopify_orders_created_at_shopify', table_name='shopify_orders')
    op.drop_index('ix_shopify_orders_status', table_name='shopify_orders')
    op.drop_index('ix_shopify_orders_store_id', table_name='shopify_orders')
    op.drop_index('ix_shopify_orders_tenant_id', table_name='shopify_orders')
    op.drop_table('shopify_orders')
