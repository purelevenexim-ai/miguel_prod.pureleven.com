from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.purchase import PurchaseOrder, PurchaseOrderItem, PurchaseOrderStatus
from app.models.product import Product
from app.models.vendor import Vendor
from app.models.employee import Employee
from app.core.tenant_utils import apply_tenant_filter, assert_tenant_ownership
from app.modules.purchases.schemas import PurchaseOrderCreate, PurchaseOrderUpdate


def _next_po_number(db: Session, tenant_id) -> str:
    """Use MAX of existing PO numbers to avoid duplicates after cancellations."""
    rows = db.query(PurchaseOrder.po_number).filter(PurchaseOrder.tenant_id == tenant_id).all()
    max_n = 0
    for (code,) in rows:
        try:
            n = int(code.split("-")[1])
            if n > max_n:
                max_n = n
        except (IndexError, ValueError):
            pass
    return f"PO-{str(max_n + 1).zfill(5)}"


def _calc_item(quantity: Decimal, unit_cost: Decimal, tax_percent: Decimal):
    taxable   = quantity * unit_cost
    tax_amt   = taxable * (tax_percent / Decimal("100"))
    line_total = taxable + tax_amt
    return taxable, tax_amt, line_total


def create_purchase_order(
    db: Session, data: PurchaseOrderCreate, current_user: Employee
) -> PurchaseOrder:
    # Validate vendor
    vendor = db.query(Vendor).filter(
        Vendor.id == data.vendor_id,
        Vendor.tenant_id == current_user.tenant_id,
        Vendor.is_active == True,
    ).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    total_amount = Decimal("0")
    tax_amount   = Decimal("0")
    items_data   = []

    for item in data.items:
        product = db.query(Product).filter(
            Product.id == item.product_id,
            Product.tenant_id == current_user.tenant_id,
        ).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")

        _, t_amt, l_total = _calc_item(item.quantity, item.unit_cost, item.tax_percent)
        taxable = item.quantity * item.unit_cost
        total_amount += taxable
        tax_amount   += t_amt
        items_data.append((item, t_amt, l_total))

    po = PurchaseOrder(
        tenant_id=current_user.tenant_id,
        po_number=_next_po_number(db, current_user.tenant_id),
        vendor_id=data.vendor_id,
        status=PurchaseOrderStatus.draft,
        total_amount=total_amount,
        tax_amount=tax_amount,
        grand_total=total_amount + tax_amount,
        expected_delivery_date=data.expected_delivery_date,
        notes=data.notes,
        created_by_id=current_user.id,
    )
    db.add(po)
    db.flush()

    for item, t_amt, l_total in items_data:
        db.add(PurchaseOrderItem(
            tenant_id=current_user.tenant_id,
            purchase_order_id=po.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_cost=item.unit_cost,
            tax_percent=item.tax_percent,
            tax_amount=t_amt,
            line_total=l_total,
        ))

    db.commit()
    db.refresh(po)
    return po


def list_purchase_orders(
    db: Session,
    current_user: Employee,
    status_filter=None,
    vendor_id=None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    query = db.query(PurchaseOrder)
    query = apply_tenant_filter(query, PurchaseOrder, current_user)
    if status_filter:
        query = query.filter(PurchaseOrder.status == status_filter)
    if vendor_id:
        query = query.filter(PurchaseOrder.vendor_id == vendor_id)
    total = query.count()
    data  = query.order_by(PurchaseOrder.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size, "data": data}


def get_purchase_order(db: Session, po_id: UUID, current_user: Employee) -> PurchaseOrder:
    obj = (
        db.query(PurchaseOrder)
        .options(joinedload(PurchaseOrder.items))
        .filter(PurchaseOrder.id == po_id)
        .first()
    )
    if not obj:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    assert_tenant_ownership(obj, current_user)
    return obj


def update_purchase_order(
    db: Session, po_id: UUID, data: PurchaseOrderUpdate, current_user: Employee
) -> PurchaseOrder:
    obj = get_purchase_order(db, po_id, current_user)
    if obj.status not in (PurchaseOrderStatus.draft, PurchaseOrderStatus.sent):
        raise HTTPException(status_code=400, detail="Only draft or sent POs can be updated")
    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, val)
    db.commit()
    db.refresh(obj)
    return obj


def advance_status(
    db: Session, po_id: UUID, new_status: PurchaseOrderStatus, current_user: Employee
) -> PurchaseOrder:
    """
    Valid transitions:
      draft → sent
      sent  → received  (triggers stock-in via inventory service)
      draft|sent → cancelled
    """
    obj = get_purchase_order(db, po_id, current_user)
    allowed = {
        PurchaseOrderStatus.draft:    [PurchaseOrderStatus.sent, PurchaseOrderStatus.cancelled],
        PurchaseOrderStatus.sent:     [PurchaseOrderStatus.received, PurchaseOrderStatus.cancelled],
        PurchaseOrderStatus.received: [],
        PurchaseOrderStatus.cancelled: [],
    }
    if new_status not in allowed.get(obj.status, []):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot move from {obj.status.value} → {new_status.value}",
        )

    obj.status = new_status

    if new_status == PurchaseOrderStatus.received:
        obj.received_at = datetime.now(timezone.utc)
        # Lazy imports to avoid circular imports
        from app.modules.inventory import service as inv_svc
        from app.models.inventory import MovementType
        # Trigger stock-in for every item
        for item in obj.items:
            inv_svc.record_movement(
                db=db,
                tenant_id=obj.tenant_id,
                product_id=item.product_id,
                movement_type=MovementType.purchase.value,
                quantity_change=item.quantity,
                reference_id=obj.id,
                reference_type="purchase_order",
                note=f"PO received: {obj.po_number}",
                created_by_id=current_user.id,
                commit=False,
            )

    db.commit()
    db.refresh(obj)
    return obj
