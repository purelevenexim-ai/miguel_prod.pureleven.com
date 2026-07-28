"""
Labels & WhatsApp Service
--------------------------
Business logic for PDF label generation and WhatsApp message composition.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.order import Order, OrderItem, PaymentMethod
from app.models.customer import Customer
from app.models.employee import Employee
from app.models.shipping_config import DeliveryPartner
from app.models.tenant import Tenant
from app.core.tenant_utils import apply_tenant_filter, assert_tenant_ownership, get_tenant_label_fields
from app.core.label_pdf import build_labels_pdf
from app.core.whatsapp import compose_whatsapp_message
from app.modules.labels.schemas import (
    LabelResponse, WhatsAppMessageResponse, WhatsAppBulkResponse,
)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _items_text(items: list[OrderItem]) -> str:
    """Render order items as 'Product Name x Qty' for the label.
    
    Example: "Kerala Cardamom 8mm - 100g x1\nCeylon Cinnamon x2"
    
    Falls back to SKU if product_name is missing.
    """
    lines = []
    for item in items:
        product_name = (item.product_name or "").strip()
        # Strip variant suffix after em-dash (e.g. "Kerala Cardamom 8mm - 100gm — 100gm" → "Kerala Cardamom 8mm - 100gm")
        if "\u2014" in product_name:
            product_name = product_name.split("\u2014")[0].strip()
        sku = (item.sku or "").strip()
        display_name = product_name if product_name else sku
        if not display_name:
            continue
        qty = item.quantity or 0
        # Format quantity: show as integer if it is a whole number
        try:
            qty_int = int(qty)
            qty_display = qty_int if qty == qty_int else float(qty)
        except Exception:
            qty_display = qty
        lines.append(f"{display_name} x{qty_display}")
    return "\n".join(lines)


def _payment_type_str(order: Order) -> str:
    """Map PaymentMethod → COD / Partial COD / Prepaid for the label."""
    if order.payment_method == PaymentMethod.cod:
        return "COD"
    if order.payment_method == PaymentMethod.partial_cod:
        return "Partial COD"
    return "Prepaid"


def _order_to_label_data(order: Order, customer: Customer, tenant=None, delivery_partner: Optional[DeliveryPartner] = None) -> dict:
    """Build the flat dict expected by label_pdf.draw_label."""

    # For Partial COD: the amount to collect at door = total - advance_paid (balance due)
    # For COD: full total_amount to collect
    # For Prepaid: total_amount (already paid, shown as reference)
    if order.payment_method == PaymentMethod.partial_cod:
        advance = order.advance_amount or Decimal("0")
        total   = order.total_amount   or Decimal("0")
        collect = max(Decimal("0"), total - advance)
        amount  = str(collect)
    else:
        amount = str(order.total_amount) if order.total_amount else ""
    
    # Determine India Post Customer ID to display.
    # Use order.india_post_customer_id directly — no need for delivery_partner lookup.
    # courier_code "india_post" is set on the order when an India Post partner is chosen.
    india_post_customer_id = ""
    is_india_post = (
        (delivery_partner and delivery_partner.partner_type == "india_post")
        or (order.courier_code and order.courier_code.lower() == "india_post")
    )
    if is_india_post and order.india_post_customer_id:
        india_post_customer_id = order.india_post_customer_id
    
    # ── Resolve correct contract ID from delivery partner config ──
    # The order stores `india_post_customer_id` at creation time.
    # But if the user later changes the service type (parcel↔speed_post) or the
    # partner's contract IDs change, we should use the *current* delivery partner
    # config matched by shipping_service to get the right contract ID.
    if is_india_post and delivery_partner and delivery_partner.customer_ids:
        cids = delivery_partner.customer_ids  # [{"id":"41903381","name":"Parcel"}, ...]
        svc = (order.shipping_service or "").lower().replace("_", " ").strip()
        matched = None
        for cid_entry in cids:
            cid_name = (cid_entry.get("name") or "").lower().strip()
            if svc and cid_name and (svc in cid_name or cid_name in svc):
                matched = cid_entry.get("id", "")
                break
        if matched:
            india_post_customer_id = matched
        # Fallback: if order has it stored and no match, use stored value
        elif not india_post_customer_id and order.india_post_customer_id:
            india_post_customer_id = order.india_post_customer_id

    # ── Build amounts for display on label ──
    # Only show the final total, not the breakdown
    final_amount = str(order.total_amount) if order.total_amount else ""

    tf = get_tenant_label_fields(tenant)

    return {
        "name":            order.delivery_name or customer.name,
        "address":         order.delivery_address or customer.address or "",
        "pincode":         order.delivery_pincode or customer.pincode or "",
        "city":            order.delivery_city or customer.city or "",
        "state":           order.delivery_state or customer.state or "",
        "phone":           customer.phone,
        "payment_type":    _payment_type_str(order),
        "amount":          amount,
        "order_number":    order.order_number,
        "tracking_number": order.tracking_number or "",
        "items_text":      _items_text(order.items),
        # From-address — from tenant company settings
        "from_name":       tf["from_name"],
        "from_address":    tf["from_address"],
        "from_pincode":    tf["from_pincode"],
        "from_phone":      tf["from_phone"],
        "slogan":          tf["slogan"],
        "logo_url":        tf["logo_url"],
        # India Post contract ID — resolved from delivery partner config
        "india_post_customer_id": india_post_customer_id,
        # Only final total amount (no breakdown)
        "final_amount":    final_amount,
    }


# ─────────────────────────────────────────────────────────────
# Label PDF
# ─────────────────────────────────────────────────────────────

def generate_labels(
    db: Session,
    order_ids: list[UUID],
    current_user: Employee,
) -> tuple[bytes, LabelResponse]:
    """
    Generate a multi-page PDF (one label per page) for the given order IDs.
    Increments printed_count on each order.
    Returns (pdf_bytes, LabelResponse).
    """
    label_data_list = []
    skipped = 0

    # Load tenant once for all labels in this batch
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()

    for oid in order_ids:
        order = (
            db.query(Order)
            .options(joinedload(Order.items))
            .filter(Order.id == oid)
            .first()
        )
        if not order or order.tenant_id != current_user.tenant_id:
            skipped += 1
            continue

        customer = db.query(Customer).filter(Customer.id == order.customer_id).first()
        if not customer:
            skipped += 1
            continue

        # Load delivery partner if shipping_partner_id is set
        delivery_partner = None
        if order.shipping_partner_id:
            delivery_partner = (
                db.query(DeliveryPartner)
                .filter(DeliveryPartner.id == order.shipping_partner_id)
                .first()
            )

        label_data_list.append(_order_to_label_data(order, customer, tenant, delivery_partner))

        # Increment printed_count
        order.printed_count = (order.printed_count or 0) + 1

    if not label_data_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid orders found to generate labels for.",
        )

    db.commit()

    pdf_bytes = build_labels_pdf(label_data_list)
    return pdf_bytes, LabelResponse(
        orders_printed=len(label_data_list),
        skipped=skipped,
        message=f"Generated {len(label_data_list)} label(s). {skipped} skipped.",
    )


# ─────────────────────────────────────────────────────────────
# WhatsApp
# ─────────────────────────────────────────────────────────────

def _order_to_whatsapp(order: Order, customer: Customer) -> WhatsAppMessageResponse:
    amount = str(order.total_amount) if order.total_amount else ""
    result = compose_whatsapp_message(
        name            = customer.name,
        phone           = customer.phone,
        order_number    = order.order_number,
        tracking_number = order.tracking_number,
        courier_name    = order.courier_name,
        items_text      = _items_text(order.items),
        amount          = amount,
        address         = order.delivery_address or customer.address or "",
        pincode         = order.delivery_pincode or customer.pincode or "",
        payment_type    = _payment_type_str(order),
    )
    return WhatsAppMessageResponse(
        order_id      = str(order.id),
        order_number  = order.order_number,
        to            = result["to"],
        phone_display = result["phone_display"],
        template      = result["template"],
        message       = result["message"],
        wa_url        = result["wa_url"],
    )


def get_whatsapp_message(
    db: Session,
    order_id: UUID,
    current_user: Employee,
) -> WhatsAppMessageResponse:
    order = (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.id == order_id, Order.tenant_id == current_user.tenant_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    customer = db.query(Customer).filter(Customer.id == order.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    return _order_to_whatsapp(order, customer)


def get_whatsapp_bulk(
    db: Session,
    order_ids: list[UUID],
    current_user: Employee,
) -> WhatsAppBulkResponse:
    results = []
    for oid in order_ids:
        order = (
            db.query(Order)
            .options(joinedload(Order.items))
            .filter(Order.id == oid)
            .first()
        )
        if not order or order.tenant_id != current_user.tenant_id:
            continue
        customer = db.query(Customer).filter(Customer.id == order.customer_id).first()
        if not customer:
            continue
        results.append(_order_to_whatsapp(order, customer))

    return WhatsAppBulkResponse(total=len(results), results=results)
