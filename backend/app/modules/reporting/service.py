"""
Reporting Service
------------------
Pure aggregated SQL queries — no ORM mutations.
All queries are tenant-scoped.
Supports optional date-range + status filters.
"""

from __future__ import annotations

from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, case, and_, or_, extract
from sqlalchemy.orm import Session, selectinload

from app.models.customer import Customer
from app.models.lead import Lead, LeadPipelineStatus, LeadSource, LeadPriority
from app.models.order import Order, OrderItem, OrderStatus, PaymentStatus
from app.models.product import Product, ProductStatus
from app.models.purchase import PurchaseOrder, PurchaseOrderItem, PurchaseOrderStatus
from app.models.inventory import InventorySummary
from app.models.profit_loss import ProfitCostConfig, ProfitMonthlyOverhead, ProfitMonthlyPlanner, OrderProfitPosting
from app.models.employee import Employee
from app.core.tenant_utils import apply_tenant_filter
from app.modules.reporting.schemas import (
    DashboardStats,
    RevenueByMonth, RevenueReport,
    EmployeePerformance, EmployeeReport,
    LeadFunnelStage, LeadFunnelReport,
    TopCustomer, TopCustomersReport,
    CustomerProfitLtvRow, CustomerProfitLtvReport,
    ProductPerformance, ProductReport,
    PricingSuggestionRow, PricingSuggestionReport,
    StateSalesRow, StateSalesReport,
    ProductUsageInsight, ProductUsageTrendPoint,
    ForecastReport, RevenueForecastPoint,
    ProductDemandForecast, ProductDemandForecastPoint,
    PurchaseRecommendationRow, PurchaseRecommendationReport,
    ProfitCostPreviewRequest, ProfitCostPreviewResponse,
    ProfitCostConfigPayload, ProfitCostConfigResponse,
    ProfitMonthlyOverheadPayload, ProfitMonthlyOverheadResponse,
    ProfitMonthlyPlannerPayload, ProfitMonthlyPlannerResponse,
    NetPnlByMonth, NetPnlReport,
    ReconciliationRow, ReconciliationReport,
    DailySummaryRequest, DailySummaryResponse,
)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _month_start(dt: datetime) -> datetime:
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _zero(v) -> Decimal:
    return Decimal(str(v or "0"))


def _norm_product_name(value: Optional[str]) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    if "—" in text:
        text = text.split("—", 1)[0].strip()
    return " ".join(text.split())


def _build_product_lookup(products: list[Product]) -> tuple[dict[str, Product], dict[str, Product], dict[str, Product], dict[str, Product]]:
    by_product_code = {str((p.product_code or "")).strip().lower(): p for p in products if p.product_code}
    by_sku = {str((p.sku or "")).strip().lower(): p for p in products if p.sku}
    by_name = {str((p.name or "")).strip().lower(): p for p in products if p.name}
    by_norm_name = {_norm_product_name(p.name): p for p in products if p.name}
    return by_product_code, by_sku, by_name, by_norm_name


def _resolve_item_product(item: OrderItem, product_lookup: tuple[dict[str, Product], dict[str, Product], dict[str, Product], dict[str, Product]]) -> Optional[Product]:
    by_product_code, by_sku, by_name, by_norm_name = product_lookup
    sku_key = str((item.sku or "")).strip().lower()
    name_key = str((item.product_name or "")).strip().lower()
    norm_name_key = _norm_product_name(item.product_name)
    return (
        by_sku.get(sku_key)
        or by_product_code.get(sku_key)
        or by_name.get(name_key)
        or by_norm_name.get(norm_name_key)
    )


def _item_tax_amount(item: OrderItem, product: Optional[Product]) -> Decimal:
    if not product:
        return Decimal("0")

    rate = _zero(product.gst_rate)
    if rate <= 0:
        return Decimal("0")

    line_total = _zero(item.line_total)
    if line_total <= 0:
        return Decimal("0")

    if product.tax_inclusive:
        return (line_total * rate / (Decimal("100") + rate)).quantize(Decimal("0.01"))
    return (line_total * rate / Decimal("100")).quantize(Decimal("0.01"))


def _apply_date_filters(query, from_date: Optional[date], to_date: Optional[date]):
    """Apply date-range filters to an order query."""
    if from_date:
        query = query.filter(Order.created_at >= datetime.combine(from_date, datetime.min.time()))
    if to_date:
        query = query.filter(Order.created_at < datetime.combine(to_date + timedelta(days=1), datetime.min.time()))
    return query


def _apply_status_filter(query, status: Optional[str]):
    """Apply status filter to an order query."""
    if status:
        try:
            st = OrderStatus(status)
            query = query.filter(Order.status == st)
        except ValueError:
            pass  # ignore invalid status
    return query


def _month_key(dt: datetime) -> str:
    return f"{dt.year:04d}-{dt.month:02d}"


def _realized_order_datetime_expr():
    return func.coalesce(Order.delivered_at, Order.created_at)


def _realized_order_month_expr():
    return func.to_char(_realized_order_datetime_expr(), "YYYY-MM")


def _realized_order_datetime_value(order: Order) -> datetime:
    return order.delivered_at or order.created_at


def _month_add(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = (year * 12 + (month - 1)) + delta
    return idx // 12, (idx % 12) + 1


def _linear_forecast(values: list[Decimal], horizon: int = 3) -> list[Decimal]:
    if not values:
        return [Decimal("0") for _ in range(horizon)]
    if len(values) == 1:
        return [values[0] for _ in range(horizon)]

    n = Decimal(len(values))
    xs = [Decimal(i + 1) for i in range(len(values))]
    sum_x = sum(xs, Decimal("0"))
    sum_y = sum(values, Decimal("0"))
    sum_xy = sum((xs[i] * values[i] for i in range(len(values))), Decimal("0"))
    sum_x2 = sum((x * x for x in xs), Decimal("0"))

    denom = (n * sum_x2) - (sum_x * sum_x)
    slope = Decimal("0") if denom == 0 else ((n * sum_xy) - (sum_x * sum_y)) / denom
    intercept = (sum_y - (slope * sum_x)) / n

    out = []
    for i in range(horizon):
        x = Decimal(len(values) + i + 1)
        pred = intercept + (slope * x)
        out.append(pred if pred > 0 else Decimal("0"))
    return out


# ─────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────

def get_dashboard(
    db: Session,
    current_user: Employee,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    status: Optional[str] = None,
) -> DashboardStats:
    tid = current_user.tenant_id
    now = datetime.now(timezone.utc)
    ms  = _month_start(now)

    # ── Leads ────────────────────────────────────────────────
    lead_base = db.query(Lead).filter(Lead.tenant_id == tid)
    if from_date:
        lead_base = lead_base.filter(Lead.created_at >= datetime.combine(from_date, datetime.min.time()))
    if to_date:
        lead_base = lead_base.filter(Lead.created_at < datetime.combine(to_date + timedelta(days=1), datetime.min.time()))
    total_leads         = lead_base.count()
    leads_this_month    = lead_base.filter(Lead.created_at >= ms).count()
    leads_won           = lead_base.filter(Lead.status == LeadPipelineStatus.success_won).count()
    leads_lost          = lead_base.filter(Lead.status == LeadPipelineStatus.lost_lead).count()
    lead_conv_rate      = round(leads_won / total_leads * 100, 1) if total_leads else 0.0

    # ── Customers ────────────────────────────────────────────
    cust_base           = db.query(Customer).filter(Customer.tenant_id == tid)
    if from_date:
        cust_base = cust_base.filter(Customer.created_at >= datetime.combine(from_date, datetime.min.time()))
    if to_date:
        cust_base = cust_base.filter(Customer.created_at < datetime.combine(to_date + timedelta(days=1), datetime.min.time()))
    total_customers     = cust_base.filter(Customer.is_active == True).count()
    new_customers_month = cust_base.filter(Customer.is_active == True, Customer.created_at >= ms).count()
    active_customers    = cust_base.filter(Customer.is_active == True).count()

    # ── Orders ───────────────────────────────────────────────
    # Orders are hard-deleted so no is_active filter needed — all rows in DB are real orders
    ord_base = db.query(Order).filter(Order.tenant_id == tid)
    ord_base = _apply_date_filters(ord_base, from_date, to_date)
    ord_base = _apply_status_filter(ord_base, status)

    total_orders        = ord_base.count()
    orders_this_month   = ord_base.filter(Order.created_at >= ms).count()
    orders_delivered    = ord_base.filter(Order.status == OrderStatus.delivered).count()
    pending_statuses    = [
        OrderStatus.confirmed, OrderStatus.processing,
        OrderStatus.packed, OrderStatus.shipped, OrderStatus.out_for_delivery,
    ]
    orders_pending      = ord_base.filter(Order.status.in_(pending_statuses)).count()

    # ── Revenue ──────────────────────────────────────────────
    # Total revenue = sum of ALL non-cancelled order values (order book value)
    total_revenue = _zero(
        ord_base.filter(Order.status.notin_([OrderStatus.cancelled]))
        .with_entities(func.sum(Order.total_amount)).scalar()
    )
    # Revenue this month (within the already-filtered set)
    revenue_this_month = _zero(
        ord_base.filter(
            Order.status.notin_([OrderStatus.cancelled]),
            Order.created_at >= ms,
        ).with_entities(func.sum(Order.total_amount)).scalar()
    )
    # Delivered revenue = only orders that reached delivered status
    delivered_revenue = _zero(
        ord_base.filter(Order.status == OrderStatus.delivered)
        .with_entities(func.sum(Order.total_amount)).scalar()
    )
    total_outstanding = _zero(
        ord_base.filter(Order.status.notin_([OrderStatus.cancelled, OrderStatus.returned]))
        .with_entities(func.sum(Order.amount_due)).scalar()
    )
    total_shipping_cost = _zero(
        ord_base.filter(Order.status.notin_([OrderStatus.cancelled]))
        .with_entities(func.sum(Order.shipping_charge)).scalar()
    )

    # ── Products ─────────────────────────────────────────────
    prod_base       = db.query(Product).filter(Product.tenant_id == tid)
    total_products  = prod_base.count()
    active_products = prod_base.filter(Product.status == ProductStatus.active).count()

    return DashboardStats(
        total_leads=total_leads,
        leads_this_month=leads_this_month,
        leads_won=leads_won,
        leads_lost=leads_lost,
        lead_conversion_rate=lead_conv_rate,
        total_customers=total_customers,
        new_customers_this_month=new_customers_month,
        active_customers=active_customers,
        total_orders=total_orders,
        orders_this_month=orders_this_month,
        orders_delivered=orders_delivered,
        orders_pending=orders_pending,
        total_revenue=total_revenue,
        revenue_this_month=revenue_this_month,
        delivered_revenue=delivered_revenue,
        total_outstanding=total_outstanding,
        total_shipping_cost=total_shipping_cost,
        total_products=total_products,
        active_products=active_products,
    )


# ─────────────────────────────────────────────────────────────
# Revenue Report
# ─────────────────────────────────────────────────────────────

def get_revenue_report(
    db: Session,
    current_user: Employee,
    months: int = 12,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> RevenueReport:
    tid = current_user.tenant_id

    base_filter = [
        Order.tenant_id == tid,
        Order.is_active == True,
        Order.status.notin_([OrderStatus.cancelled]),
    ]
    if from_date:
        base_filter.append(Order.created_at >= datetime.combine(from_date, datetime.min.time()))
    if to_date:
        base_filter.append(Order.created_at < datetime.combine(to_date + timedelta(days=1), datetime.min.time()))

    # Monthly revenue — group by year+month of created_at
    rows = (
        db.query(
            extract("year",  Order.created_at).label("yr"),
            extract("month", Order.created_at).label("mo"),
            func.count(Order.id).label("cnt"),
            func.coalesce(func.sum(Order.total_amount), 0).label("rev"),
            func.coalesce(func.sum(Order.amount_due), 0).label("due"),
        )
        .filter(*base_filter)
        .group_by("yr", "mo")
        .order_by("yr", "mo")
        .all()
    )

    by_month = [
        RevenueByMonth(
            month=f"{int(r.yr):04d}-{int(r.mo):02d}",
            order_count=r.cnt,
            revenue=_zero(r.rev),
            outstanding=_zero(r.due),
        )
        for r in rows[-months:]
    ]

    total_revenue = sum((m.revenue for m in by_month), Decimal("0"))
    total_orders  = sum(m.order_count for m in by_month)

    period = f"Last {months} months"
    if from_date and to_date:
        period = f"{from_date.isoformat()} to {to_date.isoformat()}"
    elif from_date:
        period = f"From {from_date.isoformat()}"

    return RevenueReport(
        period_label=period,
        total_revenue=total_revenue,
        total_orders=total_orders,
        by_month=by_month,
    )


# ─────────────────────────────────────────────────────────────
# Employee Performance
# ─────────────────────────────────────────────────────────────

def get_employee_report(db: Session, current_user: Employee) -> EmployeeReport:
    tid = current_user.tenant_id

    employees = (
        db.query(Employee)
        .filter(Employee.tenant_id == tid, Employee.is_active == True)
        .all()
    )

    results = []
    for emp in employees:
        leads_created = (
            db.query(func.count(Lead.id))
            .filter(Lead.tenant_id == tid, Lead.created_by_id == emp.id)
            .scalar() or 0
        )
        leads_won = (
            db.query(func.count(Lead.id))
            .filter(Lead.tenant_id == tid, Lead.created_by_id == emp.id,
                    Lead.status == LeadPipelineStatus.success_won)
            .scalar() or 0
        )
        customers_created = (
            db.query(func.count(Customer.id))
            .filter(Customer.tenant_id == tid, Customer.created_by_employee_id == emp.id)
            .scalar() or 0
        )
        orders_created = (
            db.query(func.count(Order.id))
            .filter(Order.tenant_id == tid, Order.created_by_id == emp.id,
                    Order.is_active == True)
            .scalar() or 0
        )
        revenue = _zero(
            db.query(func.sum(Order.total_amount))
            .filter(Order.tenant_id == tid, Order.created_by_id == emp.id,
                    Order.status == OrderStatus.delivered)
            .scalar()
        )
        conv_rate = round(leads_won / leads_created * 100, 1) if leads_created else 0.0

        results.append(EmployeePerformance(
            employee_id=str(emp.id),
            employee_name=emp.full_name,
            role=emp.role.value,
            leads_created=leads_created,
            leads_won=leads_won,
            customers_created=customers_created,
            orders_created=orders_created,
            revenue_generated=revenue,
            conversion_rate=conv_rate,
        ))

    # Sort by revenue descending
    results.sort(key=lambda x: x.revenue_generated, reverse=True)

    return EmployeeReport(
        total_employees=len(results),
        results=results,
    )


# ─────────────────────────────────────────────────────────────
# Lead Funnel
# ─────────────────────────────────────────────────────────────

def get_lead_funnel(
    db: Session,
    current_user: Employee,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> LeadFunnelReport:
    tid = current_user.tenant_id

    lead_filters = [Lead.tenant_id == tid]
    if from_date:
        lead_filters.append(Lead.created_at >= datetime.combine(from_date, datetime.min.time()))
    if to_date:
        lead_filters.append(Lead.created_at < datetime.combine(to_date + timedelta(days=1), datetime.min.time()))

    lead_base = db.query(Lead).filter(*lead_filters)
    total = lead_base.count()

    # By status (funnel stages in pipeline order)
    stage_order = [
        LeadPipelineStatus.created,
        LeadPipelineStatus.new_lead,
        LeadPipelineStatus.contacted,
        LeadPipelineStatus.remind_later,
        LeadPipelineStatus.success_won,
        LeadPipelineStatus.lost_lead,
    ]
    funnel = []
    for stage in stage_order:
        cnt = lead_base.filter(Lead.status == stage).count()
        funnel.append(LeadFunnelStage(
            stage=stage.value,
            count=cnt,
            pct=round(cnt / total * 100, 1) if total else 0.0,
        ))

    # By source
    source_rows = (
        db.query(Lead.source, func.count(Lead.id))
        .filter(*lead_filters)
        .group_by(Lead.source)
        .all()
    )
    by_source = {(r[0].value if r[0] else "unknown"): r[1] for r in source_rows}

    # By priority
    priority_rows = (
        db.query(Lead.priority, func.count(Lead.id))
        .filter(*lead_filters)
        .group_by(Lead.priority)
        .all()
    )
    by_priority = {(r[0].value if r[0] else "unknown"): r[1] for r in priority_rows}

    return LeadFunnelReport(
        total_leads=total,
        by_source=by_source,
        by_priority=by_priority,
        funnel=funnel,
    )


# ─────────────────────────────────────────────────────────────
# Top Customers
# ─────────────────────────────────────────────────────────────

def get_top_customers(
    db: Session,
    current_user: Employee,
    limit: int = 10,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> TopCustomersReport:
    tid = current_user.tenant_id

    order_conditions = [
        Order.customer_id == Customer.id,
        Order.tenant_id   == tid,
        Order.is_active   == True,
        Order.status.notin_([OrderStatus.cancelled]),
    ]
    if from_date:
        order_conditions.append(Order.created_at >= datetime.combine(from_date, datetime.min.time()))
    if to_date:
        order_conditions.append(Order.created_at < datetime.combine(to_date + timedelta(days=1), datetime.min.time()))

    rows = (
        db.query(
            Customer.id,
            Customer.name,
            Customer.phone,
            Customer.city,
            func.count(Order.id).label("order_count"),
            func.coalesce(func.sum(Order.total_amount), 0).label("total_spent"),
        )
        .join(Order, and_(*order_conditions))
        .filter(Customer.tenant_id == tid)
        .group_by(Customer.id, Customer.name, Customer.phone, Customer.city)
        .order_by(func.sum(Order.total_amount).desc())
        .limit(limit)
        .all()
    )

    return TopCustomersReport(results=[
        TopCustomer(
            customer_id=str(r.id),
            name=r.name,
            phone=r.phone,
            city=r.city,
            order_count=r.order_count,
            total_spent=_zero(r.total_spent),
        )
        for r in rows
    ])


def get_customer_profit_ltv(
    db: Session,
    current_user: Employee,
    limit: int = 50,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> CustomerProfitLtvReport:
    tid = current_user.tenant_id
    limit = max(1, min(limit, 500))

    order_conditions = [
        Order.customer_id == Customer.id,
        Order.tenant_id == tid,
        Order.is_active == True,
        Order.status == OrderStatus.delivered,
    ]
    if from_date:
        order_conditions.append(
            func.coalesce(Order.delivered_at, Order.created_at) >= datetime.combine(from_date, datetime.min.time())
        )
    if to_date:
        order_conditions.append(
            func.coalesce(Order.delivered_at, Order.created_at) < datetime.combine(to_date + timedelta(days=1), datetime.min.time())
        )

    rows = (
        db.query(
            Customer.id.label("customer_id"),
            Customer.name.label("name"),
            Customer.phone.label("phone"),
            Customer.city.label("city"),
            func.count(Order.id).label("total_orders"),
            func.coalesce(func.sum(Order.total_amount), 0).label("total_revenue"),
            func.coalesce(func.sum(OrderProfitPosting.total_cost), 0).label("total_cost"),
        )
        .join(Order, and_(*order_conditions))
        .outerjoin(
            OrderProfitPosting,
            and_(
                OrderProfitPosting.order_id == Order.id,
                OrderProfitPosting.tenant_id == tid,
            ),
        )
        .filter(Customer.tenant_id == tid)
        .group_by(Customer.id, Customer.name, Customer.phone, Customer.city)
        .order_by(func.coalesce(func.sum(Order.total_amount), 0).desc())
        .limit(limit)
        .all()
    )

    results: list[CustomerProfitLtvRow] = []
    vip_count = 0
    loss_count = 0

    for r in rows:
        total_orders = int(r.total_orders or 0)
        revenue = _zero(r.total_revenue)
        cost = _zero(r.total_cost)
        profit = (revenue - cost).quantize(Decimal("0.01"))
        avg_order_value = Decimal("0")
        if total_orders > 0:
            avg_order_value = (revenue / Decimal(str(total_orders))).quantize(Decimal("0.01"))

        segment = "BREAKEVEN"
        if profit > Decimal("2000"):
            segment = "VIP"
            vip_count += 1
        elif profit > Decimal("500"):
            segment = "LOYAL"
        elif profit < Decimal("0"):
            segment = "LOSS"
            loss_count += 1

        results.append(CustomerProfitLtvRow(
            customer_id=str(r.customer_id),
            name=r.name,
            phone=r.phone,
            city=r.city,
            total_orders=total_orders,
            total_revenue=revenue,
            total_cost=cost,
            total_profit=profit,
            avg_order_value=avg_order_value,
            ltv=profit,
            segment=segment,
        ))

    results.sort(key=lambda x: x.total_profit, reverse=True)

    return CustomerProfitLtvReport(
        total_customers=len(results),
        vip_customers=vip_count,
        loss_customers=loss_count,
        results=results,
    )


# ─────────────────────────────────────────────────────────────
# Product Performance
# ─────────────────────────────────────────────────────────────

def get_product_report(
    db: Session,
    current_user: Employee,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> ProductReport:
    tid = current_user.tenant_id

    # Build order filters (with optional date filters)
    order_filters = [
        Order.tenant_id == tid,
        Order.is_active == True,
        Order.status.notin_([OrderStatus.cancelled]),
    ]
    if from_date:
        order_filters.append(Order.created_at >= datetime.combine(from_date, datetime.min.time()))
    if to_date:
        order_filters.append(Order.created_at < datetime.combine(to_date + timedelta(days=1), datetime.min.time()))

    # Aggregate from order_items + orders first so sold products always appear,
    # even when catalog names drift from historical order item names.
    rows = (
        db.query(
            OrderItem.product_name.label("name"),
            OrderItem.sku.label("sku"),
            func.count(func.distinct(OrderItem.order_id)).label("times_ordered"),
            func.coalesce(func.sum(OrderItem.quantity), 0).label("units_sold"),
            func.coalesce(func.sum(OrderItem.line_total), 0).label("revenue"),
            func.coalesce(func.avg(OrderItem.unit_price), 0).label("avg_unit_price"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .filter(*order_filters)
        .group_by(OrderItem.product_name, OrderItem.sku)
        .order_by(func.coalesce(func.sum(OrderItem.line_total), 0).desc())
        .all()
    )

    total = db.query(func.count(Product.id)).filter(Product.tenant_id == tid).scalar() or 0

    # Preferred costing source: weighted average cost from received purchase orders.
    wac_rows = (
        db.query(
            PurchaseOrderItem.product_id.label("product_id"),
            func.coalesce(func.sum(PurchaseOrderItem.quantity), 0).label("qty"),
            func.coalesce(func.sum(PurchaseOrderItem.quantity * PurchaseOrderItem.unit_cost), 0).label("cost"),
        )
        .join(PurchaseOrder, PurchaseOrder.id == PurchaseOrderItem.purchase_order_id)
        .filter(
            PurchaseOrder.tenant_id == tid,
            PurchaseOrder.status == PurchaseOrderStatus.received,
        )
        .group_by(PurchaseOrderItem.product_id)
        .all()
    )
    wac_by_product = {}
    for wr in wac_rows:
        qty = _zero(wr.qty)
        if qty > 0:
            wac_by_product[str(wr.product_id)] = (_zero(wr.cost) / qty).quantize(Decimal("0.01"))

    # Build a small lookup from catalog for enrichment (category, exact code).
    products = (
        db.query(Product)
        .filter(Product.tenant_id == tid)
        .all()
    )
    def _norm_name(v: Optional[str]) -> str:
        s = str(v or "").strip().lower()
        if not s:
            return ""
        # Historical order item names often append variant text after an em dash.
        if "—" in s:
            s = s.split("—", 1)[0].strip()
        return " ".join(s.split())

    by_product_code = {str((p.product_code or '')).strip().lower(): p for p in products if p.product_code}
    by_sku = {str((p.sku or '')).strip().lower(): p for p in products if p.sku}
    by_name = {str((p.name or '')).strip().lower(): p for p in products if p.name}
    by_norm_name = {_norm_name(p.name): p for p in products if p.name}

    results = []
    for r in rows:
        sku_key = str((r.sku or '')).strip().lower()
        name_key = str((r.name or '')).strip().lower()
        norm_name_key = _norm_name(r.name)
        matched = (
            by_sku.get(sku_key)
            or by_product_code.get(sku_key)
            or by_name.get(name_key)
            or by_norm_name.get(norm_name_key)
        )

        product_id = str(matched.id) if matched else (f"sku:{r.sku}" if r.sku else f"name:{r.name}")
        product_code = (matched.product_code if matched and matched.product_code else (r.sku or '—'))
        category = matched.category if matched else None
        unit_price = _zero(matched.unit_price if matched else r.avg_unit_price)
        units_sold = _zero(r.units_sold)
        revenue = _zero(r.revenue)

        cost_price = None
        total_cost = None
        gross_profit = None
        margin_pct = None
        cost_source = None
        if matched:
            cp = wac_by_product.get(str(matched.id))
            if cp is not None:
                cost_source = "wac"
            elif matched.cost_price is not None:
                cp = _zero(matched.cost_price)
                cost_source = "catalog_cost_price"
            else:
                cp = None

            if cp is not None and cp > 0:
                cost_price = cp
                total_cost = (cp * units_sold).quantize(Decimal("0.01"))
                gross_profit = (revenue - total_cost).quantize(Decimal("0.01"))
                if revenue > 0:
                    margin_pct = float((gross_profit / revenue * Decimal("100")).quantize(Decimal("0.1")))

        results.append(ProductPerformance(
            product_id=product_id,
            product_code=product_code,
            name=r.name,
            category=category,
            unit_price=unit_price,
            times_ordered=r.times_ordered,
            units_sold=units_sold,
            revenue=revenue,
            cost_price=cost_price,
            total_cost=total_cost,
            gross_profit=gross_profit,
            margin_pct=margin_pct,
            cost_source=cost_source,
        ))

    return ProductReport(
        total_products=total,
        results=results,
    )


def get_pricing_suggestions(
    db: Session,
    current_user: Employee,
    limit: int = 200,
) -> PricingSuggestionReport:
    _ensure_profit_tables(db)

    cfg = db.query(ProfitCostConfig).filter(
        ProfitCostConfig.tenant_id == current_user.tenant_id
    ).first()
    fee_rule = (cfg.fee_rule or {}) if cfg else {}
    target_margin = _zero(fee_rule.get("target_margin_pct") or 25)
    low_threshold = _zero(fee_rule.get("low_margin_threshold_pct") or 20)

    product_report = get_product_report(db, current_user)
    rows = product_report.results[: max(1, min(limit, 1000))]

    suggestions: list[PricingSuggestionRow] = []
    low_count = 0
    neg_count = 0

    for r in rows:
        unit_price = _zero(r.unit_price)
        unit_cost = _zero(r.cost_price) if r.cost_price is not None else None

        current_margin_pct = None
        suggested_price = None
        suggested_delta = None
        severity = "ok"

        if unit_cost is not None and unit_price > 0:
            current_margin_pct = ((unit_price - unit_cost) / unit_price * Decimal("100")).quantize(Decimal("0.01"))
            suggested_price = (unit_cost * (Decimal("1") + (target_margin / Decimal("100")))).quantize(Decimal("0.01"))
            suggested_delta = (suggested_price - unit_price).quantize(Decimal("0.01"))

            if current_margin_pct < 0:
                severity = "critical"
                neg_count += 1
                low_count += 1
            elif current_margin_pct < low_threshold:
                severity = "warning"
                low_count += 1
        elif unit_cost is None:
            severity = "missing_cost"

        suggestions.append(PricingSuggestionRow(
            product_id=r.product_id,
            product_code=r.product_code,
            name=r.name,
            unit_price=unit_price,
            unit_cost=unit_cost,
            current_margin_pct=current_margin_pct,
            target_margin_pct=target_margin.quantize(Decimal("0.01")),
            low_margin_threshold=low_threshold.quantize(Decimal("0.01")),
            suggested_price=suggested_price,
            suggested_delta=suggested_delta,
            severity=severity,
            cost_source=r.cost_source,
        ))

    severity_rank = {"critical": 0, "warning": 1, "missing_cost": 2, "ok": 3}
    suggestions.sort(key=lambda x: (severity_rank.get(x.severity, 99), x.suggested_delta or Decimal("0")))

    return PricingSuggestionReport(
        total_products=len(suggestions),
        low_margin_products=low_count,
        negative_margin_products=neg_count,
        results=suggestions,
    )


# ─────────────────────────────────────────────────────────────
# State Sales
# ─────────────────────────────────────────────────────────────

def get_state_sales_report(
    db: Session,
    current_user: Employee,
    limit: int = 20,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> StateSalesReport:
    tid = current_user.tenant_id
    state_expr = func.coalesce(func.nullif(Order.delivery_state, ""), func.nullif(Customer.state, ""), "Unknown")

    order_base = [
        Order.tenant_id == tid,
        Order.is_active == True,
        Order.status.notin_([OrderStatus.cancelled]),
    ]
    if from_date:
        order_base.append(Order.created_at >= datetime.combine(from_date, datetime.min.time()))
    if to_date:
        order_base.append(Order.created_at < datetime.combine(to_date + timedelta(days=1), datetime.min.time()))

    rows = (
        db.query(
            state_expr.label("state"),
            func.count(Order.id).label("order_count"),
            func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
            func.coalesce(func.sum(Order.amount_due), 0).label("outstanding"),
        )
        .outerjoin(Customer, Customer.id == Order.customer_id)
        .filter(*order_base)
        .group_by(state_expr)
        .order_by(func.coalesce(func.sum(Order.total_amount), 0).desc())
        .limit(limit)
        .all()
    )

    units_rows = (
        db.query(
            state_expr.label("state"),
            func.coalesce(func.sum(OrderItem.quantity), 0).label("units_sold"),
        )
        .join(OrderItem, OrderItem.order_id == Order.id)
        .outerjoin(Customer, Customer.id == Order.customer_id)
        .filter(*order_base)
        .group_by(state_expr)
        .all()
    )
    units_map = {r.state: _zero(r.units_sold) for r in units_rows}

    out_rows = []
    for r in rows:
        revenue = _zero(r.revenue)
        oc = int(r.order_count or 0)
        out_rows.append(StateSalesRow(
            state=r.state,
            order_count=oc,
            units_sold=units_map.get(r.state, Decimal("0")),
            revenue=revenue,
            outstanding=_zero(r.outstanding),
            avg_order_value=(revenue / oc) if oc else Decimal("0"),
        ))

    return StateSalesReport(results=out_rows)


# ─────────────────────────────────────────────────────────────
# Product Usage Insights
# ─────────────────────────────────────────────────────────────

def get_product_usage_insight(
    db: Session,
    current_user: Employee,
    months: int = 6,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> ProductUsageInsight:
    tid = current_user.tenant_id
    months = max(1, min(months, 24))

    top = get_product_report(db, current_user, from_date=from_date, to_date=to_date).results[:8]

    filters = [
        Order.tenant_id == tid,
        Order.is_active == True,
        Order.status.notin_([OrderStatus.cancelled]),
    ]
    if from_date:
        filters.append(Order.created_at >= datetime.combine(from_date, datetime.min.time()))
    if to_date:
        filters.append(Order.created_at < datetime.combine(to_date + timedelta(days=1), datetime.min.time()))

    rows = (
        db.query(
            extract("year", Order.created_at).label("yr"),
            extract("month", Order.created_at).label("mo"),
            func.count(func.distinct(OrderItem.product_name)).label("distinct_products"),
            func.coalesce(func.sum(OrderItem.quantity), 0).label("units_sold"),
        )
        .join(OrderItem, OrderItem.order_id == Order.id)
        .filter(*filters)
        .group_by("yr", "mo")
        .order_by("yr", "mo")
        .all()
    )

    trend = [
        ProductUsageTrendPoint(
            month=f"{int(r.yr):04d}-{int(r.mo):02d}",
            distinct_products=int(r.distinct_products or 0),
            units_sold=_zero(r.units_sold),
        )
        for r in rows[-months:]
    ]

    total_products_used = int(sum((p.distinct_products for p in trend), 0))
    total_units_sold = sum((p.units_sold for p in trend), Decimal("0"))

    return ProductUsageInsight(
        total_products_used=total_products_used,
        total_units_sold=total_units_sold,
        top_products_sold=top,
        usage_trend=trend,
    )


# ─────────────────────────────────────────────────────────────
# Forecast
# ─────────────────────────────────────────────────────────────

def get_forecast_report(
    db: Session,
    current_user: Employee,
    months: int = 6,
    horizon: int = 3,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> ForecastReport:
    tid = current_user.tenant_id
    months = max(3, min(months, 24))
    horizon = max(1, min(horizon, 6))

    order_filters = [
        Order.tenant_id == tid,
        Order.is_active == True,
        Order.status.notin_([OrderStatus.cancelled]),
    ]
    if from_date:
        order_filters.append(Order.created_at >= datetime.combine(from_date, datetime.min.time()))
    if to_date:
        order_filters.append(Order.created_at < datetime.combine(to_date + timedelta(days=1), datetime.min.time()))

    rev_rows = (
        db.query(
            extract("year", Order.created_at).label("yr"),
            extract("month", Order.created_at).label("mo"),
            func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
        )
        .filter(*order_filters)
        .group_by("yr", "mo")
        .order_by("yr", "mo")
        .all()
    )
    rev_rows = rev_rows[-months:]

    if rev_rows:
        base_year = int(rev_rows[-1].yr)
        base_month = int(rev_rows[-1].mo)
        rev_forecast_values = _linear_forecast([_zero(r.revenue) for r in rev_rows], horizon=horizon)
        revenue_forecast = []
        for i, value in enumerate(rev_forecast_values, start=1):
            yr, mo = _month_add(base_year, base_month, i)
            revenue_forecast.append(RevenueForecastPoint(month=f"{yr:04d}-{mo:02d}", forecast_revenue=value))
    else:
        now = datetime.now(timezone.utc)
        revenue_forecast = []
        for i in range(1, horizon + 1):
            yr, mo = _month_add(now.year, now.month, i)
            revenue_forecast.append(RevenueForecastPoint(month=f"{yr:04d}-{mo:02d}", forecast_revenue=Decimal("0")))

    top_products = get_product_report(
        db,
        current_user,
        from_date=from_date,
        to_date=to_date,
    ).results[:5]
    product_demand_forecast = []
    for p in top_products:
        unit_rows = (
            db.query(
                extract("year", Order.created_at).label("yr"),
                extract("month", Order.created_at).label("mo"),
                func.coalesce(func.sum(OrderItem.quantity), 0).label("units"),
            )
            .join(Order, Order.id == OrderItem.order_id)
            .filter(*order_filters, OrderItem.product_name == p.name)
            .group_by("yr", "mo")
            .order_by("yr", "mo")
            .all()
        )
        unit_rows = unit_rows[-months:]

        if unit_rows:
            base_year = int(unit_rows[-1].yr)
            base_month = int(unit_rows[-1].mo)
            unit_forecast_values = _linear_forecast([_zero(r.units) for r in unit_rows], horizon=horizon)
        else:
            now = datetime.now(timezone.utc)
            base_year = now.year
            base_month = now.month
            unit_forecast_values = [Decimal("0") for _ in range(horizon)]

        trend = []
        for i, value in enumerate(unit_forecast_values, start=1):
            yr, mo = _month_add(base_year, base_month, i)
            trend.append(ProductDemandForecastPoint(month=f"{yr:04d}-{mo:02d}", forecast_units=value))

        product_demand_forecast.append(ProductDemandForecast(
            product_id=p.product_id,
            name=p.name,
            trend=trend,
        ))

    return ForecastReport(
        revenue_forecast=revenue_forecast,
        product_demand_forecast=product_demand_forecast,
    )


# ─────────────────────────────────────────────────────────────
# Purchase Recommendations
# ─────────────────────────────────────────────────────────────

def get_purchase_recommendations(
    db: Session,
    current_user: Employee,
    horizon_days: int = 30,
    safety_days: int = 10,
    lookback_days: int = 30,
) -> PurchaseRecommendationReport:
    tid = current_user.tenant_id
    horizon_days = max(1, min(horizon_days, 90))
    safety_days = max(0, min(safety_days, 60))
    lookback_days = max(7, min(lookback_days, 120))
    usage_start = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    cost_30d_start = datetime.now(timezone.utc) - timedelta(days=30)

    products = (
        db.query(Product)
        .filter(
            Product.tenant_id == tid,
            Product.status == ProductStatus.active,
        )
        .all()
    )

    stock_rows = (
        db.query(InventorySummary.product_id, func.coalesce(InventorySummary.current_stock, 0).label("stock"))
        .filter(InventorySummary.tenant_id == tid)
        .all()
    )
    stock_by_product = {str(r.product_id): _zero(r.stock) for r in stock_rows}

    usage_rows = (
        db.query(
            OrderItem.product_name.label("name"),
            OrderItem.sku.label("sku"),
            func.coalesce(func.sum(OrderItem.quantity), 0).label("qty"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .filter(
            Order.tenant_id == tid,
            Order.is_active == True,
            Order.status.notin_([OrderStatus.cancelled, OrderStatus.returned]),
            Order.created_at >= usage_start,
        )
        .group_by(OrderItem.product_name, OrderItem.sku)
        .all()
    )

    by_code = {str((p.product_code or "")).strip().lower(): p for p in products if p.product_code}
    by_name = {str((p.name or "")).strip().lower(): p for p in products if p.name}
    usage_by_product: dict[str, Decimal] = {}
    for u in usage_rows:
        sku_key = str((u.sku or "")).strip().lower()
        name_key = str((u.name or "")).strip().lower()
        matched = by_code.get(sku_key) or by_name.get(name_key)
        if not matched:
            continue
        pid = str(matched.id)
        usage_by_product[pid] = usage_by_product.get(pid, Decimal("0")) + _zero(u.qty)

    all_cost_rows = (
        db.query(
            PurchaseOrderItem.product_id.label("product_id"),
            func.coalesce(func.sum(PurchaseOrderItem.quantity), 0).label("qty"),
            func.coalesce(func.sum(PurchaseOrderItem.quantity * PurchaseOrderItem.unit_cost), 0).label("cost"),
        )
        .join(PurchaseOrder, PurchaseOrder.id == PurchaseOrderItem.purchase_order_id)
        .filter(
            PurchaseOrder.tenant_id == tid,
            PurchaseOrder.status == PurchaseOrderStatus.received,
        )
        .group_by(PurchaseOrderItem.product_id)
        .all()
    )
    current_cost_by_product: dict[str, Decimal] = {}
    for r in all_cost_rows:
        qty = _zero(r.qty)
        if qty > 0:
            current_cost_by_product[str(r.product_id)] = (_zero(r.cost) / qty).quantize(Decimal("0.01"))

    last_30d_cost_rows = (
        db.query(
            PurchaseOrderItem.product_id.label("product_id"),
            func.coalesce(func.sum(PurchaseOrderItem.quantity), 0).label("qty"),
            func.coalesce(func.sum(PurchaseOrderItem.quantity * PurchaseOrderItem.unit_cost), 0).label("cost"),
        )
        .join(PurchaseOrder, PurchaseOrder.id == PurchaseOrderItem.purchase_order_id)
        .filter(
            PurchaseOrder.tenant_id == tid,
            PurchaseOrder.status == PurchaseOrderStatus.received,
            PurchaseOrder.received_at.isnot(None),
            PurchaseOrder.received_at >= cost_30d_start,
        )
        .group_by(PurchaseOrderItem.product_id)
        .all()
    )
    avg_30d_cost_by_product: dict[str, Decimal] = {}
    for r in last_30d_cost_rows:
        qty = _zero(r.qty)
        if qty > 0:
            avg_30d_cost_by_product[str(r.product_id)] = (_zero(r.cost) / qty).quantize(Decimal("0.01"))

    rows: list[PurchaseRecommendationRow] = []
    for p in products:
        pid = str(p.id)
        stock_on_hand = stock_by_product.get(pid, Decimal("0"))
        total_usage = usage_by_product.get(pid, Decimal("0"))
        daily_usage = (total_usage / Decimal(str(lookback_days))).quantize(Decimal("0.001"))

        target_stock = (daily_usage * Decimal(str(horizon_days + safety_days))).quantize(Decimal("0.001"))
        recommended_purchase = (target_stock - stock_on_hand).quantize(Decimal("0.001"))
        if recommended_purchase < 0:
            recommended_purchase = Decimal("0")

        days_remaining = None
        if daily_usage > 0:
            days_remaining = (stock_on_hand / daily_usage).quantize(Decimal("0.1"))

        current_cost = current_cost_by_product.get(pid)
        avg_30d_cost = avg_30d_cost_by_product.get(pid)
        price_signal = None
        if current_cost is not None and avg_30d_cost is not None and avg_30d_cost > 0:
            if current_cost > avg_30d_cost * Decimal("1.05"):
                price_signal = "high_price_buy_conservative"
            elif current_cost < avg_30d_cost * Decimal("0.95"):
                price_signal = "low_price_bulk_opportunity"
            else:
                price_signal = "normal_price"

        rows.append(PurchaseRecommendationRow(
            product_id=pid,
            product_code=p.product_code,
            name=p.name,
            unit=p.unit.value if p.unit else "piece",
            stock_on_hand=stock_on_hand,
            daily_usage=daily_usage,
            days_remaining=days_remaining,
            target_stock=target_stock,
            recommended_purchase=recommended_purchase,
            current_unit_cost=current_cost,
            last_30d_avg_cost=avg_30d_cost,
            price_signal=price_signal,
        ))

    rows.sort(key=lambda r: (r.recommended_purchase, r.daily_usage), reverse=True)
    return PurchaseRecommendationReport(
        horizon_days=horizon_days,
        safety_days=safety_days,
        lookback_days=lookback_days,
        results=rows,
    )


def get_profit_cost_preview(data: ProfitCostPreviewRequest) -> ProfitCostPreviewResponse:
    """
    Dynamic cost calculator driven entirely by UI inputs.
    No fixed pouch/sticker/overhead constants are hardcoded in business logic.
    """
    box_cost = data.box_small_cost
    if data.total_items >= data.box_large_min_items or data.total_weight_grams >= data.box_large_min_weight_grams:
        box_cost = data.box_large_cost

    packaging_cost = (box_cost + data.pouch_cost_total + data.sticker_cost_total + data.packaging_extra_per_order).quantize(Decimal("0.01"))
    courier_material_cost = data.courier_material_cost.quantize(Decimal("0.01"))

    pre_fee_cost = (
        data.product_cost
        + packaging_cost
        + courier_material_cost
        + data.shipping_cost
        + data.ads_allocated
        + data.dispatch_cost
        + data.misc_cost
    ).quantize(Decimal("0.01"))

    gateway_fee = (data.selling_price * (data.gateway_fee_pct / Decimal("100"))).quantize(Decimal("0.01"))
    rto_expected_loss = (data.selling_price * (data.rto_loss_pct / Decimal("100"))).quantize(Decimal("0.01"))
    platform_fee = (data.selling_price * (data.platform_fee_pct / Decimal("100"))).quantize(Decimal("0.01"))

    total_cost = (pre_fee_cost + gateway_fee + rto_expected_loss + platform_fee).quantize(Decimal("0.01"))
    profit = (data.selling_price - total_cost).quantize(Decimal("0.01"))
    margin_pct = Decimal("0.00")
    if data.selling_price > 0:
        margin_pct = ((profit / data.selling_price) * Decimal("100")).quantize(Decimal("0.01"))

    return ProfitCostPreviewResponse(
        box_cost=box_cost.quantize(Decimal("0.01")),
        packaging_cost=packaging_cost,
        gateway_fee=gateway_fee,
        rto_expected_loss=rto_expected_loss,
        platform_fee=platform_fee,
        total_cost=total_cost,
        profit=profit,
        margin_pct=margin_pct,
    )


def _ensure_profit_tables(db: Session) -> None:
    bind = db.get_bind()
    if bind is None:
        return
    ProfitCostConfig.__table__.create(bind=bind, checkfirst=True)
    ProfitMonthlyOverhead.__table__.create(bind=bind, checkfirst=True)
    ProfitMonthlyPlanner.__table__.create(bind=bind, checkfirst=True)
    OrderProfitPosting.__table__.create(bind=bind, checkfirst=True)


def _zero_planner_payload(month: str) -> ProfitMonthlyPlannerResponse:
    z = Decimal("0")
    return ProfitMonthlyPlannerResponse(
        month=month,
        revenue=z,
        orders=z,
        cogs=z,
        returns_loss=z,
        small_box_cost=z,
        small_box_qty=z,
        large_box_cost=z,
        large_box_qty=z,
        pouch_250_cost=z,
        pouch_250_qty=z,
        pouch_500_cost=z,
        pouch_500_qty=z,
        pouch_1kg_cost=z,
        pouch_1kg_qty=z,
        sticker_total=z,
        indian_post_total=z,
        delivery_convenience=z,
        platform_gateway=z,
        ads_monthly=z,
        salary_monthly=z,
        rent_utilities=z,
        software_tools=z,
        misc_monthly=z,
        other_fixed=z,
    )


def get_profit_monthly_planner(
    db: Session,
    current_user: Employee,
    month: str,
) -> ProfitMonthlyPlannerResponse:
    _ensure_profit_tables(db)

    if not month or len(month) != 7 or month[4] != "-":
        return _zero_planner_payload(month or "")

    row = db.query(ProfitMonthlyPlanner).filter(
        ProfitMonthlyPlanner.tenant_id == current_user.tenant_id,
        ProfitMonthlyPlanner.month == month,
    ).first()
    if not row:
        return _zero_planner_payload(month)

    return ProfitMonthlyPlannerResponse(
        month=row.month,
        revenue=_zero(row.revenue),
        orders=_zero(row.orders),
        cogs=_zero(row.cogs),
        returns_loss=_zero(row.returns_loss),
        small_box_cost=_zero(row.small_box_cost),
        small_box_qty=_zero(row.small_box_qty),
        large_box_cost=_zero(row.large_box_cost),
        large_box_qty=_zero(row.large_box_qty),
        pouch_250_cost=_zero(row.pouch_250_cost),
        pouch_250_qty=_zero(row.pouch_250_qty),
        pouch_500_cost=_zero(row.pouch_500_cost),
        pouch_500_qty=_zero(row.pouch_500_qty),
        pouch_1kg_cost=_zero(row.pouch_1kg_cost),
        pouch_1kg_qty=_zero(row.pouch_1kg_qty),
        sticker_total=_zero(row.sticker_total),
        indian_post_total=_zero(row.indian_post_total),
        delivery_convenience=_zero(row.delivery_convenience),
        platform_gateway=_zero(row.platform_gateway),
        ads_monthly=_zero(row.ads_monthly),
        salary_monthly=_zero(row.salary_monthly),
        rent_utilities=_zero(row.rent_utilities),
        software_tools=_zero(row.software_tools),
        misc_monthly=_zero(row.misc_monthly),
        other_fixed=_zero(row.other_fixed),
    )


def upsert_profit_monthly_planner(
    db: Session,
    current_user: Employee,
    data: ProfitMonthlyPlannerPayload,
) -> ProfitMonthlyPlannerResponse:
    _ensure_profit_tables(db)

    row = db.query(ProfitMonthlyPlanner).filter(
        ProfitMonthlyPlanner.tenant_id == current_user.tenant_id,
        ProfitMonthlyPlanner.month == data.month,
    ).first()
    if not row:
        row = ProfitMonthlyPlanner(
            tenant_id=current_user.tenant_id,
            month=data.month,
        )
        db.add(row)

    row.revenue = data.revenue
    row.orders = data.orders
    row.cogs = data.cogs
    row.returns_loss = data.returns_loss
    row.small_box_cost = data.small_box_cost
    row.small_box_qty = data.small_box_qty
    row.large_box_cost = data.large_box_cost
    row.large_box_qty = data.large_box_qty
    row.pouch_250_cost = data.pouch_250_cost
    row.pouch_250_qty = data.pouch_250_qty
    row.pouch_500_cost = data.pouch_500_cost
    row.pouch_500_qty = data.pouch_500_qty
    row.pouch_1kg_cost = data.pouch_1kg_cost
    row.pouch_1kg_qty = data.pouch_1kg_qty
    row.sticker_total = data.sticker_total
    row.indian_post_total = data.indian_post_total
    row.delivery_convenience = data.delivery_convenience
    row.platform_gateway = data.platform_gateway
    row.ads_monthly = data.ads_monthly
    row.salary_monthly = data.salary_monthly
    row.rent_utilities = data.rent_utilities
    row.software_tools = data.software_tools
    row.misc_monthly = data.misc_monthly
    row.other_fixed = data.other_fixed

    db.commit()
    db.refresh(row)

    return ProfitMonthlyPlannerResponse(
        month=row.month,
        revenue=_zero(row.revenue),
        orders=_zero(row.orders),
        cogs=_zero(row.cogs),
        returns_loss=_zero(row.returns_loss),
        small_box_cost=_zero(row.small_box_cost),
        small_box_qty=_zero(row.small_box_qty),
        large_box_cost=_zero(row.large_box_cost),
        large_box_qty=_zero(row.large_box_qty),
        pouch_250_cost=_zero(row.pouch_250_cost),
        pouch_250_qty=_zero(row.pouch_250_qty),
        pouch_500_cost=_zero(row.pouch_500_cost),
        pouch_500_qty=_zero(row.pouch_500_qty),
        pouch_1kg_cost=_zero(row.pouch_1kg_cost),
        pouch_1kg_qty=_zero(row.pouch_1kg_qty),
        sticker_total=_zero(row.sticker_total),
        indian_post_total=_zero(row.indian_post_total),
        delivery_convenience=_zero(row.delivery_convenience),
        platform_gateway=_zero(row.platform_gateway),
        ads_monthly=_zero(row.ads_monthly),
        salary_monthly=_zero(row.salary_monthly),
        rent_utilities=_zero(row.rent_utilities),
        software_tools=_zero(row.software_tools),
        misc_monthly=_zero(row.misc_monthly),
        other_fixed=_zero(row.other_fixed),
    )


def get_profit_cost_config(db: Session, current_user: Employee) -> ProfitCostConfigResponse:
    _ensure_profit_tables(db)

    cfg = db.query(ProfitCostConfig).filter(
        ProfitCostConfig.tenant_id == current_user.tenant_id
    ).first()
    if not cfg:
        cfg = ProfitCostConfig(tenant_id=current_user.tenant_id)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)

    return ProfitCostConfigResponse(
        tenant_id=str(current_user.tenant_id),
        box_rule=cfg.box_rule or {},
        pouch_slabs=cfg.pouch_slabs or [],
        sticker_rule=cfg.sticker_rule or {},
        fee_rule=cfg.fee_rule or {},
        note=cfg.note,
    )


def upsert_profit_cost_config(
    db: Session,
    current_user: Employee,
    data: ProfitCostConfigPayload,
) -> ProfitCostConfigResponse:
    _ensure_profit_tables(db)

    cfg = db.query(ProfitCostConfig).filter(
        ProfitCostConfig.tenant_id == current_user.tenant_id
    ).first()
    if not cfg:
        cfg = ProfitCostConfig(tenant_id=current_user.tenant_id)
        db.add(cfg)

    cfg.box_rule = data.box_rule
    cfg.pouch_slabs = data.pouch_slabs
    cfg.sticker_rule = data.sticker_rule
    cfg.fee_rule = data.fee_rule
    cfg.note = data.note

    db.commit()
    db.refresh(cfg)

    return ProfitCostConfigResponse(
        tenant_id=str(current_user.tenant_id),
        box_rule=cfg.box_rule or {},
        pouch_slabs=cfg.pouch_slabs or [],
        sticker_rule=cfg.sticker_rule or {},
        fee_rule=cfg.fee_rule or {},
        note=cfg.note,
    )


def upsert_profit_monthly_overhead(
    db: Session,
    current_user: Employee,
    data: ProfitMonthlyOverheadPayload,
) -> ProfitMonthlyOverheadResponse:
    _ensure_profit_tables(db)

    row = db.query(ProfitMonthlyOverhead).filter(
        ProfitMonthlyOverhead.tenant_id == current_user.tenant_id,
        ProfitMonthlyOverhead.month == data.month,
    ).first()
    if not row:
        row = ProfitMonthlyOverhead(
            tenant_id=current_user.tenant_id,
            month=data.month,
        )
        db.add(row)

    row.ads_cost = data.ads_cost
    row.dispatch_cost = data.dispatch_cost
    row.misc_cost = data.misc_cost
    row.other_fixed_cost = data.other_fixed_cost
    row.shipping_cost = data.shipping_cost
    row.gateway_fee = data.gateway_fee

    db.commit()
    db.refresh(row)
    return ProfitMonthlyOverheadResponse(
        month=row.month,
        ads_cost=_zero(row.ads_cost),
        dispatch_cost=_zero(row.dispatch_cost),
        misc_cost=_zero(row.misc_cost),
        other_fixed_cost=_zero(row.other_fixed_cost),
        shipping_cost=_zero(row.shipping_cost),
        gateway_fee=_zero(row.gateway_fee),
    )


def get_profit_monthly_overheads(
    db: Session,
    current_user: Employee,
    months: int = 12,
) -> list[ProfitMonthlyOverheadResponse]:
    _ensure_profit_tables(db)

    months = max(1, min(months, 36))
    rows = (
        db.query(ProfitMonthlyOverhead)
        .filter(ProfitMonthlyOverhead.tenant_id == current_user.tenant_id)
        .order_by(ProfitMonthlyOverhead.month.desc())
        .limit(months)
        .all()
    )
    return [
        ProfitMonthlyOverheadResponse(
            month=r.month,
            ads_cost=_zero(r.ads_cost),
            dispatch_cost=_zero(r.dispatch_cost),
            misc_cost=_zero(r.misc_cost),
            other_fixed_cost=_zero(r.other_fixed_cost),
            shipping_cost=_zero(r.shipping_cost),
            gateway_fee=_zero(r.gateway_fee),
        )
        for r in rows
    ]


def get_net_pnl_report(
    db: Session,
    current_user: Employee,
    months: int = 12,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> NetPnlReport:
    _ensure_profit_tables(db)

    months = max(1, min(months, 36))
    realized_dt_expr = _realized_order_datetime_expr()
    realized_month_expr = _realized_order_month_expr()

    order_filter = [
        Order.tenant_id == current_user.tenant_id,
        Order.is_active == True,
        Order.status == OrderStatus.delivered,
    ]
    if from_date:
        order_filter.append(
            realized_dt_expr >= datetime.combine(from_date, datetime.min.time())
        )
    if to_date:
        order_filter.append(
            realized_dt_expr < datetime.combine(to_date + timedelta(days=1), datetime.min.time())
        )

    rev_rows = (
        db.query(
            realized_month_expr.label("month"),
            func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
            func.count(Order.id).label("order_count"),
        )
        .filter(*order_filter)
        .group_by(realized_month_expr)
        .order_by(realized_month_expr)
        .all()
    )
    if not from_date:
        rev_rows = rev_rows[-months:]
    months_list = [r.month for r in rev_rows]
    count_map = {r.month: int(r.order_count) for r in rev_rows}

    tax_map: dict[str, Decimal] = {month: Decimal("0") for month in months_list}
    if months_list:
        products = db.query(Product).filter(Product.tenant_id == current_user.tenant_id).all()
        product_lookup = _build_product_lookup(products)
        delivered_orders = (
            db.query(Order)
            .options(selectinload(Order.items))
            .filter(*order_filter)
            .all()
        )
        for order in delivered_orders:
            month = _month_key(_realized_order_datetime_value(order))
            if month not in tax_map:
                continue

            order_tax = Decimal("0")
            matched_any = False
            for item in order.items or []:
                product = _resolve_item_product(item, product_lookup)
                if not product:
                    continue
                matched_any = True
                order_tax += _item_tax_amount(item, product)

            if (not matched_any) and _zero(order.tax_amount) > 0:
                order_tax = _zero(order.tax_amount)

            tax_map[month] = tax_map.get(month, Decimal("0")) + order_tax

    # ── Overhead lookup (manual values per month, set by user in Profit Checker) ─
    overhead_rows = (
        db.query(ProfitMonthlyOverhead)
        .filter(
            ProfitMonthlyOverhead.tenant_id == current_user.tenant_id,
            ProfitMonthlyOverhead.month.in_(months_list) if months_list else False,
        )
        .all()
    ) if months_list else []
    overhead_map: dict[str, ProfitMonthlyOverhead] = {r.month: r for r in overhead_rows}

    # ── Auto product cost (COGS) per month — from OrderProfitPosting.product_cost ──
    cogs_rows = (
        db.query(
            realized_month_expr.label("month"),
            func.coalesce(func.sum(OrderProfitPosting.product_cost), 0).label("product_cost"),
            func.sum(
                case((OrderProfitPosting.product_cost == 0, 1), else_=0)
            ).label("zero_cost_cnt"),
        )
        .join(OrderProfitPosting, OrderProfitPosting.order_id == Order.id)
        .filter(*order_filter)
        .group_by(realized_month_expr)
        .all()
    ) if months_list else []
    cogs_map = {r.month: _zero(r.product_cost) for r in cogs_rows}
    zero_cost_count = int(sum((r.zero_cost_cnt or 0) for r in cogs_rows))

    # ── Packaging from postings (user has not set manually; defaults 0 until packaging cost configured) ──
    pkg_rows = (
        db.query(
            realized_month_expr.label("month"),
            func.coalesce(
                func.sum(OrderProfitPosting.packaging_cost + OrderProfitPosting.courier_material_cost), 0
            ).label("packaging_cost"),
        )
        .join(OrderProfitPosting, OrderProfitPosting.order_id == Order.id)
        .filter(*order_filter)
        .group_by(realized_month_expr)
        .all()
    ) if months_list else []
    pkg_map = {r.month: _zero(r.packaging_cost) for r in pkg_rows}

    # ── RTO: sum(shipping_charge of returned orders in period) + ₹50 per returned order ──
    rto_filter_base = [
        Order.tenant_id == current_user.tenant_id,
        Order.is_active == True,
        Order.status == OrderStatus.returned,
    ]
    if from_date:
        rto_filter_base.append(realized_dt_expr >= datetime.combine(from_date, datetime.min.time()))
    if to_date:
        rto_filter_base.append(realized_dt_expr < datetime.combine(to_date + timedelta(days=1), datetime.min.time()))
    rto_agg_rows = (
        db.query(
            realized_month_expr.label("month"),
            func.count(Order.id).label("cnt"),
            func.coalesce(func.sum(Order.shipping_charge), 0).label("ship"),
        )
        .filter(*rto_filter_base)
        .group_by(realized_month_expr)
        .all()
    )
    rto_map: dict[str, Decimal] = {}
    for rr in rto_agg_rows:
        cnt = int(rr.cnt or 0)
        ship = _zero(rr.ship)
        rto_map[rr.month] = (ship + Decimal("50") * cnt).quantize(Decimal("0.01"))

    # Pipeline: orders placed (created_at) in the filter period that are still NOT delivered
    pipeline_filter = [
        Order.tenant_id == current_user.tenant_id,
        Order.is_active == True,
        Order.status.in_([
            OrderStatus.shipped, OrderStatus.confirmed, OrderStatus.processing,
            OrderStatus.packed, OrderStatus.out_for_delivery, OrderStatus.draft,
        ]),
    ]
    if from_date:
        pipeline_filter.append(Order.created_at >= datetime.combine(from_date, datetime.min.time()))
    if to_date:
        pipeline_filter.append(Order.created_at < datetime.combine(to_date + timedelta(days=1), datetime.min.time()))
    pipeline_row = (
        db.query(
            func.count(Order.id).label("cnt"),
            func.coalesce(func.sum(Order.total_amount), 0).label("rev"),
        )
        .filter(*pipeline_filter)
        .one()
    )
    pipeline_orders  = int(pipeline_row.cnt or 0)
    pipeline_revenue = _zero(pipeline_row.rev)

    # Stale shipped: tenant-wide orders shipped > 30 days and never delivered
    stale_cutoff = datetime.utcnow() - timedelta(days=30)
    stale_row = (
        db.query(
            func.count(Order.id).label("cnt"),
            func.coalesce(func.sum(Order.total_amount), 0).label("rev"),
        )
        .filter(
            Order.tenant_id == current_user.tenant_id,
            Order.is_active == True,
            Order.status == OrderStatus.shipped,
            Order.created_at < stale_cutoff,
        )
        .one()
    )
    stale_shipped_count   = int(stale_row.cnt or 0)
    stale_shipped_revenue = _zero(stale_row.rev)

    # ── Reconciliation table fields ───────────────────────────────────────────

    # Shipped > 7 days without delivery, created within period
    cutoff_7d = datetime.utcnow() - timedelta(days=7)
    shipped7_filter = [
        Order.tenant_id == current_user.tenant_id,
        Order.is_active == True,
        Order.status == OrderStatus.shipped,
        Order.created_at < cutoff_7d,
    ]
    if from_date:
        shipped7_filter.append(Order.created_at >= datetime.combine(from_date, datetime.min.time()))
    if to_date:
        shipped7_filter.append(Order.created_at < datetime.combine(to_date + timedelta(days=1), datetime.min.time()))
    shipped7_row = (
        db.query(
            func.count(Order.id).label("cnt"),
            func.coalesce(func.sum(Order.total_amount), 0).label("rev"),
        )
        .filter(*shipped7_filter)
        .one()
    )
    shipped_7plus_count   = int(shipped7_row.cnt or 0)
    shipped_7plus_revenue = _zero(shipped7_row.rev)

    # Active non-delivered orders created in period with no status update in 2+ days
    cutoff_2d = datetime.utcnow() - timedelta(days=2)
    stale2_filter = [
        Order.tenant_id == current_user.tenant_id,
        Order.is_active == True,
        Order.status.notin_([OrderStatus.delivered, OrderStatus.cancelled, OrderStatus.returned]),
        or_(Order.updated_at == None, Order.updated_at < cutoff_2d),
    ]
    if from_date:
        stale2_filter.append(Order.created_at >= datetime.combine(from_date, datetime.min.time()))
    if to_date:
        stale2_filter.append(Order.created_at < datetime.combine(to_date + timedelta(days=1), datetime.min.time()))
    stale2_row = (
        db.query(
            func.count(Order.id).label("cnt"),
            func.coalesce(func.sum(Order.total_amount), 0).label("rev"),
        )
        .filter(*stale2_filter)
        .one()
    )
    stale_2days_count   = int(stale2_row.cnt or 0)
    stale_2days_revenue = _zero(stale2_row.rev)

    # Returned orders placed in period — reuse rto_filter_base
    returned_row = (
        db.query(
            func.count(Order.id).label("cnt"),
            func.coalesce(func.sum(Order.total_amount), 0).label("rev"),
        )
        .filter(*rto_filter_base)
        .one()
    )
    returned_count   = int(returned_row.cnt or 0)
    returned_revenue = _zero(returned_row.rev)

    # Average delivered order value in period
    avg_row = (
        db.query(
            func.coalesce(func.avg(Order.total_amount), 0).label("avg"),
        )
        .filter(*order_filter)
        .one()
    )
    avg_order_value = _zero(avg_row.avg).quantize(Decimal("0.01"))

    by_month: list[NetPnlByMonth] = []
    tot_rev = Decimal("0")
    tot_tax = Decimal("0")
    tot_var = Decimal("0")
    tot_fix = Decimal("0")
    tot_net = Decimal("0")
    tot_orders = 0

    # Breakdown totals (from manual overhead, for tooltip)
    tot_product_cost  = Decimal("0")
    tot_shipping_cost = Decimal("0")
    tot_packaging_cost = Decimal("0")
    tot_gateway_fee   = Decimal("0")
    tot_rto_expected_loss = Decimal("0")
    tot_ads_allocated = Decimal("0")
    tot_dispatch_allocated = Decimal("0")
    tot_misc_allocated = Decimal("0")
    tot_other_fixed_allocated = Decimal("0")

    for rr in rev_rows:
        month = rr.month
        rev = _zero(rr.revenue)
        order_cnt = count_map.get(month, 0)
        tax = tax_map.get(month, Decimal("0")).quantize(Decimal("0.01"))
        ov = overhead_map.get(month)

        # Auto product cost (sum of WAC/catalog cost per delivered order)
        cogs_m     = cogs_map.get(month, Decimal("0"))

        # Manual cost inputs — 0 if no overhead row saved yet for the month
        ship_m     = _zero(ov.shipping_cost)    if ov else Decimal("0")
        gw_m       = _zero(ov.gateway_fee)      if ov else Decimal("0")
        ads_m      = _zero(ov.ads_cost)         if ov else Decimal("0")
        dispatch_m = _zero(ov.dispatch_cost)    if ov else Decimal("0")
        misc_m     = _zero(ov.misc_cost)        if ov else Decimal("0")
        other_m    = _zero(ov.other_fixed_cost) if ov else Decimal("0")

        packaging_m = pkg_map.get(month, Decimal("0"))
        rto_m       = rto_map.get(month, Decimal("0"))

        var_cost = (cogs_m + ship_m + gw_m + rto_m + packaging_m).quantize(Decimal("0.01"))
        fix_cost = (ads_m + dispatch_m + misc_m + other_m).quantize(Decimal("0.01"))
        total_cost = var_cost + fix_cost
        net = rev - total_cost
        margin = Decimal("0")
        if rev > 0:
            margin = (net / rev * Decimal("100")).quantize(Decimal("0.01"))

        by_month.append(NetPnlByMonth(
            month=month,
            realized_revenue=rev,
            tax_amount=tax,
            variable_cost=var_cost,
            fixed_cost_allocated=fix_cost,
            total_cost=total_cost,
            net_profit=net,
            realized_margin_pct=margin,
        ))

        tot_rev += rev
        tot_tax += tax
        tot_var += var_cost
        tot_fix += fix_cost
        tot_net += net
        tot_orders += order_cnt

        # Accumulate manual breakdown totals
        tot_product_cost       += cogs_m
        tot_shipping_cost      += ship_m
        tot_packaging_cost     += packaging_m
        tot_gateway_fee        += gw_m
        tot_rto_expected_loss  += rto_m
        tot_ads_allocated      += ads_m
        tot_dispatch_allocated += dispatch_m
        tot_misc_allocated     += misc_m
        tot_other_fixed_allocated += other_m

    total_margin = Decimal("0")
    if tot_rev > 0:
        total_margin = (tot_net / tot_rev * Decimal("100")).quantize(Decimal("0.01"))

    return NetPnlReport(
        period_label=f"Last {months} months",
        total_realized_revenue=tot_rev,
        total_tax_amount=tot_tax,
        total_variable_cost=tot_var,
        total_fixed_cost=tot_fix,
        total_net_profit=tot_net,
        realized_margin_pct=total_margin,
        delivered_count=tot_orders,
        total_product_cost=tot_product_cost,
        total_shipping_cost=tot_shipping_cost,
        total_packaging_cost=tot_packaging_cost,
        total_ads_allocated=tot_ads_allocated,
        total_dispatch_allocated=tot_dispatch_allocated,
        total_misc_allocated=tot_misc_allocated,
        total_other_fixed_allocated=tot_other_fixed_allocated,
        total_gateway_fee=tot_gateway_fee,
        total_rto_expected_loss=tot_rto_expected_loss,
        zero_cost_orders=zero_cost_count,
        pipeline_orders=pipeline_orders,
        pipeline_revenue=pipeline_revenue,
        stale_shipped_count=stale_shipped_count,
        stale_shipped_revenue=stale_shipped_revenue,
        shipped_7plus_count=shipped_7plus_count,
        shipped_7plus_revenue=shipped_7plus_revenue,
        stale_2days_count=stale_2days_count,
        stale_2days_revenue=stale_2days_revenue,
        returned_count=returned_count,
        returned_revenue=returned_revenue,
        avg_order_value=avg_order_value,
        by_month=by_month,
    )


# ─────────────────────────────────────────────────────────────
# Inventory Reconciliation
# ─────────────────────────────────────────────────────────────

def get_inventory_reconciliation(
    db: Session,
    current_user: Employee,
) -> ReconciliationReport:
    """
    Compare InventorySummary.current_stock vs SUM(movements) per product.
    Highlights mismatches and negative-stock products.
    """
    from app.models.inventory import InventoryMovement, InventorySummary, MovementType

    # Fetch all summaries for this tenant
    summaries = (
        db.query(InventorySummary, Product)
        .join(Product, Product.id == InventorySummary.product_id)
        .filter(InventorySummary.tenant_id == current_user.tenant_id)
        .all()
    )

    # Build ledger sums per product
    from sqlalchemy import text as sa_text
    ledger_rows = (
        db.query(
            InventoryMovement.product_id,
            func.sum(InventoryMovement.quantity_change).label("ledger_sum"),
        )
        .filter(InventoryMovement.tenant_id == current_user.tenant_id)
        .group_by(InventoryMovement.product_id)
        .all()
    )
    ledger_map: dict = {str(r.product_id): Decimal(str(r.ledger_sum or 0)) for r in ledger_rows}

    results: list[ReconciliationRow] = []
    mismatch_count = 0
    negative_count = 0

    for summary, product in summaries:
        s_stock = Decimal(str(summary.current_stock or 0))
        l_sum = ledger_map.get(str(summary.product_id), Decimal("0"))
        drift = (s_stock - l_sum).quantize(Decimal("0.001"))
        is_negative = s_stock < Decimal("0")
        is_mismatch = abs(drift) > Decimal("0.001")

        status = "ok"
        if is_negative and is_mismatch:
            status = "negative_mismatch"
            negative_count += 1
            mismatch_count += 1
        elif is_negative:
            status = "negative"
            negative_count += 1
        elif is_mismatch:
            status = "mismatch"
            mismatch_count += 1

        results.append(ReconciliationRow(
            product_id=str(product.id),
            product_code=product.sku or "",
            product_name=product.name or "",
            summary_stock=s_stock,
            ledger_sum=l_sum,
            drift=drift,
            is_negative=is_negative,
            status=status,
        ))

    # Sort: negative_mismatch first, then mismatch, then negative, then ok
    _order = {"negative_mismatch": 0, "mismatch": 1, "negative": 2, "ok": 3}
    results.sort(key=lambda r: _order.get(r.status, 9))

    healthy_count = len(results) - mismatch_count - negative_count
    # avoid double-counting negative_mismatch in healthy
    healthy_count = sum(1 for r in results if r.status == "ok")

    return ReconciliationReport(
        total_products=len(results),
        mismatch_count=mismatch_count,
        negative_count=negative_count,
        healthy_count=healthy_count,
        results=results,
    )


# ─────────────────────────────────────────────────────────────
# WhatsApp Daily Summary
# ─────────────────────────────────────────────────────────────

async def send_whatsapp_daily_summary(
    db: Session,
    current_user: Employee,
    data: DailySummaryRequest,
) -> DailySummaryResponse:
    """
    Compose and send a WhatsApp daily summary message:
      - Critical / warning margin SKUs (from pricing suggestions)
      - Negative or zero stock products
      - Top 3 VIP customers and top 3 LOSS customers
    Sends via the tenant's configured WA provider.
    """
    from app.modules.wa_engine.service import get_or_create_settings, _provider
    from app.core.whatsapp import normalize_phone_e164

    # ── 1. Gather pricing alerts ──────────────────────────────
    pricing_report = get_pricing_suggestions(db, current_user, limit=50)
    critical_skus = [r for r in pricing_report.results if r.severity in ("critical", "warning")][:5]

    # ── 2. Gather stock alerts ────────────────────────────────
    recon = get_inventory_reconciliation(db, current_user)
    neg_stock = [r for r in recon.results if r.is_negative][:5]

    # ── 3. Gather customer highlights ────────────────────────
    ltv_report = get_customer_profit_ltv(db, current_user, limit=50)
    top_vip = [r for r in ltv_report.results if r.segment == "VIP"][:3]
    top_loss = [r for r in ltv_report.results if r.segment == "LOSS"][:3]

    # ── 4. Compose message ────────────────────────────────────
    today = datetime.now(timezone.utc).strftime("%d %b %Y")
    lines = [f"*Daily Summary — {today}*\n"]

    if critical_skus:
        lines.append("*⚠️ Margin Alerts:*")
        for s in critical_skus:
            icon = "🔴" if s.severity == "critical" else "🟡"
            lines.append(f"{icon} {s.name} — margin {s.current_margin_pct:.1f}% (suggested ₹{s.suggested_price:.0f})")
    else:
        lines.append("✅ No margin alerts")

    lines.append("")
    if neg_stock:
        lines.append("*📦 Negative Stock:*")
        for s in neg_stock:
            lines.append(f"🔴 {s.product_name} ({s.product_code}) — {s.summary_stock}")
    else:
        lines.append("✅ No negative stock")

    lines.append("")
    if top_vip:
        lines.append("*🌟 Top VIP Customers:*")
        for c in top_vip:
            lines.append(f"• {c.name} — ₹{c.total_profit:.0f} profit ({c.total_orders} orders)")

    if top_loss:
        lines.append("\n*🔻 Loss Customers:*")
        for c in top_loss:
            lines.append(f"• {c.name} — ₹{c.total_profit:.0f} ({c.total_orders} orders)")

    message = "\n".join(lines)

    # ── 5. Resolve recipient phone ────────────────────────────
    wa_settings = get_or_create_settings(db, current_user.tenant_id)
    to_phone = data.to_phone or wa_settings.phone_number or ""
    to_e164 = normalize_phone_e164(to_phone)

    if not to_e164:
        return DailySummaryResponse(
            sent=False,
            to=to_phone,
            message=message,
            error="No recipient phone configured. Set to_phone in request or configure WA settings phone_number.",
        )

    # ── 6. Send ───────────────────────────────────────────────
    if not wa_settings.is_active:
        return DailySummaryResponse(
            sent=False,
            to=to_e164,
            message=message,
            error="WhatsApp provider is not active for this tenant.",
        )

    try:
        provider = _provider(wa_settings)
        result = await provider.send_text(phone=to_e164, text=message)
        return DailySummaryResponse(
            sent=result.success,
            to=to_e164,
            message=message,
            error=result.error if not result.success else None,
        )
    except Exception as exc:
        return DailySummaryResponse(
            sent=False,
            to=to_e164,
            message=message,
            error=str(exc),
        )


def recalculate_profit_postings(db: Session, current_user, from_month: str, to_month: str):
    """
    Recalculate profit postings for all orders in the given month range.
    This is used when products are added/updated and need to be backfilled into
    existing orders that reference them.
    
    Returns RecalculateResponse with:
    - success: bool
    - processed: int (number of orders recalculated)
    - message: str
    """
    from datetime import datetime, timezone
    from app.modules.profit_engine.service import upsert_order_profit_posting
    from app.modules.reporting.schemas import RecalculateResponse
    
    tenant_id = current_user.tenant_id
    
    # Parse months to datetime range
    def _month_start(month_str):
        try:
            return datetime.strptime(month_str, '%Y-%m').replace(tzinfo=timezone.utc)
        except:
            return None
    
    def _next_month(dt):
        if dt.month == 12:
            return datetime(dt.year + 1, 1, 1, tzinfo=timezone.utc)
        return datetime(dt.year, dt.month + 1, 1, tzinfo=timezone.utc)
    
    start = _month_start(from_month)
    end_month = _month_start(to_month)
    
    if not start or not end_month:
        return RecalculateResponse(
            success=False,
            processed=0,
            message='Invalid date format. Use YYYY-MM.'
        )
    
    if end_month < start:
        return RecalculateResponse(
            success=False,
            processed=0,
            message='to_month must be same as or after from_month'
        )
    
    start_month_key = start.strftime('%Y-%m')
    end_month_key = end_month.strftime('%Y-%m')
    posting_month_expr = func.to_char(func.coalesce(Order.delivered_at, Order.created_at), "YYYY-MM")

    # Query orders in posting-month range (same month key used by OrderProfitPosting.month)
    orders = db.query(Order).filter(
        Order.tenant_id == tenant_id,
        Order.is_active == True,
        Order.status.notin_([OrderStatus.cancelled]),
        posting_month_expr >= start_month_key,
        posting_month_expr <= end_month_key,
    ).all()
    
    if not orders:
        return RecalculateResponse(
            success=True,
            processed=0,
            message=f'No orders found for {from_month} to {to_month}'
        )
    
    # Recalculate each order
    processed = 0
    try:
        for order in orders:
            upsert_order_profit_posting(db, tenant_id=tenant_id, order_id=order.id)
            processed += 1
            if processed % 50 == 0:
                db.commit()
        
        db.commit()
        return RecalculateResponse(
            success=True,
            processed=processed,
            message=f'Successfully recalculated {processed} order(s)'
        )
    except Exception as exc:
        db.rollback()
        return RecalculateResponse(
            success=False,
            processed=processed,
            message=f'Error during recalculation: {str(exc)}'
        )
