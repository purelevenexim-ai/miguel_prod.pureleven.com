"""
GST Accounting Service
-----------------------
Computes GSTR-1, HSN Summary, Tax Summary and CSV exports
from the existing Orders + OrderItems + Products data.

GST Logic:
  - If order.delivery_state == tenant.gst_state  →  CGST + SGST (intra-state)
  - Else                                          →  IGST only   (inter-state)

All monetary values are Decimal, rounded to 2dp.
All queries are strictly tenant-scoped.
"""

from __future__ import annotations

import csv
import io
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.tenant import Tenant


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _d(v) -> Decimal:
    """Safe Decimal conversion."""
    if v is None:
        return Decimal("0")
    return Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _round2(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _fmt(v: Decimal) -> str:
    return str(_round2(v))


def _get_tenant(db: Session, tenant_id) -> Optional[Tenant]:
    return db.query(Tenant).filter(Tenant.id == tenant_id).first()


def _orders_in_period(
    db: Session,
    tenant_id,
    date_from: date,
    date_to: date,
    state_filter: Optional[str] = None,
    b2b_filter: Optional[str] = None,   # 'b2b' | 'b2c' | None
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
) -> List[Order]:
    """
    Return confirmed/delivered orders for the period, tenant-scoped.
    Excludes draft and cancelled orders.
    """
    q = db.query(Order).filter(
        Order.tenant_id == tenant_id,
        Order.is_active == True,
        Order.status.notin_([OrderStatus.draft, OrderStatus.cancelled]),
        Order.gst_invoice == True,
        Order.created_at >= datetime.combine(date_from, datetime.min.time()),
        Order.created_at <= datetime.combine(date_to, datetime.max.time()),
    )
    if state_filter:
        q = q.filter(Order.delivery_state.ilike(f"%{state_filter}%"))
    if min_amount is not None:
        q = q.filter(Order.total_amount >= min_amount)
    if max_amount is not None:
        q = q.filter(Order.total_amount <= max_amount)

    orders = q.order_by(Order.created_at.asc()).all()

    # B2B / B2C filter (based on customer.gstin)
    if b2b_filter == 'b2b':
        orders = [o for o in orders if o.customer and o.customer.gstin]
    elif b2b_filter == 'b2c':
        orders = [o for o in orders if not (o.customer and o.customer.gstin)]

    return orders


def _build_sku_product_map(db: Session, tenant_id, skus: set) -> dict:
    """Map sku → Product for HSN/rate lookup."""
    if not skus:
        return {}
    prods = db.query(Product).filter(
        Product.tenant_id == tenant_id,
        Product.sku.in_(skus),
    ).all()
    return {p.sku: p for p in prods}


def _calc_gst(
    line_total: Decimal,
    gst_rate: Decimal,
    is_intra: bool,
):
    """
    Compute CGST/SGST/IGST from a line_total (ex-GST amount).
    Returns (taxable, cgst, sgst, igst, total_with_gst).
    """
    taxable = line_total
    gst_amount = _round2(taxable * gst_rate / 100)
    if is_intra:
        half = _round2(gst_amount / 2)
        cgst = half
        sgst = gst_amount - half   # handles odd paise
        igst = Decimal("0")
    else:
        cgst = Decimal("0")
        sgst = Decimal("0")
        igst = gst_amount
    total = taxable + gst_amount
    return taxable, cgst, sgst, igst, total


# ─────────────────────────────────────────────────────────────
# GSTR-1 Detailed
# ─────────────────────────────────────────────────────────────

def get_gstr1(
    db: Session,
    current_user,
    date_from: date,
    date_to: date,
    state_filter: Optional[str] = None,
    b2b_filter: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
) -> dict:
    tenant = _get_tenant(db, current_user.tenant_id)
    tenant_state = (tenant.gst_state or "").strip().lower() if tenant else ""

    orders = _orders_in_period(
        db, current_user.tenant_id, date_from, date_to,
        state_filter, b2b_filter, min_amount, max_amount,
    )

    # Collect all SKUs for product lookup
    all_skus = {item.sku for o in orders for item in o.items if item.sku}
    prod_map = _build_sku_product_map(db, current_user.tenant_id, all_skus)

    rows = []
    summary = {
        "total_taxable": Decimal("0"),
        "total_cgst":    Decimal("0"),
        "total_sgst":    Decimal("0"),
        "total_igst":    Decimal("0"),
        "total_invoice": Decimal("0"),
        "order_count":   0,
    }

    for order in orders:
        cust = order.customer
        cust_name  = (cust.name if cust else None) or order.delivery_name or "—"
        cust_gstin = (cust.gstin if cust else None) or ""
        cust_state = (order.delivery_state or "").strip()
        is_intra   = cust_state.lower() == tenant_state if tenant_state else False
        order_date = order.created_at.strftime("%d-%m-%Y") if order.created_at else "—"

        for item in order.items:
            prod = prod_map.get(item.sku) if item.sku else None
            hsn  = (prod.hsn_code if prod else None) or ""
            rate = _d(prod.gst_rate if prod else None)
            taxable = _d(item.line_total)
            taxable_val, cgst, sgst, igst, total = _calc_gst(taxable, rate, is_intra)

            rows.append({
                "invoice_number": order.order_number,
                "invoice_date":   order_date,
                "customer_name":  cust_name,
                "customer_gstin": cust_gstin,
                "place_of_supply": cust_state or "—",
                "hsn_code":       hsn,
                "product_name":   item.product_name,
                "quantity":       str(item.quantity),
                "unit":           item.unit.value if item.unit else "piece",
                "taxable_value":  _fmt(taxable_val),
                "gst_rate":       _fmt(rate),
                "cgst":           _fmt(cgst),
                "sgst":           _fmt(sgst),
                "igst":           _fmt(igst),
                "total_value":    _fmt(total),
                "payment_method": order.payment_method.value if order.payment_method else "—",
                "order_status":   order.status.value,
                "b2b_b2c":        "B2B" if cust_gstin else "B2C",
            })
            summary["total_taxable"] += taxable_val
            summary["total_cgst"]    += cgst
            summary["total_sgst"]    += sgst
            summary["total_igst"]    += igst
            summary["total_invoice"] += total

        summary["order_count"] += 1

    return {
        "rows": rows,
        "summary": {
            "total_taxable": _fmt(summary["total_taxable"]),
            "total_cgst":    _fmt(summary["total_cgst"]),
            "total_sgst":    _fmt(summary["total_sgst"]),
            "total_igst":    _fmt(summary["total_igst"]),
            "total_invoice": _fmt(summary["total_invoice"]),
            "order_count":   summary["order_count"],
        },
        "tenant_state": tenant.gst_state if tenant else None,
        "tenant_gstin": tenant.gstin if tenant else None,
    }


# ─────────────────────────────────────────────────────────────
# HSN Summary
# ─────────────────────────────────────────────────────────────

def get_hsn_summary(
    db: Session,
    current_user,
    date_from: date,
    date_to: date,
    state_filter: Optional[str] = None,
    b2b_filter: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
) -> dict:
    tenant = _get_tenant(db, current_user.tenant_id)
    tenant_state = (tenant.gst_state or "").strip().lower() if tenant else ""

    orders = _orders_in_period(
        db, current_user.tenant_id, date_from, date_to,
        state_filter, b2b_filter, min_amount, max_amount,
    )

    all_skus = {item.sku for o in orders for item in o.items if item.sku}
    prod_map = _build_sku_product_map(db, current_user.tenant_id, all_skus)

    # Group by (hsn_code, gst_rate)
    hsn_map: dict = {}
    for order in orders:
        cust_state = (order.delivery_state or "").strip()
        is_intra = cust_state.lower() == tenant_state if tenant_state else False

        for item in order.items:
            prod = prod_map.get(item.sku) if item.sku else None
            hsn  = (prod.hsn_code if prod else None) or "—"
            rate = _d(prod.gst_rate if prod else None)
            desc = (prod.name if prod else None) or item.product_name
            taxable = _d(item.line_total)
            _, cgst, sgst, igst, total = _calc_gst(taxable, rate, is_intra)

            key = (hsn, str(rate))
            if key not in hsn_map:
                hsn_map[key] = {
                    "hsn_code":    hsn,
                    "description": desc,
                    "gst_rate":    _fmt(rate),
                    "total_qty":   Decimal("0"),
                    "taxable":     Decimal("0"),
                    "cgst":        Decimal("0"),
                    "sgst":        Decimal("0"),
                    "igst":        Decimal("0"),
                    "total":       Decimal("0"),
                }
            h = hsn_map[key]
            h["total_qty"] += _d(item.quantity)
            h["taxable"]   += taxable
            h["cgst"]      += cgst
            h["sgst"]      += sgst
            h["igst"]      += igst
            h["total"]     += total

    rows = []
    for h in sorted(hsn_map.values(), key=lambda x: x["hsn_code"]):
        rows.append({
            "hsn_code":    h["hsn_code"],
            "description": h["description"],
            "gst_rate":    h["gst_rate"],
            "total_qty":   str(h["total_qty"]),
            "taxable":     _fmt(h["taxable"]),
            "cgst":        _fmt(h["cgst"]),
            "sgst":        _fmt(h["sgst"]),
            "igst":        _fmt(h["igst"]),
            "total":       _fmt(h["total"]),
        })

    return {"rows": rows}


# ─────────────────────────────────────────────────────────────
# Tax Summary (for GSTR-3B)
# ─────────────────────────────────────────────────────────────

def get_tax_summary(
    db: Session,
    current_user,
    date_from: date,
    date_to: date,
    state_filter: Optional[str] = None,
    b2b_filter: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
) -> dict:
    tenant = _get_tenant(db, current_user.tenant_id)
    tenant_state = (tenant.gst_state or "").strip().lower() if tenant else ""

    orders = _orders_in_period(
        db, current_user.tenant_id, date_from, date_to,
        state_filter, b2b_filter, min_amount, max_amount,
    )

    all_skus = {item.sku for o in orders for item in o.items if item.sku}
    prod_map = _build_sku_product_map(db, current_user.tenant_id, all_skus)

    # Group by gst_rate
    rate_map: dict = {}
    totals = {"taxable": Decimal("0"), "cgst": Decimal("0"),
              "sgst": Decimal("0"), "igst": Decimal("0")}

    for order in orders:
        cust_state = (order.delivery_state or "").strip()
        is_intra = cust_state.lower() == tenant_state if tenant_state else False

        for item in order.items:
            prod = prod_map.get(item.sku) if item.sku else None
            rate = _d(prod.gst_rate if prod else None)
            taxable = _d(item.line_total)
            _, cgst, sgst, igst, _ = _calc_gst(taxable, rate, is_intra)

            key = str(rate)
            if key not in rate_map:
                rate_map[key] = {
                    "gst_rate": _fmt(rate),
                    "taxable":  Decimal("0"),
                    "cgst":     Decimal("0"),
                    "sgst":     Decimal("0"),
                    "igst":     Decimal("0"),
                    "total_tax": Decimal("0"),
                }
            r = rate_map[key]
            r["taxable"]   += taxable
            r["cgst"]      += cgst
            r["sgst"]      += sgst
            r["igst"]      += igst
            r["total_tax"] += cgst + sgst + igst

            totals["taxable"] += taxable
            totals["cgst"]    += cgst
            totals["sgst"]    += sgst
            totals["igst"]    += igst

    rows = []
    for r in sorted(rate_map.values(), key=lambda x: float(x["gst_rate"])):
        rows.append({
            "gst_rate":  r["gst_rate"],
            "taxable":   _fmt(r["taxable"]),
            "cgst":      _fmt(r["cgst"]),
            "sgst":      _fmt(r["sgst"]),
            "igst":      _fmt(r["igst"]),
            "total_tax": _fmt(r["total_tax"]),
        })

    return {
        "rows": rows,
        "totals": {
            "taxable":   _fmt(totals["taxable"]),
            "cgst":      _fmt(totals["cgst"]),
            "sgst":      _fmt(totals["sgst"]),
            "igst":      _fmt(totals["igst"]),
            "total_gst": _fmt(totals["cgst"] + totals["sgst"] + totals["igst"]),
        },
    }


# ─────────────────────────────────────────────────────────────
# CSV Exports
# ─────────────────────────────────────────────────────────────

def export_gstr1_csv(gstr1_data: dict) -> str:
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow([
        "Invoice Number", "Invoice Date", "Customer Name", "Customer GSTIN",
        "Place of Supply", "HSN Code", "Product", "Quantity", "Unit",
        "Taxable Value", "GST Rate %", "CGST", "SGST", "IGST", "Total Value",
        "Payment Method", "B2B/B2C",
    ])
    for r in gstr1_data["rows"]:
        w.writerow([
            r["invoice_number"], r["invoice_date"], r["customer_name"],
            r["customer_gstin"], r["place_of_supply"], r["hsn_code"],
            r["product_name"], r["quantity"], r["unit"],
            r["taxable_value"], r["gst_rate"],
            r["cgst"], r["sgst"], r["igst"], r["total_value"],
            r["payment_method"], r["b2b_b2c"],
        ])
    # Summary row
    s = gstr1_data["summary"]
    w.writerow([])
    w.writerow(["TOTALS", "", "", "", "", "", "", "", "",
                s["total_taxable"], "", s["total_cgst"],
                s["total_sgst"], s["total_igst"], s["total_invoice"]])
    return out.getvalue()


def export_hsn_csv(hsn_data: dict) -> str:
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["HSN Code", "Description", "GST Rate %", "Total Qty",
                "Taxable Value", "CGST", "SGST", "IGST", "Total Value"])
    for r in hsn_data["rows"]:
        w.writerow([r["hsn_code"], r["description"], r["gst_rate"],
                    r["total_qty"], r["taxable"], r["cgst"],
                    r["sgst"], r["igst"], r["total"]])
    return out.getvalue()


def export_tax_summary_csv(tax_data: dict) -> str:
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["GST Rate %", "Taxable Value", "CGST", "SGST", "IGST", "Total Tax"])
    for r in tax_data["rows"]:
        w.writerow([r["gst_rate"], r["taxable"], r["cgst"],
                    r["sgst"], r["igst"], r["total_tax"]])
    t = tax_data["totals"]
    w.writerow([])
    w.writerow(["TOTAL", t["taxable"], t["cgst"], t["sgst"], t["igst"], t["total_gst"]])
    return out.getvalue()


def export_accounting_csv(gstr1_data: dict) -> str:
    """Tally / Zoho Books / Excel-compatible accounting export."""
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow([
        "Date", "Invoice No", "Customer Name", "Customer GSTIN",
        "Place of Supply", "Sales Ledger", "Taxable Amount",
        "CGST Ledger", "CGST Amount",
        "SGST Ledger", "SGST Amount",
        "IGST Ledger", "IGST Amount",
        "Total Amount", "Payment Mode", "B2B/B2C",
    ])
    # Group by invoice number
    inv_map: dict = {}
    for r in gstr1_data["rows"]:
        inv = r["invoice_number"]
        if inv not in inv_map:
            inv_map[inv] = {
                "date": r["invoice_date"],
                "customer_name": r["customer_name"],
                "gstin": r["customer_gstin"],
                "pos": r["place_of_supply"],
                "taxable": Decimal("0"),
                "cgst": Decimal("0"),
                "sgst": Decimal("0"),
                "igst": Decimal("0"),
                "total": Decimal("0"),
                "payment": r["payment_method"],
                "b2b": r["b2b_b2c"],
            }
        inv_map[inv]["taxable"] += Decimal(r["taxable_value"])
        inv_map[inv]["cgst"]    += Decimal(r["cgst"])
        inv_map[inv]["sgst"]    += Decimal(r["sgst"])
        inv_map[inv]["igst"]    += Decimal(r["igst"])
        inv_map[inv]["total"]   += Decimal(r["total_value"])

    for inv_no, d in inv_map.items():
        w.writerow([
            d["date"], inv_no, d["customer_name"], d["gstin"],
            d["pos"], "Sales",
            str(_round2(d["taxable"])),
            "CGST", str(_round2(d["cgst"])),
            "SGST", str(_round2(d["sgst"])),
            "IGST", str(_round2(d["igst"])),
            str(_round2(d["total"])),
            d["payment"], d["b2b"],
        ])
    return out.getvalue()


# ─────────────────────────────────────────────────────────────
# Tenant GST Profile CRUD
# ─────────────────────────────────────────────────────────────

def get_gst_profile(db: Session, current_user) -> dict:
    tenant = _get_tenant(db, current_user.tenant_id)
    if not tenant:
        return {}
    return {
        "company_name": tenant.company_name,
        "gstin":        tenant.gstin or "",
        "gst_state":    tenant.gst_state or "",
        "gst_address":  tenant.gst_address or "",
        "gst_city":     tenant.gst_city or "",
        "gst_pincode":  tenant.gst_pincode or "",
    }


def save_gst_profile(db: Session, current_user, data: dict) -> dict:
    tenant = _get_tenant(db, current_user.tenant_id)
    if not tenant:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant.gstin       = data.get("gstin", tenant.gstin)
    tenant.gst_state   = data.get("gst_state", tenant.gst_state)
    tenant.gst_address = data.get("gst_address", tenant.gst_address)
    tenant.gst_city    = data.get("gst_city", tenant.gst_city)
    tenant.gst_pincode = data.get("gst_pincode", tenant.gst_pincode)
    db.commit()
    return get_gst_profile(db, current_user)
