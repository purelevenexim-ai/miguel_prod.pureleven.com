#!/usr/bin/env python3
"""Shared helpers for source-to-Miguel migration."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

ORDER_ID_RE = re.compile(r"^([A-Za-z]{2,5})_(\d{2})(\d{2})(\d{2})(\d+)$")
# Pure-numeric XLSX IDs: YYMMDDNN[N] — no letter prefix, 7-9 digits
NUMERIC_ORDER_ID_RE = re.compile(r"^(\d{2})(\d{2})(\d{2})(\d{1,3})$")
ITEM_LINE_RE = re.compile(
    r"^\s*(?P<name>.+?)\s*[\u2014\-]\s*(?P<qty>\d+(?:\.\d+)?)\s*x\s*Rs\s*(?P<price>\d+(?:\.\d+)?)\s*$",
    flags=re.IGNORECASE,
)


@dataclass
class ParsedOrderId:
    source_prefix: str
    yy: str
    mm: str
    dd: str
    seq: str

    @property
    def yymmdd(self) -> str:
        return f"{self.yy}{self.mm}{self.dd}"

    @property
    def iso_date(self) -> str:
        year = 2000 + int(self.yy)
        return datetime(year, int(self.mm), int(self.dd)).date().isoformat()

    @property
    def seq_int(self) -> int:
        return int(self.seq)

    @property
    def seq_padded(self) -> str:
        return str(self.seq_int).zfill(3)


def parse_source_order_id(value: str | None) -> ParsedOrderId | None:
    raw = (value or "").strip()
    m = ORDER_ID_RE.match(raw)
    if not m:
        # Try the pure-numeric XLSX format: YYMMDDNN[N]
        m2 = NUMERIC_ORDER_ID_RE.match(raw)
        if m2:
            p = ParsedOrderId(
                source_prefix="XLSX",
                yy=m2.group(1),
                mm=m2.group(2),
                dd=m2.group(3),
                seq=m2.group(4),
            )
            try:
                _ = p.iso_date
            except ValueError:
                return None
            return p
        return None
    p = ParsedOrderId(
        source_prefix=m.group(1).upper(),
        yy=m.group(2),
        mm=m.group(3),
        dd=m.group(4),
        seq=m.group(5),
    )
    try:
        _ = p.iso_date
    except ValueError:
        return None
    return p


def tenant_prefix_from_slug(slug: str | None) -> str:
    s = re.sub(r"[^A-Za-z0-9]", "", (slug or "").upper())
    if not s:
        return "ORD"
    consonants = re.sub(r"[AEIOU0-9]", "", s)
    if len(consonants) >= 3:
        return consonants[0] + consonants[1] + consonants[-1]
    if len(s) >= 3:
        return s[:3]
    return s.ljust(3, "X")


def convert_source_order_id_to_miguel(source_order_id: str, tenant_slug: str) -> str | None:
    parsed = parse_source_order_id(source_order_id)
    if not parsed:
        return None
    return f"{tenant_prefix_from_slug(tenant_slug)}-{parsed.yymmdd}-{parsed.seq_padded}"


def normalize_phone(value: str | None) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 12 and digits.startswith("91"):
        return digits[2:]
    return digits


def normalize_payment(value: str | None) -> str:
    raw = (value or "").strip().lower()
    if raw in {"cod", "cash on delivery", "cash_on_delivery"}:
        return "cod"
    if raw in {"prepaid", "online", "upi", "card", "bank"}:
        return "upi"
    if raw in {"cash"}:
        return "cash"
    return "cod"


def norm_name(value: str | None) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"\s+", " ", text)
    return text


def tokenize(value: str | None) -> set[str]:
    text = norm_name(value)
    parts = re.findall(r"[a-z0-9]+", text)
    return {p for p in parts if len(p) >= 2}


def score_name_similarity(a: str, b: str) -> float:
    ta = tokenize(a)
    tb = tokenize(b)
    if not ta or not tb:
        return 0.0
    overlap = len(ta & tb)
    return overlap / max(1, min(len(ta), len(tb)))


def parse_items_text(items_text: str | None) -> list[dict[str, Any]]:
    lines = [ln.strip() for ln in (items_text or "").splitlines() if ln.strip()]
    out: list[dict[str, Any]] = []
    for line in lines:
        m = ITEM_LINE_RE.match(line)
        if m:
            out.append(
                {
                    "source_line": line,
                    "source_product_name": m.group("name").strip(),
                    "quantity": float(m.group("qty")),
                    "unit_price": float(m.group("price")),
                }
            )
            continue

        # Fallback parser for irregular rows.
        chunks = [c.strip() for c in re.split(r"[\u2014\-]", line, maxsplit=1)]
        name = chunks[0] if chunks else line
        out.append(
            {
                "source_line": line,
                "source_product_name": name,
                "quantity": 1.0,
                "unit_price": 0.0,
                "needs_review": True,
            }
        )
    return out


def read_alias_csv(path: str | None) -> dict[str, str]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Alias map not found: {path}")

    out: dict[str, str] = {}
    with p.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            src = norm_name(row.get("source_name"))
            dst = (row.get("target_name") or "").strip()
            if src and dst:
                out[src] = dst
    return out


def dumps_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
