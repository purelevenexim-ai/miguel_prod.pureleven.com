"""
Products Service
-----------------
All business logic for the Products module.
Thin router → fat service pattern.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.product import Product, ProductCatalogCategory, ProductCatalogType, ProductStatus
from app.models.employee import Employee
from app.models.inventory import InventoryMovement, InventorySummary
from app.core.tenant_utils import apply_tenant_filter, assert_tenant_ownership
from app.modules.products.schemas import (
    ProductCatalogCategoryCreate,
    ProductCatalogCategoryResponse,
    ProductCatalogCategoryUpdate,
    ProductCatalogTypeCreate,
    ProductCatalogTypeResponse,
    ProductCatalogTypeUpdate,
    ProductCreate, ProductUpdate, ProductFilters, ProductResponse,
    ProductTaxonomyTypeResponse,
)


DEFAULT_CATALOG_TAXONOMY: dict[str, list[str]] = {
    "Spices": ["Kerala Cardamom", "Black Pepper", "Clove", "Ceylon Cinnamon", "Cassia Cinnamon"],
    "Coffee": [],
    "Tea": [],
    "Honey": [],
}


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _next_product_code(db: Session, tenant_id) -> str:
    count = (
        db.query(func.count(Product.id))
        .filter(Product.tenant_id == tenant_id)
        .scalar()
    ) or 0
    return f"PROD-{str(count + 1).zfill(5)}"


def _ensure_product_code_unique(db: Session, tenant_id, product_code: str, exclude_product_id=None) -> str:
    code = product_code.strip().upper()
    query = db.query(Product).filter(
        Product.tenant_id == tenant_id,
        Product.product_code == code,
    )
    if exclude_product_id is not None:
        query = query.filter(Product.id != exclude_product_id)
    if query.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A product with Code '{code}' already exists.",
        )
    return code


def _get_catalog_type(db: Session, tenant_id, catalog_type_id: UUID) -> ProductCatalogType:
    catalog_type = db.query(ProductCatalogType).filter(
        ProductCatalogType.id == catalog_type_id,
        ProductCatalogType.tenant_id == tenant_id,
    ).first()
    if not catalog_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product type not found")
    return catalog_type


def _get_catalog_category(db: Session, tenant_id, catalog_category_id: UUID) -> ProductCatalogCategory:
    catalog_category = db.query(ProductCatalogCategory).filter(
        ProductCatalogCategory.id == catalog_category_id,
        ProductCatalogCategory.tenant_id == tenant_id,
    ).first()
    if not catalog_category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product category not found")
    return catalog_category


def _normalize_product_taxonomy_fields(db: Session, tenant_id, values: dict, existing_product: Product | None = None) -> None:
    category_id_supplied = "product_category_id" in values
    type_id_supplied = "product_type_id" in values
    category_value_supplied = "category" in values
    type_label_supplied = "type_label" in values

    catalog_type = None
    catalog_category = None

    product_type_id = values.get("product_type_id") if type_id_supplied else (existing_product.product_type_id if existing_product else None)
    product_category_id = values.get("product_category_id") if category_id_supplied else (existing_product.product_category_id if existing_product else None)

    if product_category_id:
        catalog_category = _get_catalog_category(db, tenant_id, product_category_id)
        if product_type_id and catalog_category.product_type_id != product_type_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected category does not belong to the selected product type.",
            )
        product_type_id = catalog_category.product_type_id

    if product_type_id:
        catalog_type = _get_catalog_type(db, tenant_id, product_type_id)

    if catalog_category:
        values["product_category_id"] = catalog_category.id
        values["category"] = catalog_category.name
    elif category_id_supplied and values.get("product_category_id") is None and not category_value_supplied:
        values["category"] = None

    if catalog_type:
        values["product_type_id"] = catalog_type.id
        values["type_label"] = catalog_type.name
    elif type_id_supplied and values.get("product_type_id") is None and not type_label_supplied:
        values["type_label"] = None


def _suggest_seeded_spice_category(product_name: str | None) -> str | None:
    normalized_name = (product_name or "").strip().lower()
    if not normalized_name:
        return None
    if "black pepper" in normalized_name:
        return "Black Pepper"
    if "cardamom" in normalized_name:
        return "Kerala Cardamom"
    if "cassia" in normalized_name:
        return "Cassia Cinnamon"
    if "clove" in normalized_name:
        return "Clove"
    if "ceylon" in normalized_name or ("cinnamon" in normalized_name and "cassia" not in normalized_name):
        return "Ceylon Cinnamon"
    return None


def _ensure_default_catalog_taxonomy(db: Session, current_user: Employee) -> None:
    tenant_id = current_user.tenant_id
    changed = False

    existing_types = db.query(ProductCatalogType).filter(
        ProductCatalogType.tenant_id == tenant_id,
    ).all()
    types_by_name = {row.name.strip().lower(): row for row in existing_types}
    categories_by_key: dict[tuple[UUID, str], ProductCatalogCategory] = {}

    existing_categories = db.query(ProductCatalogCategory).filter(
        ProductCatalogCategory.tenant_id == tenant_id,
    ).all()
    for category in existing_categories:
        categories_by_key[(category.product_type_id, category.name.strip().lower())] = category

    for type_name, category_names in DEFAULT_CATALOG_TAXONOMY.items():
        normalized_type_name = type_name.lower()
        catalog_type = types_by_name.get(normalized_type_name)
        if catalog_type is None:
            catalog_type = ProductCatalogType(
                tenant_id=tenant_id,
                name=type_name,
                is_active=True,
                created_by_id=current_user.id,
            )
            db.add(catalog_type)
            db.flush()
            types_by_name[normalized_type_name] = catalog_type
            changed = True
        elif not catalog_type.is_active:
            catalog_type.is_active = True
            changed = True

        for category_name in category_names:
            key = (catalog_type.id, category_name.lower())
            catalog_category = categories_by_key.get(key)
            if catalog_category is None:
                catalog_category = ProductCatalogCategory(
                    tenant_id=tenant_id,
                    product_type_id=catalog_type.id,
                    name=category_name,
                    is_active=True,
                    created_by_id=current_user.id,
                )
                db.add(catalog_category)
                db.flush()
                categories_by_key[key] = catalog_category
                changed = True
            elif not catalog_category.is_active:
                catalog_category.is_active = True
                changed = True

    spices_type = types_by_name.get("spices")
    if spices_type is not None:
        spice_categories = {
            key[1]: category
            for key, category in categories_by_key.items()
            if key[0] == spices_type.id
        }
        products = db.query(Product).filter(Product.tenant_id == tenant_id).all()
        for product in products:
            suggested_category_name = _suggest_seeded_spice_category(product.name)
            if not suggested_category_name:
                continue
            target_category = spice_categories.get(suggested_category_name.lower())
            if target_category is None:
                continue

            current_category_name = (product.category or "").strip().lower()
            has_specific_category = (
                product.product_category_id is not None
                and current_category_name not in {"", "spices", suggested_category_name.lower()}
                and product.product_category_id != target_category.id
            )
            if has_specific_category:
                continue

            if product.product_type_id != spices_type.id:
                product.product_type_id = spices_type.id
                changed = True
            if product.product_category_id != target_category.id:
                product.product_category_id = target_category.id
                changed = True
            if (product.type_label or "").strip() != spices_type.name:
                product.type_label = spices_type.name
                changed = True
            if (product.category or "").strip() != target_category.name:
                product.category = target_category.name
                changed = True

    if changed:
        db.commit()


# ─────────────────────────────────────────────────────────────
# CRUD
# ─────────────────────────────────────────────────────────────

def create_product(
    db: Session,
    data: ProductCreate,
    current_user: Employee,
) -> ProductResponse:
    create_fields = data.model_dump()
    _normalize_product_taxonomy_fields(db, current_user.tenant_id, create_fields)
    product_code = _next_product_code(db, current_user.tenant_id)
    if data.product_code:
        product_code = _ensure_product_code_unique(db, current_user.tenant_id, data.product_code)

    # SKU uniqueness check (within tenant)
    if data.sku:
        existing = (
            db.query(Product)
            .filter(
                Product.tenant_id == current_user.tenant_id,
                Product.sku == data.sku.strip(),
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A product with SKU '{data.sku}' already exists.",
            )

    # Name uniqueness check within same category (soft warning — not blocked)
    # If exact same name + category exists and is active, reject
    name_check = (
        db.query(Product)
        .filter(
            Product.tenant_id == current_user.tenant_id,
            Product.name == data.name.strip(),
            Product.status == ProductStatus.active,
        )
        .first()
    )
    if name_check:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An active product named '{data.name}' already exists. "
                   "Use a different name or update the existing product.",
        )

    product = Product(
        tenant_id       = current_user.tenant_id,
        product_code    = product_code,
        name            = data.name.strip(),
        sku             = data.sku.strip() if data.sku else None,
        description     = data.description,
        product_type_id = create_fields.get("product_type_id"),
        product_category_id = create_fields.get("product_category_id"),
        category        = create_fields.get("category").strip() if create_fields.get("category") else None,
        type_label      = create_fields.get("type_label").strip() if create_fields.get("type_label") else None,
        unit_price      = data.unit_price,
        cost_price      = data.cost_price,
        mrp             = data.mrp,
        unit            = data.unit,
        unit_value      = data.unit_value,
        unit_label      = data.unit_label.strip() if data.unit_label else None,
        hsn_code        = data.hsn_code.strip() if data.hsn_code else None,
        gst_rate        = data.gst_rate,
        tax_inclusive   = data.tax_inclusive,
        variation_name  = data.variation_name.strip() if data.variation_name else None,
        variation_of    = data.variation_of,
        variation_attributes = [a.model_dump() for a in data.variation_attributes] if data.variation_attributes else None,
        item_type       = data.item_type,
        pack_per_items  = data.pack_per_items,
        status          = data.status,
        created_by_id   = current_user.id,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return ProductResponse.model_validate(product)


def list_products(
    db: Session,
    filters: ProductFilters,
    current_user: Employee,
) -> dict:
    _ensure_default_catalog_taxonomy(db, current_user)
    q = apply_tenant_filter(
        db.query(Product), Product, current_user
    )

    # Status filter
    if filters.status:
        q = q.filter(Product.status == filters.status)

    if filters.product_type_id:
        q = q.filter(Product.product_type_id == filters.product_type_id)

    if filters.product_category_id:
        q = q.filter(Product.product_category_id == filters.product_category_id)

    # Item type filter
    if filters.item_type:
        q = q.filter(Product.item_type == filters.item_type)

    # Category filter
    if filters.category:
        q = q.filter(Product.category.ilike(f"%{filters.category}%"))

    # Search: name, sku, category, unit_label, variation
    if filters.search:
        term = f"%{filters.search}%"
        q = q.filter(
            or_(
                Product.name.ilike(term),
                Product.sku.ilike(term),
                Product.category.ilike(term),
                Product.type_label.ilike(term),
                Product.product_code.ilike(term),
                Product.unit_label.ilike(term),
                Product.variation_name.ilike(term),
            )
        )

    total = q.count()
    products = (
        q.order_by(Product.name.asc())
        .offset((filters.page - 1) * filters.page_size)
        .limit(filters.page_size)
        .all()
    )

    return {
        "total":     total,
        "page":      filters.page,
        "page_size": filters.page_size,
        "results":   [ProductResponse.model_validate(p) for p in products],
    }


def get_product(
    db: Session,
    product_id,
    current_user: Employee,
) -> ProductResponse:
    _ensure_default_catalog_taxonomy(db, current_user)
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    assert_tenant_ownership(product, current_user)
    return ProductResponse.model_validate(product)


def update_product(
    db: Session,
    product_id,
    data: ProductUpdate,
    current_user: Employee,
) -> ProductResponse:
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    assert_tenant_ownership(product, current_user)

    # SKU uniqueness check on update
    if data.sku is not None:
        conflict = (
            db.query(Product)
            .filter(
                Product.tenant_id == current_user.tenant_id,
                Product.sku == data.sku.strip(),
                Product.id != product_id,
            )
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Another product with SKU '{data.sku}' already exists.",
            )

    # Name uniqueness check on update (active products only)
    if data.name is not None:
        conflict = (
            db.query(Product)
            .filter(
                Product.tenant_id == current_user.tenant_id,
                Product.name == data.name.strip(),
                Product.status == ProductStatus.active,
                Product.id != product_id,
            )
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Another active product named '{data.name}' already exists.",
            )

    if data.product_code is not None:
        _ensure_product_code_unique(
            db,
            current_user.tenant_id,
            data.product_code,
            exclude_product_id=product_id,
        )

    update_fields = data.model_dump(exclude_unset=True)
    if {"product_type_id", "product_category_id", "type_label", "category"}.intersection(update_fields.keys()):
        _normalize_product_taxonomy_fields(db, current_user.tenant_id, update_fields, existing_product=product)
    for field, value in update_fields.items():
        if isinstance(value, str):
            value = value.strip() if value else None
        if field == "product_code" and value is not None:
            value = value.upper()
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return ProductResponse.model_validate(product)


def delete_product(
    db: Session,
    product_id,
    current_user: Employee,
    hard: bool = False,
) -> dict:
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    assert_tenant_ownership(product, current_user)

    if hard:
        name = product.name
        # Delete child variations first (products that reference this as parent)
        db.query(Product).filter(Product.variation_of == product_id).delete(synchronize_session=False)
        # Delete inventory records
        db.query(InventoryMovement).filter(InventoryMovement.product_id == product_id).delete(synchronize_session=False)
        db.query(InventorySummary).filter(InventorySummary.product_id == product_id).delete(synchronize_session=False)
        # Nullify FK references in vendor_products, invoice_items, purchase_items
        # (import inline to avoid circular imports)
        from app.models.vendor import VendorProduct
        db.query(VendorProduct).filter(VendorProduct.product_id == product_id).delete(synchronize_session=False)
        from app.models.invoice import InvoiceItem
        db.query(InvoiceItem).filter(InvoiceItem.product_id == product_id).update(
            {"product_id": None}, synchronize_session=False
        )
        from app.models.purchase import PurchaseItem
        db.query(PurchaseItem).filter(PurchaseItem.product_id == product_id).delete(synchronize_session=False)
        db.delete(product)
        db.commit()
        return {"message": f"Product '{name}' permanently deleted."}

    # Soft-delete: mark as discontinued instead of hard delete
    # This preserves order history that references this product name
    product.status = ProductStatus.discontinued
    db.commit()
    return {"message": f"Product '{product.name}' discontinued successfully."}


def list_categories(
    db: Session,
    current_user: Employee,
) -> list[str]:
    """Return distinct non-null categories for this tenant."""
    _ensure_default_catalog_taxonomy(db, current_user)
    taxonomy_rows = (
        db.query(ProductCatalogCategory.name)
        .join(ProductCatalogType, ProductCatalogType.id == ProductCatalogCategory.product_type_id)
        .filter(
            ProductCatalogCategory.tenant_id == current_user.tenant_id,
            ProductCatalogCategory.is_active.is_(True),
            ProductCatalogType.is_active.is_(True),
        )
        .order_by(ProductCatalogCategory.name.asc())
        .all()
    )
    rows = (
        db.query(Product.category)
        .filter(
            Product.tenant_id == current_user.tenant_id,
            Product.category.isnot(None),
        )
        .distinct()
        .order_by(Product.category.asc())
        .all()
    )
    names = {r[0] for r in rows if r[0]}
    names.update(r[0] for r in taxonomy_rows if r[0])
    return sorted(names)


def list_catalog_types(
    db: Session,
    current_user: Employee,
    include_inactive: bool = False,
) -> list[ProductCatalogTypeResponse]:
    _ensure_default_catalog_taxonomy(db, current_user)
    query = db.query(ProductCatalogType).filter(ProductCatalogType.tenant_id == current_user.tenant_id)
    if not include_inactive:
        query = query.filter(ProductCatalogType.is_active.is_(True))
    rows = query.order_by(ProductCatalogType.name.asc()).all()
    return [ProductCatalogTypeResponse.model_validate(row) for row in rows]


def create_catalog_type(
    db: Session,
    data: ProductCatalogTypeCreate,
    current_user: Employee,
) -> ProductCatalogTypeResponse:
    name = data.name.strip()
    existing = db.query(ProductCatalogType).filter(
        ProductCatalogType.tenant_id == current_user.tenant_id,
        func.lower(ProductCatalogType.name) == name.lower(),
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Product type '{name}' already exists.")
    row = ProductCatalogType(
        tenant_id=current_user.tenant_id,
        name=name,
        is_active=True,
        created_by_id=current_user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ProductCatalogTypeResponse.model_validate(row)


def update_catalog_type(
    db: Session,
    catalog_type_id,
    data: ProductCatalogTypeUpdate,
    current_user: Employee,
) -> ProductCatalogTypeResponse:
    row = _get_catalog_type(db, current_user.tenant_id, catalog_type_id)
    update_fields = data.model_dump(exclude_unset=True)
    if data.name is not None:
        name = data.name.strip()
        conflict = db.query(ProductCatalogType).filter(
            ProductCatalogType.tenant_id == current_user.tenant_id,
            func.lower(ProductCatalogType.name) == name.lower(),
            ProductCatalogType.id != catalog_type_id,
        ).first()
        if conflict:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Product type '{name}' already exists.")
        row.name = name
        db.query(Product).filter(
            Product.tenant_id == current_user.tenant_id,
            Product.product_type_id == catalog_type_id,
        ).update({"type_label": name}, synchronize_session=False)
    if "is_active" in update_fields:
        row.is_active = update_fields["is_active"]
    db.commit()
    db.refresh(row)
    return ProductCatalogTypeResponse.model_validate(row)


def delete_catalog_type(
    db: Session,
    catalog_type_id,
    current_user: Employee,
    hard: bool = False,
) -> dict:
    row = _get_catalog_type(db, current_user.tenant_id, catalog_type_id)
    if hard:
        category_count = db.query(func.count(ProductCatalogCategory.id)).filter(
            ProductCatalogCategory.tenant_id == current_user.tenant_id,
            ProductCatalogCategory.product_type_id == catalog_type_id,
        ).scalar() or 0
        if category_count:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Delete categories under this type before permanently deleting the type.",
            )
        db.query(Product).filter(
            Product.tenant_id == current_user.tenant_id,
            Product.product_type_id == catalog_type_id,
        ).update({"product_type_id": None}, synchronize_session=False)
        db.delete(row)
        db.commit()
        return {"message": f"Product type '{row.name}' deleted permanently."}
    row.is_active = False
    db.commit()
    return {"message": f"Product type '{row.name}' archived."}


def list_catalog_categories(
    db: Session,
    current_user: Employee,
    include_inactive: bool = False,
    product_type_id: UUID | None = None,
) -> list[ProductCatalogCategoryResponse]:
    _ensure_default_catalog_taxonomy(db, current_user)
    query = db.query(ProductCatalogCategory).filter(ProductCatalogCategory.tenant_id == current_user.tenant_id)
    if product_type_id:
        query = query.filter(ProductCatalogCategory.product_type_id == product_type_id)
    if not include_inactive:
        query = query.filter(ProductCatalogCategory.is_active.is_(True))
        query = query.join(ProductCatalogType, ProductCatalogType.id == ProductCatalogCategory.product_type_id).filter(ProductCatalogType.is_active.is_(True))
    rows = query.order_by(ProductCatalogCategory.name.asc()).all()
    return [ProductCatalogCategoryResponse.model_validate(row) for row in rows]


def create_catalog_category(
    db: Session,
    data: ProductCatalogCategoryCreate,
    current_user: Employee,
) -> ProductCatalogCategoryResponse:
    catalog_type = _get_catalog_type(db, current_user.tenant_id, data.product_type_id)
    name = data.name.strip()
    existing = db.query(ProductCatalogCategory).filter(
        ProductCatalogCategory.tenant_id == current_user.tenant_id,
        ProductCatalogCategory.product_type_id == data.product_type_id,
        func.lower(ProductCatalogCategory.name) == name.lower(),
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Category '{name}' already exists under {catalog_type.name}.")
    row = ProductCatalogCategory(
        tenant_id=current_user.tenant_id,
        product_type_id=data.product_type_id,
        name=name,
        is_active=True,
        created_by_id=current_user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ProductCatalogCategoryResponse.model_validate(row)


def update_catalog_category(
    db: Session,
    catalog_category_id,
    data: ProductCatalogCategoryUpdate,
    current_user: Employee,
) -> ProductCatalogCategoryResponse:
    row = _get_catalog_category(db, current_user.tenant_id, catalog_category_id)
    update_fields = data.model_dump(exclude_unset=True)
    target_type_id = data.product_type_id if data.product_type_id is not None else row.product_type_id
    target_type = _get_catalog_type(db, current_user.tenant_id, target_type_id)
    target_name = data.name.strip() if data.name is not None else row.name
    conflict = db.query(ProductCatalogCategory).filter(
        ProductCatalogCategory.tenant_id == current_user.tenant_id,
        ProductCatalogCategory.product_type_id == target_type_id,
        func.lower(ProductCatalogCategory.name) == target_name.lower(),
        ProductCatalogCategory.id != catalog_category_id,
    ).first()
    if conflict:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Category '{target_name}' already exists under {target_type.name}.")
    row.product_type_id = target_type_id
    row.name = target_name
    if "is_active" in update_fields:
        row.is_active = update_fields["is_active"]
    db.query(Product).filter(
        Product.tenant_id == current_user.tenant_id,
        Product.product_category_id == catalog_category_id,
    ).update(
        {
            "product_type_id": target_type_id,
            "product_category_id": catalog_category_id,
            "type_label": target_type.name,
            "category": target_name,
        },
        synchronize_session=False,
    )
    db.commit()
    db.refresh(row)
    return ProductCatalogCategoryResponse.model_validate(row)


def delete_catalog_category(
    db: Session,
    catalog_category_id,
    current_user: Employee,
    hard: bool = False,
) -> dict:
    row = _get_catalog_category(db, current_user.tenant_id, catalog_category_id)
    if hard:
        db.query(Product).filter(
            Product.tenant_id == current_user.tenant_id,
            Product.product_category_id == catalog_category_id,
        ).update({"product_category_id": None}, synchronize_session=False)
        db.delete(row)
        db.commit()
        return {"message": f"Product category '{row.name}' deleted permanently."}
    row.is_active = False
    db.commit()
    return {"message": f"Product category '{row.name}' archived."}


def get_taxonomy(
    db: Session,
    current_user: Employee,
    include_inactive: bool = False,
) -> list[ProductTaxonomyTypeResponse]:
    _ensure_default_catalog_taxonomy(db, current_user)
    types_query = db.query(ProductCatalogType).filter(ProductCatalogType.tenant_id == current_user.tenant_id)
    categories_query = db.query(ProductCatalogCategory).filter(ProductCatalogCategory.tenant_id == current_user.tenant_id)
    if not include_inactive:
        types_query = types_query.filter(ProductCatalogType.is_active.is_(True))
        categories_query = categories_query.filter(ProductCatalogCategory.is_active.is_(True))
    types = types_query.order_by(ProductCatalogType.name.asc()).all()
    categories = categories_query.order_by(ProductCatalogCategory.name.asc()).all()
    categories_by_type: dict[UUID, list[ProductCatalogCategoryResponse]] = {}
    for category in categories:
        categories_by_type.setdefault(category.product_type_id, []).append(ProductCatalogCategoryResponse.model_validate(category))
    return [
        ProductTaxonomyTypeResponse(
            **ProductCatalogTypeResponse.model_validate(catalog_type).model_dump(),
            categories=categories_by_type.get(catalog_type.id, []),
        )
        for catalog_type in types
    ]


# ─────────────────────────────────────────────────────────────
# Batch operations
# ─────────────────────────────────────────────────────────────

def batch_update_status(
    db: Session,
    product_ids: list,
    new_status: ProductStatus,
    current_user: Employee,
) -> dict:
    """Update status for a list of products owned by this tenant."""
    updated = (
        db.query(Product)
        .filter(
            Product.tenant_id == current_user.tenant_id,
            Product.id.in_(product_ids),
        )
        .update({"status": new_status}, synchronize_session=False)
    )
    db.commit()
    return {"updated": updated, "status": new_status.value}


def batch_delete(
    db: Session,
    product_ids: list,
    current_user: Employee,
    hard: bool = False,
) -> dict:
    """Delete or discontinue a batch of products owned by this tenant."""
    owned_products = (
        db.query(Product)
        .filter(
            Product.tenant_id == current_user.tenant_id,
            Product.id.in_(product_ids),
        )
        .all()
    )
    if not owned_products:
        return {"deleted": 0}

    if hard:
        ids = [p.id for p in owned_products]
        # Remove child variants first
        db.query(Product).filter(Product.variation_of.in_(ids)).delete(synchronize_session=False)
        # Remove inventory records
        db.query(InventoryMovement).filter(InventoryMovement.product_id.in_(ids)).delete(synchronize_session=False)
        db.query(InventorySummary).filter(InventorySummary.product_id.in_(ids)).delete(synchronize_session=False)
        # Nullify FK refs
        from app.models.vendor import VendorProduct
        db.query(VendorProduct).filter(VendorProduct.product_id.in_(ids)).delete(synchronize_session=False)
        from app.models.invoice import InvoiceItem
        db.query(InvoiceItem).filter(InvoiceItem.product_id.in_(ids)).update(
            {"product_id": None}, synchronize_session=False
        )
        from app.models.purchase import PurchaseItem
        db.query(PurchaseItem).filter(PurchaseItem.product_id.in_(ids)).delete(synchronize_session=False)
        for p in owned_products:
            db.delete(p)
        db.commit()
        return {"deleted": len(owned_products), "hard": True}

    # Soft delete
    db.query(Product).filter(
        Product.tenant_id == current_user.tenant_id,
        Product.id.in_([p.id for p in owned_products]),
    ).update({"status": ProductStatus.discontinued}, synchronize_session=False)
    db.commit()
    return {"deleted": len(owned_products), "hard": False}
