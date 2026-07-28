"""
Profit Checker Service
-----------------------
Business logic for the Profit Checker module.

Responsibilities:
  - Seed default cost groups per tenant on first use
  - CRUD for groups, group items, entries, and product maps
  - Period summary computation (monthly → quarterly → yearly)
  - Cost-update suggestions (WAC vs catalog cost_price drift)
  - Alert detection and persistence for negative-margin periods/orders
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, date
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.inventory import InventorySummary
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.profit_loss import (
    ProfitCheckerAlert,
    ProfitCheckerEntry,
    ProfitCheckerGroup,
    ProfitCheckerGroupItem,
    ProfitCheckerPeriodSnapshot,
    ProfitCheckerProductMap,
    PcGroupType,
    PcAlertType,
    OrderProfitPosting,
    ProfitCostConfig,
    ProfitMonthlyOverhead,
)
from app.models.purchase import PurchaseOrder, PurchaseOrderItem, PurchaseOrderStatus
from app.modules.profit_checker.schemas import (
    GroupCreatePayload,
    GroupItemPayload,
    EntryPayload,
    ProductMapPayload,
)


def _z(v: Any) -> Decimal:
    return Decimal(str(v if v is not None else 0))


def _month_key(dt: datetime | None) -> str:
    d = dt or datetime.now(timezone.utc)
    return f"{d.year:04d}-{d.month:02d}"


def _normalize_categories(categories: Optional[list[str]]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for category in categories or []:
        value = str(category or "").strip()
        key = value.casefold()
        if not value or key in seen:
            continue
        seen.add(key)
        out.append(value)
    return out


def _validate_entry_payload(group: ProfitCheckerGroup, data: EntryPayload) -> tuple[Optional[UUID], list[str]]:
    product_id = data.product_id
    applicable_categories = _normalize_categories(data.applicable_categories)
    is_purchase = group.group_type == PcGroupType.product_purchase
    is_packing = group.group_type == PcGroupType.packaging and group.sub_type == "packing_material"
    is_courier = group.group_type == PcGroupType.packaging and group.sub_type == "courier_material"

    if is_packing:
        if product_id is not None:
            raise ValueError("Packing material entries cannot be linked to a product.")
        if not applicable_categories:
            raise ValueError("Packing material entries require at least one applicable category.")
        return None, applicable_categories

    if is_courier:
        if product_id is not None:
            raise ValueError("Courier material entries cannot be linked to a product.")
        if applicable_categories:
            raise ValueError("Courier material entries do not use applicable categories.")
        return None, []

    if is_purchase:
        return product_id, []

    if applicable_categories:
        raise ValueError("Applicable categories are only supported for packing material entries.")
    return product_id, []


# ─────────────────────────────────────────────────────────────
# Default groups seed
# ─────────────────────────────────────────────────────────────

_DEFAULT_GROUPS = [
    {"name": "Product Purchases",   "group_type": PcGroupType.product_purchase, "sub_type": None,               "sort_order": 10, "is_system": True},
    {"name": "Packing Materials",   "group_type": PcGroupType.packaging,         "sub_type": "packing_material",  "sort_order": 20, "is_system": True},
    {"name": "Courier Materials",   "group_type": PcGroupType.packaging,         "sub_type": "courier_material",  "sort_order": 25, "is_system": True},
    {"name": "Salary & Operations", "group_type": PcGroupType.salary_ops,        "sub_type": None,               "sort_order": 30, "is_system": True},
    {"name": "Ads & Marketing",     "group_type": PcGroupType.ads_marketing,     "sub_type": None,               "sort_order": 40, "is_system": True},
    {"name": "Sales",               "group_type": PcGroupType.sales,             "sub_type": None,               "sort_order": 50, "is_system": True},
]


def seed_default_groups(db: Session, tenant_id: UUID) -> None:
    """Idempotently create default groups for a tenant."""
    existing_names = {
        r.name for r in
        db.query(ProfitCheckerGroup.name).filter(ProfitCheckerGroup.tenant_id == tenant_id).all()
    }
    for g in _DEFAULT_GROUPS:
        if g["name"] not in existing_names:
            db.add(ProfitCheckerGroup(
                tenant_id=tenant_id,
                name=g["name"],
                group_type=g["group_type"],
                sub_type=g["sub_type"],
                sort_order=g["sort_order"],
                is_system=g["is_system"],
            ))
    # Migrate old 'Packing' group to 'Packing Materials'
    old_packing = db.query(ProfitCheckerGroup).filter(
        ProfitCheckerGroup.tenant_id == tenant_id,
        ProfitCheckerGroup.name == "Packing",
    ).first()
    if old_packing:
        old_packing.name = "Packing Materials"
        old_packing.sub_type = "packing_material"
    db.flush()


# ─────────────────────────────────────────────────────────────
# Groups and items
# ─────────────────────────────────────────────────────────────

def get_groups(db: Session, current_user: Employee) -> list[ProfitCheckerGroup]:
    seed_default_groups(db, current_user.tenant_id)
    return (
        db.query(ProfitCheckerGroup)
        .filter(ProfitCheckerGroup.tenant_id == current_user.tenant_id,
                ProfitCheckerGroup.is_active == True)
        .order_by(ProfitCheckerGroup.sort_order)
        .all()
    )


def create_group(db: Session, current_user: Employee, data: GroupCreatePayload) -> ProfitCheckerGroup:
    g = ProfitCheckerGroup(
        tenant_id=current_user.tenant_id,
        name=data.name,
        group_type=PcGroupType.custom,
        sort_order=data.sort_order or 100,
    )
    db.add(g)
    db.flush()
    db.refresh(g)
    return g


def update_group(db: Session, current_user: Employee, group_id: UUID, data: GroupCreatePayload) -> ProfitCheckerGroup:
    g = db.query(ProfitCheckerGroup).filter(
        ProfitCheckerGroup.id == group_id,
        ProfitCheckerGroup.tenant_id == current_user.tenant_id,
    ).first()
    if not g:
        raise ValueError("Group not found")
    g.name = data.name
    if data.sort_order is not None:
        g.sort_order = data.sort_order
    db.flush()
    db.refresh(g)
    return g


def delete_group(db: Session, current_user: Employee, group_id: UUID) -> None:
    g = db.query(ProfitCheckerGroup).filter(
        ProfitCheckerGroup.id == group_id,
        ProfitCheckerGroup.tenant_id == current_user.tenant_id,
    ).first()
    if not g:
        raise ValueError("Group not found")
    if g.is_system:
        raise ValueError("Cannot delete a system group")
    g.is_active = False
    db.flush()


def add_group_item(db: Session, current_user: Employee, group_id: UUID, data: GroupItemPayload) -> ProfitCheckerGroupItem:
    # Verify group ownership
    g = db.query(ProfitCheckerGroup).filter(
        ProfitCheckerGroup.id == group_id,
        ProfitCheckerGroup.tenant_id == current_user.tenant_id,
    ).first()
    if not g:
        raise ValueError("Group not found")
    item = ProfitCheckerGroupItem(
        tenant_id=current_user.tenant_id,
        group_id=group_id,
        name=data.name,
        allocation_type=data.allocation_type,
        product_id=data.product_id,
        items_per_trigger=data.items_per_trigger,
        sort_order=data.sort_order or 100,
    )
    db.add(item)
    db.flush()
    db.refresh(item)
    return item


def update_group_item(db: Session, current_user: Employee, item_id: UUID, data: GroupItemPayload) -> ProfitCheckerGroupItem:
    item = db.query(ProfitCheckerGroupItem).filter(
        ProfitCheckerGroupItem.id == item_id,
        ProfitCheckerGroupItem.tenant_id == current_user.tenant_id,
    ).first()
    if not item:
        raise ValueError("Item not found")
    item.name = data.name
    item.allocation_type = data.allocation_type
    item.product_id = data.product_id
    item.items_per_trigger = data.items_per_trigger
    if data.sort_order is not None:
        item.sort_order = data.sort_order
    db.flush()
    db.refresh(item)
    return item


def delete_group_item(db: Session, current_user: Employee, item_id: UUID) -> None:
    item = db.query(ProfitCheckerGroupItem).filter(
        ProfitCheckerGroupItem.id == item_id,
        ProfitCheckerGroupItem.tenant_id == current_user.tenant_id,
    ).first()
    if not item:
        raise ValueError("Item not found")
    item.is_active = False
    db.flush()


# ─────────────────────────────────────────────────────────────
# Entries
# ─────────────────────────────────────────────────────────────

def get_entries(db: Session, current_user: Employee, month: str) -> list[ProfitCheckerEntry]:
    return (
        db.query(ProfitCheckerEntry)
        .filter(
            ProfitCheckerEntry.tenant_id == current_user.tenant_id,
            ProfitCheckerEntry.month == month,
        )
        .order_by(ProfitCheckerEntry.group_id, ProfitCheckerEntry.created_at)
        .all()
    )


def create_entry(db: Session, current_user: Employee, data: EntryPayload) -> ProfitCheckerEntry:
    # Verify group belongs to tenant
    g = db.query(ProfitCheckerGroup).filter(
        ProfitCheckerGroup.id == data.group_id,
        ProfitCheckerGroup.tenant_id == current_user.tenant_id,
    ).first()
    if not g:
        raise ValueError("Group not found")
    product_id, applicable_categories = _validate_entry_payload(g, data)
    amount = data.amount
    if amount is None and data.quantity is not None and data.unit_cost is not None:
        amount = Decimal(str(data.quantity)) * Decimal(str(data.unit_cost))
    entry = ProfitCheckerEntry(
        tenant_id=current_user.tenant_id,
        group_id=data.group_id,
        item_id=data.item_id,
        month=data.month,
        description=data.description,
        amount=amount or Decimal("0"),
        quantity=data.quantity,
        unit_cost=data.unit_cost,
        product_id=product_id,
        applicable_categories=applicable_categories or None,
        consumption_rate=data.consumption_rate,
        reference_po_id=data.reference_po_id,
        note=data.note,
        created_by_id=current_user.id,
    )
    db.add(entry)
    db.flush()
    db.refresh(entry)
    return entry


def update_entry(db: Session, current_user: Employee, entry_id: UUID, data: EntryPayload) -> ProfitCheckerEntry:
    entry = db.query(ProfitCheckerEntry).filter(
        ProfitCheckerEntry.id == entry_id,
        ProfitCheckerEntry.tenant_id == current_user.tenant_id,
    ).first()
    if not entry:
        raise ValueError("Entry not found")
    g = db.query(ProfitCheckerGroup).filter(
        ProfitCheckerGroup.id == data.group_id,
        ProfitCheckerGroup.tenant_id == current_user.tenant_id,
    ).first()
    if not g:
        raise ValueError("Group not found")
    product_id, applicable_categories = _validate_entry_payload(g, data)
    entry.group_id = data.group_id
    entry.description = data.description
    entry.month = data.month
    entry.quantity = data.quantity
    entry.unit_cost = data.unit_cost
    entry.product_id = product_id
    entry.applicable_categories = applicable_categories or None
    entry.consumption_rate = data.consumption_rate
    entry.note = data.note
    if data.amount is not None:
        entry.amount = data.amount
    elif data.quantity is not None and data.unit_cost is not None:
        entry.amount = Decimal(str(data.quantity)) * Decimal(str(data.unit_cost))
    db.flush()
    db.refresh(entry)
    return entry


def delete_entry(db: Session, current_user: Employee, entry_id: UUID) -> None:
    entry = db.query(ProfitCheckerEntry).filter(
        ProfitCheckerEntry.id == entry_id,
        ProfitCheckerEntry.tenant_id == current_user.tenant_id,
    ).first()
    if not entry:
        raise ValueError("Entry not found")
    db.delete(entry)
    db.flush()


# ─────────────────────────────────────────────────────────────
# Product Maps (raw → variant)
# ─────────────────────────────────────────────────────────────

def get_product_maps(db: Session, current_user: Employee) -> list[ProfitCheckerProductMap]:
    return (
        db.query(ProfitCheckerProductMap)
        .filter(
            ProfitCheckerProductMap.tenant_id == current_user.tenant_id,
            ProfitCheckerProductMap.is_active == True,
        )
        .all()
    )


def upsert_product_map(db: Session, current_user: Employee, data: ProductMapPayload) -> ProfitCheckerProductMap:
    existing = db.query(ProfitCheckerProductMap).filter(
        ProfitCheckerProductMap.tenant_id == current_user.tenant_id,
        ProfitCheckerProductMap.source_product_id == data.source_product_id,
        ProfitCheckerProductMap.target_product_id == data.target_product_id,
    ).first()
    if existing:
        existing.conversion_ratio = data.conversion_ratio or Decimal("1.0")
        existing.is_active = True
        db.flush()
        db.refresh(existing)
        return existing
    m = ProfitCheckerProductMap(
        tenant_id=current_user.tenant_id,
        source_product_id=data.source_product_id,
        target_product_id=data.target_product_id,
        conversion_ratio=data.conversion_ratio or Decimal("1.0"),
    )
    db.add(m)
    db.flush()
    db.refresh(m)
    return m


def delete_product_map(db: Session, current_user: Employee, map_id: UUID) -> None:
    m = db.query(ProfitCheckerProductMap).filter(
        ProfitCheckerProductMap.id == map_id,
        ProfitCheckerProductMap.tenant_id == current_user.tenant_id,
    ).first()
    if not m:
        raise ValueError("Map not found")
    m.is_active = False
    db.flush()


# ─────────────────────────────────────────────────────────────
# WAC helper
# ─────────────────────────────────────────────────────────────

def _wac_all(db: Session, tenant_id: UUID) -> dict[str, Decimal]:
    """
    Weighted-average cost per product.
    Sources:
      1. Received POs (all-time, from purchase_order_items)
      2. Manual PC entries (product_purchase group, product_id set, no reference_po_id)
         — these are bulk/generic purchases not tied to a PO record.
    """
    # ── Source 1: received POs ─────────────────────────────────
    po_rows = (
        db.query(
            PurchaseOrderItem.product_id.label("pid"),
            func.sum(PurchaseOrderItem.quantity).label("qty"),
            func.sum(PurchaseOrderItem.quantity * PurchaseOrderItem.unit_cost).label("cost"),
        )
        .join(PurchaseOrder, PurchaseOrder.id == PurchaseOrderItem.purchase_order_id)
        .filter(
            PurchaseOrder.tenant_id == tenant_id,
            PurchaseOrder.status == PurchaseOrderStatus.received,
        )
        .group_by(PurchaseOrderItem.product_id)
        .all()
    )

    # ── Source 2: manual PC purchase entries (no PO link) ───────
    # Join with pc_groups to confirm group_type = product_purchase
    pc_rows = (
        db.query(
            ProfitCheckerEntry.product_id.label("pid"),
            func.sum(ProfitCheckerEntry.quantity).label("qty"),
            func.sum(ProfitCheckerEntry.quantity * ProfitCheckerEntry.unit_cost).label("cost"),
        )
        .join(ProfitCheckerGroup, ProfitCheckerGroup.id == ProfitCheckerEntry.group_id)
        .filter(
            ProfitCheckerEntry.tenant_id == tenant_id,
            ProfitCheckerEntry.product_id.isnot(None),
            ProfitCheckerEntry.quantity.isnot(None),
            ProfitCheckerEntry.unit_cost.isnot(None),
            ProfitCheckerEntry.reference_po_id.is_(None),
            ProfitCheckerGroup.group_type == PcGroupType.product_purchase,
        )
        .group_by(ProfitCheckerEntry.product_id)
        .all()
    )

    # ── Merge into accumulator {pid: (total_qty, total_cost)} ───
    acc: dict[str, tuple[Decimal, Decimal]] = {}
    for r in po_rows:
        pid = str(r.pid)
        acc[pid] = (acc.get(pid, (Decimal("0"), Decimal("0")))[0] + _z(r.qty),
                    acc.get(pid, (Decimal("0"), Decimal("0")))[1] + _z(r.cost))
    for r in pc_rows:
        if r.pid is None:
            continue
        pid = str(r.pid)
        acc[pid] = (acc.get(pid, (Decimal("0"), Decimal("0")))[0] + _z(r.qty),
                    acc.get(pid, (Decimal("0"), Decimal("0")))[1] + _z(r.cost))

    out: dict[str, Decimal] = {}
    for pid, (qty, cost) in acc.items():
        if qty > 0:
            out[pid] = (cost / qty).quantize(Decimal("0.01"))
    return out


# ─────────────────────────────────────────────────────────────
# Inventory stock values at period
# ─────────────────────────────────────────────────────────────

def _current_stock_value(db: Session, tenant_id: UUID) -> Decimal:
    """WAC × current stock summed across all products for the tenant."""
    wac = _wac_all(db, tenant_id)
    summaries = (
        db.query(InventorySummary)
        .filter(InventorySummary.tenant_id == tenant_id)
        .all()
    )
    total = Decimal("0")
    for s in summaries:
        w = wac.get(str(s.product_id), _z(
            db.query(Product.cost_price)
            .filter(Product.id == s.product_id)
            .scalar()
        ))
        total += _z(s.current_stock) * w
    return total.quantize(Decimal("0.01"))


# ─────────────────────────────────────────────────────────────
# Period Summary Computation
# ─────────────────────────────────────────────────────────────

def compute_period_snapshot(
    db: Session,
    current_user: Employee,
    period: str,          # "2026-05" | "2026-Q2" | "2026"
    period_type: str,     # "monthly" | "quarterly" | "yearly"
) -> ProfitCheckerPeriodSnapshot:
    """
    Compute (or recompute) P&L snapshot for a period.
    - Monthly: combines auto-fetched order/COGS data with manual Profit Checker entries.
    - Quarterly/Yearly: aggregates from monthly snapshots.
    """
    tid = current_user.tenant_id

    if period_type in ("quarterly", "yearly"):
        return _aggregate_snapshot(db, tid, period, period_type)

    # ── Monthly computation ───────────────────────────────────
    month = period  # "2026-05"

    # Orders (all non-cancelled in date range)
    from datetime import datetime as dt
    year, mo = int(month[:4]), int(month[5:7])
    month_start = dt(year, mo, 1, tzinfo=timezone.utc)
    if mo == 12:
        month_end = dt(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        month_end = dt(year, mo + 1, 1, tzinfo=timezone.utc)

    orders = (
        db.query(Order)
        .filter(
            Order.tenant_id == tid,
            Order.is_active == True,
            Order.status.notin_([OrderStatus.cancelled]),
            Order.created_at >= month_start,
            Order.created_at < month_end,
        )
        .all()
    )
    sales_revenue = sum(_z(o.total_amount) for o in orders)
    order_count = len(orders)

    # COGS from OrderProfitPostings for delivered orders in this month
    cogs_rows = (
        db.query(func.sum(OrderProfitPosting.product_cost))
        .filter(
            OrderProfitPosting.tenant_id == tid,
            OrderProfitPosting.month == month,
        )
        .scalar()
    )
    cogs = _z(cogs_rows)

    # ── Packaging from postings (user-entered packaging costs in Profit Checker override)
    pkg_rows = (
        db.query(func.coalesce(func.sum(OrderProfitPosting.packaging_cost), 0))
        .filter(
            OrderProfitPosting.tenant_id == tid,
            OrderProfitPosting.month == month,
        )
        .scalar()
    )
    packaging_from_postings = _z(pkg_rows)

    # Courier material cost from postings
    courier_rows = (
        db.query(func.coalesce(func.sum(OrderProfitPosting.courier_material_cost), 0))
        .filter(
            OrderProfitPosting.tenant_id == tid,
            OrderProfitPosting.month == month,
        )
        .scalar()
    )
    courier_from_postings = _z(courier_rows)

    # ── Load manual overhead row for this month ────────────────────────────────
    monthly_overhead = (
        db.query(ProfitMonthlyOverhead)
        .filter(
            ProfitMonthlyOverhead.tenant_id == tid,
            ProfitMonthlyOverhead.month == month,
        )
        .first()
    )

    # COGS: keep auto value from OrderProfitPosting.product_cost (computed above) — no manual override

    # Shipping: manual value only — do not use auto-calculated order shipping charges
    shipping_cost = _z(monthly_overhead.shipping_cost) if monthly_overhead else Decimal("0")

    # Gateway fee: manual value only (default 0 until configured)
    gateway_fee = _z(monthly_overhead.gateway_fee) if monthly_overhead else Decimal("0")

    # RTO loss: sum of shipping_charge on returned orders in month + ₹50 per returned order
    rto_rows = (
        db.query(
            func.count(Order.id).label("cnt"),
            func.coalesce(func.sum(Order.shipping_charge), 0).label("ship"),
        )
        .filter(
            Order.tenant_id == tid,
            Order.is_active == True,
            Order.status == OrderStatus.returned,
            func.to_char(Order.created_at, "YYYY-MM") == month,
        )
        .one()
    )
    rto_loss = (_z(rto_rows.ship) + Decimal("50") * int(rto_rows.cnt or 0)).quantize(Decimal("0.01"))

    # Profit Checker entries for the month
    entries = (
        db.query(ProfitCheckerEntry)
        .filter(
            ProfitCheckerEntry.tenant_id == tid,
            ProfitCheckerEntry.month == month,
        )
        .all()
    )

    # Map group_id → (group_type, sub_type) for bucketing
    groups = {
        str(g.id): (g.group_type, g.sub_type)
        for g in db.query(ProfitCheckerGroup).filter(ProfitCheckerGroup.tenant_id == tid).all()
    }

    group_totals: dict[str, float] = {}
    packaging_manual = Decimal("0")
    courier_manual = Decimal("0")
    salary_ops = Decimal("0")
    ads_marketing = Decimal("0")
    other = Decimal("0")

    for e in entries:
        gid = str(e.group_id)
        group_totals[gid] = float(_z(group_totals.get(gid, 0)) + _z(e.amount))
        gt, sub_type = groups.get(gid, (PcGroupType.custom, None))
        if gt == PcGroupType.packaging:
            if sub_type == "courier_material":
                courier_manual += _z(e.amount)
            else:
                packaging_manual += _z(e.amount)
        elif gt == PcGroupType.salary_ops:
            salary_ops += _z(e.amount)
        elif gt == PcGroupType.ads_marketing:
            ads_marketing += _z(e.amount)
        elif gt not in (PcGroupType.product_purchase, PcGroupType.sales):
            other += _z(e.amount)

    # Packaging/courier: prefer manual PC entries if they exist, else use posting data
    packaging_cost = packaging_manual if packaging_manual > 0 else packaging_from_postings
    courier_material_cost = courier_manual if courier_manual > 0 else courier_from_postings
    # shipping_cost, gateway_fee, rto_loss already set from manual overhead above

    # Overhead fixed costs from ProfitMonthlyOverhead (manual, user-set)
    if monthly_overhead:
        ads_marketing += _z(monthly_overhead.ads_cost)
        salary_ops += _z(monthly_overhead.dispatch_cost) + _z(monthly_overhead.misc_cost)
        other += _z(monthly_overhead.other_fixed_cost)

    # Purchases value in month (received POs)
    po_rows = (
        db.query(func.sum(PurchaseOrderItem.quantity * PurchaseOrderItem.unit_cost))
        .join(PurchaseOrder, PurchaseOrder.id == PurchaseOrderItem.purchase_order_id)
        .filter(
            PurchaseOrder.tenant_id == tid,
            PurchaseOrder.status == PurchaseOrderStatus.received,
            PurchaseOrder.received_at >= month_start,
            PurchaseOrder.received_at < month_end,
        )
        .scalar()
    )
    purchases_value = _z(po_rows)

    # Opening stock value from previous month's closing, or compute current if first month
    prev_snap = _prev_monthly_snapshot(db, tid, month)
    opening_stock_value = _z(prev_snap.closing_stock_value) if prev_snap else _current_stock_value(db, tid)

    # Closing stock: current snapshot value (real-time, since we persist after compute)
    closing_stock_value = _current_stock_value(db, tid)

    total_expense = cogs + packaging_cost + courier_material_cost + shipping_cost + gateway_fee + rto_loss + salary_ops + ads_marketing + other
    gross_profit = sales_revenue - cogs
    net_profit = sales_revenue - total_expense
    margin_pct = Decimal("0")
    if sales_revenue > 0:
        margin_pct = (net_profit / sales_revenue * Decimal("100")).quantize(Decimal("0.01"))

    snap = db.query(ProfitCheckerPeriodSnapshot).filter(
        ProfitCheckerPeriodSnapshot.tenant_id == tid,
        ProfitCheckerPeriodSnapshot.period == period,
        ProfitCheckerPeriodSnapshot.period_type == period_type,
    ).first()
    if not snap:
        snap = ProfitCheckerPeriodSnapshot(tenant_id=tid, period=period, period_type=period_type)
        db.add(snap)

    snap.sales_revenue = sales_revenue.quantize(Decimal("0.01"))
    snap.order_count = order_count
    snap.cogs = cogs.quantize(Decimal("0.01"))
    snap.packaging_cost = packaging_cost.quantize(Decimal("0.01"))
    snap.courier_material_cost = courier_material_cost.quantize(Decimal("0.01"))
    snap.shipping_cost = shipping_cost.quantize(Decimal("0.01"))
    snap.gateway_fee = gateway_fee.quantize(Decimal("0.01"))
    snap.rto_loss = rto_loss.quantize(Decimal("0.01"))
    snap.salary_ops_cost = salary_ops.quantize(Decimal("0.01"))
    snap.ads_marketing_cost = ads_marketing.quantize(Decimal("0.01"))
    snap.other_cost = other.quantize(Decimal("0.01"))
    snap.total_expense = total_expense.quantize(Decimal("0.01"))
    snap.opening_stock_value = opening_stock_value.quantize(Decimal("0.01"))
    snap.closing_stock_value = closing_stock_value.quantize(Decimal("0.01"))
    snap.purchases_value = purchases_value.quantize(Decimal("0.01"))
    snap.gross_profit = gross_profit.quantize(Decimal("0.01"))
    snap.net_profit = net_profit.quantize(Decimal("0.01"))
    snap.margin_pct = margin_pct
    snap.group_totals = group_totals
    snap.computed_at = datetime.now(timezone.utc)

    db.flush()
    db.refresh(snap)

    # Detect and store alerts after computing
    _detect_and_store_alerts(db, tid, month, snap)

    return snap


def _prev_monthly_snapshot(
    db: Session, tenant_id: UUID, month: str
) -> ProfitCheckerPeriodSnapshot | None:
    """Return the snapshot for the month immediately preceding 'month'."""
    year, mo = int(month[:4]), int(month[5:7])
    if mo == 1:
        prev_month = f"{year-1:04d}-12"
    else:
        prev_month = f"{year:04d}-{mo-1:02d}"
    return db.query(ProfitCheckerPeriodSnapshot).filter(
        ProfitCheckerPeriodSnapshot.tenant_id == tenant_id,
        ProfitCheckerPeriodSnapshot.period == prev_month,
        ProfitCheckerPeriodSnapshot.period_type == "monthly",
    ).first()


def _aggregate_snapshot(
    db: Session, tenant_id: UUID, period: str, period_type: str
) -> ProfitCheckerPeriodSnapshot:
    """Derive a quarterly or yearly snapshot from monthly snapshots."""
    months = _period_months(period, period_type)
    snaps = db.query(ProfitCheckerPeriodSnapshot).filter(
        ProfitCheckerPeriodSnapshot.tenant_id == tenant_id,
        ProfitCheckerPeriodSnapshot.period.in_(months),
        ProfitCheckerPeriodSnapshot.period_type == "monthly",
    ).all()

    def _sum(field: str) -> Decimal:
        return sum((_z(getattr(s, field)) for s in snaps), Decimal("0"))

    sales_revenue = _sum("sales_revenue")
    order_count = sum(s.order_count for s in snaps)
    cogs = _sum("cogs")
    packaging_cost = _sum("packaging_cost")
    courier_material_cost = _sum("courier_material_cost")
    shipping_cost = _sum("shipping_cost")
    gateway_fee = _sum("gateway_fee")
    rto_loss = _sum("rto_loss")
    salary_ops = _sum("salary_ops_cost")
    ads_marketing = _sum("ads_marketing_cost")
    other = _sum("other_cost")
    total_expense = _sum("total_expense")

    # For multi-month periods: opening = first month's opening, closing = last month's closing
    sorted_snaps = sorted(snaps, key=lambda s: s.period)
    opening = _z(sorted_snaps[0].opening_stock_value) if sorted_snaps else Decimal("0")
    closing = _z(sorted_snaps[-1].closing_stock_value) if sorted_snaps else Decimal("0")
    purchases = _sum("purchases_value")

    gross_profit = sales_revenue - cogs
    net_profit = sales_revenue - total_expense
    margin_pct = (net_profit / sales_revenue * Decimal("100")).quantize(Decimal("0.01")) if sales_revenue > 0 else Decimal("0")

    snap = db.query(ProfitCheckerPeriodSnapshot).filter(
        ProfitCheckerPeriodSnapshot.tenant_id == tenant_id,
        ProfitCheckerPeriodSnapshot.period == period,
        ProfitCheckerPeriodSnapshot.period_type == period_type,
    ).first()
    if not snap:
        snap = ProfitCheckerPeriodSnapshot(tenant_id=tenant_id, period=period, period_type=period_type)
        db.add(snap)

    snap.sales_revenue = sales_revenue.quantize(Decimal("0.01"))
    snap.order_count = order_count
    snap.cogs = cogs.quantize(Decimal("0.01"))
    snap.packaging_cost = packaging_cost.quantize(Decimal("0.01"))
    snap.courier_material_cost = courier_material_cost.quantize(Decimal("0.01"))
    snap.shipping_cost = shipping_cost.quantize(Decimal("0.01"))
    snap.gateway_fee = gateway_fee.quantize(Decimal("0.01"))
    snap.rto_loss = rto_loss.quantize(Decimal("0.01"))
    snap.salary_ops_cost = salary_ops.quantize(Decimal("0.01"))
    snap.ads_marketing_cost = ads_marketing.quantize(Decimal("0.01"))
    snap.other_cost = other.quantize(Decimal("0.01"))
    snap.total_expense = total_expense.quantize(Decimal("0.01"))
    snap.opening_stock_value = opening.quantize(Decimal("0.01"))
    snap.closing_stock_value = closing.quantize(Decimal("0.01"))
    snap.purchases_value = purchases.quantize(Decimal("0.01"))
    snap.gross_profit = gross_profit.quantize(Decimal("0.01"))
    snap.net_profit = net_profit.quantize(Decimal("0.01"))
    snap.margin_pct = margin_pct
    snap.computed_at = datetime.now(timezone.utc)

    db.flush()
    db.refresh(snap)
    return snap


def _period_months(period: str, period_type: str) -> list[str]:
    """Returns the list of monthly period strings for a quarterly or yearly period."""
    if period_type == "yearly":
        year = int(period)
        return [f"{year:04d}-{m:02d}" for m in range(1, 13)]
    if period_type == "quarterly":
        # Format: "2026-Q2"
        year, q = int(period[:4]), int(period[-1])
        start_month = (q - 1) * 3 + 1
        return [f"{year:04d}-{m:02d}" for m in range(start_month, start_month + 3)]
    return [period]


# ─────────────────────────────────────────────────────────────
# Alert detection
# ─────────────────────────────────────────────────────────────

def _detect_and_store_alerts(
    db: Session, tenant_id: UUID, month: str,
    snap: ProfitCheckerPeriodSnapshot,
) -> None:
    """
    After computing a monthly snapshot, raise persistent alerts for:
    - Negative net profit for the month
    - Low margin months (below 10%)
    Silently skip if alert already exists (de-duplicate by type+month+reference_id).
    """
    def _has_alert(alert_type: PcAlertType, ref: Optional[UUID] = None) -> bool:
        q = db.query(ProfitCheckerAlert).filter(
            ProfitCheckerAlert.tenant_id == tenant_id,
            ProfitCheckerAlert.alert_type == alert_type,
            ProfitCheckerAlert.month == month,
        )
        if ref:
            q = q.filter(ProfitCheckerAlert.reference_id == ref)
        return q.first() is not None

    def _add_alert(alert_type: PcAlertType, message: str, severity: str, ref: Optional[UUID] = None) -> None:
        if _has_alert(alert_type, ref):
            return
        db.add(ProfitCheckerAlert(
            tenant_id=tenant_id,
            alert_type=alert_type,
            reference_id=ref,
            month=month,
            message=message,
            severity=severity,
        ))

    if snap.net_profit < 0:
        _add_alert(
            PcAlertType.negative_month,
            f"Month {month} ended with a net loss of ₹{abs(float(snap.net_profit)):,.0f}. "
            f"Revenue ₹{float(snap.sales_revenue):,.0f}, Total Expenses ₹{float(snap.total_expense):,.0f}.",
            "critical",
        )
    elif snap.margin_pct < Decimal("10"):
        _add_alert(
            PcAlertType.low_margin_month,
            f"Month {month} margin is {float(snap.margin_pct):.1f}% (below 10% threshold). "
            f"Revenue ₹{float(snap.sales_revenue):,.0f}, Net Profit ₹{float(snap.net_profit):,.0f}.",
            "warning",
        )
    db.flush()


def detect_order_alerts(db: Session, tenant_id: UUID, month: str) -> None:
    """
    Check all OrderProfitPostings for the month, raise per-order negative alerts.
    Called after running upsert_order_profit_posting for a batch.
    """
    postings = (
        db.query(OrderProfitPosting)
        .filter(
            OrderProfitPosting.tenant_id == tenant_id,
            OrderProfitPosting.month == month,
            OrderProfitPosting.profit < 0,
        )
        .all()
    )
    for p in postings:
        exists = db.query(ProfitCheckerAlert).filter(
            ProfitCheckerAlert.tenant_id == tenant_id,
            ProfitCheckerAlert.alert_type == PcAlertType.negative_order,
            ProfitCheckerAlert.reference_id == p.order_id,
        ).first()
        if not exists:
            db.add(ProfitCheckerAlert(
                tenant_id=tenant_id,
                alert_type=PcAlertType.negative_order,
                reference_id=p.order_id,
                month=month,
                message=f"Order has a negative margin: ₹{float(p.profit):,.0f} ({float(p.margin_pct):.1f}%).",
                severity="critical",
            ))
    db.flush()


# ─────────────────────────────────────────────────────────────
# Alerts CRUD
# ─────────────────────────────────────────────────────────────

def get_alerts(
    db: Session, current_user: Employee,
    month: Optional[str] = None,
    include_dismissed: bool = False,
) -> list[ProfitCheckerAlert]:
    q = db.query(ProfitCheckerAlert).filter(
        ProfitCheckerAlert.tenant_id == current_user.tenant_id
    )
    if month:
        q = q.filter(ProfitCheckerAlert.month == month)
    if not include_dismissed:
        q = q.filter(ProfitCheckerAlert.is_dismissed == False)
    return q.order_by(ProfitCheckerAlert.created_at.desc()).all()


def dismiss_alert(db: Session, current_user: Employee, alert_id: UUID) -> ProfitCheckerAlert:
    a = db.query(ProfitCheckerAlert).filter(
        ProfitCheckerAlert.id == alert_id,
        ProfitCheckerAlert.tenant_id == current_user.tenant_id,
    ).first()
    if not a:
        raise ValueError("Alert not found")
    a.is_dismissed = True
    a.dismissed_at = datetime.now(timezone.utc)
    a.dismissed_by_id = current_user.id
    db.flush()
    db.refresh(a)
    return a


# ─────────────────────────────────────────────────────────────
# Cost update suggestions
# ─────────────────────────────────────────────────────────────

def get_cost_suggestions(db: Session, current_user: Employee) -> list[dict]:
    """
    Compare each product's WAC (from received POs) against its catalog cost_price.
    Return rows where they differ by more than 2% or cost_price is null.
    """
    wac = _wac_all(db, current_user.tenant_id)
    products = (
        db.query(Product)
        .filter(
            Product.tenant_id == current_user.tenant_id,
            Product.status == "active",
        )
        .all()
    )
    suggestions = []
    for p in products:
        wac_cost = wac.get(str(p.id))
        if wac_cost is None:
            continue
        catalog = _z(p.cost_price)
        if catalog == 0:
            diff_pct = 100.0
        else:
            diff_pct = float(abs(wac_cost - catalog) / catalog * 100)
        if diff_pct > 2:
            suggestions.append({
                "product_id": str(p.id),
                "product_code": p.product_code,
                "name": p.name,
                "current_cost_price": float(catalog),
                "wac_cost": float(wac_cost),
                "diff_pct": round(diff_pct, 2),
            })
    suggestions.sort(key=lambda x: x["diff_pct"], reverse=True)
    return suggestions


def apply_cost_suggestion(db: Session, current_user: Employee, product_id: UUID) -> Product:
    """Update product.cost_price to its current WAC."""
    wac = _wac_all(db, current_user.tenant_id)
    p = db.query(Product).filter(
        Product.id == product_id,
        Product.tenant_id == current_user.tenant_id,
    ).first()
    if not p:
        raise ValueError("Product not found")
    new_cost = wac.get(str(product_id))
    if new_cost is None:
        raise ValueError("No WAC available — no received purchase orders for this product")
    p.cost_price = new_cost
    db.flush()
    db.refresh(p)
    return p


# ─────────────────────────────────────────────────────────────
# Inventory carry-forward view
# ─────────────────────────────────────────────────────────────

def get_carry_forward(db: Session, current_user: Employee, month: str) -> list[dict]:
    """
    For each raw_material / packaging product that has a product map,
    return: product info, purchased this month, sold (via variants), remaining stock, stock value.
    """
    tid = current_user.tenant_id
    maps = get_product_maps(db, current_user)

    # Group by source product
    source_ids: set[UUID] = {m.source_product_id for m in maps}
    if not source_ids:
        return []

    year, mo = int(month[:4]), int(month[5:7])
    from datetime import datetime as dt2
    month_start = dt2(year, mo, 1, tzinfo=timezone.utc)
    month_end = dt2(year, mo + 1, 1, tzinfo=timezone.utc) if mo < 12 else dt2(year + 1, 1, 1, tzinfo=timezone.utc)

    wac = _wac_all(db, tid)
    out = []

    for src_id in source_ids:
        p = db.query(Product).filter(Product.id == src_id).first()
        if not p:
            continue

        # What we received this month (in base units, kg or piece etc.)
        purchased_qty = db.query(
            func.coalesce(func.sum(PurchaseOrderItem.quantity), 0)
        ).join(PurchaseOrder, PurchaseOrder.id == PurchaseOrderItem.purchase_order_id).filter(
            PurchaseOrder.tenant_id == tid,
            PurchaseOrderItem.product_id == src_id,
            PurchaseOrder.status == PurchaseOrderStatus.received,
            PurchaseOrder.received_at >= month_start,
            PurchaseOrder.received_at < month_end,
        ).scalar()
        purchased_qty = _z(purchased_qty)

        # Sold variants mapped to this source — sum quantity_change of sale movements
        # We use InventoryMovement to track consumption directly
        from app.models.inventory import InventoryMovement, MovementType
        target_ids = [m.target_product_id for m in maps if m.source_product_id == src_id]

        sold_qty = Decimal("0")
        for tid_v in target_ids:
            sold = db.query(
                func.coalesce(func.sum(func.abs(InventoryMovement.quantity_change)), 0)
            ).filter(
                InventoryMovement.tenant_id == tid,
                InventoryMovement.product_id == tid_v,
                InventoryMovement.movement_type == MovementType.sale,
                InventoryMovement.created_at >= month_start,
                InventoryMovement.created_at < month_end,
            ).scalar()
            sold_qty += _z(sold)

        # Current stock
        summary = db.query(InventorySummary).filter(
            InventorySummary.tenant_id == tid,
            InventorySummary.product_id == src_id,
        ).first()
        current_stock = _z(summary.current_stock if summary else 0)
        cost_per_unit = wac.get(str(src_id), _z(p.cost_price))
        stock_value = (current_stock * cost_per_unit).quantize(Decimal("0.01"))

        out.append({
            "product_id": str(src_id),
            "product_code": p.product_code,
            "name": p.name,
            "unit": p.unit.value if p.unit else "piece",
            "cost_per_unit": float(cost_per_unit),
            "purchased_qty": float(purchased_qty),
            "sold_qty": float(sold_qty),
            "current_stock": float(current_stock),
            "stock_value": float(stock_value),
            "mapped_variants": [str(t) for t in target_ids],
        })

    return out


# ─────────────────────────────────────────────────────────────
# Purchase Orders for month (auto-populate Product Purchases group)
# ─────────────────────────────────────────────────────────────

def get_pos_for_month(db: Session, current_user: Employee, month: str) -> list[dict]:
    """Return received PO items for a month with product details and carry-forward context."""
    tid = current_user.tenant_id
    year, mo = int(month[:4]), int(month[5:7])
    from datetime import datetime as dt3
    month_start = dt3(year, mo, 1, tzinfo=timezone.utc)
    month_end = dt3(year, mo + 1, 1, tzinfo=timezone.utc) if mo < 12 else dt3(year + 1, 1, 1, tzinfo=timezone.utc)

    pos = (
        db.query(PurchaseOrder)
        .filter(
            PurchaseOrder.tenant_id == tid,
            PurchaseOrder.status == PurchaseOrderStatus.received,
            PurchaseOrder.received_at >= month_start,
            PurchaseOrder.received_at < month_end,
        )
        .all()
    )

    wac = _wac_all(db, tid)
    maps_by_src = {}
    for m in get_product_maps(db, current_user):
        maps_by_src.setdefault(str(m.source_product_id), []).append(str(m.target_product_id))

    rows = []
    for po in pos:
        for item in po.items or []:
            p = item.product
            if not p:
                continue
            rows.append({
                "po_id": str(po.id),
                "po_number": po.po_number,
                "received_at": po.received_at.date().isoformat() if po.received_at else None,
                "item_id": str(item.id),
                "product_id": str(p.id),
                "product_code": p.product_code,
                "name": p.name,
                "item_type": p.item_type.value if p.item_type else "sellable",
                "unit": p.unit.value if p.unit else "piece",
                "quantity": float(item.quantity),
                "unit_cost": float(item.unit_cost),
                "total": float(item.line_total),
                "wac": float(wac.get(str(p.id), _z(p.cost_price))),
                "catalog_cost": float(_z(p.cost_price)),
                "cost_changed": abs(
                    float(wac.get(str(p.id), _z(p.cost_price))) - float(_z(p.cost_price))
                ) / max(float(_z(p.cost_price)), 0.01) * 100 > 2,
                "mapped_variants": maps_by_src.get(str(p.id), []),
            })
    return rows
