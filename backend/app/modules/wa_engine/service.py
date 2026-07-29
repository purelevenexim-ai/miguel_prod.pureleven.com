"""
WhatsApp Engine — Service Layer
=================================
All business logic lives here.  Routers are thin; they call service
functions and return the result directly.

Uses synchronous SQLAlchemy Session (consistent with the rest of the app).
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.wa_engine import (
    WaSettings, WaPostbackRule, WaCampaignType,
    WaSubscriber, WaConversation, WaMessage,
    WaStatus, WaStatusHistory, WaCampaign, WaCampaignRecipient,
    WaProvider, WaPostbackAction, WaStatusEnum, WaTriggerEvent,
    WaMessageDirection, WaMessageType, WaMessageStatus,
    WaCampaignStatus, WaRecipientStatus, WaMessageLog,
    WaOutboundWebhook,
)
from app.modules.wa_engine.providers.base import InboundMessage
from app.modules.wa_engine.providers.wabis import WabisProvider
from app.modules.wa_engine.providers.meta  import MetaProvider
from app.modules.wa_engine.schemas import (
    WaSettingsSave,
    WaPostbackRuleCreate, WaPostbackRuleUpdate,
    WaCampaignTypeCreate, WaCampaignTypeUpdate,
    WaStatusUpdate, WaMessageSend, WaCampaignCreate,
)

log = logging.getLogger(__name__)

UTC = timezone.utc


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _provider(settings: WaSettings):
    """Return the appropriate provider instance for a settings row."""
    if settings.provider == WaProvider.meta:
        return MetaProvider(settings)
    return WabisProvider(settings)


def _now() -> datetime:
    return datetime.now(UTC)


# ─────────────────────────────────────────────────────────────
# Settings
# ─────────────────────────────────────────────────────────────

def get_or_create_settings(
    db: Session, tenant_id: uuid.UUID
) -> WaSettings:
    row = db.query(WaSettings).filter(WaSettings.tenant_id == tenant_id).first()
    if row is None:
        row = WaSettings(tenant_id=tenant_id)
        db.add(row)
        db.flush()
    return row


def save_settings(
    db: Session,
    tenant_id: uuid.UUID,
    data: WaSettingsSave,
) -> WaSettings:
    row = get_or_create_settings(db, tenant_id)
    update_data = data.model_dump(exclude_none=True)
    for key, val in update_data.items():
        if hasattr(row, key):
            setattr(row, key, val)
    row.updated_at = _now()
    db.flush()
    return row


async def test_connection(
    db: Session, tenant_id: uuid.UUID
) -> tuple[bool, str]:
    row = get_or_create_settings(db, tenant_id)
    provider = _provider(row)
    return await provider.test_connection()


# ─────────────────────────────────────────────────────────────
# Postback Rules
# ─────────────────────────────────────────────────────────────

def list_postback_rules(
    db: Session, tenant_id: uuid.UUID
) -> List[WaPostbackRule]:
    return (
        db.query(WaPostbackRule)
        .filter(WaPostbackRule.tenant_id == tenant_id)
        .order_by(WaPostbackRule.created_at)
        .all()
    )


def create_postback_rule(
    db: Session, tenant_id: uuid.UUID, data: WaPostbackRuleCreate
) -> WaPostbackRule:
    row = WaPostbackRule(tenant_id=tenant_id, **data.model_dump())
    db.add(row)
    db.flush()
    return row


def update_postback_rule(
    db: Session,
    tenant_id: uuid.UUID,
    rule_id: uuid.UUID,
    data: WaPostbackRuleUpdate,
) -> WaPostbackRule:
    row = (
        db.query(WaPostbackRule)
        .filter(WaPostbackRule.id == rule_id, WaPostbackRule.tenant_id == tenant_id)
        .first()
    )
    if row is None:
        raise ValueError("Postback rule not found")
    for key, val in data.model_dump(exclude_none=True).items():
        setattr(row, key, val)
    row.updated_at = _now()
    db.flush()
    return row


def delete_postback_rule(
    db: Session, tenant_id: uuid.UUID, rule_id: uuid.UUID
) -> bool:
    row = (
        db.query(WaPostbackRule)
        .filter(WaPostbackRule.id == rule_id, WaPostbackRule.tenant_id == tenant_id)
        .first()
    )
    if row is None:
        return False
    db.delete(row)
    db.flush()
    return True


# ─────────────────────────────────────────────────────────────
# Campaign Types
# ─────────────────────────────────────────────────────────────

def list_campaign_types(
    db: Session, tenant_id: uuid.UUID, active_only: bool = False
) -> List[WaCampaignType]:
    q = db.query(WaCampaignType).filter(WaCampaignType.tenant_id == tenant_id)
    if active_only:
        q = q.filter(WaCampaignType.is_active.is_(True))
    return q.order_by(WaCampaignType.name).all()


def create_campaign_type(
    db: Session,
    tenant_id: uuid.UUID,
    data: WaCampaignTypeCreate,
    employee_id: uuid.UUID,
) -> WaCampaignType:
    row = WaCampaignType(
        tenant_id=tenant_id,
        created_by_employee_id=employee_id,
        **data.model_dump(),
    )
    db.add(row)
    db.flush()
    return row


def update_campaign_type(
    db: Session,
    tenant_id: uuid.UUID,
    ct_id: uuid.UUID,
    data: WaCampaignTypeUpdate,
) -> WaCampaignType:
    row = (
        db.query(WaCampaignType)
        .filter(WaCampaignType.id == ct_id, WaCampaignType.tenant_id == tenant_id)
        .first()
    )
    if row is None:
        raise ValueError("Campaign type not found")
    for key, val in data.model_dump(exclude_none=True).items():
        setattr(row, key, val)
    row.updated_at = _now()
    db.flush()
    return row


def delete_campaign_type(
    db: Session, tenant_id: uuid.UUID, ct_id: uuid.UUID
) -> bool:
    row = (
        db.query(WaCampaignType)
        .filter(WaCampaignType.id == ct_id, WaCampaignType.tenant_id == tenant_id)
        .first()
    )
    if row is None:
        return False
    db.delete(row)
    db.flush()
    return True


# ─────────────────────────────────────────────────────────────
# Subscribers
# ─────────────────────────────────────────────────────────────

def list_subscribers(
    db: Session,
    tenant_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
) -> List[WaSubscriber]:
    q = db.query(WaSubscriber).filter(WaSubscriber.tenant_id == tenant_id)
    if search:
        q = q.filter(
            WaSubscriber.name.ilike(f"%{search}%") |
            WaSubscriber.phone_number.ilike(f"%{search}%")
        )
    return q.order_by(WaSubscriber.last_seen_at.desc().nullslast()).offset(skip).limit(limit).all()


def upsert_subscriber(
    db: Session,
    tenant_id: uuid.UUID,
    inbound: InboundMessage,
) -> WaSubscriber:
    """
    Create or update a WaSubscriber from an inbound event.

    Label policy: MERGE (union) — labels from WABIS are always additive.
      e.g. existing ["Price_checked"] + new ["Interested","Address_checked"]
           → ["Price_checked", "Interested", "Address_checked"]

    Postback policy: keep last_postback_id (most recent) AND accumulate all
      seen IDs in postback_ids list (used for send-back targeting).
    """
    row = (
        db.query(WaSubscriber)
        .filter(
            WaSubscriber.tenant_id == tenant_id,
            WaSubscriber.subscriber_id == inbound.subscriber_id,
        )
        .first()
    )
    now = _now()

    if row is None:
        row = WaSubscriber(
            tenant_id=tenant_id,
            subscriber_id=inbound.subscriber_id,
            phone_number=inbound.phone_number,
            name=inbound.subscriber_name,
            wabis_labels=inbound.labels or [],
            last_postback_id=inbound.postback_id,
            postback_ids=[inbound.postback_id] if inbound.postback_id else [],
            first_seen_at=now,
            last_seen_at=now,
        )
        db.add(row)
    else:
        if inbound.phone_number:
            row.phone_number = inbound.phone_number
        if inbound.subscriber_name:
            row.name = inbound.subscriber_name

        # ── MERGE labels (union, preserve existing) ──────────────
        if inbound.labels:
            existing = list(row.wabis_labels or [])
            merged = existing + [l for l in inbound.labels if l not in existing]
            row.wabis_labels = merged

        # ── ACCUMULATE postback IDs ───────────────────────────────
        if inbound.postback_id:
            row.last_postback_id = inbound.postback_id
            existing_pbs = list(row.postback_ids or [])
            if inbound.postback_id not in existing_pbs:
                existing_pbs.append(inbound.postback_id)
            row.postback_ids = existing_pbs

        row.last_seen_at = now

    db.flush()
    return row


# ─────────────────────────────────────────────────────────────
# Conversations + Messages
# ─────────────────────────────────────────────────────────────

def list_conversations(
    db: Session,
    tenant_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
) -> List[WaConversation]:
    return (
        db.query(WaConversation)
        .filter(WaConversation.tenant_id == tenant_id)
        .order_by(WaConversation.last_message_at.desc().nullslast())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_or_create_conversation(
    db: Session,
    tenant_id: uuid.UUID,
    subscriber: WaSubscriber,
) -> WaConversation:
    conv = (
        db.query(WaConversation)
        .filter(
            WaConversation.tenant_id == tenant_id,
            WaConversation.subscriber_id == subscriber.id,
        )
        .first()
    )
    if conv is None:
        conv = WaConversation(
            tenant_id=tenant_id,
            subscriber_id=subscriber.id,
            lead_id=subscriber.lead_id,
        )
        db.add(conv)
        db.flush()
    return conv


def list_messages(
    db: Session,
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
) -> List[WaMessage]:
    return (
        db.query(WaMessage)
        .filter(
            WaMessage.tenant_id == tenant_id,
            WaMessage.conversation_id == conversation_id,
        )
        .order_by(WaMessage.sent_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


async def send_message(
    db: Session,
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
    data: WaMessageSend,
    employee_id: uuid.UUID,
) -> WaMessage:
    """Send a text message to the subscriber in a conversation."""
    conv = (
        db.query(WaConversation)
        .filter(WaConversation.id == conversation_id, WaConversation.tenant_id == tenant_id)
        .first()
    )
    if conv is None:
        raise ValueError("Conversation not found")

    subscriber = db.query(WaSubscriber).filter(WaSubscriber.id == conv.subscriber_id).first()
    if subscriber is None:
        raise ValueError("Subscriber not found")

    settings = get_or_create_settings(db, tenant_id)
    provider = _provider(settings)

    send_result = await provider.send_text(
        phone=subscriber.phone_number,
        text=data.message,
    )

    msg = WaMessage(
        tenant_id=tenant_id,
        conversation_id=conversation_id,
        provider_message_id=send_result.provider_message_id,
        direction=WaMessageDirection.outbound,
        message_type=WaMessageType.text,
        content=data.message,
        status=WaMessageStatus.sent if send_result.success else WaMessageStatus.failed,
        sent_at=_now(),
        failed_reason=send_result.error if not send_result.success else None,
        sent_by_employee_id=employee_id,
        raw_payload=send_result.raw_response or {},
    )
    db.add(msg)

    conv.last_message_at = _now()
    conv.last_message_direction = WaMessageDirection.outbound

    db.flush()
    return msg


# ─────────────────────────────────────────────────────────────
# WhatsApp Status (separate pipeline from Lead.status)
# ─────────────────────────────────────────────────────────────

def list_wa_statuses(
    db: Session,
    tenant_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
) -> List[WaStatus]:
    return (
        db.query(WaStatus)
        .filter(WaStatus.tenant_id == tenant_id)
        .order_by(WaStatus.updated_at.desc().nullslast())
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_wa_status(
    db: Session,
    tenant_id: uuid.UUID,
    subscriber_id: uuid.UUID,
    data: WaStatusUpdate,
    employee_id: uuid.UUID,
) -> WaStatus:
    row = (
        db.query(WaStatus)
        .filter(WaStatus.tenant_id == tenant_id, WaStatus.subscriber_id == subscriber_id)
        .first()
    )
    now = _now()

    if row is None:
        row = WaStatus(
            tenant_id=tenant_id,
            subscriber_id=subscriber_id,
            status=data.status,
            note=data.note,
            assigned_to_employee_id=data.assigned_to,
            updated_by_employee_id=employee_id,
        )
        db.add(row)
        db.flush()
    else:
        old_status = row.status
        row.status = data.status
        row.note   = data.note
        row.updated_by_employee_id = employee_id
        row.updated_at = now
        if data.assigned_to:
            row.assigned_to_employee_id = data.assigned_to

        hist = WaStatusHistory(
            tenant_id=tenant_id,
            wa_status_id=row.id,
            old_status=old_status,
            new_status=data.status,
            changed_by_employee_id=employee_id,
            note=data.note,
            changed_at=now,
        )
        db.add(hist)
        db.flush()

    return row


# ─────────────────────────────────────────────────────────────
# Campaigns
# ─────────────────────────────────────────────────────────────

def list_campaigns(
    db: Session,
    tenant_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
) -> List[WaCampaign]:
    return (
        db.query(WaCampaign)
        .filter(WaCampaign.tenant_id == tenant_id)
        .order_by(WaCampaign.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_campaign(
    db: Session,
    tenant_id: uuid.UUID,
    data: WaCampaignCreate,
    employee_id: uuid.UUID,
) -> WaCampaign:
    campaign = WaCampaign(
        tenant_id=tenant_id,
        name=data.name,
        campaign_type_id=data.campaign_type_id,
        audience_filter=data.audience_filter or {},
        workflow_url_override=data.workflow_url_override,
        payload_template_override=data.payload_template_override,
        scheduled_at=data.scheduled_at,
        status=WaCampaignStatus.draft,
        created_by_employee_id=employee_id,
    )
    db.add(campaign)
    db.flush()

    recipients: List[WaCampaignRecipient] = []

    if data.recipient_subscriber_ids:
        subs = (
            db.query(WaSubscriber)
            .filter(
                WaSubscriber.tenant_id == tenant_id,
                WaSubscriber.id.in_(data.recipient_subscriber_ids),
            )
            .all()
        )
        for sub in subs:
            recipients.append(WaCampaignRecipient(
                campaign_id=campaign.id,
                tenant_id=tenant_id,
                subscriber_id=sub.id,
                lead_id=sub.lead_id,
                wa_phone=sub.phone_number,
                contact_name=sub.name,
                status=WaRecipientStatus.pending,
            ))

    if data.recipient_phones:
        for item in data.recipient_phones:
            phone = item.get("phone", "").strip()
            if phone:
                recipients.append(WaCampaignRecipient(
                    campaign_id=campaign.id,
                    tenant_id=tenant_id,
                    wa_phone=phone,
                    contact_name=item.get("name"),
                    status=WaRecipientStatus.pending,
                ))

    for r in recipients:
        db.add(r)

    campaign.total_recipients = len(recipients)
    db.flush()
    return campaign


async def start_campaign(
    db: Session,
    tenant_id: uuid.UUID,
    campaign_id: uuid.UUID,
    employee_id: uuid.UUID,
) -> WaCampaign:
    """Execute a campaign: send WA message to every pending recipient."""
    campaign = (
        db.query(WaCampaign)
        .filter(WaCampaign.id == campaign_id, WaCampaign.tenant_id == tenant_id)
        .first()
    )
    if campaign is None:
        raise ValueError("Campaign not found")
    if campaign.status not in (WaCampaignStatus.draft, WaCampaignStatus.failed):
        raise ValueError(f"Campaign cannot be started from status '{campaign.status}'")

    workflow_url = campaign.workflow_url_override
    payload_tpl: Dict[str, Any] = campaign.payload_template_override or {}

    if not workflow_url and campaign.campaign_type_id:
        ct = db.query(WaCampaignType).filter(WaCampaignType.id == campaign.campaign_type_id).first()
        if ct:
            workflow_url = ct.wabis_workflow_url
            if ct.payload_template and not payload_tpl:
                payload_tpl = ct.payload_template

    if not workflow_url:
        raise ValueError(
            "No workflow URL found — configure it in Campaign Type or set workflow_url_override"
        )

    settings = get_or_create_settings(db, tenant_id)
    provider  = _provider(settings)

    campaign.status     = WaCampaignStatus.running
    campaign.started_at = _now()
    db.flush()

    recipients = (
        db.query(WaCampaignRecipient)
        .filter(
            WaCampaignRecipient.campaign_id == campaign_id,
            WaCampaignRecipient.status == WaRecipientStatus.pending,
        )
        .all()
    )

    sent = failed = skipped = 0

    for recip in recipients:
        phone = recip.wa_phone
        if not phone or recip.status != WaRecipientStatus.pending:
            recip.status = WaRecipientStatus.skipped
            skipped += 1
            continue

        payload = _render_payload(payload_tpl, recip)

        try:
            result = await provider.send_template(
                phone=phone,
                workflow_url=workflow_url,
                payload=payload,
            )
            if result.success:
                recip.status           = WaRecipientStatus.sent
                recip.provider_response = result.raw_response
                recip.sent_at          = _now()
                sent += 1
            else:
                recip.status       = WaRecipientStatus.failed
                recip.error_reason = result.error
                failed += 1
        except Exception as exc:
            log.exception("Error sending to %s", phone)
            recip.status       = WaRecipientStatus.failed
            recip.error_reason = str(exc)
            failed += 1

    campaign.sent_count    = sent
    campaign.failed_count  = failed
    campaign.skipped_count = skipped
    campaign.status        = (
        WaCampaignStatus.completed if failed == 0 else WaCampaignStatus.failed
    )
    campaign.completed_at = _now()
    db.flush()
    return campaign


def _render_payload(
    template: Dict[str, Any],
    recip: WaCampaignRecipient,
) -> Dict[str, Any]:
    """Substitute {{name}} and {{phone}} tokens in payload template string values."""
    raw = json.dumps(template)
    raw = raw.replace("{{name}}", recip.contact_name or "")
    raw = raw.replace("{{phone}}", recip.wa_phone or "")
    return json.loads(raw)


def _render_payload_dict(
    template: Dict[str, Any],
    variables: Dict[str, str],
) -> Dict[str, Any]:
    """Substitute {{key}} tokens in payload template using a variables dict."""
    raw = json.dumps(template)
    for key, val in variables.items():
        raw = raw.replace("{{" + key + "}}", str(val or ""))
    return json.loads(raw)


# ─────────────────────────────────────────────────────────────
# Direct Send  (chat inbox → WABIS /api/v1/whatsapp/send)
# ─────────────────────────────────────────────────────────────

async def send_direct_message(
    db: Session,
    tenant_id: uuid.UUID,
    phone_number: str,
    message: str,
    employee_id: uuid.UUID,
) -> Dict[str, Any]:
    """
    Send a plain text WhatsApp message directly to a phone number via WABIS API.
    Finds or creates subscriber + conversation, logs the message in WaMessage.
    Used by the chat inbox drawer.
    """
    try:
        settings = get_or_create_settings(db, tenant_id)
        
        # Validate WABIS is configured
        if settings.provider != WaProvider.wabis:
            return {
                "success": False,
                "message": "WABIS provider not configured",
                "wa_message_id": None,
                "subscriber_id": None,
                "raw_response": {"error": "Provider not set to WABIS"},
            }
        
        if not settings.wabis_api_token or not settings.wabis_phone_number_id:
            return {
                "success": False,
                "message": "WABIS API Token or Phone Number ID not configured in Settings",
                "wa_message_id": None,
                "subscriber_id": None,
                "raw_response": {"error": "Missing WABIS credentials"},
            }
        
        provider = _provider(settings)

        # Ensure subscriber exists in WABIS and in our DB
        clean = "".join(c for c in phone_number if c.isdigit())
        subscriber = (
            db.query(WaSubscriber)
            .filter(WaSubscriber.tenant_id == tenant_id, WaSubscriber.phone_number == clean)
            .first()
        )
        if subscriber is None:
            subscriber = WaSubscriber(
                tenant_id=tenant_id,
                subscriber_id=clean,  # Use phone as subscriber_id for now
                phone_number=clean,
                name=clean,  # Use phone number as name
            )
            db.add(subscriber)
            db.flush()

        # Ensure conversation exists
        conversation = (
            db.query(WaConversation)
            .filter(WaConversation.tenant_id == tenant_id, WaConversation.subscriber_id == subscriber.id)
            .first()
        )
        if conversation is None:
            conversation = WaConversation(
                tenant_id=tenant_id,
                subscriber_id=subscriber.id,
            )
            db.add(conversation)
            db.flush()

        # Call WABIS send API
        send_result = await provider.send_text(
            phone=clean,
            text=message,
            name=subscriber.name or clean,
        )

        # Log message
        msg = WaMessage(
            tenant_id=tenant_id,
            conversation_id=conversation.id,
            provider_message_id=send_result.provider_message_id,
            direction=WaMessageDirection.outbound,
            message_type=WaMessageType.text,
            content=message,
            status=WaMessageStatus.sent if send_result.success else WaMessageStatus.failed,
            sent_at=_now(),
            failed_reason=send_result.error if not send_result.success else None,
            sent_by_employee_id=employee_id,
            raw_payload=send_result.raw_response or {},
        )
        db.add(msg)

        conversation.last_message_at = _now()
        conversation.last_message_direction = WaMessageDirection.outbound
        db.commit()

        log.info(f"Message sent to {clean}: success={send_result.success}")
        return {
            "success": send_result.success,
            "message": "Sent successfully" if send_result.success else (send_result.error or "Send failed"),
            "wa_message_id": send_result.provider_message_id,
            "subscriber_id": str(subscriber.id),
            "raw_response": send_result.raw_response,
        }
    
    except Exception as e:
        log.exception(f"Failed to send message to {phone_number}")
        return {
            "success": False,
            "message": f"Failed to send message: {str(e)}",
            "wa_message_id": None,
            "subscriber_id": None,
            "raw_response": {"error": str(e)},
        }


async def trigger_bot_flow(
    db: Session,
    tenant_id: uuid.UUID,
    phone_number: str,
    bot_flow_unique_id: str,
) -> Dict[str, Any]:
    """Trigger a WABIS bot flow for a phone number."""
    settings = get_or_create_settings(db, tenant_id)
    provider = _provider(settings)

    clean = "".join(c for c in phone_number if c.isdigit())
    result = await provider.trigger_bot(
        phone=clean,
        bot_flow_unique_id=bot_flow_unique_id,
    )
    return {
        "success": result.success,
        "message": "Bot triggered" if result.success else (result.error or "Trigger failed"),
        "raw_response": result.raw_response,
    }


# ─────────────────────────────────────────────────────────────
# Outbound Notification  (order events + ad-hoc)
# ─────────────────────────────────────────────────────────────

async def send_notification(
    db: Session,
    tenant_id: uuid.UUID,
    phone: str,
    campaign_type_id: Optional[uuid.UUID] = None,
    workflow_url: Optional[str] = None,
    variables: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Send a single outbound WhatsApp message via WABIS workflow URL.
    Used for both auto-triggered (order events) and manual sends.
    """
    settings = get_or_create_settings(db, tenant_id)
    provider = _provider(settings)

    payload_template: Dict[str, Any] = {}
    used_url = workflow_url

    if campaign_type_id:
        ct = (
            db.query(WaCampaignType)
            .filter(
                WaCampaignType.id == campaign_type_id,
                WaCampaignType.tenant_id == tenant_id,
                WaCampaignType.is_active.is_(True),
            )
            .first()
        )
        if ct is None:
            return {"success": False, "message": "Campaign type not found or inactive"}
        used_url = used_url or ct.wabis_workflow_url
        payload_template = ct.payload_template or {}

    if not used_url:
        return {"success": False, "message": "No workflow URL configured for this message type"}

    # Build payload from template + variables
    payload = _render_payload_dict(payload_template, variables or {})
    payload.setdefault("phone", phone)
    payload.setdefault("phone_number", phone)

    result = await provider.send_template(
        phone=phone,
        workflow_url=used_url,
        payload=payload,
    )

    return {
        "success": result.success,
        "message": "Sent successfully" if result.success else (result.error or "Send failed"),
        "provider_message_id": result.provider_message_id,
        "raw_response": result.raw_response,
    }


async def send_order_notification(
    db: Session,
    tenant_id: uuid.UUID,
    trigger_event: str,
    phone: str,
    variables: Dict[str, Any],
    use_utility_fallback: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Auto-trigger a WhatsApp message based on an order lifecycle event.
    Looks up the active WaCampaignType matching the trigger_event.

    If use_utility_fallback=True (caller detected outside-24h window),
    uses utility_workflow_url instead of wabis_workflow_url.

    Returns None if no matching template is configured (silent no-op).
    """
    ct = (
        db.query(WaCampaignType)
        .filter(
            WaCampaignType.tenant_id == tenant_id,
            WaCampaignType.trigger_event == trigger_event,
            WaCampaignType.is_active.is_(True),
        )
        .first()
    )
    if ct is None:
        log.debug("No active campaign type for trigger_event=%s tenant=%s", trigger_event, tenant_id)
        return None

    # Decide which URL to use:
    # - use_utility_fallback=True → use utility_workflow_url (outside 24h window)
    # - use_utility_fallback=False → use wabis_workflow_url (within 24h window)
    # If utility URL is set but regular URL is not, always use utility URL.
    workflow_url = None
    if use_utility_fallback and ct.utility_workflow_url:
        workflow_url = ct.utility_workflow_url
        log.info("Using utility_workflow_url for %s (outside 24h window)", ct.name)
    elif ct.wabis_workflow_url:
        workflow_url = ct.wabis_workflow_url
    elif ct.utility_workflow_url:
        workflow_url = ct.utility_workflow_url
        log.info("No regular workflow URL — falling back to utility_workflow_url for %s", ct.name)
    else:
        log.warning("Campaign type '%s' has no workflow URL — skipping", ct.name)
        return None

    result = await send_notification(
        db=db,
        tenant_id=tenant_id,
        phone=phone,
        campaign_type_id=ct.id,
        workflow_url=workflow_url,
        variables=variables,
    )

    log.info(
        "Order notification [%s] → phone=%s url_type=%s success=%s",
        trigger_event, phone,
        "utility" if use_utility_fallback else "regular",
        result.get("success"),
    )
    return result


# ─────────────────────────────────────────────────────────────
# Inbound Webhook Processor
# ─────────────────────────────────────────────────────────────

_STATUS_RANK = {
    WaMessageStatus.pending: 0,
    WaMessageStatus.sent: 1,
    WaMessageStatus.delivered: 2,
    WaMessageStatus.read: 3,
}


def apply_meta_status_update(
    db: Session,
    tenant_id: uuid.UUID,
    statuses: List[Dict[str, Any]],
) -> int:
    """
    Apply Meta Cloud API message-status callbacks (delivered/read/failed) to
    wa_messages, matched by provider_message_id. Called from the inbound
    webhook after signature verification — see wa_engine/router.py.

    Never regresses an already-recorded status (e.g. a late 'delivered'
    callback arriving after we already recorded 'read' is ignored for the
    status/rank, but delivered_at is still backfilled if it was missing).
    Returns the number of wa_messages rows actually updated, for logging/tests.
    """
    updated = 0
    for entry in statuses:
        provider_message_id = str(entry.get("id") or "").strip()
        raw_status = str(entry.get("status") or "").strip().lower()
        if not provider_message_id or raw_status not in {"sent", "delivered", "read", "failed"}:
            continue

        message = (
            db.query(WaMessage)
            .filter(
                WaMessage.tenant_id == tenant_id,
                WaMessage.provider_message_id == provider_message_id,
            )
            .first()
        )
        if message is None:
            continue

        raw_timestamp = entry.get("timestamp")
        try:
            event_at = datetime.fromtimestamp(int(raw_timestamp), tz=timezone.utc) if raw_timestamp else _now()
        except (TypeError, ValueError):
            event_at = _now()

        changed = False
        if raw_status == "failed":
            message.status = WaMessageStatus.failed
            errors = entry.get("errors") or []
            if errors:
                message.failed_reason = str(errors[0].get("title") or errors[0].get("message") or "").strip() or message.failed_reason
            changed = True
        else:
            new_status = WaMessageStatus(raw_status)
            if _STATUS_RANK[new_status] > _STATUS_RANK.get(message.status, -1):
                message.status = new_status
                changed = True
            if raw_status == "delivered" and message.delivered_at is None:
                message.delivered_at = event_at
                changed = True
            if raw_status == "read" and message.read_at is None:
                message.read_at = event_at
                if message.delivered_at is None:
                    message.delivered_at = event_at
                changed = True

        if changed:
            updated += 1

    return updated


async def process_inbound(
    db: Session,
    tenant_id: uuid.UUID,
    inbound: InboundMessage,
    employee_id: Optional[uuid.UUID] = None,
) -> None:
    """
    Core inbound processing pipeline:
    1. Upsert subscriber
    2. Sync WABIS data to CRM Lead record
    3. Find / create conversation
    4. Store inbound message
    5. Apply postback rule (create lead, update status, etc.)
    6. Upsert WA status → new_message
    7. Auto-reply if enabled
    """
    # 1 — subscriber
    subscriber = upsert_subscriber(db, tenant_id, inbound)

    # 2 — sync WABIS data to Lead (create or update with labels)
    _sync_wabis_to_lead(db, tenant_id, inbound, subscriber)

    # 3 — conversation
    conv = get_or_create_conversation(db, tenant_id, subscriber)

    # 3 — message
    msg_content = inbound.message_text or f"[postback: {inbound.postback_id}]"
    msg = WaMessage(
        tenant_id=tenant_id,
        conversation_id=conv.id,
        direction=WaMessageDirection.inbound,
        message_type=WaMessageType.text,
        content=msg_content,
        status=WaMessageStatus.delivered,
        sent_at=_now(),
        raw_payload=inbound.raw_payload,
    )
    db.add(msg)
    conv.last_message_at        = _now()
    conv.last_message_direction = WaMessageDirection.inbound
    conv.unread_count           = (conv.unread_count or 0) + 1
    db.flush()

    # 4 — postback rule
    if inbound.postback_id:
        _apply_postback_rule(db, tenant_id, inbound, subscriber)

    # 5 — upsert WaStatus → new_message
    _upsert_new_message_status(db, tenant_id, subscriber)

    # 6 — auto-reply
    await _maybe_auto_reply(db, tenant_id, subscriber)

    db.flush()

    # 7 — fire outbound webhooks (non-blocking background task)
    event = "postback" if inbound.postback_id else "new_message"
    import asyncio
    asyncio.create_task(
        _fire_outbound_webhooks(db, tenant_id, subscriber, inbound, event)
    )


def _sync_wabis_to_lead(
    db: Session,
    tenant_id: uuid.UUID,
    inbound: InboundMessage,
    subscriber: WaSubscriber,
) -> None:
    """
    Sync WABIS webhook data to a CRM Lead record.
    
    Creates a new Lead if:
    - Subscriber has no linked lead_id, AND
    - Has a phone number, AND
    - Phone doesn't match an existing lead
    
    Updates the Lead with:
    - Name and phone (if available)
    - WABIS labels (merged, not replaced)
    """
    from app.models.lead import Lead, LeadSource, LeadPipelineStatus
    
    # Check if subscriber already has a linked lead
    if subscriber.lead_id:
        # Update existing lead with labels
        lead = db.query(Lead).filter(Lead.id == subscriber.lead_id).first()
        if lead and inbound.labels:
            existing = list(lead.wabis_labels or [])
            merged = existing + [l for l in inbound.labels if l not in existing]
            lead.wabis_labels = merged
        return
    
    # Try to find an existing lead by phone
    if not inbound.phone_number:
        return
    
    phone = inbound.phone_number.strip()
    if not phone:
        return
    
    # Search for existing lead with same phone
    existing_lead = db.query(Lead).filter(
        Lead.tenant_id == tenant_id,
        Lead.phone == phone,
    ).first()
    
    if existing_lead:
        # Link subscriber to existing lead and update labels
        subscriber.lead_id = existing_lead.id
        if inbound.labels:
            existing_labels = list(existing_lead.wabis_labels or [])
            merged = existing_labels + [l for l in inbound.labels if l not in existing_labels]
            existing_lead.wabis_labels = merged
        return
    
    # Create new Lead from subscriber
    # Get the next lead number
    latest_lead = db.query(Lead).filter(
        Lead.tenant_id == tenant_id
    ).order_by(Lead.lead_number.desc()).first()
    
    next_num = 1
    if latest_lead and latest_lead.lead_number:
        try:
            # lead_number format: "LEAD-00001"
            num_part = latest_lead.lead_number.split('-')[-1]
            next_num = int(num_part) + 1
        except (ValueError, IndexError):
            pass
    
    lead_number = f"LEAD-{next_num:05d}"
    
    # Get a system/default employee to assign as creator
    # For now, use None (will be NULL in DB), or get the first admin if needed
    from app.models.employee import Employee, RoleEnum
    creator = db.query(Employee).filter(
        Employee.tenant_id == tenant_id,
        Employee.role == RoleEnum.admin,
    ).first()
    
    creator_id = creator.id if creator else None
    
    # Create the lead
    new_lead = Lead(
        tenant_id=tenant_id,
        lead_number=lead_number,
        name=inbound.subscriber_name or phone,
        phone=phone,
        source=LeadSource.whatsapp,
        status=LeadPipelineStatus.new_lead,
        wabis_labels=inbound.labels or [],
        created_by_id=creator_id,
        is_active=True,
    )
    db.add(new_lead)
    db.flush()
    
    # Link subscriber to new lead
    subscriber.lead_id = new_lead.id
    db.flush()  # Ensure subscriber update is flushed


def _apply_postback_rule(
    db: Session,
    tenant_id: uuid.UUID,
    inbound: InboundMessage,
    subscriber: WaSubscriber,
) -> None:
    rule = (
        db.query(WaPostbackRule)
        .filter(
            WaPostbackRule.tenant_id == tenant_id,
            WaPostbackRule.postback_id == inbound.postback_id,
            WaPostbackRule.is_active.is_(True),
        )
        .first()
    )
    if rule is None:
        return

    if rule.action == WaPostbackAction.create_lead:
        _create_lead_from_subscriber(db, tenant_id, subscriber, rule)
    elif rule.action == WaPostbackAction.update_status:
        _update_lead_status(db, tenant_id, subscriber, rule)
    elif rule.action == WaPostbackAction.add_label:
        _add_lead_label(db, tenant_id, subscriber, rule)


def _create_lead_from_subscriber(
    db: Session,
    tenant_id: uuid.UUID,
    subscriber: WaSubscriber,
    rule: WaPostbackRule,
) -> None:
    if subscriber.lead_id:
        return

    from app.models.lead import Lead  # type: ignore

    lead = Lead(
        tenant_id=tenant_id,
        name=subscriber.name or subscriber.phone_number,
        phone=subscriber.phone_number,
        source=rule.lead_source or "wabis",
        label=rule.lead_label,
        status=rule.lead_status or "new_lead",
        priority=rule.lead_priority or "medium",
    )
    db.add(lead)
    db.flush()

    subscriber.lead_id = lead.id

    conv = (
        db.query(WaConversation)
        .filter(
            WaConversation.tenant_id == tenant_id,
            WaConversation.subscriber_id == subscriber.id,
        )
        .first()
    )
    if conv:
        conv.lead_id = lead.id

    db.flush()


def _update_lead_status(
    db: Session,
    tenant_id: uuid.UUID,
    subscriber: WaSubscriber,
    rule: WaPostbackRule,
) -> None:
    if not subscriber.lead_id or not rule.lead_status:
        return
    from app.models.lead import Lead  # type: ignore

    lead = (
        db.query(Lead)
        .filter(Lead.id == subscriber.lead_id, Lead.tenant_id == tenant_id)
        .first()
    )
    if lead:
        lead.status = rule.lead_status
        db.flush()


def _add_lead_label(
    db: Session,
    tenant_id: uuid.UUID,
    subscriber: WaSubscriber,
    rule: WaPostbackRule,
) -> None:
    if not subscriber.lead_id or not rule.lead_label:
        return
    from app.models.lead import Lead  # type: ignore

    lead = (
        db.query(Lead)
        .filter(Lead.id == subscriber.lead_id, Lead.tenant_id == tenant_id)
        .first()
    )
    if lead:
        lead.label = rule.lead_label
        db.flush()


def _upsert_new_message_status(
    db: Session,
    tenant_id: uuid.UUID,
    subscriber: WaSubscriber,
) -> None:
    """
    Create the WaStatus row on FIRST contact only.
    Subsequent WABIS triggers (label updates, postbacks) do NOT reset
    the status — the agent manually manages it after first contact.
    """
    wa_status = (
        db.query(WaStatus)
        .filter(WaStatus.tenant_id == tenant_id, WaStatus.subscriber_id == subscriber.id)
        .first()
    )
    if wa_status is None:
        wa_status = WaStatus(
            tenant_id=tenant_id,
            subscriber_id=subscriber.id,
            lead_id=subscriber.lead_id,
            status=WaStatusEnum.new_message,
        )
        db.add(wa_status)
    # If it already exists → leave it unchanged (agent owns the status)

    db.flush()


async def _maybe_auto_reply(
    db: Session,
    tenant_id: uuid.UUID,
    subscriber: WaSubscriber,
) -> None:
    settings = get_or_create_settings(db, tenant_id)
    if not settings.auto_reply_enabled or not settings.auto_reply_message:
        return
    provider = _provider(settings)
    try:
        await provider.send_text(
            phone=subscriber.phone_number,
            text=settings.auto_reply_message,
        )
    except Exception as exc:
        log.warning("Auto-reply failed for %s: %s", subscriber.phone_number, exc)


# ─────────────────────────────────────────────────────────────
# Auto-Sync: Periodic Fetch from WABIS
# ─────────────────────────────────────────────────────────────

def sync_subscribers_from_wabis(db: Session, tenant_id: uuid.UUID) -> Dict[str, Any]:
    """
    Note: WABIS subscribers are synced via WEBHOOK ONLY.
    This function is kept for backward compatibility but does NOT sync via API.
    
    WABIS does not provide a public /subscriber/list endpoint.
    Subscribers are created when they send inbound messages via the webhook.
    
    Returns: status indicating webhook-based sync is active
    """
    try:
        settings = get_or_create_settings(db, tenant_id)
        
        # Ensure provider is WABIS and has required config
        if settings.provider != WaProvider.wabis:
            return {
                "success": False,
                "synced_count": 0,
                "error": "Provider is not WABIS",
                "message": "Webhook sync only works with WABIS provider",
                "bots_synced": []
            }
        
        if not settings.wabis_api_token or not settings.wabis_phone_number_id:
            return {
                "success": False,
                "synced_count": 0,
                "error": "WABIS credentials not configured",
                "message": "API Token and Phone Number ID required for outbound messaging",
                "bots_synced": []
            }
        
        # Parse Bot IDs (comma-separated string)
        bot_ids = []
        if settings.wabis_bot_id:
            bot_ids = [bid.strip() for bid in settings.wabis_bot_id.split(',') if bid.strip()]
        
        if not bot_ids:
            return {
                "success": False,
                "synced_count": 0,
                "error": "No Bot IDs configured",
                "message": "Add at least one Bot ID to receive inbound messages",
                "bots_synced": []
            }
        
        # Check if webhook is configured
        # Subscribers will only appear when they send messages via the webhook
        subscriber_count = db.query(WaSubscriber).filter(
            WaSubscriber.tenant_id == tenant_id
        ).count()
        
        return {
            "success": True,
            "synced_count": subscriber_count,
            "error": None,
            "message": f"Webhook sync active for {len(bot_ids)} bot(s). {subscriber_count} subscriber(s) synced via webhook.",
            "bots_synced": bot_ids
        }
    
    except Exception as e:
        log.exception("Auto-sync status check failed")
        return {
            "success": False,
            "synced_count": 0,
            "error": str(e),
            "message": "Sync status check failed",
            "bots_synced": []
        }


def log_whatsapp_message_sent(
    db: Session,
    tenant_id: uuid.UUID,
    subscriber_id: uuid.UUID,
    message_text: str,
    template_id: Optional[uuid.UUID] = None,
    employee_id: Optional[uuid.UUID] = None,
    campaign_id: Optional[uuid.UUID] = None,
) -> WaMessageLog:
    """
    Log a WhatsApp message sent to a subscriber.
    Called every time a message is sent via the WhatsApp API.
    """
    log_entry = WaMessageLog(
        tenant_id=tenant_id,
        subscriber_id=subscriber_id,
        message_template_id=template_id,
        message_text=message_text,
        sent_by_employee_id=employee_id,
        campaign_id=campaign_id,
        delivery_status="sent",
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry


def update_message_delivery_status(
    db: Session,
    message_log_id: uuid.UUID,
    status: str,
    failure_reason: Optional[str] = None,
) -> Optional[WaMessageLog]:
    """
    Update delivery status from webhook callbacks (delivered, read, failed).
    """
    log_entry = db.query(WaMessageLog).filter(
        WaMessageLog.id == message_log_id
    ).first()
    if not log_entry:
        return None
    
    log_entry.delivery_status = status
    if status == "delivered":
        log_entry.delivered_at = datetime.now(tz=UTC)
    elif status == "read":
        log_entry.read_at = datetime.now(tz=UTC)
    elif status == "failed":
        log_entry.failure_reason = failure_reason
    
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry


def get_subscriber_message_history(
    db: Session,
    tenant_id: uuid.UUID,
    subscriber_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> tuple[List[WaMessageLog], int]:
    """
    Get message history for a subscriber with pagination.
    Returns list of WaMessageLog records and total count.
    """
    try:
        query = db.query(WaMessageLog).filter(
            WaMessageLog.tenant_id == tenant_id,
            WaMessageLog.subscriber_id == subscriber_id,
        )
        
        total = query.count()
        logs = query.order_by(WaMessageLog.sent_at.desc()).offset(offset).limit(limit).all()
        
        return logs, total
    except Exception as e:
        log.warning(f"Failed to retrieve message history for subscriber {subscriber_id}: {e}")
        return [], 0


# ─────────────────────────────────────────────────────────────
# Outbound webhook dispatcher
# ─────────────────────────────────────────────────────────────

async def _fire_outbound_webhooks(
    db: Session,
    tenant_id: uuid.UUID,
    subscriber: WaSubscriber,
    inbound: "InboundMessage",
    event: str,
) -> None:
    """
    Fetch all active outbound webhooks for this tenant that match the event,
    build the subscriber payload from the selected data_fields,
    and POST to each URL asynchronously.
    Updates last_fired_at, last_status_code, and counters.
    """
    import httpx
    import datetime as dt

    try:
        webhooks = (
            db.query(WaOutboundWebhook)
            .filter(
                WaOutboundWebhook.tenant_id == tenant_id,
                WaOutboundWebhook.is_active.is_(True),
            )
            .all()
        )
    except Exception as exc:
        log.warning("Outbound webhooks query failed: %s", exc)
        return

    if not webhooks:
        return

    # Get the current WA status for the subscriber
    wa_status_row = (
        db.query(WaStatus)
        .filter(WaStatus.tenant_id == tenant_id, WaStatus.subscriber_id == subscriber.id)
        .first()
    )
    wa_status_code = wa_status_row.status if wa_status_row else WaStatusEnum.new_message

    # Full subscriber data pool
    full_data: Dict[str, Any] = {
        "subscriber_id":   str(subscriber.id),
        "name":            subscriber.name or "",
        "phone":           subscriber.phone_number or "",
        "email":           "",  # WaSubscriber has no email field
        "wabis_status":    str(wa_status_code),
        "wa_status_code":  str(wa_status_code),
        "labels":          subscriber.wabis_labels or [],
        "postback_id":     inbound.postback_id or "",
        "postback_title":  inbound.postback_title or "",
        "date_of_birth":   None,
        "location":        None,
        "input_flow_data": inbound.raw_payload or {},
    }

    now = dt.datetime.utcnow()

    async with httpx.AsyncClient(timeout=10.0) as client:
        for wh in webhooks:
            # Check trigger event matches
            trigger_events = wh.trigger_events or ["new_message", "postback"]
            if event not in trigger_events:
                continue

            # Check postback filter (if set)
            if wh.postback_filter and inbound.postback_id:
                if inbound.postback_id not in wh.postback_filter:
                    continue

            # Build filtered payload
            fields = wh.data_fields or list(full_data.keys())
            subscriber_payload = {f: full_data[f] for f in fields if f in full_data}

            payload = {
                "event":        event,
                "source":       "miguel",
                "tenant_id":    str(tenant_id),
                "webhook_name": wh.name,
                "timestamp":    now.isoformat() + "Z",
                "subscriber":   subscriber_payload,
            }

            headers = {
                "Content-Type":   "application/json",
                "X-Miguel-Secret": wh.secret or "",
                "User-Agent":     "Miguel-Outbound-Webhook/1.0",
            }

            try:
                resp = await client.post(wh.url, json=payload, headers=headers)
                status_code = resp.status_code
                ok = 200 <= status_code < 300
            except Exception as exc:
                log.warning("Outbound webhook '%s' failed: %s", wh.name, exc)
                status_code = None
                ok = False

            # Update stats
            try:
                wh.last_fired_at    = now
                wh.last_status_code = status_code
                wh.total_fired      = (wh.total_fired or 0) + 1
                if not ok:
                    wh.total_failed = (wh.total_failed or 0) + 1
                db.commit()
            except Exception as exc:
                log.warning("Failed to update webhook stats: %s", exc)
                db.rollback()

