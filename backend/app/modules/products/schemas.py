"""
Products Schemas
-----------------
Pydantic v2 schemas for the Products module.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator

from app.models.product import ProductUnit, ProductStatus, ProductItemType


class VariationAxis(BaseModel):
    """Single variation axis — e.g. {name: 'Size', values: ['100g', '250g']}."""
    name: str
    values: list[str]


# ─────────────────────────────────────────────────────────────
# Create
# ─────────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    product_code:   Optional[str]           = None
    name:           str
    sku:            Optional[str]           = None
    description:    Optional[str]           = None
    product_type_id: Optional[UUID]         = None
    product_category_id: Optional[UUID]     = None
    category:       Optional[str]           = None
    type_label:     Optional[str]           = None

    unit_price:     Decimal
    cost_price:     Optional[Decimal]       = None
    mrp:            Optional[Decimal]       = None

    unit:           ProductUnit             = ProductUnit.piece
    unit_value:     Optional[Decimal]       = None
    unit_label:     Optional[str]           = None   # "500g", "1kg"

    # GST / Tax
    hsn_code:       Optional[str]           = None
    gst_rate:       Optional[Decimal]       = None   # 0, 5, 12, 18, 28
    tax_inclusive:  bool                    = False

    # Variations
    variation_name:       Optional[str]              = None
    variation_of:         Optional[UUID]             = None
    variation_attributes: Optional[list[VariationAxis]] = None  # axes for variant generation

    item_type:      ProductItemType         = ProductItemType.sellable
    pack_per_items: Optional[Decimal]       = None

    status:         ProductStatus           = ProductStatus.active

    @field_validator("unit_price")
    @classmethod
    def price_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("unit_price must be greater than 0")
        return v

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name cannot be empty")
        return v

    @field_validator("product_code")
    @classmethod
    def product_code_clean(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip().upper()
        return v or None

    @field_validator("type_label")
    @classmethod
    def type_label_clean(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v or None

    @field_validator("pack_per_items")
    @classmethod
    def pack_per_items_non_negative(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < 0:
            raise ValueError("pack_per_items must be 0 or greater")
        return v


# ─────────────────────────────────────────────────────────────
# Update  (all fields optional)
# ─────────────────────────────────────────────────────────────

class ProductUpdate(BaseModel):
    product_code:   Optional[str]           = None
    name:           Optional[str]           = None
    sku:            Optional[str]           = None
    description:    Optional[str]           = None
    product_type_id: Optional[UUID]         = None
    product_category_id: Optional[UUID]     = None
    category:       Optional[str]           = None
    type_label:     Optional[str]           = None

    unit_price:     Optional[Decimal]       = None
    cost_price:     Optional[Decimal]       = None
    mrp:            Optional[Decimal]       = None

    unit:           Optional[ProductUnit]   = None
    unit_value:     Optional[Decimal]       = None
    unit_label:     Optional[str]           = None

    hsn_code:       Optional[str]           = None
    gst_rate:       Optional[Decimal]       = None
    tax_inclusive:  Optional[bool]          = None

    variation_name:       Optional[str]              = None
    variation_of:         Optional[UUID]             = None
    variation_attributes: Optional[list[VariationAxis]] = None

    item_type:      Optional[ProductItemType] = None
    pack_per_items: Optional[Decimal]       = None

    status:         Optional[ProductStatus] = None

    @field_validator("unit_price")
    @classmethod
    def price_positive(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v <= 0:
            raise ValueError("unit_price must be greater than 0")
        return v

    @field_validator("product_code")
    @classmethod
    def update_product_code_clean(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip().upper()
        return v or None

    @field_validator("type_label")
    @classmethod
    def update_type_label_clean(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v or None

    @field_validator("pack_per_items")
    @classmethod
    def update_pack_per_items_non_negative(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < 0:
            raise ValueError("pack_per_items must be 0 or greater")
        return v


# ─────────────────────────────────────────────────────────────
# Response
# ─────────────────────────────────────────────────────────────

class ProductResponse(BaseModel):
    model_config = {"from_attributes": True}

    id:             UUID
    tenant_id:      UUID
    product_code:   str

    name:           str
    sku:            Optional[str]
    description:    Optional[str]
    product_type_id: Optional[UUID]
    product_category_id: Optional[UUID]
    category:       Optional[str]
    type_label:     Optional[str]

    unit_price:     Decimal
    cost_price:     Optional[Decimal]
    mrp:            Optional[Decimal]

    unit:           ProductUnit
    unit_value:     Optional[Decimal]
    unit_label:     Optional[str]

    hsn_code:       Optional[str]       = None
    gst_rate:       Optional[Decimal]   = None
    tax_inclusive:  bool                = False

    variation_name:       Optional[str]          = None
    variation_of:         Optional[UUID]         = None
    variation_attributes: Optional[Any]          = None  # list[dict] stored as JSONB

    item_type:      ProductItemType     = ProductItemType.sellable
    pack_per_items: Optional[Decimal]   = None

    status:         ProductStatus
    created_by_id:  UUID

    created_at:     Optional[str]
    updated_at:     Optional[str]

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def dt_to_str(cls, v) -> Optional[str]:
        if v is None:
            return None
        return str(v)


# ─────────────────────────────────────────────────────────────
# Filters  (for list endpoint query params)
# ─────────────────────────────────────────────────────────────

class ProductFilters(BaseModel):
    search:     Optional[str]           = None   # name / sku / category
    category:   Optional[str]           = None
    item_type:  Optional[ProductItemType] = None
    product_type_id: Optional[UUID]     = None
    product_category_id: Optional[UUID] = None
    status:     Optional[ProductStatus] = None
    page:       int                     = 1
    page_size:  int                     = 50


class ProductCatalogTypeCreate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def type_name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name cannot be empty")
        return v


class ProductCatalogTypeUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def update_type_name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("name cannot be empty")
        return v


class ProductCatalogTypeResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    tenant_id: UUID
    name: str
    is_active: bool
    created_by_id: Optional[UUID]
    created_at: Optional[str]
    updated_at: Optional[str]

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def type_dt_to_str(cls, v) -> Optional[str]:
        if v is None:
            return None
        return str(v)


class ProductCatalogCategoryCreate(BaseModel):
    product_type_id: UUID
    name: str

    @field_validator("name")
    @classmethod
    def category_name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name cannot be empty")
        return v


class ProductCatalogCategoryUpdate(BaseModel):
    product_type_id: Optional[UUID] = None
    name: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def update_category_name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("name cannot be empty")
        return v


class ProductCatalogCategoryResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    tenant_id: UUID
    product_type_id: UUID
    name: str
    is_active: bool
    created_by_id: Optional[UUID]
    created_at: Optional[str]
    updated_at: Optional[str]

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def category_dt_to_str(cls, v) -> Optional[str]:
        if v is None:
            return None
        return str(v)


class ProductTaxonomyTypeResponse(ProductCatalogTypeResponse):
    categories: list[ProductCatalogCategoryResponse] = []


# ─────────────────────────────────────────────────────────────
# Batch Operations
# ─────────────────────────────────────────────────────────────

class ProductBatchStatusUpdate(BaseModel):
    product_ids: list[UUID]
    status: ProductStatus

    @field_validator("product_ids")
    @classmethod
    def ids_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("product_ids cannot be empty")
        if len(v) > 500:
            raise ValueError("Cannot update more than 500 products at once")
        return v


class ProductBatchDelete(BaseModel):
    product_ids: list[UUID]
    hard: bool = False

    @field_validator("product_ids")
    @classmethod
    def batch_ids_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("product_ids cannot be empty")
        if len(v) > 500:
            raise ValueError("Cannot delete more than 500 products at once")
        return v
