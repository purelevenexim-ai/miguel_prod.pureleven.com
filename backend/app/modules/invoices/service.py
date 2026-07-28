from __future__ import annotations
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.gst_engine import (
    get_financial_year,
    is_intra_state,
    split_gst,
    calc_gst_amounts,
)
from app.models.invoice import Invoice, InvoiceItem, InvoiceCounter, InvoiceStatus
from app.modules.invoices.schemas import InvoiceCreate, InvoiceUpdate


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _next_invoice_number(db: Session, tenant_id: UUID, fy: str) -> str:
    """Atomically increment the per-tenant per-FY invoice counter."""
    counter = (
        db.query(InvoiceCounter)
        .filter(
            InvoiceCounter.tenant_id == tenant_id,
            InvoiceCounter.financial_year == fy,
        )
        .with_for_update()
        .first()
    )
    if not counter:
        counter = InvoiceCounter(
            tenant_id=tenant_id,
            financial_year=fy,
            last_number=0,
        )
        db.add(counter)
        db.flush()
    counter.last_number += 1
    db.flush()
    return f"INV-{fy[:4]}-{str(counter.last_number).zfill(5)}"


def _get_or_404(db: Session, invoice_id: UUID, tenant_id: UUID) -> Invoice:
    invoice = (
        db.query(Invoice)
        .filter(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id)
        .first()
    )
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def create_invoice(db: Session, data: InvoiceCreate, current_user) -> Invoice:
    fy = get_financial_year(data.invoice_date)
    intra = is_intra_state(data.customer_state, data.supply_state)

    invoice_number = _next_invoice_number(db, current_user.tenant_id, fy)

    # Compute per-item GST amounts and accumulate totals
    total_taxable = Decimal("0")
    cgst_total    = Decimal("0")
    sgst_total    = Decimal("0")
    igst_total    = Decimal("0")

    built_items: list[dict] = []
    for item in data.items:
        taxable = (item.quantity * item.unit_price).quantize(Decimal("0.01"))
        cgst_pct, sgst_pct, igst_pct = split_gst(item.tax_percent, intra)
        cgst, sgst, igst, total_tax  = calc_gst_amounts(taxable, cgst_pct, sgst_pct, igst_pct)
        line_total = taxable + total_tax

        total_taxable += taxable
        cgst_total    += cgst
        sgst_total    += sgst
        igst_total    += igst

        built_items.append(dict(
            product_id=item.product_id,
            product_name=item.product_name,
            hsn_code=item.hsn_code,
            quantity=item.quantity,
            unit_price=item.unit_price,
            taxable_amount=taxable,
            tax_percent=item.tax_percent,
            cgst_percent=cgst_pct,
            sgst_percent=sgst_pct,
            igst_percent=igst_pct,
            cgst_amount=cgst,
            sgst_amount=sgst,
            igst_amount=igst,
            tax_amount=total_tax,
            line_total=line_total,
        ))

    total_tax  = cgst_total + sgst_total + igst_total
    grand_total = total_taxable + total_tax

    invoice = Invoice(
        tenant_id=current_user.tenant_id,
        invoice_number=invoice_number,
        financial_year=fy,
        invoice_date=data.invoice_date,
        order_id=data.order_id,
        customer_id=data.customer_id,
        billing_address=data.billing_address,
        shipping_address=data.shipping_address,
        customer_gst=data.customer_gst,
        customer_state=data.customer_state,
        supply_state=data.supply_state,
        total_taxable=total_taxable,
        cgst_amount=cgst_total,
        sgst_amount=sgst_total,
        igst_amount=igst_total,
        total_tax=total_tax,
        grand_total=grand_total,
        status=InvoiceStatus.draft,
        notes=data.notes,
        created_by_id=current_user.id,
    )
    db.add(invoice)
    db.flush()  # get invoice.id before inserting items

    for item_data in built_items:
        db.add(InvoiceItem(
            tenant_id=current_user.tenant_id,
            invoice_id=invoice.id,
            **item_data,
        ))

    db.commit()
    db.refresh(invoice)
    return invoice


def list_invoices(
    db: Session,
    current_user,
    skip: int = 0,
    limit: int = 50,
    customer_id: Optional[UUID] = None,
    invoice_status: Optional[InvoiceStatus] = None,
    financial_year: Optional[str] = None,
) -> list[Invoice]:
    q = db.query(Invoice).filter(Invoice.tenant_id == current_user.tenant_id)
    if customer_id:
        q = q.filter(Invoice.customer_id == customer_id)
    if invoice_status:
        q = q.filter(Invoice.status == invoice_status)
    if financial_year:
        q = q.filter(Invoice.financial_year == financial_year)
    return q.order_by(Invoice.invoice_date.desc(), Invoice.created_at.desc()).offset(skip).limit(limit).all()


def get_invoice(db: Session, invoice_id: UUID, current_user) -> Invoice:
    return _get_or_404(db, invoice_id, current_user.tenant_id)


def update_invoice(db: Session, invoice_id: UUID, data: InvoiceUpdate, current_user) -> Invoice:
    invoice = _get_or_404(db, invoice_id, current_user.tenant_id)
    if invoice.status != InvoiceStatus.draft:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft invoices can be updated",
        )
    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(invoice, field, val)
    db.commit()
    db.refresh(invoice)
    return invoice


def finalize_invoice(db: Session, invoice_id: UUID, current_user) -> Invoice:
    invoice = _get_or_404(db, invoice_id, current_user.tenant_id)
    if invoice.status == InvoiceStatus.finalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice is already finalized",
        )
    if invoice.status == InvoiceStatus.cancelled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot finalize a cancelled invoice",
        )
    # Trigger stock-out for each item that has a product_id
    from app.modules.inventory import service as inv_svc
    from app.models.inventory import MovementType

    for item in invoice.items:
        if item.product_id:
            inv_svc.record_movement(
                db=db,
                tenant_id=current_user.tenant_id,
                product_id=item.product_id,
                movement_type=MovementType.sale.value,
                quantity_change=-abs(item.quantity),
                reference_id=invoice.id,
                reference_type="invoice",
                note=f"Stock out — Invoice {invoice.invoice_number}",
                created_by_id=current_user.id,
                commit=False,
            )

    invoice.status = InvoiceStatus.finalized
    db.commit()
    db.refresh(invoice)
    return invoice


def cancel_invoice(db: Session, invoice_id: UUID, current_user) -> Invoice:
    invoice = _get_or_404(db, invoice_id, current_user.tenant_id)
    if invoice.status == InvoiceStatus.finalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel a finalized invoice",
        )
    if invoice.status == InvoiceStatus.cancelled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice is already cancelled",
        )
    invoice.status = InvoiceStatus.cancelled
    db.commit()
    db.refresh(invoice)
    return invoice


# ---------------------------------------------------------------------------
# PDF Generation
# ---------------------------------------------------------------------------

def _build_invoice_html(order, customer, tenant, invoice_type: str = "tax_invoice", invoice_number: str = "") -> str:
    """Build A4 HTML invoice ready for WeasyPrint — RMS Spices style."""
    from datetime import date
    from app.core.gst_engine import is_intra_state, split_gst, calc_gst_amounts
    from decimal import Decimal

    type_labels = {
        "proforma": "Proforma Invoice",
        "tax_invoice": "Tax Invoice",
        "retail_bill": "Retail Bill",
    }
    doc_title = type_labels.get(invoice_type, "Tax Invoice")
    is_proforma = invoice_type == "proforma"
    is_retail = invoice_type == "retail_bill"

    # GST calc
    tenant_state = getattr(tenant, "gst_state", "") or ""
    cust_state = getattr(customer, "state", "") or ""
    intra = is_intra_state(cust_state, tenant_state)
    gst_type = "CGST + SGST" if intra else "IGST"

    subtotal = Decimal(str(order.subtotal or 0))
    discount = Decimal(str(order.discount_amount or 0))
    tax_total = Decimal(str(order.tax_amount or 0))
    shipping = Decimal(str(order.shipping_charge or 0))
    grand_total = Decimal(str(order.total_amount or 0))
    advance = Decimal(str(order.advance_amount or 0))
    balance_due = Decimal(str(order.amount_due or 0))
    you_saved = discount

    # items
    items_rows = ""
    for i, item in enumerate(order.items or []):
        qty = item.quantity
        price = item.unit_price
        disc_pct = getattr(item, "discount_pct", 0) or 0
        taxable = qty * price * (1 - Decimal(str(disc_pct)) / 100)
        unit_label = item.unit.value if hasattr(item.unit, "value") else item.unit

        gst_cell = ""
        if not is_retail:
            gst_rate = Decimal("5")
            if intra:
                half = gst_rate / 2
                gst_cell = f"CGST {half}%<br>SGST {half}%"
            else:
                gst_cell = f"IGST {gst_rate}%"

        items_rows += f"""
        <tr>
            <td style="padding:8px 10px;border-bottom:1px solid #e8e8e8;text-align:center;font-size:12px;">{i+1}</td>
            <td style="padding:8px 10px;border-bottom:1px solid #e8e8e8;font-size:12px;">
                <strong>{item.product_name}</strong>
                {f'<br><span style="color:#999;font-size:11px;">SKU: {item.sku}</span>' if getattr(item,"sku","") else ""}
            </td>
            <td style="padding:8px 10px;border-bottom:1px solid #e8e8e8;text-align:center;font-size:12px;">{qty}</td>
            <td style="padding:8px 10px;border-bottom:1px solid #e8e8e8;text-align:center;font-size:12px;">{unit_label}</td>
            <td style="padding:8px 10px;border-bottom:1px solid #e8e8e8;text-align:right;font-size:12px;">&#8377;{float(price):,.2f}</td>
            {f'<td style="padding:8px 10px;border-bottom:1px solid #e8e8e8;text-align:center;font-size:11px;color:#666;">{gst_cell}</td>' if not is_retail else ""}
            <td style="padding:8px 10px;border-bottom:1px solid #e8e8e8;text-align:right;font-weight:600;font-size:12px;">&#8377;{float(taxable):,.2f}</td>
        </tr>"""

    # payment method display
    pm_map = {"cod": "Cash on Delivery", "upi": "UPI", "cash": "Cash", "bank_transfer": "Bank Transfer",
              "cheque": "Cheque", "credit": "Credit", "partial_cod": "Partial COD"}
    payment_display = pm_map.get(str(order.payment_method.value if hasattr(order.payment_method, "value") else order.payment_method or ""), "—")

    # Tenant info
    tenant_addr_parts = filter(None, [
        getattr(tenant, "address_line1", "") or getattr(tenant, "gst_address", "") or "",
        getattr(tenant, "address_line2", "") or "",
    ])
    tenant_addr_line = ", ".join(tenant_addr_parts)
    tenant_city_state = ", ".join(filter(None, [
        getattr(tenant, "gst_city", "") or "",
        getattr(tenant, "gst_state", "") or "",
        getattr(tenant, "gst_pincode", "") or "",
    ]))
    tenant_phone = getattr(tenant, "phone", "") or getattr(tenant, "contact_phone", "") or ""
    tenant_email = getattr(tenant, "email", "") or getattr(tenant, "owner_email", "") or ""
    tenant_gstin = getattr(tenant, "gstin", "") or ""
    tenant_logo = getattr(tenant, "logo_url", "") or ""

    # Logo HTML
    logo_html = ""
    if tenant_logo:
        logo_html = f'<img src="{tenant_logo}" style="max-width:80px;max-height:50px;object-fit:contain;" alt="Logo">'
    else:
        logo_html = f'<div style="width:60px;height:40px;background:#f0f0f0;border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:10px;color:#999;">Logo</div>'

    # Bank details
    bank_html = ""
    if getattr(tenant, "bank_name", None):
        bank_html = f"""
        <div style="font-size:11px;line-height:1.6;">
            <div style="font-weight:700;margin-bottom:4px;color:#333;font-size:12px;">Bank Details</div>
            <div><span style="color:#888;">Bank:</span> {tenant.bank_name}</div>
            <div><span style="color:#888;">A/C:</span> {getattr(tenant,'bank_account','')}</div>
            <div><span style="color:#888;">IFSC:</span> {getattr(tenant,'bank_ifsc','')}</div>
            <div><span style="color:#888;">Branch:</span> {getattr(tenant,'bank_branch','')}</div>
            {f'<div><span style="color:#888;">UPI:</span> {tenant.upi_id}</div>' if getattr(tenant,'upi_id',None) else ''}
        </div>"""

    proforma_notice = ""
    if is_proforma:
        proforma_notice = '<div style="background:#fff8e1;border:1px solid #ffd54f;border-radius:6px;padding:10px 14px;margin-bottom:16px;font-size:12px;color:#795548;">&#9888;&#65039; This is a Proforma Invoice — not a tax document. Not valid for GST input credit.</div>'

    inv_num = invoice_number or order.order_number or "—"
    inv_date = date.today().strftime("%d %b %Y")

    cust_addr = getattr(customer, "address", "") or (order.delivery_address or "")
    cust_city = getattr(customer, "city", "") or (order.delivery_city or "")
    cust_state_val = getattr(customer, "state", "") or (order.delivery_state or "")
    cust_pincode = getattr(customer, "pincode", "") or (order.delivery_pincode or "")

    ship_name = order.delivery_name or customer.name
    ship_addr = order.delivery_address or customer.address or "—"
    ship_city_state = ", ".join(filter(None, [order.delivery_city or "", order.delivery_state or "", order.delivery_pincode or ""]))

    gst_head = "" if is_retail else "<th style='padding:8px 10px;background:#1a73e8;color:#fff;text-align:center;font-size:11px;font-weight:600;'>GST</th>"

    # Number to words helper (basic Indian format)
    def _amount_words(amt):
        try:
            num = int(float(amt))
            if num == 0:
                return "Zero"
            ones = ['','One','Two','Three','Four','Five','Six','Seven','Eight','Nine','Ten',
                    'Eleven','Twelve','Thirteen','Fourteen','Fifteen','Sixteen','Seventeen','Eighteen','Nineteen']
            tens = ['','','Twenty','Thirty','Forty','Fifty','Sixty','Seventy','Eighty','Ninety']
            if num < 20:
                return ones[num]
            if num < 100:
                return tens[num//10] + ('' if num%10==0 else ' ' + ones[num%10])
            if num < 1000:
                return ones[num//100] + ' Hundred' + ('' if num%100==0 else ' and ' + _amount_words(num%100))
            if num < 100000:
                return _amount_words(num//1000) + ' Thousand' + ('' if num%1000==0 else ' ' + _amount_words(num%1000))
            if num < 10000000:
                return _amount_words(num//100000) + ' Lakh' + ('' if num%100000==0 else ' ' + _amount_words(num%100000))
            return _amount_words(num//10000000) + ' Crore' + ('' if num%10000000==0 else ' ' + _amount_words(num%10000000))
        except Exception:
            return str(amt)

    amount_in_words = _amount_words(grand_total) + " Rupees Only"

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  * {{ margin:0;padding:0;box-sizing:border-box; }}
  body {{ font-family:'Inter',sans-serif;font-size:13px;color:#1a1a1a;background:#fff;padding:24px; }}
  @media print {{ body {{ padding:0; }} @page {{ size:A4;margin:14mm 10mm; }} }}
  table {{ border-collapse:collapse; }}
</style>
</head>
<body>

  <!-- ═══ HEADER ═══ -->
  <div style="display:flex;align-items:flex-start;gap:16px;margin-bottom:12px;padding-bottom:12px;border-bottom:2px solid #1a73e8;">
    <!-- Logo -->
    <div style="flex-shrink:0;">{logo_html}</div>
    <!-- Company Info -->
    <div style="flex:1;">
      <div style="font-size:20px;font-weight:700;color:#1a73e8;">{tenant.company_name}</div>
      {f'<div style="font-size:11px;color:#888;margin-top:2px;">{getattr(tenant,"slogan","")}</div>' if getattr(tenant,"slogan",None) else ""}
      <div style="font-size:11px;color:#555;margin-top:4px;">{tenant_addr_line}</div>
      <div style="font-size:11px;color:#555;">{tenant_city_state}</div>
      <div style="font-size:11px;color:#555;">Ph: {tenant_phone}{f' | {tenant_email}' if tenant_email else ''}</div>
      {f'<div style="font-size:11px;color:#555;">GSTIN: {tenant_gstin}</div>' if tenant_gstin else ""}
    </div>
    <!-- Order Meta Table -->
    <div style="flex-shrink:0;">
      <table style="border:1px solid #ddd;border-radius:6px;overflow:hidden;font-size:12px;">
        <tr><td style="padding:6px 10px;background:#f8f9fa;font-weight:600;color:#555;">Order No</td><td style="padding:6px 10px;font-weight:700;">{order.order_number}</td></tr>
        <tr><td style="padding:6px 10px;background:#f8f9fa;font-weight:600;color:#555;">Date</td><td style="padding:6px 10px;">{inv_date}</td></tr>
        <tr><td style="padding:6px 10px;background:#f8f9fa;font-weight:600;color:#555;">Payment</td><td style="padding:6px 10px;">{payment_display}</td></tr>
      </table>
    </div>
  </div>

  <!-- Doc Title -->
  <div style="text-align:center;margin-bottom:14px;">
    <span style="display:inline-block;padding:4px 20px;background:#1a73e8;color:#fff;border-radius:4px;font-size:14px;font-weight:700;letter-spacing:0.05em;">{doc_title}</span>
    <span style="margin-left:12px;font-size:13px;color:#666;">#{inv_num}</span>
  </div>

  {proforma_notice}

  <!-- ═══ ORDER FROM / SHIP TO ═══ -->
  <div style="display:flex;gap:16px;margin-bottom:16px;">
    <div style="flex:1;padding:12px;background:#f8f9fa;border-radius:8px;border:1px solid #eee;">
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:#1a73e8;margin-bottom:6px;letter-spacing:0.05em;">Order From / Bill To</div>
      <div style="font-weight:600;font-size:13px;">{customer.name}</div>
      <div style="font-size:12px;color:#555;margin-top:3px;">{cust_addr}</div>
      <div style="font-size:12px;color:#555;">{", ".join(filter(None,[cust_city, cust_state_val, cust_pincode]))}</div>
      <div style="font-size:12px;color:#555;margin-top:2px;">Ph: {customer.phone}</div>
      {f'<div style="font-size:12px;color:#555;margin-top:2px;">GSTIN: {customer.gstin}</div>' if getattr(customer,"gstin",None) else ""}
    </div>
    <div style="flex:1;padding:12px;background:#f8f9fa;border-radius:8px;border:1px solid #eee;">
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:#1a73e8;margin-bottom:6px;letter-spacing:0.05em;">Ship To</div>
      <div style="font-weight:600;font-size:13px;">{ship_name}</div>
      <div style="font-size:12px;color:#555;margin-top:3px;">{ship_addr}</div>
      <div style="font-size:12px;color:#555;">{ship_city_state}</div>
      {f'<div style="font-size:12px;color:#555;margin-top:3px;"><span style="color:#888;">Courier:</span> {order.courier_name}</div>' if order.courier_name else ""}
      {f'<div style="font-size:12px;color:#555;"><span style="color:#888;">Tracking:</span> {order.tracking_number}</div>' if order.tracking_number else ""}
    </div>
  </div>

  <!-- ═══ ITEMS TABLE ═══ -->
  <table style="width:100%;margin-bottom:16px;border:1px solid #e0e0e0;border-radius:6px;overflow:hidden;">
    <thead>
      <tr>
        <th style="padding:8px 10px;background:#1a73e8;color:#fff;text-align:center;font-size:11px;font-weight:600;width:36px;">SL.NO</th>
        <th style="padding:8px 10px;background:#1a73e8;color:#fff;text-align:left;font-size:11px;font-weight:600;">ITEM</th>
        <th style="padding:8px 10px;background:#1a73e8;color:#fff;text-align:center;font-size:11px;font-weight:600;">QTY</th>
        <th style="padding:8px 10px;background:#1a73e8;color:#fff;text-align:center;font-size:11px;font-weight:600;">UNIT</th>
        <th style="padding:8px 10px;background:#1a73e8;color:#fff;text-align:right;font-size:11px;font-weight:600;">PRICE/UNIT</th>
        {gst_head}
        <th style="padding:8px 10px;background:#1a73e8;color:#fff;text-align:right;font-size:11px;font-weight:600;">FINAL AMOUNT</th>
      </tr>
    </thead>
    <tbody>
      {items_rows}
    </tbody>
  </table>

  <!-- ═══ TOTALS ═══ -->
  <div style="display:flex;justify-content:flex-end;margin-bottom:16px;">
    <div style="min-width:300px;border:1px solid #e0e0e0;border-radius:6px;overflow:hidden;">
      <div style="display:flex;justify-content:space-between;padding:8px 14px;font-size:13px;background:#fafafa;border-bottom:1px solid #eee;">
        <span style="color:#555;">Sub Total</span><span style="font-weight:600;">&#8377;{float(subtotal):,.2f}</span>
      </div>
      {f'<div style="display:flex;justify-content:space-between;padding:8px 14px;font-size:13px;background:#fff;border-bottom:1px solid #eee;"><span style="color:#e53935;">Discount</span><span style="color:#e53935;font-weight:600;">- &#8377;{float(discount):,.2f}</span></div>' if discount > 0 else ""}
      {f'<div style="display:flex;justify-content:space-between;padding:8px 14px;font-size:13px;background:#fafafa;border-bottom:1px solid #eee;"><span style="color:#555;">Tax ({gst_type})</span><span>&#8377;{float(tax_total):,.2f}</span></div>' if tax_total > 0 and not is_retail else ""}
      {f'<div style="display:flex;justify-content:space-between;padding:8px 14px;font-size:13px;background:#fff;border-bottom:1px solid #eee;"><span style="color:#555;">Shipping</span><span>&#8377;{float(shipping):,.2f}</span></div>' if shipping > 0 else ""}
      <div style="display:flex;justify-content:space-between;padding:10px 14px;font-size:15px;font-weight:700;background:#1a73e8;color:#fff;">
        <span>Total</span><span>&#8377;{float(grand_total):,.2f}</span>
      </div>
      {f'<div style="display:flex;justify-content:space-between;padding:8px 14px;font-size:13px;background:#e8f5e9;border-bottom:1px solid #eee;"><span style="color:#2e7d32;">Advance Paid</span><span style="color:#2e7d32;font-weight:600;">&#8377;{float(advance):,.2f}</span></div>' if advance > 0 else ""}
      {f'<div style="display:flex;justify-content:space-between;padding:8px 14px;font-size:14px;font-weight:700;background:#fff3e0;"><span style="color:#e65100;">Balance Due</span><span style="color:#e65100;">&#8377;{float(balance_due):,.2f}</span></div>' if balance_due > 0 else ""}
      {f'<div style="display:flex;justify-content:space-between;padding:6px 14px;font-size:12px;background:#f1f8e9;color:#558b2f;"><span>You Saved</span><span>&#8377;{float(you_saved):,.2f}</span></div>' if you_saved > 0 else ""}
    </div>
  </div>

  <!-- Amount in words -->
  <div style="margin-bottom:16px;padding:8px 14px;background:#f8f9fa;border-radius:6px;border:1px solid #eee;font-size:12px;">
    <span style="color:#888;font-weight:600;">Amount in Words:</span> <span style="font-weight:600;color:#333;">{amount_in_words}</span>
  </div>

  {f'<div style="margin-bottom:16px;padding:8px 14px;background:#f8f9fa;border-radius:6px;border:1px solid #eee;font-size:12px;"><span style="color:#888;font-weight:600;">Payment Mode:</span> <span style="font-weight:600;color:#333;">{payment_display}</span></div>' if payment_display != '—' else ''}

  {f'<div style="margin-bottom:16px;padding:10px 14px;background:#f5f5f5;border-radius:6px;font-size:12px;color:#555;"><strong>Notes:</strong> {order.notes}</div>' if order.notes else ""}

  <!-- ═══ FOOTER: Terms + Bank + Signature ═══ -->
  <div style="display:flex;gap:16px;margin-top:20px;padding-top:16px;border-top:1px solid #e0e0e0;">
    <!-- Left: Terms & Bank -->
    <div style="flex:1;">
      <div style="font-size:11px;color:#666;line-height:1.6;">
        <div style="font-weight:700;color:#333;margin-bottom:4px;font-size:12px;">Terms & Conditions</div>
        <div>1. Goods once sold will not be taken back.</div>
        <div>2. All disputes are subject to local jurisdiction.</div>
        <div>3. E&OE (Errors and Omissions Excepted).</div>
      </div>
      <div style="margin-top:12px;">{bank_html}</div>
    </div>
    <!-- Right: Authorized Signatory -->
    <div style="width:200px;text-align:center;">
      <div style="margin-top:60px;border-top:1px solid #999;padding-top:6px;">
        <div style="font-size:12px;font-weight:700;color:#333;">Authorized Signatory</div>
        <div style="font-size:11px;color:#888;">For {tenant.company_name}</div>
      </div>
    </div>
  </div>

  <!-- Generated by -->
  <div style="margin-top:20px;padding-top:8px;border-top:1px solid #eee;text-align:center;font-size:10px;color:#bbb;">
    Generated by {tenant.company_name} CRM | This is a computer-generated document.
  </div>

</body>
</html>"""


def generate_invoice_pdf(db: Session, invoice_id: UUID, current_user, invoice_type: str = "tax_invoice") -> bytes:
    """Generate A4 PDF for a saved invoice record."""
    invoice = _get_or_404(db, invoice_id, current_user.tenant_id)
    from app.models.customer import Customer
    from app.models.order import Order
    from app.models.tenant import Tenant

    customer = db.query(Customer).filter(Customer.id == invoice.customer_id).first()
    order = db.query(Order).filter(Order.id == invoice.order_id).first() if invoice.order_id else None
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()

    if not customer or not tenant:
        raise HTTPException(status_code=404, detail="Data not found")

    html = _build_invoice_html(order or _fake_order_from_invoice(invoice), customer, tenant,
                               invoice_type=invoice_type, invoice_number=invoice.invoice_number)
    return _html_to_pdf(html)


def generate_order_invoice_pdf(db: Session, order_id: UUID, current_user, invoice_type: str = "tax_invoice") -> bytes:
    """Generate A4 PDF directly from order (no invoice record needed)."""
    from app.models.customer import Customer
    from app.models.order import Order
    from app.models.tenant import Tenant
    from sqlalchemy.orm import joinedload

    order = db.query(Order).options(joinedload(Order.items)).filter(
        Order.id == order_id,
        Order.tenant_id == current_user.tenant_id,
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    customer = db.query(Customer).filter(Customer.id == order.customer_id).first()
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()

    if not customer or not tenant:
        raise HTTPException(status_code=404, detail="Customer/Tenant not found")

    html = _build_invoice_html(order, customer, tenant, invoice_type=invoice_type,
                               invoice_number=order.order_number)
    return _html_to_pdf(html)


def _html_to_pdf(html: str) -> bytes:
    """Convert HTML to PDF bytes using WeasyPrint if available, else fallback."""
    try:
        from weasyprint import HTML
        return HTML(string=html).write_pdf()
    except ImportError:
        # Fallback: return HTML as bytes if WeasyPrint not installed
        return html.encode("utf-8")


def _fake_order_from_invoice(invoice):
    """Create a minimal order-like object from invoice data for rendering."""
    class FakeOrder:
        order_number = invoice.invoice_number
        delivery_name = None
        delivery_address = invoice.shipping_address
        delivery_city = None
        delivery_state = invoice.customer_state
        delivery_pincode = None
        courier_name = None
        tracking_number = None
        subtotal = invoice.total_taxable
        discount_amount = getattr(invoice, "discount_amount", 0) or 0
        tax_amount = invoice.total_tax
        shipping_charge = getattr(invoice, "shipping_charge", 0) or 0
        total_amount = invoice.grand_total
        advance_amount = getattr(invoice, "advance_paid", 0) or 0
        amount_due = getattr(invoice, "amount_due", 0) or 0
        payment_method = None
        notes = invoice.notes
        status = "finalized"
        items = invoice.items
    return FakeOrder()
