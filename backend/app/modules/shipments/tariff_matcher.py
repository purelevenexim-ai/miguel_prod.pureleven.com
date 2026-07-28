"""
tariff_matcher.py
─────────────────
Core matching logic that pairs XLSX rows against existing orders.

Matching cascade (in order, first match wins):
  Level 1 (high)   — normalised tracking number matches order.tracking_number
  Level 2 (high)   — xlsx_order_ref matches order.order_number exactly
  Level 3 (medium) — fuzzy customer-name match AND shipping amount within ±30 %
  Level 4 (low)    — delivery pincode match + name token overlap ≥ 1

Returns a list of StagingRow dataclasses ready to be bulk-inserted.

Two validation gates are checked regardless of match level:
  Gate A — tracking format  : must be valid India Post article number
  Gate B — amount sanity    : 5 ≤ x ≤ 5000; and if matched order already has
                              a non-zero shipping_charge, flag suspicious if the
                              proposed value differs by > 100 %.
"""

from __future__ import annotations

import re
import logging
import uuid
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

_IP_TRACKING_RE = re.compile(r'^[A-Z]{2}\d{9}[A-Z]{2}$', re.IGNORECASE)
_AMOUNT_MIN = 5.0
_AMOUNT_MAX = 5000.0
# Configurable threshold for suspicious amount detection.
# 2.0 means: flag when proposed charge is more than 100 % higher (>2× current)
# or more than 50 % lower (<½ current) than the existing order shipping charge.
# Adjust this constant here when business rules change — do NOT scatter magic numbers.
SUSPICIOUS_CHANGE_FACTOR: float = 2.0


# ──────────────────────────────────────────────────────────────────────────────
# Dataclasses
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class XlsxRow:
    """Parsed representation of one XLSX data row."""
    row_num:       int
    tracking:      Optional[str] = None
    order_ref:     Optional[str] = None
    customer_name: Optional[str] = None
    amount:        Optional[float] = None
    weight:        Optional[float] = None
    status_text:   Optional[str] = None
    pincode:       Optional[str] = None   # digits-only 6-digit India pincode


@dataclass
class OrderSnapshot:
    """Minimal order data used for matching."""
    order_id:         uuid.UUID
    order_number:     str
    tracking_number:  Optional[str]
    delivery_name:    Optional[str]
    delivery_pincode: Optional[str]
    shipping_charge:  float


@dataclass
class StagingRow:
    """Corresponds 1-to-1 with a TariffUploadStaging DB row."""
    # source
    xlsx_row_num:      int
    xlsx_tracking:     Optional[str]
    xlsx_order_ref:    Optional[str]
    xlsx_customer_name: Optional[str]
    xlsx_amount:       Optional[float]
    xlsx_weight:       Optional[float]
    xlsx_status_text:  Optional[str]
    # match
    order_id:          Optional[uuid.UUID] = None
    order_number:      Optional[str] = None
    match_method:      Optional[str] = None       # see module docstring
    confidence:        str = "none"               # high | medium | low | none
    # gates
    tracking_valid:    bool = False
    amount_valid:      bool = False
    amount_suspicious: bool = False
    # diff
    current_tracking:  Optional[str] = None
    proposed_tracking: Optional[str] = None
    current_shipping:  Optional[float] = None
    proposed_shipping: Optional[float] = None


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _normalise_tracking(raw: Optional[str]) -> str:
    """Strip separators and uppercase; 'EL 718 896 255 IN' → 'EL718896255IN'."""
    if not raw:
        return ""
    return re.sub(r"[^A-Z0-9]+", "", raw.strip().upper())


def _is_valid_india_post_tracking(normalised: str) -> bool:
    return bool(_IP_TRACKING_RE.match(normalised))


def _normalise_name(name: Optional[str]) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    if not name:
        return ""
    text = name.lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _name_tokens(name: Optional[str]) -> set[str]:
    """Return meaningful words (length ≥ 3) from a name string."""
    return {w for w in _normalise_name(name).split() if len(w) >= 3}


def _fuzzy_name_match(order_name: Optional[str], xlsx_name: Optional[str]) -> bool:
    """
    True if the two names share at least 1 meaningful token AND the longer
    name is ≥ 50 % covered by the shorter name's tokens.
    """
    a = _name_tokens(order_name)
    b = _name_tokens(xlsx_name)
    if not a or not b:
        return False
    overlap = a & b
    if not overlap:
        return False
    coverage = len(overlap) / min(len(a), len(b))
    return coverage >= 0.5


def _amount_within_pct(a: Optional[float], b: Optional[float], pct: float = 0.30) -> bool:
    """True if |a - b| / max(a, b) ≤ pct (both must be positive)."""
    if a is None or b is None or a <= 0 or b <= 0:
        return False
    diff = abs(a - b)
    return diff / max(a, b) <= pct


def _is_amount_suspicious(current: Optional[float], proposed: Optional[float]) -> bool:
    """Flag if proposed differs from an existing non-zero charge by > 100 % (or < 50 %).
    Threshold is controlled by SUSPICIOUS_CHANGE_FACTOR at the top of this module.
    """
    if not current or not proposed:
        return False
    if current <= 0:
        return False
    ratio = proposed / current
    return ratio > SUSPICIOUS_CHANGE_FACTOR or ratio < (1.0 / SUSPICIOUS_CHANGE_FACTOR)


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def match_rows(
    xlsx_rows: list[XlsxRow],
    orders: list[OrderSnapshot],
    mode: str = "tariff",
) -> list[StagingRow]:
    """
    Match every XLSX row against the supplied order snapshots.
    One StagingRow is returned for every XlsxRow (including unmatched rows).

    Parameters
    ----------
    xlsx_rows : parsed rows from the uploaded file
    orders    : pre-loaded order snapshots from the DB (same tenant, open period)
    mode      : "tariff" (full matching) | "tracking" (validate number) | "delivery" (validate status)

    Returns
    -------
    list of StagingRow ready for bulk-insert into tariff_upload_staging
    """
    if mode not in ("tariff", "tracking", "delivery"):
        mode = "tariff"
    staging: list[StagingRow] = []

    # For tracking & delivery modes: simple validation, no matching needed
    if mode in ("tracking", "delivery"):
        for row in xlsx_rows:
            s = StagingRow(
                xlsx_row_num=row.row_num,
                xlsx_tracking=row.tracking,
                xlsx_order_ref=row.order_ref,
                xlsx_customer_name=row.customer_name,
                xlsx_amount=row.amount,
                xlsx_weight=row.weight,
                xlsx_status_text=row.status_text,
            )
            norm_xlsx_tracking = _normalise_tracking(row.tracking)
            s.tracking_valid = _is_valid_india_post_tracking(norm_xlsx_tracking)
            s.proposed_tracking = row.tracking
            s.confidence = "high" if s.tracking_valid else "none"
            s.match_method = "validation_only" if s.tracking_valid else "invalid_tracking"
            staging.append(s)
        logger.info("tracking_delivery_mode: %d rows validated", len(staging))
        return staging

    # For tariff mode: full 4-level matching with amount validation
    # Build fast lookup indices
    tracking_index: dict[str, OrderSnapshot] = {}
    order_ref_index: dict[str, OrderSnapshot] = {}

    for o in orders:
        norm_t = _normalise_tracking(o.tracking_number)
        if norm_t:
            tracking_index[norm_t] = o

        norm_r = (o.order_number or "").strip().lower()
        if norm_r:
            order_ref_index[norm_r] = o

    for row in xlsx_rows:
        s = StagingRow(
            xlsx_row_num=row.row_num,
            xlsx_tracking=row.tracking,
            xlsx_order_ref=row.order_ref,
            xlsx_customer_name=row.customer_name,
            xlsx_amount=row.amount,
            xlsx_weight=row.weight,
            xlsx_status_text=row.status_text,
        )

        # ── Validation gate A: tracking format ──────────────────────────────
        norm_xlsx_tracking = _normalise_tracking(row.tracking)
        s.tracking_valid = _is_valid_india_post_tracking(norm_xlsx_tracking)

        # ── Validation gate B: amount sanity ────────────────────────────────
        if row.amount is not None:
            s.amount_valid = _AMOUNT_MIN <= row.amount <= _AMOUNT_MAX

        # ── Level 1 — tracking exact ─────────────────────────────────────────
        matched: Optional[OrderSnapshot] = None
        method = "unmatched"
        confidence = "none"

        if norm_xlsx_tracking and norm_xlsx_tracking in tracking_index:
            matched = tracking_index[norm_xlsx_tracking]
            method = "tracking_exact"
            confidence = "high"
        
        # ── Level 2 — order number exact ────────────────────────────────────
        if not matched and row.order_ref:
            norm_ref = row.order_ref.strip().lower()
            if norm_ref in order_ref_index:
                matched = order_ref_index[norm_ref]
                method = "order_number_exact"
                confidence = "high"

        # ── Level 3 — name fuzzy + amount close ─────────────────────────────
        if not matched:
            for o in orders:
                if _fuzzy_name_match(o.delivery_name, row.customer_name):
                    if _amount_within_pct(o.shipping_charge, row.amount):
                        matched = o
                        method = "name_amount_close"
                        confidence = "medium"
                        break
            # Fuzzy name matched but amount doesn't fit — still low confidence
            if not matched:
                for o in orders:
                    if _fuzzy_name_match(o.delivery_name, row.customer_name) and row.amount is not None:
                        matched = o
                        method = "name_match_only"
                        confidence = "low"
                        break

        # ── Level 4 — pincode exact match + partial name ─────────────────────
        # Only activates when the XLSX file has a pincode column.
        if not matched and row.pincode and row.customer_name:
            xlsx_tokens = _name_tokens(row.customer_name)
            for o in orders:
                if not o.delivery_pincode:
                    continue
                import re as _re4
                order_pin = _re4.sub(r"[^0-9]", "", str(o.delivery_pincode).strip())
                if order_pin != row.pincode:
                    continue
                if len(xlsx_tokens & _name_tokens(o.delivery_name)) >= 1:
                    matched = o
                    method = "pincode_name_match"
                    confidence = "low"
                    break

        # ── Build staging row ────────────────────────────────────────────────
        if matched:
            s.order_id      = matched.order_id
            s.order_number  = matched.order_number
            s.match_method  = method
            s.confidence    = confidence

            s.current_tracking  = matched.tracking_number
            s.proposed_tracking = row.tracking if row.tracking else matched.tracking_number

            s.current_shipping  = float(matched.shipping_charge) if matched.shipping_charge else None
            s.proposed_shipping = row.amount

            # Amount suspicious gate (only meaningful when matched)
            if s.amount_valid:
                s.amount_suspicious = _is_amount_suspicious(
                    s.current_shipping, s.proposed_shipping
                )
        else:
            s.match_method = "unmatched"
            s.confidence   = "none"

        staging.append(s)

    logger.info(
        "tariff_matcher: %d rows processed — high=%d medium=%d low=%d unmatched=%d",
        len(staging),
        sum(1 for r in staging if r.confidence == "high"),
        sum(1 for r in staging if r.confidence == "medium"),
        sum(1 for r in staging if r.confidence == "low"),
        sum(1 for r in staging if r.confidence == "none"),
    )
    return staging
