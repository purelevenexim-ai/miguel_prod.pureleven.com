#!/usr/bin/env python3
"""Validation tests for Customer Retarget request contracts."""

from datetime import datetime, timedelta, timezone
import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.models.customer_retarget import RetargetOutcome
from app.modules.customer_retarget.schemas import (
    RetargetCallCreate,
    RetargetTemplateBulkSend,
    UnlinkedCustomerCreate,
    UnlinkedResolveRequest,
)
from app.modules.message_automation.service import (
    _manual_meta_components_from_template_json,
)


class RetargetCallValidationTests(unittest.TestCase):
    def test_follow_up_outcomes_require_future_callback(self):
        for outcome in [
            RetargetOutcome.no_answer,
            RetargetOutcome.callback,
            RetargetOutcome.interested,
        ]:
            with self.assertRaises(ValidationError):
                RetargetCallCreate(outcome=outcome)

            request = RetargetCallCreate(
                outcome=outcome,
                next_callback_at=datetime.now(timezone.utc)
                + timedelta(days=1),
            )
            self.assertEqual(request.outcome, outcome)

    def test_risk_requires_notes(self):
        with self.assertRaises(ValidationError):
            RetargetCallCreate(outcome=RetargetOutcome.risk)

        request = RetargetCallCreate(
            outcome=RetargetOutcome.risk,
            notes="Customer reported a serious service problem",
        )
        self.assertTrue(request.notes)

    def test_closed_outcome_does_not_require_callback(self):
        request = RetargetCallCreate(
            outcome=RetargetOutcome.not_interested,
        )
        self.assertIsNone(request.next_callback_at)


class UnlinkedResolveValidationTests(unittest.TestCase):
    def test_resolution_requires_exactly_one_target(self):
        with self.assertRaises(ValidationError):
            UnlinkedResolveRequest()

        customer = UnlinkedCustomerCreate(name="Buyer", phone="9999999999")
        request = UnlinkedResolveRequest(customer=customer)
        self.assertEqual(request.customer.name, "Buyer")


class RetargetTemplateValidationTests(unittest.TestCase):
    def test_bulk_send_requires_explicit_permission_confirmation(self):
        with self.assertRaises(ValidationError):
            RetargetTemplateBulkSend(
                customer_ids=[uuid4()],
                template_name="customer_product_greeting_v1",
            )

    def test_bulk_send_deduplicates_customers_and_requires_https_media(self):
        customer_id = uuid4()
        request = RetargetTemplateBulkSend(
            customer_ids=[customer_id, customer_id],
            template_name=" customer_product_greeting_v1 ",
            language_code="ml",
            header_image_url="https://example.com/pureleven.jpg",
            consent_confirmed=True,
        )
        self.assertEqual(request.customer_ids, [customer_id])
        self.assertEqual(request.template_name, "customer_product_greeting_v1")

        with self.assertRaises(ValidationError):
            RetargetTemplateBulkSend(
                customer_ids=[customer_id],
                template_name="customer_product_greeting_v1",
                header_image_url="http://example.com/pureleven.jpg",
                consent_confirmed=True,
            )

    def test_customer_name_fills_first_positional_template_value(self):
        components = _manual_meta_components_from_template_json(
            {
                "components": [
                    {
                        "type": "BODY",
                        "text": "Dear {{1}}, warm greetings from Pureleven.",
                    }
                ]
            },
            {"customer_name": "Anu"},
        )
        self.assertEqual(
            components,
            [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": "Anu"}],
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
