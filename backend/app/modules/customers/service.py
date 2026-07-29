"""
Customers Service Layer
------------------------
All business logic for the Customers module lives here.
Routes are thin — all logic is here.
Every query is tenant-scoped.
"""

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func, or_
from fastapi import HTTPException, status
from fastapi.responses import HTMLResponse
from datetime import datetime, date, timezone
from uuid import UUID
from decimal import Decimal
import re

from app.models.customer import (
    Customer, CustomerProduct, CustomerInteraction,
    CustomerTag, CustomerTagMap, LeadStatus
)
from app.models.order import Order, OrderItem, PaymentMethod
from app.models.employee import Employee
from app.modules.customers.schemas import (
    CustomerCreate, CustomerUpdate,
    CustomerProductCreate, InteractionCreate
)
from app.core.tenant_utils import apply_tenant_filter, assert_tenant_ownership, get_tenant_label_fields
from app.core.whatsapp import compose_whatsapp_message as _compose_wa
from app.models.customer import InteractionType
from app.core.sequence import next_customer_code
# ShopifyOrder import deferred inside functions to avoid circular import at module load time
# but the import itself is safe at top level after all models are registered


# ─────────────────────────────────────────────────────────────
# Customer Code Generator
# ─────────────────────────────────────────────────────────────

def generate_customer_code(db: Session, tenant_id: UUID) -> str:
    """
    Generates a unique sequential customer code per tenant.
    Format: CUST-00001, CUST-00002 ...
    Uses advisory lock to prevent race conditions under concurrency.
    """
    return next_customer_code(db, tenant_id)


# ─────────────────────────────────────────────────────────────
# Create Customer
# ─────────────────────────────────────────────────────────────

def create_customer(
    db: Session,
    data: CustomerCreate,
    current_user: Employee,
) -> Customer:
    code = generate_customer_code(db, current_user.tenant_id)

    customer = Customer(
        tenant_id              = current_user.tenant_id,
        unique_customer_code   = code,
        name                   = data.name,
        phone                  = data.phone,
        alternate_phone        = data.alternate_phone,
        email                  = data.email,
        address                = data.address,
        pincode                = data.pincode,
        city                   = data.city,
        state                  = data.state,
        country                = data.country or "India",
        customer_type          = data.customer_type,
        payment_mode_preference= data.payment_mode_preference,
        source                 = data.source,
        lead_status            = data.lead_status or LeadStatus.new,
        interest_status        = data.interest_status,
        assigned_employee_id   = data.assigned_employee_id,
        created_by_employee_id = current_user.id,
        next_followup_date     = data.next_followup_date,
        notes                  = data.notes,
        is_active              = True,
    )

    db.add(customer)
    db.flush()  # Get customer.id before commit

    # Auto-log first interaction
    interaction = CustomerInteraction(
        tenant_id        = current_user.tenant_id,
        customer_id      = customer.id,
        employee_id      = current_user.id,
        interaction_type = "note",
        message_content  = "Customer created",
        old_status       = None,
        new_status       = customer.lead_status,
    )
    db.add(interaction)
    db.commit()
    db.refresh(customer)

    return customer


# ─────────────────────────────────────────────────────────────
# List Customers (with filters + pagination)
# ─────────────────────────────────────────────────────────────

def list_customers(
    db: Session,
    current_user: Employee,
    lead_status=None,
    interest_status=None,
    source=None,
    city: str = None,
    assigned_employee_id: UUID = None,
    date_from: date = None,
    date_to: date = None,
    page: int = 1,
    limit: int = 50,
):
    query = db.query(Customer)  # include inactive — frontend fades and shows reactivate button

    # ── Tenant Isolation ─────────────────────────────────────
    query = apply_tenant_filter(query, Customer, current_user)

    # ── Filters ──────────────────────────────────────────────
    if lead_status:
        query = query.filter(Customer.lead_status == lead_status)
    if interest_status:
        query = query.filter(Customer.interest_status == interest_status)
    if source:
        query = query.filter(Customer.source == source)
    if city:
        query = query.filter(Customer.city.ilike(f"%{city}%"))
    if assigned_employee_id:
        query = query.filter(Customer.assigned_employee_id == assigned_employee_id)
    if date_from:
        query = query.filter(Customer.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(Customer.created_at <= datetime.combine(date_to, datetime.max.time()))

    # ── Pagination ───────────────────────────────────────────
    total = query.count()
    customers = query.order_by(Customer.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    return {"total": total, "page": page, "limit": limit, "data": customers}


# ─────────────────────────────────────────────────────────────
# Get Customer Detail
# ─────────────────────────────────────────────────────────────

def get_customer(
    db: Session,
    customer_id: UUID,
    current_user: Employee,
) -> Customer:
    customer = (
        db.query(Customer)
        .options(
            joinedload(Customer.products),
            joinedload(Customer.interactions),
            joinedload(Customer.tags),
        )
        .filter(Customer.id == customer_id, Customer.tenant_id == current_user.tenant_id, Customer.is_active == True)
        .first()
    )

    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    
    # If customer address fields are empty, try to populate from latest Shopify order
    # and persist the update so we don't re-query every time
    if not customer.address or not customer.pincode:
        from app.models.shopify_order import ShopifyOrder
        latest_shopify = (
            db.query(ShopifyOrder)
            .filter(ShopifyOrder.customer_id == customer_id, ShopifyOrder.tenant_id == current_user.tenant_id)
            .order_by(ShopifyOrder.created_at_shopify.desc())
            .first()
        )
        if latest_shopify:
            updated = False
            if not customer.address and latest_shopify.shipping_address_line1:
                customer.address = latest_shopify.shipping_address_line1
                updated = True
            if not customer.pincode and latest_shopify.shipping_zip:
                customer.pincode = latest_shopify.shipping_zip
                updated = True
            if not customer.city and latest_shopify.shipping_city:
                customer.city = latest_shopify.shipping_city
                updated = True
            if not customer.state and latest_shopify.shipping_province:
                customer.state = latest_shopify.shipping_province
                updated = True
            if updated:
                customer.updated_at = datetime.now(timezone.utc)
                db.commit()
                db.refresh(customer)

    return customer


# ─────────────────────────────────────────────────────────────
# Update Customer
# ─────────────────────────────────────────────────────────────

def update_customer(
    db: Session,
    customer_id: UUID,
    data: CustomerUpdate,
    current_user: Employee,
) -> Customer:
    customer = get_customer(db, customer_id, current_user)

    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(customer, field, value)

    customer.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(customer)

    return customer


# ─────────────────────────────────────────────────────────────
# Soft Delete Customer
# ─────────────────────────────────────────────────────────────

def delete_customer(
    db: Session,
    customer_id: UUID,
    current_user: Employee,
):
    from app.models.order import Order
    from app.models.invoice import Invoice
    from app.models.shopify_order import ShopifyOrder
    from app.models.lead import Lead
    from fastapi import HTTPException

    # Fetch customer regardless of is_active status so inactive customers can also be deleted
    customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id, Customer.tenant_id == current_user.tenant_id)
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Block if the customer has real orders or invoices (non-nullable FK)
    order_count = db.query(Order).filter(Order.customer_id == customer.id).count()
    if order_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete: customer has {order_count} order(s). Delete the orders first."
        )
    invoice_count = db.query(Invoice).filter(Invoice.customer_id == customer.id).count()
    if invoice_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete: customer has {invoice_count} invoice(s). Delete the invoices first."
        )

    # Nullify nullable FK references before deleting
    db.query(ShopifyOrder).filter(ShopifyOrder.customer_id == customer.id).update(
        {"customer_id": None}, synchronize_session=False
    )
    db.query(Lead).filter(Lead.converted_customer_id == customer.id).update(
        {"converted_customer_id": None}, synchronize_session=False
    )
    db.query(Lead).filter(Lead.customer_id == customer.id).update(
        {"customer_id": None}, synchronize_session=False
    )

    code = customer.unique_customer_code
    db.delete(customer)
    db.commit()

    return {"message": f"Customer {code} permanently deleted"}


# ─────────────────────────────────────────────────────────────
# Add Interaction
# ─────────────────────────────────────────────────────────────

def add_interaction(
    db: Session,
    customer_id: UUID,
    data: InteractionCreate,
    current_user: Employee,
) -> CustomerInteraction:
    customer = get_customer(db, customer_id, current_user)

    old_status = customer.lead_status

    # If status is changing — update customer
    if data.new_status and data.new_status != old_status:
        customer.lead_status    = data.new_status
        customer.last_contacted_at = datetime.now(timezone.utc)
        customer.updated_at     = datetime.now(timezone.utc)

    interaction = CustomerInteraction(
        tenant_id        = current_user.tenant_id,
        customer_id      = customer.id,
        employee_id      = current_user.id,
        interaction_type = data.interaction_type,
        message_content  = data.message_content,
        old_status       = old_status,
        new_status       = data.new_status or old_status,
    )

    db.add(interaction)
    db.commit()
    db.refresh(interaction)

    return interaction


# ─────────────────────────────────────────────────────────────
# Add Product Interest
# ─────────────────────────────────────────────────────────────

def add_product_interest(
    db: Session,
    customer_id: UUID,
    data: CustomerProductCreate,
    current_user: Employee,
) -> CustomerProduct:
    customer = get_customer(db, customer_id, current_user)

    product = CustomerProduct(
        tenant_id           = current_user.tenant_id,
        customer_id         = customer.id,
        product_name        = data.product_name,
        quantity_interested = data.quantity_interested,
        note                = data.note,
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return product


# ─────────────────────────────────────────────────────────────
# Reporting Queries
# ─────────────────────────────────────────────────────────────

def get_customer_stats(db: Session, current_user: Employee) -> dict:
    """Quick stats for dashboard — uses single GROUP BY query instead of N separate counts."""
    today = date.today()

    base_filter = (
        Customer.tenant_id == current_user.tenant_id,
        Customer.is_active == True,
    )

    total = db.query(func.count(Customer.id)).filter(*base_filter).scalar() or 0

    # Single GROUP BY for lead_status breakdown
    status_rows = (
        db.query(Customer.lead_status, func.count(Customer.id))
        .filter(*base_filter)
        .group_by(Customer.lead_status)
        .all()
    )
    by_lead_status = {s.value: 0 for s in LeadStatus}
    for row_status, cnt in status_rows:
        key = row_status.value if hasattr(row_status, 'value') else str(row_status)
        by_lead_status[key] = cnt

    converted = by_lead_status.get("converted", 0)

    hot_leads = db.query(func.count(Customer.id)).filter(
        *base_filter,
        Customer.interest_status == "hot",
    ).scalar() or 0

    followups_today = db.query(func.count(Customer.id)).filter(
        *base_filter,
        Customer.next_followup_date == today,
    ).scalar() or 0

    return {
        "total":           total,
        "hot_leads":       hot_leads,
        "converted":       converted,
        "followups_today": followups_today,
        "by_lead_status":  by_lead_status,
    }


# ─────────────────────────────────────────────────────────────
# Toggle Customer Status
# ─────────────────────────────────────────────────────────────

def toggle_customer_status(db: Session, customer_id: UUID, current_user: Employee) -> dict:
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.tenant_id == current_user.tenant_id,
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    customer.is_active = not customer.is_active
    customer.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": str(customer.id), "is_active": customer.is_active}


# ─────────────────────────────────────────────────────────────
# Customer List WITH latest order summary
# ─────────────────────────────────────────────────────────────

def list_customers_with_orders(
    db: Session,
    current_user: Employee,
    search: str = None,
    state: str = None,
    is_active: bool = None,
    page: int = 1,
    limit: int = 50,
) -> dict:
    query = db.query(Customer).filter(Customer.tenant_id == current_user.tenant_id)

    if is_active is not None:
        query = query.filter(Customer.is_active == is_active)
    # if is_active is None → return all (active + inactive); frontend fades inactive rows

    if state:
        query = query.filter(Customer.state.ilike(f"%{state}%"))

    if search:
        q = f"%{search}%"
        clauses = [
            Customer.name.ilike(q),
            Customer.phone.ilike(q),
            Customer.alternate_phone.ilike(q),
            Customer.unique_customer_code.ilike(q),
        ]

        digits = re.sub(r"\D", "", search)
        if digits:
            variants = {digits}
            if len(digits) == 10:
                variants.add(f"91{digits}")
            if len(digits) == 12 and digits.startswith("91"):
                variants.add(digits[2:])

            customer_phone_digits = func.regexp_replace(func.coalesce(Customer.phone, ""), r"\D", "", "g")
            alt_phone_digits = func.regexp_replace(func.coalesce(Customer.alternate_phone, ""), r"\D", "", "g")
            for v in variants:
                digit_q = f"%{v}%"
                clauses.append(customer_phone_digits.ilike(digit_q))
                clauses.append(alt_phone_digits.ilike(digit_q))

        query = query.filter(or_(*clauses))

    total = query.count()
    customers = query.order_by(Customer.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    if not customers:
        return {"total": total, "page": page, "limit": limit, "data": []}

    from app.models.shopify_order import ShopifyOrder

    customer_ids = [c.id for c in customers]

    # ── Batch-fetch latest manual order per customer (1 query) ───────────────
    # Subquery: rank orders per customer by created_at desc
    from sqlalchemy import over
    from sqlalchemy.dialects.postgresql import aggregate_order_by

    # Use a CTE to get the latest order_id per customer
    latest_manual_subq = (
        db.query(
            Order.customer_id,
            func.max(Order.created_at).label("max_created"),
        )
        .filter(
            Order.tenant_id == current_user.tenant_id,
            Order.customer_id.in_(customer_ids),
        )
        .group_by(Order.customer_id)
        .subquery()
    )
    manual_orders_q = (
        db.query(Order)
        .options(joinedload(Order.items))
        .join(
            latest_manual_subq,
            (Order.customer_id == latest_manual_subq.c.customer_id) &
            (Order.created_at == latest_manual_subq.c.max_created),
        )
        .all()
    )
    manual_by_cid = {str(o.customer_id): o for o in manual_orders_q}

    # ── Batch-fetch latest Shopify order per customer (1 query) ───────────────
    latest_shopify_subq = (
        db.query(
            ShopifyOrder.customer_id,
            func.max(ShopifyOrder.created_at_shopify).label("max_created"),
        )
        .filter(
            ShopifyOrder.tenant_id == current_user.tenant_id,
            ShopifyOrder.customer_id.in_(customer_ids),
        )
        .group_by(ShopifyOrder.customer_id)
        .subquery()
    )
    shopify_orders_q = (
        db.query(ShopifyOrder)
        .join(
            latest_shopify_subq,
            (ShopifyOrder.customer_id == latest_shopify_subq.c.customer_id) &
            (ShopifyOrder.created_at_shopify == latest_shopify_subq.c.max_created),
        )
        .all()
    )
    shopify_by_cid = {str(so.customer_id): so for so in shopify_orders_q}

    # ── Batch-count manual orders per customer (1 query) ─────────────────────
    manual_counts = dict(
        db.query(Order.customer_id, func.count(Order.id))
        .filter(Order.tenant_id == current_user.tenant_id, Order.customer_id.in_(customer_ids))
        .group_by(Order.customer_id)
        .all()
    )

    # ── Batch-count Shopify orders per customer (1 query) ─────────────────────
    shopify_counts = dict(
        db.query(ShopifyOrder.customer_id, func.count(ShopifyOrder.id))
        .filter(ShopifyOrder.tenant_id == current_user.tenant_id, ShopifyOrder.customer_id.in_(customer_ids))
        .group_by(ShopifyOrder.customer_id)
        .all()
    )

    rows = []
    for c in customers:
        cid = str(c.id)
        m_order = manual_by_cid.get(cid)
        s_order = shopify_by_cid.get(cid)

        # Use whichever is more recent
        if s_order and (not m_order or s_order.created_at_shopify > m_order.created_at):
            latest_order = s_order
            is_shopify = True
        else:
            latest_order = m_order
            is_shopify = False

        total_order_count = (manual_counts.get(c.id, 0) + shopify_counts.get(c.id, 0))

        # Items text from latest order
        items_text = ""
        if latest_order:
            if is_shopify:
                items_json = latest_order.line_items_json or []
                if items_json:
                    items_text = ", ".join(f"{item.get('title', 'Item')} x{item.get('quantity', 1)}" for item in items_json[:3])
            else:
                if hasattr(latest_order, 'items') and latest_order.items:
                    items_text = ", ".join(
                        f"{item.product_name} x{item.quantity}" for item in latest_order.items[:3]
                    )

        # Resolve payment_status safely for both order types
        if is_shopify and latest_order:
            fs = latest_order.shopify_fulfillment_status
            payment_status_val = fs if isinstance(fs, str) else (fs.value if fs else "")
        elif latest_order and hasattr(latest_order, 'payment_status') and latest_order.payment_status:
            payment_status_val = latest_order.payment_status.value
        else:
            payment_status_val = ""

        rows.append({
            "id":                  cid,
            "unique_customer_code": c.unique_customer_code,
            "name":                c.name,
            "phone":               c.phone,
            "alternate_phone":     c.alternate_phone or "",
            "email":               c.email or "",
            "address":             c.address or "",
            "pincode":             c.pincode or "",
            "city":                c.city or "",
            "state":               c.state or "",
            "is_active":           c.is_active,
            "notes":               c.notes or "",
            "created_at":          c.created_at.isoformat() if c.created_at else None,
            "customer_type":       c.customer_type.value if c.customer_type else "",
            "source":              c.source.value if c.source else "manual",
            # Engagement tracking
            "first_order_date":    c.first_order_date.isoformat() if c.first_order_date else None,
            "last_order_date":     c.last_order_date.isoformat() if c.last_order_date else None,
            "last_seen_at":        c.last_seen_at.isoformat() if c.last_seen_at else None,
            "total_orders_count":  total_order_count,
            "average_order_value": str(c.average_order_value) if c.average_order_value else "0",
            "abandoned_carts":     c.abandoned_carts or 0,
            # Latest order fields
            "order_id":            (latest_order.order_number if m_order and not is_shopify else
                                   (latest_order.shopify_order_name if is_shopify and latest_order else "")),
            "order_uuid":          str(latest_order.id) if latest_order else "",
            "tracking_number":     (latest_order.tracking_number or "") if latest_order else "",
            "order_status":        (
                latest_order.status.value if not is_shopify and latest_order and hasattr(latest_order, 'status') and latest_order.status else
                ((latest_order.shopify_fulfillment_status if isinstance(latest_order.shopify_fulfillment_status, str) else
                  (latest_order.shopify_fulfillment_status.value if latest_order.shopify_fulfillment_status else ""))
                 if is_shopify and latest_order and hasattr(latest_order, 'shopify_fulfillment_status') else "")
            ),
            "payment_method":      (
                latest_order.payment_method.value if not is_shopify and latest_order and latest_order.payment_method else
                (latest_order.shopify_financial_status if is_shopify and latest_order else "")
            ),
            "total_amount":        (
                str(latest_order.total_amount) if not is_shopify and latest_order else
                (str(latest_order.total_price) if is_shopify and latest_order else "0")
            ),
            # For Partial COD: advance + cod balance = total
            "advance_amount":      (
                str(latest_order.advance_amount) if not is_shopify and latest_order and latest_order.advance_amount else
                "0"
            ),
            "cod_amount":          (
                str(latest_order.cod_amount) if not is_shopify and latest_order and latest_order.cod_amount else
                "0"
            ),
            "payment_status":      payment_status_val,
            "printed_count":       (latest_order.printed_count if not is_shopify and latest_order else 0),
            "items_text":          items_text,
            "order_count":         total_order_count,
            "is_shopify":          is_shopify,
        })

    return {"total": total, "page": page, "limit": limit, "data": rows}


# ─────────────────────────────────────────────────────────────
# Customer Order History
# ─────────────────────────────────────────────────────────────

def get_customer_orders(db: Session, customer_id: UUID, current_user: Employee) -> list:
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.tenant_id == current_user.tenant_id,
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    from app.models.shopify_order import ShopifyOrder
    
    # Get manual orders
    manual_orders = (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.customer_id == customer_id, Order.tenant_id == current_user.tenant_id)
        .order_by(Order.created_at.desc())
        .all()
    )
    
    # Get Shopify orders
    shopify_orders = (
        db.query(ShopifyOrder)
        .filter(ShopifyOrder.customer_id == customer_id, ShopifyOrder.tenant_id == current_user.tenant_id)
        .order_by(ShopifyOrder.created_at_shopify.desc())
        .all()
    )

    result = []
    
    # Process manual orders
    for o in manual_orders:
        result.append({
            "id":              str(o.id),
            "order_number":    o.order_number,
            "order_type":      "manual",
            "status":          o.status.value,
            "payment_status":  o.payment_status.value,
            "payment_method":  o.payment_method.value if o.payment_method else "",
            "total_amount":    str(o.total_amount),
            "amount_paid":     str(o.amount_paid),
            "amount_due":      str(o.amount_due),
            "tracking_number": o.tracking_number or "",
            "tracking_url":    "",
            "courier_name":    o.courier_name or "",
            "shipping_partner": "",
            "printed_count":   o.printed_count,
            "notes":           o.notes or "",
            "delivery_address": o.delivery_address or "",
            "delivery_city":   o.delivery_city or "",
            "delivery_state":  o.delivery_state or "",
            "delivery_pincode": o.delivery_pincode or "",
            "expected_delivery": o.expected_delivery.isoformat() if o.expected_delivery else None,
            "created_at":      o.created_at.isoformat() if o.created_at else None,
            "items": [
                {
                    "product_name": item.product_name,
                    "quantity":     str(item.quantity),
                    "unit":         item.unit.value,
                    "unit_price":   str(item.unit_price),
                    "line_total":   str(item.line_total),
                }
                for item in o.items
            ],
        })
    
    # Process Shopify orders
    for so in shopify_orders:
        items_data = []
        if so.line_items_json:
            for item in so.line_items_json:
                items_data.append({
                    "product_name": item.get('title', 'Item'),
                    "quantity":     str(item.get('quantity', 1)),
                    "unit":         "pcs",
                    "unit_price":   str(item.get('price', '0')),
                    "line_total":   str(float(item.get('price', 0)) * item.get('quantity', 1)),
                })
        
        result.append({
            "id":              str(so.id),
            "order_number":    so.shopify_order_name,
            "order_type":      "shopify",
            "status":          so.shopify_fulfillment_status if isinstance(so.shopify_fulfillment_status, str) else so.shopify_fulfillment_status.value,
            "payment_status":  so.shopify_financial_status or "unknown",
            "payment_method":  so.payment_gateway or "shopify",
            "total_amount":    str(so.total_price),
            "amount_paid":     str(so.total_price) if so.shopify_financial_status == "paid" else "0",
            "amount_due":      "0" if so.shopify_financial_status == "paid" else str(so.total_price),
            "tracking_number": so.tracking_number or "",
            "tracking_url":    so.tracking_url or "",
            "courier_name":    so.shipping_partner or "",
            "shipping_partner": so.shipping_partner or "",
            "printed_count":   0,
            "notes":           "",
            "delivery_address": so.shipping_address_line1 or "",
            "delivery_city":   so.shipping_city or "",
            "delivery_state":  so.shipping_province or "",
            "delivery_pincode": so.shipping_zip or "",
            "expected_delivery": None,
            "created_at":      so.created_at_shopify.isoformat() if so.created_at_shopify else None,
            "items": items_data,
        })
    
    # Sort all orders by created_at descending
    result.sort(key=lambda x: x["created_at"] or "0", reverse=True)
    
    return result


# ─────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────
# Helper: Build tenant invoice header (for invoice HTML)
# ─────────────────────────────────────────────────────────────

def _build_tenant_invoice_header(tenant) -> str:
    """Build a multi-line address block for invoices."""
    lines = []
    if getattr(tenant, "address_line1", None):
        lines.append(tenant.address_line1)
    if getattr(tenant, "address_line2", None):
        lines.append(tenant.address_line2)
    city_state_pin = ", ".join(
        p for p in [
            getattr(tenant, "gst_city", None) or "",
            getattr(tenant, "gst_state", None) or "",
            getattr(tenant, "gst_pincode", None) or "",
        ] if p
    )
    if city_state_pin:
        lines.append(city_state_pin)
    if getattr(tenant, "phone", None):
        lines.append(f"Ph: {tenant.phone}")
    if getattr(tenant, "email", None):
        lines.append(f"Email: {tenant.email}")
    if getattr(tenant, "gstin", None):
        lines.append(f"GSTIN: {tenant.gstin}")
    return "<br>".join(lines)


# ─────────────────────────────────────────────────────────────
# Generate Shipping Label PDF
# ─────────────────────────────────────────────────────────────

def _label_items_text(items: list[OrderItem]) -> str:
    """Render order items as 'Product Name x Qty' for thermal labels."""
    lines = []
    for item in items:
        product_name = (item.product_name or "").strip()
        # Strip variant suffix after em-dash to reduce noisy duplicate text.
        if "\u2014" in product_name:
            product_name = product_name.split("\u2014")[0].strip()
        sku = (item.sku or "").strip()
        display_name = product_name if product_name else sku
        if not display_name:
            continue
        qty = item.quantity or 0
        try:
            qty_int = int(qty)
            qty_display = qty_int if qty == qty_int else float(qty)
        except Exception:
            qty_display = qty
        lines.append(f"{display_name} x{qty_display}")
    return "\n".join(lines)

def generate_customer_label(
    db: Session,
    customer_id: UUID,
    order_id: UUID,
    current_user: Employee,
) -> bytes:
    from app.core.label_pdf import build_labels_pdf
    from app.models.tenant import Tenant
    from app.models.shipping_config import DeliveryPartner

    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.tenant_id == current_user.tenant_id,
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    order = db.query(Order).options(joinedload(Order.items)).filter(
        Order.id == order_id,
        Order.customer_id == customer_id,
        Order.tenant_id == current_user.tenant_id,
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()

    # Load delivery partner to check if India Post (optional, for validation)
    delivery_partner = None
    if order.shipping_partner_id:
        delivery_partner = db.query(DeliveryPartner).filter(
            DeliveryPartner.id == order.shipping_partner_id
        ).first()

    india_post_customer_id = ""
    is_india_post = (
        (delivery_partner and delivery_partner.partner_type == "india_post")
        or (order.courier_code and order.courier_code.lower() == "india_post")
    )
    if is_india_post and order.india_post_customer_id:
        india_post_customer_id = order.india_post_customer_id

    # Resolve correct contract ID from delivery partner config by shipping_service
    if is_india_post and delivery_partner and delivery_partner.customer_ids:
        cids = delivery_partner.customer_ids
        svc = (order.shipping_service or "").lower().replace("_", " ").strip()
        matched = None
        for cid_entry in cids:
            cid_name = (cid_entry.get("name") or "").lower().strip()
            if svc and cid_name and (svc in cid_name or cid_name in svc):
                matched = cid_entry.get("id", "")
                break
        if matched:
            india_post_customer_id = matched

    items_text = _label_items_text(order.items)

    # Determine payment type display
    if order.payment_method == PaymentMethod.partial_cod:
        payment_type = "Partial COD"
    elif order.payment_method == PaymentMethod.cod:
        payment_type = "COD"
    elif order.payment_method in (PaymentMethod.upi, PaymentMethod.bank_transfer, PaymentMethod.cheque, PaymentMethod.credit, PaymentMethod.cash):
        payment_type = "Prepaid"
    else:
        payment_type = order.payment_method.value.replace("_", " ").title() if order.payment_method else "COD"

    # For Partial COD: amount to collect = total - advance. For COD: full total. For Prepaid: reference amount.
    if order.payment_method == PaymentMethod.partial_cod:
        advance = order.advance_amount or Decimal("0")
        total = order.total_amount or Decimal("0")
        collect_amount = str(max(Decimal("0"), total - advance))
    elif order.payment_method == PaymentMethod.cod:
        collect_amount = str(order.total_amount) if order.total_amount else ""
    else:
        # Prepaid — show full amount as reference
        collect_amount = str(order.total_amount) if order.total_amount else ""

    # Build amounts
    subtotal = str(order.subtotal) if order.subtotal else ""
    discount_amount = str(order.discount_amount) if order.discount_amount and order.discount_amount > 0 else ""
    shipping_charge = str(order.shipping_charge) if order.shipping_charge and order.shipping_charge > 0 else ""
    final_amount = str(order.total_amount) if order.total_amount else ""

    tf = get_tenant_label_fields(tenant)

    label_data = {
        "name":            order.delivery_name or customer.name,
        "address":         order.delivery_address or customer.address or "",
        "pincode":         order.delivery_pincode or customer.pincode or "",
        "city":            order.delivery_city or customer.city or "",
        "state":           order.delivery_state or customer.state or "",
        "phone":           customer.phone,
        "payment_type":    payment_type,
        "amount":          collect_amount,  # COD amount for COD/Partial COD, total for Prepaid
        "order_number":    order.order_number,
        "tracking_number": order.tracking_number or "",
        "items_text":      items_text,
        "from_name":       tf["from_name"],
        "from_address":    tf["from_address"],
        "from_pincode":    tf["from_pincode"],
        "from_phone":      tf["from_phone"],
        "slogan":          tf["slogan"],
        "logo_url":        tf["logo_url"],
        "india_post_customer_id": india_post_customer_id,
        "subtotal":        subtotal,
        "discount_amount": discount_amount,
        "shipping_charge": shipping_charge,
        "final_amount":    final_amount,
    }

    # Increment printed_count
    order.printed_count = (order.printed_count or 0) + 1
    db.commit()

    return build_labels_pdf([label_data])


# ─────────────────────────────────────────────────────────────
# Generate Invoice HTML (printable)
# ─────────────────────────────────────────────────────────────

def generate_customer_invoice(
    db: Session,
    customer_id: UUID,
    order_id: UUID,
    current_user: Employee,
):
    from app.models.tenant import Tenant

    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.tenant_id == current_user.tenant_id,
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    order = db.query(Order).options(joinedload(Order.items)).filter(
        Order.id == order_id,
        Order.customer_id == customer_id,
        Order.tenant_id == current_user.tenant_id,
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()

    items_rows = "".join(
        f"""<tr>
          <td>{i+1}</td>
          <td>{item.product_name}</td>
          <td>{item.quantity} {item.unit.value}</td>
          <td>₹{item.unit_price}</td>
          <td>₹{item.line_total}</td>
        </tr>"""
        for i, item in enumerate(order.items)
    )

    payment_method = order.payment_method.value.upper() if order.payment_method else "—"
    delivery_addr = order.delivery_address or customer.address or "—"

    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Invoice {order.order_number}</title>
<style>
  body {{ font-family: Arial, sans-serif; font-size: 13px; margin: 30px; color: #111; }}
  h1 {{ font-size: 22px; color: #0f172a; margin: 0; }}
  .header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; border-bottom: 2px solid #0f172a; padding-bottom: 14px; }}
  .from {{ font-size: 12px; color: #444; }}
  .inv-meta {{ text-align: right; }}
  .inv-meta strong {{ font-size: 16px; color: #0f172a; }}
  .section {{ margin-bottom: 18px; }}
  .section h3 {{ font-size: 12px; font-weight: 700; text-transform: uppercase; color: #64748b; margin-bottom: 6px; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ background: #f8fafc; padding: 8px 10px; text-align: left; font-size: 11px; font-weight: 700; text-transform: uppercase; color: #64748b; }}
  td {{ padding: 8px 10px; border-bottom: 1px solid #f1f5f9; }}
  .total-row {{ font-weight: 700; background: #f8fafc; }}
  .total-row td {{ border-top: 2px solid #0f172a; font-size: 14px; }}
  .pill {{ display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 700; }}
  .pill-cod {{ background: #fef3c7; color: #92400e; }}
  .pill-paid {{ background: #dcfce7; color: #15803d; }}
  .pill-pending {{ background: #fee2e2; color: #b91c1c; }}
  .footer {{ margin-top: 30px; font-size: 11px; color: #94a3b8; text-align: center; border-top: 1px solid #e2e8f0; padding-top: 10px; }}
  @media print {{ body {{ margin: 10px; }} .no-print {{ display: none; }} }}
</style>
</head>
<body>
<div class="no-print" style="margin-bottom:16px">
  <button onclick="window.print()" style="padding:8px 18px;background:#0f172a;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-weight:600">🖨 Print Invoice</button>
  <button onclick="window.close()" style="margin-left:8px;padding:8px 18px;background:#f1f5f9;color:#0f172a;border:1px solid #e2e8f0;border-radius:6px;cursor:pointer;font-size:13px">Close</button>
</div>

<div class="header">
  <div>
    <h1>{tenant.company_name if tenant else 'Invoice'}</h1>
    <div class="from">Tax Invoice / Bill of Supply</div>
    <div class="from" style="margin-top:4px;font-size:11px;color:#666;">{_build_tenant_invoice_header(tenant) if tenant else ''}</div>
  </div>
  <div class="inv-meta">
    <strong>{order.order_number}</strong><br>
    <span style="font-size:12px;color:#64748b">Date: {order.created_at.strftime('%d %b %Y') if order.created_at else '—'}</span><br>
    <span class="pill {'pill-cod' if order.payment_method and order.payment_method.value == 'cod' else 'pill-paid'}">{payment_method}</span>
  </div>
</div>

<div style="display:flex;gap:40px;margin-bottom:20px">
  <div class="section" style="flex:1">
    <h3>Bill To</h3>
    <strong>{customer.name}</strong><br>
    {customer.phone}<br>
    {delivery_addr}<br>
    {order.delivery_pincode or customer.pincode or ''} {order.delivery_state or customer.state or ''}
  </div>
  <div class="section" style="flex:1">
    <h3>Delivery Info</h3>
    Tracking: <strong>{order.tracking_number or '—'}</strong><br>
    Courier: {order.courier_name or '—'}<br>
    Expected: {order.expected_delivery.strftime('%d %b %Y') if order.expected_delivery else '—'}<br>
    Status: <strong>{order.status.value.upper()}</strong>
  </div>
</div>

<div class="section">
  <h3>Items</h3>
  <table>
    <thead><tr><th>#</th><th>Product</th><th>Qty</th><th>Rate</th><th>Amount</th></tr></thead>
    <tbody>
      {items_rows}
    </tbody>
  </table>
</div>

<div style="display:flex;justify-content:flex-end">
  <table style="width:280px">
    <tbody>
      <tr><td>Subtotal</td><td style="text-align:right">₹{order.subtotal}</td></tr>
      {'<tr><td>Discount</td><td style="text-align:right">-₹' + str(order.discount_amount) + '</td></tr>' if order.discount_amount else ''}
      {'<tr><td>Tax</td><td style="text-align:right">₹' + str(order.tax_amount) + '</td></tr>' if order.tax_amount else ''}
      {'<tr><td>Shipping</td><td style="text-align:right">₹' + str(order.shipping_charge) + '</td></tr>' if order.shipping_charge else ''}
      <tr class="total-row"><td><strong>Total</strong></td><td style="text-align:right"><strong>₹{order.total_amount}</strong></td></tr>
      <tr><td>Amount Paid</td><td style="text-align:right">₹{order.amount_paid}</td></tr>
      <tr><td><strong>Amount Due</strong></td><td style="text-align:right;color:#b91c1c"><strong>₹{order.amount_due}</strong></td></tr>
    </tbody>
  </table>
</div>

{f'<div class="section" style="margin-top:20px"><h3>Notes</h3><p style="color:#444">{order.notes}</p></div>' if order.notes else ''}

<div class="footer">
  Thank you for your business! &nbsp;|&nbsp; {tenant.company_name if tenant else ''} &nbsp;|&nbsp; Label printed {order.printed_count} time(s)
</div>
</body>
</html>"""

    return HTMLResponse(content=html)


# ─────────────────────────────────────────────────────────────
# Bulk Print Labels (multi-select)
# ─────────────────────────────────────────────────────────────

def generate_bulk_labels(
    db: Session,
    items: list,          # [{customer_id, order_id}, ...]
    current_user: Employee,
) -> bytes:
    from app.core.label_pdf import build_labels_pdf
    from app.models.tenant import Tenant
    from app.models.shipping_config import DeliveryPartner

    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    label_data_list = []

    for item in items:
        try:
            cid = UUID(str(item.get("customer_id", "")))
            oid = UUID(str(item.get("order_id", "")))
        except Exception:
            continue

        customer = db.query(Customer).filter(
            Customer.id == cid,
            Customer.tenant_id == current_user.tenant_id,
        ).first()
        order = db.query(Order).options(joinedload(Order.items)).filter(
            Order.id == oid,
            Order.customer_id == cid,
            Order.tenant_id == current_user.tenant_id,
        ).first()

        if not customer or not order:
            continue

        # Load delivery partner to check if India Post (optional, for validation)
        delivery_partner = None
        if order.shipping_partner_id:
            delivery_partner = db.query(DeliveryPartner).filter(
                DeliveryPartner.id == order.shipping_partner_id
            ).first()

        india_post_customer_id = ""
        is_india_post = (
            (delivery_partner and delivery_partner.partner_type == "india_post")
            or (order.courier_code and order.courier_code.lower() == "india_post")
        )
        if is_india_post and order.india_post_customer_id:
            india_post_customer_id = order.india_post_customer_id
        # Resolve correct contract ID from delivery partner config by shipping_service
        if is_india_post and delivery_partner and delivery_partner.customer_ids:
            cids = delivery_partner.customer_ids
            svc = (order.shipping_service or "").lower().replace("_", " ").strip()
            for cid_entry in cids:
                cid_name = (cid_entry.get("name") or "").lower().strip()
                if svc and cid_name and (svc in cid_name or cid_name in svc):
                    india_post_customer_id = cid_entry.get("id", "")
                    break

        items_text = _label_items_text(order.items)
        
        # Determine payment type display
        if order.payment_method == PaymentMethod.partial_cod:
            payment_type = "Partial COD"
        elif order.payment_method == PaymentMethod.cod:
            payment_type = "COD"
        elif order.payment_method in (PaymentMethod.upi, PaymentMethod.bank_transfer, PaymentMethod.cheque, PaymentMethod.credit, PaymentMethod.cash):
            payment_type = "Prepaid"
        else:
            payment_type = order.payment_method.value.replace("_", " ").title() if order.payment_method else "COD"

        # For Partial COD: amount to collect = total - advance. For COD: full total. For Prepaid: total as reference.
        if order.payment_method == PaymentMethod.partial_cod:
            advance = order.advance_amount or Decimal("0")
            total = order.total_amount or Decimal("0")
            collect_amount = str(max(Decimal("0"), total - advance))
        elif order.payment_method == PaymentMethod.cod:
            collect_amount = str(order.total_amount) if order.total_amount else ""
        else:
            # Prepaid — show full amount as reference
            collect_amount = str(order.total_amount) if order.total_amount else ""

        subtotal = str(order.subtotal) if order.subtotal else ""
        discount_amt = str(order.discount_amount) if order.discount_amount and order.discount_amount > 0 else ""
        shipping_chr = str(order.shipping_charge) if order.shipping_charge and order.shipping_charge > 0 else ""
        final_amt = str(order.total_amount) if order.total_amount else ""

        tf = get_tenant_label_fields(tenant)

        label_data_list.append({
            "name":            order.delivery_name or customer.name,
            "address":         order.delivery_address or customer.address or "",
            "pincode":         order.delivery_pincode or customer.pincode or "",
            "city":            order.delivery_city or customer.city or "",
            "state":           order.delivery_state or customer.state or "",
            "phone":           customer.phone,
            "payment_type":    payment_type,
            "amount":          collect_amount,  # COD amount for COD/Partial COD, total for Prepaid
            "order_number":    order.order_number,
            "tracking_number": order.tracking_number or "",
            "items_text":      items_text,
            "from_name":       tf["from_name"],
            "from_address":    tf["from_address"],
            "from_pincode":    tf["from_pincode"],
            "from_phone":      tf["from_phone"],
            "slogan":          tf["slogan"],
            "logo_url":        tf["logo_url"],
            "india_post_customer_id": india_post_customer_id,
            "subtotal":        subtotal,
            "discount_amount": discount_amt,
            "shipping_charge": shipping_chr,
            "final_amount":    final_amt,
        })
        # Increment printed_count
        order.printed_count = (order.printed_count or 0) + 1

    db.commit()

    if not label_data_list:
        raise HTTPException(status_code=400, detail="No valid label data found")

    return build_labels_pdf(label_data_list)


# ─────────────────────────────────────────────────────────────
# Bulk Print Invoices (multi-select) — returns combined HTML
# ─────────────────────────────────────────────────────────────

def generate_bulk_invoices(
    db: Session,
    items: list,
    current_user: Employee,
):
    from app.models.tenant import Tenant

    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    invoice_blocks = []

    for item in items:
        try:
            cid = UUID(str(item.get("customer_id", "")))
            oid = UUID(str(item.get("order_id", "")))
        except Exception:
            continue

        customer = db.query(Customer).filter(
            Customer.id == cid,
            Customer.tenant_id == current_user.tenant_id,
        ).first()
        order = db.query(Order).options(joinedload(Order.items)).filter(
            Order.id == oid,
            Order.customer_id == cid,
            Order.tenant_id == current_user.tenant_id,
        ).first()
        if not customer or not order:
            continue

        items_rows = "".join(
            f"<tr><td>{i+1}</td><td>{oi.product_name}</td><td>{oi.quantity} {oi.unit.value}</td>"
            f"<td>₹{oi.unit_price}</td><td>₹{oi.line_total}</td></tr>"
            for i, oi in enumerate(order.items)
        )
        pm = order.payment_method.value.upper() if order.payment_method else "—"
        delivery_addr = order.delivery_address or customer.address or "—"

        invoice_blocks.append(f"""
<div class="invoice-page">
  <div class="header">
    <div><h1>{tenant.company_name if tenant else ''}</h1><div class="from">Tax Invoice</div>
    <div class="from" style="margin-top:2px;font-size:10px;color:#666;">{_build_tenant_invoice_header(tenant) if tenant else ''}</div></div>
    <div class="inv-meta"><strong>{order.order_number}</strong><br>
      <span>{order.created_at.strftime('%d %b %Y') if order.created_at else ''}</span><br>
      <span class="pill">{pm}</span></div>
  </div>
  <div style="display:flex;gap:32px;margin-bottom:16px">
    <div style="flex:1"><strong>Bill To</strong><br>{customer.name}<br>{customer.phone}<br>
      {delivery_addr}<br>{order.delivery_pincode or customer.pincode or ''} {order.delivery_state or customer.state or ''}</div>
    <div style="flex:1"><strong>Delivery</strong><br>Tracking: {order.tracking_number or '—'}<br>
      Courier: {order.courier_name or '—'}<br>Status: {order.status.value.upper()}</div>
  </div>
  <table><thead><tr><th>#</th><th>Product</th><th>Qty</th><th>Rate</th><th>Amount</th></tr></thead>
  <tbody>{items_rows}</tbody></table>
  <div style="text-align:right;margin-top:10px">
    <strong>Total: ₹{order.total_amount}</strong> &nbsp;|&nbsp; Paid: ₹{order.amount_paid} &nbsp;|&nbsp;
    <span style="color:#b91c1c">Due: ₹{order.amount_due}</span>
  </div>
</div>""")

    if not invoice_blocks:
        raise HTTPException(status_code=400, detail="No valid invoices found")

    combined = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Bulk Invoices</title>
<style>
  body {{ font-family: Arial, sans-serif; font-size: 12px; color: #111; margin: 0; }}
  .invoice-page {{ padding: 24px 28px; page-break-after: always; border-bottom: 3px dashed #e2e8f0; }}
  .invoice-page:last-child {{ page-break-after: auto; border-bottom: none; }}
  h1 {{ font-size: 18px; color: #0f172a; margin: 0; }}
  .header {{ display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:16px; border-bottom:2px solid #0f172a; padding-bottom:10px; }}
  .inv-meta {{ text-align:right; }}
  table {{ width:100%; border-collapse:collapse; margin-top:8px; font-size:12px; }}
  th {{ background:#f8fafc; padding:6px 8px; text-align:left; font-size:10px; font-weight:700; text-transform:uppercase; color:#64748b; }}
  td {{ padding:6px 8px; border-bottom:1px solid #f1f5f9; }}
  .pill {{ display:inline-block; padding:1px 7px; border-radius:99px; font-size:10px; font-weight:700; background:#fef3c7; color:#92400e; }}
  .no-print {{ margin:12px; }}
  @media print {{ .no-print {{ display:none; }} }}
</style>
</head>
<body>
<div class="no-print">
  <button onclick="window.print()" style="padding:8px 18px;background:#0f172a;color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:600">🖨 Print All ({len(invoice_blocks)} invoices)</button>
  <button onclick="window.close()" style="margin-left:8px;padding:8px 18px;background:#f1f5f9;color:#0f172a;border:1px solid #e2e8f0;border-radius:6px;cursor:pointer">Close</button>
</div>
{''.join(invoice_blocks)}
</body></html>"""

    return HTMLResponse(content=combined)


# ─────────────────────────────────────────────────────────────
# WhatsApp Chat
# ─────────────────────────────────────────────────────────────

def get_whatsapp_history(db: Session, customer_id: UUID, current_user: Employee):
    """Return all WhatsApp interactions for a customer, newest first."""
    customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id, Customer.tenant_id == current_user.tenant_id)
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    interactions = (
        db.query(CustomerInteraction)
        .filter(
            CustomerInteraction.tenant_id == current_user.tenant_id,
            CustomerInteraction.customer_id == customer_id,
            CustomerInteraction.interaction_type == InteractionType.whatsapp,
        )
        .order_by(CustomerInteraction.created_at.desc())
        .all()
    )

    result = []
    if interactions:
        # Batch-fetch all employee names in one query
        emp_ids = list({i.employee_id for i in interactions})
        employees = db.query(Employee).filter(Employee.id.in_(emp_ids)).all()
        emp_map = {str(e.id): e.name for e in employees}
        for i in interactions:
            result.append({
                "id": str(i.id),
                "message": i.message_content,
                "sent_by": emp_map.get(str(i.employee_id), "Unknown"),
                "sent_at": i.created_at.isoformat() if i.created_at else None,
            })
    return {"phone": customer.phone, "messages": result}


def compose_whatsapp_for_customer(
    db: Session, customer_id: UUID, order_id, current_user: Employee
):
    """Compose a WhatsApp message from an order (no logging — just preview)."""
    customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id, Customer.tenant_id == current_user.tenant_id)
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    if not order_id:
        # Return a bare link with no template
        from app.core.whatsapp import normalize_phone_e164, format_phone_display
        to = normalize_phone_e164(customer.phone or "")
        return {
            "phone_display": format_phone_display(customer.phone or ""),
            "wa_url": f"https://wa.me/{to}" if to else "",
            "message": "",
            "template": "custom",
        }

    order = (
        db.query(Order)
        .filter(Order.id == order_id, Order.tenant_id == current_user.tenant_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    items_text = "\n".join(
        f"{oi.product_name} x{oi.quantity}" for oi in order.items
    )
    address = " ".join(filter(None, [
        order.delivery_address,
        order.delivery_city,
        order.delivery_state,
    ]))
    pincode = order.delivery_pincode or ""
    amount = str(int(order.total_amount)) if order.total_amount else ""
    payment_type = order.payment_method.value if order.payment_method else ""

    result = _compose_wa(
        name=customer.name,
        phone=customer.phone or "",
        order_number=order.order_number,
        tracking_number=order.tracking_number or None,
        courier_name=order.courier_name or None,
        items_text=items_text,
        amount=amount,
        address=address,
        pincode=pincode,
        payment_type=payment_type,
    )
    return result


def log_whatsapp_message(
    db: Session, customer_id: UUID, message: str, order_id, current_user: Employee
):
    """Log a WhatsApp message as a CustomerInteraction and return wa_url."""
    customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id, Customer.tenant_id == current_user.tenant_id)
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    interaction = CustomerInteraction(
        tenant_id=current_user.tenant_id,
        customer_id=customer_id,
        employee_id=current_user.id,
        interaction_type=InteractionType.whatsapp,
        message_content=message,
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)

    from app.core.whatsapp import normalize_phone_e164, format_phone_display
    import urllib.parse
    to = normalize_phone_e164(customer.phone or "")
    wa_url = f"https://wa.me/{to}?text={urllib.parse.quote(message)}" if to else ""

    return {
        "id": str(interaction.id),
        "wa_url": wa_url,
        "phone_display": format_phone_display(customer.phone or ""),
        "message": message,
        "sent_at": interaction.created_at.isoformat() if interaction.created_at else None,
    }
