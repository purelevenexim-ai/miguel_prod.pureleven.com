"""fix shopify store URL uniqueness to be per-tenant (multi-tenant isolation)

Revision ID: w0x1y2z3a4b5
Revises: v9w0x1y2z3a5
Create Date: 2026-02-27

Problem: shopify_stores.store_url had a GLOBAL unique constraint, meaning
two different tenants could not configure the same Shopify store URL.
Fix: Drop global unique index, add composite unique per (tenant_id, store_url).
"""

from alembic import op
import sqlalchemy as sa

revision = 'w0x1y2z3a4b5'
down_revision = 'v9w0x1y2z3a5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Drop old GLOBAL unique constraint on store_url ────────────────────────
    # The constraint name in Postgres is automatically 'shopify_stores_store_url_key'
    # We try both the auto-generated name and the explicit name to be safe.
    with op.get_context().autocommit_block():
        pass  # no DDL transaction needed for index ops in Postgres

    # Drop global unique index (Postgres auto-names it shopify_stores_store_url_key)
    try:
        op.drop_index('shopify_stores_store_url_key', table_name='shopify_stores')
    except Exception:
        pass  # may already be dropped or named differently

    try:
        op.drop_constraint('shopify_stores_store_url_key', 'shopify_stores', type_='unique')
    except Exception:
        pass  # ignore if not found

    # ── Add per-tenant composite unique constraint ────────────────────────────
    op.create_unique_constraint(
        'uq_shopify_stores_tenant_url',
        'shopify_stores',
        ['tenant_id', 'store_url'],
    )


def downgrade() -> None:
    # Restore global unique constraint (only if no duplicates across tenants)
    op.drop_constraint('uq_shopify_stores_tenant_url', 'shopify_stores', type_='unique')
    op.create_unique_constraint(
        'shopify_stores_store_url_key',
        'shopify_stores',
        ['store_url'],
    )
