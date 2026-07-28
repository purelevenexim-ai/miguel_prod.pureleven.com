"""add profit checker tables and product item_type

Revision ID: a1b2c3d4e5g6
Revises: z3a4b5c6d7e8
Create Date: 2026-05-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'a1b2c3d4e5g6'
down_revision = 'z3a4b5c6d7e8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    def col_exists(table, col):
        r = conn.execute(sa.text(
            "SELECT 1 FROM information_schema.columns WHERE table_name=:t AND column_name=:c"
        ), {"t": table, "c": col}).fetchone()
        return r is not None

    def type_exists(name):
        r = conn.execute(sa.text(
            "SELECT 1 FROM pg_type WHERE typname=:n"
        ), {"n": name}).fetchone()
        return r is not None

    def table_exists(name):
        r = conn.execute(sa.text(
            "SELECT 1 FROM information_schema.tables WHERE table_name=:n"
        ), {"n": name}).fetchone()
        return r is not None

    def index_exists(name):
        r = conn.execute(sa.text(
            "SELECT 1 FROM pg_indexes WHERE indexname=:n"
        ), {"n": name}).fetchone()
        return r is not None

    # ── 1. Extend products: item_type + pack_per_items ──────────────────────
    if not type_exists('productitemtype'):
        op.execute("CREATE TYPE productitemtype AS ENUM ('sellable','raw_material','packaging','internal')")
    if not col_exists('products', 'item_type'):
        op.execute("ALTER TABLE products ADD COLUMN item_type productitemtype NOT NULL DEFAULT 'sellable'")
    if not col_exists('products', 'pack_per_items'):
        op.execute("ALTER TABLE products ADD COLUMN pack_per_items NUMERIC(6,2)")

    # ── 2. pc_groups ────────────────────────────────────────────────────────
    if not type_exists('pcgrouptype'):
        op.execute("CREATE TYPE pcgrouptype AS ENUM ('product_purchase','packaging','salary_ops','ads_marketing','sales','custom')")
    if not table_exists('pc_groups'):
        op.execute("""
            CREATE TABLE pc_groups (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id),
                name VARCHAR(100) NOT NULL,
                group_type pcgrouptype NOT NULL DEFAULT 'custom',
                sort_order INTEGER NOT NULL DEFAULT 100,
                is_system BOOLEAN NOT NULL DEFAULT false,
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE (tenant_id, name)
            )
        """)
    if not index_exists('ix_pc_groups_tenant_id'):
        op.execute("CREATE INDEX ix_pc_groups_tenant_id ON pc_groups(tenant_id)")

    # ── 3. pc_group_items ───────────────────────────────────────────────────
    if not type_exists('pcallocationtype'):
        op.execute("CREATE TYPE pcallocationtype AS ENUM ('monthly','per_order','per_unit')")
    if not table_exists('pc_group_items'):
        op.execute("""
            CREATE TABLE pc_group_items (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id),
                group_id UUID NOT NULL REFERENCES pc_groups(id),
                name VARCHAR(100) NOT NULL,
                allocation_type pcallocationtype NOT NULL DEFAULT 'monthly',
                product_id UUID REFERENCES products(id),
                items_per_trigger NUMERIC(6,2),
                is_active BOOLEAN NOT NULL DEFAULT true,
                sort_order INTEGER NOT NULL DEFAULT 100,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
    if not index_exists('ix_pc_group_items_tenant_group'):
        op.execute("CREATE INDEX ix_pc_group_items_tenant_group ON pc_group_items(tenant_id, group_id)")

    # ── 4. pc_entries ───────────────────────────────────────────────────────
    if not table_exists('pc_entries'):
        op.execute("""
            CREATE TABLE pc_entries (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id),
                group_id UUID NOT NULL REFERENCES pc_groups(id),
                item_id UUID REFERENCES pc_group_items(id),
                month VARCHAR(7) NOT NULL,
                label VARCHAR(255) NOT NULL,
                amount NUMERIC(14,2) NOT NULL DEFAULT 0,
                quantity NUMERIC(12,3),
                unit_cost NUMERIC(12,2),
                reference_po_id UUID REFERENCES purchase_orders(id),
                note TEXT,
                created_by_id UUID REFERENCES employees(id),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
    if not index_exists('ix_pc_entries_tenant_month'):
        op.execute("CREATE INDEX ix_pc_entries_tenant_month ON pc_entries(tenant_id, month)")
    if not index_exists('ix_pc_entries_group_id'):
        op.execute("CREATE INDEX ix_pc_entries_group_id ON pc_entries(group_id)")
    if not index_exists('ix_pc_entries_po_id'):
        op.execute("CREATE INDEX ix_pc_entries_po_id ON pc_entries(reference_po_id)")

    # ── 5. pc_product_maps ──────────────────────────────────────────────────
    if not table_exists('pc_product_maps'):
        op.execute("""
            CREATE TABLE pc_product_maps (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id),
                source_product_id UUID NOT NULL REFERENCES products(id),
                target_product_id UUID NOT NULL REFERENCES products(id),
                conversion_ratio NUMERIC(10,6) NOT NULL DEFAULT 1.0,
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE (tenant_id, source_product_id, target_product_id)
            )
        """)
    if not index_exists('ix_pc_product_maps_tenant_source'):
        op.execute("CREATE INDEX ix_pc_product_maps_tenant_source ON pc_product_maps(tenant_id, source_product_id)")

    # ── 6. pc_period_snapshots ──────────────────────────────────────────────
    if not table_exists('pc_period_snapshots'):
        op.execute("""
            CREATE TABLE pc_period_snapshots (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id),
                period VARCHAR(10) NOT NULL,
                period_type VARCHAR(10) NOT NULL DEFAULT 'monthly',
                sales_revenue NUMERIC(14,2) NOT NULL DEFAULT 0,
                order_count INTEGER NOT NULL DEFAULT 0,
                cogs NUMERIC(14,2) NOT NULL DEFAULT 0,
                packaging_cost NUMERIC(14,2) NOT NULL DEFAULT 0,
                salary_ops_cost NUMERIC(14,2) NOT NULL DEFAULT 0,
                ads_marketing_cost NUMERIC(14,2) NOT NULL DEFAULT 0,
                other_cost NUMERIC(14,2) NOT NULL DEFAULT 0,
                total_expense NUMERIC(14,2) NOT NULL DEFAULT 0,
                opening_stock_value NUMERIC(14,2) NOT NULL DEFAULT 0,
                closing_stock_value NUMERIC(14,2) NOT NULL DEFAULT 0,
                purchases_value NUMERIC(14,2) NOT NULL DEFAULT 0,
                gross_profit NUMERIC(14,2) NOT NULL DEFAULT 0,
                net_profit NUMERIC(14,2) NOT NULL DEFAULT 0,
                margin_pct NUMERIC(7,2) NOT NULL DEFAULT 0,
                group_totals JSONB,
                is_locked BOOLEAN NOT NULL DEFAULT false,
                computed_at TIMESTAMPTZ DEFAULT NOW(),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE (tenant_id, period, period_type)
            )
        """)
    if not index_exists('ix_pc_period_snapshots_tenant_period'):
        op.execute("CREATE INDEX ix_pc_period_snapshots_tenant_period ON pc_period_snapshots(tenant_id, period)")

    # ── 7. pc_alerts ────────────────────────────────────────────────────────
    if not type_exists('pcalerttype'):
        op.execute("CREATE TYPE pcalerttype AS ENUM ('negative_order','negative_month','low_margin_sku','low_margin_month')")
    if not table_exists('pc_alerts'):
        op.execute("""
            CREATE TABLE pc_alerts (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id),
                alert_type pcalerttype NOT NULL,
                reference_id UUID,
                month VARCHAR(7) NOT NULL,
                message TEXT NOT NULL,
                severity VARCHAR(10) NOT NULL DEFAULT 'warning',
                is_dismissed BOOLEAN NOT NULL DEFAULT false,
                dismissed_at TIMESTAMPTZ,
                dismissed_by_id UUID REFERENCES employees(id),
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
    if not index_exists('ix_pc_alerts_tenant_month'):
        op.execute("CREATE INDEX ix_pc_alerts_tenant_month ON pc_alerts(tenant_id, month)")
    if not index_exists('ix_pc_alerts_tenant_dismissed'):
        op.execute("CREATE INDEX ix_pc_alerts_tenant_dismissed ON pc_alerts(tenant_id, is_dismissed)")


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS pc_alerts')
    op.execute('DROP TYPE IF EXISTS pcalerttype')
    op.execute('DROP TABLE IF EXISTS pc_period_snapshots')
    op.execute('DROP TABLE IF EXISTS pc_product_maps')
    op.execute('DROP TABLE IF EXISTS pc_entries')
    op.execute('DROP TABLE IF EXISTS pc_group_items')
    op.execute('DROP TYPE IF EXISTS pcallocationtype')
    op.execute('DROP TABLE IF EXISTS pc_groups')
    op.execute('DROP TYPE IF EXISTS pcgrouptype')
    op.execute('ALTER TABLE products DROP COLUMN IF EXISTS pack_per_items')
    op.execute('ALTER TABLE products DROP COLUMN IF EXISTS item_type')
    op.execute('DROP TYPE IF EXISTS productitemtype')
