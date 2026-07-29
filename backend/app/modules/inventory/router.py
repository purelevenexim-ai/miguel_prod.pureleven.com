from typing import Optional
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.core.auth.tenant import get_current_tenant_user, require_roles
from app.models.employee import Employee, RoleEnum
from app.models.inventory import MovementType
from app.modules.inventory.schemas import (
    StockAdjustmentRequest,
    InventoryMovementResponse,
    InventorySummaryResponse,
)
from app.modules.inventory import service

router = APIRouter(prefix="/api/inventory", tags=["Inventory"])


@router.get("/stock", response_model=list[InventorySummaryResponse])
def stock_summary(
    low_stock_threshold: Optional[Decimal] = Query(None, description="Filter products at or below this quantity"),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Current stock levels for all products. Optionally filter low-stock."""
    return [
        InventorySummaryResponse.model_validate(s)
        for s in service.list_stock_summary(db, current_user, low_stock_threshold)
    ]


@router.get("/stock/{product_id}")
def get_stock(
    product_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Current stock for a single product."""
    qty = service.get_stock(db, current_user.tenant_id, product_id)
    return {"product_id": str(product_id), "current_stock": str(qty)}


@router.get("/wac/{product_id}")
def get_product_wac(
    product_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Weighted average cost snapshot for a product from received purchases."""
    return service.get_wac_snapshot(db, current_user.tenant_id, product_id)


@router.get("/movements", response_model=dict)
def list_movements(
    product_id:    Optional[UUID]         = Query(None),
    movement_type: Optional[MovementType] = Query(None),
    page:          int                    = Query(1, ge=1),
    page_size:     int                    = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Full movement ledger — audit trail of all stock changes."""
    result = service.list_movements(db, current_user, product_id, movement_type, page, page_size)
    result["data"] = [InventoryMovementResponse.model_validate(m) for m in result["data"]]
    return result


@router.post("/adjust", response_model=InventoryMovementResponse, status_code=201)
def adjust_stock(
    data: StockAdjustmentRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations)),
):
    """Manual stock adjustment. Positive = add, Negative = remove. Admin + operations only."""
    return InventoryMovementResponse.model_validate(
        service.adjust_stock(db, data, current_user)
    )
