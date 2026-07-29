from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import re
from typing import Optional
from urllib.parse import urlparse
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

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
from app.models.message_automation import (
    CustomerMessagePreference,
    MessageAutomationTask,
)
from app.models.order import Order, OrderStatus
from app.models.shopify_order import ShopifyOrder, ShopifyOrderStatus
from app.models.wa_engine import (
    WaConversation,
    WaMessage,
    WaMessageDirection,
    WaSubscriber,
)
from app.modules.customer_retarget.schemas import (
    RetargetCallCreate,
    RetargetManualCustomerCreate,
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
    "premium",
    "high_value",
    "follow_up",
    "interested",
    "not_interested",
    "purchased_again",
    "closed",
    "risk",
    "missing_details",
    "unlinked",
    "all",
}
OLD_CUSTOMERS_TAG = "Old Customers"
MANUAL_RETARGET_TAG = "Customer Retarget"
TEST_CUSTOMER_TAG = "Test Customer"
RETARGET_TEMPLATE_VARIABLES = {
    "customer_name",
    "name",
    "phone",
    "website_url",
    "whatsapp_link",
}
MAX_RETARGET_BULK_RECIPIENTS = 5000
CAMPAIGN_REPORT_TIMEZONE = "Asia/Kolkata"
MAX_CAMPAIGN_REPORT_DAYS = 366
CAMPAIGN_MESSAGE_STATUSES = {
    "all",
    "pending",
    "sent",
    "failed",
    "skipped",
    "cancelled",
}


def _phone_key(value: Optional[str]) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 12 and digits.startswith("91"):
        return digits[2:]
    if len(digits) > 10:
        return digits[-10:]
    return digits


def _validate_custom_header_media_url(
    media_url: Optional[str],
    header_format: Optional[str],
) -> None:
    if not media_url or not header_format:
        return
    parsed = urlparse(media_url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    if host == "drive.google.com" and "/file/d/" in path:
        raise HTTPException(
            status_code=422,
            detail=(
                "Google Drive sharing pages cannot be used as WhatsApp "
                "header media. Leave this field blank to use the media "
                "approved with the Meta template."
            ),
        )

    extensions = {
        "image": {".jpg", ".jpeg", ".png", ".webp"},
        "video": {".mp4", ".3gp"},
        "document": {".pdf"},
    }
    known_extensions = set().union(*extensions.values())
    actual_extension = next(
        (extension for extension in known_extensions if path.endswith(extension)),
        None,
    )
    if actual_extension and actual_extension not in extensions.get(
        header_format,
        set(),
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                f"This template requires {header_format} header media, "
                f"but the custom URL points to {actual_extension}."
            ),
        )


def _old_customer_ids_query(db: Session, tenant_id: UUID):
    return _tagged_customer_ids_query(
        db,
        tenant_id,
        [OLD_CUSTOMERS_TAG],
    )


def _tagged_customer_ids_query(
    db: Session,
    tenant_id: UUID,
    tag_names: list[str],
):
    return (
        db.query(CustomerTagMap.customer_id)
        .join(CustomerTag, CustomerTag.id == CustomerTagMap.tag_id)
        .filter(
            CustomerTagMap.tenant_id == tenant_id,
            CustomerTag.tenant_id == tenant_id,
            func.lower(CustomerTag.name).in_(
                [name.lower() for name in tag_names]
            ),
        )
    )


def _is_old_customer(db: Session, tenant_id: UUID, customer_id: UUID) -> bool:
    return (
        _old_customer_ids_query(db, tenant_id)
        .filter(CustomerTagMap.customer_id == customer_id)
        .first()
        is not None
    )


def _is_manual_retarget_customer(
    db: Session,
    tenant_id: UUID,
    customer_id: UUID,
) -> bool:
    return (
        _tagged_customer_ids_query(
            db,
            tenant_id,
            [MANUAL_RETARGET_TAG],
        )
        .filter(CustomerTagMap.customer_id == customer_id)
        .first()
        is not None
    )


def _is_test_customer(
    db: Session,
    tenant_id: UUID,
    customer_id: UUID,
) -> bool:
    return (
        _tagged_customer_ids_query(
            db,
            tenant_id,
            [TEST_CUSTOMER_TAG],
        )
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


def _ensure_customer_tag(
    db: Session,
    tenant_id: UUID,
    customer_id: UUID,
    tag_name: str,
) -> None:
    tag = (
        db.query(CustomerTag)
        .filter(
            CustomerTag.tenant_id == tenant_id,
            func.lower(CustomerTag.name) == tag_name.lower(),
        )
        .first()
    )
    if tag is None:
        tag = CustomerTag(tenant_id=tenant_id, name=tag_name)
        db.add(tag)
        db.flush()
    exists_map = (
        db.query(CustomerTagMap.id)
        .filter(
            CustomerTagMap.tenant_id == tenant_id,
            CustomerTagMap.customer_id == customer_id,
            CustomerTagMap.tag_id == tag.id,
        )
        .first()
    )
    if exists_map is None:
        db.add(
            CustomerTagMap(
                tenant_id=tenant_id,
                customer_id=customer_id,
                tag_id=tag.id,
            )
        )


def add_manual_retarget_customer(
    db: Session,
    current_user: Employee,
    data: RetargetManualCustomerCreate,
) -> dict:
    tenant_id = current_user.tenant_id
    primary_key = _phone_key(data.phone)
    alternate_key = _phone_key(data.alternate_phone)
    if len(primary_key) != 10:
        raise HTTPException(
            status_code=422,
            detail="Enter a valid 10-digit primary phone number",
        )
    if alternate_key and len(alternate_key) != 10:
        raise HTTPException(
            status_code=422,
            detail="Enter a valid 10-digit alternate phone number",
        )
    if alternate_key and alternate_key == primary_key:
        raise HTTPException(
            status_code=422,
            detail="Primary and alternate phone numbers must be different",
        )

    customer_phone = func.right(
        func.regexp_replace(func.coalesce(Customer.phone, ""), r"\D", "", "g"),
        10,
    )
    alternate_phone = func.right(
        func.regexp_replace(
            func.coalesce(Customer.alternate_phone, ""),
            r"\D",
            "",
            "g",
        ),
        10,
    )
    match_keys = [primary_key] + ([alternate_key] if alternate_key else [])
    matches = (
        db.query(Customer)
        .filter(
            Customer.tenant_id == tenant_id,
            or_(
                customer_phone.in_(match_keys),
                alternate_phone.in_(match_keys),
            ),
        )
        .order_by(Customer.is_active.desc(), Customer.created_at.asc())
        .all()
    )
    customer = next(
        (
            item
            for item in matches
            if _phone_key(item.phone) == primary_key
            or _phone_key(item.alternate_phone) == primary_key
        ),
        None,
    )
    created = customer is None
    if customer is None:
        customer = Customer(
            tenant_id=tenant_id,
            unique_customer_code=generate_customer_code(db, tenant_id),
            name=data.name,
            phone=primary_key,
            alternate_phone=alternate_key or None,
            country="India",
            customer_type=CustomerType.retail,
            source=SourceType.manual,
            lead_status=LeadStatus.new,
            created_by_employee_id=current_user.id,
            notes=data.notes or "Manually added from Customer Retarget",
            is_active=True,
        )
        db.add(customer)
        db.flush()
    else:
        if _phone_key(customer.phone) == primary_key:
            customer.phone = primary_key
        if alternate_key:
            conflicting = next(
                (item for item in matches if item.id != customer.id),
                None,
            )
            if conflicting is not None:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "The alternate phone belongs to another customer: "
                        f"{conflicting.name}"
                    ),
                )
            customer.alternate_phone = alternate_key
        if not (customer.name or "").strip() or customer.name.lower() in {
            "unknown",
            "customer",
        }:
            customer.name = data.name
        if data.notes:
            customer.notes = data.notes
        customer.is_active = True

    _ensure_customer_tag(
        db,
        tenant_id,
        customer.id,
        MANUAL_RETARGET_TAG,
    )
    if data.is_test_customer:
        _ensure_customer_tag(
            db,
            tenant_id,
            customer.id,
            TEST_CUSTOMER_TAG,
        )
    db.commit()
    db.refresh(customer)
    return {
        "customer_id": str(customer.id),
        "customer_code": customer.unique_customer_code,
        "name": customer.name,
        "phone": customer.phone,
        "alternate_phone": customer.alternate_phone,
        "created": created,
        "is_test_customer": data.is_test_customer,
        "message": (
            "Customer created and added to Customer Retarget"
            if created
            else "Existing customer added to Customer Retarget"
        ),
    }


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

    header_format = message_automation_service._template_header_format(template_json)
    _validate_custom_header_media_url(
        data.header_image_url,
        header_format,
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
    override_phone = message_automation_service.normalize_phone_e164(
        data.recipient_phone_override
    )
    override_customer_id = (
        data.customer_ids[0] if override_phone and data.customer_ids else None
    )
    if override_customer_id:
        override_customer = customers_by_id.get(override_customer_id)
        allowed_phones = {
            message_automation_service.normalize_phone_e164(value)
            for value in (
                override_customer.phone if override_customer else None,
                (
                    override_customer.alternate_phone
                    if override_customer
                    else None
                ),
            )
            if value
        }
        if override_phone not in allowed_phones:
            raise HTTPException(
                status_code=422,
                detail=(
                    "The selected WhatsApp number must be the customer's "
                    "primary or alternate phone"
                ),
            )
    batch_id = uuid4()
    queued = []
    skipped = []
    normalized_phones = {
        phone
        for customer in customers
        if (
            phone := (
                override_phone
                if customer.id == override_customer_id
                else message_automation_service.normalize_phone_e164(
                    customer.phone
                )
            )
        )
    }
    blocked_phones = {
        preference.phone_e164
        for preference in db.query(CustomerMessagePreference)
        .filter(
            CustomerMessagePreference.tenant_id == current_user.tenant_id,
            CustomerMessagePreference.phone_e164.in_(normalized_phones),
            or_(
                CustomerMessagePreference.automation_paused.is_(True),
                CustomerMessagePreference.whatsapp_opted_out.is_(True),
            ),
        )
        .all()
    } if normalized_phones else set()
    automation_settings = message_automation_service.get_or_create_settings(
        db,
        current_user.tenant_id,
    )
    if not automation_settings.is_enabled:
        raise HTTPException(status_code=422, detail="Messaging automation is disabled")
    links = message_automation_service.tenant_links(db, current_user.tenant_id)
    scheduled_at = message_automation_service.now_utc()
    tasks_to_add: list[MessageAutomationTask] = []

    for customer_id in data.customer_ids:
        customer = customers_by_id.get(customer_id)
        if customer is None:
            skipped.append({"customer_id": str(customer_id), "reason": "Customer not found"})
            continue

        phone = (
            override_phone
            if customer.id == override_customer_id
            else message_automation_service.normalize_phone_e164(
                customer.phone
            )
        )
        if not phone:
            skipped.append(
                {"customer_id": str(customer.id), "name": customer.name, "reason": "Missing valid phone"}
            )
            continue
        if phone in blocked_phones:
            skipped.append(
                {"customer_id": str(customer.id), "name": customer.name, "reason": "WhatsApp opted out"}
            )
            continue

        customer_name = (customer.name or "").strip() or (
            "സുഹൃത്തേ"
            if message_automation_service._language_matches("ml", data.language_code)
            else "Customer"
        )
        task = MessageAutomationTask(
            id=uuid4(),
            tenant_id=current_user.tenant_id,
            customer_id=customer.id,
            channel="whatsapp",
            template_key=message_automation_service.RETARGET_MANUAL_TEMPLATE_KEY,
            event_type="customer_retarget_manual",
            status=message_automation_service.PENDING,
            recipient_phone_e164=phone,
            recipient_name=customer_name,
            body=f"WhatsApp template: {data.template_name}",
            payload={
                "manual_template_name": data.template_name,
                "manual_language_code": data.language_code,
                "manual_header_image_url": data.header_image_url,
                "manual_employee_id": str(current_user.id),
                "manual_batch_id": str(batch_id),
                "customer_name": customer_name,
                "name": customer_name,
                "phone": phone,
                **links,
            },
            dedupe_key=(
                f"customer-retarget:{batch_id}:{customer.id}:"
                f"{data.template_name}:{data.language_code}"
            ),
            scheduled_at=scheduled_at,
        )
        tasks_to_add.append(task)
        queued.append(
            {
                "task_id": str(task.id),
                "customer_id": str(customer.id),
                "name": customer.name,
                "phone": phone,
            }
        )

    if tasks_to_add:
        db.add_all(tasks_to_add)
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


def _retarget_batch_column():
    return MessageAutomationTask.payload["manual_batch_id"].astext


def _campaign_report_window(
    date_from: Optional[date],
    date_to: Optional[date],
) -> tuple[date, date, datetime, datetime]:
    report_timezone = ZoneInfo(CAMPAIGN_REPORT_TIMEZONE)
    today = datetime.now(report_timezone).date()
    selected_to = date_to or today
    selected_from = date_from or (selected_to - timedelta(days=6))
    if selected_from > selected_to:
        raise HTTPException(
            status_code=422,
            detail="Start date must be on or before end date",
        )
    if (selected_to - selected_from).days + 1 > MAX_CAMPAIGN_REPORT_DAYS:
        raise HTTPException(
            status_code=422,
            detail=f"Campaign report range cannot exceed {MAX_CAMPAIGN_REPORT_DAYS} days",
        )
    range_start = datetime.combine(
        selected_from,
        time.min,
        tzinfo=report_timezone,
    ).astimezone(timezone.utc)
    range_end = datetime.combine(
        selected_to + timedelta(days=1),
        time.min,
        tzinfo=report_timezone,
    ).astimezone(timezone.utc)
    return selected_from, selected_to, range_start, range_end


def list_retarget_campaigns(
    db: Session,
    current_user: Employee,
    *,
    page: int = 1,
    limit: int = 25,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> dict:
    """
    Discover WhatsApp Customer Retarget bulk-send batches.
    There is no dedicated campaign table for this feature — each bulk send from
    the "Send WhatsApp template" modal stamps a batch_id into
    message_automation_tasks.payload['manual_batch_id']; a "campaign" here is
    just that batch grouping.
    """
    batch_col = _retarget_batch_column()
    template_col = MessageAutomationTask.payload["manual_template_name"].astext
    language_col = MessageAutomationTask.payload["manual_language_code"].astext
    selected_from, selected_to, range_start, range_end = (
        _campaign_report_window(date_from, date_to)
    )

    task_filters = (
        MessageAutomationTask.tenant_id == current_user.tenant_id,
        MessageAutomationTask.template_key
        == message_automation_service.RETARGET_MANUAL_TEMPLATE_KEY,
        batch_col.isnot(None),
        MessageAutomationTask.created_at >= range_start,
        MessageAutomationTask.created_at < range_end,
    )
    base_query = (
        db.query(
            batch_col.label("batch_id"),
            func.min(template_col).label("template_name"),
            func.min(language_col).label("language_code"),
            func.min(MessageAutomationTask.created_at).label("sent_at"),
            func.count(MessageAutomationTask.id).label("recipient_count"),
            func.sum(case((MessageAutomationTask.status == "sent", 1), else_=0)).label("sent_count"),
            func.sum(case((MessageAutomationTask.status == "failed", 1), else_=0)).label("failed_count"),
            func.sum(case((MessageAutomationTask.status == "pending", 1), else_=0)).label("pending_count"),
        )
        .filter(*task_filters)
        .group_by(batch_col)
    )
    total = base_query.count()

    summary = (
        db.query(
            func.count(func.distinct(batch_col)).label("campaign_count"),
            func.count(MessageAutomationTask.id).label("recipient_count"),
            func.sum(
                case((MessageAutomationTask.status == "sent", 1), else_=0)
            ).label("sent_count"),
            func.sum(
                case((MessageAutomationTask.status == "failed", 1), else_=0)
            ).label("failed_count"),
            func.sum(
                case((MessageAutomationTask.status == "pending", 1), else_=0)
            ).label("pending_count"),
        )
        .filter(*task_filters)
        .first()
    )
    local_day = func.date(
        func.timezone(
            CAMPAIGN_REPORT_TIMEZONE,
            MessageAutomationTask.created_at,
        )
    )
    daily_rows = (
        db.query(
            local_day.label("result_date"),
            func.count(func.distinct(batch_col)).label("campaign_count"),
            func.count(MessageAutomationTask.id).label("recipient_count"),
            func.sum(
                case((MessageAutomationTask.status == "sent", 1), else_=0)
            ).label("sent_count"),
            func.sum(
                case((MessageAutomationTask.status == "failed", 1), else_=0)
            ).label("failed_count"),
            func.sum(
                case((MessageAutomationTask.status == "pending", 1), else_=0)
            ).label("pending_count"),
        )
        .filter(*task_filters)
        .group_by(local_day)
        .order_by(local_day.desc())
        .all()
    )

    page = max(1, page)
    limit = max(1, min(limit, 200))
    rows = (
        base_query.order_by(func.min(MessageAutomationTask.created_at).desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    daily_by_date = {row.result_date: row for row in daily_rows}
    daily_results = []
    result_date = selected_to
    while result_date >= selected_from:
        row = daily_by_date.get(result_date)
        recipient_count = int(row.recipient_count or 0) if row else 0
        sent_count = int(row.sent_count or 0) if row else 0
        daily_results.append(
            {
                "date": result_date.isoformat(),
                "campaign_count": int(row.campaign_count or 0) if row else 0,
                "recipient_count": recipient_count,
                "sent_count": sent_count,
                "failed_count": int(row.failed_count or 0) if row else 0,
                "pending_count": int(row.pending_count or 0) if row else 0,
                "success_rate": round(
                    (sent_count / (recipient_count or 1)) * 100,
                    1,
                ),
            }
        )
        result_date -= timedelta(days=1)
    return {
        "campaigns": [
            {
                "batch_id": row.batch_id,
                "template_name": row.template_name or "",
                "language_code": row.language_code or "en",
                "sent_at": row.sent_at,
                "recipient_count": row.recipient_count,
                "sent_count": row.sent_count or 0,
                "failed_count": row.failed_count or 0,
                "pending_count": row.pending_count or 0,
            }
            for row in rows
        ],
        "page": page,
        "limit": limit,
        "total": total,
        "filters": {
            "date_from": selected_from.isoformat(),
            "date_to": selected_to.isoformat(),
            "timezone": CAMPAIGN_REPORT_TIMEZONE,
        },
        "summary": {
            "campaign_count": int(summary.campaign_count or 0),
            "recipient_count": int(summary.recipient_count or 0),
            "sent_count": int(summary.sent_count or 0),
            "failed_count": int(summary.failed_count or 0),
            "pending_count": int(summary.pending_count or 0),
            "success_rate": round(
                (int(summary.sent_count or 0) / int(summary.recipient_count or 1))
                * 100,
                1,
            ),
        },
        "daily_results": daily_results,
    }


def list_retarget_messages(
    db: Session,
    current_user: Employee,
    *,
    page: int = 1,
    limit: int = 50,
    status: str = "all",
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> dict:
    selected_status = (status or "all").strip().lower()
    if selected_status not in CAMPAIGN_MESSAGE_STATUSES:
        raise HTTPException(status_code=422, detail="Unknown message status")

    selected_from, selected_to, range_start, range_end = (
        _campaign_report_window(date_from, date_to)
    )
    batch_col = _retarget_batch_column()
    filters = [
        MessageAutomationTask.tenant_id == current_user.tenant_id,
        MessageAutomationTask.template_key
        == message_automation_service.RETARGET_MANUAL_TEMPLATE_KEY,
        batch_col.isnot(None),
        MessageAutomationTask.created_at >= range_start,
        MessageAutomationTask.created_at < range_end,
    ]
    if selected_status != "all":
        filters.append(MessageAutomationTask.status == selected_status)

    query = db.query(MessageAutomationTask).filter(*filters)
    total = query.count()
    page = max(1, page)
    limit = max(1, min(limit, 200))
    tasks = (
        query.order_by(
            MessageAutomationTask.created_at.desc(),
            MessageAutomationTask.id.desc(),
        )
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    provider_ids = [
        task.provider_message_id
        for task in tasks
        if task.provider_message_id
    ]
    wa_by_provider_id = {}
    if provider_ids:
        wa_by_provider_id = {
            message.provider_message_id: message
            for message in db.query(WaMessage)
            .filter(
                WaMessage.tenant_id == current_user.tenant_id,
                WaMessage.provider_message_id.in_(provider_ids),
            )
            .all()
        }

    messages = []
    for task in tasks:
        payload = dict(task.payload or {})
        wa_message = wa_by_provider_id.get(task.provider_message_id)
        messages.append(
            {
                "id": str(task.id),
                "batch_id": str(payload.get("manual_batch_id") or ""),
                "customer_id": (
                    str(task.customer_id) if task.customer_id else None
                ),
                "customer_name": task.recipient_name or "",
                "phone": task.recipient_phone_e164 or "",
                "template_name": str(
                    payload.get("manual_template_name") or ""
                ),
                "language_code": str(
                    payload.get("manual_language_code") or "en"
                ),
                "task_status": task.status,
                "delivery_status": (
                    wa_message.status.value if wa_message else None
                ),
                "read_at": (
                    wa_message.read_at if wa_message else None
                ),
                "created_at": task.created_at,
                "scheduled_at": task.scheduled_at,
                "sent_at": task.sent_at,
                "attempts": task.attempts,
                "max_attempts": task.max_attempts,
                "provider_message_id": task.provider_message_id,
                "error_reason": task.error_reason,
                "body": task.body,
                "header_image_url": payload.get(
                    "manual_header_image_url"
                ),
                "customer_name_variable": payload.get("customer_name"),
                "website_url": payload.get("website_url"),
                "whatsapp_link": payload.get("whatsapp_link"),
            }
        )

    return {
        "messages": messages,
        "page": page,
        "limit": limit,
        "total": total,
        "status": selected_status,
        "filters": {
            "date_from": selected_from.isoformat(),
            "date_to": selected_to.isoformat(),
            "timezone": CAMPAIGN_REPORT_TIMEZONE,
        },
    }


def _phone_variants(value: Optional[str]) -> set[str]:
    digits = re.sub(r"\D", "", value or "")
    if not digits:
        return set()
    variants = {digits, f"+{digits}"}
    if len(digits) == 12 and digits.startswith("91"):
        variants.add(digits[2:])
    elif len(digits) == 10:
        variants.add(f"91{digits}")
        variants.add(f"+91{digits}")
    return variants


RETARGET_REPLY_ATTRIBUTION_DAYS = 7


def get_retarget_campaign_detail(
    db: Session,
    current_user: Employee,
    batch_id: str,
    *,
    page: int = 1,
    limit: int = 25,
) -> dict:
    """
    Real, backend-driven results for one Customer Retarget WhatsApp batch.

    Data honesty notes:
    - `status` / `error_reason` come straight from message_automation_tasks —
      this is the true send outcome from Meta's synchronous API response
      (e.g. a real Meta error like "#132012 Parameter format does not match").
    - `delivery_status` / `read` come from wa_messages, joined by the exact
      provider_message_id Meta returned at send time, and populated by the
      Meta statuses[] webhook handler. If that webhook hasn't reported a
      status yet for a message, these are None ("Not tracked"), not False —
      we never fabricate a delivery/read result.
    - `replied` is computed for real: an inbound WhatsApp message recorded
      for that customer's phone within RETARGET_REPLY_ATTRIBUTION_DAYS of
      their message actually being sent. Only tasks that were actually
      sent (status == 'sent') are eligible — a reply can't be attributed to
      a message that never reached the customer.
    """
    batch_col = _retarget_batch_column()
    base_filters = (
        MessageAutomationTask.tenant_id == current_user.tenant_id,
        MessageAutomationTask.template_key == message_automation_service.RETARGET_MANUAL_TEMPLATE_KEY,
        batch_col == batch_id,
    )

    summary_row = (
        db.query(
            func.min(MessageAutomationTask.payload["manual_template_name"].astext).label("template_name"),
            func.min(MessageAutomationTask.payload["manual_language_code"].astext).label("language_code"),
            func.min(MessageAutomationTask.created_at).label("sent_at"),
            func.count(MessageAutomationTask.id).label("total"),
        )
        .filter(*base_filters)
        .first()
    )
    if not summary_row or not summary_row.total:
        raise HTTPException(status_code=404, detail="Campaign batch not found")

    page = max(1, page)
    limit = max(1, min(limit, 200))
    tasks = (
        db.query(MessageAutomationTask)
        .filter(*base_filters)
        .order_by(MessageAutomationTask.created_at.asc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    # ---- delivery/read status, joined by the exact Meta message id ----
    provider_ids = [task.provider_message_id for task in tasks if task.provider_message_id]
    wa_by_provider_id: dict[str, WaMessage] = {}
    if provider_ids:
        wa_rows = (
            db.query(WaMessage)
            .filter(
                WaMessage.tenant_id == current_user.tenant_id,
                WaMessage.provider_message_id.in_(provider_ids),
            )
            .all()
        )
        wa_by_provider_id = {row.provider_message_id: row for row in wa_rows}

    # ---- reply detection: phone -> subscriber -> conversation -> inbound messages ----
    # Only tasks that actually sent are eligible for reply attribution.
    sent_tasks = [task for task in tasks if task.status == "sent"]
    all_variants: set[str] = set()
    for task in sent_tasks:
        all_variants |= _phone_variants(task.recipient_phone_e164)

    subscribers = (
        db.query(WaSubscriber)
        .filter(
            WaSubscriber.tenant_id == current_user.tenant_id,
            WaSubscriber.phone_number.in_(all_variants),
        )
        .all()
        if all_variants
        else []
    )
    subscriber_by_variant = {row.phone_number: row for row in subscribers}

    conversations = (
        db.query(WaConversation)
        .filter(
            WaConversation.tenant_id == current_user.tenant_id,
            WaConversation.subscriber_id.in_([row.id for row in subscribers]),
        )
        .all()
        if subscribers
        else []
    )
    conversation_by_subscriber_id = {row.subscriber_id: row for row in conversations}

    inbound_times_by_conversation: dict[UUID, list[datetime]] = {}
    if conversations:
        inbound_rows = (
            db.query(WaMessage.conversation_id, WaMessage.sent_at)
            .filter(
                WaMessage.tenant_id == current_user.tenant_id,
                WaMessage.conversation_id.in_([row.id for row in conversations]),
                WaMessage.direction == WaMessageDirection.inbound,
            )
            .all()
        )
        for conversation_id, sent_at in inbound_rows:
            inbound_times_by_conversation.setdefault(conversation_id, []).append(sent_at)

    recipients = []
    for task in tasks:
        wa_message = wa_by_provider_id.get(task.provider_message_id) if task.provider_message_id else None
        delivery_status = wa_message.status.value if wa_message else None
        is_read = bool(wa_message.read_at) if wa_message else None

        replied = False
        replied_at = None
        if task.status == "sent" and task.sent_at:
            subscriber = None
            for variant in _phone_variants(task.recipient_phone_e164):
                if variant in subscriber_by_variant:
                    subscriber = subscriber_by_variant[variant]
                    break
            if subscriber:
                conversation = conversation_by_subscriber_id.get(subscriber.id)
                if conversation:
                    window_end = task.sent_at + timedelta(days=RETARGET_REPLY_ATTRIBUTION_DAYS)
                    candidate_times = [
                        ts for ts in inbound_times_by_conversation.get(conversation.id, [])
                        if task.sent_at < ts <= window_end
                    ]
                    if candidate_times:
                        replied = True
                        replied_at = min(candidate_times)

        recipients.append(
            {
                "customer_id": str(task.customer_id) if task.customer_id else None,
                "name": task.recipient_name or "",
                "phone": task.recipient_phone_e164 or "",
                "status": task.status,
                "error_reason": task.error_reason,
                "sent_at": task.sent_at,
                "delivery_status": delivery_status,
                "read": is_read,
                "replied": replied,
                "replied_at": replied_at,
            }
        )

    return {
        "batch_id": batch_id,
        "template_name": summary_row.template_name or "",
        "language_code": summary_row.language_code or "en",
        "sent_at": summary_row.sent_at,
        "read_receipts_tracked": False,
        "reply_attribution_days": RETARGET_REPLY_ATTRIBUTION_DAYS,
        "recipients": recipients,
        "page": page,
        "limit": limit,
        "total_recipients": summary_row.total,
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
    test_customer_ids = {
        row[0]
        for row in _tagged_customer_ids_query(
            db,
            tenant_id,
            [TEST_CUSTOMER_TAG],
        )
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
                "is_test_customer": customer.id in test_customer_ids,
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
        .outerjoin(
            CustomerRetargetState,
            and_(
                CustomerRetargetState.tenant_id == tenant_id,
                CustomerRetargetState.customer_id == Customer.id,
            ),
        )
        .filter(
            Customer.tenant_id == tenant_id,
            exists().where(
                and_(
                    CustomerTagMap.tenant_id == tenant_id,
                    CustomerTagMap.customer_id == Customer.id,
                    CustomerTag.id == CustomerTagMap.tag_id,
                    CustomerTag.tenant_id == tenant_id,
                    func.lower(CustomerTag.name).in_(
                        [
                            OLD_CUSTOMERS_TAG.lower(),
                            MANUAL_RETARGET_TAG.lower(),
                        ]
                    ),
                )
            ),
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
    customer_ids = [customer.id for customer, _ in rows]
    old_customer_ids = {
        row[0]
        for row in _tagged_customer_ids_query(
            db,
            tenant_id,
            [OLD_CUSTOMERS_TAG],
        )
        .filter(CustomerTagMap.customer_id.in_(customer_ids))
        .all()
    } if customer_ids else set()
    test_customer_ids = {
        row[0]
        for row in _tagged_customer_ids_query(
            db,
            tenant_id,
            [TEST_CUSTOMER_TAG],
        )
        .filter(CustomerTagMap.customer_id.in_(customer_ids))
        .all()
    } if customer_ids else set()
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
                "latest_order_number": (
                    "Test contact"
                    if customer.id in test_customer_ids
                    else (
                        "Old WhatsApp contact"
                        if customer.id in old_customer_ids
                        else "Manually added contact"
                    )
                ),
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
                "is_old_customer": customer.id in old_customer_ids,
                "is_test_customer": customer.id in test_customer_ids,
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

    if repeat_only or view == "premium":
        query = query.filter(aggregate.c.order_count > 1)
    if view == "high_value":
        query = query.filter(aggregate.c.lifetime_value > Decimal("1500"))

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
        pending_customer_ids = [
            entry[0].id for entry in pending_ordered
        ] + [
            entry[0].id for entry in pending_old_without_orders
        ]
        test_customer_ids = {
            row[0]
            for row in _tagged_customer_ids_query(
                db,
                tenant_id,
                [TEST_CUSTOMER_TAG],
            )
            .filter(CustomerTagMap.customer_id.in_(pending_customer_ids))
            .all()
        } if pending_customer_ids else set()
        oldest = datetime.min.replace(tzinfo=timezone.utc)
        mixed = [
            (
                oldest,
                (
                    f"0-test:{row[0].id}"
                    if row[0].id in test_customer_ids
                    else f"1-old:{row[0].id}"
                ),
                "old",
                row,
            )
            for row in pending_old_without_orders
        ] + [
            (
                (
                    oldest
                    if row[0].id in tagged_ordered_ids
                    or row[0].id in test_customer_ids
                    else row[5]
                ),
                (
                    f"0-test:{row[0].id}"
                    if row[0].id in test_customer_ids
                    else (
                        f"1-old:{row[0].id}"
                        if row[0].id in tagged_ordered_ids
                        else f"2-customer:{row[0].id}"
                    )
                ),
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
    elif view == "not_interested":
        query = query.filter(
            CustomerRetargetState.current_outcome
            == RetargetOutcome.not_interested
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


def get_queue_selection(
    db: Session,
    current_user: Employee,
    *,
    view: str,
    search: Optional[str],
    repeat_only: bool,
) -> dict:
    """
    Return selectable customer IDs for the complete active queue audience.

    This deliberately reuses get_queue so bulk targeting follows exactly the
    same tenant, outcome, search, repeat-buyer, old-customer, and value rules
    as the visible table. Unlinked buyers and customers without a phone remain
    visible in coverage but are not selectable for WhatsApp.
    """
    queue = get_queue(
        db,
        current_user,
        view=view,
        search=search,
        repeat_only=repeat_only,
        page=1,
        limit=MAX_RETARGET_BULK_RECIPIENTS,
    )
    customer_ids: list[str] = []
    seen: set[str] = set()
    for row in queue["data"]:
        customer_id = str(row.get("customer_id") or "")
        if (
            row.get("kind") == "customer"
            and customer_id
            and row.get("phone")
            and customer_id not in seen
        ):
            seen.add(customer_id)
            customer_ids.append(customer_id)

    return {
        "customer_ids": customer_ids,
        "selectable_total": len(customer_ids),
        "matching_total": queue["total"],
        "selection_limit": MAX_RETARGET_BULK_RECIPIENTS,
        "truncated": queue["total"] > MAX_RETARGET_BULK_RECIPIENTS,
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
    is_manual_retarget_customer = _is_manual_retarget_customer(
        db,
        current_user.tenant_id,
        customer.id,
    )
    is_test_customer = _is_test_customer(
        db,
        current_user.tenant_id,
        customer.id,
    )
    if not has_order and not is_old_customer and not is_manual_retarget_customer:
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
            "is_test_customer": is_test_customer,
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
    is_manual_retarget_customer = _is_manual_retarget_customer(
        db,
        current_user.tenant_id,
        customer.id,
    )
    if not has_order and not is_old_customer and not is_manual_retarget_customer:
        raise HTTPException(
            status_code=400,
            detail="Only ordered or manually queued customers can be retargeted",
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
