from __future__ import annotations

import json
import logging
import os
import re
import smtplib
import uuid
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from types import SimpleNamespace
from typing import Any, Optional
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from app.models.customer import Customer
from app.models.message_automation import (
    CustomerMessagePreference,
    MessageAutomationSetting,
    MessageAutomationTask,
)
from app.models.order import Order, OrderStatus
from app.models.shipping_config import ShopifyStore
from app.models.tenant import Tenant
from app.models.wa_engine import (
    WaConversation,
    WaMessage,
    WaMessageDirection,
    WaMessageStatus,
    WaMessageType,
    WaSubscriber,
)
from app.modules.message_automation.templates import TEMPLATES, template_catalog

log = logging.getLogger(__name__)

UTC = timezone.utc
INDIA_TZ = ZoneInfo("Asia/Kolkata")
PENDING = "pending"
SENT = "sent"
FAILED = "failed"
CANCELLED = "cancelled"
SKIPPED = "skipped"
RETARGET_MANUAL_TEMPLATE_KEY = "customer_retarget_manual"
TERMINAL_ORDER_STATUSES = {OrderStatus.delivered, OrderStatus.returned, OrderStatus.cancelled}
DEFAULT_ADMIN_PHONE = "+919447744583"
WABIS_TEMPLATE_CACHE_TTL = timedelta(minutes=10)
TEMPLATE_BINDING_KEYS = (
    "order_created",
    "tracking_added",
    "tracking_followup_3_day",
    "review_request",
    "monthly_promo_whatsapp",
)

_WABIS_TEMPLATE_CACHE: dict[str, dict[str, Any]] = {}

WHATSAPP_TEMPLATE_REQUIRED_KEYS = {
    *TEMPLATE_BINDING_KEYS,
    RETARGET_MANUAL_TEMPLATE_KEY,
}

ORDER_WHATSAPP_JOURNEY_KEYS = (
    "order_created",
    "tracking_added",
    "tracking_followup_3_day",
    "review_request",
)

ORDER_WHATSAPP_JOURNEY_LABELS = {
    "order_created": "Order Created",
    "tracking_added": "Tracking Added",
    "tracking_followup_3_day": "Follow-Up",
    "review_request": "Review Request",
}

WHATSAPP_TEMPLATE_FALLBACKS: dict[str, list[str]] = {
    "order_created": [
        "system_order_success_notification_new",
        "pl_shopify_order_create",
        "order_management_1",
        "pureleven_order_created",
    ],
    "tracking_added": ["shopify_order_shipped"],
    "tracking_followup_3_day": ["pureleven_tracking_update"],
    "review_request": [],
    "monthly_promo_whatsapp": [],
}

WHATSAPP_TEMPLATE_SPECS: dict[str, dict[str, Any]] = {
    "pureleven_order_created": {
        "parameter_format": "named",
        "body": {
            "customer_name": "customer_name",
            "order_number": "order_number",
            "items_summary": "items_summary",
            "total_amount": "total_amount",
            "website_url": "website_url",
        },
    },
    "pureleven_prod_order": {
        "parameter_format": "positional",
        "body": ["customer_name"],
    },
    "pl_shopify_order_create": {
        "parameter_format": "named",
        "body": {
            "customer_name": "customer_name",
            "order_number": "order_number",
            "items_summary": "items_summary",
            "total_amount": "total_amount",
            "website_url": "website_url",
        },
    },
    "system_order_success_notification_new": {
        "parameter_format": "named",
        "body": {
            "customer_name": "customer_name",
            "order_number": "order_number",
            "items_summary": "items_summary",
            "total_amount": "total_amount",
            "website_url": "website_url",
        },
    },
    "order_management_1": {
        "parameter_format": "positional",
        "body": [
            "customer_name",
            "order_number",
            "total_amount",
        ],
        "buttons": {
            0: ["button_url_suffix"],
        },
    },
    "pureleven_tracking_update": {
        "parameter_format": "positional",
        "body": [
            "customer_name",
            "courier_name",
            "tracking_number",
        ],
    },
    "shopify_order_shipped": {
        "parameter_format": "named",
        "body": {
            "customer_name": "customer_name",
            "courier_name": "courier_name",
            "tracking_number": "tracking_number",
        },
    },
    "pureleven_tracking_followup_3_day": {
        "parameter_format": "named",
        "body": {
            "customer_name": "customer_name",
            "status_text": "status_text",
            "location": "location",
            "expected_delivery": "expected_delivery",
            "tracking_number": "tracking_number",
        },
    },
    "pureleven_review_request": {
        "parameter_format": "named",
        "body": {
            "customer_name": "customer_name",
            "google_review_url": "google_review_url",
            "website_url": "website_url",
            "whatsapp_link": "whatsapp_link",
        },
    },
    "pureleven_monthly_reorder": {
        "parameter_format": "named",
        "body": {
            "customer_name": "customer_name",
            "website_url": "website_url",
            "whatsapp_link": "whatsapp_link",
        },
    },
}


def _default_template_bindings() -> dict[str, str]:
    bindings: dict[str, str] = {}
    for key in TEMPLATE_BINDING_KEYS:
        template = TEMPLATES.get(key)
        fallback_names = WHATSAPP_TEMPLATE_FALLBACKS.get(key) or []
        default_name = getattr(template, "meta_template_name", None) or (fallback_names[0] if fallback_names else "")
        bindings[key] = str(default_name or "")
    return bindings


def _normalize_template_bindings(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}

    defaults = _default_template_bindings()
    bindings: dict[str, str] = {}
    for key in TEMPLATE_BINDING_KEYS:
        if key not in value:
            continue
        template_name = str(value.get(key) or "").strip()
        bindings[key] = template_name or defaults.get(key, "")
    return bindings


def resolved_template_bindings(settings_row: MessageAutomationSetting | None) -> dict[str, str]:
    bindings = _default_template_bindings()
    if settings_row is None:
        return bindings
    bindings.update(_normalize_template_bindings(getattr(settings_row, "template_bindings", None)))
    return bindings


def _default_template_header_media_urls() -> dict[str, str | None]:
    return {key: None for key in TEMPLATE_BINDING_KEYS}


def _normalize_template_header_media_urls(value: Any) -> dict[str, str | None]:
    if not isinstance(value, dict):
        return {}

    header_media_urls: dict[str, str | None] = {}
    for key in TEMPLATE_BINDING_KEYS:
        if key not in value:
            continue
        media_url = str(value.get(key) or "").strip()
        header_media_urls[key] = media_url or None
    return header_media_urls

def resolved_template_header_media_urls(settings_row: MessageAutomationSetting | None) -> dict[str, str | None]:
    bindings = _default_template_header_media_urls()
    if settings_row is None:
        return bindings
    bindings.update(
        _normalize_template_header_media_urls(getattr(settings_row, "template_header_media_urls", None))
    )
    return bindings


def _configured_template_name(settings_row: Any, template_key: str) -> str | None:
    return resolved_template_bindings(settings_row).get(template_key)


def _normalize_meta_template_asset_id(value: Optional[str]) -> str | None:
    digits = re.sub(r"\D", "", str(value or ""))
    return digits or None


def _runtime_template_settings(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    automation_settings_row: MessageAutomationSetting | None = None,
    wa_settings_row: Any | None = None,
) -> Any:
    if automation_settings_row is None:
        automation_settings_row = get_or_create_settings(db, tenant_id)
    if wa_settings_row is None:
        from app.modules.wa_engine.service import get_or_create_settings as get_wa_settings

        wa_settings_row = get_wa_settings(db, tenant_id)

    return SimpleNamespace(
        tenant_id=tenant_id,
        template_bindings=resolved_template_bindings(automation_settings_row),
        template_header_media_urls=resolved_template_header_media_urls(automation_settings_row),
        meta_template_asset_id=_normalize_meta_template_asset_id(
            getattr(automation_settings_row, "meta_template_asset_id", None)
        ),
        wabis_api_token=getattr(wa_settings_row, "wabis_api_token", None),
        wabis_phone_number_id=getattr(wa_settings_row, "wabis_phone_number_id", None),
        meta_access_token=getattr(wa_settings_row, "meta_access_token", None),
        meta_api_version=getattr(wa_settings_row, "meta_api_version", None),
    )


# ---------------------------------------------------------------------------
# Public template/settings helpers
# ---------------------------------------------------------------------------

def templates_for_meta_manager() -> list[dict]:
    return template_catalog()


def _template_text_example(parameter_name: str) -> str:
    examples = {
        "customer_name": "Basil",
        "order_number": "PRN-260523-325",
        "items_summary": "Premium cardamom 250g",
        "total_amount": "799.00",
        "website_url": "https://purelevenexim.com",
        "courier_name": "India Post",
        "tracking_number": "TESTTRACK123",
        "status_text": "In transit",
        "location": "Kochi Hub",
        "expected_delivery": "26 May 2026",
        "google_review_url": "https://www.google.com/search?q=Pureleven+Exim+Google+review",
        "whatsapp_link": "https://wa.me/919447744583",
    }
    return examples.get(parameter_name, parameter_name.replace("_", " ").title())


def _body_component_payload(parameter_spec: Any, parameter_format: str, body_text: str) -> dict[str, Any]:
    if parameter_format == "named" and isinstance(parameter_spec, dict):
        example_values = [
            {
                "param_name": param_name,
                "example": _template_text_example(variable_name),
            }
            for param_name, variable_name in parameter_spec.items()
        ]
        return {
            "type": "BODY",
            "text": body_text,
            "example": {"body_text_named_params": example_values},
        }

    ordered_fields = list(parameter_spec.values()) if isinstance(parameter_spec, dict) else list(parameter_spec)
    return {
        "type": "BODY",
        "text": body_text,
        "example": {"body_text": [[_template_text_example(field_name) for field_name in ordered_fields]]},
    }


def meta_template_payloads() -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for template_key, template in TEMPLATES.items():
        if template.channel != "whatsapp" or not template.meta_template_name:
            continue

        spec = WHATSAPP_TEMPLATE_SPECS.get(template.meta_template_name)
        if not spec:
            continue

        parameter_format = str(spec.get("parameter_format") or "positional").upper()
        components: list[dict[str, Any]] = [
            _body_component_payload(spec.get("body") or [], parameter_format.lower(), template.body)
        ]

        payloads.append(
            {
                "template_key": template_key,
                "template_name": template.meta_template_name,
                "category": (template.meta_category or template.category or "UTILITY").upper(),
                "language": template.language,
                "parameter_format": parameter_format,
                "components": components,
                "sample_variables": {
                    key: _template_text_example(key)
                    for key in (
                        list((spec.get("body") or {}).values())
                        if isinstance(spec.get("body"), dict)
                        else list(spec.get("body") or [])
                    )
                },
            }
        )

    return payloads


def now_utc() -> datetime:
    return datetime.now(UTC)


def get_or_create_settings(db: Session, tenant_id: uuid.UUID) -> MessageAutomationSetting:
    settings_row = (
        db.query(MessageAutomationSetting)
        .filter(MessageAutomationSetting.tenant_id == tenant_id)
        .first()
    )
    if settings_row is None:
        links = _derive_links(db, tenant_id, None)
        settings_row = MessageAutomationSetting(
            tenant_id=tenant_id,
            website_url=links["website_url"],
            google_review_url=links["google_review_url"],
            business_whatsapp_phone=links["business_whatsapp_phone"],
            template_bindings=_default_template_bindings(),
            template_header_media_urls=_default_template_header_media_urls(),
            is_enabled=True,
        )
        db.add(settings_row)
        db.flush()
    return settings_row


def update_settings(db: Session, tenant_id: uuid.UUID, data: dict[str, Any]) -> MessageAutomationSetting:
    settings_row = get_or_create_settings(db, tenant_id)
    for field_name in ("is_enabled", "website_url", "google_review_url", "business_whatsapp_phone"):
        if field_name in data:
            setattr(settings_row, field_name, data[field_name])
    if "meta_template_asset_id" in data:
        settings_row.meta_template_asset_id = _normalize_meta_template_asset_id(data.get("meta_template_asset_id"))
    if "template_bindings" in data:
        merged_bindings = resolved_template_bindings(settings_row)
        merged_bindings.update(_normalize_template_bindings(data.get("template_bindings")))
        settings_row.template_bindings = merged_bindings
    if "template_header_media_urls" in data:
        merged_header_media_urls = resolved_template_header_media_urls(settings_row)
        merged_header_media_urls.update(
            _normalize_template_header_media_urls(data.get("template_header_media_urls"))
        )
        settings_row.template_header_media_urls = merged_header_media_urls
    settings_row.updated_at = now_utc()
    db.flush()
    return settings_row


# ---------------------------------------------------------------------------
# Phone, links, rendering
# ---------------------------------------------------------------------------

def phone_digits(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"\D", "", str(value))


def normalize_phone_e164(value: Optional[str]) -> str:
    digits = phone_digits(value)
    if not digits:
        return ""
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) == 10:
        digits = f"91{digits}"
    elif len(digits) == 11 and digits.startswith("0"):
        digits = f"91{digits[1:]}"
    elif len(digits) == 12 and digits.startswith("91"):
        pass
    return f"+{digits}"


def whatsapp_send_phone(value: str) -> str:
    return normalize_phone_e164(value).lstrip("+")


def _language_matches(requested: str | None, actual: str | None) -> bool:
    requested_code = str(requested or "").strip().lower().replace("-", "_")
    actual_code = str(actual or "").strip().lower().replace("-", "_")
    if not requested_code:
        return True
    if requested_code == actual_code:
        return True
    return requested_code.split("_", 1)[0] == actual_code.split("_", 1)[0]


def _normalize_url(value: Optional[str]) -> str:
    if not value:
        return ""
    clean = str(value).strip()
    if not clean:
        return ""
    if clean.startswith("http://") or clean.startswith("https://"):
        return clean.rstrip("/")
    return f"https://{clean.rstrip('/')}"


def _derive_links(db: Session, tenant_id: uuid.UUID, settings_row: Optional[MessageAutomationSetting]) -> dict[str, str]:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

    website_url = _normalize_url(settings_row.website_url if settings_row else None)
    if not website_url:
        website_url = _normalize_url(os.getenv("PUBLIC_WEBSITE_URL") or os.getenv("WEBSITE_URL"))
    if not website_url:
        primary_store = (
            db.query(ShopifyStore)
            .filter(ShopifyStore.tenant_id == tenant_id, ShopifyStore.is_active.is_(True))
            .order_by(ShopifyStore.is_primary.desc(), ShopifyStore.created_at.asc())
            .first()
        )
        if primary_store:
            website_url = _normalize_url(primary_store.store_url)
    if not website_url:
        website_url = "https://purelevenexim.com"

    google_review_url = _normalize_url(settings_row.google_review_url if settings_row else None)
    if not google_review_url:
        google_review_url = _normalize_url(os.getenv("GOOGLE_REVIEW_URL") or os.getenv("GOOGLE_BUSINESS_REVIEW_URL"))
    if not google_review_url:
        google_review_url = "https://www.google.com/search?q=Pureleven+Exim+Google+review"

    whatsapp_phone = normalize_phone_e164(settings_row.business_whatsapp_phone if settings_row else None)
    if not whatsapp_phone and tenant:
        whatsapp_phone = normalize_phone_e164(tenant.phone or tenant.contact_phone)
    if not whatsapp_phone:
        whatsapp_phone = DEFAULT_ADMIN_PHONE

    return {
        "website_url": website_url,
        "google_review_url": google_review_url,
        "business_whatsapp_phone": whatsapp_phone,
        "whatsapp_link": f"https://wa.me/{whatsapp_phone.lstrip('+')}",
    }


def tenant_links(db: Session, tenant_id: uuid.UUID) -> dict[str, str]:
    settings_row = get_or_create_settings(db, tenant_id)
    return _derive_links(db, tenant_id, settings_row)


def _render_text(template_text: str, variables: dict[str, Any]) -> str:
    rendered = template_text
    for key, value in variables.items():
        rendered = rendered.replace("{{" + key + "}}", str(value or ""))
    return rendered


def _format_money(value: Any) -> str:
    if value is None:
        return "0"
    try:
        return f"{float(value):,.2f}"
    except Exception:
        return str(value)


def _format_date(value: Any) -> str:
    if not value:
        return "Not published by courier yet"
    if isinstance(value, datetime):
        return value.strftime("%d %b %Y")
    if isinstance(value, date):
        return value.strftime("%d %b %Y")
    return str(value)


def _items_summary(order: Order) -> str:
    items = list(order.items or [])
    if not items:
        return "your selected products"
    parts = []
    for item in items[:4]:
        quantity = str(item.quantity).rstrip("0").rstrip(".") if item.quantity is not None else "1"
        parts.append(f"{item.product_name} x{quantity}")
    if len(items) > 4:
        parts.append(f"+{len(items) - 4} more")
    return ", ".join(parts)


def _delivery_address(order: Order) -> str:
    parts = [
        order.delivery_address,
        order.delivery_city,
        order.delivery_state,
        order.delivery_pincode,
    ]
    clean_parts = [str(part).strip() for part in parts if part and str(part).strip()]
    return ", ".join(clean_parts) or "Delivery address shared with the order"


def _customer_name(customer: Optional[Customer], fallback: str = "Customer") -> str:
    name = (customer.name if customer else None) or fallback or "Customer"
    clean_name = re.sub(r"\s+", " ", str(name).replace("\r", " ").replace("\n", " ")).strip()
    return clean_name or "Customer"


def _order_phone(order: Order) -> str:
    if order.customer and order.customer.phone:
        return normalize_phone_e164(order.customer.phone)
    return normalize_phone_e164(order.delivery_phone2)


def _status_text(order: Order) -> str:
    if order.tracking_status_text:
        return order.tracking_status_text
    status_value = order.status.value if hasattr(order.status, "value") else str(order.status or "")
    return status_value.replace("_", " ").title() if status_value else "Tracking created"


def _location_text(order: Order) -> str:
    return order.tracking_last_location or "Not updated by courier yet"


def _order_variables(db: Session, order: Order) -> dict[str, Any]:
    links = tenant_links(db, order.tenant_id)
    customer = order.customer
    variables = {
        "customer_name": _customer_name(customer, order.delivery_name or "Customer"),
        "order_number": order.order_number or "",
        "order_id": str(order.id),
        "order_lookup_key": order.order_number or str(order.id),
        "order_address": _delivery_address(order),
        "items_summary": _items_summary(order),
        "total_amount": _format_money(order.total_amount),
        "tracking_number": order.tracking_number or "",
        "courier_name": order.courier_name or "Courier",
        "status_text": _status_text(order),
        "location": _location_text(order),
        "expected_delivery": _format_date(order.expected_delivery),
        "last_event_at": _format_date(order.tracking_last_event_at),
        **links,
    }
    return variables


def _render_template(template_key: str, variables: dict[str, Any]) -> tuple[str | None, str]:
    template = TEMPLATES[template_key]
    subject = _render_text(template.subject, variables) if template.subject else None
    body = _render_text(template.body, variables)
    return subject, body


# ---------------------------------------------------------------------------
# Preferences / opt-out
# ---------------------------------------------------------------------------

def get_or_create_preference(
    db: Session,
    tenant_id: uuid.UUID,
    phone_e164: str,
    customer_id: uuid.UUID | None = None,
) -> CustomerMessagePreference:
    normalized_phone = normalize_phone_e164(phone_e164)
    preference = (
        db.query(CustomerMessagePreference)
        .filter(CustomerMessagePreference.tenant_id == tenant_id, CustomerMessagePreference.phone_e164 == normalized_phone)
        .first()
    )
    if preference is None:
        preference = CustomerMessagePreference(
            tenant_id=tenant_id,
            customer_id=customer_id,
            phone_e164=normalized_phone,
        )
        db.add(preference)
        db.flush()
    elif customer_id and not preference.customer_id:
        preference.customer_id = customer_id
    return preference


def preference_blocks(
    db: Session,
    tenant_id: uuid.UUID,
    phone_e164: str | None,
    channel: str,
) -> bool:
    normalized_phone = normalize_phone_e164(phone_e164)
    if not normalized_phone:
        return False
    preference = (
        db.query(CustomerMessagePreference)
        .filter(CustomerMessagePreference.tenant_id == tenant_id, CustomerMessagePreference.phone_e164 == normalized_phone)
        .first()
    )
    if preference is None:
        return False
    if preference.automation_paused:
        return True
    if channel == "whatsapp" and preference.whatsapp_opted_out:
        return True
    if channel == "email" and preference.email_opted_out:
        return True
    return False


def cancel_customer_messages(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    customer_id: uuid.UUID | None = None,
    phone: str | None = None,
    whatsapp: bool = True,
    email: bool = True,
    reason: str | None = None,
) -> dict[str, Any]:
    customer = None
    if customer_id:
        customer = (
            db.query(Customer)
            .filter(Customer.id == customer_id, Customer.tenant_id == tenant_id)
            .first()
        )
    normalized_phone = normalize_phone_e164(phone or (customer.phone if customer else None))
    if not normalized_phone:
        raise ValueError("A customer with phone or a phone number is required")

    preference = get_or_create_preference(db, tenant_id, normalized_phone, customer.id if customer else None)
    preference.automation_paused = True
    preference.whatsapp_opted_out = bool(whatsapp)
    preference.email_opted_out = bool(email)
    preference.pause_reason = reason or "Customer requested no automated messages"
    preference.paused_at = now_utc()
    preference.updated_at = now_utc()

    subscriber = (
        db.query(WaSubscriber)
        .filter(
            WaSubscriber.tenant_id == tenant_id,
            WaSubscriber.phone_number.in_({normalized_phone, normalized_phone.lstrip("+")}),
        )
        .first()
    )
    if subscriber:
        subscriber.is_opted_out = True

    task_query = db.query(MessageAutomationTask).filter(
        MessageAutomationTask.tenant_id == tenant_id,
        MessageAutomationTask.status == PENDING,
    )
    if customer:
        task_query = task_query.filter(
            or_(
                MessageAutomationTask.customer_id == customer.id,
                MessageAutomationTask.recipient_phone_e164 == normalized_phone,
            )
        )
    else:
        task_query = task_query.filter(MessageAutomationTask.recipient_phone_e164 == normalized_phone)

    cancelled_count = 0
    for task in task_query.all():
        task.status = CANCELLED
        task.cancelled_at = now_utc()
        task.error_reason = preference.pause_reason
        cancelled_count += 1

    db.flush()
    return {"success": True, "phone_e164": normalized_phone, "cancelled_tasks": cancelled_count}


def resume_customer_messages(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    customer_id: uuid.UUID | None = None,
    phone: str | None = None,
) -> dict[str, Any]:
    customer = None
    if customer_id:
        customer = (
            db.query(Customer)
            .filter(Customer.id == customer_id, Customer.tenant_id == tenant_id)
            .first()
        )
    normalized_phone = normalize_phone_e164(phone or (customer.phone if customer else None))
    if not normalized_phone:
        raise ValueError("A customer with phone or a phone number is required")

    preference = get_or_create_preference(db, tenant_id, normalized_phone, customer.id if customer else None)
    preference.automation_paused = False
    preference.whatsapp_opted_out = False
    preference.email_opted_out = False
    preference.pause_reason = None
    preference.paused_at = None
    preference.updated_at = now_utc()

    subscriber = (
        db.query(WaSubscriber)
        .filter(
            WaSubscriber.tenant_id == tenant_id,
            WaSubscriber.phone_number.in_({normalized_phone, normalized_phone.lstrip("+")}),
        )
        .first()
    )
    if subscriber:
        subscriber.is_opted_out = False
    db.flush()
    return {"success": True, "phone_e164": normalized_phone}


# ---------------------------------------------------------------------------
# Queue creation
# ---------------------------------------------------------------------------

def _queue_task(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    channel: str,
    template_key: str,
    event_type: str,
    dedupe_key: str,
    scheduled_at: datetime,
    body: str,
    subject: str | None = None,
    customer_id: uuid.UUID | None = None,
    order_id: uuid.UUID | None = None,
    recipient_phone_e164: str | None = None,
    recipient_email: str | None = None,
    recipient_name: str | None = None,
    payload: dict[str, Any] | None = None,
) -> MessageAutomationTask | None:
    settings_row = get_or_create_settings(db, tenant_id)
    if not settings_row.is_enabled:
        return None

    normalized_phone = normalize_phone_e164(recipient_phone_e164)
    if channel == "whatsapp" and not normalized_phone:
        return None
    if channel == "email" and not recipient_email and not normalized_phone:
        return None
    if preference_blocks(db, tenant_id, normalized_phone, channel):
        return None

    existing = (
        db.query(MessageAutomationTask)
        .filter(MessageAutomationTask.tenant_id == tenant_id, MessageAutomationTask.dedupe_key == dedupe_key)
        .first()
    )
    if existing:
        if existing.status in (PENDING, FAILED):
            existing.status = PENDING
            existing.scheduled_at = scheduled_at
            existing.next_retry_at = None
            existing.body = body
            existing.subject = subject
            existing.payload = payload or {}
            existing.updated_at = now_utc()
        return existing

    task = MessageAutomationTask(
        tenant_id=tenant_id,
        customer_id=customer_id,
        order_id=order_id,
        channel=channel,
        template_key=template_key,
        event_type=event_type,
        status=PENDING,
        recipient_phone_e164=normalized_phone or None,
        recipient_email=recipient_email,
        recipient_name=recipient_name,
        subject=subject,
        body=body,
        payload=payload or {},
        dedupe_key=dedupe_key,
        scheduled_at=scheduled_at,
    )
    db.add(task)
    db.flush()
    return task


def _load_order(db: Session, order: Order | uuid.UUID) -> Order | None:
    if isinstance(order, Order):
        order_id = order.id
    else:
        order_id = order
    return (
        db.query(Order)
        .options(joinedload(Order.customer), joinedload(Order.items))
        .filter(Order.id == order_id)
        .first()
    )


def schedule_order_created(db: Session, order: Order | uuid.UUID, due_at: datetime | None = None) -> MessageAutomationTask | None:
    order_row = _load_order(db, order)
    if not order_row or order_row.status in TERMINAL_ORDER_STATUSES:
        return None
    phone = _order_phone(order_row)
    variables = _order_variables(db, order_row)
    subject, body = _render_template("order_created", variables)
    return _queue_task(
        db,
        tenant_id=order_row.tenant_id,
        channel="whatsapp",
        template_key="order_created",
        event_type="order_created",
        dedupe_key=f"order:{order_row.id}:order_created",
        scheduled_at=due_at or now_utc(),
        subject=subject,
        body=body,
        customer_id=order_row.customer_id,
        order_id=order_row.id,
        recipient_phone_e164=phone,
        recipient_name=variables["customer_name"],
        payload=variables,
    )


def schedule_tracking_added(db: Session, order: Order | uuid.UUID, due_at: datetime | None = None) -> MessageAutomationTask | None:
    order_row = _load_order(db, order)
    if not order_row or not order_row.tracking_number or order_row.status in TERMINAL_ORDER_STATUSES:
        return None
    phone = _order_phone(order_row)
    variables = _order_variables(db, order_row)
    subject, body = _render_template("tracking_added", variables)
    task = _queue_task(
        db,
        tenant_id=order_row.tenant_id,
        channel="whatsapp",
        template_key="tracking_added",
        event_type="tracking_added",
        dedupe_key=f"order:{order_row.id}:tracking_added:{order_row.tracking_number}",
        scheduled_at=due_at or now_utc(),
        subject=subject,
        body=body,
        customer_id=order_row.customer_id,
        order_id=order_row.id,
        recipient_phone_e164=phone,
        recipient_name=variables["customer_name"],
        payload=variables,
    )
    schedule_tracking_followup(db, order_row, due_at=(due_at or now_utc()) + timedelta(days=3))
    return task


def schedule_tracking_followup(db: Session, order: Order | uuid.UUID, due_at: datetime | None = None) -> MessageAutomationTask | None:
    order_row = _load_order(db, order)
    if not order_row or not order_row.tracking_number or order_row.status in TERMINAL_ORDER_STATUSES:
        return None
    scheduled_at = due_at or (now_utc() + timedelta(days=3))
    phone = _order_phone(order_row)
    variables = _order_variables(db, order_row)
    subject, body = _render_template("tracking_followup_3_day", variables)
    return _queue_task(
        db,
        tenant_id=order_row.tenant_id,
        channel="whatsapp",
        template_key="tracking_followup_3_day",
        event_type="tracking_followup_3_day",
        dedupe_key=f"order:{order_row.id}:tracking_followup:{scheduled_at.date().isoformat()}",
        scheduled_at=scheduled_at,
        subject=subject,
        body=body,
        customer_id=order_row.customer_id,
        order_id=order_row.id,
        recipient_phone_e164=phone,
        recipient_name=variables["customer_name"],
        payload=variables,
    )


def cancel_tracking_followups_for_order(db: Session, order: Order | uuid.UUID, reason: str) -> int:
    order_id = order.id if isinstance(order, Order) else order
    cancelled_count = 0
    tasks = (
        db.query(MessageAutomationTask)
        .filter(
            MessageAutomationTask.order_id == order_id,
            MessageAutomationTask.status == PENDING,
            MessageAutomationTask.template_key == "tracking_followup_3_day",
        )
        .all()
    )
    for task in tasks:
        task.status = CANCELLED
        task.cancelled_at = now_utc()
        task.error_reason = reason
        cancelled_count += 1
    db.flush()
    return cancelled_count


def schedule_review_request(
    db: Session,
    *,
    tenant_id: uuid.UUID | None = None,
    customer: Customer | None = None,
    order: Order | None = None,
    phone: str | None = None,
    name: str | None = None,
    due_at: datetime | None = None,
    dedupe_suffix: str = "initial",
) -> MessageAutomationTask | None:
    if order and not customer:
        customer = order.customer
    resolved_tenant_id = tenant_id or (customer.tenant_id if customer else order.tenant_id if order else None)
    if resolved_tenant_id is None:
        return None
    phone_source = phone or (customer.phone if customer else None) or (_order_phone(order) if order else None)
    normalized_phone = normalize_phone_e164(phone_source)
    customer_name = _customer_name(customer, name or "Customer")
    links = tenant_links(db, resolved_tenant_id)
    variables = {"customer_name": customer_name, **links}
    if order:
        variables.update(_order_variables(db, order))
    subject, body = _render_template("review_request", variables)
    dedupe_base = f"order:{order.id}" if order else f"customer:{customer.id}" if customer else f"phone:{normalized_phone}"
    return _queue_task(
        db,
        tenant_id=resolved_tenant_id,
        channel="whatsapp",
        template_key="review_request",
        event_type="review_request",
        dedupe_key=f"{dedupe_base}:review_request:{dedupe_suffix}",
        scheduled_at=due_at or now_utc(),
        subject=subject,
        body=body,
        customer_id=customer.id if customer else None,
        order_id=order.id if order else None,
        recipient_phone_e164=normalized_phone,
        recipient_name=customer_name,
        payload=variables,
    )


def schedule_monthly_promo(
    db: Session,
    *,
    customer: Customer | None = None,
    tenant_id: uuid.UUID | None = None,
    phone: str | None = None,
    email: str | None = None,
    name: str | None = None,
    due_at: datetime | None = None,
) -> MessageAutomationTask | None:
    resolved_tenant_id = tenant_id or (customer.tenant_id if customer else None)
    if resolved_tenant_id is None:
        return None
    customer_name = _customer_name(customer, name or "Customer")
    normalized_phone = normalize_phone_e164(phone or (customer.phone if customer else None))
    recipient_email = email or (customer.email if customer else None)
    scheduled_at = due_at or (now_utc() + timedelta(days=30))
    links = tenant_links(db, resolved_tenant_id)
    variables = {"customer_name": customer_name, **links}

    template_key = "monthly_promo_email" if recipient_email else "monthly_promo_whatsapp"
    channel = "email" if recipient_email else "whatsapp"
    subject, body = _render_template(template_key, variables)
    dedupe_base = f"customer:{customer.id}" if customer else f"phone:{normalized_phone or recipient_email}"
    return _queue_task(
        db,
        tenant_id=resolved_tenant_id,
        channel=channel,
        template_key=template_key,
        event_type="monthly_promo",
        dedupe_key=f"{dedupe_base}:monthly_promo:{scheduled_at.date().isoformat()}",
        scheduled_at=scheduled_at,
        subject=subject,
        body=body,
        customer_id=customer.id if customer else None,
        recipient_phone_e164=normalized_phone,
        recipient_email=recipient_email,
        recipient_name=customer_name,
        payload=variables,
    )


def schedule_monthly_promo_whatsapp(
    db: Session,
    *,
    customer: Customer | None = None,
    tenant_id: uuid.UUID | None = None,
    phone: str | None = None,
    name: str | None = None,
    due_at: datetime | None = None,
    dedupe_suffix: str = "manual_backfill",
) -> MessageAutomationTask | None:
    resolved_tenant_id = tenant_id or (customer.tenant_id if customer else None)
    if resolved_tenant_id is None:
        return None

    customer_name = _customer_name(customer, name or "Customer")
    normalized_phone = normalize_phone_e164(phone or (customer.phone if customer else None))
    if not normalized_phone:
        return None

    scheduled_at = due_at or now_utc()
    links = tenant_links(db, resolved_tenant_id)
    variables = {"customer_name": customer_name, **links}
    subject, body = _render_template("monthly_promo_whatsapp", variables)
    dedupe_base = f"customer:{customer.id}" if customer else f"phone:{normalized_phone}"
    return _queue_task(
        db,
        tenant_id=resolved_tenant_id,
        channel="whatsapp",
        template_key="monthly_promo_whatsapp",
        event_type="monthly_promo",
        dedupe_key=f"{dedupe_base}:monthly_promo:{dedupe_suffix}:{scheduled_at.date().isoformat()}",
        scheduled_at=scheduled_at,
        subject=subject,
        body=body,
        customer_id=customer.id if customer else None,
        recipient_phone_e164=normalized_phone,
        recipient_name=customer_name,
        payload=variables,
    )


async def send_monthly_promo_backfill(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    cutoff_date: date,
    limit: int = 2000,
) -> dict[str, Any]:
    cutoff_start_utc = _india_day_bounds(cutoff_date)[1]
    now = now_utc()

    eligible_customers = (
        db.query(Customer)
        .filter(
            Customer.tenant_id == tenant_id,
            Customer.is_active.is_(True),
            Customer.phone.isnot(None),
            or_(Customer.last_order_date.isnot(None), Customer.first_order_date.isnot(None)),
            or_(
                Customer.last_order_date < cutoff_start_utc,
                Customer.first_order_date < cutoff_start_utc,
            ),
        )
        .order_by(Customer.last_order_date.asc().nullsfirst(), Customer.first_order_date.asc().nullsfirst())
        .limit(limit)
        .all()
    )

    pending_tasks = (
        db.query(MessageAutomationTask)
        .filter(
            MessageAutomationTask.tenant_id == tenant_id,
            MessageAutomationTask.channel == "whatsapp",
            MessageAutomationTask.template_key == "monthly_promo_whatsapp",
            MessageAutomationTask.status == PENDING,
        )
        .order_by(MessageAutomationTask.created_at.desc())
        .all()
    )
    pending_by_customer_id: dict[uuid.UUID, MessageAutomationTask] = {}
    for task in pending_tasks:
        if task.customer_id and task.customer_id not in pending_by_customer_id:
            pending_by_customer_id[task.customer_id] = task

    queued_existing = 0
    created_new = 0
    skipped_no_phone = 0
    tasks_to_send: list[MessageAutomationTask] = []

    for customer in eligible_customers:
        phone = normalize_phone_e164(customer.phone)
        if not phone:
            skipped_no_phone += 1
            continue

        existing_task = pending_by_customer_id.get(customer.id)
        if existing_task is not None:
            existing_task.scheduled_at = now
            existing_task.next_retry_at = None
            existing_task.recipient_phone_e164 = phone
            existing_task.recipient_name = _customer_name(customer, customer.name)
            existing_task.payload = {
                "customer_name": _customer_name(customer, customer.name),
                **tenant_links(db, tenant_id),
            }
            queued_existing += 1
            tasks_to_send.append(existing_task)
            continue

        new_task = schedule_monthly_promo_whatsapp(
            db,
            customer=customer,
            due_at=now,
            dedupe_suffix="april_15_backfill",
        )
        if new_task is not None:
            created_new += 1
            tasks_to_send.append(new_task)

    db.commit()

    sent_count = 0
    failed_count = 0
    cancelled_count = 0
    skipped_count = 0

    for task in tasks_to_send:
        try:
            task = (
                db.query(MessageAutomationTask)
                .options(joinedload(MessageAutomationTask.order))
                .filter(MessageAutomationTask.id == task.id)
                .first()
            ) or task

            if _task_blocked_by_preference(db, task):
                task.status = CANCELLED
                task.cancelled_at = now_utc()
                task.error_reason = "Customer messaging preference is paused or opted out"
                cancelled_count += 1
                db.commit()
                continue

            task.attempts = (task.attempts or 0) + 1
            result = await _send_task(db, task)
            if result.get("success"):
                task.status = SENT
                task.sent_at = now_utc()
                task.provider_message_id = result.get("provider_message_id")
                task.provider_response = result
                task.error_reason = None
                sent_count += 1
            elif result.get("skipped"):
                task.status = SKIPPED
                task.error_reason = result.get("message")
                task.provider_response = result
                skipped_count += 1
            else:
                _mark_retry_or_failed(
                    task,
                    result.get("message") or "Send failed",
                    permanent=result.get("permanent_failure", False),
                )
                failed_count += 1 if task.status == FAILED else 0

            db.commit()
        except Exception as exc:
            db.rollback()
            log.exception("Monthly promo backfill failed: %s", task.id if task else "unknown")
            task = db.query(MessageAutomationTask).filter(MessageAutomationTask.id == task.id).first() if task else None
            if task:
                task.attempts = (task.attempts or 0) + 1
                _mark_retry_or_failed(task, str(exc))
                db.commit()
                failed_count += 1 if task.status == FAILED else 0

    return {
        "success": True,
        "cutoff_date": cutoff_date.isoformat(),
        "eligible_customers": len(eligible_customers),
        "queued_existing": queued_existing,
        "created_new": created_new,
        "skipped_no_phone": skipped_no_phone,
        "sent": sent_count,
        "failed": failed_count,
        "skipped": skipped_count,
        "cancelled": cancelled_count,
    }


def handle_order_created(db: Session, order: Order | uuid.UUID) -> None:
    schedule_order_created(db, order)


def handle_order_changed(
    db: Session,
    order: Order | uuid.UUID,
    *,
    previous_tracking_number: str | None = None,
    previous_status: OrderStatus | str | None = None,
) -> None:
    order_row = _load_order(db, order)
    if not order_row:
        return

    previous_tracking = (previous_tracking_number or "").strip()
    current_tracking = (order_row.tracking_number or "").strip()
    if current_tracking and not previous_tracking and order_row.status not in TERMINAL_ORDER_STATUSES:
        schedule_tracking_added(db, order_row)

    if order_row.status in TERMINAL_ORDER_STATUSES:
        cancel_tracking_followups_for_order(db, order_row, f"Order is {order_row.status.value}")
        if order_row.status == OrderStatus.delivered:
            due_at = (order_row.delivered_at or now_utc()) + timedelta(days=2)
            schedule_review_request(db, customer=order_row.customer, order=order_row, due_at=due_at, dedupe_suffix="delivered")
    elif current_tracking:
        active_followup = (
            db.query(MessageAutomationTask)
            .filter(
                MessageAutomationTask.order_id == order_row.id,
                MessageAutomationTask.template_key == "tracking_followup_3_day",
                MessageAutomationTask.status == PENDING,
            )
            .first()
        )
        if active_followup is None:
            schedule_tracking_followup(db, order_row)


def queue_existing_customer_review_campaign(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    include_phones: list[str] | None = None,
) -> dict[str, Any]:
    queued_reviews = 0
    queued_promos = 0
    skipped = 0
    seen_phones: set[str] = set()
    due_now = now_utc()
    promo_due = due_now + timedelta(days=30)

    settings_row = get_or_create_settings(db, tenant_id)
    if settings_row.review_campaign_started_at is None:
        settings_row.review_campaign_started_at = due_now

    customers = (
        db.query(Customer)
        .filter(Customer.tenant_id == tenant_id, Customer.is_active.is_(True))
        .order_by(Customer.created_at.asc())
        .all()
    )
    for customer in customers:
        normalized_phone = normalize_phone_e164(customer.phone)
        if not normalized_phone:
            skipped += 1
            continue
        seen_phones.add(normalized_phone)
        review_task = schedule_review_request(
            db,
            customer=customer,
            due_at=due_now,
            dedupe_suffix="existing_customer_start",
        )
        promo_task = schedule_monthly_promo(db, customer=customer, due_at=promo_due)
        queued_reviews += 1 if review_task else 0
        queued_promos += 1 if promo_task else 0

    for phone in include_phones or []:
        normalized_phone = normalize_phone_e164(phone)
        if not normalized_phone or normalized_phone in seen_phones:
            continue
        review_task = schedule_review_request(
            db,
            tenant_id=tenant_id,
            phone=normalized_phone,
            name="Pureleven Team",
            due_at=due_now,
            dedupe_suffix="existing_customer_start",
        )
        promo_task = schedule_monthly_promo(
            db,
            tenant_id=tenant_id,
            phone=normalized_phone,
            name="Pureleven Team",
            due_at=promo_due,
        )
        queued_reviews += 1 if review_task else 0
        queued_promos += 1 if promo_task else 0

    db.flush()
    return {
        "success": True,
        "customers_checked": len(customers),
        "review_tasks_queued": queued_reviews,
        "promo_tasks_queued": queued_promos,
        "skipped_no_phone": skipped,
    }


# ---------------------------------------------------------------------------
# Sending / worker
# ---------------------------------------------------------------------------

async def process_due_tasks(db: Session, *, limit: int = 50) -> dict[str, Any]:
    due_time = now_utc()
    tasks = (
        db.query(MessageAutomationTask)
        .filter(
            MessageAutomationTask.status == PENDING,
            MessageAutomationTask.scheduled_at <= due_time,
            or_(MessageAutomationTask.next_retry_at.is_(None), MessageAutomationTask.next_retry_at <= due_time),
        )
        .order_by(MessageAutomationTask.scheduled_at.asc(), MessageAutomationTask.created_at.asc())
        .limit(limit)
        .all()
    )

    sent_count = 0
    failed_count = 0
    skipped_count = 0
    cancelled_count = 0

    for task in tasks:
        try:
            processed = await _process_single_task(db, task)
            outcome = processed.get("outcome")
            if outcome == "sent":
                sent_count += 1
            elif outcome == "skipped":
                skipped_count += 1
            elif outcome == "cancelled":
                cancelled_count += 1
            elif outcome == "failed":
                failed_count += 1

            db.commit()
        except Exception as exc:
            db.rollback()
            log.exception("Message automation task failed: %s", task.id)
            task = db.query(MessageAutomationTask).filter(MessageAutomationTask.id == task.id).first()
            if task:
                task.attempts = (task.attempts or 0) + 1
                _mark_retry_or_failed(task, str(exc))
                db.commit()
                failed_count += 1 if task.status == FAILED else 0

    return {
        "success": True,
        "checked": len(tasks),
        "sent": sent_count,
        "failed": failed_count,
        "skipped": skipped_count,
        "cancelled": cancelled_count,
    }


async def _process_single_task(db: Session, task: MessageAutomationTask) -> dict[str, Any]:
    refreshed = _refresh_dynamic_task(db, task)
    if not refreshed:
        return {"outcome": "cancelled", "message": task.error_reason}

    if _task_blocked_by_preference(db, task):
        task.status = CANCELLED
        task.cancelled_at = now_utc()
        task.error_reason = "Customer messaging preference is paused or opted out"
        return {"outcome": "cancelled", "message": task.error_reason}

    task.attempts = (task.attempts or 0) + 1
    result = await _send_task(db, task)
    if result.get("success"):
        task.status = SENT
        task.sent_at = now_utc()
        task.provider_message_id = result.get("provider_message_id")
        task.provider_response = result
        task.error_reason = None
        _schedule_next_after_success(db, task)
        return {"outcome": "sent", "result": result}

    if result.get("skipped"):
        task.status = SKIPPED
        task.error_reason = result.get("message")
        task.provider_response = result
        return {"outcome": "skipped", "result": result}

    _mark_retry_or_failed(
        task,
        result.get("message") or "Send failed",
        permanent=result.get("permanent_failure", False),
    )
    return {
        "outcome": "failed" if task.status == FAILED else "pending",
        "result": result,
    }


def _refresh_dynamic_task(db: Session, task: MessageAutomationTask) -> bool:
    if task.order_id and task.template_key in {"tracking_added", "tracking_followup_3_day", "review_request"}:
        order_row = _load_order(db, task.order_id)
        if not order_row:
            task.status = CANCELLED
            task.cancelled_at = now_utc()
            task.error_reason = "Order no longer exists"
            return False
        if task.template_key == "tracking_followup_3_day" and order_row.status in TERMINAL_ORDER_STATUSES:
            task.status = CANCELLED
            task.cancelled_at = now_utc()
            task.error_reason = f"Order is {order_row.status.value}"
            return False
        variables = _order_variables(db, order_row)
        subject, body = _render_template(task.template_key, variables)
        task.subject = subject
        task.body = body
        task.payload = variables
    return True


def _task_blocked_by_preference(db: Session, task: MessageAutomationTask) -> bool:
    return preference_blocks(db, task.tenant_id, task.recipient_phone_e164, task.channel)


def _template_parameters(values: list[Any]) -> list[dict[str, str]]:
    return [{"type": "text", "text": str(value or "")} for value in values]


def _named_template_parameters(mapping: dict[str, str], variables: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "type": "text",
            "text": str(variables.get(variable_name, "") or ""),
            "parameter_name": parameter_name,
        }
        for parameter_name, variable_name in mapping.items()
    ]


def _unique_template_names(names: list[Optional[str]]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for name in names:
        if not name:
            continue
        clean = str(name).strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        ordered.append(clean)
    return ordered


def _template_components(template_json: dict[str, Any]) -> list[dict[str, Any]]:
    components = template_json.get("components") or []
    return components if isinstance(components, list) else []


def _body_parameter_mapping_from_template_json(template_json: dict[str, Any]) -> tuple[str | None, dict[str, str] | list[str]]:
    for component in _template_components(template_json):
        component_type = str(component.get("type") or "").lower()
        if component_type != "body":
            continue

        example = component.get("example") or {}
        named_params = example.get("body_text_named_params") or []
        mapping: dict[str, str] = {}
        for item in named_params:
            param_name = str((item or {}).get("param_name") or "").strip()
            if param_name:
                mapping[param_name] = param_name
        if mapping:
            return "named", mapping

        body_text = str(component.get("text") or "")
        named_placeholders = re.findall(r"{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}", body_text)
        if named_placeholders:
            ordered_names = list(dict.fromkeys(named_placeholders))
            return "named", {name: name for name in ordered_names}

        if "{{" not in body_text:
            return "none", []

        return None, []

    return "none", []


def _auto_meta_components_from_template_json(template_json: dict[str, Any], variables: dict[str, Any]) -> list[dict[str, Any]] | None:
    parameter_format, body_fields = _body_parameter_mapping_from_template_json(template_json)
    if parameter_format is None:
        return None
    if parameter_format != "named" or not isinstance(body_fields, dict) or not body_fields:
        return []
    return [{"type": "body", "parameters": _named_template_parameters(body_fields, variables)}]


def _manual_meta_components_from_template_json(
    template_json: dict[str, Any],
    variables: dict[str, Any],
) -> list[dict[str, Any]]:
    parameter_format, body_fields = _body_parameter_mapping_from_template_json(template_json)
    if parameter_format == "named" and isinstance(body_fields, dict):
        return [{"type": "body", "parameters": _named_template_parameters(body_fields, variables)}]
    if parameter_format == "none":
        return []

    body_text = ""
    for component in _template_components(template_json):
        if str(component.get("type") or "").lower() == "body":
            body_text = str(component.get("text") or "")
            break
    positional_parameters = sorted(
        {int(value) for value in re.findall(r"{{\s*(\d+)\s*}}", body_text)}
    )
    if not positional_parameters:
        return []
    if positional_parameters != list(range(1, len(positional_parameters) + 1)):
        raise ValueError("Template body parameters must be sequential")

    configured_values = list(variables.get("body_parameter_values") or [])
    values: list[str] = []
    for index in range(len(positional_parameters)):
        if index == 0:
            values.append(str(variables.get("customer_name") or "Customer"))
        elif index < len(configured_values):
            values.append(str(configured_values[index] or ""))
        else:
            raise ValueError(
                "This template needs additional body values and is not compatible with Customer Retarget bulk send"
            )
    return [{"type": "body", "parameters": _template_parameters(values)}]


def _template_parameter_summary(template_name: str, template_json: dict[str, Any]) -> tuple[str, list[str]]:
    parameter_format, body_fields = _body_parameter_mapping_from_template_json(template_json)
    if parameter_format is not None:
        if parameter_format == "named" and isinstance(body_fields, dict):
            return "NAMED", list(body_fields.keys())
        if parameter_format == "none":
            return "NONE", []

    body_text = ""
    for component in _template_components(template_json):
        if str(component.get("type") or "").lower() == "body":
            body_text = str(component.get("text") or "")
            break
    positional_parameters = sorted(
        {int(value) for value in re.findall(r"{{\s*(\d+)\s*}}", body_text)}
    )
    if positional_parameters:
        return "POSITIONAL", [f"{{{{{value}}}}}" for value in positional_parameters]

    spec = WHATSAPP_TEMPLATE_SPECS.get(template_name)
    if spec is None:
        return "UNKNOWN", []

    parameter_format = str(spec.get("parameter_format") or "positional").upper()
    body_fields = spec.get("body") or []
    if isinstance(body_fields, dict):
        if parameter_format == "NAMED":
            return parameter_format, list(body_fields.keys())
        return parameter_format, list(body_fields.values())
    return parameter_format, list(body_fields)


def _template_button_parameter_summary(template_json: dict[str, Any]) -> list[str]:
    parameters: list[str] = []
    for component in _template_components(template_json):
        if str(component.get("type") or "").lower() != "buttons":
            continue
        for index, button in enumerate(component.get("buttons") or []):
            if str((button or {}).get("type") or "").lower() != "url":
                continue
            button_url = str((button or {}).get("url") or "")
            placeholder_count = len(re.findall(r"{{\s*\d+\s*}}", button_url))
            example_values = (button or {}).get("example") or []
            if not placeholder_count and not example_values:
                continue
            label = str((button or {}).get("text") or f"Button {index + 1}").strip() or f"Button {index + 1}"
            for param_index in range(max(placeholder_count, 1)):
                parameters.append(f"{label} URL parameter {param_index + 1}")
    return parameters


def _template_health_details(template_name: str, template_json: dict[str, Any]) -> dict[str, Any]:
    parameter_format, body_parameters = _template_parameter_summary(template_name, template_json)
    button_parameters = _template_button_parameter_summary(template_json)
    warnings: list[str] = []
    health = "ok"

    if parameter_format == "UNKNOWN":
        warnings.append("Body parameter inference is unknown. This template may fail unless the app has an explicit mapping.")
        health = "danger"

    if button_parameters:
        warnings.append(
            f"Dynamic URL button parameters detected: {', '.join(button_parameters)}. Validate button mappings before using this template in automation."
        )
        if health != "danger":
            health = "warning"

    summary = None
    if health == "danger":
        summary = "Template has unknown parameter inference and should be validated before automation."
    elif health == "warning":
        summary = "Template uses dynamic button parameters and is higher risk for automated sends."

    return {
        "parameter_format": parameter_format,
        "body_parameters": body_parameters,
        "button_parameters": button_parameters,
        "template_health": health,
        "template_health_summary": summary,
        "template_health_warnings": warnings,
    }


def _template_has_media_header(template_json: dict[str, Any]) -> bool:
    for component in _template_components(template_json):
        if str(component.get("type") or "").lower() != "header":
            continue
        if str(component.get("format") or "").lower() == "image":
            return True
    return False


def _build_meta_components(template_name: str, variables: dict[str, Any], *, template_json: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    if template_json:
        auto_components = _auto_meta_components_from_template_json(template_json, variables)
        if auto_components is not None:
            return auto_components

    spec = WHATSAPP_TEMPLATE_SPECS.get(template_name)
    if spec is None:
        raise ValueError(f"No automation parameter mapping is defined for WhatsApp template '{template_name}'")

    components: list[dict[str, Any]] = []
    body_fields = spec.get("body") or []
    if body_fields:
        parameter_format = str(spec.get("parameter_format") or "positional").lower()
        if parameter_format == "named" and isinstance(body_fields, dict):
            body_parameters = _named_template_parameters(body_fields, variables)
        else:
            if isinstance(body_fields, dict):
                body_values = [variables.get(field_name, "") for field_name in body_fields.values()]
            else:
                body_values = [variables.get(field_name, "") for field_name in body_fields]
        components.append(
            {
                "type": "body",
                "parameters": body_parameters if parameter_format == "named" and isinstance(body_fields, dict) else _template_parameters(body_values),
            }
        )

    for index, field_names in (spec.get("buttons") or {}).items():
        components.append(
            {
                "type": "button",
                "sub_type": "url",
                "index": str(index),
                "parameters": _template_parameters([variables.get(field_name, "") for field_name in field_names]),
            }
        )

    return components


def _header_component_from_template(
    template_json: dict[str, Any],
    *,
    media_url: str | None = None,
) -> dict[str, Any] | None:
    for component in _template_components(template_json):
        if str(component.get("type") or "").lower() != "header":
            continue
        if str(component.get("format") or "").lower() != "image":
            continue
        configured_media_url = str(media_url or "").strip()
        if configured_media_url:
            return {
                "type": "header",
                "parameters": [
                    {
                        "type": "image",
                        "image": {"link": configured_media_url},
                    }
                ],
            }
        header_handles = ((component.get("example") or {}).get("header_handle") or [])
        if not header_handles:
            return None
        return {
            "type": "header",
            "parameters": [
                {
                    "type": "image",
                    "image": {"link": header_handles[0]},
                }
            ],
        }
    return None


async def _approved_wabis_templates(settings_row: Any) -> dict[str, dict[str, Any]]:
    if not settings_row.wabis_api_token or not settings_row.wabis_phone_number_id:
        return {}

    cache_key = f"{settings_row.tenant_id}:{settings_row.wabis_phone_number_id}"
    cached = _WABIS_TEMPLATE_CACHE.get(cache_key)
    current_time = now_utc()
    if cached and cached.get("expires_at") and cached["expires_at"] > current_time:
        return cached.get("templates", {})

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            "https://bot.wabis.in/api/v1/whatsapp/template/list",
            data={
                "apiToken": settings_row.wabis_api_token,
                "phone_number_id": settings_row.wabis_phone_number_id,
            },
        )
        response.raise_for_status()
        payload = response.json()

    raw_templates = payload.get("message") or []
    if isinstance(raw_templates, dict):
        raw_templates = [raw_templates]

    templates: dict[str, dict[str, Any]] = {}
    shared_access_token: str | None = None
    for raw_template in raw_templates:
        if str(raw_template.get("status") or "").lower() != "approved":
            continue
        try:
            template_json = json.loads(raw_template.get("template_json") or "{}")
        except Exception:
            template_json = {}

        template_name = (raw_template.get("template_name") or template_json.get("name") or "").strip()
        if not template_name:
            continue

        template_access_token = template_json.get("access_token")
        if template_access_token and not shared_access_token:
            shared_access_token = template_access_token

        templates[template_name] = {
            "name": template_name,
            "locale": raw_template.get("locale") or template_json.get("language") or "en",
            "access_token": template_access_token,
            "template_id": raw_template.get("template_id") or template_json.get("id"),
            "status": raw_template.get("status") or template_json.get("status") or "APPROVED",
            "category": raw_template.get("template_category") or template_json.get("category"),
            "template_json": template_json,
        }

    if shared_access_token:
        for template_info in templates.values():
            template_info["access_token"] = template_info.get("access_token") or shared_access_token

    _WABIS_TEMPLATE_CACHE[cache_key] = {
        "expires_at": current_time + WABIS_TEMPLATE_CACHE_TTL,
        "templates": templates,
    }
    return templates


def _meta_template_access_token(settings_row: Any, approved_templates: dict[str, dict[str, Any]]) -> str | None:
    configured_token = (getattr(settings_row, "meta_access_token", None) or "").strip()
    if configured_token:
        return configured_token
    for template_info in approved_templates.values():
        access_token = (template_info.get("access_token") or "").strip()
        if access_token:
            return access_token
    return None


def _meta_template_row_to_info(row: dict[str, Any], access_token: str) -> dict[str, Any]:
    template_json = {
        "name": row.get("name"),
        "language": row.get("language") or "en",
        "status": row.get("status") or "UNKNOWN",
        "category": row.get("category"),
        "id": row.get("id"),
        "components": row.get("components") or [],
    }
    return {
        "name": row.get("name"),
        "locale": row.get("language") or "en",
        "access_token": access_token,
        "template_id": row.get("id"),
        "status": row.get("status") or "UNKNOWN",
        "category": row.get("category"),
        "template_json": template_json,
    }


async def _meta_templates_by_name(
    settings_row: Any,
    candidate_names: list[str],
    approved_templates: dict[str, dict[str, Any]],
    language_code: str | None = None,
) -> dict[str, dict[str, Any]]:
    asset_id = _normalize_meta_template_asset_id(getattr(settings_row, "meta_template_asset_id", None))
    access_token = _meta_template_access_token(settings_row, approved_templates)
    if not asset_id or not access_token:
        return {}

    api_version = settings_row.meta_api_version or "v19.0"
    resolved: dict[str, dict[str, Any]] = {}
    async with httpx.AsyncClient(timeout=20) as client:
        for template_name in _unique_template_names(candidate_names):
            response = await client.get(
                f"https://graph.facebook.com/{api_version}/{asset_id}/message_templates",
                params={"name": template_name, "fields": "name,status,category,id,language,components"},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if response.status_code != 200:
                continue
            payload = response.json()
            for row in payload.get("data") or []:
                if str(row.get("name") or "").strip() != template_name:
                    continue
                if str(row.get("status") or "").upper() != "APPROVED":
                    continue
                if language_code and not _language_matches(language_code, row.get("language")):
                    continue
                resolved[template_name] = _meta_template_row_to_info(row, access_token)
                break
    return resolved


async def _meta_template_inventory(
    settings_row: Any,
    approved_templates: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    asset_id = _normalize_meta_template_asset_id(getattr(settings_row, "meta_template_asset_id", None))
    access_token = _meta_template_access_token(settings_row, approved_templates)
    if not asset_id or not access_token:
        return {}

    api_version = settings_row.meta_api_version or "v19.0"
    templates: dict[str, dict[str, Any]] = {}
    next_after: str | None = None

    async with httpx.AsyncClient(timeout=20) as client:
        while True:
            params = {"limit": "100", "fields": "name,status,category,id,language,components"}
            if next_after:
                params["after"] = next_after
            response = await client.get(
                f"https://graph.facebook.com/{api_version}/{asset_id}/message_templates",
                params=params,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if response.status_code != 200:
                break
            payload = response.json()
            for row in payload.get("data") or []:
                template_name = str(row.get("name") or "").strip()
                if not template_name:
                    continue
                templates[template_name] = _meta_template_row_to_info(row, access_token)
            next_after = ((payload.get("paging") or {}).get("cursors") or {}).get("after")
            if not next_after:
                break

    return templates


async def available_whatsapp_templates(db: Session, tenant_id: uuid.UUID) -> list[dict[str, Any]]:
    runtime_settings = _runtime_template_settings(db, tenant_id)
    approved_templates = await _approved_wabis_templates(runtime_settings)
    meta_templates = await _meta_template_inventory(runtime_settings, approved_templates)

    names = sorted(set([*approved_templates.keys(), *meta_templates.keys()]), key=str.lower)
    options: list[dict[str, Any]] = []
    for template_name in names:
        template_info = meta_templates.get(template_name) or approved_templates.get(template_name) or {}
        template_json = template_info.get("template_json") or {}
        health_details = _template_health_details(template_name, template_json)
        sources: list[str] = []
        if template_name in approved_templates:
            sources.append("wabis")
        if template_name in meta_templates:
            sources.append("meta")
        options.append(
            {
                "name": template_name,
                "status": str(template_info.get("status") or ("APPROVED" if template_name in approved_templates else "UNKNOWN")),
                "category": template_info.get("category"),
                "language": template_info.get("locale") or template_json.get("language"),
                "source": ",".join(sources) if sources else "unknown",
                "app_visible": template_name in approved_templates,
                "has_media_header": _template_has_media_header(template_json),
                "parameter_format": health_details["parameter_format"],
                "body_parameters": health_details["body_parameters"],
                "button_parameters": health_details["button_parameters"],
                "template_health": health_details["template_health"],
                "template_health_summary": health_details["template_health_summary"],
                "template_health_warnings": health_details["template_health_warnings"],
            }
        )
    return options


async def resolve_manual_whatsapp_template(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    template_name: str,
    language_code: str,
) -> dict[str, Any] | None:
    runtime_settings = _runtime_template_settings(db, tenant_id)
    approved_templates = await _approved_wabis_templates(runtime_settings)
    meta_templates = await _meta_templates_by_name(
        runtime_settings,
        [template_name],
        approved_templates,
        language_code=language_code,
    )
    template_info = meta_templates.get(template_name)
    if template_info:
        return template_info

    approved_info = approved_templates.get(template_name)
    if approved_info and _language_matches(language_code, approved_info.get("locale")):
        return approved_info
    return None


def queue_manual_retarget_template(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    customer: Customer,
    template_name: str,
    language_code: str,
    header_image_url: str | None,
    employee_id: uuid.UUID,
    batch_id: uuid.UUID,
) -> MessageAutomationTask | None:
    normalized_phone = normalize_phone_e164(customer.phone)
    if not normalized_phone:
        return None

    links = tenant_links(db, tenant_id)
    customer_name = (customer.name or "").strip() or (
        "സുഹൃത്തേ" if _language_matches("ml", language_code) else "Customer"
    )
    payload = {
        "manual_template_name": template_name,
        "manual_language_code": language_code,
        "manual_header_image_url": header_image_url,
        "manual_employee_id": str(employee_id),
        "manual_batch_id": str(batch_id),
        "customer_name": customer_name,
        "name": customer_name,
        "phone": normalized_phone,
        **links,
    }
    return _queue_task(
        db,
        tenant_id=tenant_id,
        channel="whatsapp",
        template_key=RETARGET_MANUAL_TEMPLATE_KEY,
        event_type="customer_retarget_manual",
        dedupe_key=f"customer-retarget:{batch_id}:{customer.id}:{template_name}:{language_code}",
        scheduled_at=now_utc(),
        body=f"WhatsApp template: {template_name}",
        customer_id=customer.id,
        recipient_phone_e164=normalized_phone,
        recipient_name=customer_name,
        payload=payload,
    )


async def _resolve_whatsapp_template(settings_row: Any, task: MessageAutomationTask) -> dict[str, Any] | None:
    if task.template_key == RETARGET_MANUAL_TEMPLATE_KEY:
        variables = dict(task.payload or {})
        template_name = str(variables.get("manual_template_name") or "").strip()
        language_code = str(variables.get("manual_language_code") or "en").strip()
        if not template_name:
            return None

        approved_templates = await _approved_wabis_templates(settings_row)
        meta_templates = await _meta_templates_by_name(
            settings_row,
            [template_name],
            approved_templates,
            language_code=language_code,
        )
        template_info = meta_templates.get(template_name)
        if template_info is None:
            approved_info = approved_templates.get(template_name)
            if approved_info and _language_matches(language_code, approved_info.get("locale")):
                template_info = approved_info
        if template_info is None:
            return None

        template_json = template_info.get("template_json") or {}
        components = _manual_meta_components_from_template_json(template_json, variables)
        header_component = _header_component_from_template(
            template_json,
            media_url=variables.get("manual_header_image_url"),
        )
        if _template_has_media_header(template_json) and header_component is None:
            raise ValueError("This template requires a public HTTPS header image URL")
        if header_component:
            components = [header_component, *components]
        return {
            **template_info,
            "locale": template_info.get("locale") or language_code,
            "components": components,
        }

    desired_template = TEMPLATES.get(task.template_key)
    selected_template_name = _configured_template_name(settings_row, task.template_key)
    candidate_names = _unique_template_names(
        [
            selected_template_name,
            desired_template.meta_template_name if desired_template else None,
            *WHATSAPP_TEMPLATE_FALLBACKS.get(task.template_key, []),
        ]
    )
    if not candidate_names:
        return None

    approved_templates = await _approved_wabis_templates(settings_row)
    meta_templates = await _meta_templates_by_name(settings_row, candidate_names, approved_templates)
    variables = dict(task.payload or {})
    variables.setdefault("customer_name", task.recipient_name or "Customer")
    header_media_url = resolved_template_header_media_urls(settings_row).get(task.template_key)

    for candidate_name in candidate_names:
        template_info = approved_templates.get(candidate_name) or meta_templates.get(candidate_name)
        if not template_info:
            continue
        components = _build_meta_components(candidate_name, variables, template_json=template_info.get("template_json") or {})
        header_component = _header_component_from_template(
            template_info.get("template_json") or {},
            media_url=header_media_url,
        )
        if header_component:
            components = [header_component, *components]
        return {
            **template_info,
            "components": components,
        }
    return None


async def _send_meta_template(settings_row: Any, *, phone: str, template_info: dict[str, Any]) -> dict[str, Any]:
    access_token = (template_info.get("access_token") or "").strip()
    if not access_token:
        return {
            "success": False,
            "message": f"WhatsApp template '{template_info.get('name')}' is approved but missing an access token",
            "permanent_failure": True,
        }
    if not settings_row.wabis_phone_number_id:
        return {
            "success": False,
            "message": "WhatsApp phone_number_id is not configured",
            "permanent_failure": True,
        }

    api_version = settings_row.meta_api_version or "v19.0"
    meta_payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "template",
        "template": {
            "name": template_info["name"],
            "language": {"code": template_info.get("locale") or "en"},
        },
    }
    if template_info.get("components"):
        meta_payload["template"]["components"] = template_info["components"]

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            f"https://graph.facebook.com/{api_version}/{settings_row.wabis_phone_number_id}/messages",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json=meta_payload,
        )
        payload = response.json()

    if response.status_code in {200, 201} or payload.get("messages"):
        provider_message_id = (payload.get("messages") or [{}])[0].get("id")
        return {
            "success": True,
            "message": "Template sent successfully",
            "provider_message_id": provider_message_id,
            "raw_response": payload,
            "via": "meta_template",
            "template_name": template_info["name"],
        }

    error_message = payload.get("error", {}).get("message") or payload.get("message") or str(payload)
    return {
        "success": False,
        "message": error_message,
        "raw_response": payload,
        "via": "meta_template",
        "template_name": template_info["name"],
    }


def _log_whatsapp_outbound(
    db: Session,
    *,
    task: MessageAutomationTask,
    conversation: WaConversation,
    content: str,
    message_type: WaMessageType,
    result: dict[str, Any],
) -> None:
    employee_id = None
    raw_employee_id = (task.payload or {}).get("manual_employee_id")
    if raw_employee_id:
        try:
            employee_id = uuid.UUID(str(raw_employee_id))
        except (TypeError, ValueError):
            employee_id = None
    message_row = WaMessage(
        tenant_id=task.tenant_id,
        conversation_id=conversation.id,
        provider_message_id=result.get("provider_message_id"),
        direction=WaMessageDirection.outbound,
        message_type=message_type,
        content=content,
        status=WaMessageStatus.sent if result.get("success") else WaMessageStatus.failed,
        sent_at=now_utc(),
        failed_reason=None if result.get("success") else result.get("message"),
        sent_by_employee_id=employee_id,
        raw_payload=result.get("raw_response") or result,
    )
    db.add(message_row)
    conversation.last_message_at = now_utc()
    conversation.last_message_direction = WaMessageDirection.outbound


async def _send_task(db: Session, task: MessageAutomationTask) -> dict[str, Any]:
    if task.channel == "whatsapp":
        return await _send_whatsapp_text(db, task)

    if task.channel == "email":
        email_result = _send_email(task)
        if email_result.get("success"):
            return email_result
        if task.template_key == "monthly_promo_email" and task.recipient_phone_e164:
            variables = task.payload or {}
            subject, body = _render_template("monthly_promo_whatsapp", variables)
            fallback_task = task
            fallback_task.body = body
            fallback_task.subject = subject
            fallback_result = await _send_whatsapp_text(db, fallback_task)
            fallback_result["fallback_from"] = "email"
            fallback_result["email_error"] = email_result.get("message")
            return fallback_result
        return email_result

    return {"success": False, "message": f"Unsupported channel {task.channel}"}


async def _send_whatsapp_text(db: Session, task: MessageAutomationTask) -> dict[str, Any]:
    if not task.recipient_phone_e164:
        return {"success": False, "message": "No WhatsApp phone number"}

    from app.modules.wa_engine.service import _provider, get_or_create_settings as get_wa_settings

    wa_settings_row = get_wa_settings(db, task.tenant_id)
    if not wa_settings_row.is_active:
        return {"success": False, "skipped": True, "message": "WhatsApp settings are inactive"}

    send_phone = whatsapp_send_phone(task.recipient_phone_e164)
    provider = _provider(wa_settings_row)
    runtime_settings = _runtime_template_settings(db, task.tenant_id, wa_settings_row=wa_settings_row)

    subscriber = _get_or_create_subscriber(db, task, send_phone)
    conversation = _get_or_create_conversation(db, task.tenant_id, subscriber)

    template_result = await _resolve_whatsapp_template(runtime_settings, task)
    if template_result is not None:
        send_result = await _send_meta_template(runtime_settings, phone=send_phone, template_info=template_result)
        _log_whatsapp_outbound(
            db,
            task=task,
            conversation=conversation,
            content=task.body,
            message_type=WaMessageType.template,
            result=send_result,
        )
        send_result["channel"] = "whatsapp"
        send_result["subscriber_id"] = str(subscriber.id)
        return send_result

    if task.template_key in WHATSAPP_TEMPLATE_REQUIRED_KEYS:
        return {
            "success": False,
            "message": f"No approved WhatsApp template is configured for automation '{task.template_key}'",
            "permanent_failure": True,
            "channel": "whatsapp",
            "subscriber_id": str(subscriber.id),
        }

    send_result = await provider.send_text(phone=send_phone, text=task.body)
    _log_whatsapp_outbound(
        db,
        task=task,
        conversation=conversation,
        content=task.body,
        message_type=WaMessageType.text,
        result={
            "success": send_result.success,
            "message": send_result.error or "Sent successfully",
            "provider_message_id": send_result.provider_message_id,
            "raw_response": send_result.raw_response or {},
        },
    )

    return {
        "success": send_result.success,
        "message": "Sent successfully" if send_result.success else (send_result.error or "WhatsApp send failed"),
        "provider_message_id": send_result.provider_message_id,
        "raw_response": send_result.raw_response,
        "channel": "whatsapp",
        "subscriber_id": str(subscriber.id),
    }


def _get_or_create_subscriber(db: Session, task: MessageAutomationTask, send_phone: str) -> WaSubscriber:
    phone_variants = {send_phone, task.recipient_phone_e164 or "", normalize_phone_e164(send_phone)}
    phone_variants = {item for item in phone_variants if item}
    subscriber = (
        db.query(WaSubscriber)
        .filter(WaSubscriber.tenant_id == task.tenant_id, WaSubscriber.phone_number.in_(phone_variants))
        .first()
    )
    if subscriber is None:
        subscriber = WaSubscriber(
            tenant_id=task.tenant_id,
            subscriber_id=send_phone,
            phone_number=send_phone,
            name=task.recipient_name or send_phone,
        )
        db.add(subscriber)
        db.flush()
    elif task.recipient_name and not subscriber.name:
        subscriber.name = task.recipient_name
    return subscriber


def _get_or_create_conversation(db: Session, tenant_id: uuid.UUID, subscriber: WaSubscriber) -> WaConversation:
    conversation = (
        db.query(WaConversation)
        .filter(WaConversation.tenant_id == tenant_id, WaConversation.subscriber_id == subscriber.id)
        .first()
    )
    if conversation is None:
        conversation = WaConversation(tenant_id=tenant_id, subscriber_id=subscriber.id, lead_id=subscriber.lead_id)
        db.add(conversation)
        db.flush()
    return conversation


def _send_email(task: MessageAutomationTask) -> dict[str, Any]:
    if not task.recipient_email:
        return {"success": False, "message": "No email address"}

    smtp_server = os.getenv("SMTP_SERVER") or os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT") or "587")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM") or smtp_user
    if not smtp_server or not smtp_from:
        return {"success": False, "message": "SMTP is not configured"}

    message = EmailMessage()
    message["From"] = smtp_from
    message["To"] = task.recipient_email
    message["Subject"] = task.subject or "Pureleven"
    message.set_content(task.body)

    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=20) as smtp:
            if os.getenv("SMTP_TLS", "true").lower() not in {"false", "0", "no"}:
                smtp.starttls()
            if smtp_user and smtp_password:
                smtp.login(smtp_user, smtp_password)
            smtp.send_message(message)
        return {"success": True, "message": "Email sent", "channel": "email"}
    except Exception as exc:
        return {"success": False, "message": f"Email send failed: {exc}"}


def _mark_retry_or_failed(task: MessageAutomationTask, reason: str, *, permanent: bool = False) -> None:
    task.error_reason = reason
    if permanent:
        task.status = FAILED
        task.next_retry_at = None
        return
    if (task.attempts or 0) >= (task.max_attempts or 3):
        task.status = FAILED
        task.next_retry_at = None
        return
    task.status = PENDING
    delay_minutes = min(60, max(5, (task.attempts or 1) * 10))
    task.next_retry_at = now_utc() + timedelta(minutes=delay_minutes)


def _schedule_next_after_success(db: Session, task: MessageAutomationTask) -> None:
    if task.template_key == "tracking_followup_3_day" and task.order_id:
        order_row = _load_order(db, task.order_id)
        if order_row and order_row.status not in TERMINAL_ORDER_STATUSES:
            schedule_tracking_followup(db, order_row, due_at=now_utc() + timedelta(days=3))
    elif task.event_type == "monthly_promo":
        customer = db.query(Customer).filter(Customer.id == task.customer_id).first() if task.customer_id else None
        schedule_monthly_promo(
            db,
            customer=customer,
            tenant_id=task.tenant_id,
            phone=task.recipient_phone_e164,
            email=task.recipient_email,
            name=task.recipient_name,
            due_at=now_utc() + timedelta(days=30),
        )


def _clean_whatsapp_issue(reason: str | None, *, template_name: str | None = None) -> str | None:
    clean = str(reason or "").strip()
    if not clean:
        return None

    lowered = clean.lower()
    if "waiting for approved whatsapp template" in lowered:
        current_template_name = str(template_name or "").strip()
        if not current_template_name:
            current_template_name = clean.split("template", 1)[-1].strip() if "template" in lowered else ""
        if current_template_name:
            return f"Waiting for approved WhatsApp template {current_template_name}."
        return "Waiting for an approved WhatsApp template before this message can send."
    if "24 hour window" in lowered:
        return "Outside the 24-hour WhatsApp window. Use an approved template or wait for the customer to reply."
    if "131049" in clean:
        return "Meta blocked delivery for engagement quality reasons (131049)."
    if "no customer phone" in lowered or "no whatsapp phone" in lowered:
        return "No customer phone number is available on this order."
    if "preference is paused or opted out" in lowered:
        return "Customer messaging is paused or opted out."
    if "no approved whatsapp template is configured" in lowered:
        return "No approved WhatsApp template is configured for this automation."
    if lowered.startswith("order is "):
        return None
    return clean


def _message_status_label(task: MessageAutomationTask) -> str:
    status = str(task.status or "").lower()
    if status == SENT:
        return "accepted"
    if status == PENDING:
        lowered = str(task.error_reason or "").lower()
        if "waiting for approved whatsapp template" in lowered:
            return "blocked"
        return "pending"
    if status == CANCELLED:
        lowered = str(task.error_reason or "").lower()
        if lowered.startswith("order is "):
            return "stopped"
        return "cancelled"
    return status or "unknown"


def _message_status_detail(task: MessageAutomationTask, duplicate_count: int) -> str | None:
    status_label = _message_status_label(task)
    if status_label == "accepted":
        detail = "Accepted by Meta. Final delivered or read receipts are not available in this app yet."
    elif status_label == "blocked":
        detail = "This automation is waiting for an approved WhatsApp template before it can send."
    elif status_label == "stopped":
        detail = "No send was needed because the order already reached a terminal status."
    elif status_label == "cancelled":
        detail = "This send was cancelled before delivery."
    else:
        detail = None

    if duplicate_count > 1:
        suffix = f" Latest of {duplicate_count} attempts is shown."
        return f"{detail}{suffix}" if detail else suffix.strip()
    return detail


def _message_task_action_required(task: MessageAutomationTask, *, issue_summary: str | None = None) -> bool:
    status_label = _message_status_label(task)
    if status_label in {"accepted", "stopped"}:
        return False
    return (issue_summary if issue_summary is not None else _clean_whatsapp_issue(task.error_reason)) is not None


def _message_task_log_dict(
    task: MessageAutomationTask,
    *,
    duplicate_count: int = 1,
    settings_row: MessageAutomationSetting | None = None,
) -> dict[str, Any]:
    order_row = getattr(task, "order", None)
    provider_response = task.provider_response if isinstance(task.provider_response, dict) else {}
    order_status = None
    if order_row is not None:
        raw_status = getattr(order_row, "status", None)
        order_status = raw_status.value if hasattr(raw_status, "value") else (str(raw_status) if raw_status else None)

    configured_template_name = _configured_template_name(settings_row, task.template_key) if settings_row else None
    desired_template = TEMPLATES.get(task.template_key)
    issue_summary = _clean_whatsapp_issue(
        task.error_reason,
        template_name=configured_template_name or (desired_template.meta_template_name if desired_template else None),
    )
    status_label = _message_status_label(task)

    return {
        "id": str(task.id),
        "order_id": str(task.order_id) if task.order_id else None,
        "order_number": getattr(order_row, "order_number", None),
        "order_status": order_status,
        "channel": task.channel,
        "template_key": task.template_key,
        "event_type": task.event_type,
        "status": task.status,
        "recipient_name": task.recipient_name,
        "recipient_phone_e164": task.recipient_phone_e164,
        "provider_message_id": task.provider_message_id,
        "provider_template_name": provider_response.get("template_name"),
        "scheduled_at": task.scheduled_at.isoformat() if task.scheduled_at else None,
        "sent_at": task.sent_at.isoformat() if task.sent_at else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "attempts": task.attempts or 0,
        "duplicate_count": duplicate_count,
        "status_label": status_label,
        "status_detail": _message_status_detail(task, duplicate_count),
        "action_required": _message_task_action_required(task, issue_summary=issue_summary),
        "error_reason": task.error_reason,
        "issue_summary": issue_summary,
    }


def _india_day_bounds(target_date: date | None = None) -> tuple[date, datetime, datetime]:
    local_date = target_date or datetime.now(INDIA_TZ).date()
    start_local = datetime(local_date.year, local_date.month, local_date.day, tzinfo=INDIA_TZ)
    end_local = start_local + timedelta(days=1)
    return local_date, start_local.astimezone(UTC), end_local.astimezone(UTC)


def _format_task_resume_cursor(task: MessageAutomationTask) -> str | None:
    if not task.created_at or not task.id:
        return None
    return f"{task.created_at.isoformat()}|{task.id}"


def _parse_task_resume_cursor(resume_cursor: str | None) -> tuple[datetime, uuid.UUID] | None:
    if not resume_cursor:
        return None
    parts = str(resume_cursor).strip().split("|", 1)
    if len(parts) != 2:
        raise ValueError("Invalid resume cursor")
    created_at_raw, task_id_raw = parts
    try:
        created_at = datetime.fromisoformat(created_at_raw)
        task_id = uuid.UUID(task_id_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid resume cursor") from exc
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return created_at.astimezone(UTC), task_id


def _historical_review_request_candidate_dict(task: MessageAutomationTask) -> dict[str, Any]:
    order_row = getattr(task, "order", None)
    raw_status = getattr(order_row, "status", None)
    order_status = raw_status.value if hasattr(raw_status, "value") else (str(raw_status) if raw_status else None)
    return {
        "task_id": str(task.id),
        "order_id": str(task.order_id) if task.order_id else None,
        "order_number": getattr(order_row, "order_number", None),
        "order_status": order_status,
        "template_key": task.template_key,
        "recipient_name": task.recipient_name,
        "recipient_phone_e164": task.recipient_phone_e164,
        "scheduled_at": task.scheduled_at.isoformat() if task.scheduled_at else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "status": task.status,
    }


def _historical_review_request_batch_candidates(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    older_than_days: int = 7,
    batch_limit: int = 50,
    resume_cursor: str | None = None,
) -> dict[str, Any]:
    normalized_older_than_days = max(7, int(older_than_days or 7))
    normalized_batch_limit = max(1, min(int(batch_limit or 50), 200))
    cutoff_time = now_utc() - timedelta(days=normalized_older_than_days)
    parsed_resume_cursor = _parse_task_resume_cursor(resume_cursor)

    query = (
        db.query(MessageAutomationTask)
        .options(joinedload(MessageAutomationTask.order))
        .filter(
            MessageAutomationTask.tenant_id == tenant_id,
            MessageAutomationTask.channel == "whatsapp",
            MessageAutomationTask.order_id.isnot(None),
            MessageAutomationTask.template_key == "review_request",
            MessageAutomationTask.status == PENDING,
            MessageAutomationTask.created_at < cutoff_time,
            or_(MessageAutomationTask.scheduled_at.is_(None), MessageAutomationTask.scheduled_at <= now_utc()),
        )
    )
    if parsed_resume_cursor:
        cursor_created_at, cursor_task_id = parsed_resume_cursor
        query = query.filter(
            or_(
                MessageAutomationTask.created_at > cursor_created_at,
                and_(
                    MessageAutomationTask.created_at == cursor_created_at,
                    MessageAutomationTask.id > cursor_task_id,
                ),
            )
        )

    total_matching = query.count()
    rows = query.order_by(MessageAutomationTask.created_at.asc(), MessageAutomationTask.id.asc()).limit(normalized_batch_limit + 1).all()
    has_more = len(rows) > normalized_batch_limit
    candidate_tasks = rows[:normalized_batch_limit]
    next_resume_cursor = _format_task_resume_cursor(candidate_tasks[-1]) if has_more and candidate_tasks else None
    return {
        "older_than_days": normalized_older_than_days,
        "batch_limit": normalized_batch_limit,
        "cutoff_time": cutoff_time,
        "resume_cursor_used": resume_cursor,
        "total_matching": total_matching,
        "has_more": has_more,
        "next_resume_cursor": next_resume_cursor,
        "tasks": candidate_tasks,
    }


def _latest_order_whatsapp_tasks(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    days: int = 7,
    limit: int = 200,
    event_type: str | None = None,
    template_keys: list[str] | None = None,
) -> tuple[list[MessageAutomationTask], dict[tuple[str | None, str, str], int]]:
    since_time = now_utc() - timedelta(days=max(1, days))
    query = (
        db.query(MessageAutomationTask)
        .options(joinedload(MessageAutomationTask.order))
        .filter(
            MessageAutomationTask.tenant_id == tenant_id,
            MessageAutomationTask.channel == "whatsapp",
            MessageAutomationTask.order_id.isnot(None),
            MessageAutomationTask.created_at >= since_time,
        )
    )
    if event_type:
        query = query.filter(MessageAutomationTask.event_type == str(event_type).strip())

    normalized_template_keys = sorted(
        {
            str(template_key).strip()
            for template_key in (template_keys or [])
            if str(template_key).strip()
        }
    )
    if normalized_template_keys:
        query = query.filter(MessageAutomationTask.template_key.in_(normalized_template_keys))

    tasks = query.order_by(MessageAutomationTask.created_at.desc()).all()

    latest_tasks: list[MessageAutomationTask] = []
    duplicate_counts: dict[tuple[str | None, str, str], int] = {}
    seen: set[tuple[str | None, str, str]] = set()
    for task in tasks:
        key = (str(task.order_id) if task.order_id else None, task.template_key, task.event_type)
        duplicate_counts[key] = duplicate_counts.get(key, 0) + 1
        if key in seen:
            continue
        seen.add(key)
        latest_tasks.append(task)
        if len(latest_tasks) >= limit:
            break

    return latest_tasks, duplicate_counts


def list_order_whatsapp_logs(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    days: int = 7,
    limit: int = 200,
    event_type: str | None = None,
    template_key: str | None = None,
) -> list[dict[str, Any]]:
    settings_row = get_or_create_settings(db, tenant_id)
    latest_tasks, duplicate_counts = _latest_order_whatsapp_tasks(
        db,
        tenant_id,
        days=days,
        limit=limit,
        event_type=event_type,
        template_keys=[template_key] if template_key else None,
    )

    return [
        _message_task_log_dict(
            task,
            duplicate_count=duplicate_counts[(str(task.order_id) if task.order_id else None, task.template_key, task.event_type)],
            settings_row=settings_row,
        )
        for task in latest_tasks
    ]


def preview_historical_review_request_batch(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    older_than_days: int = 7,
    batch_limit: int = 50,
    resume_cursor: str | None = None,
) -> dict[str, Any]:
    batch = _historical_review_request_batch_candidates(
        db,
        tenant_id,
        older_than_days=older_than_days,
        batch_limit=batch_limit,
        resume_cursor=resume_cursor,
    )
    candidate_tasks = batch["tasks"]
    preview_count = len(candidate_tasks)
    required_confirmation_phrase = f"RETRY {preview_count} REVIEW REQUESTS" if preview_count else None
    remaining_after_this_batch = max(0, int(batch["total_matching"]) - preview_count)

    if not preview_count:
        message = "No pending review requests older than the selected age were found for the current batch scope"
    else:
        message = (
            f"Previewing {preview_count} pending historical review request(s) older than {batch['older_than_days']} day(s)"
        )

    return {
        "success": True,
        "message": message,
        "older_than_days": batch["older_than_days"],
        "batch_limit": batch["batch_limit"],
        "resume_cursor_used": batch["resume_cursor_used"],
        "next_resume_cursor": batch["next_resume_cursor"],
        "has_more": batch["has_more"],
        "total_matching": batch["total_matching"],
        "remaining_after_this_batch": remaining_after_this_batch,
        "preview_count": preview_count,
        "required_confirmation_phrase": required_confirmation_phrase,
        "counts_by_template": {"review_request": preview_count} if preview_count else {},
        "candidates": [_historical_review_request_candidate_dict(task) for task in candidate_tasks],
    }


def _reset_task_for_immediate_retry(task: MessageAutomationTask) -> None:
    task.status = PENDING
    task.scheduled_at = now_utc()
    task.next_retry_at = None
    task.cancelled_at = None
    task.sent_at = None
    task.error_reason = None
    task.provider_message_id = None
    task.provider_response = None
    if (task.attempts or 0) >= (task.max_attempts or 3):
        task.attempts = 0


def _order_whatsapp_badge_variant(status_label: str, *, action_required: bool) -> str:
    if action_required:
        return "red"
    return {
        "accepted": "green",
        "pending": "blue",
        "blocked": "amber",
        "cancelled": "amber",
        "failed": "red",
        "stopped": "gray",
        "skipped": "gray",
    }.get(status_label, "gray")


def _order_whatsapp_step_badge_label(template_key: str, status_label: str) -> str:
    label = ORDER_WHATSAPP_JOURNEY_LABELS.get(template_key, template_key.replace("_", " ").title())
    if status_label == "accepted":
        return f"{label} ✓"
    if status_label == "pending":
        return f"{label} Pending"
    if status_label == "blocked":
        return f"{label} Blocked"
    if status_label == "cancelled":
        return f"{label} Cancelled"
    if status_label == "failed":
        return f"{label} Failed"
    if status_label == "stopped":
        return f"{label} Stopped"
    if status_label == "skipped":
        return f"{label} Skipped"
    return label


def get_order_whatsapp_journey_map(
    db: Session,
    tenant_id: uuid.UUID,
    order_ids: list[uuid.UUID],
) -> dict[str, dict[str, Any]]:
    unique_order_ids = list(dict.fromkeys(order_ids))
    if not unique_order_ids:
        return {}

    settings_row = get_or_create_settings(db, tenant_id)
    tasks = (
        db.query(MessageAutomationTask)
        .filter(
            MessageAutomationTask.tenant_id == tenant_id,
            MessageAutomationTask.channel == "whatsapp",
            MessageAutomationTask.order_id.in_(unique_order_ids),
            MessageAutomationTask.template_key.in_(ORDER_WHATSAPP_JOURNEY_KEYS),
        )
        .order_by(MessageAutomationTask.created_at.desc())
        .all()
    )

    latest_by_key: dict[tuple[str, str], MessageAutomationTask] = {}
    duplicate_counts: dict[tuple[str, str], int] = {}
    for task in tasks:
        if not task.order_id:
            continue
        order_key = str(task.order_id)
        group_key = (order_key, task.template_key)
        duplicate_counts[group_key] = duplicate_counts.get(group_key, 0) + 1
        latest_by_key.setdefault(group_key, task)

    journeys: dict[str, dict[str, Any]] = {}
    for order_id in unique_order_ids:
        order_key = str(order_id)
        steps: list[dict[str, Any]] = []
        for template_key in ORDER_WHATSAPP_JOURNEY_KEYS:
            group_key = (order_key, template_key)
            task = latest_by_key.get(group_key)
            if not task:
                continue

            task_log = _message_task_log_dict(
                task,
                duplicate_count=duplicate_counts.get(group_key, 1),
                settings_row=settings_row,
            )
            status_label = task_log.get("status_label") or "unknown"
            action_required = bool(task_log.get("action_required"))
            step = {
                "key": template_key,
                "label": ORDER_WHATSAPP_JOURNEY_LABELS.get(template_key, template_key.replace("_", " ").title()),
                "badge_label": _order_whatsapp_step_badge_label(template_key, status_label),
                "badge_variant": _order_whatsapp_badge_variant(status_label, action_required=action_required),
                "status_label": status_label,
                "status_detail": task_log.get("status_detail"),
                "issue_summary": task_log.get("issue_summary"),
                "action_required": action_required,
                "sent_at": task_log.get("sent_at"),
                "created_at": task_log.get("created_at"),
                "_sort_at": task_log.get("sent_at") or task_log.get("created_at") or "",
            }
            steps.append(step)

        if not steps:
            continue

        steps.sort(key=lambda step: step.get("_sort_at") or "", reverse=True)
        latest_step = steps[0]
        sent_count = sum(1 for step in steps if step.get("status_label") == "accepted")
        pending_count = sum(1 for step in steps if step.get("status_label") in {"pending", "blocked"})
        issue_count = sum(1 for step in steps if step.get("action_required"))

        summary_parts = []
        if sent_count:
            summary_parts.append(f"{sent_count} sent")
        if pending_count:
            summary_parts.append(f"{pending_count} pending")
        if issue_count:
            summary_parts.append(f"{issue_count} need attention")

        journeys[order_key] = {
            "badge_label": f"WA {latest_step['badge_label']}",
            "badge_variant": latest_step["badge_variant"],
            "latest_template_key": latest_step["key"],
            "latest_status_label": latest_step["status_label"],
            "sent_count": sent_count,
            "pending_count": pending_count,
            "issue_count": issue_count,
            "summary": "WhatsApp journey: " + ", ".join(summary_parts) if summary_parts else "WhatsApp automation activity logged for this order.",
            "steps": [
                {
                    key: value
                    for key, value in step.items()
                    if key != "_sort_at"
                }
                for step in steps
            ],
        }

    return journeys


async def send_order_created_test_batch(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    limit: int = 200,
    target_date: date | None = None,
) -> dict[str, Any]:
    settings_row = get_or_create_settings(db, tenant_id)
    if not settings_row.is_enabled:
        return {
            "success": False,
            "message": "Message automation is disabled.",
            "matched_orders": 0,
            "results": [],
        }

    local_date, start_time, end_time = _india_day_bounds(target_date)
    orders = (
        db.query(Order)
        .options(joinedload(Order.customer), joinedload(Order.items))
        .filter(
            Order.tenant_id == tenant_id,
            Order.is_active.is_(True),
            Order.status == OrderStatus.confirmed,
            Order.created_at >= start_time,
            Order.created_at < end_time,
        )
        .order_by(Order.created_at.asc())
        .limit(limit)
        .all()
    )

    batch_id = now_utc().strftime("%Y%m%d%H%M%S")
    sent_count = 0
    failed_count = 0
    cancelled_count = 0
    skipped_count = 0
    results: list[dict[str, Any]] = []

    for order_row in orders:
        variables = _order_variables(db, order_row)
        subject, body = _render_template("order_created", variables)
        task = MessageAutomationTask(
            tenant_id=tenant_id,
            customer_id=order_row.customer_id,
            order_id=order_row.id,
            channel="whatsapp",
            template_key="order_created",
            event_type="manual_test_order_created",
            status=PENDING,
            recipient_phone_e164=normalize_phone_e164(_order_phone(order_row)) or None,
            recipient_name=variables.get("customer_name"),
            subject=subject,
            body=body,
            payload=variables,
            dedupe_key=f"order:{order_row.id}:manual_test_order_created:{batch_id}",
            scheduled_at=now_utc(),
            max_attempts=1,
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        try:
            if not task.recipient_phone_e164:
                task.status = FAILED
                task.error_reason = "No customer phone number is available on this order"
                failed_count += 1
            elif _task_blocked_by_preference(db, task):
                task.status = CANCELLED
                task.cancelled_at = now_utc()
                task.error_reason = "Customer messaging preference is paused or opted out"
                cancelled_count += 1
            else:
                task.attempts = 1
                result = await _send_task(db, task)
                if result.get("success"):
                    task.status = SENT
                    task.sent_at = now_utc()
                    task.provider_message_id = result.get("provider_message_id")
                    task.provider_response = result
                    task.error_reason = None
                    order_row.wa_confirmed_sent = True
                    sent_count += 1
                elif result.get("skipped"):
                    task.status = SKIPPED
                    task.provider_response = result
                    task.error_reason = result.get("message")
                    skipped_count += 1
                else:
                    task.status = FAILED
                    task.provider_response = result
                    task.error_reason = result.get("message") or "WhatsApp send failed"
                    failed_count += 1

            db.commit()
        except Exception as exc:
            db.rollback()
            persisted_task = db.query(MessageAutomationTask).filter(MessageAutomationTask.id == task.id).first()
            if persisted_task:
                persisted_task.attempts = max(persisted_task.attempts or 0, 1)
                persisted_task.status = FAILED
                persisted_task.error_reason = str(exc)
                persisted_task.provider_response = {"success": False, "message": str(exc)}
                db.commit()
                task = persisted_task
            failed_count += 1

        logged_task = (
            db.query(MessageAutomationTask)
            .options(joinedload(MessageAutomationTask.order))
            .filter(MessageAutomationTask.id == task.id)
            .first()
        )
        if logged_task is not None:
            results.append(_message_task_log_dict(logged_task))

    return {
        "success": True,
        "batch_id": batch_id,
        "local_date": local_date.isoformat(),
        "matched_orders": len(orders),
        "sent_count": sent_count,
        "failed_count": failed_count,
        "cancelled_count": cancelled_count,
        "skipped_count": skipped_count,
        "results": results,
    }


# ---------------------------------------------------------------------------
# Admin listing helpers
# ---------------------------------------------------------------------------

def list_tasks(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    status: str | None = None,
    limit: int = 100,
) -> list[MessageAutomationTask]:
    query = db.query(MessageAutomationTask).filter(MessageAutomationTask.tenant_id == tenant_id)
    if status:
        query = query.filter(MessageAutomationTask.status == status)
    return query.order_by(MessageAutomationTask.scheduled_at.desc()).limit(limit).all()


def release_tasks(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    template_keys: list[str] | None = None,
    statuses: list[str] | None = None,
    release_pending_only: bool = False,
) -> dict[str, Any]:
    normalized_statuses = [str(status).strip().lower() for status in (statuses or [PENDING, FAILED]) if str(status).strip()]
    query = db.query(MessageAutomationTask).filter(MessageAutomationTask.tenant_id == tenant_id)

    if template_keys:
        query = query.filter(MessageAutomationTask.template_key.in_(template_keys))
    if normalized_statuses:
        query = query.filter(MessageAutomationTask.status.in_(normalized_statuses))
    if release_pending_only:
        query = query.filter(MessageAutomationTask.scheduled_at <= now_utc())

    tasks = query.all()
    for task in tasks:
        task.status = PENDING
        task.next_retry_at = None
        task.error_reason = None if task.status == PENDING else task.error_reason
    db.flush()
    return {
        "success": True,
        "released": len(tasks),
        "template_keys": template_keys or [],
        "statuses": normalized_statuses,
    }


async def retry_order_whatsapp_task_now(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    order_id: uuid.UUID,
    template_key: str,
) -> dict[str, Any]:
    normalized_template_key = str(template_key or "").strip()
    if not normalized_template_key:
        raise ValueError("template_key is required")

    task = (
        db.query(MessageAutomationTask)
        .filter(
            MessageAutomationTask.tenant_id == tenant_id,
            MessageAutomationTask.order_id == order_id,
            MessageAutomationTask.channel == "whatsapp",
            MessageAutomationTask.template_key == normalized_template_key,
        )
        .order_by(MessageAutomationTask.created_at.desc())
        .first()
    )
    if task is None:
        raise ValueError("No WhatsApp automation task exists for this order and step")
    if task.status == SENT:
        raise ValueError("This WhatsApp step has already been sent")

    _reset_task_for_immediate_retry(task)

    processed = await _process_single_task(db, task)
    return {
        "success": processed.get("outcome") == "sent",
        "message": (processed.get("result") or {}).get("message") or task.error_reason or "Task processed",
        "outcome": processed.get("outcome"),
        "template_key": normalized_template_key,
        "task": task_to_dict(task),
    }


async def retry_pending_order_whatsapp_tasks_now(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    days: int = 7,
    limit: int = 200,
    template_keys: list[str] | None = None,
    task_ids: list[uuid.UUID] | None = None,
) -> dict[str, Any]:
    normalized_template_keys = sorted(
        {
            str(template_key).strip()
            for template_key in (template_keys or [])
            if str(template_key).strip()
        }
    )
    normalized_task_ids = [task_id for task_id in (task_ids or []) if task_id]

    if normalized_task_ids:
        query = (
            db.query(MessageAutomationTask)
            .options(joinedload(MessageAutomationTask.order))
            .filter(
                MessageAutomationTask.tenant_id == tenant_id,
                MessageAutomationTask.channel == "whatsapp",
                MessageAutomationTask.order_id.isnot(None),
                MessageAutomationTask.id.in_(normalized_task_ids),
            )
        )
        tasks_by_id = {task.id: task for task in query.all()}
        pending_tasks = [
            tasks_by_id[task_id]
            for task_id in normalized_task_ids
            if task_id in tasks_by_id and tasks_by_id[task_id].status in {PENDING, FAILED}
        ]
        scope_message = "selected order-linked WhatsApp step(s)"
    else:
        latest_tasks, _ = _latest_order_whatsapp_tasks(
            db,
            tenant_id,
            days=days,
            limit=limit,
            template_keys=normalized_template_keys,
        )
        pending_tasks = [task for task in latest_tasks if task.status == PENDING]
        pending_tasks.sort(key=lambda task: (task.scheduled_at or task.created_at or now_utc(), task.created_at or now_utc()))
        scope_message = "pending order-linked WhatsApp step(s)"

    if not pending_tasks:
        return {
            "success": True,
            "message": "No retryable order-linked WhatsApp steps found in the requested scope",
            "days": days,
            "limit": limit,
            "template_keys": normalized_template_keys,
            "task_ids": [str(task_id) for task_id in normalized_task_ids],
            "processed": 0,
            "sent": 0,
            "pending": 0,
            "failed": 0,
            "cancelled": 0,
            "skipped": 0,
            "results": [],
        }

    results: list[dict[str, Any]] = []
    for task in pending_tasks:
        order_number = getattr(getattr(task, "order", None), "order_number", None)
        try:
            result = await retry_order_whatsapp_task_now(
                db,
                tenant_id,
                order_id=task.order_id,
                template_key=task.template_key,
            )
            task_status = (result.get("task") or {}).get("status") or task.status
            results.append(
                {
                    "task_id": str(task.id),
                    "order_id": str(task.order_id) if task.order_id else None,
                    "order_number": order_number,
                    "template_key": task.template_key,
                    "success": bool(result.get("success")),
                    "outcome": result.get("outcome"),
                    "status": task_status,
                    "message": result.get("message"),
                }
            )
        except ValueError as exc:
            results.append(
                {
                    "task_id": str(task.id),
                    "order_id": str(task.order_id) if task.order_id else None,
                    "order_number": order_number,
                    "template_key": task.template_key,
                    "success": False,
                    "outcome": "failed",
                    "status": task.status,
                    "message": str(exc),
                }
            )

    sent = sum(1 for item in results if item.get("status") == SENT)
    still_pending = sum(1 for item in results if item.get("status") == PENDING)
    failed = sum(1 for item in results if item.get("status") == FAILED)
    cancelled = sum(1 for item in results if item.get("status") == CANCELLED)
    skipped = sum(1 for item in results if item.get("status") == SKIPPED)

    parts = [f"Processed {len(results)} {scope_message}", f"{sent} sent"]
    if still_pending:
        parts.append(f"{still_pending} still pending")
    if failed:
        parts.append(f"{failed} failed")
    if cancelled:
        parts.append(f"{cancelled} cancelled")
    if skipped:
        parts.append(f"{skipped} skipped")

    return {
        "success": failed == 0 and still_pending == 0,
        "message": ", ".join(parts),
        "days": days,
        "limit": limit,
        "template_keys": normalized_template_keys,
        "task_ids": [str(task_id) for task_id in normalized_task_ids],
        "processed": len(results),
        "sent": sent,
        "pending": still_pending,
        "failed": failed,
        "cancelled": cancelled,
        "skipped": skipped,
        "results": results,
    }


async def retry_historical_review_request_batch_now(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    older_than_days: int = 7,
    batch_limit: int = 50,
    resume_cursor: str | None = None,
    confirmation_phrase: str | None = None,
) -> dict[str, Any]:
    batch = _historical_review_request_batch_candidates(
        db,
        tenant_id,
        older_than_days=older_than_days,
        batch_limit=batch_limit,
        resume_cursor=resume_cursor,
    )
    candidate_tasks: list[MessageAutomationTask] = batch["tasks"]
    preview_count = len(candidate_tasks)

    if not preview_count:
        return {
            "success": True,
            "message": "No pending historical review requests remain in the selected batch scope",
            "older_than_days": batch["older_than_days"],
            "batch_limit": batch["batch_limit"],
            "resume_cursor_used": batch["resume_cursor_used"],
            "next_resume_cursor": None,
            "has_more": False,
            "total_matching": 0,
            "processed": 0,
            "sent": 0,
            "pending": 0,
            "failed": 0,
            "cancelled": 0,
            "skipped": 0,
            "results": [],
        }

    expected_confirmation_phrase = f"RETRY {preview_count} REVIEW REQUESTS"
    if str(confirmation_phrase or "").strip() != expected_confirmation_phrase:
        raise ValueError(f"Confirmation phrase must match exactly: {expected_confirmation_phrase}")

    results: list[dict[str, Any]] = []
    for task in candidate_tasks:
        order_number = getattr(getattr(task, "order", None), "order_number", None)
        _reset_task_for_immediate_retry(task)
        processed = await _process_single_task(db, task)
        results.append(
            {
                "task_id": str(task.id),
                "order_id": str(task.order_id) if task.order_id else None,
                "order_number": order_number,
                "template_key": task.template_key,
                "outcome": processed.get("outcome"),
                "status": task.status,
                "message": (processed.get("result") or {}).get("message") or task.error_reason or "Task processed",
            }
        )

    sent = sum(1 for item in results if item.get("status") == SENT)
    still_pending = sum(1 for item in results if item.get("status") == PENDING)
    failed = sum(1 for item in results if item.get("status") == FAILED)
    cancelled = sum(1 for item in results if item.get("status") == CANCELLED)
    skipped = sum(1 for item in results if item.get("status") == SKIPPED)
    remaining_after_this_batch = max(0, int(batch["total_matching"]) - preview_count)

    parts = [f"Processed {preview_count} historical review request(s)", f"{sent} sent"]
    if still_pending:
        parts.append(f"{still_pending} still pending")
    if failed:
        parts.append(f"{failed} failed")
    if cancelled:
        parts.append(f"{cancelled} cancelled")
    if skipped:
        parts.append(f"{skipped} skipped")
    if batch["has_more"]:
        parts.append(f"{remaining_after_this_batch} more remain in later batches")

    return {
        "success": failed == 0 and still_pending == 0,
        "message": ", ".join(parts),
        "older_than_days": batch["older_than_days"],
        "batch_limit": batch["batch_limit"],
        "resume_cursor_used": batch["resume_cursor_used"],
        "next_resume_cursor": batch["next_resume_cursor"],
        "has_more": batch["has_more"],
        "total_matching": batch["total_matching"],
        "remaining_after_this_batch": remaining_after_this_batch,
        "processed": preview_count,
        "sent": sent,
        "pending": still_pending,
        "failed": failed,
        "cancelled": cancelled,
        "skipped": skipped,
        "results": results,
    }


def task_to_dict(task: MessageAutomationTask) -> dict[str, Any]:
    return {
        "id": str(task.id),
        "tenant_id": str(task.tenant_id),
        "customer_id": str(task.customer_id) if task.customer_id else None,
        "order_id": str(task.order_id) if task.order_id else None,
        "channel": task.channel,
        "template_key": task.template_key,
        "event_type": task.event_type,
        "status": task.status,
        "recipient_phone_e164": task.recipient_phone_e164,
        "recipient_email": task.recipient_email,
        "recipient_name": task.recipient_name,
        "subject": task.subject,
        "scheduled_at": task.scheduled_at.isoformat() if task.scheduled_at else None,
        "sent_at": task.sent_at.isoformat() if task.sent_at else None,
        "attempts": task.attempts,
        "error_reason": task.error_reason,
    }


def settings_to_dict(settings_row: MessageAutomationSetting, db: Session) -> dict[str, Any]:
    links = _derive_links(db, settings_row.tenant_id, settings_row)
    return {
        "id": str(settings_row.id),
        "tenant_id": str(settings_row.tenant_id),
        "is_enabled": settings_row.is_enabled,
        "website_url": links["website_url"],
        "google_review_url": links["google_review_url"],
        "business_whatsapp_phone": links["business_whatsapp_phone"],
        "meta_template_asset_id": _normalize_meta_template_asset_id(settings_row.meta_template_asset_id),
        "template_bindings": resolved_template_bindings(settings_row),
        "template_header_media_urls": resolved_template_header_media_urls(settings_row),
        "whatsapp_link": links["whatsapp_link"],
        "review_campaign_started_at": settings_row.review_campaign_started_at.isoformat() if settings_row.review_campaign_started_at else None,
        "updated_at": settings_row.updated_at.isoformat() if settings_row.updated_at else None,
    }
