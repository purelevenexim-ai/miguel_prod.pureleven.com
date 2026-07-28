from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.vendor import Vendor, VendorProduct
from app.models.product import Product
from app.models.purchase import PurchaseOrder, PurchaseOrderItem
from app.models.employee import Employee
from app.core.tenant_utils import apply_tenant_filter, assert_tenant_ownership
from app.modules.vendors.schemas import (
    VendorCreate, VendorUpdate,
    VendorProductCreate, VendorProductUpdate,
    VendorProductResponse, ProductSourcingEntry,
)


def _next_vendor_code(db: Session, tenant_id) -> str:
    """Use MAX of existing code numbers to avoid duplicates after soft-deletes."""
    rows = db.query(Vendor.vendor_code).filter(Vendor.tenant_id == tenant_id).all()
    max_n = 0
    for (code,) in rows:
        try:
            n = int(code.split("-")[1])
            if n > max_n:
                max_n = n
        except (IndexError, ValueError):
            pass
    return f"VEND-{str(max_n + 1).zfill(5)}"


def _enrich_vendor_product(vp: VendorProduct) -> VendorProductResponse:
    """Add computed fields to VendorProductResponse."""
    resp = VendorProductResponse.model_validate(vp)
    if vp.product:
        resp.product_name = vp.product.name
        resp.product_code = vp.product.product_code
        resp.product_unit = vp.product.unit.value if vp.product.unit else None
    # Landed cost per unit = price + gst + transport (per unit if min_order_qty given)
    if vp.unit_price is not None:
        price     = Decimal(str(vp.unit_price))
        gst_amt   = price * Decimal(str(vp.gst_percent or 0)) / Decimal("100")
        transport = Decimal(str(vp.transport_charge or 0))
        resp.landed_cost = (price + gst_amt + transport).quantize(Decimal("0.01"))
    return resp


# ─────────────────────────────────────────────────────────────────────────────
# Vendor CRUD
# ─────────────────────────────────────────────────────────────────────────────

def create_vendor(db: Session, data: VendorCreate, current_user: Employee) -> Vendor:
    vendor = Vendor(
        tenant_id=current_user.tenant_id,
        vendor_code=_next_vendor_code(db, current_user.tenant_id),
        **data.model_dump(),
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


def list_vendors(
    db: Session,
    current_user: Employee,
    search: str | None = None,
    is_active: bool | None = True,
    product_id: UUID | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    query = db.query(Vendor)
    query = apply_tenant_filter(query, Vendor, current_user)
    if is_active is not None:
        query = query.filter(Vendor.is_active == is_active)
    if search:
        q = f"%{search}%"
        query = query.filter(
            Vendor.company_name.ilike(q) |
            Vendor.vendor_code.ilike(q)  |
            Vendor.phone.ilike(q)        |
            Vendor.city.ilike(q)         |
            Vendor.gst_number.ilike(q)
        )
    if product_id:
        # Filter only vendors that supply this product
        query = query.join(
            VendorProduct,
            (VendorProduct.vendor_id == Vendor.id) & (VendorProduct.product_id == product_id)
        )
    total = query.count()
    data  = query.order_by(Vendor.is_preferred.desc(), Vendor.company_name).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size, "data": data}


def get_vendor(db: Session, vendor_id: UUID, current_user: Employee) -> Vendor:
    obj = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Vendor not found")
    assert_tenant_ownership(obj, current_user)
    return obj


def update_vendor(db: Session, vendor_id: UUID, data: VendorUpdate, current_user: Employee) -> Vendor:
    obj = get_vendor(db, vendor_id, current_user)
    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, val)
    db.commit()
    db.refresh(obj)
    return obj


def delete_vendor(db: Session, vendor_id: UUID, current_user: Employee) -> None:
    obj = get_vendor(db, vendor_id, current_user)
    obj.is_active = False
    db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Vendor Product Catalog
# ─────────────────────────────────────────────────────────────────────────────

def list_vendor_products(
    db: Session, vendor_id: UUID, current_user: Employee
) -> list[VendorProductResponse]:
    vendor = get_vendor(db, vendor_id, current_user)
    rows = (
        db.query(VendorProduct)
        .filter(VendorProduct.vendor_id == vendor.id)
        .all()
    )
    return [_enrich_vendor_product(r) for r in rows]


def upsert_vendor_product(
    db: Session, vendor_id: UUID, data: VendorProductCreate, current_user: Employee
) -> VendorProductResponse:
    vendor = get_vendor(db, vendor_id, current_user)
    # Validate product belongs to tenant
    product = db.query(Product).filter(
        Product.id == data.product_id,
        Product.tenant_id == current_user.tenant_id,
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    existing = db.query(VendorProduct).filter(
        VendorProduct.vendor_id == vendor.id,
        VendorProduct.product_id == data.product_id,
    ).first()

    if existing:
        for field, val in data.model_dump(exclude_unset=True).items():
            setattr(existing, field, val)
        existing.price_updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return _enrich_vendor_product(existing)
    else:
        vp = VendorProduct(
            tenant_id=current_user.tenant_id,
            vendor_id=vendor.id,
            price_updated_at=datetime.now(timezone.utc),
            **data.model_dump(),
        )
        db.add(vp)
        db.commit()
        db.refresh(vp)
        return _enrich_vendor_product(vp)


def update_vendor_product(
    db: Session, vp_id: UUID, data: VendorProductUpdate, current_user: Employee
) -> VendorProductResponse:
    vp = db.query(VendorProduct).filter(VendorProduct.id == vp_id).first()
    if not vp:
        raise HTTPException(status_code=404, detail="Vendor product not found")
    # Verify tenant ownership via vendor
    get_vendor(db, vp.vendor_id, current_user)
    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(vp, field, val)
    vp.price_updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(vp)
    return _enrich_vendor_product(vp)


def delete_vendor_product(db: Session, vp_id: UUID, current_user: Employee) -> None:
    vp = db.query(VendorProduct).filter(VendorProduct.id == vp_id).first()
    if not vp:
        raise HTTPException(status_code=404, detail="Vendor product not found")
    get_vendor(db, vp.vendor_id, current_user)
    db.delete(vp)
    db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Product Sourcing Intelligence
# ─────────────────────────────────────────────────────────────────────────────

def get_product_sourcing(
    db: Session, product_id: UUID, current_user: Employee
) -> list[ProductSourcingEntry]:
    """Get all vendors who supply a specific product, with pricing intelligence."""
    rows = (
        db.query(VendorProduct, Vendor)
        .join(Vendor, VendorProduct.vendor_id == Vendor.id)
        .filter(
            VendorProduct.product_id == product_id,
            Vendor.tenant_id == current_user.tenant_id,
            Vendor.is_active == True,
        )
        .order_by(Vendor.is_preferred.desc(), VendorProduct.unit_price.asc())
        .all()
    )
    result = []
    for vp, v in rows:
        price   = Decimal(str(vp.unit_price))
        gst_amt = price * Decimal(str(vp.gst_percent or 0)) / Decimal("100")
        transport = Decimal(str(vp.transport_charge or 0))
        landed_cost = (price + gst_amt + transport).quantize(Decimal("0.01"))
        result.append(ProductSourcingEntry(
            vendor_id         = v.id,
            vendor_code       = v.vendor_code,
            company_name      = v.company_name,
            city              = v.city,
            state             = v.state,
            phone             = v.phone,
            whatsapp          = v.whatsapp,
            is_preferred      = v.is_preferred,
            unit_price        = vp.unit_price,
            gst_percent       = vp.gst_percent,
            transport_charge  = vp.transport_charge,
            transport_method  = vp.transport_method,
            lead_time_days    = vp.lead_time_days,
            reorder_cycle_days= vp.reorder_cycle_days,
            landed_cost       = landed_cost,
            price_updated_at  = vp.price_updated_at,
        ))
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Purchase History per Vendor
# ─────────────────────────────────────────────────────────────────────────────

def get_vendor_purchase_history(
    db: Session, vendor_id: UUID, current_user: Employee, limit: int = 20
) -> list[dict]:
    vendor = get_vendor(db, vendor_id, current_user)
    orders = (
        db.query(PurchaseOrder)
        .filter(
            PurchaseOrder.vendor_id == vendor.id,
            PurchaseOrder.tenant_id == current_user.tenant_id,
        )
        .order_by(PurchaseOrder.created_at.desc())
        .limit(limit)
        .all()
    )
    result = []
    for po in orders:
        items = db.query(PurchaseOrderItem).filter(
            PurchaseOrderItem.purchase_order_id == po.id
        ).all()
        items_data = []
        for item in items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            items_data.append({
                "product_id":   str(item.product_id),
                "product_name": product.name if product else "Unknown",
                "product_unit": product.unit.value if product and product.unit else None,
                "quantity":     float(item.quantity),
                "unit_cost":    float(item.unit_cost),
                "tax_percent":  float(item.tax_percent),
                "tax_amount":   float(item.tax_amount),
                "line_total":   float(item.line_total),
            })
        result.append({
            "id":              str(po.id),
            "po_number":       po.po_number,
            "status":          po.status.value,
            "total_amount":    float(po.total_amount),
            "tax_amount":      float(po.tax_amount),
            "grand_total":     float(po.grand_total),
            "expected_delivery_date": po.expected_delivery_date.isoformat() if po.expected_delivery_date else None,
            "received_at":     po.received_at.isoformat() if po.received_at else None,
            "created_at":      po.created_at.isoformat() if po.created_at else None,
            "notes":           po.notes,
            "items":           items_data,
        })
    return result
