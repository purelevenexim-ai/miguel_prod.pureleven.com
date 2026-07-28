from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.core.auth.tenant import get_current_tenant_user, require_roles
from app.models.employee import Employee, RoleEnum
from app.models.purchase import PurchaseOrderStatus
from app.modules.purchases.schemas import (
    PurchaseOrderCreate, PurchaseOrderUpdate,
    PurchaseOrderResponse, PurchaseOrderDetail,
)
from app.modules.purchases import service

router = APIRouter(prefix="/api/purchases", tags=["Purchases"])


@router.post("/", response_model=PurchaseOrderDetail, status_code=201)
def create_po(
    data: PurchaseOrderCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations)),
):
    return service.create_purchase_order(db, data, current_user)


@router.get("/", response_model=dict)
def list_pos(
    status:    Optional[PurchaseOrderStatus] = Query(None),
    vendor_id: Optional[UUID]                = Query(None),
    page:      int                           = Query(1, ge=1),
    page_size: int                           = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    result = service.list_purchase_orders(db, current_user, status, vendor_id, page, page_size)
    result["data"] = [PurchaseOrderResponse.model_validate(p) for p in result["data"]]
    return result


@router.get("/{po_id}", response_model=PurchaseOrderDetail)
def get_po(
    po_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    return service.get_purchase_order(db, po_id, current_user)


@router.patch("/{po_id}", response_model=PurchaseOrderResponse)
def update_po(
    po_id: UUID,
    data: PurchaseOrderUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations)),
):
    return service.update_purchase_order(db, po_id, data, current_user)


@router.post("/{po_id}/status", response_model=PurchaseOrderResponse)
def advance_status(
    po_id:      UUID,
    new_status: PurchaseOrderStatus,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations)),
):
    return service.advance_status(db, po_id, new_status, current_user)
