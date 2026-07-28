"""
Products Router
----------------
8 endpoints for the Products module.
Prefix: /api/products
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.auth.tenant import get_current_tenant_user, require_roles
from app.models.employee import RoleEnum
from app.modules.products.schemas import (
    ProductCatalogCategoryCreate,
    ProductCatalogCategoryResponse,
    ProductCatalogCategoryUpdate,
    ProductCatalogTypeCreate,
    ProductCatalogTypeResponse,
    ProductCatalogTypeUpdate,
    ProductCreate, ProductUpdate, ProductResponse, ProductFilters,
    ProductTaxonomyTypeResponse,
    ProductBatchStatusUpdate, ProductBatchDelete,
)
from app.modules.products import service

router = APIRouter(prefix="/api/products", tags=["Products"])

# Role guards
_admin_ops   = require_roles(RoleEnum.admin, RoleEnum.operations)
_all_roles   = require_roles(
    RoleEnum.admin, RoleEnum.operations, RoleEnum.sales,
    RoleEnum.support, RoleEnum.marketing,
)


# ─────────────────────────────────────────────────────────────
# POST /api/products
# ─────────────────────────────────────────────────────────────
@router.post("/", response_model=ProductResponse, status_code=201)
def create_product(
    data: ProductCreate,
    db: Session = Depends(get_db),
    current_user=Depends(_admin_ops),
):
    return service.create_product(db, data, current_user)


# ─────────────────────────────────────────────────────────────
# GET /api/products
# ─────────────────────────────────────────────────────────────
@router.get("/", response_model=dict)
def list_products(
    search:     Optional[str]   = Query(None),
    category:   Optional[str]   = Query(None),
    item_type:  Optional[str]   = Query(None),
    product_type_id: Optional[UUID] = Query(None),
    product_category_id: Optional[UUID] = Query(None),
    status:     Optional[str]   = Query(None),
    page:       int             = Query(1, ge=1),
    page_size:  int             = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    from app.models.product import ProductStatus, ProductItemType
    filters = ProductFilters(
        search=search,
        category=category,
        item_type=ProductItemType(item_type) if item_type else None,
        product_type_id=product_type_id,
        product_category_id=product_category_id,
        status=ProductStatus(status) if status else None,
        page=page,
        page_size=page_size,
    )
    return service.list_products(db, filters, current_user)


@router.get("/taxonomy", response_model=list[ProductTaxonomyTypeResponse])
def get_taxonomy(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    return service.get_taxonomy(db, current_user, include_inactive=include_inactive)


@router.get("/taxonomy/types", response_model=list[ProductCatalogTypeResponse])
def list_catalog_types(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    return service.list_catalog_types(db, current_user, include_inactive=include_inactive)


@router.post("/taxonomy/types", response_model=ProductCatalogTypeResponse, status_code=201)
def create_catalog_type(
    data: ProductCatalogTypeCreate,
    db: Session = Depends(get_db),
    current_user=Depends(_admin_ops),
):
    return service.create_catalog_type(db, data, current_user)


@router.patch("/taxonomy/types/{catalog_type_id}", response_model=ProductCatalogTypeResponse)
def update_catalog_type(
    catalog_type_id: UUID,
    data: ProductCatalogTypeUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(_admin_ops),
):
    return service.update_catalog_type(db, catalog_type_id, data, current_user)


@router.delete("/taxonomy/types/{catalog_type_id}", response_model=dict)
def delete_catalog_type(
    catalog_type_id: UUID,
    hard: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(_admin_ops),
):
    return service.delete_catalog_type(db, catalog_type_id, current_user, hard=hard)


@router.get("/taxonomy/categories", response_model=list[ProductCatalogCategoryResponse])
def list_catalog_categories(
    include_inactive: bool = Query(False),
    product_type_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    return service.list_catalog_categories(db, current_user, include_inactive=include_inactive, product_type_id=product_type_id)


@router.post("/taxonomy/categories", response_model=ProductCatalogCategoryResponse, status_code=201)
def create_catalog_category(
    data: ProductCatalogCategoryCreate,
    db: Session = Depends(get_db),
    current_user=Depends(_admin_ops),
):
    return service.create_catalog_category(db, data, current_user)


@router.patch("/taxonomy/categories/{catalog_category_id}", response_model=ProductCatalogCategoryResponse)
def update_catalog_category(
    catalog_category_id: UUID,
    data: ProductCatalogCategoryUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(_admin_ops),
):
    return service.update_catalog_category(db, catalog_category_id, data, current_user)


@router.delete("/taxonomy/categories/{catalog_category_id}", response_model=dict)
def delete_catalog_category(
    catalog_category_id: UUID,
    hard: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(_admin_ops),
):
    return service.delete_catalog_category(db, catalog_category_id, current_user, hard=hard)


# ─────────────────────────────────────────────────────────────
# GET /api/products/categories
# ─────────────────────────────────────────────────────────────
@router.get("/categories", response_model=list)
def list_categories(
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    return service.list_categories(db, current_user)


# ─────────────────────────────────────────────────────────────
# GET /api/products/{id}
# ─────────────────────────────────────────────────────────────
@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    return service.get_product(db, product_id, current_user)


# ─────────────────────────────────────────────────────────────
# PATCH /api/products/{id}
# ─────────────────────────────────────────────────────────────
@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: UUID,
    data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(_admin_ops),
):
    return service.update_product(db, product_id, data, current_user)


# ─────────────────────────────────────────────────────────────
# DELETE /api/products/{id}  (soft delete → discontinued, or hard=true for permanent)
# ─────────────────────────────────────────────────────────────
@router.delete("/{product_id}", response_model=dict)
def delete_product(
    product_id: UUID,
    hard: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(_admin_ops),
):
    return service.delete_product(db, product_id, current_user, hard=hard)


# ─────────────────────────────────────────────────────────────
# POST /api/products/batch-status  (bulk activate / deactivate)
# ─────────────────────────────────────────────────────────────
@router.post("/batch-status", response_model=dict)
def batch_update_status(
    data: ProductBatchStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(_admin_ops),
):
    return service.batch_update_status(db, data.product_ids, data.status, current_user)


# ─────────────────────────────────────────────────────────────
# POST /api/products/batch-delete  (bulk soft or hard delete)
# ─────────────────────────────────────────────────────────────
@router.post("/batch-delete", response_model=dict)
def batch_delete_products(
    data: ProductBatchDelete,
    db: Session = Depends(get_db),
    current_user=Depends(_admin_ops),
):
    return service.batch_delete(db, data.product_ids, current_user, hard=data.hard)
