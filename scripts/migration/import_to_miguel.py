#!/usr/bin/env python3
"""Import normalized migration CSV into Miguel DB with idempotent upsert behavior."""

from __future__ import annotations

import argparse
import csv
import json
import re
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Import normalized rows into Miguel DB")
    p.add_argument("--input", required=True, help="Normalized CSV path")
    p.add_argument("--target-db-url", required=True, help="Miguel DB URL")
    p.add_argument("--target-tenant-id", required=True, help="Miguel tenant UUID")
    p.add_argument("--created-by-id", required=True, help="Miguel employee UUID used as created_by")
    p.add_argument("--dry-run", action="store_true", help="Validate + report only; no writes")
    p.add_argument(
        "--allow-unresolved-products",
        action="store_true",
        help="Allow importing rows with unresolved product mapping (default false)",
    )
    return p.parse_args()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def payment_status_for(payment_method: str) -> str:
    return "pending" if payment_method == "cod" else "paid"


def normalize_phone(value: str | None) -> str:
    # Handle multi-number cells (e.g. "9446700486\n8132847113") — take the first number only
    raw = (value or "").strip()
    # Split on any whitespace/newline separator and grab first segment that looks like a phone
    for segment in re.split(r"[\s\n/,;]+", raw):
        digits = re.sub(r"\D", "", segment)
        if len(digits) == 12 and digits.startswith("91"):
            return digits[2:]
        if 7 <= len(digits) <= 13:
            return digits
    # Fallback: strip all non-digits
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 12 and digits.startswith("91"):
        return digits[2:]
    # Merged multi-number: take first 10 digits (Indian mobile length)
    if len(digits) > 10:
        return digits[:10]
    return digits


def find_customer_id(conn, tenant_id: str, phone: str):
    digits = normalize_phone(phone)
    if not digits:
        return None
    variants = {digits}
    if len(digits) == 10:
        variants.add(f"91{digits}")

    sql = text(
        """
        SELECT id
        FROM customers
        WHERE tenant_id = CAST(:tenant_id AS UUID)
          AND regexp_replace(COALESCE(phone, ''), '\\D', '', 'g') = ANY(:variants)
        ORDER BY created_at ASC
        LIMIT 1
        """
    )
    return conn.execute(sql, {"tenant_id": tenant_id, "variants": list(variants)}).scalar()


def upsert_customer(conn, tenant_id: str, created_by_id: str, row: dict[str, str]):
    # Extract only the numeric 6-digit PIN from whatever format the pincode arrived in
    raw_pin = row.get("pincode", "").strip()
    digits_only = re.sub(r"\D", "", raw_pin)
    pincode = digits_only[:6] if len(digits_only) >= 5 else ""

    phone_clean = normalize_phone(row.get("phone", ""))
    existing_id = find_customer_id(conn, tenant_id, row.get("phone", ""))
    if existing_id:
        conn.execute(
            text(
                """
                UPDATE customers
                SET name = COALESCE(NULLIF(:name, ''), name),
                    address = COALESCE(NULLIF(:address, ''), address),
                    pincode = COALESCE(NULLIF(:pincode, ''), pincode),
                    city = COALESCE(city, ''),
                    state = COALESCE(state, ''),
                    updated_at = NOW()
                WHERE id = CAST(:id AS UUID)
                """
            ),
            {
                "id": str(existing_id),
                "name": row.get("name", "").strip(),
                "address": row.get("address", "").strip(),
                "pincode": pincode,
            },
        )
        return str(existing_id), True

    customer_id = str(uuid.uuid4())
    conn.execute(
        text(
            """
            INSERT INTO customers (
              id, tenant_id, unique_customer_code, name, phone, address, pincode,
              city, state, country,
              customer_type, payment_mode_preference, source, lead_status,
              created_by_employee_id, is_active, created_at, updated_at
            ) VALUES (
              CAST(:id AS UUID), CAST(:tenant_id AS UUID), :code, :name, :phone, :address, :pincode,
              '', '', 'India',
              'retail', CAST(CASE WHEN :payment_type = 'cod' THEN 'cod' ELSE 'prepaid' END AS paymentmode),
              'manual', 'converted',
              CAST(:created_by AS UUID), TRUE, NOW(), NOW()
            )
            """
        ),
        {
            "id": customer_id,
            "tenant_id": tenant_id,
            "code": f"CUST-MIG-{customer_id[:8].upper()}",
            "name": row.get("name", "").strip() or "Unknown",
            "phone": phone_clean,
            "address": row.get("address", "").strip(),
            "pincode": pincode,
            "payment_type": row.get("payment_type", "cod"),
            "created_by": created_by_id,
        },
    )
    return customer_id, False


def find_order_by_source_marker(conn, tenant_id: str, source_order_id: str):
    sql = text(
        """
        SELECT id
        FROM orders
        WHERE tenant_id = CAST(:tenant_id AS UUID)
          AND notes ILIKE :marker
        LIMIT 1
        """
    )
    return conn.execute(
        sql,
        {
            "tenant_id": tenant_id,
            "marker": f"%SOURCE_ORDER_ID={source_order_id}%",
        },
    ).scalar()


def next_order_number(conn, tenant_id: str, date_yymmdd: str, prefix: str) -> str:
    sql = text(
        """
        SELECT COALESCE(MAX(CAST(substring(order_number from '([0-9]+)$') AS INTEGER)), 0)
        FROM orders
        WHERE tenant_id = CAST(:tenant_id AS UUID)
          AND order_number LIKE :pref
        """
    )
    max_seq = conn.execute(
        sql,
        {
            "tenant_id": tenant_id,
            "pref": f"{prefix}-{date_yymmdd}-%",
        },
    ).scalar() or 0
    return f"{prefix}-{date_yymmdd}-{str(int(max_seq) + 1).zfill(3)}"


def import_rows(args: argparse.Namespace) -> None:
    try:
        from sqlalchemy import create_engine, text
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing dependency 'sqlalchemy'. Install it or run in your backend Python environment."
        ) from exc

    globals()["text"] = text

    input_path = Path(args.input)
    engine = create_engine(args.target_db_url)

    summary = {
        "rows_total": 0,
        "rows_imported": 0,
        "rows_skipped_existing": 0,
        "rows_skipped_unresolved": 0,
        "customers_created": 0,
        "customers_updated": 0,
    }

    with input_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    summary["rows_total"] = len(rows)
    if not rows:
        print("No rows to import.")
        return

    if args.dry_run:
        for r in rows:
            if int(r.get("mapping_unresolved_count") or 0) > 0 and not args.allow_unresolved_products:
                summary["rows_skipped_unresolved"] += 1
        print("DRY RUN SUMMARY:")
        print(json.dumps(summary, indent=2))
        return

    with engine.begin() as conn:
        tenant_slug = conn.execute(
            text("SELECT slug FROM tenants WHERE id = CAST(:tid AS UUID)"),
            {"tid": args.target_tenant_id},
        ).scalar() or "ORD"
        prefix = re.sub(r"[^A-Za-z0-9]", "", tenant_slug.upper())[:3] or "ORD"

        for row in rows:
            source_order_id = row.get("source_order_id", "").strip()
            unresolved_count = int(row.get("mapping_unresolved_count") or 0)
            if unresolved_count > 0 and not args.allow_unresolved_products:
                summary["rows_skipped_unresolved"] += 1
                continue

            existing_order = find_order_by_source_marker(conn, args.target_tenant_id, source_order_id)
            if existing_order:
                summary["rows_skipped_existing"] += 1
                continue

            customer_id, was_update = upsert_customer(
                conn,
                tenant_id=args.target_tenant_id,
                created_by_id=args.created_by_id,
                row=row,
            )
            if was_update:
                summary["customers_updated"] += 1
            else:
                summary["customers_created"] += 1

            src_date = row.get("source_order_date", "")
            date_yymmdd = datetime.fromisoformat(src_date).strftime("%y%m%d") if src_date else now_utc().strftime("%y%m%d")
            order_number = next_order_number(conn, args.target_tenant_id, date_yymmdd, prefix)

            order_id = str(uuid.uuid4())
            # Extract numeric part of amount (e.g., "900 (call)" -> 900)
            amount_str = (row.get("amount") or "0").strip()
            amount_numeric = re.sub(r"[^\d.]", "", amount_str) or "0"
            amount = Decimal(str(amount_numeric))
            payment = (row.get("payment_type") or "cod").lower()
            notes = (row.get("migration_notes") or "") + f" | MIGRATED_AT={now_utc().isoformat()}"

            conn.execute(
                text(
                    """
                    INSERT INTO orders (
                      id, tenant_id, order_number, customer_id,
                      status, payment_status, payment_method,
                      subtotal, discount_amount, tax_amount, shipping_charge,
                      total_amount, amount_paid, amount_due,
                      delivery_address, delivery_city, delivery_state, delivery_pincode,
                      tracking_number, shipping_service,
                      created_by_id, notes, is_active, created_at, updated_at,
                      printed_count
                    ) VALUES (
                      CAST(:id AS UUID), CAST(:tenant_id AS UUID), :order_number, CAST(:customer_id AS UUID),
                      CAST('confirmed' AS orderstatus), CAST(:payment_status AS paymentstatus), CAST(:payment_method AS paymentmethod),
                      :subtotal, 0, 0, 0,
                      :total_amount, :amount_paid, :amount_due,
                      :delivery_address, '', '', :delivery_pincode,
                      :tracking_number, CASE WHEN :payment_method='cod' THEN 'speed_post' ELSE 'parcel' END,
                      CAST(:created_by_id AS UUID), :notes, TRUE, NOW(), NOW(),
                      0
                    )
                    """
                ),
                {
                    "id": order_id,
                    "tenant_id": args.target_tenant_id,
                    "order_number": order_number,
                    "customer_id": customer_id,
                    "payment_status": payment_status_for(payment),
                    "payment_method": payment,
                    "subtotal": amount,
                    "total_amount": amount,
                    "amount_paid": amount if payment != "cod" else Decimal("0"),
                    "amount_due": Decimal("0") if payment != "cod" else amount,
                    "delivery_address": row.get("address", ""),
                    "delivery_pincode": re.sub(r"\D", "", row.get("pincode", ""))[:6],
                    # Tracking: keep only first line and cap at 98 chars; discard multi-line descriptions
                    "tracking_number": (raw_tracking.splitlines()[0][:98] if (raw_tracking := row.get("tracking_id", "").strip()) else None) or None,
                    "created_by_id": args.created_by_id,
                    "notes": notes,
                },
            )

            items = json.loads(row.get("items_mapped_json") or "[]")
            for it in items:
                if not it.get("target_product_name") and not args.allow_unresolved_products:
                    continue
                conn.execute(
                    text(
                        """
                        INSERT INTO order_items (
                          id, tenant_id, order_id, product_name, sku, quantity, unit, unit_price,
                          discount_pct, line_total, notes, created_at
                        ) VALUES (
                          CAST(:id AS UUID), CAST(:tenant_id AS UUID), CAST(:order_id AS UUID),
                          :product_name, NULL, :quantity, 'piece', :unit_price,
                          0, :line_total, :notes, NOW()
                        )
                        """
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "tenant_id": args.target_tenant_id,
                        "order_id": order_id,
                        "product_name": it.get("target_product_name") or it.get("source_product_name") or "Unknown",
                        "quantity": Decimal(str(it.get("quantity") or 1)),
                        "unit_price": Decimal(str(it.get("unit_price") or 0)),
                        "line_total": Decimal(str(it.get("quantity") or 1)) * Decimal(str(it.get("unit_price") or 0)),
                        "notes": f"source={it.get('source_product_name','')}; method={it.get('match_method','')}; score={it.get('match_score',0)}",
                    },
                )

            summary["rows_imported"] += 1

    print("IMPORT SUMMARY:")
    print(json.dumps(summary, indent=2))


def main() -> int:
    args = parse_args()
    import_rows(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
