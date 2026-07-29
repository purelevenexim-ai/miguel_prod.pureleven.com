#!/usr/bin/env python3
"""Normalize source CSV rows and map products against Miguel product catalog."""

from __future__ import annotations

import argparse
from contextlib import ExitStack
import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from common import (
    convert_source_order_id_to_miguel,
    dumps_json,
    norm_name,
    normalize_payment,
    normalize_phone,
    parse_items_text,
    parse_source_order_id,
    read_alias_csv,
    score_name_similarity,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Normalize source rows and product-map for Miguel")
    p.add_argument("--input", required=True, help="Raw extracted CSV")
    p.add_argument("--normalized-output", required=True, help="Normalized CSV")
    p.add_argument("--reject-output", required=True, help="Rejected rows CSV")
    p.add_argument("--mapping-report", required=True, help="Product mapping report CSV")
    p.add_argument("--target-db-url", required=True, help="Miguel DB URL for product lookup")
    p.add_argument("--target-tenant-id", required=True, help="Miguel tenant UUID")
    p.add_argument("--target-tenant-slug", required=True, help="Miguel tenant slug")
    p.add_argument("--alias-map", help="Optional CSV: source_name,target_name")
    p.add_argument(
        "--pending-translation-output",
        help="Optional CSV for unmatched source item names to review/translate",
    )
    return p.parse_args()


def parse_created_date(value: str | None) -> str | None:
    raw = (value or "").strip()
    if not raw:
        return None

    normalized = raw.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).date().isoformat()
    except ValueError:
        pass

    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def normalize_order_id(value: str | None) -> str:
    text = (value or "").strip()
    if not text:
        return ""

    text = "".join(text.split())
    if text[:3].upper() == "PUR" and (len(text) == 3 or text[3].isdigit() or text[3] in "_-/"):
        return "PUUR" + text[3:]
    return text


def top_similar_products(src_name: str, products: list[dict[str, Any]], limit: int = 3) -> str:
    scored: list[tuple[float, str]] = []
    for p in products:
        name = str(p.get("name") or "").strip()
        if not name:
            continue
        score = score_name_similarity(src_name, name)
        if score <= 0:
            continue
        scored.append((score, name))

    if not scored:
        return ""

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:limit]
    return "; ".join([f"{name} ({round(score, 4)})" for score, name in top])


def load_products(db_url: str, tenant_id: str) -> list[dict[str, Any]]:
    try:
        from sqlalchemy import create_engine, text
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing dependency 'sqlalchemy'. Install it or run in your backend Python environment."
        ) from exc

    engine = create_engine(db_url)
    sql = text(
        """
        SELECT id, product_code, sku, name, unit, unit_price
        FROM products
        WHERE tenant_id = CAST(:tenant_id AS UUID)
          AND status = 'active'
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"tenant_id": tenant_id}).mappings().all()
    return [dict(r) for r in rows]


def build_maps(products: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    by_sku: dict[str, dict[str, Any]] = {}
    by_code: dict[str, dict[str, Any]] = {}
    by_name: dict[str, dict[str, Any]] = {}
    by_norm: dict[str, dict[str, Any]] = {}
    for p in products:
        if p.get("sku"):
            by_sku[str(p["sku"]).strip().lower()] = p
        if p.get("product_code"):
            by_code[str(p["product_code"]).strip().lower()] = p
        if p.get("name"):
            by_name[str(p["name"]).strip().lower()] = p
            by_norm[norm_name(p["name"])] = p
    return {"by_sku": by_sku, "by_code": by_code, "by_name": by_name, "by_norm": by_norm}


def match_product(
    src_name: str,
    maps: dict[str, dict[str, dict[str, Any]]],
    aliases: dict[str, str],
    products: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, str, float]:
    k = src_name.strip().lower()
    nk = norm_name(src_name)

    if k in maps["by_sku"]:
        return maps["by_sku"][k], "sku", 1.0
    if k in maps["by_code"]:
        return maps["by_code"][k], "product_code", 1.0
    if k in maps["by_name"]:
        return maps["by_name"][k], "exact_name", 1.0
    if nk in maps["by_norm"]:
        return maps["by_norm"][nk], "normalized_name", 0.98

    alias_target = aliases.get(nk)
    if alias_target:
        if alias_target.strip().upper() == "__SKIP__":
            return {"id": None, "name": "__SKIP__", "_skip": True}, "alias_skip", 1.0
        ap = maps["by_name"].get(alias_target.strip().lower()) or maps["by_norm"].get(norm_name(alias_target))
        if ap:
            return ap, "alias_map", 0.97

    best = None
    best_score = 0.0
    for p in products:
        score = score_name_similarity(src_name, str(p.get("name") or ""))
        if score > best_score:
            best = p
            best_score = score

    if best and best_score >= 0.6:
        return best, "token_similarity", round(best_score, 4)
    return None, "unmatched", round(best_score, 4)


def main() -> int:
    args = parse_args()

    products = load_products(args.target_db_url, args.target_tenant_id)
    maps = build_maps(products)
    aliases = read_alias_csv(args.alias_map)

    input_path = Path(args.input)
    normalized_path = Path(args.normalized_output)
    reject_path = Path(args.reject_output)
    report_path = Path(args.mapping_report)
    pending_path = Path(args.pending_translation_output) if args.pending_translation_output else None

    out_paths = [normalized_path, reject_path, report_path]
    if pending_path:
        out_paths.append(pending_path)
    for p in out_paths:
        p.parent.mkdir(parents=True, exist_ok=True)

    normalized_headers = [
        "name",
        "address",
        "pincode",
        "phone",
        "payment_type",
        "amount",
        "source_order_id",
        "source_order_date",
        "source_order_seq",
        "suggested_miguel_order_number",
        "tracking_id",
        "items_raw",
        "items_mapped_json",
        "mapping_confidence_min",
        "mapping_unresolved_count",
        "source_created_ts",
        "migration_notes",
    ]

    reject_headers = ["reason", "order_id", "name", "phone", "raw_row_json"]
    report_headers = [
        "order_id",
        "source_product_name",
        "matched_product_id",
        "matched_product_name",
        "match_method",
        "score",
    ]
    pending_headers = [
        "order_id",
        "source_product_name",
        "customer_name",
        "phone",
        "items_raw",
        "best_suggestions",
        "reason",
    ]

    normalized_count = 0
    reject_count = 0
    report_rows = 0

    with ExitStack() as stack:
        rf = stack.enter_context(input_path.open("r", encoding="utf-8", newline=""))
        nf = stack.enter_context(normalized_path.open("w", encoding="utf-8", newline=""))
        jf = stack.enter_context(reject_path.open("w", encoding="utf-8", newline=""))
        mf = stack.enter_context(report_path.open("w", encoding="utf-8", newline=""))

        pending_writer = None
        if pending_path:
            pf = stack.enter_context(pending_path.open("w", encoding="utf-8", newline=""))
            pending_writer = csv.DictWriter(pf, fieldnames=pending_headers)
            pending_writer.writeheader()

        reader = csv.DictReader(rf)
        n_writer = csv.DictWriter(nf, fieldnames=normalized_headers)
        r_writer = csv.DictWriter(jf, fieldnames=reject_headers)
        m_writer = csv.DictWriter(mf, fieldnames=report_headers)

        n_writer.writeheader()
        r_writer.writeheader()
        m_writer.writeheader()

        for row in reader:
            raw_source_order_id = (row.get("order_id") or "").strip()
            source_order_id = normalize_order_id(raw_source_order_id)
            parsed = parse_source_order_id(source_order_id)
            created_ts = (row.get("created_ts") or "").strip()
            source_notes = (row.get("notes") or "").strip()
            phone_norm = normalize_phone(row.get("phone"))

            # Rows with no source_order_id: use the row's unique _id as the dedup key
            # so the importer can still deduplicate them across runs.
            if not source_order_id:
                row_id = (row.get("_id") or "").strip()
                if row_id:
                    source_order_id = row_id
                    parsed = None  # will fall through to created_ts fallback below
                else:
                    reject_count += 1
                    r_writer.writerow(
                        {
                            "reason": "invalid_source_order_id",
                            "order_id": source_order_id,
                            "name": row.get("name", ""),
                            "phone": row.get("phone", ""),
                            "raw_row_json": dumps_json(row),
                        }
                    )
                    continue

            source_order_date = ""
            source_order_seq: str | int = ""
            suggested_miguel_order_number = ""

            if parsed:
                source_order_date = parsed.iso_date
                source_order_seq = parsed.seq_int
                suggested_miguel_order_number = (
                    convert_source_order_id_to_miguel(source_order_id, args.target_tenant_slug) or ""
                )
            else:
                fallback_date = parse_created_date(created_ts)
                if not fallback_date:
                    reject_count += 1
                    r_writer.writerow(
                        {
                            "reason": "invalid_source_order_id_and_created_ts",
                            "order_id": source_order_id,
                            "name": row.get("name", ""),
                            "phone": row.get("phone", ""),
                            "raw_row_json": dumps_json(row),
                        }
                    )
                    continue
                source_order_date = fallback_date

            if not phone_norm:
                reject_count += 1
                r_writer.writerow(
                    {
                        "reason": "missing_phone",
                        "order_id": source_order_id,
                        "name": row.get("name", ""),
                        "phone": row.get("phone", ""),
                        "raw_row_json": dumps_json(row),
                    }
                )
                continue

            parsed_items = parse_items_text(row.get("items"))
            mapped_items: list[dict[str, Any]] = []
            unresolved = 0
            min_score = 1.0

            for it in parsed_items:
                matched, method, score = match_product(
                    src_name=it.get("source_product_name", ""),
                    maps=maps,
                    aliases=aliases,
                    products=products,
                )
                # skip items explicitly aliased to __SKIP__ (e.g. Delivery Charge)
                if matched and matched.get("_skip"):
                    continue
                min_score = min(min_score, score)
                if not matched:
                    unresolved += 1
                    if pending_writer is not None:
                        pending_writer.writerow(
                            {
                                "order_id": source_order_id,
                                "source_product_name": it.get("source_product_name", ""),
                                "customer_name": row.get("name", ""),
                                "phone": phone_norm,
                                "items_raw": row.get("items") or "",
                                "best_suggestions": top_similar_products(
                                    str(it.get("source_product_name") or ""), products
                                ),
                                "reason": "unmatched_product_name",
                            }
                        )

                mapped = {
                    "source_product_name": it.get("source_product_name"),
                    "quantity": it.get("quantity", 1.0),
                    "unit_price": it.get("unit_price", 0.0),
                    "match_method": method,
                    "match_score": score,
                    "target_product_id": str(matched["id"]) if matched else None,
                    "target_product_name": matched.get("name") if matched else None,
                }
                mapped_items.append(mapped)

                report_rows += 1
                m_writer.writerow(
                    {
                        "order_id": source_order_id,
                        "source_product_name": it.get("source_product_name"),
                        "matched_product_id": mapped["target_product_id"] or "",
                        "matched_product_name": mapped["target_product_name"] or "",
                        "match_method": method,
                        "score": score,
                    }
                )

            n_writer.writerow(
                {
                    "name": row.get("name", "").strip(),
                    "address": row.get("address", "").strip(),
                    "pincode": (row.get("pincode") or "").strip(),
                    "phone": phone_norm,
                    "payment_type": normalize_payment(row.get("payment_type")),
                    "amount": row.get("amount") or "0",
                    "source_order_id": source_order_id,
                    "source_order_date": source_order_date,
                    "source_order_seq": source_order_seq,
                    "suggested_miguel_order_number": suggested_miguel_order_number,
                    "tracking_id": (row.get("tracking_id") or "").strip(),
                    "items_raw": row.get("items") or "",
                    "items_mapped_json": dumps_json(mapped_items),
                    "mapping_confidence_min": round(min_score, 4),
                    "mapping_unresolved_count": unresolved,
                    "source_created_ts": row.get("created_ts") or "",
                    "migration_notes": (
                        f"SOURCE_ORDER_ID={source_order_id}"
                        + (
                            f" | SOURCE_ORDER_ID_ORIGINAL={raw_source_order_id}"
                            if raw_source_order_id and raw_source_order_id != source_order_id
                            else ""
                        )
                        + (" | DATE_FROM_CREATED_TS=1" if not parsed else "")
                        + (f" | SOURCE_CREATED_TS={created_ts}" if created_ts else "")
                        + (f" | {source_notes}" if source_notes else "")
                    ),
                }
            )
            normalized_count += 1

    print(
        "Normalization complete: "
        f"normalized={normalized_count}, rejects={reject_count}, mapping_rows={report_rows}"
    )
    print(f"Normalized CSV: {normalized_path}")
    print(f"Reject CSV:     {reject_path}")
    print(f"Mapping report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
