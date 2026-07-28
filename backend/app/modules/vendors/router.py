from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.core.auth.tenant import get_current_tenant_user, require_roles
from app.models.employee import Employee, RoleEnum
from app.modules.vendors.schemas import (
    VendorCreate, VendorUpdate, VendorResponse,
    VendorProductCreate, VendorProductUpdate, VendorProductResponse,
    ProductSourcingEntry,
)
from app.modules.vendors import service

router = APIRouter(prefix="/api/vendors", tags=["Vendors"])


# ─────────────────────────────────────────────────────────────────────────────
# Vendor CRUD
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/", response_model=VendorResponse, status_code=201)
def create_vendor(
    data: VendorCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations)),
):
    return service.create_vendor(db, data, current_user)


@router.get("/", response_model=dict)
def list_vendors(
    search:     Optional[str]  = Query(None),
    is_active:  Optional[bool] = Query(True),
    product_id: Optional[UUID] = Query(None),
    page:       int            = Query(1, ge=1),
    page_size:  int            = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    result = service.list_vendors(db, current_user, search, is_active, product_id, page, page_size)
    result["data"] = [VendorResponse.model_validate(v) for v in result["data"]]
    return result


@router.get("/{vendor_id}", response_model=VendorResponse)
def get_vendor(
    vendor_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    return VendorResponse.model_validate(service.get_vendor(db, vendor_id, current_user))


@router.patch("/{vendor_id}", response_model=VendorResponse)
def update_vendor(
    vendor_id: UUID,
    data: VendorUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations)),
):
    return VendorResponse.model_validate(service.update_vendor(db, vendor_id, data, current_user))


@router.delete("/{vendor_id}", status_code=204)
def delete_vendor(
    vendor_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin)),
):
    service.delete_vendor(db, vendor_id, current_user)


# ─────────────────────────────────────────────────────────────────────────────
# Vendor Product Catalog
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{vendor_id}/products", response_model=list[VendorProductResponse])
def list_vendor_products(
    vendor_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    return service.list_vendor_products(db, vendor_id, current_user)


@router.post("/{vendor_id}/products", response_model=VendorProductResponse, status_code=201)
def upsert_vendor_product(
    vendor_id: UUID,
    data: VendorProductCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations)),
):
    """Add or update a product in a vendor's pricing catalog."""
    return service.upsert_vendor_product(db, vendor_id, data, current_user)


@router.patch("/products/{vp_id}", response_model=VendorProductResponse)
def update_vendor_product(
    vp_id: UUID,
    data: VendorProductUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations)),
):
    return service.update_vendor_product(db, vp_id, data, current_user)


@router.delete("/products/{vp_id}", status_code=204)
def delete_vendor_product(
    vp_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations)),
):
    service.delete_vendor_product(db, vp_id, current_user)


# ─────────────────────────────────────────────────────────────────────────────
# Sourcing Intelligence
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/sourcing/{product_id}", response_model=list[ProductSourcingEntry])
def get_product_sourcing(
    product_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Get all vendors who supply a specific product, sorted by price."""
    return service.get_product_sourcing(db, product_id, current_user)


# ─────────────────────────────────────────────────────────────────────────────
# Purchase History
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{vendor_id}/purchases", response_model=list[dict])
def get_vendor_purchase_history(
    vendor_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    return service.get_vendor_purchase_history(db, vendor_id, current_user, limit)
