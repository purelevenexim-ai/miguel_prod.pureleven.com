"""
Reporting Schemas
------------------
Response shapes for all reporting/analytics endpoints.
No ORM models — reporting is pure aggregated SQL.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


# ─────────────────────────────────────────────────────────────
# Shared
# ─────────────────────────────────────────────────────────────

class PeriodParam(BaseModel):
    """Query param helper — not used as response."""
    period: str = "all"   # all | today | week | month | quarter | year


# ─────────────────────────────────────────────────────────────
# Dashboard Summary
# ─────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    # Leads
    total_leads:                int
    leads_this_month:           int
    leads_won:                  int
    leads_lost:                 int
    lead_conversion_rate:       float       # won / total * 100

    # Customers
    total_customers:            int
    new_customers_this_month:   int
    active_customers:           int

    # Orders
    total_orders:               int
    orders_this_month:          int
    orders_delivered:           int
    orders_pending:             int         # confirmed + processing + packed + shipped

    # Revenue
    total_revenue:              Decimal     # sum of all non-cancelled order values (order book)
    revenue_this_month:         Decimal
    delivered_revenue:          Decimal = Decimal("0")  # sum of delivered orders only (realised)
    collected_revenue:          Decimal = Decimal("0")  # actual amount_paid across operational orders
    total_outstanding:          Decimal     # amount_due across open orders
    total_shipping_cost:        Decimal = Decimal("0")  # sum of order.actual_shipping_cost

    # Products
    total_products:             int
    active_products:            int


# ─────────────────────────────────────────────────────────────
# Revenue Report
# ─────────────────────────────────────────────────────────────

class RevenueByMonth(BaseModel):
    month:          str          # "2026-01"
    order_count:    int
    revenue:        Decimal
    collected:      Decimal = Decimal("0")
    outstanding:    Decimal


class RevenueReport(BaseModel):
    period_label:   str
    total_revenue:  Decimal
    total_orders:   int
    by_month:       list[RevenueByMonth]


# ─────────────────────────────────────────────────────────────
# Employee Performance
# ─────────────────────────────────────────────────────────────

class EmployeePerformance(BaseModel):
    employee_id:        str
    employee_name:      str
    role:               str
    leads_created:      int
    leads_won:          int
    customers_created:  int
    orders_created:     int
    revenue_generated:  Decimal
    conversion_rate:    float   # leads_won / leads_created * 100


class EmployeeReport(BaseModel):
    total_employees:    int
    results:            list[EmployeePerformance]


# ─────────────────────────────────────────────────────────────
# Lead Funnel
# ─────────────────────────────────────────────────────────────

class LeadFunnelStage(BaseModel):
    stage:  str
    count:  int
    pct:    float   # % of total leads


class LeadFunnelReport(BaseModel):
    total_leads:    int
    by_source:      dict[str, int]
    by_priority:    dict[str, int]
    funnel:         list[LeadFunnelStage]


# ─────────────────────────────────────────────────────────────
# Top Customers
# ─────────────────────────────────────────────────────────────

class TopCustomer(BaseModel):
    customer_id:    str
    name:           str
    phone:          str
    city:           Optional[str]
    order_count:    int
    total_spent:    Decimal


class TopCustomersReport(BaseModel):
    results: list[TopCustomer]


class CustomerProfitLtvRow(BaseModel):
    customer_id:      str
    name:             str
    phone:            str
    city:             Optional[str]
    total_orders:     int
    total_revenue:    Decimal
    total_cost:       Decimal
    total_profit:     Decimal
    avg_order_value:  Decimal
    ltv:              Decimal
    segment:          str


class CustomerProfitLtvReport(BaseModel):
    total_customers:  int
    vip_customers:    int
    loss_customers:   int
    results:          list[CustomerProfitLtvRow]


# ─────────────────────────────────────────────────────────────
# Product Performance
# ─────────────────────────────────────────────────────────────

class ProductPerformance(BaseModel):
    product_id:     str
    product_code:   str
    name:           str
    category:       Optional[str]
    unit_price:     Decimal
    times_ordered:  int
    units_sold:     Decimal
    revenue:        Decimal
    cost_price:     Optional[Decimal] = None
    total_cost:     Optional[Decimal] = None
    gross_profit:   Optional[Decimal] = None
    margin_pct:     Optional[float] = None
    cost_source:    Optional[str] = None


class ProductReport(BaseModel):
    total_products: int
    results:        list[ProductPerformance]


class PricingSuggestionRow(BaseModel):
    product_id:            str
    product_code:          str
    name:                  str
    unit_price:            Decimal
    unit_cost:             Optional[Decimal] = None
    current_margin_pct:    Optional[Decimal] = None
    target_margin_pct:     Decimal
    low_margin_threshold:  Decimal
    suggested_price:       Optional[Decimal] = None
    suggested_delta:       Optional[Decimal] = None
    severity:              str
    cost_source:           Optional[str] = None


class PricingSuggestionReport(BaseModel):
    total_products:        int
    low_margin_products:   int
    negative_margin_products: int
    results:               list[PricingSuggestionRow]


# ─────────────────────────────────────────────────────────────
# State Sales
# ─────────────────────────────────────────────────────────────

class StateSalesRow(BaseModel):
    state:           str
    order_count:     int
    units_sold:      Decimal
    revenue:         Decimal
    outstanding:     Decimal
    avg_order_value: Decimal


class StateSalesReport(BaseModel):
    results: list[StateSalesRow]


# ─────────────────────────────────────────────────────────────
# Product Usage Insights
# ─────────────────────────────────────────────────────────────

class ProductUsageTrendPoint(BaseModel):
    month:                str
    distinct_products:    int
    units_sold:           Decimal


class ProductUsageInsight(BaseModel):
    total_products_used:  int
    total_units_sold:     Decimal
    top_products_sold:    list[ProductPerformance]
    usage_trend:          list[ProductUsageTrendPoint]


# ─────────────────────────────────────────────────────────────
# Forecast
# ─────────────────────────────────────────────────────────────

class RevenueForecastPoint(BaseModel):
    month:            str
    forecast_revenue: Decimal


class ProductDemandForecastPoint(BaseModel):
    month:          str
    forecast_units: Decimal


class ProductDemandForecast(BaseModel):
    product_id:   str
    name:         str
    trend:        list[ProductDemandForecastPoint]


class ForecastReport(BaseModel):
    revenue_forecast:        list[RevenueForecastPoint]
    product_demand_forecast: list[ProductDemandForecast]


# ─────────────────────────────────────────────────────────────
# Purchase Recommendation
# ─────────────────────────────────────────────────────────────

class PurchaseRecommendationRow(BaseModel):
    product_id:              str
    product_code:            str
    name:                    str
    unit:                    str
    stock_on_hand:           Decimal
    daily_usage:             Decimal
    days_remaining:          Optional[Decimal]
    target_stock:            Decimal
    recommended_purchase:    Decimal
    current_unit_cost:       Optional[Decimal] = None
    last_30d_avg_cost:       Optional[Decimal] = None
    price_signal:            Optional[str] = None


class PurchaseRecommendationReport(BaseModel):
    horizon_days:            int
    safety_days:             int
    lookback_days:           int
    results:                 list[PurchaseRecommendationRow]


# ─────────────────────────────────────────────────────────────
# Profit Cost Preview (Dynamic UI inputs)
# ─────────────────────────────────────────────────────────────

class ProfitCostPreviewRequest(BaseModel):
    selling_price:                 Decimal
    product_cost:                  Decimal = Decimal("0")
    total_items:                   int = 1
    total_weight_grams:            Decimal = Decimal("0")

    box_small_cost:                Decimal = Decimal("10")
    box_large_cost:                Decimal = Decimal("24")
    box_large_min_items:           int = 3
    box_large_min_weight_grams:    Decimal = Decimal("500")

    pouch_cost_total:              Decimal = Decimal("0")
    sticker_cost_total:            Decimal = Decimal("0")
    courier_material_cost:         Decimal = Decimal("0")
    shipping_cost:                 Decimal = Decimal("0")
    ads_allocated:                 Decimal = Decimal("0")
    dispatch_cost:                 Decimal = Decimal("0")
    misc_cost:                     Decimal = Decimal("0")
    gateway_fee_pct:               Decimal = Decimal("0")
    rto_loss_pct:                  Decimal = Decimal("0")
    platform_fee_pct:              Decimal = Decimal("0")
    packaging_extra_per_order:     Decimal = Decimal("0")


class ProfitCostPreviewResponse(BaseModel):
    box_cost:                      Decimal
    packaging_cost:                Decimal
    gateway_fee:                   Decimal
    rto_expected_loss:             Decimal
    platform_fee:                  Decimal
    total_cost:                    Decimal
    profit:                        Decimal
    margin_pct:                    Decimal


# ─────────────────────────────────────────────────────────────
# Persisted Profit Config + Net P&L
# ─────────────────────────────────────────────────────────────

class ProfitCostConfigPayload(BaseModel):
    box_rule:      dict
    pouch_slabs:   list[dict]
    sticker_rule:  dict
    fee_rule:      dict
    note:          Optional[str] = None


class ProfitCostConfigResponse(BaseModel):
    tenant_id:     str
    box_rule:      dict
    pouch_slabs:   list[dict]
    sticker_rule:  dict
    fee_rule:      dict
    note:          Optional[str] = None


class ProfitMonthlyOverheadPayload(BaseModel):
    month:             str
    ads_cost:          Decimal = Decimal("0")
    dispatch_cost:     Decimal = Decimal("0")
    misc_cost:         Decimal = Decimal("0")
    other_fixed_cost:  Decimal = Decimal("0")
    # Manual cost inputs
    shipping_cost:     Decimal = Decimal("0")
    gateway_fee:       Decimal = Decimal("0")


class ProfitMonthlyOverheadResponse(BaseModel):
    month:             str
    ads_cost:          Decimal
    dispatch_cost:     Decimal
    misc_cost:         Decimal
    other_fixed_cost:  Decimal
    shipping_cost:     Decimal = Decimal("0")
    gateway_fee:       Decimal = Decimal("0")


class ProfitMonthlyPlannerPayload(BaseModel):
    month:                 str
    revenue:               Decimal = Decimal("0")
    orders:                Decimal = Decimal("0")
    cogs:                  Decimal = Decimal("0")
    returns_loss:          Decimal = Decimal("0")

    small_box_cost:        Decimal = Decimal("0")
    small_box_qty:         Decimal = Decimal("0")
    large_box_cost:        Decimal = Decimal("0")
    large_box_qty:         Decimal = Decimal("0")

    pouch_250_cost:        Decimal = Decimal("0")
    pouch_250_qty:         Decimal = Decimal("0")
    pouch_500_cost:        Decimal = Decimal("0")
    pouch_500_qty:         Decimal = Decimal("0")
    pouch_1kg_cost:        Decimal = Decimal("0")
    pouch_1kg_qty:         Decimal = Decimal("0")

    sticker_total:         Decimal = Decimal("0")
    indian_post_total:     Decimal = Decimal("0")
    delivery_convenience:  Decimal = Decimal("0")
    platform_gateway:      Decimal = Decimal("0")

    ads_monthly:           Decimal = Decimal("0")
    salary_monthly:        Decimal = Decimal("0")
    rent_utilities:        Decimal = Decimal("0")
    software_tools:        Decimal = Decimal("0")
    misc_monthly:          Decimal = Decimal("0")
    other_fixed:           Decimal = Decimal("0")


class ProfitMonthlyPlannerResponse(BaseModel):
    month:                 str
    revenue:               Decimal
    orders:                Decimal
    cogs:                  Decimal
    returns_loss:          Decimal

    small_box_cost:        Decimal
    small_box_qty:         Decimal
    large_box_cost:        Decimal
    large_box_qty:         Decimal

    pouch_250_cost:        Decimal
    pouch_250_qty:         Decimal
    pouch_500_cost:        Decimal
    pouch_500_qty:         Decimal
    pouch_1kg_cost:        Decimal
    pouch_1kg_qty:         Decimal

    sticker_total:         Decimal
    indian_post_total:     Decimal
    delivery_convenience:  Decimal
    platform_gateway:      Decimal

    ads_monthly:           Decimal
    salary_monthly:        Decimal
    rent_utilities:        Decimal
    software_tools:        Decimal
    misc_monthly:          Decimal
    other_fixed:           Decimal


class NetPnlByMonth(BaseModel):
    month:                     str
    realized_revenue:          Decimal
    tax_amount:                Decimal
    variable_cost:             Decimal
    fixed_cost_allocated:      Decimal
    total_cost:                Decimal
    net_profit:                Decimal
    realized_margin_pct:       Decimal


class NetPnlReport(BaseModel):
    period_label:              str
    total_realized_revenue:    Decimal
    total_tax_amount:          Decimal
    total_variable_cost:       Decimal
    total_fixed_cost:          Decimal
    total_net_profit:          Decimal
    realized_margin_pct:       Decimal
    delivered_count:           int
    # cost breakdown for tooltip
    total_product_cost:        Decimal
    total_shipping_cost:       Decimal
    total_packaging_cost:      Decimal
    total_ads_allocated:       Decimal
    total_dispatch_allocated:  Decimal
    total_misc_allocated:      Decimal
    total_other_fixed_allocated: Decimal
    total_gateway_fee:         Decimal
    total_rto_expected_loss:   Decimal
    # data quality
    zero_cost_orders:          int
    # pipeline: orders placed in period, not yet delivered
    pipeline_orders:           int
    pipeline_revenue:          Decimal
    # stale shipped: tenant-wide orders shipped > 30 days, never delivered
    stale_shipped_count:       int
    stale_shipped_revenue:     Decimal
    # reconciliation table
    shipped_7plus_count:       int      # placed in period, status=shipped, >7 days old
    shipped_7plus_revenue:     Decimal
    stale_2days_count:         int      # active non-delivered, not updated in 2+ days (period)
    stale_2days_revenue:       Decimal
    returned_count:            int      # returned orders placed in period
    returned_revenue:          Decimal
    avg_order_value:           Decimal  # avg total_amount of delivered orders in period
    by_month:                  list[NetPnlByMonth]


# ─────────────────────────────────────────────────────────────
# Inventory Reconciliation
# ─────────────────────────────────────────────────────────────

class ReconciliationRow(BaseModel):
    product_id:     str
    product_code:   str
    product_name:   str
    summary_stock:  Decimal   # what InventorySummary says
    ledger_sum:     Decimal   # sum of all movement rows
    drift:          Decimal   # summary_stock - ledger_sum
    is_negative:    bool      # summary_stock < 0
    status:         str       # "mismatch" | "negative" | "ok"


class ReconciliationReport(BaseModel):
    total_products:     int
    mismatch_count:     int
    negative_count:     int
    healthy_count:      int
    results:            list[ReconciliationRow]


# ─────────────────────────────────────────────────────────────
# WhatsApp Daily Summary
# ─────────────────────────────────────────────────────────────

class DailySummaryRequest(BaseModel):
    to_phone: Optional[str] = None   # override; falls back to WA settings phone_number


class DailySummaryResponse(BaseModel):
    sent:    bool
    to:      str
    message: str
    error:   Optional[str] = None


# ─────────────────────────────────────────────────────────────
# Profit Posting Recalculation
# ─────────────────────────────────────────────────────────────

class RecalculateRequest(BaseModel):
    from_month:  str  # YYYY-MM format
    to_month:    str  # YYYY-MM format


class RecalculateResponse(BaseModel):
    success:     bool
    processed:   int
    message:     str
