"""
Orders Service
---------------
Full Fulfillment Engine.
- Not Confirmed orders → auto-create Lead
- Confirmed orders → auto-create/link Customer + reduce inventory
- Phone dedup check
- Address parse support
- WhatsApp trigger on confirm
"""

from __future__ import annotations

import logging
import re
import uuid as _uuid
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_, and_
from sqlalchemy.orm import Session, joinedload, selectinload
from app.core.cache import cache_ttl, invalidate_cache
from app.core.config import settings

log = logging.getLogger(__name__)

from app.models.order import (
    Order, OrderItem, OrderPayment, OrderStatusHistory,
    OrderStatus, PaymentStatus, PaymentMethod, Courier, IndiaPostCustomerId,
)
from app.models.customer import Customer, LeadStatus as CustomerLeadStatus, SourceType, CustomerType, PaymentMode
from app.models.lead import Lead, LeadPipelineStatus, LeadActivity, LeadActivityType, LeadSource
from app.models.product import Product, ProductStatus
from app.models.employee import Employee
from app.models.tenant import Tenant
from app.core.tenant_utils import apply_tenant_filter, assert_tenant_ownership
from app.core.whatsapp import compose_whatsapp_message as _compose_wa
from app.core.logger import log_activity
from app.models.activity_log import LogLevel, LogModule
from app.core.sequence import next_order_number as _safe_order_number, next_customer_code, next_lead_number
from app.modules.orders.schemas import (
    OrderCreate, OrderUpdate, OrderFilters, OrderStats,
    OrderStatusUpdate, OrderPaymentCreate,
    OrderResponse, OrderDetail,
)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _slug_prefix(slug: str) -> str:
    """
    Derive a short 3-4 char prefix from a tenant slug.
    purelevenexim → PLX  (first char + last 2 consonants, uppercased)
    """
    import re
    s = slug.upper().replace("-", "").replace("_", "")
    consonants = re.sub(r'[AEIOU0-9]', '', s)
    if len(consonants) >= 3:
        return consonants[0] + consonants[1] + consonants[-1]
    # fallback: first 3 chars of slug
    return s[:3] if len(s) >= 3 else s.ljust(3, 'X')


def _next_order_number(db: Session, tenant_id, slug: str = "") -> str:
    """Thread-safe order number using advisory lock."""
    return _safe_order_number(db, tenant_id, slug)


def _phone_digits(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"\D", "", str(value))


def _phone_match_variants(value: Optional[str]) -> set[str]:
    """
    Build equivalent search variants for phone matching.
    - 91XXXXXXXXXX <-> XXXXXXXXXX (India)
    - keep raw digit token for all other countries
    """
    digits = _phone_digits(value)
    if not digits:
        return set()

    variants = {digits}
    if len(digits) == 10:
        variants.add(f"91{digits}")
    if len(digits) == 12 and digits.startswith("91"):
        variants.add(digits[2:])
    return variants


def _calc_line_total(qty: Decimal, unit_price: Decimal, discount_pct: Decimal) -> Decimal:
    discount_pct = discount_pct or Decimal("0")
    return (qty * unit_price * (1 - discount_pct / 100)).quantize(Decimal("0.01"))


def _recalc_order_totals(order: Order) -> None:
    """Recompute subtotal and total_amount from live items."""
    subtotal = sum(item.line_total for item in order.items) or Decimal("0")
    order.subtotal = subtotal
    order.total_amount = (
        subtotal
        - (order.discount_amount or Decimal("0"))
        + (order.tax_amount or Decimal("0"))
        + (order.shipping_charge or Decimal("0"))
    ).quantize(Decimal("0.01"))
    if order.payment_status == PaymentStatus.paid:
        # A settled order remains settled when totals are recalculated
        # (for example when a final courier charge is synchronized).
        order.amount_paid = order.total_amount
        order.amount_due = Decimal("0")
    else:
        order.amount_due = max(
            Decimal("0"),
            order.total_amount - (order.amount_paid or Decimal("0")),
        )
    
    # ── Partial COD: Recalculate cod_amount (Issue: Partial COD) ────────────
    if order.payment_method and hasattr(PaymentMethod, "partial_cod") and \
       order.payment_method.value == "partial_cod":
        # For partial COD: cod_amount = total_amount - advance_amount
        order.cod_amount = max(
            Decimal("0"),
            order.total_amount - (order.advance_amount or Decimal("0")),
        ).quantize(Decimal("0.01"))
    else:
        order.cod_amount = Decimal("0")


def _update_payment_status(order: Order) -> None:
    """Derive payment_status from amounts AND payment method.
    - UPI / bank_transfer / cheque: mark as paid immediately (prepaid)
    - Partial COD: mark as partial once advance is paid
    - COD: pending until delivered
    - Falls back to amount-based logic if amounts are present
    """
    method = getattr(order, 'payment_method', None)
    # If a manual override was already applied (via update_order), respect it
    # Otherwise auto-derive
    if order.amount_paid and order.amount_paid >= order.total_amount and order.total_amount > 0:
        order.payment_status = PaymentStatus.paid
        order.amount_paid = order.total_amount
        order.amount_due = Decimal("0")
    elif method and hasattr(PaymentMethod, "partial_cod") and \
         method.value == "partial_cod" and order.advance_amount and order.advance_amount > 0:
        # Partial COD with advance paid → mark as partial
        order.payment_status = PaymentStatus.partial
        order.amount_paid = min(order.advance_amount, order.total_amount)
        order.amount_due = max(Decimal("0"), order.total_amount - order.amount_paid)
    elif order.amount_paid and order.amount_paid > 0:
        order.payment_status = PaymentStatus.partial
        order.amount_due = max(Decimal("0"), order.total_amount - order.amount_paid)
    elif method and method.value in ('upi', 'bank_transfer', 'cheque'):
        # Prepaid methods → mark paid immediately
        order.payment_status = PaymentStatus.paid
        order.amount_paid = order.total_amount
        order.amount_due = Decimal("0")
    else:
        # COD or unset → pending
        order.payment_status = PaymentStatus.pending
        order.amount_paid = Decimal("0")
        order.amount_due = order.total_amount


def _sync_order_profit_posting(db: Session, order: Order) -> None:
    """Best-effort sync of order profit posting; never blocks order workflows."""
    try:
        from app.modules.profit_engine.service import upsert_order_profit_posting

        upsert_order_profit_posting(db, order.tenant_id, order.id)
        db.commit()
    except Exception as exc:
        db.rollback()
        log.warning("Order %s profit posting sync skipped: %s", order.order_number, exc)


# ─────────────────────────────────────────────────────────────
# Phone Lookup — check if phone already exists (customer/lead)
# ─────────────────────────────────────────────────────────────

def lookup_phone(db: Session, phone: str, current_user: Employee) -> dict:
    """
    Check if a phone number already belongs to a customer or lead.
    Returns match info so the employee can decide to reuse or create new.
    """
    phone_clean = phone.strip().replace(" ", "").replace("-", "")
    variants = list(_phone_match_variants(phone_clean))
    if not variants:
        return {"found": False}

    customer_phone_digits = func.regexp_replace(func.coalesce(Customer.phone, ""), r"\D", "", "g")

    customer = db.query(Customer).filter(
        Customer.tenant_id == current_user.tenant_id,
        customer_phone_digits.in_(variants),
        Customer.is_active == True,
    ).first()
    if customer:
        return {
            "found": True,
            "type": "customer",
            "id": str(customer.id),
            "name": customer.name,
            "phone": customer.phone,
            "alternate_phone": customer.alternate_phone,
            "address": customer.address,
            "city": customer.city,
            "state": customer.state,
            "pincode": customer.pincode,
            "customer_code": customer.unique_customer_code,
            "payment_mode_preference": customer.payment_mode_preference.value if customer.payment_mode_preference else None,
            "total_orders": customer.total_orders,
        }

    lead_phone_digits = func.regexp_replace(func.coalesce(Lead.phone, ""), r"\D", "", "g")

    lead = db.query(Lead).filter(
        Lead.tenant_id == current_user.tenant_id,
        lead_phone_digits.in_(variants),
        Lead.is_active == True,
    ).first()
    if lead:
        return {
            "found": True,
            "type": "lead",
            "id": str(lead.id),
            "name": lead.name,
            "phone": lead.phone,
            "alternate_phone": lead.alternate_phone,
            "city": lead.city,
            "state": lead.state,
            "lead_number": lead.lead_number,
            "lead_status": lead.status.value,
        }

    return {"found": False}


def _attach_order_whatsapp_journey(db: Session, tenant_id, orders: list[Order]) -> None:
    if not orders:
        return

    try:
        from app.modules.message_automation.service import get_order_whatsapp_journey_map

        journey_map = get_order_whatsapp_journey_map(
            db,
            tenant_id,
            [order.id for order in orders if getattr(order, "id", None)],
        )
    except Exception as exc:
        log.warning("Order WhatsApp journey load skipped: %s", exc)
        journey_map = {}

    for order in orders:
        setattr(order, "whatsapp_journey", journey_map.get(str(order.id)))


# ─────────────────────────────────────────────────────────────
# Customer Stats Recalculation (called after order create/update)
# ─────────────────────────────────────────────────────────────

def _recalculate_customer_stats(db: Session, customer: Customer) -> None:
    """
    Recalculate denormalized customer stats from live data.
    Called after an order is created or confirmed.
    """
    from app.models.shopify_order import ShopifyOrder as _ShopifyOrder

    manual_count = db.query(func.count(Order.id)).filter(
        Order.customer_id == customer.id,
        Order.tenant_id == customer.tenant_id,
    ).scalar() or 0

    shopify_count = db.query(func.count(_ShopifyOrder.id)).filter(
        _ShopifyOrder.customer_id == customer.id,
        _ShopifyOrder.tenant_id == customer.tenant_id,
    ).scalar() or 0

    customer.total_orders = manual_count + shopify_count

    if customer.total_orders > 0:
        manual_value = db.query(func.sum(Order.total_amount)).filter(
            Order.customer_id == customer.id,
            Order.tenant_id == customer.tenant_id,
        ).scalar() or Decimal("0")

        shopify_value = db.query(func.sum(_ShopifyOrder.total_price)).filter(
            _ShopifyOrder.customer_id == customer.id,
            _ShopifyOrder.tenant_id == customer.tenant_id,
        ).scalar() or Decimal("0")

        combined = Decimal(str(manual_value)) + Decimal(str(shopify_value))
        customer.average_order_value = (combined / customer.total_orders).quantize(Decimal("0.01"))

    # Update first_order_date if not set
    if not customer.first_order_date:
        earliest = db.query(func.min(Order.created_at)).filter(
            Order.customer_id == customer.id,
        ).scalar()
        if earliest:
            customer.first_order_date = earliest

    customer.last_order_date = datetime.now(timezone.utc)
    customer.last_seen_at = datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────
# Auto-create / find Customer for confirmed order
# ─────────────────────────────────────────────────────────────

def _ensure_customer(
    db: Session,
    current_user: Employee,
    name: str,
    phone: str,
    phone2: Optional[str],
    address: Optional[str],
    city: Optional[str],
    state: Optional[str],
    pincode: Optional[str],
    payment_method: Optional[str],
    existing_customer_id: Optional[str],
) -> Customer:
    """
    Find existing customer by ID or phone, or create a new one.
    Returns the Customer object.
    """
    # 1. Use explicit existing customer ID if provided
    if existing_customer_id:
        cust = db.query(Customer).filter(
            Customer.id == existing_customer_id,
            Customer.tenant_id == current_user.tenant_id,
        ).first()
        if cust:
            # Update address/info if we have better data now
            if address and not cust.address:
                cust.address = address
            if city and not cust.city:
                cust.city = city
            if state and not cust.state:
                cust.state = state
            if pincode and not cust.pincode:
                cust.pincode = pincode
            if phone2 and not cust.alternate_phone:
                cust.alternate_phone = phone2
            cust.last_order_date = datetime.now(timezone.utc)
            cust.updated_at = datetime.now(timezone.utc)
            # Don't increment here — let post-commit recalculation handle stats
            return cust

    # 2. Look up by phone
    phone_clean = phone.strip().replace(" ", "").replace("-", "") if phone else ""
    if phone_clean:
        variants = list(_phone_match_variants(phone_clean))
        customer_phone_digits = func.regexp_replace(func.coalesce(Customer.phone, ""), r"\D", "", "g")
        cust = db.query(Customer).filter(
            Customer.tenant_id == current_user.tenant_id,
            customer_phone_digits.in_(variants),
            Customer.is_active == True,
        ).first()
        if cust:
            cust.last_order_date = datetime.now(timezone.utc)
            cust.updated_at = datetime.now(timezone.utc)
            return cust

    # 3. Create new customer
    customer_code = next_customer_code(db, current_user.tenant_id)

    payment_mode = None
    if payment_method == "cod":
        payment_mode = PaymentMode.cod
    elif payment_method in ("upi", "bank_transfer", "cheque"):
        payment_mode = PaymentMode.prepaid

    cust = Customer(
        tenant_id=current_user.tenant_id,
        unique_customer_code=customer_code,
        name=name or "Unknown",
        phone=phone_clean or phone or "",
        alternate_phone=phone2,
        address=address,
        city=city,
        state=state,
        pincode=pincode,
        source=SourceType.manual,
        lead_status=CustomerLeadStatus.converted,
        payment_mode_preference=payment_mode,
        created_by_employee_id=current_user.id,
        assigned_employee_id=current_user.id,
        first_order_date=datetime.now(timezone.utc),
        last_order_date=datetime.now(timezone.utc),
        total_orders=1,
    )
    db.add(cust)
    db.flush()
    return cust


# ─────────────────────────────────────────────────────────────
# Auto-create Lead for not_confirmed order
# ─────────────────────────────────────────────────────────────

def _ensure_lead(
    db: Session,
    current_user: Employee,
    name: str,
    phone: str,
    phone2: Optional[str],
    city: Optional[str],
    state: Optional[str],
    reason: Optional[str],
    product_interest: Optional[str],
    followup_date=None,
) -> Lead:
    """Create (or reuse) a Lead for a not-confirmed order."""
    phone_clean = phone.strip().replace(" ", "").replace("-", "") if phone else ""

    # Check if lead already exists for this phone
    if phone_clean:
        variants = list(_phone_match_variants(phone_clean))
        lead_phone_digits = func.regexp_replace(func.coalesce(Lead.phone, ""), r"\D", "", "g")
        existing = db.query(Lead).filter(
            Lead.tenant_id == current_user.tenant_id,
            lead_phone_digits.in_(variants),
            Lead.is_active == True,
        ).first()
        if existing:
            # Log new activity
            act = LeadActivity(
                tenant_id=current_user.tenant_id,
                lead_id=existing.id,
                employee_id=current_user.id,
                activity_type=LeadActivityType.note,
                note=f"Not confirmed order created. Reason: {reason or 'not specified'}",
                new_status=existing.status,
            )
            db.add(act)
            db.flush()
            return existing

    # Count leads for sequential number
    lead_number = next_lead_number(db, current_user.tenant_id)

    lead = Lead(
        tenant_id=current_user.tenant_id,
        lead_number=lead_number,
        name=name or "Unknown",
        phone=phone_clean or phone or "",
        alternate_phone=phone2,
        city=city,
        state=state,
        source=LeadSource.manual,
        status=LeadPipelineStatus.created,
        product_interest=product_interest,
        assigned_to_id=current_user.id,
        created_by_id=current_user.id,
        next_followup_date=followup_date,
        notes=f"Not confirmed. Reason: {reason or 'not specified'}",
    )
    db.add(lead)
    db.flush()

    act = LeadActivity(
        tenant_id=current_user.tenant_id,
        lead_id=lead.id,
        employee_id=current_user.id,
        activity_type=LeadActivityType.note,
        note=f"Lead created from not-confirmed order. {reason or ''}",
        new_status=LeadPipelineStatus.created,
    )
    db.add(act)
    db.flush()
    return lead


# ─────────────────────────────────────────────────────────────
# Inventory reduction on confirm
# ─────────────────────────────────────────────────────────────

def _sync_lead_order_link(db: Session, order: "Order", tenant_id, old_lead_id=None) -> None:
    """
    Keep the bidirectional Lead ↔ Order link consistent.

    Rules:
    - When an order gets a new lead_id → set Lead.order_id = order.id
    - When an order's lead_id is cleared or replaced → clear old Lead.order_id
    Prevents stale / orphaned cross-references (Issue #41).
    """
    # Clear the old lead's back-reference if lead_id is changing away from it
    if old_lead_id and old_lead_id != order.lead_id:
        old_lead = db.query(Lead).filter(
            Lead.id == old_lead_id,
            Lead.tenant_id == tenant_id,
        ).first()
        if old_lead and old_lead.order_id == order.id:
            old_lead.order_id = None

    # Set the new lead's back-reference
    if order.lead_id:
        new_lead = db.query(Lead).filter(
            Lead.id == order.lead_id,
            Lead.tenant_id == tenant_id,
        ).first()
        if new_lead and new_lead.order_id != order.id:
            new_lead.order_id = order.id


def _reduce_inventory_for_order(db: Session, order: Order, current_user: Employee) -> None:
    """
    Reduce inventory for each order item where SKU matches a product.
    Called when order is confirmed.
    """
    from app.modules.inventory import service as inv_svc
    from app.models.inventory import MovementType

    for item in order.items:
        if not item.sku:
            continue
        product = db.query(Product).filter(
            Product.tenant_id == current_user.tenant_id,
            Product.sku == item.sku,
            Product.status == ProductStatus.active,
        ).first()
        if not product:
            continue

        qty = Decimal(str(item.quantity or 0))
        if qty <= 0:
            continue

        # Enforce stock guardrails only when strict mode is enabled.
        if settings.ENFORCE_STOCK_VALIDATION:
            inv_svc.validate_stock(
                db=db,
                tenant_id=current_user.tenant_id,
                product_id=product.id,
                required_qty=qty,
            )

        # Single-path movement write via inventory service.
        inv_svc.record_movement(
            db=db,
            tenant_id=current_user.tenant_id,
            product_id=product.id,
            movement_type=MovementType.sale.value,
            quantity_change=-qty,
            reference_id=order.id,
            reference_type="order",
            note=f"Order {order.order_number} confirmed",
            created_by_id=current_user.id,
            commit=False,
        )
    db.flush()


def _restore_inventory_for_return(db: Session, order: Order, current_user: Employee) -> None:
    """
    Restore inventory when an order is marked as returned.
    Creates a return_in movement for each order item that maps to an active product.
    Called inside update_order_status before db.commit() so it's part of the same tx.
    """
    from app.modules.inventory import service as inv_svc
    from app.models.inventory import MovementType

    for item in order.items:
        if not item.sku:
            continue
        product = db.query(Product).filter(
            Product.tenant_id == current_user.tenant_id,
            Product.sku == item.sku,
            Product.status == ProductStatus.active,
        ).first()
        if not product:
            continue

        qty = Decimal(str(item.quantity or 0))
        if qty <= 0:
            continue

        # Check if a return_in movement already exists for this order+product
        # to avoid double-restoring on repeated status saves.
        from app.models.inventory import InventoryMovement, MovementType as MT
        already = db.query(InventoryMovement).filter(
            InventoryMovement.tenant_id == current_user.tenant_id,
            InventoryMovement.product_id == product.id,
            InventoryMovement.movement_type == MT.return_in,
            InventoryMovement.reference_id == order.id,
        ).first()
        if already:
            continue

        inv_svc.record_movement(
            db=db,
            tenant_id=current_user.tenant_id,
            product_id=product.id,
            movement_type=MovementType.return_in.value,
            quantity_change=qty,
            reference_id=order.id,
            reference_type="order",
            note=f"Return: Order {order.order_number}",
            created_by_id=current_user.id,
            commit=False,
        )
    db.flush()


# ─────────────────────────────────────────────────────────────
# CRUD
# ─────────────────────────────────────────────────────────────

def create_order(db: Session, data: OrderCreate, current_user: Employee) -> Order:
    """
    Full Fulfillment Engine Create Order.

    Flow:
    - confirmed (default) → auto-create/link customer + reduce inventory + WhatsApp
    - not_confirmed → auto-create/link lead (no inventory, no WhatsApp)
    - customer_id is now OPTIONAL — phone + name can be provided for auto-lookup/create
    """
    # ── Determine order intent status ─────────────────────────
    order_intent = getattr(data, 'order_intent', 'confirmed')  # 'confirmed' | 'not_confirmed'
    is_not_confirmed = (order_intent == 'not_confirmed')

    customer_id = None
    lead_id = None

    # ── Phase 5: If caller passes lead_id directly (Move to Order flow) ───
    explicit_lead_id = getattr(data, 'lead_id', None)

    if is_not_confirmed:
        # Auto-create / find lead
        lead = _ensure_lead(
            db, current_user,
            name=getattr(data, 'customer_name', None) or "",
            phone=getattr(data, 'customer_phone', None) or "",
            phone2=getattr(data, 'customer_phone2', None),
            city=data.delivery_city,
            state=data.delivery_state,
            reason=getattr(data, 'not_confirmed_reason', None),
            product_interest=", ".join(i.product_name for i in data.items),
            followup_date=getattr(data, 'followup_date', None),
        )
        lead_id = lead.id
        # Still need a customer_id for the FK — use a dummy or create minimal customer
        # We create a temp customer to satisfy the FK
        cust = _ensure_customer(
            db, current_user,
            name=getattr(data, 'customer_name', None) or lead.name,
            phone=getattr(data, 'customer_phone', None) or lead.phone,
            phone2=getattr(data, 'customer_phone2', None),
            address=data.delivery_address,
            city=data.delivery_city,
            state=data.delivery_state,
            pincode=data.delivery_pincode,
            payment_method=data.payment_method.value if data.payment_method else None,
            existing_customer_id=str(data.customer_id) if data.customer_id else None,
        )
        customer_id = cust.id
    else:
        # Confirmed order — auto-create/find customer
        cust = _ensure_customer(
            db, current_user,
            name=getattr(data, 'customer_name', None) or "",
            phone=getattr(data, 'customer_phone', None) or "",
            phone2=getattr(data, 'customer_phone2', None),
            address=data.delivery_address,
            city=data.delivery_city,
            state=data.delivery_state,
            pincode=data.delivery_pincode,
            payment_method=data.payment_method.value if data.payment_method else None,
            existing_customer_id=str(data.customer_id) if data.customer_id else None,
        )
        customer_id = cust.id
        # Phase 5: link to existing lead if provided
        if explicit_lead_id:
            lead_id = explicit_lead_id
            # Update the lead: mark it as success_won and link to this customer + order
            src_lead = db.query(Lead).filter(
                Lead.id == explicit_lead_id,
                Lead.tenant_id == current_user.tenant_id,
            ).first()
            if src_lead:
                src_lead.status = LeadPipelineStatus.success_won
                src_lead.converted_customer_id = cust.id
                from datetime import datetime, timezone
                src_lead.converted_at = datetime.now(timezone.utc)
                src_lead.is_archived = True
                db.flush()

    order_number = _next_order_number(db, current_user.tenant_id, current_user.tenant.slug if current_user.tenant else "")

    # Determine shipping service default based on COD vs Prepaid
    shipping_service = getattr(data, 'shipping_service', None)
    if not shipping_service:
        if data.payment_method and data.payment_method.value == 'cod':
            shipping_service = 'speed_post'
        else:
            shipping_service = 'parcel'

    final_status = OrderStatus.confirmed if not is_not_confirmed else OrderStatus.draft

    order = Order(
        tenant_id=current_user.tenant_id,
        order_number=order_number,
        customer_id=customer_id,
        status=final_status,
        payment_method=data.payment_method,
        delivery_address=data.delivery_address,
        delivery_name=getattr(data, 'delivery_name', None) or getattr(data, 'customer_name', None),
        address_name2=getattr(data, 'address_name2', None),
        delivery_phone2=getattr(data, 'customer_phone2', None),
        delivery_city=data.delivery_city,
        delivery_district=getattr(data, 'delivery_district', None),
        delivery_state=data.delivery_state,
        delivery_pincode=data.delivery_pincode,
        address_raw=getattr(data, 'address_raw', None),
        expected_delivery=data.expected_delivery,
        tracking_number=data.tracking_number,
        courier_name=data.courier_name,
        shipping_service=shipping_service,
        india_post_customer_id=getattr(data, 'india_post_customer_id', None),
        courier_code=getattr(data, 'courier_code', None),
        discount_amount=data.discount_amount or Decimal("0"),
        tax_amount=data.tax_amount or Decimal("0"),
        shipping_charge=data.shipping_charge or Decimal("0"),
        advance_amount=getattr(data, 'advance_amount', Decimal("0")) or Decimal("0"),  # Partial COD
        assigned_to_id=data.assigned_to_id,
        created_by_id=current_user.id,
        notes=data.notes,
        not_confirmed_reason=getattr(data, 'not_confirmed_reason', None),
        order_source=getattr(data, 'order_source', 'manual'),
        gst_invoice=getattr(data, 'gst_invoice', True),
        lead_id=lead_id,
        shipping_partner_id=getattr(data, 'shipping_partner_id', None),
    )
    db.add(order)
    db.flush()

    # ── Line items ────────────────────────────────────────────
    for item_data in data.items:
        discount = item_data.discount_pct or Decimal("0")
        line_total = _calc_line_total(item_data.quantity, item_data.unit_price, discount)
        item = OrderItem(
            tenant_id=current_user.tenant_id,
            order_id=order.id,
            product_name=item_data.product_name,
            sku=item_data.sku,
            quantity=item_data.quantity,
            unit=item_data.unit,
            unit_price=item_data.unit_price,
            discount_pct=discount,
            line_total=line_total,
            notes=item_data.notes,
        )
        db.add(item)

    db.flush()
    db.refresh(order)
    _recalc_order_totals(order)
    _update_payment_status(order)

    # ── Phase 5: sync Lead.order_id ↔ Order.lead_id (Issue #41) ──────────
    # Covers all cases: explicit lead_id, auto-created lead (not-confirmed), etc.
    if order.lead_id:
        _sync_lead_order_link(db, order, current_user.tenant_id)

    # ── Status history ────────────────────────────────────────
    history = OrderStatusHistory(
        tenant_id=current_user.tenant_id,
        order_id=order.id,
        employee_id=current_user.id,
        old_status=None,
        new_status=final_status,
        note="Order created" + (" (not confirmed)" if is_not_confirmed else " — confirmed"),
    )
    db.add(history)

    # ── Confirmed: reduce inventory ───────────────────────────
    if not is_not_confirmed:
        _reduce_inventory_for_order(db, order, current_user)

    # ── Recalculate customer stats ────────────────────────────
    if customer_id:
        cust_obj = db.query(Customer).filter(Customer.id == customer_id).first()
        if cust_obj:
            _recalculate_customer_stats(db, cust_obj)

    db.commit()
    db.refresh(order)

    _sync_order_profit_posting(db, order)

    # ── Log order creation ────────────────────────────────────
    log_activity(
        db          = db,
        tenant_id   = str(current_user.tenant_id),
        actor       = current_user,
        module      = LogModule.ORDERS,
        action      = "order.create",
        level       = LogLevel.INFO,
        message     = f"Order {order.order_number} created ({'not confirmed' if is_not_confirmed else 'confirmed'})",
        detail      = {
            "order_id":      str(order.id),
            "order_number":  order.order_number,
            "status":        final_status.value,
            "intent":        order_intent,
            "item_count":    len(data.items),
            "total":         float(order.total_amount or 0),
            "payment":       data.payment_method.value if data.payment_method else None,
        },
    )

    # ── Automated customer messaging: order-created confirmation ───
    if not is_not_confirmed and cust.phone:
        try:
            from app.modules.message_automation.service import handle_order_created

            handle_order_created(db, order)
            db.commit()
        except Exception as exc:
            db.rollback()
            log.warning("Order %s message automation queue skipped: %s", order.order_number, exc)

    # ── Invalidate orders caches ────────────────────────────────────
    invalidate_cache("orders:")

    return order


def list_orders(db: Session, filters: OrderFilters, current_user: Employee) -> dict:
    query = db.query(Order)  # include inactive — frontend fades and shows reactivate button
    query = apply_tenant_filter(query, Order, current_user)
    query = _apply_order_filters(query, filters)

    total = query.count()

    # Server-side grouping & ordering
    # Groups (top → bottom):
    #  0 → returned TODAY                              → amber highlight
    #  1 → no tracking, 2+ days old, active           → light red
    #  2 → new orders (draft/confirmed, ≤ 2 days)    → normal
    #  3 → shipped / out_for_delivery (≤ 7 days)      → pastel yellow
    #  4 → shipped / out_for_delivery (7+ days)       → pastel blue
    #  5 → everything else
    #  6 → delivered                                  → pastel green, bottom
    # NOTE: case() uses SA 2.0 positional-arg syntax (list form removed in 2.0)
    from sqlalchemy import case
    from datetime import timedelta

    now_utc    = datetime.now(timezone.utc)
    two_days   = now_utc - timedelta(days=2)
    seven_days = now_utc - timedelta(days=7)
    today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)

    no_tracking_cond   = or_(Order.tracking_number == None, Order.tracking_number == "")
    active_status_cond = Order.status.notin_([
        OrderStatus.delivered, OrderStatus.cancelled, OrderStatus.returned
    ])

    group_rank = case(
        (and_(Order.status == OrderStatus.returned,
              func.coalesce(Order.updated_at, Order.created_at) >= today_start), 0),
        (and_(no_tracking_cond, Order.created_at < two_days, active_status_cond), 1),
        (and_(Order.status.in_([OrderStatus.draft, OrderStatus.confirmed]),
              Order.created_at >= two_days), 2),
        (and_(Order.status.in_([OrderStatus.shipped, OrderStatus.out_for_delivery]),
              func.coalesce(Order.updated_at, Order.created_at) >= seven_days), 3),
        (and_(Order.status.in_([OrderStatus.shipped, OrderStatus.out_for_delivery]),
              func.coalesce(Order.updated_at, Order.created_at) < seven_days), 4),
        (Order.status == OrderStatus.delivered, 6),
        else_=5,
    )

    # Keep extracted migration orders at the bottom of the list regardless of
    # their status/no-tracking heuristics so recent live orders stay visible first.
    extracted_rank = case(
        (
            or_(
                Order.order_number.ilike("PUR-%"),
                Order.notes.ilike("%SOURCE_ORDER_ID=%"),
            ),
            1,
        ),
        else_=0,
    )

    orders = (
        query
        .options(
            joinedload(Order.customer),
            selectinload(Order.items),
            selectinload(Order.payments),
            selectinload(Order.status_history)
        )
        .order_by(extracted_rank.asc(), group_rank.asc(), Order.created_at.desc())
        .offset((filters.page - 1) * filters.page_size)
        .limit(filters.page_size)
        .all()
    )

    _attach_order_whatsapp_journey(db, current_user.tenant_id, orders)

    return {
        "total": total,
        "page": filters.page,
        "page_size": filters.page_size,
        "results": [OrderResponse.model_validate(o) for o in orders],
    }


def _apply_order_filters(query, filters: Optional[OrderFilters]):
    """Apply the same filter semantics for list and stats queries."""
    if not filters:
        return query

    # is_active filter: True=active only, False=inactive only, None=all
    if filters.is_active is not None:
        query = query.filter(Order.is_active == filters.is_active)

    if filters.status:
        query = query.filter(Order.status == filters.status)
    if filters.payment_status:
        query = query.filter(Order.payment_status == filters.payment_status)
    if filters.customer_id:
        query = query.filter(Order.customer_id == filters.customer_id)
    if filters.assigned_to_id:
        query = query.filter(Order.assigned_to_id == filters.assigned_to_id)
    if filters.search:
        # Global search: order number, customer details, delivery details, tracking
        query = query.outerjoin(Order.customer)
        term = f"%{filters.search}%"
        clauses = [
            Order.order_number.ilike(term),
            Customer.name.ilike(term),
            Order.delivery_name.ilike(term),
            Order.delivery_address.ilike(term),
            Order.tracking_number.ilike(term),
        ]

        digit_variants = _phone_match_variants(filters.search)
        if digit_variants:
            order_phone_digits = func.regexp_replace(func.coalesce(Order.delivery_phone2, ""), r"\D", "", "g")
            customer_phone_digits = func.regexp_replace(func.coalesce(Customer.phone, ""), r"\D", "", "g")
            for v in digit_variants:
                digit_term = f"%{v}%"
                clauses.append(order_phone_digits.ilike(digit_term))
                clauses.append(customer_phone_digits.ilike(digit_term))

        query = query.filter(or_(*clauses))
    if filters.created_after:
        query = query.filter(func.date(Order.created_at) >= filters.created_after)
    if filters.created_before:
        query = query.filter(func.date(Order.created_at) <= filters.created_before)

    return query


def get_order(db: Session, order_id: str, current_user: Employee) -> Order:
    order = db.query(Order).options(
        joinedload(Order.customer)
    ).filter(
        Order.id == order_id,
        Order.tenant_id == current_user.tenant_id,
        Order.is_active == True,
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    _attach_order_whatsapp_journey(db, current_user.tenant_id, [order])
    return order


def update_order(db: Session, order_id: str, data: OrderUpdate, current_user: Employee) -> Order:
    order = get_order(db, order_id, current_user)
    previous_tracking_number = order.tracking_number
    previous_status = order.status

    updated = data.model_dump(exclude_unset=True)

    # ── Allow status/payment-only updates even on terminal orders ──────────
    non_status_fields = {k for k in updated if k not in ('status', 'payment_status', 'payment_method')}
    if non_status_fields and order.status in (OrderStatus.delivered, OrderStatus.cancelled, OrderStatus.returned):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot edit a {order.status.value} order",
        )

    # ── Capture old lead_id before any mutation (Issue #41) ───────────────
    old_lead_id = order.lead_id

    # Handle manual status override (pop before loop to apply cleanly)
    manual_status = updated.pop("status", None)

    # Handle manual payment_status override separately (don't let loop overwrite amounts)
    manual_payment_status = updated.pop("payment_status", None)

    # Pop items — handled separately via OrderItem replacement, cannot use setattr
    items_payload = updated.pop("items", None)

    for field, value in updated.items():
        # Skip computed @property fields (items_summary, customer_name) — they have no setter
        if isinstance(getattr(type(order), field, None), property):
            continue
        setattr(order, field, value)

    # Apply manual order status override
    if manual_status is not None:
        order.status = OrderStatus(manual_status) if isinstance(manual_status, str) else manual_status
        
        # Auto-mark as paid if order is delivered (since delivery implies payment was collected)
        if order.status == OrderStatus.delivered:
            order.payment_status = PaymentStatus.paid
            order.amount_paid = order.total_amount
            order.amount_due = Decimal("0")

    # ── Auto-transition to shipped when tracking number is assigned ──────────
    # If order is in a pre-shipped state and a tracking number is being set, auto-advance to shipped
    pre_shipped_statuses = (OrderStatus.confirmed, OrderStatus.processing, OrderStatus.packed)
    if "tracking_number" in updated and updated["tracking_number"] and order.status in pre_shipped_statuses:
        old_status = order.status
        order.status = OrderStatus.shipped
        # Create status history entry for this auto-transition
        history_entry = OrderStatusHistory(
            tenant_id=order.tenant_id,
            order_id=order.id,
            employee_id=current_user.id,
            old_status=old_status,
            new_status=OrderStatus.shipped,
            note=f"Auto-transitioned to shipped: tracking {updated['tracking_number']} assigned",
        )
        db.add(history_entry)

    # If payment_method changed, handle COD/partial_cod/prepaid transitions
    if "payment_method" in updated and not manual_payment_status:
        method_val = updated["payment_method"]
        method_str = method_val.value if hasattr(method_val, 'value') else str(method_val)
        if method_str in ('upi', 'bank_transfer', 'cheque'):
            order.payment_status = PaymentStatus.paid
            order.amount_paid = order.total_amount
            order.amount_due = Decimal("0")
            order.advance_amount = Decimal("0")
            order.cod_amount = Decimal("0")
        elif method_str == 'cod':
            order.advance_amount = Decimal("0")
            order.cod_amount = Decimal("0")
            # COD = full amount due on delivery
            order.amount_paid = Decimal("0")
            order.amount_due = order.total_amount
            order.payment_status = PaymentStatus.pending
        elif method_str == 'partial_cod':
            # Reset amounts to match advance_amount semantics
            adv = order.advance_amount or Decimal("0")
            order.amount_paid = adv
            order.amount_due = max(Decimal("0"), order.total_amount - adv)
            _recalc_order_totals(order)
            _update_payment_status(order)

    # If advance_amount changed on a partial_cod order, recalculate cod_amount and payment status
    if "advance_amount" in updated:
        order.advance_amount = max(Decimal("0"), updated["advance_amount"] or Decimal("0"))
        if order.payment_method and hasattr(order.payment_method, 'value') and order.payment_method.value == 'partial_cod':
            _recalc_order_totals(order)
            _update_payment_status(order)

    # Apply manual payment_status override last (highest priority)
    if manual_payment_status:
        order.payment_status = PaymentStatus(manual_payment_status) if isinstance(manual_payment_status, str) else manual_payment_status
        # Sync amounts accordingly
        if order.payment_status == PaymentStatus.paid:
            order.amount_paid = order.total_amount
            order.amount_due = Decimal("0")
        elif order.payment_status == PaymentStatus.pending:
            order.amount_paid = Decimal("0")
            order.amount_due = order.total_amount

    # ── Handle manual amount_paid and amount_due edits (for draft orders) ──
    # If user manually sets amount_paid/amount_due, auto-infer payment status if not explicitly set
    if "amount_paid" in updated or "amount_due" in updated:
        if "amount_paid" in updated:
            order.amount_paid = max(Decimal("0"), updated["amount_paid"] or Decimal("0"))
        if "amount_due" in updated:
            order.amount_due = max(Decimal("0"), updated["amount_due"] or Decimal("0"))
        
        # Auto-infer payment_status from amounts if not manually overridden
        if not manual_payment_status:
            if order.amount_paid >= order.total_amount and order.total_amount > 0:
                order.payment_status = PaymentStatus.paid
            elif order.amount_paid > 0:
                order.payment_status = PaymentStatus.partial
            else:
                order.payment_status = PaymentStatus.pending

    # ── Replace order items if provided ──────────────────────────────────────
    if items_payload is not None:
        # Delete existing items
        db.query(OrderItem).filter(OrderItem.order_id == order.id).delete()
        new_subtotal = Decimal("0")
        for item_data in items_payload:
            qty   = Decimal(str(item_data.get("quantity", 1)))
            price = Decimal(str(item_data.get("unit_price", 0)))
            disc  = Decimal(str(item_data.get("discount_pct", 0)))
            line  = qty * price * (1 - disc / 100)
            new_subtotal += line
            new_item = OrderItem(
                tenant_id    = order.tenant_id,
                order_id     = order.id,
                product_name = item_data.get("product_name", ""),
                sku          = item_data.get("sku"),
                quantity     = qty,
                unit         = item_data.get("unit", "piece"),
                unit_price   = price,
                discount_pct = disc,
                line_total   = line,
            )
            db.add(new_item)
        db.flush()
        order.subtotal = new_subtotal
        # Rebuild total_amount from subtotal ± discount/shipping/tax
        order.total_amount = max(
            Decimal("0"),
            new_subtotal
            - (order.discount_amount or Decimal("0"))
            + (order.shipping_charge or Decimal("0"))
            + (order.tax_amount or Decimal("0"))
        )
        # items_summary is a computed @property — no need to set it manually

    # Recalc totals if any financial field changed
    if items_payload is not None or any(f in updated for f in ("discount_amount", "tax_amount", "shipping_charge")):
        db.refresh(order)
        _recalc_order_totals(order)
        if order.payment_method and hasattr(order.payment_method, 'value') and order.payment_method.value == 'partial_cod':
            _update_payment_status(order)

    # ── Sync Lead.order_id ↔ Order.lead_id if lead_id changed (Issue #41) ─
    if "lead_id" in updated:
        db.flush()
        _sync_lead_order_link(db, order, current_user.tenant_id, old_lead_id=old_lead_id)

    # ── Sync delivery edits back to the linked Customer record ─────────────
    # When an employee updates delivery details on an order, keep the Customer
    # profile in sync so the order list, customer page, and future orders all
    # show the corrected information.
    _customer_sync_fields = {
        "delivery_name":    "name",
        "delivery_address": "address",
        "delivery_city":    "city",
        "delivery_state":   "state",
        "delivery_pincode": "pincode",
    }
    customer_dirty = {
        cust_field: updated[order_field]
        for order_field, cust_field in _customer_sync_fields.items()
        if order_field in updated and updated[order_field] is not None
    }
    if customer_dirty and order.customer_id:
        customer = db.query(Customer).filter(Customer.id == order.customer_id).first()
        if customer:
            for cust_field, value in customer_dirty.items():
                setattr(customer, cust_field, value)

    order.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(order)

    try:
        from app.modules.message_automation.service import handle_order_changed

        handle_order_changed(
            db,
            order,
            previous_tracking_number=previous_tracking_number,
            previous_status=previous_status,
        )
        db.commit()
        db.refresh(order)
    except Exception as exc:
        db.rollback()
        log.warning("Order %s message automation queue skipped: %s", order.order_number, exc)

    _sync_order_profit_posting(db, order)
    
    # ── Invalidate orders caches ────────────────────────────────────
    invalidate_cache("orders:")
    
    return order


def delete_order(db: Session, order_id: str, current_user: Employee) -> dict:
    order = get_order(db, order_id, current_user)

    order.is_active = False
    order.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": f"Order {order.order_number} deleted"}


def reactivate_order(db: Session, order_id: str, current_user: Employee) -> dict:
    """Restore a soft-deleted order (set is_active=True)."""
    order = (
        db.query(Order)
        .filter(Order.id == order_id, Order.tenant_id == current_user.tenant_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.is_active = True
    order.updated_at = datetime.now(timezone.utc)
    db.commit()
    _sync_order_profit_posting(db, order)
    return {"message": f"Order {order.order_number} reactivated", "id": str(order.id)}


# ─────────────────────────────────────────────────────────────
# Status Flow
# ─────────────────────────────────────────────────────────────

# Valid forward transitions
_ALLOWED_TRANSITIONS: dict[OrderStatus, list[OrderStatus]] = {
    OrderStatus.draft:            [OrderStatus.confirmed, OrderStatus.cancelled],
    OrderStatus.confirmed:        [OrderStatus.processing, OrderStatus.cancelled],
    OrderStatus.processing:       [OrderStatus.packed, OrderStatus.cancelled],
    OrderStatus.packed:           [OrderStatus.shipped, OrderStatus.cancelled],
    OrderStatus.shipped:          [OrderStatus.out_for_delivery, OrderStatus.returned],
    OrderStatus.out_for_delivery: [OrderStatus.delivered, OrderStatus.returned],
    OrderStatus.delivered:        [OrderStatus.returned],
    OrderStatus.cancelled:        [],
    OrderStatus.returned:         [],
}

# Map order statuses → WA trigger events
_STATUS_TO_WA_TRIGGER: dict[OrderStatus, str] = {
    OrderStatus.confirmed:  "order_confirmed",
    OrderStatus.packed:     "order_packed",
    OrderStatus.shipped:    "order_shipped",
    OrderStatus.delivered:  "order_delivered",
}


def _trigger_wa_notification(
    db: Session,
    order: Order,
    new_status: OrderStatus,
    current_user: Employee,
    explicit_trigger: str | None = None,
) -> None:
    """
    Fire-and-forget WhatsApp notification via WABIS workflow URL
    when an order reaches a trigger status (created, confirmed, packed, shipped, delivered).
    Runs async inside an event loop; any failure is logged but never blocks.

    Pass explicit_trigger='order_created' when calling from create_order.
    """
    import asyncio

    trigger_event = explicit_trigger or _STATUS_TO_WA_TRIGGER.get(new_status)
    if not trigger_event:
        return

    # Skip if already sent (for confirmed/shipped flags)
    if new_status == OrderStatus.confirmed and order.wa_confirmed_sent:
        return
    if new_status == OrderStatus.shipped and order.wa_shipped_sent:
        return

    # Get customer phone
    customer = order.customer
    if not customer or not customer.phone:
        log.debug("Order %s: no customer phone — skipping WA notification", order.order_number)
        return

    phone = customer.phone.strip()
    if not phone:
        return

    # Build item summary for label/confirmation messages
    try:
        item_lines = "\n".join(
            f"• {i.product_name} x{i.quantity} = ₹{i.line_total}"
            for i in (order.items or [])
        )
        items_summary = ", ".join(
            f"{i.product_name}({i.quantity})" for i in (order.items or [])
        )
    except Exception:
        item_lines = ""
        items_summary = ""

    # Build variables for the payload template
    variables = {
        "customer_name":   customer.name or "",
        "name":            customer.name or "",
        "phone":           phone,
        "order_number":    order.order_number or "",
        "order_id":        str(order.id),
        "total_amount":    str(order.total_amount or ""),
        "tracking_number": order.tracking_number or "",
        "courier_name":    order.courier_name or "",
        "status":          new_status.value if new_status else trigger_event,
        # Label / confirmation extras
        "delivery_address": order.delivery_address or "",
        "delivery_city":    order.delivery_city or "",
        "delivery_state":   order.delivery_state or "",
        "delivery_pincode": order.delivery_pincode or "",
        "payment_method":   order.payment_method.value if order.payment_method else "",
        "items_text":       item_lines,
        "items_summary":    items_summary,
        "shipping_service": order.shipping_service or "",
    }

    async def _fire():
        try:
            from app.modules.wa_engine.service import send_order_notification
            from app.models.wa_engine import WaConversation, WaMessageDirection

            # ── 24-hour window check ──────────────────────────────
            # Check if this customer's last INBOUND message was within 24h.
            # If outside, use the utility workflow URL (template message).
            use_utility = False
            try:
                from app.models.wa_engine import WaSubscriber
                subscriber = (
                    db.query(WaSubscriber)
                    .filter(
                        WaSubscriber.tenant_id == current_user.tenant_id,
                        WaSubscriber.phone_number == phone,
                    )
                    .first()
                )
                if subscriber:
                    conv = (
                        db.query(WaConversation)
                        .filter(WaConversation.subscriber_id == subscriber.id)
                        .first()
                    )
                    if conv and conv.last_message_at:
                        last_in_direction = conv.last_message_direction
                        age_hours = (
                            datetime.now(timezone.utc) - conv.last_message_at
                        ).total_seconds() / 3600
                        # Outside 24h window = no inbound in last 24h
                        if last_in_direction != WaMessageDirection.inbound or age_hours > 24:
                            use_utility = True
                    else:
                        # No conversation history = never messaged us = outside window
                        use_utility = True
                else:
                    # No subscriber record = outside window
                    use_utility = True
            except Exception as e:
                log.debug("Could not check 24h window: %s", e)
                use_utility = False  # default to regular if check fails

            result = await send_order_notification(
                db=db,
                tenant_id=current_user.tenant_id,
                trigger_event=trigger_event,
                phone=phone,
                variables=variables,
                use_utility_fallback=use_utility,
            )
            if result and result.get("success"):
                # Set the flag so we don't re-send
                if new_status == OrderStatus.confirmed or trigger_event == "order_created":
                    order.wa_confirmed_sent = True
                elif new_status == OrderStatus.shipped:
                    order.wa_shipped_sent = True
                db.commit()
                log.info("WA notification sent for order %s → %s (utility=%s)",
                         order.order_number, trigger_event, use_utility)
            elif result:
                log.warning("WA notification failed for order %s: %s", order.order_number, result.get("message"))
        except Exception as exc:
            log.exception("WA notification error for order %s: %s", order.order_number, exc)

    # Run the async notification
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_fire())
    except RuntimeError:
        # No running loop — create one (shouldn't happen in FastAPI, but safety net)
        asyncio.run(_fire())


def update_order_status(
    db: Session,
    order_id: str,
    data: OrderStatusUpdate,
    current_user: Employee,
) -> Order:
    order = get_order(db, order_id, current_user)
    old_status = order.status
    previous_tracking_number = order.tracking_number

    # ── Update tracking info first (will affect auto-transition logic) ──
    if data.tracking_number:
        order.tracking_number = data.tracking_number
    if data.courier_name:
        order.courier_name = data.courier_name

    # ── Auto-transition logic: if tracking is being assigned, advance to shipped ──
    # If order is in a pre-shipped state and a tracking number is being set,
    # auto-advance to shipped (unless manually requesting a different status)
    pre_shipped_statuses = (OrderStatus.confirmed, OrderStatus.processing, OrderStatus.packed)
    
    # Detect if we're assigning a tracking number to a pre-shipped order
    # and user is trying to move to "shipped" status
    if (data.tracking_number and 
        order.status in pre_shipped_statuses and 
        data.status == OrderStatus.shipped):
        # This is the natural flow: user clicked "Mark Shipped" after assigning tracking
        # Auto-transition creates a note explaining the auto-transition happened
        pass  # Allow transition below
    elif (data.tracking_number and 
          order.status in pre_shipped_statuses and 
          data.status != OrderStatus.shipped):
        # User is assigning tracking but trying to move to a non-shipped status
        # For now, allow the manual override (user knows what they're doing)
        pass
    elif data.status == old_status:
        return order

    allowed = _ALLOWED_TRANSITIONS.get(old_status, [])
    if data.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot move from '{old_status.value}' to '{data.status.value}'. "
                   f"Allowed: {[s.value for s in allowed]}",
        )

    order.status = data.status
    order.updated_at = datetime.now(timezone.utc)

    # Auto-set delivered_at
    if data.status == OrderStatus.delivered:
        order.delivered_at = datetime.now(timezone.utc)
    
    # Auto-mark as paid if delivered (COD orders)
    if data.status == OrderStatus.delivered and not order.payment_status == PaymentStatus.paid:
        if order.payment_method in (PaymentMethod.cod, PaymentMethod.partial_cod, None):
            order.payment_status = PaymentStatus.paid
            order.amount_paid = order.total_amount
            order.amount_due = Decimal("0")

    # Build note: auto-transition info when tracking is assigned
    note = data.note or ""
    if data.tracking_number and old_status != OrderStatus.shipped:
        if note:
            note += f" (tracking {data.tracking_number} assigned)"
        else:
            note = f"Auto-transitioned to shipped: tracking {data.tracking_number} assigned"

    history = OrderStatusHistory(
        tenant_id=current_user.tenant_id,
        order_id=order.id,
        employee_id=current_user.id,
        old_status=old_status,
        new_status=data.status,
        note=note,
    )
    db.add(history)

    # ── Return stock restoration ──────────────────────────────
    # When an order transitions TO 'returned', restore stock for each item
    # that maps to a known product (via SKU). Uses return_in movement.
    if data.status == OrderStatus.returned and old_status != OrderStatus.returned:
        _restore_inventory_for_return(db, order, current_user)

    db.commit()
    db.refresh(order)

    _sync_order_profit_posting(db, order)

    # ── Log status change ─────────────────────────────────────
    log_activity(
        db          = db,
        tenant_id   = str(current_user.tenant_id),
        actor       = current_user,
        module      = LogModule.ORDERS,
        action      = "order.status_change",
        level       = LogLevel.INFO,
        message     = f"Order {order.order_number}: {old_status.value} → {data.status.value}",
        detail      = {
            "order_id":    str(order.id),
            "order_number": order.order_number,
            "old_status":  old_status.value,
            "new_status":  data.status.value,
            "note":        data.note,
        },
    )

    # ── Automated customer messaging: tracking/delivery state ────
    try:
        from app.modules.message_automation.service import handle_order_changed

        handle_order_changed(
            db,
            order,
            previous_tracking_number=previous_tracking_number,
            previous_status=old_status,
        )
        db.commit()
        db.refresh(order)
    except Exception as exc:
        db.rollback()
        log.warning("Order %s message automation queue skipped: %s", order.order_number, exc)

    return order


# ─────────────────────────────────────────────────────────────
# Payment Recording
# ─────────────────────────────────────────────────────────────

def record_payment(
    db: Session,
    order_id: str,
    data: OrderPaymentCreate,
    current_user: Employee,
) -> OrderPayment:
    order = get_order(db, order_id, current_user)

    if order.status == OrderStatus.cancelled:
        raise HTTPException(status_code=400, detail="Cannot record payment on a cancelled order")

    if order.payment_status == PaymentStatus.paid:
        raise HTTPException(status_code=400, detail="Order is already fully paid")

    if data.amount > order.amount_due:
        raise HTTPException(
            status_code=400,
            detail=f"Payment amount ({data.amount}) exceeds amount due ({order.amount_due})",
        )

    payment = OrderPayment(
        tenant_id=current_user.tenant_id,
        order_id=order.id,
        employee_id=current_user.id,
        amount=data.amount,
        method=data.method,
        reference=data.reference,
        note=data.note,
    )
    db.add(payment)

    # Update order amounts
    order.amount_paid = (order.amount_paid or Decimal("0")) + data.amount
    order.amount_due = max(Decimal("0"), order.total_amount - order.amount_paid)
    _update_payment_status(order)
    order.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(payment)
    _sync_order_profit_posting(db, order)
    return payment


# ─────────────────────────────────────────────────────────────
# Stats
# ─────────────────────────────────────────────────────────────

@cache_ttl(ttl_seconds=600, key_prefix="orders:")
def get_order_stats(
    db: Session,
    current_user: Employee,
    filters: Optional[OrderFilters] = None,
    cache_tenant: Optional[str] = None,
) -> OrderStats:
    """
    Get order stats using optional list-style filters.
    Uses 4 targeted SA-2.0-compatible DB queries.
    Results cached for 10 minutes to reduce database load.
    """
    base = db.query(Order)
    base = apply_tenant_filter(base, Order, current_user)
    base = _apply_order_filters(base, filters)

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # ── Query 1: per-status counts ────────────────────────────────────
    status_rows = (
        base
        .with_entities(Order.status, func.count().label("cnt"))
        .group_by(Order.status)
        .all()
    )
    by_status = {s.value: 0 for s in OrderStatus}
    total_orders = 0
    for row in status_rows:
        by_status[row.status.value] = row.cnt
        total_orders += row.cnt

    # ── Query 2: per-payment-status counts ───────────────────────────
    pay_rows = (
        base
        .with_entities(Order.payment_status, func.count().label("cnt"))
        .group_by(Order.payment_status)
        .all()
    )
    by_payment = {s.value: 0 for s in PaymentStatus}
    for row in pay_rows:
        by_payment[row.payment_status.value] = row.cnt

    # ── Query 3: revenue & outstanding aggregates (SA 2.0 CASE WHEN) ─
    from sqlalchemy import case as sa_case
    agg = (
        base
        .with_entities(
            func.sum(
                sa_case(
                    (Order.status == OrderStatus.delivered,
                     func.coalesce(Order.total_amount, 0)),
                    else_=0,
                )
            ).label("total_revenue"),
            func.sum(
                sa_case(
                    (Order.status.notin_([OrderStatus.cancelled, OrderStatus.returned]),
                     func.coalesce(Order.amount_due, 0)),
                    else_=0,
                )
            ).label("total_outstanding"),
            func.count(
                sa_case(
                    (Order.created_at >= month_start, 1),
                    else_=None,
                )
            ).label("orders_this_month"),
            func.sum(
                sa_case(
                    (and_(
                        Order.status == OrderStatus.delivered,
                        Order.delivered_at >= month_start,
                    ), func.coalesce(Order.total_amount, 0)),
                    else_=0,
                )
            ).label("rev_this_month"),
        )
        .one()
    )
    total_revenue      = Decimal(str(agg.total_revenue or 0))
    total_outstanding  = Decimal(str(agg.total_outstanding or 0))
    orders_this_month  = agg.orders_this_month or 0
    revenue_this_month = Decimal(str(agg.rev_this_month or 0))

    # ── Query 4: COD pending count ────────────────────────────────────
    cod_pending_count = (
        base.filter(
            Order.payment_method.in_([PaymentMethod.cod, PaymentMethod.partial_cod]),
            Order.status.notin_([OrderStatus.delivered, OrderStatus.cancelled, OrderStatus.returned]),
        )
        .count()
    )

    return OrderStats(
        total_orders=total_orders,
        by_status=by_status,
        by_payment_status=by_payment,
        total_revenue=total_revenue,
        total_outstanding=total_outstanding,
        orders_this_month=orders_this_month,
        revenue_this_month=revenue_this_month,
        cod_pending_count=cod_pending_count,
    )
