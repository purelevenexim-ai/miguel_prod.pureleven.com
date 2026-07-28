#!/usr/bin/env python3
"""Audit and optionally repair order amount_due/cod_amount invariants.

Dry-run is the default:
    python backend/scripts/repair_order_payment_balances.py --tenant pureleven

Apply only after reviewing the output:
    python backend/scripts/repair_order_payment_balances.py --tenant pureleven --apply
"""

from __future__ import annotations

import argparse
from decimal import Decimal

from app.database.session import SessionLocal
from app.models.order import Order, PaymentMethod, PaymentStatus
from app.models.tenant import Tenant


CENT = Decimal("0.01")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant", required=True, help="Tenant slug")
    parser.add_argument("--apply", action="store_true", help="Commit repairs")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.slug == args.tenant).first()
        if not tenant:
            raise SystemExit(f"Tenant not found: {args.tenant}")

        orders = db.query(Order).filter(Order.tenant_id == tenant.id).all()
        repairs: list[tuple[Order, Decimal, Decimal, Decimal, Decimal]] = []
        for order in orders:
            total = Decimal(str(order.total_amount or 0))
            current_paid = Decimal(str(order.amount_paid or 0)).quantize(CENT)
            expected_paid = (
                total.quantize(CENT)
                if order.payment_status == PaymentStatus.paid
                else min(current_paid, total).quantize(CENT)
            )
            expected_due = max(Decimal("0"), total - expected_paid).quantize(CENT)
            current_due = Decimal(str(order.amount_due or 0)).quantize(CENT)
            if current_due != expected_due or current_paid != expected_paid:
                repairs.append((order, current_paid, expected_paid, current_due, expected_due))

        print(f"Tenant: {tenant.slug}")
        print(f"Inconsistent orders: {len(repairs)}")
        for order, current_paid, expected_paid, current_due, expected_due in repairs:
            print(
                f"{order.order_number}: paid {current_paid} -> {expected_paid}; "
                f"due {current_due} -> {expected_due} (total={order.total_amount})"
            )

        if not args.apply:
            print("Dry run only; no rows changed.")
            return 0

        for order, _, expected_paid, _, expected_due in repairs:
            order.amount_paid = expected_paid
            order.amount_due = expected_due
            if order.payment_method == PaymentMethod.partial_cod:
                order.cod_amount = expected_due
        db.commit()
        print(f"Applied repairs: {len(repairs)}")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
