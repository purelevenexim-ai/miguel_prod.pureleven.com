#!/usr/bin/env python3
"""Static regression contracts for dashboard data and presentation semantics."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
REPORTING = ROOT / "backend/app/modules/reporting/service.py"
SCHEMAS = ROOT / "backend/app/modules/reporting/schemas.py"
ROUTER = ROOT / "backend/app/modules/reporting/router.py"
ORDERS = ROOT / "backend/app/modules/orders/service.py"
DASHBOARD = ROOT / "frontend/tenant-admin.html"
PROFIT_LOSS = ROOT / "frontend/profit-loss.html"


class DashboardConsistencyContractTests(unittest.TestCase):
    def test_default_reporting_scope_is_shared_and_operational(self):
        source = REPORTING.read_text()
        self.assertIn("_OPERATIONAL_ORDER_STATUSES", source)
        self.assertIn("_order_scope_conditions", source)
        self.assertIn("Order.is_active == True", source)
        for status in ["confirmed", "processing", "packed", "shipped", "out_for_delivery", "delivered"]:
            self.assertIn(f"OrderStatus.{status}", source)

    def test_financial_metrics_use_source_fields(self):
        service = REPORTING.read_text()
        schema = SCHEMAS.read_text()
        self.assertIn("collected_revenue", schema)
        self.assertIn("func.sum(Order.amount_paid)", service)
        self.assertIn("func.sum(Order.actual_shipping_cost)", service)
        self.assertNotIn("func.sum(Order.shipping_charge)).scalar()", service)

    def test_all_order_analytics_accept_status_and_state(self):
        router = ROUTER.read_text()
        self.assertGreaterEqual(router.count('status: Optional[str] = Query(None'), 6)
        self.assertGreaterEqual(router.count('state: Optional[str] = Query(None'), 7)

    def test_partial_payment_updates_due_balance(self):
        source = ORDERS.read_text()
        self.assertIn("order.total_amount - order.amount_paid", source)
        self.assertIn("order.amount_paid = min(order.advance_amount, order.total_amount)", source)
        self.assertIn("if order.payment_status == PaymentStatus.paid:", source)
        self.assertIn("order.amount_paid = order.total_amount", source)

    def test_dashboard_uses_explicit_metric_names_and_shared_filters(self):
        html = DASHBOARD.read_text()
        for marker in [
            "Realized Revenue",
            "Actual Shipping Cost",
            "All operational",
            "shadcn-inspired analytical surface",
            "q.set('state', merged.state)",
            "d.delivered_revenue",
            "d.collected_revenue",
            "Order Book and Outstanding",
            "Current leads by stage—not cumulative funnel progression",
        ]:
            self.assertIn(marker, html)
        self.assertNotIn("Math.max(0, rev - out)", html)
        profit_html = PROFIT_LOSS.read_text()
        self.assertIn("parseFloat(m.collected)", profit_html)
        self.assertNotIn("parseFloat(m.revenue)||0) - (parseFloat(m.outstanding)", profit_html)
        self.assertNotIn("var collected = rev - out", profit_html)


if __name__ == "__main__":
    unittest.main()
