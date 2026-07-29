"""
Logistics Intelligence Tables — Phase 2 & 3
RTO Zones, Customer Delivery Scores, Blacklisted Customers,
COD Transactions, NDR Records, Notification Logs, Order Risk Assessments

Revision ID: logistics_001_initial
Revises: shopify_orders_001_initial
Create Date: 2026-02-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'logistics_001_initial'
down_revision = 'shopify_orders_001'
branch_labels = None
depends_on = None


def upgrade():

    # ── RTO Zones ─────────────────────────────────────────────
    op.create_table(
        'rto_zones',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('pincode', sa.String(10), nullable=False),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(100), nullable=True),
        sa.Column('delivery_zone', sa.String(10), nullable=True),
        sa.Column('total_shipments', sa.Integer(), default=0, nullable=False),
        sa.Column('rto_count', sa.Integer(), default=0, nullable=False),
        sa.Column('ndr_count', sa.Integer(), default=0, nullable=False),
        sa.Column('delivered_count', sa.Integer(), default=0, nullable=False),
        sa.Column('rto_percentage', sa.Numeric(5, 2), default=0.0, nullable=False),
        sa.Column('risk_level', sa.String(20), default='low', nullable=False),
        sa.Column('risk_score', sa.Numeric(5, 2), default=0.0, nullable=False),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'pincode', name='uq_rto_zone_pincode_tenant'),
    )
    op.create_index('ix_rto_zones_tenant_id', 'rto_zones', ['tenant_id'])
    op.create_index('ix_rto_zones_pincode', 'rto_zones', ['pincode'])
    op.create_index('ix_rto_zones_risk_level', 'rto_zones', ['risk_level'])

    # ── Customer Delivery Scores ───────────────────────────────
    op.create_table(
        'customer_delivery_scores',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('customer_phone', sa.String(20), nullable=False),
        sa.Column('customer_email', sa.String(255), nullable=True),
        sa.Column('customer_name', sa.String(255), nullable=True),
        sa.Column('total_orders', sa.Integer(), default=0, nullable=False),
        sa.Column('delivered_orders', sa.Integer(), default=0, nullable=False),
        sa.Column('rto_orders', sa.Integer(), default=0, nullable=False),
        sa.Column('ndr_orders', sa.Integer(), default=0, nullable=False),
        sa.Column('cancelled_orders', sa.Integer(), default=0, nullable=False),
        sa.Column('cod_orders', sa.Integer(), default=0, nullable=False),
        sa.Column('cod_confirmed', sa.Integer(), default=0, nullable=False),
        sa.Column('cod_rejected', sa.Integer(), default=0, nullable=False),
        sa.Column('cod_timeout', sa.Integer(), default=0, nullable=False),
        sa.Column('delivery_score', sa.Numeric(5, 2), default=50.0, nullable=False),
        sa.Column('risk_level', sa.String(20), default='low', nullable=False),
        sa.Column('last_order_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'customer_phone', name='uq_customer_score_phone'),
    )
    op.create_index('ix_customer_scores_tenant_id', 'customer_delivery_scores', ['tenant_id'])
    op.create_index('ix_customer_scores_phone', 'customer_delivery_scores', ['customer_phone'])
    op.create_index('ix_customer_scores_risk_level', 'customer_delivery_scores', ['risk_level'])

    # ── Blacklisted Customers ──────────────────────────────────
    op.create_table(
        'blacklisted_customers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('customer_phone', sa.String(20), nullable=False),
        sa.Column('customer_email', sa.String(255), nullable=True),
        sa.Column('customer_name', sa.String(255), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('blacklist_type', sa.String(20), default='manual', nullable=False),
        sa.Column('is_permanent', sa.Boolean(), default=False, nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('blocked_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_blacklist_tenant_id', 'blacklisted_customers', ['tenant_id'])
    op.create_index('ix_blacklist_phone', 'blacklisted_customers', ['customer_phone'])
    op.create_index('ix_blacklist_active', 'blacklisted_customers', ['is_active'])

    # ── COD Transactions ───────────────────────────────────────
    op.create_table(
        'cod_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('shopify_order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shopify_orders.id'), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('currency', sa.String(10), default='INR', nullable=False),
        sa.Column('customer_phone', sa.String(20), nullable=False),
        sa.Column('customer_name', sa.String(255), nullable=True),
        sa.Column('status', sa.String(20), default='pending', nullable=False),
        sa.Column('confirmation_code', sa.String(20), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('whatsapp_message_id', sa.String(255), nullable=True),
        sa.Column('sms_message_id', sa.String(255), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reminder_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reminder_count', sa.Integer(), default=0, nullable=False),
        sa.Column('response_data', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_cod_transactions_tenant_id', 'cod_transactions', ['tenant_id'])
    op.create_index('ix_cod_transactions_order_id', 'cod_transactions', ['shopify_order_id'])
    op.create_index('ix_cod_transactions_status', 'cod_transactions', ['status'])

    # ── NDR Records ────────────────────────────────────────────
    op.create_table(
        'ndr_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('shopify_order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shopify_orders.id'), nullable=False),
        sa.Column('tracking_number', sa.String(100), nullable=False),
        sa.Column('courier_name', sa.String(100), nullable=False),
        sa.Column('ndr_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reason', sa.String(50), default='other', nullable=False),
        sa.Column('reason_detail', sa.Text(), nullable=True),
        sa.Column('attempt_number', sa.Integer(), default=1, nullable=False),
        sa.Column('status', sa.String(30), default='pending', nullable=False),
        sa.Column('action_taken', sa.String(100), nullable=True),
        sa.Column('action_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_note', sa.Text(), nullable=True),
        sa.Column('customer_phone', sa.String(20), nullable=True),
        sa.Column('customer_notified', sa.Boolean(), default=False, nullable=False),
        sa.Column('notified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('raw_ndr_data', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ndr_records_tenant_id', 'ndr_records', ['tenant_id'])
    op.create_index('ix_ndr_records_order_id', 'ndr_records', ['shopify_order_id'])
    op.create_index('ix_ndr_records_status', 'ndr_records', ['status'])
    op.create_index('ix_ndr_records_tracking', 'ndr_records', ['tracking_number'])

    # ── Notification Logs ──────────────────────────────────────
    op.create_table(
        'notification_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('shopify_order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shopify_orders.id'), nullable=True),
        sa.Column('channel', sa.String(20), nullable=False),
        sa.Column('recipient', sa.String(255), nullable=False),
        sa.Column('message_type', sa.String(50), nullable=False),
        sa.Column('message_body', sa.Text(), nullable=True),
        sa.Column('template_name', sa.String(100), nullable=True),
        sa.Column('status', sa.String(20), default='pending', nullable=False),
        sa.Column('provider_id', sa.String(255), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('provider_response', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_notification_logs_tenant_id', 'notification_logs', ['tenant_id'])
    op.create_index('ix_notification_logs_order_id', 'notification_logs', ['shopify_order_id'])
    op.create_index('ix_notification_logs_status', 'notification_logs', ['status'])
    op.create_index('ix_notification_logs_channel', 'notification_logs', ['channel'])

    # ── Order Risk Assessments ─────────────────────────────────
    op.create_table(
        'order_risk_assessments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('shopify_order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shopify_orders.id'), nullable=False),
        sa.Column('overall_risk_level', sa.String(20), default='low', nullable=False),
        sa.Column('overall_risk_score', sa.Numeric(5, 2), default=0.0, nullable=False),
        sa.Column('decision', sa.String(20), default='approve', nullable=False),
        sa.Column('customer_risk_score', sa.Numeric(5, 2), default=0.0),
        sa.Column('pincode_risk_score', sa.Numeric(5, 2), default=0.0),
        sa.Column('order_value_score', sa.Numeric(5, 2), default=0.0),
        sa.Column('cod_risk_score', sa.Numeric(5, 2), default=0.0),
        sa.Column('is_customer_blacklisted', sa.Boolean(), default=False),
        sa.Column('is_high_rto_zone', sa.Boolean(), default=False),
        sa.Column('is_high_value_order', sa.Boolean(), default=False),
        sa.Column('is_cod_order', sa.Boolean(), default=False),
        sa.Column('is_new_customer', sa.Boolean(), default=False),
        sa.Column('has_multiple_rto', sa.Boolean(), default=False),
        sa.Column('has_cod_rejections', sa.Boolean(), default=False),
        sa.Column('risk_reasons', postgresql.JSON(), nullable=True),
        sa.Column('reviewed_by', sa.String(255), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('shopify_order_id', name='uq_risk_per_order'),
    )
    op.create_index('ix_risk_assessments_tenant_id', 'order_risk_assessments', ['tenant_id'])
    op.create_index('ix_risk_assessments_order_id', 'order_risk_assessments', ['shopify_order_id'])
    op.create_index('ix_risk_assessments_decision', 'order_risk_assessments', ['decision'])
    op.create_index('ix_risk_assessments_risk_level', 'order_risk_assessments', ['overall_risk_level'])


def downgrade():
    op.drop_table('order_risk_assessments')
    op.drop_table('notification_logs')
    op.drop_table('ndr_records')
    op.drop_table('cod_transactions')
    op.drop_table('blacklisted_customers')
    op.drop_table('customer_delivery_scores')
    op.drop_table('rto_zones')
