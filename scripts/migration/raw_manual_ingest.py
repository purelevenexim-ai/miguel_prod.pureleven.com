#!/usr/bin/env python3
"""Convert raw manual rows into Miguel-ready create/update staging files.

Input: CSV with columns similar to:
row_no, name, address, pincode, phone, paid, cost, source_order_id, tracking_id, items, issues

Output files:
- create_orders_api.jsonl: payload per row for POST /api/orders/
- update_tracking_upload.csv: customer/tracking sheet for manual-orders tracking upload
- hold_rows.csv: rows intentionally held based on issue notes
- ingest_report.csv: row classification summary
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


HOLD_KEYWORDS = (
    "eppo venda",
    "parayam",
    "hold",
    "later",
    "wait",
)


def looks_like_items_text(text: str) -> bool:
    t = text.lower()
    if not t:
        return False
    item_markers = (
        "gm",
        "kg",
        "pepper",
        "cardamom",
        "elakka",
        "kurumulaku",
        "ഗ്രാമ്പൂ",
        "ഏലക്ക",
        "കുരുമുളക്",
        "₹",
        "=",
        "+",
    )
    return any(m in t for m in item_markers)


def normalize_items_and_issues(row: dict[str, str]) -> tuple[str, str]:
    items_text = norm(row.get("items"))
    issues_text = norm(row.get("issues"))

    extra_values = row.get(None) or []
    extra_text = " | ".join(norm(v) for v in extra_values if norm(v))

    if extra_text:
        extra_is_hold = is_hold_row(extra_text)
        issues_is_hold = is_hold_row(issues_text)

        if extra_is_hold:
            if issues_text and not issues_is_hold and looks_like_items_text(issues_text) and not items_text:
                items_text = issues_text
            issues_text = extra_text
        elif not issues_text:
            issues_text = extra_text

    if not items_text and issues_text and not is_hold_row(issues_text) and looks_like_items_text(issues_text):
        items_text = issues_text
        issues_text = ""

    return items_text, issues_text


def with_normalized_row(row: dict[str, str]) -> dict[str, str]:
    fixed = dict(row)
    if None in fixed:
        fixed.pop(None, None)
    items_text, issues_text = normalize_items_and_issues(row)
    fixed["items"] = items_text
    fixed["issues"] = issues_text
    return fixed


@dataclass
class RowDecision:
    row_no: str
    name: str
    bucket: str
    reason: str
    source_order_id: str
    tracking_id: str


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Split raw manual rows into create/update import files")
    p.add_argument("--input", required=True, help="Path to raw input CSV")
    p.add_argument("--out-dir", required=True, help="Output directory")
    p.add_argument(
        "--default-order-source",
        default="manual_raw_ingest",
        help="order_source value for created orders",
    )
    return p.parse_args()


def norm(v: str | None) -> str:
    return (v or "").strip()


def digits_only(v: str | None) -> str:
    return re.sub(r"\D", "", v or "")


def to_decimal_string(v: str | None) -> str:
    raw = norm(v)
    if not raw:
        return "0"
    cleaned = re.sub(r"[^\d.]", "", raw)
    return cleaned or "0"


def is_yes(v: str | None) -> bool:
    return norm(v).lower() in {"yes", "y", "paid", "true", "1"}


def is_hold_row(issues: str) -> bool:
    txt = issues.lower()
    return any(k in txt for k in HOLD_KEYWORDS)


def classify_row(row: dict[str, str]) -> RowDecision:
    row_no = norm(row.get("row_no"))
    name = norm(row.get("name"))
    source_order_id = norm(row.get("source_order_id"))
    tracking_id = norm(row.get("tracking_id"))
    issues = norm(row.get("issues")).lower()

    if is_hold_row(issues):
        return RowDecision(row_no, name, "hold", "issue_note_hold_keyword", source_order_id, tracking_id)

    # Numeric order IDs usually indicate known order references from source list.
    if tracking_id:
        return RowDecision(row_no, name, "update", "has_tracking_id", source_order_id, tracking_id)

    if source_order_id.isdigit() and len(source_order_id) >= 6:
        return RowDecision(row_no, name, "update", "has_numeric_source_order_id", source_order_id, tracking_id)

    return RowDecision(row_no, name, "create", "missing_existing_references", source_order_id, tracking_id)


def build_create_payload(row: dict[str, str], default_order_source: str) -> dict:
    name = norm(row.get("name"))
    phone = digits_only(row.get("phone"))
    address = norm(row.get("address"))
    pincode = digits_only(row.get("pincode"))
    cost_str = to_decimal_string(row.get("cost"))
    paid_flag = is_yes(row.get("paid"))
    items_text = norm(row.get("items"))
    issues = norm(row.get("issues"))
    source_order_id = norm(row.get("source_order_id"))
    tracking_id = norm(row.get("tracking_id"))

    # Keep one fallback item so OrderCreate validation passes even for free-form item text.
    item_name = items_text if items_text else "Raw imported item"
    notes_parts = [
        "RAW_INGEST=1",
        f"SOURCE_ROW={norm(row.get('row_no'))}",
        f"SOURCE_ORDER_ID={source_order_id or '-'}",
        f"SOURCE_TRACKING_ID={tracking_id or '-'}",
        f"PAID_FLAG={norm(row.get('paid')) or '-'}",
    ]
    if issues:
        notes_parts.append(f"ISSUES={issues}")

    payload = {
        "customer_name": name,
        "customer_phone": phone,
        "delivery_name": name,
        "delivery_address": address,
        "delivery_pincode": pincode,
        "payment_method": "prepaid" if paid_flag else "cod",
        "items": [
            {
                "product_name": item_name,
                "quantity": "1",
                "unit_price": cost_str,
            }
        ],
        "order_source": default_order_source,
        "notes": " | ".join(notes_parts),
    }

    if is_hold_row(issues.lower()):
        payload["order_intent"] = "not_confirmed"
        payload["not_confirmed_reason"] = issues or "on_hold_from_raw_sheet"
    else:
        payload["order_intent"] = "confirmed"

    return payload


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict]) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main() -> int:
    args = parse_args()

    in_path = Path(args.input)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with in_path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    create_payloads: list[dict] = []
    update_rows: list[dict] = []
    hold_rows: list[dict] = []
    report_rows: list[dict] = []

    for row in rows:
        row_fixed = with_normalized_row(row)
        d = classify_row(row_fixed)

        report_rows.append(
            {
                "row_no": d.row_no,
                "name": d.name,
                "bucket": d.bucket,
                "reason": d.reason,
                "source_order_id": d.source_order_id,
                "tracking_id": d.tracking_id,
            }
        )

        if d.bucket == "hold":
            hold_rows.append(row_fixed)
            continue

        if d.bucket == "update":
            update_rows.append(
                {
                    "customer name": norm(row_fixed.get("name")),
                    "article no": norm(row_fixed.get("tracking_id")),
                    "delivery status": "",
                    "source_order_id": norm(row_fixed.get("source_order_id")),
                    "issues": norm(row_fixed.get("issues")),
                }
            )
            continue

        create_payloads.append(build_create_payload(row_fixed, args.default_order_source))

    write_jsonl(out_dir / "create_orders_api.jsonl", create_payloads)

    write_csv(
        out_dir / "update_tracking_upload.csv",
        ["customer name", "article no", "delivery status", "source_order_id", "issues"],
        update_rows,
    )

    hold_headers = list(rows[0].keys()) if rows else []
    write_csv(out_dir / "hold_rows.csv", hold_headers, hold_rows)

    write_csv(
        out_dir / "ingest_report.csv",
        ["row_no", "name", "bucket", "reason", "source_order_id", "tracking_id"],
        report_rows,
    )

    print(
        json.dumps(
            {
                "input_rows": len(rows),
                "create_rows": len(create_payloads),
                "update_rows": len(update_rows),
                "hold_rows": len(hold_rows),
                "out_dir": str(out_dir),
            },
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
