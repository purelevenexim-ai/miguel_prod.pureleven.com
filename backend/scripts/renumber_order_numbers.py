from __future__ import annotations

from datetime import datetime, timezone
import argparse
import re

from sqlalchemy import text

from app.database.session import SessionLocal
from app.models.order import Order
from app.models.tenant import Tenant


def derive_prefix(slug: str | None) -> str:
    if slug:
        s = slug.upper().replace("-", "").replace("_", "")
        consonants = re.sub(r"[AEIOU0-9]", "", s)
        if len(consonants) >= 3:
            return consonants[0] + consonants[1] + consonants[-1]
        if len(s) >= 3:
            return s[:3]
        return s.ljust(3, "X")
    return "ORD"


def as_utc(dt: datetime | None) -> datetime:
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def renumber_orders(apply_changes: bool) -> None:
    db = SessionLocal()
    try:
        # Block concurrent order writes while renumbering to avoid race issues.
        db.execute(text("LOCK TABLE orders IN EXCLUSIVE MODE"))

        tenant_rows = (
            db.query(Order.tenant_id, Tenant.slug)
            .join(Tenant, Tenant.id == Order.tenant_id)
            .distinct()
            .all()
        )

        if not tenant_rows:
            print("No orders found. Nothing to renumber.")
            db.rollback()
            return

        total_orders = 0
        changed_orders = 0

        for tenant_id, slug in tenant_rows:
            prefix = derive_prefix(slug)
            orders = (
                db.query(Order)
                .filter(Order.tenant_id == tenant_id)
                .order_by(Order.created_at.asc(), Order.id.asc())
                .all()
            )

            total_orders += len(orders)
            if not orders:
                continue

            planned = []
            for idx, order in enumerate(orders, start=1):
                date_str = as_utc(order.created_at).strftime("%y%m%d")
                new_number = f"{prefix}-{date_str}-{idx:03d}"
                planned.append((order, new_number))

            sample_old = planned[0][0].order_number
            sample_new = planned[0][1]
            tail_old = planned[-1][0].order_number
            tail_new = planned[-1][1]

            print(
                f"Tenant {tenant_id} ({slug}): {len(planned)} orders | "
                f"first: {sample_old} -> {sample_new} | "
                f"last: {tail_old} -> {tail_new}"
            )

            if not apply_changes:
                continue

            # Phase 1: assign temporary unique values to avoid unique constraint collisions.
            for order, _ in planned:
                order.order_number = "TMP-" + str(order.id).replace("-", "")[:26]
            db.flush()

            # Phase 2: assign final continuous numbers.
            for order, new_number in planned:
                if order.order_number != new_number:
                    changed_orders += 1
                order.order_number = new_number

            db.flush()

        if apply_changes:
            db.commit()
            print(
                f"Done. Renumbered {changed_orders} of {total_orders} orders "
                f"across {len(tenant_rows)} tenant(s)."
            )
        else:
            db.rollback()
            print(
                f"Dry run complete. {total_orders} orders inspected "
                f"across {len(tenant_rows)} tenant(s)."
            )

    except Exception as exc:
        db.rollback()
        print(f"Renumber failed: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Renumber order numbers continuously per tenant")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (without this flag, runs as dry-run)",
    )
    args = parser.parse_args()
    renumber_orders(apply_changes=args.apply)
