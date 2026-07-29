#!/usr/bin/env python3
"""
Tests for the WhatsApp campaign results tracker on Customer Retarget.

Pure-logic pieces (phone matching, attribution window) are tested with real
assertions. Pieces that require a live Postgres session (tenant isolation on
the ORM queries, pagination, reply-window gating in
get_retarget_campaign_detail, and the Meta webhook signature/fail-closed
behaviour) are covered as static source contracts here, matching this
repo's existing test conventions (see test_customer_retarget_contract.py) —
there is no test-database fixture in this repo to run them against a real
session. The webhook and reply-attribution logic were additionally verified
live against production in a rolled-back transaction during development;
see the deploy notes for that session.
"""

from pathlib import Path
import unittest

from app.modules.customer_retarget.service import (
    RETARGET_REPLY_ATTRIBUTION_DAYS,
    _phone_variants,
)


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "backend" / "app" / "modules" / "customer_retarget" / "service.py"
ROUTER = ROOT / "backend" / "app" / "modules" / "customer_retarget" / "router.py"
WA_ROUTER = ROOT / "backend" / "app" / "modules" / "wa_engine" / "router.py"
WA_SERVICE = ROOT / "backend" / "app" / "modules" / "wa_engine" / "service.py"
META_PROVIDER = ROOT / "backend" / "app" / "modules" / "wa_engine" / "providers" / "meta.py"
WA_SCHEMAS = ROOT / "backend" / "app" / "modules" / "wa_engine" / "schemas.py"
WHATSAPP_PAGE = ROOT / "frontend" / "whatsapp.html"


class PhoneVariantMatchingTests(unittest.TestCase):
    def test_ten_digit_number_produces_e164_and_local_variants(self):
        variants = _phone_variants("9833822820")
        self.assertIn("9833822820", variants)
        self.assertIn("919833822820", variants)
        self.assertIn("+919833822820", variants)

    def test_e164_number_produces_local_variant(self):
        variants = _phone_variants("+919833822820")
        self.assertIn("919833822820", variants)
        self.assertIn("9833822820", variants)
        self.assertIn("+919833822820", variants)

    def test_empty_or_missing_phone_produces_no_variants(self):
        self.assertEqual(_phone_variants(""), set())
        self.assertEqual(_phone_variants(None), set())


class ReplyAttributionWindowTests(unittest.TestCase):
    def test_attribution_window_is_seven_days(self):
        self.assertEqual(RETARGET_REPLY_ATTRIBUTION_DAYS, 7)


class CampaignTrackerTenantIsolationContractTests(unittest.TestCase):
    """
    Every campaign query must be scoped by current_user.tenant_id — a batch_id
    is a client-suppliable path parameter, so without this filter one tenant
    could read another tenant's WhatsApp campaign (customer names, phone
    numbers, Meta error text) by guessing/enumerating batch_ids.
    """

    def test_list_campaigns_is_tenant_scoped(self):
        source = SERVICE.read_text()
        self.assertIn("def list_retarget_campaigns(", source)
        self.assertIn(
            "MessageAutomationTask.tenant_id == current_user.tenant_id",
            source,
        )

    def test_campaign_detail_is_tenant_scoped(self):
        source = SERVICE.read_text()
        self.assertIn("def get_retarget_campaign_detail(", source)
        # tenant_id filter must appear on every relevant query: tasks, wa_messages,
        # wa_subscribers, wa_conversations, inbound wa_messages.
        self.assertGreaterEqual(
            source.count("tenant_id == current_user.tenant_id"), 5
        )

    def test_missing_batch_returns_404_not_other_tenants_data(self):
        source = SERVICE.read_text()
        self.assertIn('raise HTTPException(status_code=404, detail="Campaign batch not found")', source)


class CampaignTrackerFailureStateTests(unittest.TestCase):
    def test_reply_is_only_attributed_to_successfully_sent_tasks(self):
        source = SERVICE.read_text()
        self.assertIn('if task.status == "sent" and task.sent_at:', source)

    def test_reply_window_is_bounded_not_open_ended(self):
        source = SERVICE.read_text()
        self.assertIn("window_end = task.sent_at + timedelta(days=RETARGET_REPLY_ATTRIBUTION_DAYS)", source)
        self.assertIn("task.sent_at < ts <= window_end", source)

    def test_delivery_and_read_are_never_fabricated(self):
        source = SERVICE.read_text()
        # None (not False) when no wa_messages row has reported a status yet.
        self.assertIn("delivery_status = wa_message.status.value if wa_message else None", source)
        self.assertIn("is_read = bool(wa_message.read_at) if wa_message else None", source)
        self.assertIn('"read_receipts_tracked": False', source)


class CampaignTrackerPaginationContractTests(unittest.TestCase):
    def test_router_accepts_page_and_limit_on_both_endpoints(self):
        source = ROUTER.read_text()
        self.assertIn('@router.get("/whatsapp/campaigns")', source)
        self.assertIn('@router.get("/whatsapp/campaigns/{batch_id}")', source)
        self.assertGreaterEqual(source.count("page: int = Query(1, ge=1)"), 2)
        self.assertGreaterEqual(source.count("limit: int = Query(25, ge=1, le=200)"), 2)

    def test_service_paginates_recipients_not_just_the_list(self):
        source = SERVICE.read_text()
        self.assertIn(".offset((page - 1) * limit)", source)
        self.assertIn("total_recipients", source)


class CampaignDailyReportingContractTests(unittest.TestCase):
    def test_router_accepts_specific_date_range(self):
        source = ROUTER.read_text()
        self.assertIn("date_from: Optional[date] = Query(None)", source)
        self.assertIn("date_to: Optional[date] = Query(None)", source)

    def test_daily_results_use_india_local_dates_and_include_zero_days(self):
        source = SERVICE.read_text()
        for marker in [
            'CAMPAIGN_REPORT_TIMEZONE = "Asia/Kolkata"',
            "MAX_CAMPAIGN_REPORT_DAYS = 366",
            "MessageAutomationTask.created_at >= range_start",
            "MessageAutomationTask.created_at < range_end",
            "daily_by_date =",
            "while result_date >= selected_from:",
            '"daily_results": daily_results',
        ]:
            self.assertIn(marker, source)

    def test_frontend_has_quick_and_custom_date_filters(self):
        source = (
            ROOT / "frontend" / "customer-retarget.html"
        ).read_text()
        for marker in [
            "setCampaignRange(1)",
            "setCampaignRange(3)",
            "setCampaignRange(7)",
            'id="campaignDateFrom"',
            'id="campaignDateTo"',
            "applyCampaignCustomRange()",
            "Results by day",
            "daily_results",
        ]:
            self.assertIn(marker, source)


class MetaStatusWebhookSecurityContractTests(unittest.TestCase):
    """
    A message-status callback (delivered/read/failed) must never be applied
    without a verified Meta signature. Missing configuration must fail
    closed (skip processing), never fail open (process unverified data).
    """

    def test_parse_statuses_exists_and_is_shape_aware(self):
        source = META_PROVIDER.read_text()
        self.assertIn("def parse_statuses(", source)
        self.assertIn('value.get("statuses", [])', source)

    def test_router_verifies_signature_before_applying_status_updates(self):
        source = WA_ROUTER.read_text()
        verify_index = source.index("MetaProvider.verify_signature(")
        apply_index = source.index("service.apply_meta_status_update(")
        self.assertLess(
            verify_index,
            apply_index,
            "signature must be verified before status updates are applied",
        )

    def test_missing_app_secret_fails_closed(self):
        source = WA_ROUTER.read_text()
        self.assertIn("if not row.meta_app_secret:", source)
        # the fail-closed branch must not call apply_meta_status_update
        skip_branch_start = source.index("if not row.meta_app_secret:")
        skip_branch_end = source.index("elif not MetaProvider.verify_signature")
        skip_branch = source[skip_branch_start:skip_branch_end]
        self.assertNotIn("apply_meta_status_update", skip_branch)

    def test_app_secret_is_configurable_but_not_returned(self):
        schemas_source = WA_SCHEMAS.read_text()
        page_source = WHATSAPP_PAGE.read_text()
        self.assertIn("meta_app_secret:            Optional[str] = None", schemas_source)
        self.assertIn("meta_app_secret_set:         bool = False", schemas_source)
        self.assertIn('id="sMetaAppSecret"', page_source)
        self.assertIn("body.meta_app_secret = metaSecretVal", page_source)

    def test_status_update_never_regresses_delivery_state(self):
        source = WA_SERVICE.read_text()
        self.assertIn("_STATUS_RANK", source)
        self.assertIn("_STATUS_RANK[new_status] > _STATUS_RANK.get(message.status, -1)", source)


if __name__ == "__main__":
    unittest.main()
