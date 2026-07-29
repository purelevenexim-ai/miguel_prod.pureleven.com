"""
Label PDF Generator — Modern & Minimal
--------------------------------------
4x6 inch shipping labels with clean design.
Helvetica font, centered alignment, balanced spacing.
"""

from __future__ import annotations

import io
import textwrap
import base64
import re

from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.utils import ImageReader

# ── Fonts ──────────────────────────────────────────────────────
FONT_NORMAL = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

# ── Font sizes (THERMAL PRINTER OPTIMIZED) ────────────────────
# Increased significantly for readability on 4x6 thermal labels
FS_COMPANY   = 13
FS_ORDER_NUM = 11
FS_BADGE     = 12
FS_AMOUNT    = 16
FS_NAME      = 15
FS_ADDRESS   = 9
FS_CITY      = 9
FS_LABEL     = 9
FS_ITEMS     = 8
FS_TOTAL     = 13
FS_FOOTER    = 7

# ── Line heights (tighter for thermal, more content) ────────────
LH    = 15  # Adjusted for larger fonts
LH_SM = 12  # Adjusted for larger fonts

# ── Label dimensions ───────────────────────────────────────────
LABEL_W = 4.0 * inch
LABEL_H = 6.0 * inch
PAGE_SIZE = (LABEL_W, LABEL_H)

# ── Colours ────────────────────────────────────────────────────
C_BLACK       = HexColor("#000000")
C_DARK_GRAY   = HexColor("#333333")
C_MED_GRAY    = HexColor("#666666")
C_LIGHT_GRAY  = HexColor("#aaaaaa")
C_BORDER      = HexColor("#e0e0e0")
C_BG_LIGHT    = HexColor("#f8f8f8")
C_BG_FROM     = HexColor("#f5f5f5")
C_COD_RED     = HexColor("#dc2626")
C_COD_BG      = HexColor("#fef2f2")
C_COD_BORDER  = HexColor("#fecaca")
C_PREPAID_GRN = HexColor("#16a34a")
C_PREPAID_BG  = HexColor("#f0fdf4")
C_PREPAID_BDR = HexColor("#bbf7d0")


# ── Helpers ────────────────────────────────────────────────────

def _wrap(text: str, width_chars: int = 40) -> list:
    if not text:
        return []
    lines = []
    for para in str(text).splitlines():
        para = para.strip()
        if not para:
            continue
        wrapped = textwrap.wrap(para, width=width_chars)
        lines.extend(wrapped if wrapped else [])
    return lines


def _fit_text(c, text: str, max_width: float, font_name: str, font_size: float) -> str:
    text = str(text or "").strip()
    if not text or c.stringWidth(text, font_name, font_size) <= max_width:
        return text
    suffix = "..."
    fitted = text
    while fitted and c.stringWidth(fitted + suffix, font_name, font_size) > max_width:
        fitted = fitted[:-1].rstrip()
    return (fitted + suffix) if fitted else suffix


def _draw_fitted(c, text: str, x: float, y: float, max_width: float, font_name: str, font_size: float):
    c.setFont(font_name, font_size)
    c.drawString(x, y, _fit_text(c, text, max_width, font_name, font_size))


def _fmt_phone(v: str) -> str:
    if not v:
        return ""
    digits = (v.replace(" ", "").replace("+", "")
               .replace("-", "").replace("(", "").replace(")", ""))
    # Strip Indian country code (91XXXXXXXXXX → 10 digits)
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    if len(digits) == 10:
        return digits
    return v


def _clean_address_text(v: str) -> str:
    """Remove noisy trailing phrases and normalize spacing for label output."""
    if not v:
        return ""
    text = str(v).strip()
    text = re.sub(r",?\s*phone\s*number\.?$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s{2,}", " ", text)
    # Remove repeated consecutive comma-separated segments, e.g. "Adimali, Adimali".
    parts = [p.strip() for p in text.split(",") if p.strip()]
    dedup_parts = []
    for p in parts:
        if not dedup_parts or dedup_parts[-1].casefold() != p.casefold():
            dedup_parts.append(p)
    return ", ".join(dedup_parts).strip(" ,")


def _try_load_logo(logo_url: str, max_w=20, max_h=16):
    if not logo_url:
        return None
    try:
        if logo_url.startswith("data:"):
            _, b64data = logo_url.split(",", 1)
            img = ImageReader(io.BytesIO(base64.b64decode(b64data)))
        else:
            img = ImageReader(logo_url)
        iw, ih = img.getSize()
        if iw <= 0 or ih <= 0:
            return None
        ratio = min(max_w / iw, max_h / ih)
        return img, iw * ratio, ih * ratio
    except Exception:
        return None


def _box(c, x, y, w, h, r=4, fill=None, stroke=None, lw=1):
    """Draw a rounded box."""
    c.saveState()
    c.setLineWidth(lw)
    c.setStrokeColor(stroke or C_BORDER)
    c.setFillColor(fill or white)
    c.roundRect(x, y, w, h, r, stroke=1 if stroke else 0, fill=1 if fill else 0)
    c.restoreState()


def _line(c, x1, x2, y, color=None, lw=0.8):
    """Draw a horizontal line."""
    c.saveState()
    c.setStrokeColor(color or C_BORDER)
    c.setLineWidth(lw)
    c.line(x1, y, x2, y)
    c.restoreState()


# ── Main label drawing ─────────────────────────────────────────

def draw_label(c, data):
    """Draw a thermal-printer-optimized 4x6 shipping label with improved readability."""

    # Page setup with optimized padding for thermal printers
    PAD = 8  # Reduced from 12 to maximize usable space
    LX = PAD
    RX = LABEL_W - PAD
    CX = LABEL_W / 2
    CW = RX - LX  # Content width
    DETAIL_X = LX + 14  # Indent name/address content from section labels

    # Fixed bottom zones to prevent overlap on long-content labels.
    TOTAL_RULE_Y = 52
    TOTAL_TEXT_Y = 39
    FOOTER_RULE_Y = 34
    FOOTER_TITLE_Y = 24
    FOOTER_SUBTITLE_Y = 12
    
    y = LABEL_H - 12  # Reduced top margin

    # ═══════════════════════════════════════════════════════════
    # HEADER SECTION
    # ═══════════════════════════════════════════════════════════
    
    brand        = str(data.get("from_name", "pureleven")).strip() or "pureleven"
    order_number = str(data.get("order_number", "")).strip()

    # Logo + Brand (centered)
    logo_result = _try_load_logo(str(data.get("logo_url", "")))
    logo_x = LX
    
    if logo_result:
        img, iw, ih = logo_result
        try:
            logo_y = y - 22
            c.drawImage(img, LX, logo_y, width=iw, height=ih, mask="auto")
            logo_x = LX + iw + 6
        except Exception:
            pass

    c.setFont(FONT_BOLD, FS_COMPANY)
    c.setFillColor(C_BLACK)
    c.drawString(logo_x, y - 16, brand)

    # Order number right-aligned
    if order_number:
        c.setFont(FONT_NORMAL, FS_ORDER_NUM)
        c.setFillColor(C_MED_GRAY)
        c.drawRightString(RX, y - 16, f"#{order_number}")

    y -= 36  # Space after header

    # ═══════════════════════════════════════════════════════════
    # STATUS & CONTRACT ID ROW (THERMAL OPTIMIZED — LARGER AMOUNT)
    # ═══════════════════════════════════════════════════════════
    
    payment_type   = str(data.get("payment_type", "")).strip().lower()
    amount         = str(data.get("amount", "")).strip()
    advance_paid   = str(data.get("advance_paid", "")).strip()
    india_post_cid = str(data.get("india_post_customer_id", "")).strip()

    is_cod         = payment_type == "cod"
    is_partial_cod = payment_type == "partial cod"
    is_collect     = is_cod or is_partial_cod

    # Determine badge and amount to show
    if is_partial_cod:
        badge_text, badge_color, badge_bg, badge_bdr = "PART COD", C_COD_RED, C_COD_BG, C_COD_BORDER
        # For partial COD, show the balance due (amount - advance_paid)
        try:
            amt_val = float(amount) if amount else 0
            adv_val = float(advance_paid) if advance_paid else 0
            badge_amount = amt_val - adv_val
        except:
            badge_amount = 0
    elif is_cod:
        badge_text, badge_color, badge_bg, badge_bdr = "COD", C_COD_RED, C_COD_BG, C_COD_BORDER
        # For COD, show the full amount
        try:
            badge_amount = float(amount) if amount else 0
        except:
            badge_amount = 0
    else:
        badge_text, badge_color, badge_bg, badge_bdr = "PREPAID", C_PREPAID_GRN, C_PREPAID_BG, C_PREPAID_BDR
        badge_amount = 0

    # Layout: [Contract ID box] [Payment Badge] or [Payment Badge]
    total_row_w = CW
    
    if india_post_cid:
        contract_w = 100
        badge_w = 84
        space = total_row_w - contract_w - badge_w - 8
        
        contract_x = LX
        badge_x = contract_x + contract_w + space
        
        # Contract ID box
        _box(c, contract_x, y - 28, contract_w, 28, 3, fill=white, stroke=C_BORDER, lw=1.2)
        c.setFont(FONT_NORMAL, FS_LABEL)
        c.setFillColor(C_DARK_GRAY)
        c.drawString(contract_x + 6, y - 9, "Contract ID")
        c.setFont(FONT_BOLD, 12)
        c.setFillColor(C_BLACK)
        c.drawString(contract_x + 6, y - 22, india_post_cid)
    else:
        badge_x = RX - 85

    # Payment badge — LARGER for thermal readability
    badge_w = 84
    badge_h = 30 if badge_amount == 0 else 46
    _box(c, badge_x, y - badge_h, badge_w, badge_h, 3, fill=badge_bg, stroke=badge_bdr, lw=2)
    
    # Badge text (top)
    c.setFont(FONT_BOLD, FS_BADGE)
    c.setFillColor(badge_color)
    badge_text_y = y - 17 if badge_amount == 0 else y - 13
    c.drawCentredString(badge_x + badge_w / 2, badge_text_y, badge_text)
    
    # Badge amount (bottom, only for COD and PARTIAL COD) — MUCH LARGER
    if badge_amount > 0:
        c.setFont(FONT_BOLD, FS_AMOUNT)  # 18pt for excellent visibility
        c.setFillColor(badge_color)
        amount_str = f"{badge_amount:.2f}".rstrip('0').rstrip('.')
        c.drawCentredString(badge_x + badge_w / 2, y - 32, f"Rs.{amount_str}")

    y -= max(36, badge_h + 6)

    # ═══════════════════════════════════════════════════════════
    # RECIPIENT SECTION (SHIP TO) — THERMAL OPTIMIZED
    # ═══════════════════════════════════════════════════════════
    
    y -= 6  # Section margin
    c.setFont(FONT_NORMAL, FS_LABEL)
    c.setFillColor(C_DARK_GRAY)  # Changed from C_LIGHT_GRAY for readability
    c.drawString(LX, y, "SHIP TO")
    y -= 10

    # Recipient name — larger and bolder
    name = str(data.get("name", "")).strip()
    if name:
        c.setFillColor(C_BLACK)
        _draw_fitted(c, name, DETAIL_X, y, RX - DETAIL_X, FONT_BOLD, FS_NAME)
        y -= 16

    # Address — proper line spacing for readability on thermal
    addr_text = _clean_address_text(str(data.get("address", "")))
    addr_lines = _wrap(addr_text, width_chars=38)
    c.setFont(FONT_NORMAL, FS_ADDRESS)
    c.setFillColor(C_BLACK)  # Changed from C_DARK_GRAY for better contrast
    for ln in addr_lines[:2]:
        _draw_fitted(c, ln, DETAIL_X, y, RX - DETAIL_X, FONT_NORMAL, FS_ADDRESS)
        y -= 11

    # City, State
    city_parts = [p for p in [data.get("city", ""), data.get("state", "")] if str(p).strip()]
    if city_parts:
        y -= 2
        c.setFont(FONT_NORMAL, FS_CITY)
        c.setFillColor(C_BLACK)
        _draw_fitted(c, ", ".join(city_parts), DETAIL_X, y, RX - DETAIL_X, FONT_NORMAL, FS_CITY)
        y -= 10

    # PIN
    pincode = str(data.get("pincode", "")).strip()
    if pincode:
        y -= 2
        c.setFont(FONT_BOLD, FS_CITY)  # Bold for emphasis
        c.setFillColor(C_BLACK)
        c.drawString(DETAIL_X, y, f"PIN: {pincode}")
        y -= 10

    # Phone
    phone = _fmt_phone(str(data.get("phone", "")).strip())
    if phone:
        c.setFont(FONT_NORMAL, FS_CITY)
        c.setFillColor(C_DARK_GRAY)
        c.drawString(DETAIL_X, y, f"Ph: {phone}")
        y -= 10

    y -= 5
    _line(c, LX, RX, y, color=C_BORDER, lw=0.6)
    y -= 6

    # ═══════════════════════════════════════════════════════════
    # FROM SECTION — SIMPLIFIED FOR THERMAL
    # ═══════════════════════════════════════════════════════════
    
    from_name    = str(data.get("from_name",    "")).strip()
    from_address = _clean_address_text(str(data.get("from_address", "")).strip())
    from_pincode = str(data.get("from_pincode", "")).strip()
    from_phone   = _fmt_phone(str(data.get("from_phone", "")).strip())

    y -= 5
    c.setFont(FONT_NORMAL, FS_LABEL)
    c.setFillColor(C_DARK_GRAY)
    c.drawString(LX, y, "FROM")
    y -= 10
    
    c.setFont(FONT_BOLD, 10)
    c.setFillColor(C_BLACK)
    _draw_fitted(c, from_name, DETAIL_X, y, RX - DETAIL_X, FONT_BOLD, 10)
    y -= 11

    c.setFont(FONT_NORMAL, FS_ADDRESS)
    c.setFillColor(C_DARK_GRAY)
    if from_address:
        _draw_fitted(c, from_address, DETAIL_X, y, RX - DETAIL_X, FONT_NORMAL, FS_ADDRESS)
        y -= 10
    
    if from_pincode:
        c.drawString(DETAIL_X, y, f"PIN: {from_pincode}")
        y -= 10
    
    if from_phone:
        c.drawString(DETAIL_X, y, f"Ph: {from_phone}")
        y -= 10

    y -= 5

    # ═══════════════════════════════════════════════════════════
    # ITEMS SECTION — fit up to six product lines on the label.
    # ═══════════════════════════════════════════════════════════
    
    items_text = str(data.get("items_text", "")).strip()
    if items_text and y > (TOTAL_RULE_Y + 16):
        y -= 4
        c.setFont(FONT_NORMAL, FS_LABEL)
        c.setFillColor(C_DARK_GRAY)
        c.drawString(LX, y, "ITEMS")
        y -= 9

        item_lines = [l.strip() for l in items_text.splitlines() if l.strip()]
        visible_count = min(len(item_lines), 6)
        if visible_count > 0:
            available_h = max(0, y - (TOTAL_RULE_Y + 4))
            line_h = 11 if visible_count <= 2 else 9
            if available_h and available_h < visible_count * line_h:
                line_h = max(6.5, available_h / visible_count)
            item_font = FS_ITEMS if visible_count <= 2 else min(FS_ITEMS, max(6.0, line_h - 1.0))
            c.setFillColor(C_BLACK)
            max_item_w = RX - (LX + 8)
            for idx, item in enumerate(item_lines[:visible_count]):
                extra = ""
                if idx == visible_count - 1 and len(item_lines) > visible_count:
                    extra = f" +{len(item_lines) - visible_count} more"
                _draw_fitted(c, f"• {item}{extra}", LX + 4, y, max_item_w, FONT_NORMAL, item_font)
                y -= line_h

        y -= 4

    # ═══════════════════════════════════════════════════════════
    # TOTAL SECTION
    # ═══════════════════════════════════════════════════════════
    
    final_amount = str(data.get("final_amount", "")).strip()
    if final_amount:
        _line(c, LX, RX, TOTAL_RULE_Y, color=C_BORDER, lw=0.6)
        c.setFont(FONT_BOLD, FS_TOTAL)
        c.setFillColor(C_BLACK)
        c.drawString(LX, TOTAL_TEXT_Y, "Total")
        c.drawRightString(RX, TOTAL_TEXT_Y, f"Rs.{final_amount}")

    # ═══════════════════════════════════════════════════════════
    # FOOTER SECTION — THERMAL OPTIMIZED
    # ═══════════════════════════════════════════════════════════
    
    tracking = str(data.get("tracking_number", "")).strip()

    if not tracking:
        _line(c, LX, RX, FOOTER_RULE_Y, color=C_BORDER, lw=0.6)
        c.setFont(FONT_BOLD, 10)
        c.setFillColor(C_BLACK)
        c.drawCentredString(CX, FOOTER_TITLE_Y, "No.1 Spices Online Store (Premium)")
        c.setFont(FONT_NORMAL, FS_FOOTER)
        c.setFillColor(C_MED_GRAY)
        c.drawCentredString(CX, FOOTER_SUBTITLE_Y, "Purchase Original Kerala Spices from www.pureleven.com")

    # Tracking box at bottom — LARGER for thermal visibility
    if tracking:
        TRACK_H = 24
        TRACK_Y = PAD + 1
        _box(c, LX - 1, TRACK_Y, CW + 2, TRACK_H, 3, fill=C_BG_LIGHT)
        c.setFont(FONT_NORMAL, FS_LABEL)
        c.setFillColor(C_DARK_GRAY)
        c.drawString(LX + 3, TRACK_Y + 9, "TRACKING")
        c.setFont(FONT_BOLD, 13)  # Larger tracking number
        c.setFillColor(C_BLACK)
        c.drawRightString(RX - 3, TRACK_Y + 9, tracking)


def build_labels_pdf(label_data_list):
    """Build multi-page PDF: one 4x6 label per page."""
    bio = io.BytesIO()
    cv  = canvas.Canvas(bio, pagesize=PAGE_SIZE)
    for data in label_data_list:
        draw_label(cv, data)
        cv.showPage()
    cv.save()
    bio.seek(0)
    return bio.read()
