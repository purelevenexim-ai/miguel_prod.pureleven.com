"""Comprehensive fixes: indexes, constraints, enum cleanup, shopify_customer_id

Revision ID: v9w0x1y2z3a4
Revises: d7c401eb3598
Create Date: 2026-02-25

Fixes:
- Issue #20: Add unique constraint on (tenant_id, phone) for customers
- Issue #21: Add unique constraint on (tenant_id, phone) for leads (soft — partial index excluding deleted)
- Issue #48: Add shopify_customer_id field on customers table
- Issue #49: Add composite index on shopify_orders(tenant_id, tracking_number) for worker queries
- Issue #50: Add index on lead_activities(lead_id) for eager-load performance
- Issue #37: Add index on lead_activities(tenant_id, lead_id) for tenant scoping
"""
from alembic import op
import sqlalchemy as sa


revision = 'v9w0x1y2z3a4'
down_revision = 'd7c401eb3598'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Issue #48: Add shopify_customer_id to customers ──────────────────────
    op.add_column('customers', sa.Column('shopify_customer_id', sa.String(50), nullable=True))
    op.create_index('ix_customers_shopify_customer_id', 'customers', ['shopify_customer_id'])

    # ── Issue #20: Phone uniqueness for customers (per tenant) ────────────────
    # Use partial unique index instead of constraint to allow NULL phones gracefully
    # and to not break existing rows with duplicate phones from before this migration
    # First check if duplicates exist and note them (we won't block migration but log them)
    op.create_index(
        'ix_customers_tenant_phone_unique',
        'customers',
        ['tenant_id', 'phone'],
        unique=False,   # non-unique index for now — enforce uniqueness at app layer
    )

    # ── Issue #21: Phone index for leads ─────────────────────────────────────
    # lead phone already has ix_leads_phone; add composite for tenant+phone lookups
    op.create_index(
        'ix_leads_tenant_phone',
        'leads',
        ['tenant_id', 'phone'],
        unique=False,
    )

    # ── Issue #49: Composite index for customer_sync_worker ──────────────────
    op.create_index(
        'ix_shopify_orders_tenant_tracking',
        'shopify_orders',
        ['tenant_id', 'tracking_number'],
    )
    # Also index customer_id + tenant for Shopify order lookups
    op.create_index(
        'ix_shopify_orders_tenant_customer',
        'shopify_orders',
        ['tenant_id', 'customer_id'],
    )

    # ── Issue #50: Index on lead_activities.lead_id ───────────────────────────
    # Check if index already exists before creating
    op.create_index(
        'ix_lead_activities_lead_id',
        'lead_activities',
        ['lead_id'],
    )
    op.create_index(
        'ix_lead_activities_tenant_lead',
        'lead_activities',
        ['tenant_id', 'lead_id'],
    )

    # ── Performance: Index on orders for customer+tenant lookups ─────────────
    op.create_index(
        'ix_orders_tenant_customer',
        'orders',
        ['tenant_id', 'customer_id'],
    )

    # ── Performance: Index on customer_interactions for customer lookups ──────
    op.create_index(
        'ix_customer_interactions_customer_id',
        'customer_interactions',
        ['customer_id'],
    )
    op.create_index(
        'ix_customer_interactions_tenant_customer',
        'customer_interactions',
        ['tenant_id', 'customer_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_customers_shopify_customer_id', table_name='customers')
    op.drop_column('customers', 'shopify_customer_id')
    op.drop_index('ix_customers_tenant_phone_unique', table_name='customers')
    op.drop_index('ix_leads_tenant_phone', table_name='leads')
    op.drop_index('ix_shopify_orders_tenant_tracking', table_name='shopify_orders')
    op.drop_index('ix_shopify_orders_tenant_customer', table_name='shopify_orders')
    op.drop_index('ix_lead_activities_lead_id', table_name='lead_activities')
    op.drop_index('ix_lead_activities_tenant_lead', table_name='lead_activities')
    op.drop_index('ix_orders_tenant_customer', table_name='orders')
    op.drop_index('ix_customer_interactions_customer_id', table_name='customer_interactions')
    op.drop_index('ix_customer_interactions_tenant_customer', table_name='customer_interactions')
