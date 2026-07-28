from __future__ import annotations

import logging
import re
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from typing import Any, Iterable, Optional
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.shipping.india_post_client import IndiaPostAPIClient
from app.core.shipping.india_post_portal_client import IndiaPostPortalClient
from app.models.customer import Customer
from app.models.employee import Employee
from app.models.order import (
    Order,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    OrderStatusHistory,
)
from app.models.shipping_config import DeliveryPartner
from app.modules.shipping_config import service as shipping_config_service

log = logging.getLogger(__name__)

TERMINAL_STATUSES = {OrderStatus.cancelled, OrderStatus.returned}
FINAL_STATUSES = {OrderStatus.delivered, OrderStatus.cancelled, OrderStatus.returned}
STATUS_RANK = {
    OrderStatus.draft: 0,
    OrderStatus.confirmed: 1,
    OrderStatus.processing: 2,
    OrderStatus.packed: 3,
    OrderStatus.shipped: 4,
    OrderStatus.out_for_delivery: 5,
    OrderStatus.delivered: 6,
    OrderStatus.returned: 7,
    OrderStatus.cancelled: 8,
}


def _digits(value: Any) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _phone_key(value: Any) -> str:
    digits = _digits(value)
    if len(digits) >= 10:
        return digits[-10:]
    return digits


def _clean_tracking(value: Any) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", str(value or "")).upper()


def _clean_name(value: Any) -> str:
    return re.sub(r"[^A-Za-z0-9 ]", " ", str(value or "").upper()).strip()


def _name_key(value: Any) -> str:
    return " ".join(_clean_name(value).split())


def _first(data: dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return None


def _deep_first(data: Any, keys: Iterable[str]) -> Any:
    if isinstance(data, dict):
        direct = _first(data, keys)
        if direct not in (None, ""):
            return direct
        for value in data.values():
            found = _deep_first(value, keys)
            if found not in (None, ""):
                return found
    elif isinstance(data, list):
        for value in data:
            found = _deep_first(value, keys)
            if found not in (None, ""):
                return found
    return None


def _parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    for candidate in (
        text,
        text.replace("Z", "+00:00"),
        text.replace(" ", "T"),
        text.replace(" ", "T").replace("Z", "+00:00"),
    ):
        try:
            parsed = datetime.fromisoformat(candidate)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d-%m-%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    for fmt in ("%Y/%m/%dT%H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _parse_money(value: Any) -> Optional[Decimal]:
    if value in (None, ""):
        return None
    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.01"))
    text = re.sub(r"[^0-9.\-]", "", str(value))
    if not text or text in (".", "-", "-."):
        return None
    try:
        return Decimal(text).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def _map_tracking_status(status_text: str) -> tuple[str, Optional[OrderStatus], Optional[str]]:
    text = (status_text or "").strip()
    lower = text.lower()
    if any(token in lower for token in ("rto", "return to sender", "returned", "return item", "returned to sender")):
        return "returned", OrderStatus.returned, text or "Returned"
    if "deliver" in lower and "not deliver" not in lower and "undeliver" not in lower and "out for" not in lower:
        return "delivered", OrderStatus.delivered, None
    if "out for delivery" in lower or "ofd" == lower:
        return "out_for_delivery", OrderStatus.out_for_delivery, None
    if any(token in lower for token in ("booked", "bagged", "dispatched", "transit", "received", "item received", "picked", "article")):
        return "in_transit", OrderStatus.shipped, None
    if any(token in lower for token in ("cancel", "void")):
        return "cancelled", OrderStatus.cancelled, None
    if not lower:
        return "pending", None, None
    return "in_transit", OrderStatus.shipped, None


def _normalize_portal_booking_row(row: dict[str, Any]) -> dict[str, Any]:
    article = _clean_tracking(_first(row, ("article-number", "articleNumber", "article_number")))
    status_text = str(_first(row, ("event-description", "eventDescription", "status", "status_text")) or "")
    mapped_status, order_status, return_status = _map_tracking_status(status_text)
    booked_at = _parse_datetime(_first(row, ("booking-date-time", "bookingDateTime", "booking_date_time")))
    location = _first(row, ("destination-office-name", "destinationOfficeName", "booking-office-name", "bookingOfficeName")) or ""
    cost = _parse_money(_first(row, ("tarrif", "tariff", "totalCharge", "base-amount", "baseAmount")))
    pincode = _digits(_first(row, ("destination-pin", "destinationPin", "deliveryPincode", "receiverPincode")))
    receiver_name = _name_key(_first(row, ("receiver-name", "receiverName", "recipientName")))
    phone = _phone_key(_first(row, ("receiver-mobile", "receiverMobile", "mobile", "phone")))
    event = {
        "status": mapped_status,
        "status_text": status_text,
        "location": str(location or ""),
        "description": status_text,
        "time": booked_at.isoformat() if booked_at else None,
        "raw": row,
    }
    return {
        "tracking_number": article,
        "status": mapped_status,
        "order_status": order_status,
        "status_text": status_text,
        "location": str(location or ""),
        "last_event_at": booked_at,
        "events": [event] if status_text or booked_at else [],
        "actual_shipping_cost": cost,
        "return_status": return_status,
        "phone_key": phone,
        "pincode": pincode,
        "receiver_name_key": receiver_name,
        "raw": {"source": "india_post_portal_booking_report", "row": row},
    }


def _extract_event_list(raw: Any) -> list[Any]:
    def nested_tracking_events(items: list[Any]) -> list[Any]:
        nested_events: list[Any] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            nested = item.get("tracking_details") or item.get("trackingDetails") or item.get("trackDetails")
            if isinstance(nested, list):
                nested_events.extend(nested)
        return nested_events

    if isinstance(raw, dict):
        for key in (
            "events",
            "history",
            "tracking_history",
            "trackingHistory",
            "tracking_details",
            "trackingDetails",
            "trackDetails",
            "eventList",
            "scans",
        ):
            value = raw.get(key)
            if isinstance(value, list):
                return nested_tracking_events(value) or value
        data = raw.get("data")
        if isinstance(data, (dict, list)):
            nested = _extract_event_list(data)
            if nested:
                return nested
    elif isinstance(raw, list):
        return nested_tracking_events(raw) or raw
    return []


def _normalize_event(event: Any) -> dict[str, Any]:
    if not isinstance(event, dict):
        return {"description": str(event), "status": "in_transit"}
    status_text = str(_first(event, ("status_text", "status", "eventStatus", "event", "currentStatus", "scan", "description", "remarks")) or "")
    mapped_status, _, _ = _map_tracking_status(status_text)
    event_time = _parse_datetime(_first(event, ("date", "time", "eventTime", "event_time", "scanDate", "timestamp", "createdAt")))
    location = _first(event, ("location", "office", "officeName", "currentLocation", "city", "hub", "facility", "locationName"))
    description = _first(event, ("description", "detail", "remarks", "event", "scan", "status_text", "status"))
    return {
        "status": mapped_status,
        "status_text": status_text or str(description or ""),
        "location": str(location or ""),
        "description": str(description or status_text or ""),
        "time": event_time.isoformat() if event_time else None,
        "raw": event,
    }


def normalize_india_post_tracking(raw: Any, tracking_number: str | None = None) -> dict[str, Any]:
    payload = raw or {}
    if isinstance(payload, dict) and (
        "article-number" in payload
        or "booking-date-time" in payload
        or payload.get("_source") == "portal_booking_report"
    ):
        tracking = _normalize_portal_booking_row(payload)
        if tracking_number and not tracking.get("tracking_number"):
            tracking["tracking_number"] = _clean_tracking(tracking_number)
        return tracking

    data = payload.get("data", payload) if isinstance(payload, dict) else payload
    if isinstance(data, list) and data:
        data = data[0]
    if not isinstance(data, dict):
        data = {}

    article = _clean_tracking(
        tracking_number
        or _deep_first(data, ("tracking_number", "trackingNumber", "articleNumber", "article_number", "consignmentNumber", "consignment_no", "awb", "barcode"))
        or _deep_first(payload, ("tracking_number", "trackingNumber", "articleNumber", "article_number", "consignmentNumber", "consignment_no", "awb", "barcode"))
    )
    status_value = _deep_first(
        data,
        ("status_text", "currentStatus", "current_status", "status", "deliveryStatus", "eventStatus", "latestStatus"),
    )
    if isinstance(payload, dict) and status_value in (None, ""):
        status_value = payload.get("status_text") or payload.get("status")
    status_text = str(status_value or "")

    events = [_normalize_event(event) for event in _extract_event_list(payload) or _extract_event_list(data)]
    events.sort(key=lambda event: event.get("time") or "", reverse=True)
    latest_event = events[0] if events else {}
    if latest_event.get("status_text"):
        status_text = str(latest_event.get("status_text") or status_text)

    mapped_status, order_status, return_status = _map_tracking_status(status_text)
    location = (
        _deep_first(data, ("currentLocation", "current_location", "lastLocation", "location", "officeName", "currentOffice", "deliveryOffice", "delivery_location"))
        or latest_event.get("location")
        or ""
    )
    event_time = _parse_datetime(
        _deep_first(data, ("lastUpdate", "last_update", "eventTime", "event_time", "statusDate", "updatedAt", "delivery_confirmed_on"))
    )
    if not event_time and latest_event.get("time"):
        event_time = _parse_datetime(latest_event.get("time"))

    cost = _parse_money(
        _deep_first(data, ("actual_shipping_cost", "actualShippingCost", "totalCharge", "total_charges", "chargedAmount", "postage", "tariff", "tarrif", "freight", "amount", "bookingAmount"))
    )
    pincode = _digits(
        _deep_first(data, ("pincode", "destinationPincode", "destination_pincode", "deliveryPincode", "receiverPincode", "recipientPincode", "addresseePincode"))
    )
    phone = _phone_key(
        _deep_first(data, ("phone", "mobile", "receiverMobile", "recipientMobile", "addresseeMobile", "customerPhone", "consigneeMobile"))
    )
    explicit_return = _deep_first(data, ("returnStatus", "return_status", "rtoStatus", "rtsStatus"))
    if explicit_return:
        return_status = str(explicit_return)

    return {
        "tracking_number": article,
        "status": mapped_status,
        "order_status": order_status,
        "status_text": status_text or latest_event.get("status_text") or "",
        "location": str(location or ""),
        "last_event_at": event_time,
        "events": events,
        "actual_shipping_cost": cost,
        "return_status": return_status,
        "phone_key": phone,
        "pincode": pincode,
        "raw": payload,
    }


def order_tracking_snapshot(order: Order) -> dict[str, Any]:
    tracking = normalize_india_post_tracking(order.tracking_raw_response or {}, order.tracking_number)
    if order.tracking_status_text:
        tracking["status_text"] = order.tracking_status_text
    if order.tracking_last_location:
        tracking["location"] = order.tracking_last_location
    if order.tracking_last_event_at:
        tracking["last_event_at"] = order.tracking_last_event_at
    if order.tracking_events_json:
        tracking["events"] = order.tracking_events_json
    if order.actual_shipping_cost is not None:
        tracking["actual_shipping_cost"] = order.actual_shipping_cost
    if order.return_status:
        tracking["return_status"] = order.return_status
    if order.tracking_number:
        tracking["tracking_number"] = order.tracking_number
    if not tracking.get("status_text") and order.status:
        tracking["status_text"] = order.status.value.replace("_", " ")
    return tracking


def _india_post_partner(db: Session, tenant_id: UUID) -> Optional[DeliveryPartner]:
    return (
        db.query(DeliveryPartner)
        .filter(
            DeliveryPartner.tenant_id == tenant_id,
            DeliveryPartner.partner_type == "india_post",
            DeliveryPartner.is_active == True,
        )
        .order_by(DeliveryPartner.is_primary.desc(), DeliveryPartner.updated_at.desc().nullslast())
        .first()
    )


def _client_for_partner(partner: DeliveryPartner) -> IndiaPostAPIClient:
    username = partner.client_id or ""
    password = shipping_config_service.decrypt_credential(partner.api_key) if partner.api_key else ""
    customer_id = (partner.customer_ids[0]["id"] if partner.customer_ids else "") or ""
    use_sandbox = (partner.client_name or "sandbox") != "production"
    return IndiaPostAPIClient(
        username=username,
        password=password,
        customer_id=customer_id,
        sandbox=use_sandbox,
    )


def _is_india_post_order(order: Order, partner: DeliveryPartner | None = None) -> bool:
    if partner and order.shipping_partner_id == partner.id:
        return True
    courier_name = (order.courier_name or "").lower()
    courier_code = (order.courier_code or "").lower()
    return bool(
        "india" in courier_name and "post" in courier_name
        or "india_post" in courier_code
        or order.india_post_customer_id
        or order.shipping_service
    )


def _should_change_status(old_status: OrderStatus, new_status: Optional[OrderStatus]) -> bool:
    if not new_status or old_status == new_status:
        return False
    if old_status == OrderStatus.cancelled:
        return False
    if new_status == OrderStatus.returned:
        return old_status != OrderStatus.returned
    if old_status in TERMINAL_STATUSES:
        return False
    if old_status == OrderStatus.delivered:
        return False
    return STATUS_RANK.get(new_status, 0) > STATUS_RANK.get(old_status, 0)


def _order_phone_key(order: Order) -> str:
    return _phone_key(order.customer.phone if order.customer and order.customer.phone else order.delivery_phone2)


def _order_name_keys(order: Order) -> set[str]:
    keys = {
        _name_key(order.delivery_name),
        _name_key(order.customer.name if order.customer else None),
    }
    return {key for key in keys if key}


def _name_match_score(portal_name: str, order: Order) -> float:
    if not portal_name:
        return 0.0
    scores = []
    portal_tokens = set(portal_name.split())
    for candidate in _order_name_keys(order):
        candidate_tokens = set(candidate.split())
        if not candidate_tokens:
            continue
        token_score = len(portal_tokens & candidate_tokens) / max(len(portal_tokens), len(candidate_tokens), 1)
        ratio = SequenceMatcher(None, portal_name, candidate).ratio()
        scores.append(max(token_score, ratio))
    return max(scores, default=0.0)


def _portal_name_supports_order(portal_name: str, order: Order) -> bool:
    if not portal_name:
        return False

    portal_tokens = set(portal_name.split())
    for candidate in _order_name_keys(order):
        candidate_tokens = set(candidate.split())
        if not candidate_tokens:
            continue
        if portal_tokens & candidate_tokens:
            return True
        for portal_token in portal_tokens:
            for candidate_token in candidate_tokens:
                if len(portal_token) >= 3 and len(candidate_token) >= 3:
                    if portal_token in candidate_token or candidate_token in portal_token:
                        return True

    return _name_match_score(portal_name, order) >= 0.5


def _is_booking_date_plausible(order: Order, booking_at: datetime | None) -> bool:
    if not booking_at or not order.created_at:
        return True
    created_at = order.created_at if order.created_at.tzinfo else order.created_at.replace(tzinfo=timezone.utc)
    return created_at - timedelta(hours=12) <= booking_at <= created_at + timedelta(days=5)


def _match_portal_row_to_missing_order(
    tracking: dict[str, Any],
    missing_orders: list[Order],
    used_order_ids: set[UUID],
) -> Order | None:
    article = tracking.get("tracking_number")
    pincode = tracking.get("pincode") or ""
    if not article or not pincode:
        return None

    booking_at = tracking.get("last_event_at")
    candidates = [
        order
        for order in missing_orders
        if order.id not in used_order_ids
        and _digits(order.delivery_pincode) == pincode
        and order.printed_count > 0
        and _is_booking_date_plausible(order, booking_at)
    ]
    if not candidates:
        return None

    phone_key = tracking.get("phone_key") or ""
    if phone_key:
        phone_matches = [order for order in candidates if _order_phone_key(order) == phone_key]
        if len(phone_matches) == 1:
            return phone_matches[0]
        if len(phone_matches) > 1:
            return None

    portal_name = tracking.get("receiver_name_key") or ""
    if len(candidates) == 1 and _portal_name_supports_order(portal_name, candidates[0]):
        return candidates[0]

    scored = [(order, _name_match_score(portal_name, order)) for order in candidates]
    strong = [(order, score) for order, score in scored if score >= 0.5]
    if len(strong) != 1:
        return None

    best_order, best_score = strong[0]
    competing_scores = [score for order, score in scored if order.id != best_order.id]
    if competing_scores and best_score - max(competing_scores) < 0.12:
        return None
    return best_order


def apply_tracking_update(
    db: Session,
    order: Order,
    tracking: dict[str, Any],
    *,
    actor_id: UUID | None = None,
    source: str = "india_post_api",
) -> bool:
    changed = False
    now = datetime.now(timezone.utc)
    old_status = order.status
    old_tracking_number = order.tracking_number

    article = _clean_tracking(tracking.get("tracking_number"))
    if article and order.tracking_number != article:
        order.tracking_number = article
        changed = True
    if not order.courier_name or "india" not in order.courier_name.lower():
        order.courier_name = "India Post"
        changed = True
    if not order.courier_code:
        order.courier_code = "INDIA_POST"
        changed = True

    metadata_pairs = {
        "tracking_status_text": tracking.get("status_text") or None,
        "tracking_last_location": tracking.get("location") or None,
        "tracking_last_event_at": tracking.get("last_event_at"),
        "tracking_synced_at": now,
        "tracking_events_json": tracking.get("events") or None,
        "tracking_raw_response": tracking.get("raw") or None,
        "return_status": tracking.get("return_status") or None,
    }
    for field, value in metadata_pairs.items():
        if getattr(order, field) != value:
            setattr(order, field, value)
            changed = True

    cost = tracking.get("actual_shipping_cost")
    if cost is not None:
        if order.actual_shipping_cost != cost:
            order.actual_shipping_cost = cost
            changed = True
        if cost >= 0 and order.shipping_charge != cost:
            order.shipping_charge = cost
            changed = True

    new_status = tracking.get("order_status")
    if _should_change_status(order.status, new_status):
        order.status = new_status
        order.updated_at = now
        changed = True
        if new_status == OrderStatus.delivered:
            order.delivered_at = tracking.get("last_event_at") or now
            if order.payment_method in (PaymentMethod.cod, PaymentMethod.partial_cod, None):
                order.payment_status = PaymentStatus.paid
                order.amount_paid = order.total_amount
                order.amount_due = Decimal("0")
        history = OrderStatusHistory(
            tenant_id=order.tenant_id,
            order_id=order.id,
            employee_id=actor_id or order.created_by_id,
            old_status=old_status,
            new_status=new_status,
            note=f"India Post tracking sync: {tracking.get('status_text') or new_status.value} ({source})",
        )
        db.add(history)

    if changed:
        order.updated_at = now
        try:
            from app.modules.message_automation.service import handle_order_changed

            handle_order_changed(
                db,
                order,
                previous_tracking_number=old_tracking_number,
                previous_status=old_status,
            )
        except Exception as exc:
            log.warning("Order %s message automation queue skipped: %s", order.order_number, exc)
    return changed


def _extract_recent_rows(result: dict[str, Any]) -> list[Any]:
    for key in ("articles", "records", "shipments", "tracking", "items", "data"):
        value = result.get(key) if isinstance(result, dict) else None
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            nested = _extract_recent_rows(value)
            if nested:
                return nested
    return []


async def refresh_order_tracking_detail(db: Session, order_id: str, current_user: Employee) -> dict[str, Any]:
    order = (
        db.query(Order)
        .options(joinedload(Order.customer))
        .filter(Order.id == order_id, Order.tenant_id == current_user.tenant_id)
        .first()
    )
    if not order:
        raise ValueError("Order not found")

    stored = order_tracking_snapshot(order)
    if not order.tracking_number:
        return {"success": True, "live": False, "tracking": stored, "order_id": str(order.id)}

    partner = _india_post_partner(db, current_user.tenant_id)
    if not partner or not _is_india_post_order(order, partner):
        return {"success": True, "live": False, "tracking": stored, "order_id": str(order.id)}

    client = _client_for_partner(partner)
    result = await client.track_article(order.tracking_number)
    if result.get("success") is False:
        return {"success": False, "error": result.get("error", "Tracking fetch failed"), "tracking": stored}

    tracking = normalize_india_post_tracking(result, order.tracking_number)
    apply_tracking_update(db, order, tracking, actor_id=current_user.id, source="manual_detail_refresh")
    db.commit()
    return {"success": True, "live": True, "tracking": tracking, "order_id": str(order.id)}


async def sync_tenant_india_post_orders(
    db: Session,
    tenant_id: UUID,
    *,
    actor_id: UUID | None = None,
    days: int = 7,
    include_recent_lookup: bool = True,
    limit: int = 50,
) -> dict[str, Any]:
    partner = _india_post_partner(db, tenant_id)
    if not partner:
        return {"success": False, "tenant_id": str(tenant_id), "error": "India Post is not configured"}

    client = _client_for_partner(partner)
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(days, 1))
    updated_orders: set[UUID] = set()
    errors: list[dict[str, Any]] = []
    india_post_filter = or_(
        Order.shipping_partner_id == partner.id,
        Order.courier_name.ilike("%india%post%"),
        Order.courier_code.ilike("%india_post%"),
        Order.india_post_customer_id.isnot(None),
        Order.shipping_service.isnot(None),
    )

    missing_orders = (
        db.query(Order)
        .options(joinedload(Order.customer))
        .filter(
            Order.tenant_id == tenant_id,
            Order.is_active == True,
            india_post_filter,
            or_(Order.tracking_number.is_(None), Order.tracking_number == ""),
            Order.created_at >= cutoff,
            Order.status.in_([OrderStatus.confirmed, OrderStatus.processing, OrderStatus.packed]),
            Order.delivery_pincode.isnot(None),
        )
        .order_by(Order.created_at.desc(), Order.id.desc())
        .all()
    )

    known_orders = (
        db.query(Order)
        .options(joinedload(Order.customer))
        .filter(
            Order.tenant_id == tenant_id,
            Order.is_active == True,
            Order.tracking_number.isnot(None),
            Order.tracking_number != "",
            Order.status.notin_([OrderStatus.delivered, OrderStatus.returned, OrderStatus.cancelled]),
            india_post_filter,
        )
        .order_by(Order.created_at.desc(), Order.id.desc())
        .limit(limit)
        .all()
    )

    for order in known_orders:
        try:
            result = await client.track_article(order.tracking_number)
            if result.get("success") is False:
                errors.append({"order_number": order.order_number, "tracking": order.tracking_number, "error": result.get("error")})
                continue
            tracking = normalize_india_post_tracking(result, order.tracking_number)
            if apply_tracking_update(db, order, tracking, actor_id=actor_id, source="scheduled_tracking_refresh"):
                updated_orders.add(order.id)
        except Exception as exc:
            db.rollback()
            errors.append({"order_number": order.order_number, "tracking": order.tracking_number, "error": str(exc)})

    matched_recent = 0
    skipped_recent = 0
    recent_lookup_error = None
    portal_report_rows = 0
    portal_matches = 0
    portal_rows_skipped = 0
    portal_lookup_error = None
    if include_recent_lookup:
        recent_result = await client.fetch_recent_tracking(days=days)
        if recent_result.get("success"):
            rows = _extract_recent_rows(recent_result)
            index: dict[tuple[str, str], list[Order]] = {}
            for order in missing_orders:
                key = (_order_phone_key(order), _digits(order.delivery_pincode))
                if key[0] and key[1]:
                    index.setdefault(key, []).append(order)

            for row in rows:
                tracking = normalize_india_post_tracking(row)
                key = (tracking.get("phone_key") or "", tracking.get("pincode") or "")
                article = tracking.get("tracking_number")
                if not key[0] or not key[1] or not article:
                    skipped_recent += 1
                    continue
                candidates = index.get(key, [])
                if len(candidates) != 1:
                    skipped_recent += 1
                    continue
                order = candidates[0]
                if apply_tracking_update(db, order, tracking, actor_id=actor_id, source="recent_article_match"):
                    updated_orders.add(order.id)
                    matched_recent += 1
        else:
            recent_lookup_error = recent_result.get("error") or recent_result.get("message")

        if missing_orders:
            username = partner.client_id or ""
            password = shipping_config_service.decrypt_credential(partner.api_key) if partner.api_key else ""
            portal_client = IndiaPostPortalClient(username, password)
            portal_result = await portal_client.fetch_recent_booking_report(days=days)
            if portal_result.get("success"):
                portal_rows = _extract_recent_rows(portal_result)
                portal_report_rows = len(portal_rows)
                used_order_ids = set(updated_orders)
                for row in portal_rows:
                    tracking = normalize_india_post_tracking(row)
                    article = tracking.get("tracking_number")
                    if not article:
                        portal_rows_skipped += 1
                        continue
                    order = _match_portal_row_to_missing_order(tracking, missing_orders, used_order_ids)
                    if not order:
                        portal_rows_skipped += 1
                        continue
                    if apply_tracking_update(db, order, tracking, actor_id=actor_id, source="portal_booking_report_match"):
                        updated_orders.add(order.id)
                        used_order_ids.add(order.id)
                        portal_matches += 1
            else:
                portal_lookup_error = portal_result.get("error") or portal_result.get("message")

    db.commit()

    profit_postings_refreshed = 0
    if updated_orders:
        try:
            from app.modules.profit_engine.service import upsert_order_profit_posting
            for order_id in updated_orders:
                if upsert_order_profit_posting(db, tenant_id, order_id) is not None:
                    profit_postings_refreshed += 1
            db.commit()
        except Exception as exc:
            db.rollback()
            log.warning("Profit posting refresh after India Post sync skipped: %s", exc)

    return {
        "success": True,
        "tenant_id": str(tenant_id),
        "known_tracking_checked": len(known_orders),
        "orders_updated": len(updated_orders),
        "missing_tracking_candidates": len(missing_orders),
        "missing_tracking_order_numbers": [order.order_number for order in missing_orders[:20]],
        "recent_matches": matched_recent,
        "recent_rows_skipped": skipped_recent,
        "recent_lookup_error": recent_lookup_error,
        "portal_report_rows": portal_report_rows,
        "portal_matches": portal_matches,
        "portal_rows_skipped": portal_rows_skipped,
        "portal_lookup_error": portal_lookup_error,
        "profit_postings_refreshed": profit_postings_refreshed,
        "errors": errors[:20],
    }


async def sync_all_tenants_india_post_orders(db: Session, *, days: int = 7, limit: int = 50) -> dict[str, Any]:
    tenant_ids = [
        row[0]
        for row in db.query(DeliveryPartner.tenant_id)
        .filter(DeliveryPartner.partner_type == "india_post", DeliveryPartner.is_active == True)
        .distinct()
        .all()
    ]
    summaries = []
    for tenant_id in tenant_ids:
        try:
            summaries.append(await sync_tenant_india_post_orders(db, tenant_id, days=days, limit=limit))
        except Exception as exc:
            db.rollback()
            summaries.append({"success": False, "tenant_id": str(tenant_id), "error": str(exc)})
    return {
        "success": True,
        "tenants_checked": len(tenant_ids),
        "orders_updated": sum(item.get("orders_updated", 0) for item in summaries),
        "missing_tracking_candidates": sum(item.get("missing_tracking_candidates", 0) for item in summaries),
        "portal_matches": sum(item.get("portal_matches", 0) for item in summaries),
        "summaries": summaries,
    }
