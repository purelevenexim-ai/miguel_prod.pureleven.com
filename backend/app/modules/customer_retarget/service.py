from datetime import datetime, timezone
from decimal import Decimal
import re
from typing import Optional
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import and_, case, exists, func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.customer import (
    Customer,
    CustomerTag,
    CustomerTagMap,
    CustomerType,
    LeadStatus,
    SourceType,
)
from app.models.customer_retarget import (
    CustomerRetargetCall,
    CustomerRetargetState,
    RetargetOutcome,
)
from app.models.employee import Employee
from app.models.order import Order, OrderStatus
from app.models.shopify_order import ShopifyOrder, ShopifyOrderStatus
from app.modules.customer_retarget.schemas import (
    RetargetCallCreate,
    RetargetTemplateBulkSend,
    UnlinkedResolveRequest,
)
from app.modules.customers.service import (
    generate_customer_code,
    get_customer_orders,
)
from app.modules.message_automation import service as message_automation_service


FOLLOW_UP_OUTCOMES = (
    RetargetOutcome.no_answer,
    RetargetOutcome.callback,
    RetargetOutcome.interested,
)
CLOSED_OUTCOMES = (
    RetargetOutcome.not_interested,
    RetargetOutcome.purchased_elsewhere,
)
VALID_VIEWS = {
    "to_contact",
    "follow_up",
    "interested",
    "purchased_again",
    "closed",
    "risk",
    "missing_details",
    "unlinked",
    "all",
}
OLD_CUSTOMERS_TAG = "Old Customers"
RETARGET_TEMPLATE_VARIABLES = {
    "customer_name",
    "name",
    "phone",
    "website_url",
    "whatsapp_link",
}


def _phone_key(value: Optional[str]) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 12 and digits.startswith("91"):
        return digits[2:]
    if len(digits) > 10:
        return digits[-10:]
    return digits


def _old_customer_ids_query(db: Session, tenant_id: UUID):
    return (
        db.query(CustomerTagMap.customer_id)
        .join(CustomerTag, CustomerTag.id == CustomerTagMap.tag_id)
        .filter(
            CustomerTagMap.tenant_id == tenant_id,
            CustomerTag.tenant_id == tenant_id,
            func.lower(CustomerTag.name) == OLD_CUSTOMERS_TAG.lower(),
        )
    )


def _is_old_customer(db: Session, tenant_id: UUID, customer_id: UUID) -> bool:
    return (
        _old_customer_ids_query(db, tenant_id)
        .filter(CustomerTagMap.customer_id == customer_id)
        .first()
        is not None
    )


def _missing_fields(customer: Customer) -> list[str]:
    missing = []
    name = (customer.name or "").strip()
    if not name or name.lower() in {"unknown", "customer", "n/a", "na"}:
        missing.append("name")
    if not _phone_key(customer.phone):
        missing.append("phone")
    if not (customer.address or "").strip():
        missing.append("address")
    if not (customer.city or "").strip():
        missing.append("city")
    if not (customer.state or "").strip():
        missing.append("state")
    if not (customer.pincode or "").strip():
        missing.append("pincode")
    return missing


async def queue_retarget_template(
    db: Session,
    current_user: Employee,
    data: RetargetTemplateBulkSend,
) -> dict:
    template_info = await message_automation_service.resolve_manual_whatsapp_template(
        db,
        current_user.tenant_id,
        template_name=data.template_name,
        language_code=data.language_code,
    )
    if template_info is None:
        raise HTTPException(
            status_code=422,
            detail="The selected template and language are not approved or are unavailable",
        )

    template_json = template_info.get("template_json") or {}
    parameter_format, body_parameters = message_automation_service._template_parameter_summary(
        data.template_name,
        template_json,
    )
    if parameter_format == "POSITIONAL" and len(body_parameters) > 1:
        raise HTTPException(
            status_code=422,
            detail="This template needs more than the customer-name value and cannot be bulk sent from Customer Retarget",
        )
    if parameter_format == "NAMED":
        unsupported = [
            value for value in body_parameters
            if value not in RETARGET_TEMPLATE_VARIABLES
        ]
        if unsupported:
            raise HTTPException(
                status_code=422,
                detail=f"Template requires unsupported values: {', '.join(unsupported)}",
            )
    if message_automation_service._template_button_parameter_summary(template_json):
        raise HTTPException(
            status_code=422,
            detail="Templates with dynamic website-button values are not supported here; use a static website URL",
        )

    has_media_header = message_automation_service._template_has_media_header(template_json)
    if has_media_header and not data.header_image_url:
        raise HTTPException(
            status_code=422,
            detail="This template requires a public HTTPS header image URL",
        )

    customers = (
        db.query(Customer)
        .filter(
            Customer.tenant_id == current_user.tenant_id,
            Customer.id.in_(data.customer_ids),
        )
        .all()
    )
    customers_by_id = {customer.id: customer for customer in customers}
    batch_id = uuid4()
    queued = []
    skipped = []

    for customer_id in data.customer_ids:
        customer = customers_by_id.get(customer_id)
        if customer is None:
            skipped.append({"customer_id": str(customer_id), "reason": "Customer not found"})
            continue

        phone = message_automation_service.normalize_phone_e164(customer.phone)
        if not phone:
            skipped.append(
                {"customer_id": str(customer.id), "name": customer.name, "reason": "Missing valid phone"}
            )
            continue
        if message_automation_service.preference_blocks(
            db,
            current_user.tenant_id,
            phone,
            "whatsapp",
        ):
            skipped.append(
                {"customer_id": str(customer.id), "name": customer.name, "reason": "WhatsApp opted out"}
            )
            continue

        task = message_automation_service.queue_manual_retarget_template(
            db,
            tenant_id=current_user.tenant_id,
            customer=customer,
            template_name=data.template_name,
            language_code=data.language_code,
            header_image_url=data.header_image_url,
            employee_id=current_user.id,
            batch_id=batch_id,
        )
        if task is None:
            skipped.append(
                {"customer_id": str(customer.id), "name": customer.name, "reason": "Messaging automation unavailable"}
            )
            continue
        queued.append(
            {
                "task_id": str(task.id),
                "customer_id": str(customer.id),
                "name": customer.name,
                "phone": phone,
            }
        )

    db.commit()
    return {
        "batch_id": str(batch_id),
        "template_name": data.template_name,
        "language_code": template_info.get("locale") or data.language_code,
        "requested": len(data.customer_ids),
        "queued": len(queued),
        "skipped": len(skipped),
        "queued_customers": queued,
        "skipped_customers": skipped,
        "message": (
            f"{len(queued)} WhatsApp message{'s' if len(queued) != 1 else ''} queued for sending"
        ),
    }


def _order_aggregate_subquery(db: Session, tenant_id: UUID):
    manual_success = case(
        (
            Order.status.in_([OrderStatus.cancelled, OrderStatus.returned]),
            0,
        ),
        else_=1,
    )
    shopify_success = case(
        (
            ShopifyOrder.shopify_status.in_(
                [ShopifyOrderStatus.cancelled, ShopifyOrderStatus.returned]
            ),
            0,
        ),
        else_=1,
    )

    manual = db.query(
        Order.customer_id.label("customer_id"),
        Order.created_at.label("ordered_at"),
        Order.total_amount.label("amount"),
        manual_success.label("successful"),
    ).filter(
        Order.tenant_id == tenant_id,
        Order.customer_id.isnot(None),
    )

    shopify = db.query(
        ShopifyOrder.customer_id.label("customer_id"),
        ShopifyOrder.created_at_shopify.label("ordered_at"),
        ShopifyOrder.total_price.label("amount"),
        shopify_success.label("successful"),
    ).filter(
        ShopifyOrder.tenant_id == tenant_id,
        ShopifyOrder.customer_id.isnot(None),
    )

    combined = manual.union_all(shopify).subquery()
    return (
        db.query(
            combined.c.customer_id.label("customer_id"),
            func.count().label("order_count"),
            func.sum(combined.c.successful).label("successful_order_count"),
            func.coalesce(
                func.sum(
                    case(
                        (combined.c.successful == 1, combined.c.amount),
                        else_=0,
                    )
                ),
                0,
            ).label("lifetime_value"),
            func.min(combined.c.ordered_at).label("first_order_date"),
            func.max(combined.c.ordered_at).label("latest_order_date"),
        )
        .group_by(combined.c.customer_id)
        .subquery()
    )


def _unlinked_groups(
    db: Session,
    tenant_id: UUID,
    search: Optional[str] = None,
    repeat_only: bool = False,
) -> list[dict]:
    orders = (
        db.query(ShopifyOrder)
        .filter(
            ShopifyOrder.tenant_id == tenant_id,
            ShopifyOrder.customer_id.is_(None),
        )
        .order_by(
            ShopifyOrder.created_at_shopify.asc(),
            ShopifyOrder.id.asc(),
        )
        .all()
    )

    grouped: dict[str, list[ShopifyOrder]] = {}
    for order in orders:
        phone = order.customer_phone or order.shipping_phone or ""
        key = _phone_key(phone) or f"order:{order.id}"
        grouped.setdefault(key, []).append(order)

    phone_keys = [key for key in grouped if not key.startswith("order:")]
    customer_matches: dict[str, Customer] = {}
    if phone_keys:
        customer_phone = func.right(
            func.regexp_replace(func.coalesce(Customer.phone, ""), r"\D", "", "g"),
            10,
        )
        matches = (
            db.query(Customer)
            .filter(
                Customer.tenant_id == tenant_id,
                customer_phone.in_(phone_keys),
            )
            .order_by(Customer.is_active.desc(), Customer.created_at.asc())
            .all()
        )
        for match in matches:
            customer_matches.setdefault(_phone_key(match.phone), match)

    result = []
    search_text = (search or "").strip().lower()
    for key, buyer_orders in grouped.items():
        latest = max(
            buyer_orders,
            key=lambda item: (item.created_at_shopify, str(item.id)),
        )
        if repeat_only and len(buyer_orders) <= 1:
            continue

        searchable = " ".join(
            [
                latest.customer_name or "",
                latest.shipping_name or "",
                latest.customer_phone or "",
                latest.shipping_phone or "",
                latest.shopify_order_name or "",
            ]
        ).lower()
        if search_text and search_text not in searchable:
            continue

        successful = [
            item
            for item in buyer_orders
            if item.shopify_status
            not in {ShopifyOrderStatus.cancelled, ShopifyOrderStatus.returned}
        ]
        value = sum(
            (Decimal(str(item.total_price or 0)) for item in successful),
            Decimal("0"),
        )
        products = []
        for line in latest.line_items_json or []:
            label = line.get("title") or line.get("name") or "Item"
            quantity = line.get("quantity", 1)
            products.append(f"{label} ×{quantity}")

        suggested = customer_matches.get(key)
        result.append(
            {
                "kind": "unlinked",
                "id": f"unlinked:{key}",
                "representative_order_id": str(latest.id),
                "order_ids": [str(item.id) for item in buyer_orders],
                "customer_id": None,
                "customer_code": "",
                "name": latest.customer_name or latest.shipping_name or "Unknown customer",
                "phone": latest.customer_phone or latest.shipping_phone or "",
                "alternate_phone": (
                    latest.shipping_phone
                    if latest.shipping_phone != latest.customer_phone
                    else ""
                ),
                "email": latest.customer_email or "",
                "address": ", ".join(
                    part
                    for part in [
                        latest.shipping_address_line1,
                        latest.shipping_address_line2,
                    ]
                    if part
                ),
                "city": latest.shipping_city or "",
                "state": latest.shipping_state or "",
                "pincode": latest.shipping_zip or "",
                "latest_order_date": latest.created_at_shopify.isoformat(),
                "latest_order_number": latest.shopify_order_name,
                "latest_order_status": (
                    latest.shopify_status.value
                    if latest.shopify_status
                    else ""
                ),
                "latest_products": products[:3],
                "order_count": len(buyer_orders),
                "successful_order_count": len(successful),
                "lifetime_value": str(value),
                "outcome": "unlinked",
                "last_call_at": None,
                "next_callback_at": None,
                "latest_notes": "",
                "last_employee_name": "",
                "missing_fields": [
                    field
                    for field, value_item in {
                        "name": latest.customer_name or latest.shipping_name,
                        "phone": latest.customer_phone or latest.shipping_phone,
                        "address": latest.shipping_address_line1,
                        "city": latest.shipping_city,
                        "state": latest.shipping_state,
                        "pincode": latest.shipping_zip,
                    }.items()
                    if not (value_item or "").strip()
                ],
                "suggested_customer": (
                    {
                        "id": str(suggested.id),
                        "name": suggested.name,
                        "phone": suggested.phone,
                        "customer_code": suggested.unique_customer_code,
                    }
                    if suggested
                    else None
                ),
            }
        )

    result.sort(key=lambda item: (item["latest_order_date"], item["id"]))
    return result


def _summary(
    db: Session,
    tenant_id: UUID,
    aggregate,
    unlinked_groups: list[dict],
) -> dict:
    now = datetime.now(timezone.utc)
    rows = (
        db.query(
            aggregate.c.customer_id,
            aggregate.c.order_count,
            CustomerRetargetState.current_outcome,
            CustomerRetargetState.next_callback_at,
        )
        .outerjoin(
            CustomerRetargetState,
            and_(
                CustomerRetargetState.tenant_id == tenant_id,
                CustomerRetargetState.customer_id == aggregate.c.customer_id,
            ),
        )
        .all()
    )
    old_rows = _old_customers_without_orders_query(
        db,
        tenant_id,
    ).all()
    old_states = [state for _, state in old_rows]
    old_customer_count = _old_customer_ids_query(db, tenant_id).count()

    linked_total = len(rows)
    never_contacted = sum(1 for row in rows if row.current_outcome is None)
    never_contacted += sum(1 for state in old_states if state is None)
    callbacks_due = sum(
        1
        for row in rows
        if row.current_outcome in FOLLOW_UP_OUTCOMES
        and row.next_callback_at is not None
        and row.next_callback_at <= now
    )
    callbacks_due += sum(
        1
        for state in old_states
        if state is not None
        and state.current_outcome in FOLLOW_UP_OUTCOMES
        and state.next_callback_at is not None
        and state.next_callback_at <= now
    )
    interested = sum(
        1 for row in rows if row.current_outcome == RetargetOutcome.interested
    )
    interested += sum(
        1
        for state in old_states
        if state is not None
        and state.current_outcome == RetargetOutcome.interested
    )
    purchased_again = sum(
        1 for row in rows if row.current_outcome == RetargetOutcome.purchased_again
    )
    purchased_again += sum(
        1
        for state in old_states
        if state is not None
        and state.current_outcome == RetargetOutcome.purchased_again
    )
    risk = sum(1 for row in rows if row.current_outcome == RetargetOutcome.risk)
    risk += sum(
        1
        for state in old_states
        if state is not None and state.current_outcome == RetargetOutcome.risk
    )
    repeat_buyers = sum(1 for row in rows if (row.order_count or 0) > 1)
    repeat_buyers += sum(1 for item in unlinked_groups if item["order_count"] > 1)

    unlinked_count = len(unlinked_groups)
    old_without_orders = len(old_rows)
    total_eligible = linked_total + unlinked_count + old_without_orders
    contacted = (
        linked_total
        + old_without_orders
        - never_contacted
    )
    coverage = round((contacted / total_eligible) * 100, 1) if total_eligible else 0

    return {
        "total_eligible": total_eligible,
        "linked_customers": linked_total,
        "unlinked_buyers": unlinked_count,
        "never_contacted": never_contacted + unlinked_count,
        "contacted": contacted,
        "coverage_percent": coverage,
        "callbacks_due": callbacks_due,
        "interested": interested,
        "purchased_again": purchased_again,
        "risk": risk,
        "repeat_buyers": repeat_buyers,
        "old_customers": old_customer_count,
    }


def _latest_orders(
    db: Session,
    tenant_id: UUID,
    customer_ids: list[UUID],
) -> dict[UUID, tuple[object, bool]]:
    if not customer_ids:
        return {}

    manual_orders = (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(
            Order.tenant_id == tenant_id,
            Order.customer_id.in_(customer_ids),
        )
        .distinct(Order.customer_id)
        .order_by(
            Order.customer_id,
            Order.created_at.desc(),
            Order.id.desc(),
        )
        .all()
    )
    shopify_orders = (
        db.query(ShopifyOrder)
        .filter(
            ShopifyOrder.tenant_id == tenant_id,
            ShopifyOrder.customer_id.in_(customer_ids),
        )
        .distinct(ShopifyOrder.customer_id)
        .order_by(
            ShopifyOrder.customer_id,
            ShopifyOrder.created_at_shopify.desc(),
            ShopifyOrder.id.desc(),
        )
        .all()
    )

    latest: dict[UUID, tuple[object, bool]] = {
        order.customer_id: (order, False) for order in manual_orders
    }
    for order in shopify_orders:
        current = latest.get(order.customer_id)
        if current is None or order.created_at_shopify > current[0].created_at:
            latest[order.customer_id] = (order, True)
    return latest


def _serialize_linked_rows(
    db: Session,
    tenant_id: UUID,
    rows: list,
    offset: int,
) -> list[dict]:
    customer_ids = [row[0].id for row in rows]
    latest_orders = _latest_orders(db, tenant_id, customer_ids)
    old_customer_ids = {
        row[0]
        for row in _old_customer_ids_query(db, tenant_id)
        .filter(CustomerTagMap.customer_id.in_(customer_ids))
        .all()
    } if customer_ids else set()
    employee_ids = {
        row[6].last_employee_id
        for row in rows
        if row[6] is not None and row[6].last_employee_id
    }
    employee_names = {}
    if employee_ids:
        employee_names = {
            employee.id: employee.full_name
            for employee in db.query(Employee)
            .filter(
                Employee.tenant_id == tenant_id,
                Employee.id.in_(employee_ids),
            )
            .all()
        }

    items = []
    for index, row in enumerate(rows):
        (
            customer,
            order_count,
            successful_order_count,
            lifetime_value,
            first_order_date,
            latest_order_date,
            state,
        ) = row
        latest_info = latest_orders.get(customer.id)
        latest_order = latest_info[0] if latest_info else None
        is_shopify = latest_info[1] if latest_info else False

        products = []
        latest_order_number = ""
        latest_status = ""
        if latest_order:
            if is_shopify:
                latest_order_number = latest_order.shopify_order_name
                latest_status = (
                    latest_order.shopify_status.value
                    if latest_order.shopify_status
                    else ""
                )
                for line in latest_order.line_items_json or []:
                    products.append(
                        f"{line.get('title') or line.get('name') or 'Item'} "
                        f"×{line.get('quantity', 1)}"
                    )
            else:
                latest_order_number = latest_order.order_number
                latest_status = (
                    latest_order.status.value if latest_order.status else ""
                )
                products = [
                    f"{item.product_name} ×{item.quantity}"
                    for item in (latest_order.items or [])
                ]

        items.append(
            {
                "kind": "customer",
                "queue_position": offset + index + 1,
                "id": str(customer.id),
                "customer_id": str(customer.id),
                "customer_code": customer.unique_customer_code,
                "name": customer.name,
                "phone": customer.phone,
                "alternate_phone": customer.alternate_phone or "",
                "email": customer.email or "",
                "address": customer.address or "",
                "city": customer.city or "",
                "state": customer.state or "",
                "pincode": customer.pincode or "",
                "first_order_date": (
                    first_order_date.isoformat() if first_order_date else None
                ),
                "latest_order_date": (
                    latest_order_date.isoformat() if latest_order_date else None
                ),
                "latest_order_number": latest_order_number,
                "latest_order_status": latest_status,
                "latest_products": products[:3],
                "order_count": int(order_count or 0),
                "successful_order_count": int(successful_order_count or 0),
                "lifetime_value": str(lifetime_value or 0),
                "outcome": (
                    state.current_outcome.value if state else "pending"
                ),
                "last_call_at": (
                    state.last_call_at.isoformat() if state else None
                ),
                "next_callback_at": (
                    state.next_callback_at.isoformat()
                    if state and state.next_callback_at
                    else None
                ),
                "latest_notes": state.latest_notes or "" if state else "",
                "last_employee_name": (
                    employee_names.get(state.last_employee_id, "")
                    if state
                    else ""
                ),
                "missing_fields": _missing_fields(customer),
                "is_old_customer": customer.id in old_customer_ids,
            }
        )
    return items


def _old_customers_without_orders_query(
    db: Session,
    tenant_id: UUID,
    search: Optional[str] = None,
):
    query = (
        db.query(Customer, CustomerRetargetState)
        .join(
            CustomerTagMap,
            and_(
                CustomerTagMap.customer_id == Customer.id,
                CustomerTagMap.tenant_id == tenant_id,
            ),
        )
        .join(
            CustomerTag,
            and_(
                CustomerTag.id == CustomerTagMap.tag_id,
                CustomerTag.tenant_id == tenant_id,
                func.lower(CustomerTag.name) == OLD_CUSTOMERS_TAG.lower(),
            ),
        )
        .outerjoin(
            CustomerRetargetState,
            and_(
                CustomerRetargetState.tenant_id == tenant_id,
                CustomerRetargetState.customer_id == Customer.id,
            ),
        )
        .filter(
            Customer.tenant_id == tenant_id,
            ~exists().where(
                and_(
                    Order.tenant_id == tenant_id,
                    Order.customer_id == Customer.id,
                )
            ),
            ~exists().where(
                and_(
                    ShopifyOrder.tenant_id == tenant_id,
                    ShopifyOrder.customer_id == Customer.id,
                )
            ),
        )
    )
    if search:
        value = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Customer.name.ilike(value),
                Customer.phone.ilike(value),
                Customer.alternate_phone.ilike(value),
                Customer.unique_customer_code.ilike(value),
            )
        )
    return query


def _serialize_old_customer_rows(
    db: Session,
    tenant_id: UUID,
    rows: list,
    offset: int,
) -> list[dict]:
    employee_ids = {
        state.last_employee_id
        for _, state in rows
        if state is not None and state.last_employee_id
    }
    employee_names = {
        employee.id: employee.full_name
        for employee in db.query(Employee)
        .filter(
            Employee.tenant_id == tenant_id,
            Employee.id.in_(employee_ids),
        )
        .all()
    } if employee_ids else {}

    result = []
    for index, (customer, state) in enumerate(rows):
        missing = _missing_fields(customer)
        missing.extend(["purchase date", "products purchased"])
        result.append(
            {
                "kind": "customer",
                "queue_position": offset + index + 1,
                "id": str(customer.id),
                "customer_id": str(customer.id),
                "customer_code": customer.unique_customer_code,
                "name": customer.name,
                "phone": customer.phone,
                "alternate_phone": customer.alternate_phone or "",
                "email": customer.email or "",
                "address": customer.address or "",
                "city": customer.city or "",
                "state": customer.state or "",
                "pincode": customer.pincode or "",
                "first_order_date": None,
                "latest_order_date": None,
                "latest_order_number": "Old WhatsApp contact",
                "latest_order_status": "Purchase history unavailable",
                "latest_products": [],
                "order_count": 0,
                "successful_order_count": 0,
                "lifetime_value": "0",
                "outcome": state.current_outcome.value if state else "pending",
                "last_call_at": (
                    state.last_call_at.isoformat() if state else None
                ),
                "next_callback_at": (
                    state.next_callback_at.isoformat()
                    if state and state.next_callback_at
                    else None
                ),
                "latest_notes": state.latest_notes or "" if state else "",
                "last_employee_name": (
                    employee_names.get(state.last_employee_id, "")
                    if state
                    else ""
                ),
                "missing_fields": list(dict.fromkeys(missing)),
                "is_old_customer": True,
            }
        )
    return result


def get_queue(
    db: Session,
    current_user: Employee,
    *,
    view: str,
    search: Optional[str],
    repeat_only: bool,
    page: int,
    limit: int,
) -> dict:
    if view not in VALID_VIEWS:
        raise HTTPException(status_code=400, detail="Unknown queue view")

    tenant_id = current_user.tenant_id
    aggregate = _order_aggregate_subquery(db, tenant_id)
    all_unlinked = _unlinked_groups(db, tenant_id)
    summary = _summary(db, tenant_id, aggregate, all_unlinked)

    if view == "unlinked":
        filtered = _unlinked_groups(
            db,
            tenant_id,
            search=search,
            repeat_only=repeat_only,
        )
        total = len(filtered)
        offset = (page - 1) * limit
        page_items = filtered[offset : offset + limit]
        for index, item in enumerate(page_items):
            item["queue_position"] = offset + index + 1
        return {
            "summary": summary,
            "total": total,
            "page": page,
            "limit": limit,
            "data": page_items,
        }

    query = (
        db.query(
            Customer,
            aggregate.c.order_count,
            aggregate.c.successful_order_count,
            aggregate.c.lifetime_value,
            aggregate.c.first_order_date,
            aggregate.c.latest_order_date,
            CustomerRetargetState,
        )
        .join(aggregate, aggregate.c.customer_id == Customer.id)
        .outerjoin(
            CustomerRetargetState,
            and_(
                CustomerRetargetState.tenant_id == tenant_id,
                CustomerRetargetState.customer_id == Customer.id,
            ),
        )
        .filter(Customer.tenant_id == tenant_id)
    )

    if search:
        search_value = f"%{search.strip()}%"
        normalized_search = _phone_key(search)
        search_clauses = [
            Customer.name.ilike(search_value),
            Customer.phone.ilike(search_value),
            Customer.alternate_phone.ilike(search_value),
            Customer.unique_customer_code.ilike(search_value),
            exists().where(
                and_(
                    Order.tenant_id == tenant_id,
                    Order.customer_id == Customer.id,
                    Order.order_number.ilike(search_value),
                )
            ),
            exists().where(
                and_(
                    ShopifyOrder.tenant_id == tenant_id,
                    ShopifyOrder.customer_id == Customer.id,
                    ShopifyOrder.shopify_order_name.ilike(search_value),
                )
            ),
        ]
        if normalized_search:
            customer_phone = func.regexp_replace(
                func.coalesce(Customer.phone, ""),
                r"\D",
                "",
                "g",
            )
            alt_phone = func.regexp_replace(
                func.coalesce(Customer.alternate_phone, ""),
                r"\D",
                "",
                "g",
            )
            search_clauses.extend(
                [
                    customer_phone.ilike(f"%{normalized_search}%"),
                    alt_phone.ilike(f"%{normalized_search}%"),
                ]
            )
        query = query.filter(or_(*search_clauses))

    if repeat_only:
        query = query.filter(aggregate.c.order_count > 1)

    if view == "to_contact":
        pending_ordered = (
            query.filter(CustomerRetargetState.id.is_(None))
            .order_by(
                aggregate.c.latest_order_date.asc(),
                Customer.id.asc(),
            )
            .all()
        )
        pending_old_without_orders = []
        if not repeat_only:
            pending_old_without_orders = (
                _old_customers_without_orders_query(
                    db,
                    tenant_id,
                    search=search,
                )
                .filter(CustomerRetargetState.id.is_(None))
                .order_by(Customer.created_at.asc(), Customer.id.asc())
                .all()
            )
        tagged_ordered_ids = {
            row[0]
            for row in _old_customer_ids_query(db, tenant_id)
            .filter(
                CustomerTagMap.customer_id.in_(
                    [entry[0].id for entry in pending_ordered]
                )
            )
            .all()
        } if pending_ordered else set()
        oldest = datetime.min.replace(tzinfo=timezone.utc)
        mixed = [
            (
                oldest,
                f"old:{row[0].id}",
                "old",
                row,
            )
            for row in pending_old_without_orders
        ] + [
            (
                oldest if row[0].id in tagged_ordered_ids else row[5],
                f"customer:{row[0].id}",
                "customer",
                row,
            )
            for row in pending_ordered
        ]
        mixed.sort(key=lambda entry: (entry[0], entry[1]))
        total = len(mixed)
        offset = (page - 1) * limit
        page_entries = mixed[offset : offset + limit]
        linked_entries = [
            entry[3] for entry in page_entries if entry[2] == "customer"
        ]
        old_entries = [
            entry[3] for entry in page_entries if entry[2] == "old"
        ]
        linked_map = {
            item["id"]: item
            for item in _serialize_linked_rows(
                db,
                tenant_id,
                linked_entries,
                0,
            )
        }
        old_map = {
            item["id"]: item
            for item in _serialize_old_customer_rows(
                db,
                tenant_id,
                old_entries,
                0,
            )
        }
        data = []
        for index, entry in enumerate(page_entries):
            customer_id = str(entry[3][0].id)
            item = (
                linked_map[customer_id]
                if entry[2] == "customer"
                else old_map[customer_id]
            )
            item["queue_position"] = offset + index + 1
            data.append(item)
        return {
            "summary": summary,
            "total": total,
            "page": page,
            "limit": limit,
            "data": data,
        }

    if view == "follow_up":
        query = query.filter(
            CustomerRetargetState.current_outcome.in_(FOLLOW_UP_OUTCOMES)
        )
    elif view == "interested":
        query = query.filter(
            CustomerRetargetState.current_outcome == RetargetOutcome.interested
        )
    elif view == "purchased_again":
        query = query.filter(
            CustomerRetargetState.current_outcome
            == RetargetOutcome.purchased_again
        )
    elif view == "closed":
        query = query.filter(
            CustomerRetargetState.current_outcome.in_(CLOSED_OUTCOMES)
        )
    elif view == "risk":
        query = query.filter(
            CustomerRetargetState.current_outcome == RetargetOutcome.risk
        )
    elif view == "missing_details":
        query = query.filter(
            or_(
                func.coalesce(func.trim(Customer.name), "").in_(
                    ["", "Unknown", "unknown", "Customer", "customer"]
                ),
                func.coalesce(func.trim(Customer.phone), "") == "",
                func.coalesce(func.trim(Customer.address), "") == "",
                func.coalesce(func.trim(Customer.city), "") == "",
                func.coalesce(func.trim(Customer.state), "") == "",
                func.coalesce(func.trim(Customer.pincode), "") == "",
                CustomerRetargetState.current_outcome
                == RetargetOutcome.invalid_number,
            )
        )

    offset = (page - 1) * limit
    if view == "all":
        linked_rows = query.order_by(
            aggregate.c.latest_order_date.asc(),
            Customer.id.asc(),
        ).all()
        filtered_unlinked = _unlinked_groups(
            db,
            tenant_id,
            search=search,
            repeat_only=repeat_only,
        )
        old_without_orders = []
        if not repeat_only:
            old_without_orders = (
                _old_customers_without_orders_query(
                    db,
                    tenant_id,
                    search=search,
                )
                .order_by(Customer.created_at.asc(), Customer.id.asc())
                .all()
            )
        mixed = [
            (
                row[5],
                f"customer:{row[0].id}",
                "customer",
                row,
            )
            for row in linked_rows
        ] + [
            (
                datetime.fromisoformat(item["latest_order_date"]),
                item["id"],
                "unlinked",
                item,
            )
            for item in filtered_unlinked
        ] + [
            (
                datetime.min.replace(tzinfo=timezone.utc),
                f"old:{row[0].id}",
                "old",
                row,
            )
            for row in old_without_orders
        ]
        mixed.sort(key=lambda entry: (entry[0], entry[1]))
        total = len(mixed)
        page_entries = mixed[offset : offset + limit]
        selected_linked = [
            entry[3] for entry in page_entries if entry[2] == "customer"
        ]
        selected_old = [
            entry[3] for entry in page_entries if entry[2] == "old"
        ]
        serialized_linked = {
            item["id"]: item
            for item in _serialize_linked_rows(
                db,
                tenant_id,
                selected_linked,
                0,
            )
        }
        serialized_old = {
            item["id"]: item
            for item in _serialize_old_customer_rows(
                db,
                tenant_id,
                selected_old,
                0,
            )
        }
        data = []
        for index, entry in enumerate(page_entries):
            if entry[2] == "customer":
                item = serialized_linked[str(entry[3][0].id)]
            elif entry[2] == "unlinked":
                item = entry[3]
            else:
                item = serialized_old[str(entry[3][0].id)]
            item["queue_position"] = offset + index + 1
            data.append(item)
        return {
            "summary": summary,
            "total": total,
            "page": page,
            "limit": limit,
            "data": data,
        }

    total = query.count()
    if view == "follow_up":
        query = query.order_by(
            CustomerRetargetState.next_callback_at.asc(),
            aggregate.c.latest_order_date.asc(),
            Customer.id.asc(),
        )
    else:
        query = query.order_by(
            aggregate.c.latest_order_date.asc(),
            Customer.id.asc(),
        )
    rows = query.offset(offset).limit(limit).all()

    return {
        "summary": summary,
        "total": total,
        "page": page,
        "limit": limit,
        "data": _serialize_linked_rows(db, tenant_id, rows, offset),
    }


def get_customer_workspace(
    db: Session,
    current_user: Employee,
    customer_id: UUID,
) -> dict:
    customer = (
        db.query(Customer)
        .filter(
            Customer.id == customer_id,
            Customer.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    has_order = (
        db.query(Order.id)
        .filter(
            Order.tenant_id == current_user.tenant_id,
            Order.customer_id == customer.id,
        )
        .first()
        or db.query(ShopifyOrder.id)
        .filter(
            ShopifyOrder.tenant_id == current_user.tenant_id,
            ShopifyOrder.customer_id == customer.id,
        )
        .first()
    )
    is_old_customer = _is_old_customer(
        db,
        current_user.tenant_id,
        customer.id,
    )
    if not has_order and not is_old_customer:
        raise HTTPException(
            status_code=404,
            detail="Customer has no orders and is not in the retarget queue",
        )

    state = (
        db.query(CustomerRetargetState)
        .filter(
            CustomerRetargetState.tenant_id == current_user.tenant_id,
            CustomerRetargetState.customer_id == customer.id,
        )
        .first()
    )
    calls = (
        db.query(CustomerRetargetCall, Employee)
        .join(Employee, Employee.id == CustomerRetargetCall.employee_id)
        .filter(
            CustomerRetargetCall.tenant_id == current_user.tenant_id,
            CustomerRetargetCall.customer_id == customer.id,
        )
        .order_by(
            CustomerRetargetCall.created_at.desc(),
            CustomerRetargetCall.id.desc(),
        )
        .all()
    )

    return {
        "customer": {
            "id": str(customer.id),
            "customer_code": customer.unique_customer_code,
            "name": customer.name,
            "phone": customer.phone,
            "alternate_phone": customer.alternate_phone or "",
            "email": customer.email or "",
            "address": customer.address or "",
            "city": customer.city or "",
            "state": customer.state or "",
            "pincode": customer.pincode or "",
            "country": customer.country or "India",
            "notes": customer.notes or "",
            "missing_fields": _missing_fields(customer),
            "is_old_customer": is_old_customer,
        },
        "state": {
            "outcome": state.current_outcome.value if state else "pending",
            "last_call_at": state.last_call_at.isoformat() if state else None,
            "next_callback_at": (
                state.next_callback_at.isoformat()
                if state and state.next_callback_at
                else None
            ),
            "latest_notes": state.latest_notes or "" if state else "",
        },
        "orders": get_customer_orders(db, customer.id, current_user),
        "calls": [
            {
                "id": str(call.id),
                "outcome": call.outcome.value,
                "phone_called": call.phone_called or "",
                "notes": call.notes or "",
                "next_callback_at": (
                    call.next_callback_at.isoformat()
                    if call.next_callback_at
                    else None
                ),
                "created_at": call.created_at.isoformat(),
                "employee_id": str(employee.id),
                "employee_name": employee.full_name,
            }
            for call, employee in calls
        ],
    }


def log_customer_call(
    db: Session,
    current_user: Employee,
    customer_id: UUID,
    data: RetargetCallCreate,
) -> dict:
    customer = (
        db.query(Customer)
        .filter(
            Customer.id == customer_id,
            Customer.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    has_manual_order = (
        db.query(Order.id)
        .filter(
            Order.tenant_id == current_user.tenant_id,
            Order.customer_id == customer.id,
        )
        .first()
        is not None
    )
    has_shopify_order = (
        db.query(ShopifyOrder.id)
        .filter(
            ShopifyOrder.tenant_id == current_user.tenant_id,
            ShopifyOrder.customer_id == customer.id,
        )
        .first()
        is not None
    )
    has_order = has_manual_order or has_shopify_order
    is_old_customer = _is_old_customer(
        db,
        current_user.tenant_id,
        customer.id,
    )
    if not has_order and not is_old_customer:
        raise HTTPException(
            status_code=400,
            detail="Only ordered or tagged old customers can be retargeted",
        )

    called_at = datetime.now(timezone.utc)
    phone_called = data.phone_called or customer.phone or None
    call = CustomerRetargetCall(
        tenant_id=current_user.tenant_id,
        customer_id=customer.id,
        employee_id=current_user.id,
        outcome=data.outcome,
        phone_called=phone_called,
        notes=data.notes,
        next_callback_at=data.next_callback_at,
        created_at=called_at,
    )
    db.add(call)

    state = (
        db.query(CustomerRetargetState)
        .filter(
            CustomerRetargetState.tenant_id == current_user.tenant_id,
            CustomerRetargetState.customer_id == customer.id,
        )
        .first()
    )
    if state is None:
        state = CustomerRetargetState(
            tenant_id=current_user.tenant_id,
            customer_id=customer.id,
            current_outcome=data.outcome,
            last_call_at=called_at,
            next_callback_at=data.next_callback_at,
            latest_notes=data.notes,
            last_employee_id=current_user.id,
        )
        db.add(state)
    else:
        state.current_outcome = data.outcome
        state.last_call_at = called_at
        state.next_callback_at = data.next_callback_at
        state.latest_notes = data.notes
        state.last_employee_id = current_user.id
        state.updated_at = called_at

    db.commit()
    db.refresh(call)
    return {
        "id": str(call.id),
        "customer_id": str(customer.id),
        "outcome": call.outcome.value,
        "phone_called": call.phone_called or "",
        "notes": call.notes or "",
        "next_callback_at": (
            call.next_callback_at.isoformat() if call.next_callback_at else None
        ),
        "created_at": call.created_at.isoformat(),
        "employee_name": current_user.full_name,
    }


def resolve_unlinked_buyer(
    db: Session,
    current_user: Employee,
    shopify_order_id: UUID,
    data: UnlinkedResolveRequest,
) -> dict:
    target = (
        db.query(ShopifyOrder)
        .filter(
            ShopifyOrder.id == shopify_order_id,
            ShopifyOrder.tenant_id == current_user.tenant_id,
            ShopifyOrder.customer_id.is_(None),
        )
        .first()
    )
    if not target:
        raise HTTPException(
            status_code=404,
            detail="Unlinked Shopify order not found",
        )

    target_phone = target.customer_phone or target.shipping_phone or ""
    target_key = _phone_key(target_phone)
    matching_orders_query = db.query(ShopifyOrder).filter(
        ShopifyOrder.tenant_id == current_user.tenant_id,
        ShopifyOrder.customer_id.is_(None),
    )
    if target_key:
        order_phone = func.right(
            func.regexp_replace(
                func.coalesce(
                    ShopifyOrder.customer_phone,
                    ShopifyOrder.shipping_phone,
                    "",
                ),
                r"\D",
                "",
                "g",
            ),
            10,
        )
        matching_orders_query = matching_orders_query.filter(
            order_phone == target_key
        )
    else:
        matching_orders_query = matching_orders_query.filter(
            ShopifyOrder.id == target.id
        )
    matching_orders = matching_orders_query.all()

    created = False
    if data.customer_id:
        customer = (
            db.query(Customer)
            .filter(
                Customer.id == data.customer_id,
                Customer.tenant_id == current_user.tenant_id,
            )
            .first()
        )
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
    else:
        payload = data.customer
        customer = Customer(
            tenant_id=current_user.tenant_id,
            unique_customer_code=generate_customer_code(
                db,
                current_user.tenant_id,
            ),
            name=payload.name.strip(),
            phone=payload.phone.strip(),
            alternate_phone=(payload.alternate_phone or "").strip() or None,
            email=payload.email,
            address=(payload.address or "").strip() or None,
            pincode=(payload.pincode or "").strip() or None,
            city=(payload.city or "").strip() or None,
            state=(payload.state or "").strip() or None,
            country=(payload.country or "India").strip(),
            customer_type=CustomerType.retail,
            source=SourceType.website,
            lead_status=LeadStatus.converted,
            notes=(payload.notes or "").strip()
            or f"Created from Shopify order {target.shopify_order_name}",
            created_by_employee_id=current_user.id,
        )
        db.add(customer)
        db.flush()
        created = True

    for order in matching_orders:
        order.customer_id = customer.id
    db.flush()

    linked_shopify = (
        db.query(ShopifyOrder)
        .filter(
            ShopifyOrder.tenant_id == current_user.tenant_id,
            ShopifyOrder.customer_id == customer.id,
        )
        .all()
    )
    linked_manual = (
        db.query(Order)
        .filter(
            Order.tenant_id == current_user.tenant_id,
            Order.customer_id == customer.id,
        )
        .all()
    )
    dates = [item.created_at_shopify for item in linked_shopify] + [
        item.created_at for item in linked_manual if item.created_at
    ]
    amounts = [
        Decimal(str(item.total_price or 0)) for item in linked_shopify
    ] + [Decimal(str(item.total_amount or 0)) for item in linked_manual]
    if dates:
        customer.first_order_date = min(dates)
        customer.last_order_date = max(dates)
    customer.total_orders = len(linked_shopify) + len(linked_manual)
    if customer.total_orders:
        customer.average_order_value = (
            sum(amounts, Decimal("0")) / customer.total_orders
        ).quantize(Decimal("0.01"))
    customer.updated_at = datetime.now(timezone.utc)

    db.commit()
    return {
        "customer_id": str(customer.id),
        "customer_code": customer.unique_customer_code,
        "created": created,
        "linked_order_count": len(matching_orders),
    }
