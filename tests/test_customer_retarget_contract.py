#!/usr/bin/env python3
"""Static contract tests for the isolated Customer Retarget feature."""

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "frontend" / "customer-retarget.html"
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
            "Follow-up / Overdue",
            "Risk Customers",
            "Unlinked Orders",
            "Old Customers",
            "Save &amp; next customer",
            "Create and link customer",
            "/api/customer-retarget/queue",
            "/api/customers/${currentCustomerId}",
        ]:
            self.assertIn(marker, html)

    def test_retarget_handoff_and_navigation_are_present(self):
        html = PAGE.read_text()
        self.assertNotIn("['old_customers','Old Customers']", html)
        for marker in [
            "Saved delivery address",
            "View full customer",
            "Open full order form",
            "Use items in new order",
            "retarget_order_prefill",
            "if(outcome==='interested'&&CAN_CREATE_ORDER){startOrder();return}",
            "OLD CUSTOMER",
        ]:
            self.assertIn(marker, html)

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
