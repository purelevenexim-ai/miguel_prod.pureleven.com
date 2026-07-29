"""add high-impact composite indexes for orders workloads

Revision ID: b1c2d3e4f5a6
Revises: a0b1c2d3e4f5
Create Date: 2026-05-01 00:00:00.000000

"""

from alembic import op


revision = "b1c2d3e4f5a6"
down_revision = "a0b1c2d3e4f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tenant-scoped status listing/sorting path used by orders list APIs.
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_orders_tenant_status_created
        ON orders (tenant_id, status, created_at DESC)
        """
    )

    # Tenant-scoped active listing/sorting path used for active/inactive filters.
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_orders_tenant_active_created
        ON orders (tenant_id, is_active, created_at DESC)
        """
    )

    # Payment dashboard and settlement views.
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_orders_tenant_payment_created
        ON orders (tenant_id, payment_status, created_at DESC)
        """
    )

    # Order timeline/status history retrieval.
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_order_status_history_order_created
        ON order_status_history (order_id, created_at DESC)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_order_status_history_order_created")
    op.execute("DROP INDEX IF EXISTS ix_orders_tenant_payment_created")
    op.execute("DROP INDEX IF EXISTS ix_orders_tenant_active_created")
    op.execute("DROP INDEX IF EXISTS ix_orders_tenant_status_created")
