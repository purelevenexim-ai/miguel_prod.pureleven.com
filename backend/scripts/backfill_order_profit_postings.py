from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database.session import SessionLocal
from app.models.order import Order, OrderStatus
from app.modules.profit_engine.service import upsert_order_profit_posting


_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


def _month_start(month: str) -> datetime:
    if not _MONTH_RE.match(month):
        raise ValueError(f"Invalid month '{month}'. Expected YYYY-MM.")
    year = int(month[:4])
    mon = int(month[5:7])
    if mon < 1 or mon > 12:
        raise ValueError(f"Invalid month '{month}'. Month must be 01-12.")
    return datetime(year, mon, 1, tzinfo=timezone.utc)


def _next_month(dt: datetime) -> datetime:
    if dt.month == 12:
        return datetime(dt.year + 1, 1, 1, tzinfo=timezone.utc)
    return datetime(dt.year, dt.month + 1, 1, tzinfo=timezone.utc)


def backfill(
    from_month: str,
    to_month: str,
    apply_changes: bool,
    tenant_id: str | None,
    batch_size: int,
) -> None:
    start = _month_start(from_month)
    end_month = _month_start(to_month)
    if end_month < start:
        raise ValueError("to-month must be the same as or after from-month.")
    end_exclusive = _next_month(end_month)

    db = SessionLocal()
    try:
        q = db.query(Order.id, Order.tenant_id, Order.created_at).filter(
            Order.is_active == True,
            Order.status.notin_([OrderStatus.cancelled]),
            Order.created_at >= start,
            Order.created_at < end_exclusive,
        )
        if tenant_id:
            q = q.filter(Order.tenant_id == UUID(tenant_id))

        rows = q.order_by(Order.created_at.asc(), Order.id.asc()).all()
        total = len(rows)
        if not total:
            print("No eligible orders found for the requested range.")
            return

        tenant_counts: dict[str, int] = {}
        for _oid, tid, _created_at in rows:
            key = str(tid)
            tenant_counts[key] = tenant_counts.get(key, 0) + 1

        print(
            f"Range {from_month}..{to_month}: {total} orders across "
            f"{len(tenant_counts)} tenant(s)."
        )
        for tid, cnt in sorted(tenant_counts.items(), key=lambda x: x[0]):
            print(f"  - {tid}: {cnt} order(s)")

        if not apply_changes:
            print("Dry run complete. Use --apply to persist postings.")
            return

        processed = 0
        for order_id, tid, _created_at in rows:
            upsert_order_profit_posting(db, tenant_id=tid, order_id=order_id)
            processed += 1
            if processed % batch_size == 0:
                db.commit()
                print(f"Committed {processed}/{total} order postings...")

        db.commit()
        print(f"Done. Recalculated {processed} order profit posting(s).")

    except Exception as exc:
        db.rollback()
        print(f"Backfill failed: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Recalculate order profit postings for a month range"
    )
    parser.add_argument("--from-month", required=True, help="Start month (YYYY-MM)")
    parser.add_argument("--to-month", required=True, help="End month (YYYY-MM), inclusive")
    parser.add_argument("--tenant-id", help="Optional tenant UUID filter")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=200,
        help="Commit interval while applying changes",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (without this flag, runs as dry-run)",
    )
    args = parser.parse_args()

    backfill(
        from_month=args.from_month,
        to_month=args.to_month,
        apply_changes=args.apply,
        tenant_id=args.tenant_id,
        batch_size=max(1, args.batch_size),
    )