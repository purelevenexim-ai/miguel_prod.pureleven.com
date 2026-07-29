"""
Profit Checker Router
----------------------
API prefix: /api/profit-checker
All tenant roles can read; management roles can write.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.auth.tenant import require_roles
from app.models.employee import RoleEnum
from app.modules.profit_checker import service
from app.modules.profit_checker.schemas import (
    AlertOut,
    CostSuggestionRow,
    EntryOut,
    EntryPayload,
    GroupCreatePayload,
    GroupItemOut,
    GroupItemPayload,
    GroupOut,
    PeriodSnapshotOut,
    ProductMapOut,
    ProductMapPayload,
)

router = APIRouter(prefix="/api/profit-checker", tags=["Profit Checker"])

_all_roles = require_roles(RoleEnum.admin, RoleEnum.marketing, RoleEnum.sales, RoleEnum.support, RoleEnum.operations)
_mgmt = require_roles(RoleEnum.admin, RoleEnum.operations)


# ─────────────────────────────────────────────────────────────
# Groups
# ─────────────────────────────────────────────────────────────

@router.get("/groups", response_model=list[GroupOut])
def list_groups(
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    return service.get_groups(db, current_user)


@router.post("/groups", response_model=GroupOut, status_code=201)
def create_group(
    data: GroupCreatePayload,
    db: Session = Depends(get_db),
    current_user=Depends(_mgmt),
):
    try:
        g = service.create_group(db, current_user, data)
        db.commit()
        return g
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.put("/groups/{group_id}", response_model=GroupOut)
def update_group(
    group_id: UUID,
    data: GroupCreatePayload,
    db: Session = Depends(get_db),
    current_user=Depends(_mgmt),
):
    try:
        g = service.update_group(db, current_user, group_id, data)
        db.commit()
        return g
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/groups/{group_id}", status_code=204)
def delete_group(
    group_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(_mgmt),
):
    try:
        service.delete_group(db, current_user, group_id)
        db.commit()
    except ValueError as e:
        raise HTTPException(400, str(e))


# ─────────────────────────────────────────────────────────────
# Group Items
# ─────────────────────────────────────────────────────────────

@router.post("/groups/{group_id}/items", response_model=GroupItemOut, status_code=201)
def add_group_item(
    group_id: UUID,
    data: GroupItemPayload,
    db: Session = Depends(get_db),
    current_user=Depends(_mgmt),
):
    try:
        item = service.add_group_item(db, current_user, group_id, data)
        db.commit()
        return item
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.put("/items/{item_id}", response_model=GroupItemOut)
def update_group_item(
    item_id: UUID,
    data: GroupItemPayload,
    db: Session = Depends(get_db),
    current_user=Depends(_mgmt),
):
    try:
        item = service.update_group_item(db, current_user, item_id, data)
        db.commit()
        return item
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/items/{item_id}", status_code=204)
def delete_group_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(_mgmt),
):
    try:
        service.delete_group_item(db, current_user, item_id)
        db.commit()
    except ValueError as e:
        raise HTTPException(400, str(e))


# ─────────────────────────────────────────────────────────────
# Entries
# ─────────────────────────────────────────────────────────────

@router.get("/entries", response_model=list[EntryOut])
def list_entries(
    month: str = Query(..., description="YYYY-MM"),
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    return service.get_entries(db, current_user, month)


@router.post("/entries", response_model=EntryOut, status_code=201)
def create_entry(
    data: EntryPayload,
    db: Session = Depends(get_db),
    current_user=Depends(_mgmt),
):
    try:
        e = service.create_entry(db, current_user, data)
        db.commit()
        return e
    except ValueError as ex:
        raise HTTPException(400, str(ex))


@router.put("/entries/{entry_id}", response_model=EntryOut)
def update_entry(
    entry_id: UUID,
    data: EntryPayload,
    db: Session = Depends(get_db),
    current_user=Depends(_mgmt),
):
    try:
        e = service.update_entry(db, current_user, entry_id, data)
        db.commit()
        return e
    except ValueError as ex:
        raise HTTPException(400, str(ex))


@router.delete("/entries/{entry_id}", status_code=204)
def delete_entry(
    entry_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(_mgmt),
):
    try:
        service.delete_entry(db, current_user, entry_id)
        db.commit()
    except ValueError as ex:
        raise HTTPException(400, str(ex))


# ─────────────────────────────────────────────────────────────
# Product Maps
# ─────────────────────────────────────────────────────────────

@router.get("/product-maps", response_model=list[ProductMapOut])
def list_product_maps(
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    return service.get_product_maps(db, current_user)


@router.post("/product-maps", response_model=ProductMapOut, status_code=201)
def upsert_product_map(
    data: ProductMapPayload,
    db: Session = Depends(get_db),
    current_user=Depends(_mgmt),
):
    try:
        m = service.upsert_product_map(db, current_user, data)
        db.commit()
        return m
    except ValueError as ex:
        raise HTTPException(400, str(ex))


@router.delete("/product-maps/{map_id}", status_code=204)
def delete_product_map(
    map_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(_mgmt),
):
    try:
        service.delete_product_map(db, current_user, map_id)
        db.commit()
    except ValueError as ex:
        raise HTTPException(400, str(ex))


# ─────────────────────────────────────────────────────────────
# Period Summary
# ─────────────────────────────────────────────────────────────

@router.post("/summary", response_model=PeriodSnapshotOut)
def compute_summary(
    period: str = Query(..., description="YYYY-MM | YYYY-Qn | YYYY"),
    period_type: str = Query("monthly", description="monthly | quarterly | yearly"),
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    """Compute (or recompute) the P&L snapshot for the requested period."""
    try:
        snap = service.compute_period_snapshot(db, current_user, period, period_type)
        db.commit()
        return snap
    except Exception as ex:
        raise HTTPException(500, str(ex))


@router.get("/summary", response_model=Optional[PeriodSnapshotOut])
def get_summary(
    period: str = Query(...),
    period_type: str = Query("monthly"),
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    """Return cached snapshot if it exists, else null (call POST /summary to compute)."""
    from app.models.profit_loss import ProfitCheckerPeriodSnapshot
    snap = db.query(ProfitCheckerPeriodSnapshot).filter(
        ProfitCheckerPeriodSnapshot.tenant_id == current_user.tenant_id,
        ProfitCheckerPeriodSnapshot.period == period,
        ProfitCheckerPeriodSnapshot.period_type == period_type,
    ).first()
    return snap


# ─────────────────────────────────────────────────────────────
# Carry-forward inventory
# ─────────────────────────────────────────────────────────────

@router.get("/carry-forward")
def get_carry_forward(
    month: str = Query(..., description="YYYY-MM"),
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    return service.get_carry_forward(db, current_user, month)


# ─────────────────────────────────────────────────────────────
# Purchase orders for month (product purchases auto-view)
# ─────────────────────────────────────────────────────────────

@router.get("/purchases-for-month")
def get_purchases_for_month(
    month: str = Query(..., description="YYYY-MM"),
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    return service.get_pos_for_month(db, current_user, month)


# ─────────────────────────────────────────────────────────────
# Cost update suggestions
# ─────────────────────────────────────────────────────────────

@router.get("/cost-suggestions", response_model=list[CostSuggestionRow])
def list_cost_suggestions(
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    return service.get_cost_suggestions(db, current_user)


@router.post("/cost-suggestions/{product_id}/apply", status_code=200)
def apply_cost_suggestion(
    product_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(_mgmt),
):
    try:
        p = service.apply_cost_suggestion(db, current_user, product_id)
        db.commit()
        return {"product_id": str(p.id), "new_cost_price": float(p.cost_price)}
    except ValueError as ex:
        raise HTTPException(400, str(ex))


# ─────────────────────────────────────────────────────────────
# Alerts
# ─────────────────────────────────────────────────────────────

@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(
    month: Optional[str] = Query(None),
    include_dismissed: bool = Query(False),
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    return service.get_alerts(db, current_user, month=month, include_dismissed=include_dismissed)


@router.post("/alerts/{alert_id}/dismiss", response_model=AlertOut)
def dismiss_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(_mgmt),
):
    try:
        a = service.dismiss_alert(db, current_user, alert_id)
        db.commit()
        return a
    except ValueError as ex:
        raise HTTPException(400, str(ex))
