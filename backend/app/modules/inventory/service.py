"""
Inventory Service — the ONLY place stock is written.

All stock changes must go through record_movement().
Direct writes to inventory_summary or inventory_movements
from anywhere else in the codebase are forbidden.
"""
from __future__ import annotations
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.inventory import InventoryMovement, InventorySummary, MovementType
from app.models.product import Product
from app.models.purchase import PurchaseOrder, PurchaseOrderItem, PurchaseOrderStatus
from app.models.employee import Employee
from app.modules.inventory.schemas import StockAdjustmentRequest


def record_movement(
    db: Session,
    tenant_id: UUID,
    product_id: UUID,
    movement_type: str,      # MovementType value string
    quantity_change: Decimal,
    reference_id: Optional[UUID] = None,
    reference_type: Optional[str] = None,
    note: Optional[str] = None,
    created_by_id: Optional[UUID] = None,
    commit: bool = True,
) -> InventoryMovement:
    """
    Core atomic operation: append a movement row + update summary.
    Pass commit=False when called inside a larger transaction.
    """
    mv = InventoryMovement(
        tenant_id=tenant_id,
        product_id=product_id,
        movement_type=MovementType(movement_type),
        quantity_change=quantity_change,
        reference_id=reference_id,
        reference_type=reference_type,
        note=note,
        created_by_id=created_by_id,
    )
    db.add(mv)

    # Upsert summary
    summary = db.query(InventorySummary).filter(
        InventorySummary.tenant_id == tenant_id,
        InventorySummary.product_id == product_id,
    ).first()
    if summary:
        summary.current_stock = summary.current_stock + quantity_change
    else:
        summary = InventorySummary(
            tenant_id=tenant_id,
            product_id=product_id,
            current_stock=quantity_change,
        )
        db.add(summary)

    if commit:
        db.commit()
        db.refresh(mv)
    else:
        db.flush()
    return mv


def get_stock(db: Session, tenant_id: UUID, product_id: UUID) -> Decimal:
    """Return current stock for a product (0 if no summary row yet)."""
    summary = db.query(InventorySummary).filter(
        InventorySummary.tenant_id == tenant_id,
        InventorySummary.product_id == product_id,
    ).first()
    return summary.current_stock if summary else Decimal("0")


def validate_stock(
    db: Session,
    tenant_id: UUID,
    product_id: UUID,
    required_qty: Decimal,
) -> None:
    """Raise 400 if available stock < required_qty."""
    available = get_stock(db, tenant_id, product_id)
    if available < required_qty:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock. Available: {available}, Required: {required_qty}",
        )


def list_movements(
    db: Session,
    current_user: Employee,
    product_id: Optional[UUID] = None,
    movement_type: Optional[MovementType] = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    query = db.query(InventoryMovement).filter(
        InventoryMovement.tenant_id == current_user.tenant_id
    )
    if product_id:
        query = query.filter(InventoryMovement.product_id == product_id)
    if movement_type:
        query = query.filter(InventoryMovement.movement_type == movement_type)
    total = query.count()
    data  = query.order_by(InventoryMovement.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size, "data": data}


def list_stock_summary(
    db: Session,
    current_user: Employee,
    low_stock_threshold: Optional[Decimal] = None,
) -> list[InventorySummary]:
    query = db.query(InventorySummary).filter(
        InventorySummary.tenant_id == current_user.tenant_id
    )
    if low_stock_threshold is not None:
        query = query.filter(InventorySummary.current_stock <= low_stock_threshold)
    return query.order_by(InventorySummary.current_stock.asc()).all()


def adjust_stock(
    db: Session,
    data: StockAdjustmentRequest,
    current_user: Employee,
) -> InventoryMovement:
    """Manual adjustment (positive or negative). Admin only."""
    product = db.query(Product).filter(
        Product.id == data.product_id,
        Product.tenant_id == current_user.tenant_id,
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return record_movement(
        db=db,
        tenant_id=current_user.tenant_id,
        product_id=data.product_id,
        movement_type=MovementType.adjustment.value,
        quantity_change=data.quantity_change,
        note=data.note or "Manual stock adjustment",
        created_by_id=current_user.id,
        commit=True,
    )


def get_wac_snapshot(db: Session, tenant_id: UUID, product_id: UUID) -> dict:
    """
    Compute weighted average cost from received purchase orders.
    Falls back to product.cost_price when no received purchases exist.
    """
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.tenant_id == tenant_id,
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    row = (
        db.query(
            func.coalesce(func.sum(PurchaseOrderItem.quantity), 0).label("qty"),
            func.coalesce(func.sum(PurchaseOrderItem.quantity * PurchaseOrderItem.unit_cost), 0).label("cost"),
        )
        .join(PurchaseOrder, PurchaseOrder.id == PurchaseOrderItem.purchase_order_id)
        .filter(
            PurchaseOrder.tenant_id == tenant_id,
            PurchaseOrder.status == PurchaseOrderStatus.received,
            PurchaseOrderItem.product_id == product_id,
        )
        .one()
    )

    total_qty = Decimal(str(row.qty or 0))
    total_cost = Decimal(str(row.cost or 0))
    if total_qty > 0:
        return {
            "product_id": str(product_id),
            "product_name": product.name,
            "cost_source": "wac",
            "wac": (total_cost / total_qty).quantize(Decimal("0.01")),
            "total_received_qty": total_qty,
            "total_received_cost": total_cost.quantize(Decimal("0.01")),
        }

    fallback = Decimal(str(product.cost_price or 0)).quantize(Decimal("0.01"))
    return {
        "product_id": str(product_id),
        "product_name": product.name,
        "cost_source": "catalog_cost_price",
        "wac": fallback,
        "total_received_qty": Decimal("0"),
        "total_received_cost": Decimal("0.00"),
    }
