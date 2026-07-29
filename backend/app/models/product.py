import enum
import uuid
from sqlalchemy import (
    Column, String, Boolean, Text, DateTime,
    Enum, ForeignKey, Numeric, UniqueConstraint, Index, Integer
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


# ─────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────

class ProductUnit(str, enum.Enum):
    kg      = "kg"
    gram    = "gram"
    litre   = "litre"
    ml      = "ml"
    piece   = "piece"
    bag     = "bag"
    box     = "box"
    carton  = "carton"
    bundle  = "bundle"
    pack    = "pack"


class ProductStatus(str, enum.Enum):
    active      = "active"
    inactive    = "inactive"
    discontinued = "discontinued"


class ProductItemType(str, enum.Enum):
    """
    Classification used by Profit Checker.
    - sellable:     customer-facing product (default)
    - raw_material: bulk purchase that feeds sellable variants (e.g. 50kg cardamom)
    - packaging:    consumed per order (e.g. corrugated box, pouch, sticker roll)
    - internal:     overhead item not allocated per order (e.g. office supplies)
    """
    sellable     = "sellable"
    raw_material = "raw_material"
    packaging    = "packaging"
    internal     = "internal"


class ProductCatalogType(Base):
    __tablename__ = "product_catalog_types"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id       = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name            = Column(String(100), nullable=False)
    is_active       = Column(Boolean, nullable=False, default=True)
    created_by_id   = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_product_catalog_type_tenant"),
        Index("ix_product_catalog_types_tenant_id", "tenant_id"),
        Index("ix_product_catalog_types_name", "name"),
    )


class ProductCatalogCategory(Base):
    __tablename__ = "product_catalog_categories"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id       = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    product_type_id = Column(UUID(as_uuid=True), ForeignKey("product_catalog_types.id"), nullable=False)
    name            = Column(String(100), nullable=False)
    is_active       = Column(Boolean, nullable=False, default=True)
    created_by_id   = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "product_type_id", "name", name="uq_product_catalog_category_tenant_type"),
        Index("ix_product_catalog_categories_tenant_id", "tenant_id"),
        Index("ix_product_catalog_categories_type_id", "product_type_id"),
        Index("ix_product_catalog_categories_name", "name"),
    )


# ─────────────────────────────────────────────────────────────
# Product (Master Catalog)
# ─────────────────────────────────────────────────────────────

class Product(Base):
    __tablename__ = "products"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id       = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    product_code    = Column(String(30), nullable=False)        # PROD-00001

    # ── Identity ─────────────────────────────────────────────
    name            = Column(String(255), nullable=False)
    sku             = Column(String(100), nullable=True)        # Stock Keeping Unit
    description     = Column(Text, nullable=True)
    product_type_id = Column(UUID(as_uuid=True), ForeignKey("product_catalog_types.id"), nullable=True)
    product_category_id = Column(UUID(as_uuid=True), ForeignKey("product_catalog_categories.id"), nullable=True)
    category        = Column(String(100), nullable=True)        # e.g. "Spices", "Dry Fruits"

    # ── Pricing ──────────────────────────────────────────────
    unit_price      = Column(Numeric(12, 2), nullable=False)    # selling price per unit
    cost_price      = Column(Numeric(12, 2), nullable=True)     # purchase / manufacturing cost
    mrp             = Column(Numeric(12, 2), nullable=True)     # max retail price

    # ── Unit / Weight ─────────────────────────────────────────
    unit            = Column(Enum(ProductUnit), nullable=False, default=ProductUnit.piece)
    unit_value      = Column(Numeric(10, 3), nullable=True)     # e.g. 0.500 for 500g bag
    # full label: "500g" or "1kg" — free text so seller can write what they like
    unit_label      = Column(String(50), nullable=True)         # e.g. "500g", "1kg", "250ml"

    # ── GST / Tax ────────────────────────────────────────────
    hsn_code        = Column(String(20),  nullable=True)        # e.g. "0910" for spices
    gst_rate        = Column(Numeric(5, 2), nullable=True, default=5) # 0, 5, 12, 18, 28
    tax_inclusive   = Column(Boolean, nullable=False, default=False)  # is unit_price inclusive of GST?

    # ── Variations ───────────────────────────────────────────
    variation_name  = Column(String(100), nullable=True)        # e.g. "100g / 250g / 500g"
    variation_of    = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)

    # ── Item type (Profit Checker) ────────────────────────────
    item_type       = Column(Enum(ProductItemType), nullable=False, default=ProductItemType.sellable)
    type_label      = Column(String(100), nullable=True)        # user-defined display type, e.g. "Loose Spice", "Courier Box"
    # For packaging items: how many units are consumed per order by default
    # e.g. 1 corrugated box per 4 ordered items → store 4 here, rule type in Profit Checker
    pack_per_items  = Column(Numeric(6, 2), nullable=True)

    # ── Variation Attributes ──────────────────────────────────
    # Stores axes used to generate variants, e.g.:
    # [{"name": "Size", "values": ["100g", "250g", "500g"]}]
    variation_attributes = Column(JSONB, nullable=True)

    # ── Status ───────────────────────────────────────────────
    status          = Column(Enum(ProductStatus), nullable=False, default=ProductStatus.active)

    # ── Ownership ────────────────────────────────────────────
    created_by_id   = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)

    # ── Timestamps ───────────────────────────────────────────
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    # ── Indexes + Constraints ─────────────────────────────────
    __table_args__ = (
        UniqueConstraint("tenant_id", "product_code", name="uq_product_code_tenant"),
        UniqueConstraint("tenant_id", "sku", name="uq_product_sku_tenant"),
        Index("ix_products_tenant_id",  "tenant_id"),
        Index("ix_products_name",       "name"),
        Index("ix_products_category",   "category"),
        Index("ix_products_product_type_id", "product_type_id"),
        Index("ix_products_product_category_id", "product_category_id"),
        Index("ix_products_status",     "status"),
        Index("ix_products_sku",        "sku"),
    )

    # ── Relationships ────────────────────────────────────────
    shipping_tariffs = relationship("ShippingTariff", back_populates="product")
