"""add_shipping_config_tables

Revision ID: c0e793280887
Revises: 34b2c24ed0c6
Create Date: 2026-02-24 16:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'c0e793280887'
down_revision: Union[str, Sequence[str], None] = '34b2c24ed0c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── shopify_stores ────────────────────────────────────────────────────────
    op.create_table(
        'shopify_stores',
        sa.Column('id',                  postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id',           postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('store_name',          sa.String(255), nullable=False),
        sa.Column('store_url',           sa.String(255), nullable=False, unique=True),
        sa.Column('is_primary',          sa.Boolean(), server_default='false', nullable=False),
        sa.Column('api_access_token',    sa.Text(), nullable=False),
        sa.Column('api_client_id',       sa.String(255), nullable=True),
        sa.Column('api_client_secret',   sa.Text(), nullable=True),
        sa.Column('api_version',         sa.String(20), server_default='2024-01'),
        sa.Column('webhook_secret',      sa.Text(), nullable=True),
        sa.Column('webhook_topics',      postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active',           sa.Boolean(), server_default='true', nullable=False),
        sa.Column('is_connected',        sa.Boolean(), server_default='false', nullable=False),
        sa.Column('last_connection_test',sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_sync',           sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at',          sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at',          sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_shopify_stores_tenant_id', 'shopify_stores', ['tenant_id'])

    # ── delivery_partners ─────────────────────────────────────────────────────
    op.create_table(
        'delivery_partners',
        sa.Column('id',                      postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id',               postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('partner_type',            sa.String(50), nullable=False),
        sa.Column('display_name',            sa.String(255), nullable=False),
        sa.Column('is_primary',              sa.Boolean(), server_default='false', nullable=False),
        sa.Column('api_key',                 sa.Text(), nullable=False),
        sa.Column('api_secret',              sa.Text(), nullable=True),
        sa.Column('client_name',             sa.String(255), nullable=True),
        sa.Column('client_id',               sa.String(255), nullable=True),
        sa.Column('api_base_url',            sa.String(255), nullable=True),
        sa.Column('api_version',             sa.String(20), nullable=True),
        sa.Column('pickup_location_code',    sa.String(100), nullable=True),
        sa.Column('warehouse_name',          sa.String(255), nullable=True),
        sa.Column('warehouse_address',       sa.Text(), nullable=True),
        sa.Column('warehouse_phone',         sa.String(20), nullable=True),
        sa.Column('supported_shipment_types',postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('default_shipment_type',   sa.String(50), server_default='surface'),
        sa.Column('is_active',               sa.Boolean(), server_default='true', nullable=False),
        sa.Column('is_connected',            sa.Boolean(), server_default='false', nullable=False),
        sa.Column('last_connection_test',    sa.DateTime(timezone=True), nullable=True),
        sa.Column('base_charge',             sa.Numeric(10, 2), nullable=True),
        sa.Column('weight_rate_per_kg',      sa.Numeric(10, 2), nullable=True),
        sa.Column('created_at',              sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at',              sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_delivery_partners_tenant_id', 'delivery_partners', ['tenant_id'])

    # ── notification_channels ─────────────────────────────────────────────────
    op.create_table(
        'notification_channels',
        sa.Column('id',                  postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id',           postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('channel_type',        sa.String(50), nullable=False),
        sa.Column('provider',            sa.String(50), nullable=True),
        sa.Column('is_primary',          sa.Boolean(), server_default='false', nullable=False),
        sa.Column('api_key',             sa.Text(), nullable=False),
        sa.Column('api_secret',          sa.Text(), nullable=True),
        sa.Column('access_token',        sa.Text(), nullable=True),
        sa.Column('phone_number',        sa.String(25), nullable=True),
        sa.Column('business_account_id', sa.String(255), nullable=True),
        sa.Column('phone_number_id',     sa.String(255), nullable=True),
        sa.Column('sender_email',        sa.String(255), nullable=True),
        sa.Column('is_active',           sa.Boolean(), server_default='true', nullable=False),
        sa.Column('is_connected',        sa.Boolean(), server_default='false', nullable=False),
        sa.Column('last_connection_test',sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at',          sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at',          sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_notification_channels_tenant_id', 'notification_channels', ['tenant_id'])

    # ── shipping_business_rules ───────────────────────────────────────────────
    op.create_table(
        'shipping_business_rules',
        sa.Column('id',                              postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id',                       postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('max_order_value',                 sa.Numeric(15, 2), server_default='50000'),
        sa.Column('max_cod_amount',                  sa.Numeric(15, 2), server_default='10000'),
        sa.Column('high_rto_threshold',              sa.Numeric(5, 2),  server_default='15.0'),
        sa.Column('medium_rto_threshold',            sa.Numeric(5, 2),  server_default='8.0'),
        sa.Column('auto_blacklist_rto_count',        sa.String(10), server_default='5'),
        sa.Column('auto_blacklist_ndr_count',        sa.String(10), server_default='5'),
        sa.Column('auto_blacklist_fraud_score',      sa.Numeric(5, 2), server_default='80.0'),
        sa.Column('blacklist_duration_days',         sa.String(10), nullable=True),
        sa.Column('require_cod_confirmation',        sa.Boolean(), server_default='true'),
        sa.Column('cod_confirmation_timeout_minutes',sa.String(10), server_default='30'),
        sa.Column('auto_create_reattempt_on_ndr',    sa.Boolean(), server_default='false'),
        sa.Column('max_ndr_reattempts',              sa.String(5),  server_default='2'),
        sa.Column('auto_create_on_order_created',    sa.Boolean(), server_default='true'),
        sa.Column('auto_create_on_payment_confirmed',sa.Boolean(), server_default='false'),
        sa.Column('require_manual_approval',         sa.Boolean(), server_default='false'),
        sa.Column('tracking_sync_interval_minutes',  sa.String(5),  server_default='15'),
        sa.Column('send_delivery_confirmation',      sa.Boolean(), server_default='true'),
        sa.Column('send_rto_alerts',                 sa.Boolean(), server_default='true'),
        sa.Column('send_ndr_alerts',                 sa.Boolean(), server_default='true'),
        sa.Column('notify_via_whatsapp',             sa.Boolean(), server_default='true'),
        sa.Column('notify_via_sms',                  sa.Boolean(), server_default='false'),
        sa.Column('notify_via_email',                sa.Boolean(), server_default='false'),
        sa.Column('admin_alert_on_rto',              sa.Boolean(), server_default='true'),
        sa.Column('admin_alert_on_ndr',              sa.Boolean(), server_default='true'),
        sa.Column('admin_alert_on_high_value_order', sa.Boolean(), server_default='true'),
        sa.Column('admin_emails',                    postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at',                      sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at',                      sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_shipping_business_rules_tenant_id', 'shipping_business_rules', ['tenant_id'])


def downgrade() -> None:
    op.drop_table('shipping_business_rules')
    op.drop_table('notification_channels')
    op.drop_table('delivery_partners')
    op.drop_table('shopify_stores')
