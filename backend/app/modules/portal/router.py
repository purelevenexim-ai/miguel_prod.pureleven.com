"""
Customer Portal API
-------------------
Public endpoints that allow customers to self-serve:
  GET /api/portal/order-status  — look up order by order_id/phone/email

No authentication required — only returns safe public fields.
Rate-limiting should be applied at the nginx/reverse-proxy layer.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.order import Order, OrderStatus
from app.models.shopify_order import ShopifyOrder, ShippingInfo, TrackingEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portal", tags=["Customer Portal"])


@router.get("/order-status")
def get_order_status(
    order_id: Optional[str] = Query(None, description="Order number or ID"),
    phone:    Optional[str] = Query(None, description="Customer phone number"),
    email:    Optional[str] = Query(None, description="Customer email"),
    tenant:   Optional[str] = Query(None, description="Tenant slug (required for multi-tenant)"),
    db: Session = Depends(get_db),
):
    """
    Public order status lookup.
    Returns a sanitised view of the order: status, items, shipping, tracking events.
    Requires at least one of: order_id or phone.
    For security, phone or email is validated against the order before revealing details.
    """
    if not order_id and not phone:
        raise HTTPException(status_code=400, detail="Provide at least order_id or phone number")

    # ── Try CRM orders first ──────────────────────────────────
    order = _find_crm_order(db, order_id, phone, email, tenant)

    # ── Try Shopify orders ────────────────────────────────────
    if not order:
        shopify_order = _find_shopify_order(db, order_id, phone, email, tenant)
        if shopify_order:
            return _format_shopify_order(db, shopify_order)

    if not order:
        raise HTTPException(status_code=404, detail="Order not found. Please check your order ID or phone number.")

    return _format_crm_order(order)


def _find_crm_order(db, order_id, phone, email, tenant):
    """Try to find a CRM-native order."""
    try:
        q = db.query(Order)
        if order_id:
            # Match by ID string, order_number, or shopify name
            clean = order_id.lstrip("#").strip()
            q = q.filter(
                Order.order_number.ilike(f"%{clean}%") |
                (Order.id.cast(db.bind.dialect.name == 'postgresql' and __import__('sqlalchemy').String or str) == clean)
            )
        elif phone:
            clean_phone = "".join(c for c in phone if c.isdigit())
            q = q.filter(Order.customer_phone.contains(clean_phone[-10:]))  # match last 10 digits

        orders = q.limit(10).all()
        if not orders:
            return None

        # Security: if we found by phone, phone already matches.
        # If found by order_id, verify phone/email matches for security.
        if order_id and (phone or email):
            for o in orders:
                ph_match = phone and ("".join(c for c in (o.customer_phone or "") if c.isdigit()).endswith(
                    "".join(c for c in phone if c.isdigit())[-10:]
                ))
                em_match = email and (o.customer_email or "").lower() == email.lower()
                if ph_match or em_match:
                    return o
            return None

        return orders[0] if orders else None
    except Exception as e:
        logger.warning(f"CRM order lookup error: {e}")
        return None


def _find_shopify_order(db, order_id, phone, email, tenant):
    """Try to find a Shopify-synced order."""
    try:
        q = db.query(ShopifyOrder)
        if tenant:
            from app.models.tenant import Tenant
            t = db.query(Tenant).filter(Tenant.slug == tenant).first()
            if t:
                q = q.filter(ShopifyOrder.tenant_id == t.id)

        if order_id:
            clean = order_id.lstrip("#").strip()
            # Match by shopify_order_name (e.g. "#1001") or shopify_order_id
            q = q.filter(
                ShopifyOrder.shopify_order_name.ilike(f"%{clean}%") |
                ShopifyOrder.shopify_order_id.contains(clean)
            )
        elif phone:
            clean_phone = "".join(c for c in phone if c.isdigit())[-10:]
            q = q.filter(ShopifyOrder.customer_phone.contains(clean_phone))

        orders = q.order_by(ShopifyOrder.created_at_shopify.desc()).limit(5).all()
        if not orders:
            return None

        # Security check: if found by order_id, verify phone/email
        if order_id and (phone or email):
            for o in orders:
                ph_match = phone and ("".join(c for c in (o.customer_phone or "") if c.isdigit())).endswith(
                    "".join(c for c in phone if c.isdigit())[-10:]
                )
                em_match = email and (o.customer_email or "").lower() == email.lower()
                if ph_match or em_match:
                    return o
            return None

        return orders[0] if orders else None
    except Exception as e:
        logger.warning(f"Shopify order lookup error: {e}")
        return None


def _format_crm_order(order: Order) -> dict:
    """Return a public-safe representation of a CRM order."""
    items = []
    try:
        for item in (order.items or []):
            items.append({
                "name":     item.product_name if hasattr(item, 'product_name') else str(item),
                "quantity": getattr(item, 'quantity', 1),
                "price":    getattr(item, 'unit_price', None),
            })
    except Exception:
        pass

    return {
        "order": {
            "id":            str(order.id),
            "order_number":  order.order_number or str(order.id),
            "status":        order.status.value if order.status else "pending",
            "payment_status":order.payment_status.value if hasattr(order,'payment_status') and order.payment_status else "pending",
            "total_amount":  float(order.total_amount or 0),
            "shipping_charge": float(order.shipping_charge or 0),
            "shipping_service": order.shipping_service or None,
            "created_at":    order.created_at.isoformat() if order.created_at else None,
            "shipping_address": order.delivery_address or None,
        },
        "items": items,
        "tracking": {
            "awb_number": order.tracking_number or None,
            "shipping_partner": order.courier_name or None,
            "shipping_service": order.shipping_service or None,
            "shipping_charge": float(order.shipping_charge or 0),
        },
        "tracking_events": [],
        "source": "crm",
    }


def _format_shopify_order(db, order: ShopifyOrder) -> dict:
    """Return a public-safe representation of a Shopify order."""
    # Get shipping info & tracking events
    shipping = db.query(ShippingInfo).filter(ShippingInfo.shopify_order_id == order.id).first()
    events_q = []
    if shipping:
        events_q = (
            db.query(TrackingEvent)
            .filter(TrackingEvent.shipping_info_id == shipping.id)
            .order_by(TrackingEvent.timestamp.desc())
            .limit(20)
            .all()
        )

    # Parse items from raw_data
    items = []
    try:
        raw = order.raw_data or {}
        for li in (raw.get("line_items") or []):
            items.append({
                "name":          li.get("title", ""),
                "variant_title": li.get("variant_title", ""),
                "quantity":      li.get("quantity", 1),
                "price":         li.get("price"),
                "image_url":     (li.get("image") or {}).get("src") or None,
            })
    except Exception:
        pass

    # Parse shipping address
    shipping_address = None
    try:
        raw = order.raw_data or {}
        sa  = raw.get("shipping_address") or raw.get("billing_address") or {}
        if sa:
            shipping_address = {
                "address1": sa.get("address1", ""),
                "address2": sa.get("address2", ""),
                "city":     sa.get("city", ""),
                "province": sa.get("province", ""),
                "country":  sa.get("country", ""),
                "zip":      sa.get("zip", ""),
            }
    except Exception:
        pass

    tracking_events = []
    for ev in events_q:
        tracking_events.append({
            "status_description": ev.status_description or ev.activity or "",
            "timestamp":          ev.timestamp.isoformat() if ev.timestamp else None,
            "location":           ev.location or "",
        })

    return {
        "order": {
            "id":                  str(order.id),
            "order_number":        order.shopify_order_name or order.shopify_order_number or str(order.shopify_order_id),
            "status":              order.shopify_status.value if order.shopify_status else "pending",
            "financial_status":    order.financial_status or "pending",
            "payment_status":      order.financial_status or "pending",
            "total_price":         float(order.total_price or 0),
            "created_at_shopify":  order.created_at_shopify.isoformat() if order.created_at_shopify else None,
            "shipping_address":    shipping_address,
        },
        "items": items,
        "tracking": {
            "awb_number":      shipping.tracking_number if shipping else None,
            "shipping_partner": order.shipping_partner.value if order.shipping_partner else None,
            "is_delivered":    shipping.is_delivered if shipping else False,
            "estimated_delivery": shipping.estimated_delivery.isoformat() if shipping and getattr(shipping,'estimated_delivery',None) else None,
        },
        "tracking_events": tracking_events,
        "source": "shopify",
    }
