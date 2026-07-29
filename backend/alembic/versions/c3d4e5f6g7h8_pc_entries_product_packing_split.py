"""pc entries: product_id, consumption_rate, description; packing split

Revision ID: c3d4e5f6g7h8
Revises: a1b2c3d4e5g6, b1c2d3e4f5a6
Create Date: 2026-05-01

Changes:
  1. pc_entries: rename label → description (safe: ADD description, copy, DROP label)
  2. pc_entries: ADD product_id (FK to products, nullable)
  3. pc_entries: ADD consumption_rate (numeric, nullable)
  4. pc_groups:  ADD sub_type (varchar, nullable)
  5. Data: rename existing 'Packing' groups to 'Packing Materials', set sub_type
  6. Data: insert 'Courier Materials' group for tenants that have Packing Materials
"""

from alembic import op
import sqlalchemy as sa

revision = 'c3d4e5f6g7h8'
down_revision = ('a1b2c3d4e5g6', 'b1c2d3e4f5a6')
branch_labels = None
depends_on = None


def col_exists(table: str, column: str) -> bool:
    res = op.get_bind().execute(
        sa.text("""
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_name = :t AND column_name = :c
        """),
        {"t": table, "c": column}
    ).scalar()
    return bool(res)


def upgrade():
    conn = op.get_bind()

    # ── 1 & 2: pc_entries — rename label → description ────────
    if not col_exists("pc_entries", "description"):
        if col_exists("pc_entries", "label"):
            # Add new column, copy data, drop old
            op.add_column("pc_entries", sa.Column("description", sa.String(255), nullable=True))
            conn.execute(sa.text("UPDATE pc_entries SET description = label"))
            conn.execute(sa.text("ALTER TABLE pc_entries ALTER COLUMN description SET NOT NULL"))
            op.drop_column("pc_entries", "label")
        else:
            # Neither exists — fresh table, just add description
            op.add_column("pc_entries", sa.Column("description", sa.String(255), nullable=False, server_default=""))

    # ── 3: pc_entries — add product_id (FK to products) ───────
    if not col_exists("pc_entries", "product_id"):
        op.add_column("pc_entries", sa.Column(
            "product_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="SET NULL"),
            nullable=True
        ))
        conn.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS ix_pc_entries_product_id
            ON pc_entries (product_id)
        """))

    # ── 4: pc_entries — add consumption_rate ──────────────────
    if not col_exists("pc_entries", "consumption_rate"):
        op.add_column("pc_entries", sa.Column(
            "consumption_rate", sa.Numeric(10, 4), nullable=True
        ))

    # ── 5: pc_groups — add sub_type ───────────────────────────
    if not col_exists("pc_groups", "sub_type"):
        op.add_column("pc_groups", sa.Column("sub_type", sa.String(30), nullable=True))

    # ── 6: data migrations ────────────────────────────────────
    # Rename 'Packing' → 'Packing Materials' + set sub_type
    conn.execute(sa.text("""
        UPDATE pc_groups
        SET name = 'Packing Materials', sub_type = 'packing_material'
        WHERE name = 'Packing' AND is_system = TRUE
    """))

    # Set sub_type on existing 'Packing Materials' rows that don't have it
    conn.execute(sa.text("""
        UPDATE pc_groups
        SET sub_type = 'packing_material'
        WHERE name = 'Packing Materials' AND sub_type IS NULL AND is_system = TRUE
    """))

    # Insert 'Courier Materials' for each tenant that has 'Packing Materials' but not yet 'Courier Materials'
    conn.execute(sa.text("""
        INSERT INTO pc_groups (id, tenant_id, name, group_type, sub_type, sort_order, is_system, is_active, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            pm.tenant_id,
            'Courier Materials',
            'packaging',
            'courier_material',
            25,
            TRUE,
            TRUE,
            NOW(),
            NOW()
        FROM pc_groups pm
        WHERE pm.name = 'Packing Materials' AND pm.is_system = TRUE
        AND NOT EXISTS (
            SELECT 1 FROM pc_groups cm
            WHERE cm.tenant_id = pm.tenant_id AND cm.name = 'Courier Materials'
        )
    """))


def downgrade():
    conn = op.get_bind()

    # Remove Courier Materials rows added by this migration
    conn.execute(sa.text(
        "DELETE FROM pc_groups WHERE name = 'Courier Materials' AND is_system = TRUE"
    ))

    # Revert Packing Materials → Packing
    conn.execute(sa.text("""
        UPDATE pc_groups SET name = 'Packing', sub_type = NULL
        WHERE name = 'Packing Materials' AND is_system = TRUE
    """))

    # Restore label column from description
    if col_exists("pc_entries", "label"):
        pass  # already has label, nothing to do
    elif col_exists("pc_entries", "description"):
        op.add_column("pc_entries", sa.Column("label", sa.String(255), nullable=True))
        conn.execute(sa.text("UPDATE pc_entries SET label = description"))
        conn.execute(sa.text("ALTER TABLE pc_entries ALTER COLUMN label SET NOT NULL"))
        op.drop_column("pc_entries", "description")

    # Remove added columns
    if col_exists("pc_entries", "consumption_rate"):
        op.drop_column("pc_entries", "consumption_rate")
    if col_exists("pc_entries", "product_id"):
        conn.execute(sa.text("DROP INDEX IF EXISTS ix_pc_entries_product_id"))
        op.drop_column("pc_entries", "product_id")
    if col_exists("pc_groups", "sub_type"):
        op.drop_column("pc_groups", "sub_type")
