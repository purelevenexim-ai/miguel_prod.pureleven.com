from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import re
from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.purchase import PurchaseOrder, PurchaseOrderItem, PurchaseOrderStatus
from app.models.profit_loss import (
    ProfitCheckerEntry,
    ProfitCheckerGroup,
    ProfitCostConfig,
    ProfitMonthlyOverhead,
    OrderProfitPosting,
    PcGroupType,
)


def _to_decimal(v: Any, default: str = "0") -> Decimal:
    return Decimal(str(v if v is not None else default))


def _ensure_profit_tables(db: Session) -> None:
    bind = db.get_bind()
    if bind is None:
        return
    ProfitCostConfig.__table__.create(bind=bind, checkfirst=True)
    ProfitMonthlyOverhead.__table__.create(bind=bind, checkfirst=True)
    OrderProfitPosting.__table__.create(bind=bind, checkfirst=True)


def _month_key(dt: datetime | None) -> str:
    d = dt or datetime.now(timezone.utc)
    return f"{d.year:04d}-{d.month:02d}"


def _norm_name(value: str | None) -> str:
    """Strip variant suffix after em-dash and normalise whitespace/case."""
    text = str(value or "").strip().lower()
    if "\u2014" in text:          # em-dash  —
        text = text.split("\u2014", 1)[0].strip()
    if "\u2013" in text:          # en-dash  –
        text = text.split("\u2013", 1)[0].strip()
    return " ".join(text.split())


def _product_maps(db: Session, tenant_id: UUID):
    products = db.query(Product).filter(Product.tenant_id == tenant_id).all()
    by_code = {str((p.product_code or "")).strip().lower(): p for p in products if p.product_code}
    by_sku = {str((p.sku or "")).strip().lower(): p for p in products if p.sku}
    by_name = {str((p.name or "")).strip().lower(): p for p in products if p.name}
    by_norm = {_norm_name(p.name): p for p in products if p.name}
    return products, by_code, by_sku, by_name, by_norm


def _resolve_order_product(item: OrderItem, by_code: dict[str, Product], by_sku: dict[str, Product], by_name: dict[str, Product], by_norm: dict[str, Product] | None = None) -> Product | None:
    sku_key = str((item.sku or "")).strip().lower()
    name_key = str((item.product_name or "")).strip().lower()
    norm_key = _norm_name(item.product_name)
    return (
        by_sku.get(sku_key)
        or by_code.get(sku_key)
        or by_name.get(name_key)
        or (by_norm.get(norm_key) if by_norm else None)
    )


def _wac_by_product(db: Session, tenant_id: UUID) -> dict[str, Decimal]:
    rows = (
        db.query(
            PurchaseOrderItem.product_id.label("product_id"),
            func.coalesce(func.sum(PurchaseOrderItem.quantity), 0).label("qty"),
            func.coalesce(func.sum(PurchaseOrderItem.quantity * PurchaseOrderItem.unit_cost), 0).label("cost"),
        )
        .join(PurchaseOrder, PurchaseOrder.id == PurchaseOrderItem.purchase_order_id)
        .filter(
            PurchaseOrder.tenant_id == tenant_id,
            PurchaseOrder.status == PurchaseOrderStatus.received,
        )
        .group_by(PurchaseOrderItem.product_id)
        .all()
    )

    out: dict[str, Decimal] = {}
    for r in rows:
        qty = _to_decimal(r.qty)
        if qty > 0:
            out[str(r.product_id)] = (_to_decimal(r.cost) / qty).quantize(Decimal("0.01"))
    return out


def _item_pack_grams(product: Product | None) -> Decimal:
    if not product:
        return Decimal("0")

    # Priority 1: unit + unit_value
    uv = _to_decimal(product.unit_value)
    if uv > 0 and product.unit is not None:
        u = product.unit.value
        if u == "gram":
            return uv
        if u == "kg":
            return (uv * Decimal("1000")).quantize(Decimal("0.001"))

    # Priority 2: parse unit_label
    txt = str(product.unit_label or "").strip().lower()
    if txt:
        m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(kg|g)", txt)
        if m:
            n = Decimal(m.group(1))
            if m.group(2) == "kg":
                return (n * Decimal("1000")).quantize(Decimal("0.001"))
            return n

    return Decimal("0")


def _get_or_create_config(db: Session, tenant_id: UUID) -> ProfitCostConfig:
    cfg = db.query(ProfitCostConfig).filter(ProfitCostConfig.tenant_id == tenant_id).first()
    if cfg:
        return cfg
    cfg = ProfitCostConfig(tenant_id=tenant_id)
    db.add(cfg)
    db.flush()
    return cfg


def _monthly_overhead(db: Session, tenant_id: UUID, month: str) -> ProfitMonthlyOverhead | None:
    return (
        db.query(ProfitMonthlyOverhead)
        .filter(
            ProfitMonthlyOverhead.tenant_id == tenant_id,
            ProfitMonthlyOverhead.month == month,
        )
        .first()
    )


def _material_cost_rows(db: Session, tenant_id: UUID, month: str, sub_type: str) -> list[dict[str, Any]]:
    rows = (
        db.query(ProfitCheckerEntry, ProfitCheckerGroup)
        .join(ProfitCheckerGroup, ProfitCheckerGroup.id == ProfitCheckerEntry.group_id)
        .filter(
            ProfitCheckerEntry.tenant_id == tenant_id,
            ProfitCheckerEntry.month == month,
            ProfitCheckerGroup.group_type == PcGroupType.packaging,
            ProfitCheckerGroup.sub_type == sub_type,
            ProfitCheckerEntry.quantity.isnot(None),
            ProfitCheckerEntry.consumption_rate.isnot(None),
        )
        .all()
    )

    grouped: dict[tuple[str, tuple[str, ...], str], dict[str, Any]] = {}
    for entry, _group in rows:
        qty = _to_decimal(entry.quantity)
        rate = _to_decimal(entry.consumption_rate)
        if qty <= 0 or rate <= 0:
            continue
        amount = _to_decimal(entry.amount)
        if amount <= 0:
            unit_cost = _to_decimal(entry.unit_cost)
            amount = qty * unit_cost
        if amount <= 0:
            continue

        categories = tuple(sorted({str(cat).strip().casefold() for cat in (entry.applicable_categories or []) if str(cat).strip()}))
        key = (str(entry.description or "").strip().casefold(), categories, str(rate))
        bucket = grouped.setdefault(key, {
            "categories": list(categories),
            "rate": rate,
            "total_qty": Decimal("0"),
            "total_cost": Decimal("0"),
        })
        bucket["total_qty"] += qty
        bucket["total_cost"] += amount

    out: list[dict[str, Any]] = []
    for bucket in grouped.values():
        if bucket["total_qty"] <= 0:
            continue
        out.append({
            "categories": bucket["categories"],
            "rate": bucket["rate"],
            "unit_cost": (bucket["total_cost"] / bucket["total_qty"]).quantize(Decimal("0.0001")),
        })
    return out


def upsert_order_profit_posting(db: Session, tenant_id: UUID, order_id: UUID) -> OrderProfitPosting | None:
    _ensure_profit_tables(db)

    order = (
        db.query(Order)
        .options(selectinload(Order.items))
        .filter(Order.id == order_id, Order.tenant_id == tenant_id)
        .first()
    )
    if not order:
        return None

    # Skip inactive/cancelled orders from cost posting
    if (not order.is_active) or order.status == OrderStatus.cancelled:
        existing = db.query(OrderProfitPosting).filter(
            OrderProfitPosting.tenant_id == tenant_id,
            OrderProfitPosting.order_id == order_id,
        ).first()
        if existing:
            db.delete(existing)
            db.flush()
        return None

    products, by_code, by_sku, by_name, by_norm = _product_maps(db, tenant_id)
    _ = products
    wac_map = _wac_by_product(db, tenant_id)
    cfg = _get_or_create_config(db, tenant_id)

    # Use delivery date for month so costs align with revenue
    month = _month_key(order.delivered_at or order.created_at)
    packing_rows = _material_cost_rows(db, tenant_id, month, "packing_material")
    courier_rows = _material_cost_rows(db, tenant_id, month, "courier_material")

    box_rule = cfg.box_rule or {}
    _ = box_rule

    fee_rule = cfg.fee_rule or {}
    gateway_pct = _to_decimal(fee_rule.get("gateway_fee_pct", 0))
    rto_loss_pct = _to_decimal(fee_rule.get("rto_loss_pct", 0))

    total_items = Decimal("0")
    product_cost = Decimal("0")
    pouch_cost = Decimal("0")

    for item in order.items or []:
        qty = _to_decimal(item.quantity)
        total_items += qty

        product = _resolve_order_product(item, by_code, by_sku, by_name, by_norm)

        if product:
            p_cost = wac_map.get(str(product.id))
            if p_cost is None:
                p_cost = _to_decimal(product.cost_price)
            product_cost += (p_cost * qty)

    # Apply hardcoded packing costs
    # Pouch: ₹10 per item
    pouch_cost = (total_items * Decimal("10")).quantize(Decimal("0.01"))
    # Box: ₹15 per order
    box_cost = Decimal("15.00")
    sticker_cost = Decimal("0.00")
    packaging_cost = (pouch_cost + box_cost).quantize(Decimal("0.01"))
    courier_material_cost = sum((row["unit_cost"] * row["rate"] for row in courier_rows), Decimal("0")).quantize(Decimal("0.01"))

    shipping_cost = _to_decimal(order.shipping_charge).quantize(Decimal("0.01"))
    overhead = _monthly_overhead(db, tenant_id, month)

    # Use the same month key logic as posting.month (delivered_at fallback created_at)
    # so per-order fixed allocations are not skewed by created_at-only counts.
    posting_month_expr = func.to_char(func.coalesce(Order.delivered_at, Order.created_at), "YYYY-MM")
    active_orders_in_month = (
        db.query(func.count(Order.id))
        .filter(
            Order.tenant_id == tenant_id,
            Order.is_active == True,
            Order.status.notin_([OrderStatus.cancelled]),
            posting_month_expr == month,
        )
        .scalar() or 0
    )
    divisor = Decimal(str(active_orders_in_month if active_orders_in_month > 0 else 1))

    ads_allocated = Decimal("0")
    dispatch_allocated = Decimal("0")
    misc_allocated = Decimal("0")
    other_fixed_allocated = Decimal("0")
    if overhead:
        ads_allocated = (_to_decimal(overhead.ads_cost) / divisor).quantize(Decimal("0.01"))
        dispatch_allocated = (_to_decimal(overhead.dispatch_cost) / divisor).quantize(Decimal("0.01"))
        misc_allocated = (_to_decimal(overhead.misc_cost) / divisor).quantize(Decimal("0.01"))
        other_fixed_allocated = (_to_decimal(overhead.other_fixed_cost) / divisor).quantize(Decimal("0.01"))

    revenue = _to_decimal(order.total_amount).quantize(Decimal("0.01"))
    gateway_fee = (revenue * gateway_pct / Decimal("100")).quantize(Decimal("0.01"))
    rto_expected_loss = (revenue * rto_loss_pct / Decimal("100")).quantize(Decimal("0.01"))

    total_cost = (
        product_cost
        + packaging_cost
        + courier_material_cost
        + shipping_cost
        + ads_allocated
        + dispatch_allocated
        + misc_allocated
        + other_fixed_allocated
        + gateway_fee
        + rto_expected_loss
    ).quantize(Decimal("0.01"))
    profit = (revenue - total_cost).quantize(Decimal("0.01"))
    margin_pct = Decimal("0")
    if revenue > 0:
        margin_pct = ((profit / revenue) * Decimal("100")).quantize(Decimal("0.01"))

    posting = db.query(OrderProfitPosting).filter(
        OrderProfitPosting.tenant_id == tenant_id,
        OrderProfitPosting.order_id == order_id,
    ).first()
    if not posting:
        posting = OrderProfitPosting(tenant_id=tenant_id, order_id=order_id)
        db.add(posting)

    posting.month = month
    posting.cost_source = "wac_or_catalog"
    posting.product_cost = product_cost.quantize(Decimal("0.01"))
    posting.box_cost = box_cost.quantize(Decimal("0.01"))
    posting.pouch_cost = pouch_cost.quantize(Decimal("0.01"))
    posting.sticker_cost = sticker_cost
    posting.packaging_cost = packaging_cost
    posting.courier_material_cost = courier_material_cost
    posting.shipping_cost = shipping_cost
    posting.ads_allocated = ads_allocated
    posting.dispatch_allocated = dispatch_allocated
    posting.misc_allocated = misc_allocated
    posting.other_fixed_allocated = other_fixed_allocated
    posting.gateway_fee = gateway_fee
    posting.rto_expected_loss = rto_expected_loss
    posting.total_cost = total_cost
    posting.profit = profit
    posting.margin_pct = margin_pct

    db.flush()
    return posting
