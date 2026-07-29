#!/usr/bin/env python3
"""Extract raw customer/order rows from source application DB into CSV."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


DEFAULT_SQL = """
SELECT
  c.name,
  c.address,
  c.pincode,
  c.phone,
  c.phone_display,
  c.payment_type,
  c.amount,
  c.order_id,
  c.tracking_id,
  c.items,
  c.notes,
  c._id,
  c.created_ts,
  c.printed_count
FROM customers c
WHERE (:date_from IS NULL OR c.created_ts::date >= :date_from)
  AND (:date_to IS NULL OR c.created_ts::date <= :date_to)
ORDER BY c.created_ts ASC
"""


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Extract source customer/order rows to CSV")
    p.add_argument("--source-db-url", required=True, help="SQLAlchemy DB URL for source app")
    p.add_argument("--output", required=True, help="Output CSV path")
    p.add_argument("--sql-file", help="Optional SQL file path for custom extraction")
    p.add_argument("--date-from", help="Optional ISO date filter, e.g. 2026-03-01")
    p.add_argument("--date-to", help="Optional ISO date filter, e.g. 2026-03-31")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    query = Path(args.sql_file).read_text(encoding="utf-8") if args.sql_file else DEFAULT_SQL

    try:
        from sqlalchemy import create_engine, text
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing dependency 'sqlalchemy'. Install it or run in your backend Python environment."
        ) from exc

    engine = create_engine(args.source_db_url)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with engine.connect() as conn:
        result = conn.execute(
            text(query),
            {
                "date_from": args.date_from,
                "date_to": args.date_to,
            },
        )
        rows = result.mappings().all()

    if not rows:
        output_path.write_text("", encoding="utf-8")
        print("No rows extracted.")
        return 0

    headers = list(rows[0].keys())
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))

    print(f"Extracted {len(rows)} rows -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
