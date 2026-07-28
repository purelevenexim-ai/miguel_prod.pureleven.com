#!/usr/bin/env python3
"""Static contract tests for the isolated Customer Retarget feature."""

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "frontend" / "customer-retarget.html"
ORDERS_PAGE = ROOT / "frontend" / "orders.html"
SERVICE = ROOT / "backend" / "app" / "modules" / "customer_retarget" / "service.py"
IMPORTER = ROOT / "backend" / "scripts" / "import_old_whatsapp_customers.py"
ROUTER = ROOT / "backend" / "app" / "modules" / "customer_retarget" / "router.py"
MODEL = ROOT / "backend" / "app" / "models" / "customer_retarget.py"
MIGRATION = (
    ROOT
    / "backend"
    / "alembic"
    / "versions"
    / "rtg001_customer_retarget.py"
)


class CustomerRetargetContractTests(unittest.TestCase):
    def test_python_sources_parse(self):
        for path in [SERVICE, ROUTER, MODEL, MIGRATION, IMPORTER]:
            ast.parse(path.read_text(), filename=str(path))

    def test_migration_is_based_on_production_head(self):
        source = MIGRATION.read_text()
        self.assertIn('down_revision = "z1a2b3c4d5e6"', source)
        self.assertIn('"customer_retarget_states"', source)
        self.assertIn('"customer_retarget_calls"', source)

    def test_api_contract_is_present(self):
        source = ROUTER.read_text()
        self.assertIn('@router.get("/queue")', source)
        self.assertIn(
            '@router.post("/unlinked/{shopify_order_id}/resolve")',
            source,
        )
        self.assertIn('@router.get("/{customer_id}")', source)
        self.assertIn('@router.post("/{customer_id}/calls"', source)
        self.assertIn('@router.post("/whatsapp/send-template"', source)

    def test_all_required_outcomes_exist(self):
        source = MODEL.read_text()
        for outcome in [
            "no_answer",
            "callback",
            "interested",
            "purchased_again",
            "not_interested",
            "purchased_elsewhere",
            "invalid_number",
            "risk",
        ]:
            self.assertIn(f'{outcome} = "{outcome}"', source)

    def test_standalone_page_contains_required_workflows(self):
        html = PAGE.read_text()
        for marker in [
            "Customer Retarget",
            "To Contact",
            "Premium Customers",
            "High Value Purchase",
            "Follow-up / Overdue",
            "Risk Customers",
            "Unlinked Orders",
            "Old Customers",
            "Save &amp; next customer",
            "Create and link customer",
            "/api/customer-retarget/queue",
            "/api/customer-retarget/whatsapp/send-template",
            "/api/message-automation/available-whatsapp-templates",
            "/api/customers/${currentCustomerId}",
            "Choose template &amp; send",
            "toggleSelectPage",
            "consent_confirmed:true",
        ]:
            self.assertIn(marker, html)

    def test_bulk_template_send_is_tenant_scoped_and_audited(self):
        source = SERVICE.read_text()
        for marker in [
            "queue_retarget_template",
            "Customer.tenant_id == current_user.tenant_id",
            "preference_blocks",
            "queue_manual_retarget_template",
            "current_user.id",
            "db.commit()",
        ]:
            self.assertIn(marker, source)

    def test_premium_and_high_value_queue_filters_are_present(self):
        source = SERVICE.read_text()
        for marker in [
            '"premium"',
            '"high_value"',
            'view == "premium"',
            "aggregate.c.order_count > 1",
            'view == "high_value"',
            'aggregate.c.lifetime_value > Decimal("1500")',
        ]:
            self.assertIn(marker, source)

    def test_retarget_handoff_and_navigation_are_present(self):
        html = PAGE.read_text()
        self.assertNotIn("['old_customers','Old Customers']", html)
        for marker in [
            'class="sidebar retarget-sidebar"',
            'aria-current="page"',
            "Saved delivery address",
            "View full customer",
            "Send WhatsApp template",
            "openWorkspaceTemplate",
            "Open full order form",
            "Use items in new order",
            "retarget_order_prefill",
            "if(outcome==='interested'&&CAN_CREATE_ORDER){startOrder();return}",
            "OLD CUSTOMER",
        ]:
            self.assertIn(marker, html)

        orders_html = ORDERS_PAGE.read_text()
        for marker in [
            "retarget-order-mode",
            "Complete order workspace for",
            "products, pricing, payment, courier, status and final confirmation",
        ]:
            self.assertIn(marker, orders_html)

        for relative_path in [
            "frontend/tenant-admin.html",
            "frontend/marketing.html",
            "frontend/modules/mobile-nav.v4.js",
        ]:
            self.assertIn(
                "/customer-retarget.html",
                (ROOT / relative_path).read_text(),
            )


if __name__ == "__main__":
    unittest.main()
