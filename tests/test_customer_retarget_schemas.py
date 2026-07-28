#!/usr/bin/env python3
"""Validation tests for Customer Retarget request contracts."""

from datetime import datetime, timedelta, timezone
import unittest

from pydantic import ValidationError

from app.models.customer_retarget import RetargetOutcome
from app.modules.customer_retarget.schemas import (
    RetargetCallCreate,
    UnlinkedCustomerCreate,
    UnlinkedResolveRequest,
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


if __name__ == "__main__":
    unittest.main()
