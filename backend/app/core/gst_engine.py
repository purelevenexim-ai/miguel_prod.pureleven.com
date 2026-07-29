"""
GST Engine Utilities
---------------------
Financial year calculation (April–March Indian FY).
GST type determination (intra-state vs inter-state).
Tax split logic.
Invoice number generation.
"""
from __future__ import annotations
from datetime import date
from decimal import Decimal, ROUND_HALF_UP


def get_financial_year(d: date | None = None) -> str:
    """
    Return financial year string for a date.
    April–March cycle. e.g. April 2025 → March 2026 = "2025-26"
    """
    if d is None:
        d = date.today()
    if d.month >= 4:
        return f"{d.year}-{str(d.year + 1)[2:]}"
    else:
        return f"{d.year - 1}-{str(d.year)[2:]}"


def is_intra_state(customer_state: str | None, supply_state: str | None) -> bool:
    """True if both states are provided and match (case-insensitive)."""
    if not customer_state or not supply_state:
        return False
    return customer_state.strip().lower() == supply_state.strip().lower()


def split_gst(tax_percent: Decimal, intra: bool) -> tuple[Decimal, Decimal, Decimal]:
    """
    Returns (cgst_percent, sgst_percent, igst_percent).
    Intra-state: split equally into CGST + SGST.
    Inter-state: full rate as IGST.
    """
    half = (tax_percent / Decimal("2")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if intra:
        return half, half, Decimal("0")
    else:
        return Decimal("0"), Decimal("0"), tax_percent


def calc_gst_amounts(
    taxable_amount: Decimal,
    cgst_percent: Decimal,
    sgst_percent: Decimal,
    igst_percent: Decimal,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """
    Returns (cgst_amount, sgst_amount, igst_amount, total_tax).
    All rounded to 2 decimal places.
    """
    r = Decimal("0.01")
    cgst = (taxable_amount * cgst_percent / Decimal("100")).quantize(r, ROUND_HALF_UP)
    sgst = (taxable_amount * sgst_percent / Decimal("100")).quantize(r, ROUND_HALF_UP)
    igst = (taxable_amount * igst_percent / Decimal("100")).quantize(r, ROUND_HALF_UP)
    return cgst, sgst, igst, cgst + sgst + igst
