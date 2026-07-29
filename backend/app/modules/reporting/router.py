"""
Reporting Router
-----------------
6 read-only analytics endpoints.
Prefix: /api/reports
All roles can view — no mutations here.
Supports optional date-range and status filters.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.auth.tenant import get_current_tenant_user, require_roles
from app.models.employee import RoleEnum
from app.modules.reporting.schemas import (
    DashboardStats,
    RevenueReport,
    EmployeeReport,
    LeadFunnelReport,
    TopCustomersReport,
    CustomerProfitLtvReport,
    ProductReport,
    PricingSuggestionReport,
    StateSalesReport,
    ProductUsageInsight,
    ForecastReport,
    PurchaseRecommendationReport,
    ProfitCostPreviewRequest,
    ProfitCostPreviewResponse,
    ProfitCostConfigPayload,
    ProfitCostConfigResponse,
    ProfitMonthlyOverheadPayload,
    ProfitMonthlyOverheadResponse,
    ProfitMonthlyPlannerPayload,
    ProfitMonthlyPlannerResponse,
    NetPnlReport,
    ReconciliationReport,
    DailySummaryRequest,
    DailySummaryResponse,
    RecalculateRequest,
    RecalculateResponse,
)
from app.modules.reporting import service

router = APIRouter(prefix="/api/reports", tags=["Reporting"])

# All roles can view reports
_all_roles = require_roles(
    RoleEnum.admin, RoleEnum.operations, RoleEnum.sales,
    RoleEnum.support, RoleEnum.marketing,
)

# Only admin + operations can see employee breakdown
_mgmt = require_roles(RoleEnum.admin, RoleEnum.operations)


# ─────────────────────────────────────────────────────────────
# GET /api/reports/dashboard
# ─────────────────────────────────────────────────────────────
@router.get("/dashboard", response_model=DashboardStats)
def dashboard(
    from_date: Optional[date] = Query(None, alias="from", description="Start date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, alias="to", description="End date (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="Filter by order status"),
    state: Optional[str] = Query(None, description="Filter by delivery/customer state"),
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    """
    Single-call summary: all KPIs for the tenant dashboard.
    Leads | Customers | Orders | Revenue | Products.
    Supports optional date-range and status filters.
    """
    return service.get_dashboard(
        db,
        current_user,
        from_date=from_date,
        to_date=to_date,
        status=status,
        state=state,
    )


# ─────────────────────────────────────────────────────────────
# GET /api/reports/revenue
# ─────────────────────────────────────────────────────────────
@router.get("/revenue", response_model=RevenueReport)
def revenue_report(
    months: int = Query(12, ge=1, le=36, description="How many months of history"),
    from_date: Optional[date] = Query(None, alias="from", description="Start date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, alias="to", description="End date (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="Filter by order status"),
    state: Optional[str] = Query(None, description="Filter by delivery/customer state"),
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    """
    Monthly revenue breakdown — order count, revenue, outstanding per month.
    Supports optional date-range filters.
    """
    return service.get_revenue_report(
        db,
        current_user,
        months=months,
        from_date=from_date,
        to_date=to_date,
        status=status,
        state=state,
    )


# ─────────────────────────────────────────────────────────────
# GET /api/reports/employees
# ─────────────────────────────────────────────────────────────
@router.get("/employees", response_model=EmployeeReport)
def employee_report(
    db: Session = Depends(get_db),
    current_user=Depends(_mgmt),
):
    """
    Per-employee breakdown: leads created/won, customers, orders, revenue, conversion %.
    Admin + operations only.
    """
    return service.get_employee_report(db, current_user)


# ─────────────────────────────────────────────────────────────
# GET /api/reports/leads/funnel
# ─────────────────────────────────────────────────────────────
@router.get("/leads/funnel", response_model=LeadFunnelReport)
def lead_funnel(
    from_date: Optional[date] = Query(None, alias="from", description="Start date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, alias="to", description="End date (YYYY-MM-DD)"),
    state: Optional[str] = Query(None, description="Filter by lead state"),
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    """
    Lead pipeline funnel: count + % at each stage.
    Also breaks down by source and priority.
    """
    return service.get_lead_funnel(
        db,
        current_user,
        from_date=from_date,
        to_date=to_date,
        state=state,
    )


# ─────────────────────────────────────────────────────────────
# GET /api/reports/customers/top
# ─────────────────────────────────────────────────────────────
@router.get("/customers/top", response_model=TopCustomersReport)
def top_customers(
    limit: int = Query(10, ge=1, le=50),
    from_date: Optional[date] = Query(None, alias="from", description="Start date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, alias="to", description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    """
    Top customers by total delivered order value.
    Supports optional date-range filters.
    """
    return service.get_top_customers(db, current_user, limit=limit, from_date=from_date, to_date=to_date)


# ─────────────────────────────────────────────────────────────
# GET /api/reports/customers/profit-ltv
# ─────────────────────────────────────────────────────────────
@router.get("/customers/profit-ltv", response_model=CustomerProfitLtvReport)
def customers_profit_ltv(
    limit: int = Query(50, ge=1, le=500),
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    """
    Customer-level profitability (LTV as total profit) from delivered orders.
    Supports optional from/to date filters (YYYY-MM-DD).
    """
    return service.get_customer_profit_ltv(db, current_user, limit=limit, from_date=from_date, to_date=to_date)


# ─────────────────────────────────────────────────────────────
# GET /api/reports/products
# ─────────────────────────────────────────────────────────────
@router.get("/products", response_model=ProductReport)
def product_report(
    from_date: Optional[date] = Query(None, alias="from", description="Start date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, alias="to", description="End date (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="Filter by order status"),
    state: Optional[str] = Query(None, description="Filter by delivery/customer state"),
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    """
    Product catalog performance: times ordered, units sold, revenue per product.
    Supports optional date-range filters.
    """
    return service.get_product_report(
        db,
        current_user,
        from_date=from_date,
        to_date=to_date,
        status=status,
        state=state,
    )


# ─────────────────────────────────────────────────────────────
# GET /api/reports/profit/pricing-suggestions
# ─────────────────────────────────────────────────────────────
@router.get("/profit/pricing-suggestions", response_model=PricingSuggestionReport)
def pricing_suggestions(
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    """
    SKU-level pricing suggestions using current cost source and configured target margin.
    """
    return service.get_pricing_suggestions(db, current_user, limit=limit)


# ─────────────────────────────────────────────────────────────
# GET /api/reports/sales/state
# ─────────────────────────────────────────────────────────────
@router.get("/sales/state", response_model=StateSalesReport)
def sales_by_state(
    limit: int = Query(20, ge=1, le=100),
    from_date: Optional[date] = Query(None, alias="from", description="Start date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, alias="to", description="End date (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="Filter by order status"),
    state: Optional[str] = Query(None, description="Filter by delivery/customer state"),
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    """
    State-wise sales performance with orders, units, revenue and outstanding.
    Supports optional date-range filters.
    """
    return service.get_state_sales_report(
        db,
        current_user,
        limit=limit,
        from_date=from_date,
        to_date=to_date,
        status=status,
        state=state,
    )


# ─────────────────────────────────────────────────────────────
# GET /api/reports/products/usage
# ─────────────────────────────────────────────────────────────
@router.get("/products/usage", response_model=ProductUsageInsight)
def product_usage_insights(
    months: int = Query(6, ge=1, le=24, description="How many months for trend"),
    from_date: Optional[date] = Query(None, alias="from", description="Start date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, alias="to", description="End date (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="Filter by order status"),
    state: Optional[str] = Query(None, description="Filter by delivery/customer state"),
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    """
    Product usage trend and top products sold.
    Supports optional date-range filters.
    """
    return service.get_product_usage_insight(
        db,
        current_user,
        months=months,
        from_date=from_date,
        to_date=to_date,
        status=status,
        state=state,
    )


# ─────────────────────────────────────────────────────────────
# GET /api/reports/forecast
# ─────────────────────────────────────────────────────────────
@router.get("/forecast", response_model=ForecastReport)
def forecast_report(
    months: int = Query(6, ge=3, le=24, description="History window for trend forecast"),
    horizon: int = Query(3, ge=1, le=6, description="Forecast horizon in months"),
    from_date: Optional[date] = Query(None, alias="from", description="Start date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, alias="to", description="End date (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="Filter by order status"),
    state: Optional[str] = Query(None, description="Filter by delivery/customer state"),
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    """
    Revenue and top-product demand forecast using trend projection.
    """
    return service.get_forecast_report(
        db,
        current_user,
        months=months,
        horizon=horizon,
        from_date=from_date,
        to_date=to_date,
        status=status,
        state=state,
    )


# ─────────────────────────────────────────────────────────────
# GET /api/reports/purchase/recommendations
# ─────────────────────────────────────────────────────────────
@router.get("/purchase/recommendations", response_model=PurchaseRecommendationReport)
def purchase_recommendations(
    horizon_days: int = Query(30, ge=1, le=90, description="Purchase planning horizon"),
    safety_days: int = Query(10, ge=0, le=60, description="Safety buffer days"),
    lookback_days: int = Query(30, ge=7, le=120, description="Demand lookback period"),
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    """
    SKU-wise purchase recommendation based on recent usage and current stock.
    """
    return service.get_purchase_recommendations(
        db,
        current_user,
        horizon_days=horizon_days,
        safety_days=safety_days,
        lookback_days=lookback_days,
    )


# ─────────────────────────────────────────────────────────────
# POST /api/reports/profit/cost-preview
# ─────────────────────────────────────────────────────────────
@router.post("/profit/cost-preview", response_model=ProfitCostPreviewResponse)
def profit_cost_preview(
    data: ProfitCostPreviewRequest,
    current_user=Depends(_all_roles),
):
    """
    Dynamic per-order profit calculator using UI-provided cost inputs.
    """
    _ = current_user  # role guard only
    return service.get_profit_cost_preview(data)


# ─────────────────────────────────────────────────────────────
# GET/PATCH /api/reports/profit/config
# ─────────────────────────────────────────────────────────────
@router.get("/profit/config", response_model=ProfitCostConfigResponse)
def get_profit_config(
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    return service.get_profit_cost_config(db, current_user)


@router.patch("/profit/config", response_model=ProfitCostConfigResponse)
def update_profit_config(
    data: ProfitCostConfigPayload,
    db: Session = Depends(get_db),
    current_user=Depends(_mgmt),
):
    return service.upsert_profit_cost_config(db, current_user, data)


# ─────────────────────────────────────────────────────────────
# GET/PUT /api/reports/profit/monthly-overheads
# ─────────────────────────────────────────────────────────────
@router.get("/profit/monthly-overheads", response_model=list[ProfitMonthlyOverheadResponse])
def list_profit_monthly_overheads(
    months: int = Query(12, ge=1, le=36),
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    return service.get_profit_monthly_overheads(db, current_user, months=months)


@router.put("/profit/monthly-overheads", response_model=ProfitMonthlyOverheadResponse)
def upsert_profit_monthly_overhead(
    data: ProfitMonthlyOverheadPayload,
    db: Session = Depends(get_db),
    current_user=Depends(_mgmt),
):
    return service.upsert_profit_monthly_overhead(db, current_user, data)


# ─────────────────────────────────────────────────────────────
# GET/PUT /api/reports/profit/monthly-planner
# ─────────────────────────────────────────────────────────────
@router.get("/profit/monthly-planner", response_model=ProfitMonthlyPlannerResponse)
def get_profit_monthly_planner(
    month: str = Query(..., description="Month in YYYY-MM"),
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    return service.get_profit_monthly_planner(db, current_user, month=month)


@router.put("/profit/monthly-planner", response_model=ProfitMonthlyPlannerResponse)
def upsert_profit_monthly_planner(
    data: ProfitMonthlyPlannerPayload,
    db: Session = Depends(get_db),
    current_user=Depends(_mgmt),
):
    return service.upsert_profit_monthly_planner(db, current_user, data)


# ─────────────────────────────────────────────────────────────
# GET /api/reports/profit/net-monthly
# ─────────────────────────────────────────────────────────────
@router.get("/profit/net-monthly", response_model=NetPnlReport)
def net_monthly_pnl(
    months: int = Query(12, ge=1, le=36),
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    db: Session = Depends(get_db),
    current_user=Depends(_all_roles),
):
    """
    Monthly realized net P&L with fixed + variable allocations and margin trend.
    Supports optional from/to date filters (YYYY-MM-DD).
    """
    return service.get_net_pnl_report(db, current_user, months=months, from_date=from_date, to_date=to_date)


# ─────────────────────────────────────────────────────────────
# POST /api/reports/profit/recalculate
# ─────────────────────────────────────────────────────────────
@router.post("/profit/recalculate", response_model=RecalculateResponse)
def recalculate_profit_postings(
    data: RecalculateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(_mgmt),
):
    """
    Recalculate profit postings for all orders in a date range.
    Requires management role. Used to backfill costs when products are added/updated.
    """
    return service.recalculate_profit_postings(db, current_user, data.from_month, data.to_month)
