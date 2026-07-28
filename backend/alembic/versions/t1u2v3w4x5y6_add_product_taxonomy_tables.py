"""add product taxonomy tables

Revision ID: t1u2v3w4x5y6
Revises: s1t2u3v4w5x6
Create Date: 2026-05-02 00:00:00.000000
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "t1u2v3w4x5y6"
down_revision = "s1t2u3v4w5x6"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists("product_catalog_types"):
        op.create_table(
            "product_catalog_types",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("employees.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
            sa.UniqueConstraint("tenant_id", "name", name="uq_product_catalog_type_tenant"),
        )
        op.create_index("ix_product_catalog_types_tenant_id", "product_catalog_types", ["tenant_id"], unique=False)
        op.create_index("ix_product_catalog_types_name", "product_catalog_types", ["name"], unique=False)

    if not _table_exists("product_catalog_categories"):
        op.create_table(
            "product_catalog_categories",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("product_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("product_catalog_types.id"), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("employees.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
            sa.UniqueConstraint("tenant_id", "product_type_id", "name", name="uq_product_catalog_category_tenant_type"),
        )
        op.create_index("ix_product_catalog_categories_tenant_id", "product_catalog_categories", ["tenant_id"], unique=False)
        op.create_index("ix_product_catalog_categories_type_id", "product_catalog_categories", ["product_type_id"], unique=False)
        op.create_index("ix_product_catalog_categories_name", "product_catalog_categories", ["name"], unique=False)

    if not _column_exists("products", "product_type_id"):
        op.add_column("products", sa.Column("product_type_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key("fk_products_product_type_id", "products", "product_catalog_types", ["product_type_id"], ["id"])
        op.create_index("ix_products_product_type_id", "products", ["product_type_id"], unique=False)

    if not _column_exists("products", "product_category_id"):
        op.add_column("products", sa.Column("product_category_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key("fk_products_product_category_id", "products", "product_catalog_categories", ["product_category_id"], ["id"])
        op.create_index("ix_products_product_category_id", "products", ["product_category_id"], unique=False)

    tenants = bind.execute(sa.text("SELECT id FROM tenants")).fetchall()
    seed_type_names = ["Spices", "Coffee", "Tea", "Honey"]
    spice_categories = ["Kerala Cardamom", "Black Pepper", "Ceylon Cinnamon", "Clove", "Cassia Cinnamon"]

    for (tenant_id,) in tenants:
        type_ids: dict[str, str] = {}
        for type_name in seed_type_names:
            row = bind.execute(sa.text(
                "SELECT id FROM product_catalog_types WHERE tenant_id = :tenant_id AND lower(name) = lower(:name)"
            ), {"tenant_id": tenant_id, "name": type_name}).fetchone()
            if row:
                type_ids[type_name] = str(row[0])
            else:
                new_id = str(uuid4())
                bind.execute(sa.text(
                    """
                    INSERT INTO product_catalog_types (id, tenant_id, name, is_active, created_at, updated_at)
                    VALUES (:id, :tenant_id, :name, true, now(), now())
                    """
                ), {"id": new_id, "tenant_id": tenant_id, "name": type_name})
                type_ids[type_name] = new_id

        for category_name in spice_categories:
            row = bind.execute(sa.text(
                """
                SELECT id FROM product_catalog_categories
                WHERE tenant_id = :tenant_id AND product_type_id = :type_id AND lower(name) = lower(:name)
                """
            ), {"tenant_id": tenant_id, "type_id": type_ids["Spices"], "name": category_name}).fetchone()
            if not row:
                bind.execute(sa.text(
                    """
                    INSERT INTO product_catalog_categories (id, tenant_id, product_type_id, name, is_active, created_at, updated_at)
                    VALUES (:id, :tenant_id, :type_id, :name, true, now(), now())
                    """
                ), {"id": str(uuid4()), "tenant_id": tenant_id, "type_id": type_ids["Spices"], "name": category_name})

        category_rows = bind.execute(sa.text(
            "SELECT id, name FROM product_catalog_categories WHERE tenant_id = :tenant_id"
        ), {"tenant_id": tenant_id}).fetchall()
        category_ids = {str(name): str(id_) for id_, name in category_rows}

        bind.execute(sa.text(
            """
            UPDATE products
            SET product_type_id = :type_id,
                type_label = 'Spices',
                product_category_id = :category_id,
                category = 'Black Pepper'
            WHERE tenant_id = :tenant_id AND name ILIKE 'Black Pepper%'
            """
        ), {"tenant_id": tenant_id, "type_id": type_ids["Spices"], "category_id": category_ids.get("Black Pepper")})

        bind.execute(sa.text(
            """
            UPDATE products
            SET product_type_id = :type_id,
                type_label = 'Spices',
                product_category_id = :category_id,
                category = 'Kerala Cardamom'
            WHERE tenant_id = :tenant_id AND name ILIKE 'Kerala Cardamom%'
            """
        ), {"tenant_id": tenant_id, "type_id": type_ids["Spices"], "category_id": category_ids.get("Kerala Cardamom")})

        bind.execute(sa.text(
            """
            UPDATE products
            SET product_type_id = :type_id,
                type_label = 'Spices',
                product_category_id = :category_id,
                category = 'Ceylon Cinnamon'
            WHERE tenant_id = :tenant_id AND (name ILIKE 'Ceylon True Cinnamon%' OR name ILIKE 'Ceylon Cinnamon%')
            """
        ), {"tenant_id": tenant_id, "type_id": type_ids["Spices"], "category_id": category_ids.get("Ceylon Cinnamon")})

        bind.execute(sa.text(
            """
            UPDATE products
            SET product_type_id = :type_id,
                type_label = 'Spices',
                product_category_id = :category_id,
                category = 'Clove'
            WHERE tenant_id = :tenant_id AND name ILIKE '%Clove%'
            """
        ), {"tenant_id": tenant_id, "type_id": type_ids["Spices"], "category_id": category_ids.get("Clove")})

        bind.execute(sa.text(
            """
            UPDATE products
            SET product_type_id = :type_id,
                type_label = 'Spices',
                product_category_id = :category_id,
                category = 'Cassia Cinnamon'
            WHERE tenant_id = :tenant_id AND name ILIKE '%Cassia%'
            """
        ), {"tenant_id": tenant_id, "type_id": type_ids["Spices"], "category_id": category_ids.get("Cassia Cinnamon")})


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    product_indexes = {idx["name"] for idx in inspector.get_indexes("products")}
    product_columns = {col["name"] for col in inspector.get_columns("products")}
    tables = set(inspector.get_table_names())

    if "ix_products_product_category_id" in product_indexes:
        op.drop_index("ix_products_product_category_id", table_name="products")
    if "product_category_id" in product_columns:
        fk_names = {fk["name"] for fk in inspector.get_foreign_keys("products")}
        if "fk_products_product_category_id" in fk_names:
            op.drop_constraint("fk_products_product_category_id", "products", type_="foreignkey")
        op.drop_column("products", "product_category_id")

    inspector = sa.inspect(op.get_bind())
    product_indexes = {idx["name"] for idx in inspector.get_indexes("products")}
    product_columns = {col["name"] for col in inspector.get_columns("products")}
    if "ix_products_product_type_id" in product_indexes:
        op.drop_index("ix_products_product_type_id", table_name="products")
    if "product_type_id" in product_columns:
        fk_names = {fk["name"] for fk in inspector.get_foreign_keys("products")}
        if "fk_products_product_type_id" in fk_names:
            op.drop_constraint("fk_products_product_type_id", "products", type_="foreignkey")
        op.drop_column("products", "product_type_id")

    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "product_catalog_categories" in tables:
        for idx_name in ["ix_product_catalog_categories_name", "ix_product_catalog_categories_type_id", "ix_product_catalog_categories_tenant_id"]:
            existing_indexes = {idx["name"] for idx in sa.inspect(op.get_bind()).get_indexes("product_catalog_categories")}
            if idx_name in existing_indexes:
                op.drop_index(idx_name, table_name="product_catalog_categories")
        op.drop_table("product_catalog_categories")

    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "product_catalog_types" in tables:
        for idx_name in ["ix_product_catalog_types_name", "ix_product_catalog_types_tenant_id"]:
            existing_indexes = {idx["name"] for idx in sa.inspect(op.get_bind()).get_indexes("product_catalog_types")}
            if idx_name in existing_indexes:
                op.drop_index(idx_name, table_name="product_catalog_types")
        op.drop_table("product_catalog_types")