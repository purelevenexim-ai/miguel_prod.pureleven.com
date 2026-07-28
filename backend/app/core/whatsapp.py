"""
WhatsApp Message Composer
--------------------------
Generates WhatsApp message text for orders.
Two templates:
  - pre_dispatch  : order confirmed, being prepared (no tracking yet)
  - shipped       : order dispatched with tracking number

Returns a dict with `to` (E.164 phone) and `message` (plain text).
The frontend opens:  https://wa.me/{to}?text={encoded_message}
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Optional


# ─────────────────────────────────────────────────────────────
# Phone helpers
# ─────────────────────────────────────────────────────────────

def normalize_phone_e164(phone: str) -> str:
    """
    Convert any Indian phone to E.164 format (91XXXXXXXXXX).
    Accepts: +91XXXXXXXXXX  |  0XXXXXXXXXX  |  XXXXXXXXXX
    Returns empty string if invalid.
    """
    if not phone:
        return ""
    s = re.sub(r"\s+|-", "", str(phone).strip())
    if re.fullmatch(r"\+91\d{10}", s):
        return "91" + s[-10:]
    if re.fullmatch(r"91\d{10}", s):
        return s
    if re.fullmatch(r"0\d{10}", s):
        return "91" + s[-10:]
    if re.fullmatch(r"\d{10}", s):
        return "91" + s
    return ""


def format_phone_display(phone: str) -> str:
    """Return +91 XXXXX XXXXX for display."""
    e = normalize_phone_e164(phone)
    if not e or len(e) < 10:
        return phone
    digits = e[-10:]
    return f"+91 {digits[:5]} {digits[5:]}"


# ─────────────────────────────────────────────────────────────
# Message templates
# ─────────────────────────────────────────────────────────────

def _first_item_summary(items_text: str) -> str:
    """Extract first product line as a short summary."""
    if not items_text:
        return ""
    lines = [ln.strip() for ln in items_text.splitlines() if ln.strip()]
    if not lines:
        return ""
    line = lines[0]
    # strip trailing price portion e.g. " — 2 x Rs 450.00"
    base = re.split(r"\s*[—–-]\s*\d", line)[0].strip()
    return base or line


def compose_pre_dispatch(
    name: str,
    order_number: str,
    items_text: str,
    amount: Optional[str],
    address: str,
    pincode: str,
    payment_type: str,
) -> str:
    item_summary = _first_item_summary(items_text)
    pay_type = str(payment_type or "").strip().lower()
    amt_line = f"Amount (Cash on Delivery): ₹ {amount}" if pay_type == "cod" and amount else (
        f"Amount Paid: ₹ {amount}" if amount else ""
    )

    lines = [
        f"Hello {name},",
        "",
        f"We're carefully preparing your PureLeven Spices order *{order_number}*, "
        "and it will be dispatched within the next 24 hours.",
        "",
    ]
    if item_summary:
        lines.append(f"Item: {item_summary}")
    if amt_line:
        lines.append(amt_line)
    lines += [
        "",
        f"Delivery Address:",
        f"{address}" + (f", PIN {pincode}" if pincode else ""),
        "",
        "If you'd like to make any updates or changes, simply reply to this message.",
        "",
        "Warm regards,",
        "Team PureLeven Spices",
    ]
    return "\n".join(lines)


def compose_shipped(
    name: str,
    order_number: str,
    tracking_number: str,
    courier_name: str,
    items_text: str,
    amount: Optional[str],
    address: str,
    pincode: str,
    payment_type: str,
) -> str:
    pay_type = str(payment_type or "").strip().lower()
    if pay_type == "cod" and amount:
        payment_line = f"Cash on Delivery — Collect ₹{amount}"
    elif amount:
        payment_line = f"Prepaid — Paid ₹{amount}"
    else:
        payment_line = "Prepaid"

    courier = courier_name or "India Post"

    # Build product summary (up to 3 lines)
    prod_lines = [ln.strip() for ln in items_text.splitlines() if ln.strip()][:3]
    products_str = ", ".join(
        re.split(r"\s*[—–-]\s*\d", ln)[0].strip() for ln in prod_lines
    ) if prod_lines else ""

    lines = [
        f"Hello {name},",
        "",
        f"Your PureLeven Spices order *{order_number}* has been shipped via *{courier}*.",
        "",
        f"🔖 Tracking ID: *{tracking_number}*",
        "📦 Estimated Delivery: 4–5 days",
        "",
    ]
    if products_str:
        lines.append(f"Items: {products_str}")
    lines += [
        f"",
        f"Delivery Address:",
        f"{address}" + (f", PIN {pincode}" if pincode else ""),
        "",
        f"Payment: {payment_line}",
        "",
        "Track your shipment:",
        "https://www.indiapost.gov.in/_layouts/15/dop.portal.tracking/trackconsignment.aspx",
    ]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# Main compose function
# ─────────────────────────────────────────────────────────────

def compose_whatsapp_message(
    name: str,
    phone: str,
    order_number: str,
    tracking_number: Optional[str],
    courier_name: Optional[str],
    items_text: str,
    amount: Optional[str],
    address: str,
    pincode: str,
    payment_type: str,
) -> dict:
    """
    Returns:
        {
          "to": "91XXXXXXXXXX",       # E.164 without +
          "phone_display": "+91 ...", # for UI
          "message": "...",           # full WhatsApp text
          "template": "pre_dispatch" | "shipped",
          "wa_url": "https://wa.me/91...?text=..."
        }
    """
    import urllib.parse

    to = normalize_phone_e164(phone)
    template = "shipped" if tracking_number else "pre_dispatch"

    if template == "shipped":
        message = compose_shipped(
            name=name,
            order_number=order_number,
            tracking_number=tracking_number or "",
            courier_name=courier_name or "India Post",
            items_text=items_text,
            amount=amount,
            address=address,
            pincode=pincode,
            payment_type=payment_type,
        )
    else:
        message = compose_pre_dispatch(
            name=name,
            order_number=order_number,
            items_text=items_text,
            amount=amount,
            address=address,
            pincode=pincode,
            payment_type=payment_type,
        )

    wa_url = ""
    if to:
        wa_url = f"https://wa.me/{to}?text={urllib.parse.quote(message)}"

    return {
        "to": to,
        "phone_display": format_phone_display(phone),
        "message": message,
        "template": template,
        "wa_url": wa_url,
    }
