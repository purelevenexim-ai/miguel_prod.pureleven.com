"""
WhatsApp Engine — API Router
==============================
All routes are under /api/wa/
Public inbound webhook: POST /api/wa/inbound/{tenant_id}  (no auth, secret header)
Everything else requires tenant JWT auth.

Uses synchronous Session (consistent with the rest of the app).
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.auth.tenant import get_current_tenant_user, require_roles
from app.database.session import get_db
from app.models.employee import RoleEnum
from app.models.lead import Lead  # For fetching linked lead data
from app.models.wa_engine import (
    WaCampaign,
    WaCampaignRecipient,
    WaConversation,
    WaMessage,
    WaMessageDirection,
    WaOutboundWebhook,
    WaSettings,
    WaSubscriber,
)
from app.modules.wa_engine import schemas, service
from app.modules.wa_engine.providers.meta import MetaProvider
from app.modules.wa_engine.providers.wabis import WabisProvider
from pydantic import BaseModel as PydanticBaseModel

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wa", tags=["WhatsApp Engine"])


def _safe_meta_status_diagnostics(statuses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return a bounded, content-free summary for rejected status callbacks."""
    diagnostics: List[Dict[str, Any]] = []
    for entry in statuses[:20]:
        errors = entry.get("errors") if isinstance(entry, dict) else []
        error = errors[0] if isinstance(errors, list) and errors and isinstance(errors[0], dict) else {}
        provider_id = str(entry.get("id") or "") if isinstance(entry, dict) else ""
        diagnostics.append({
            "provider_id_suffix": provider_id[-16:],
            "status": str(entry.get("status") or "")[:24] if isinstance(entry, dict) else "",
            "error_code": str(error.get("code") or "")[:24],
            "error_title": str(error.get("title") or error.get("message") or "")[:240],
        })
    return diagnostics


def _restricted_meta_status_entries(
    db: Session,
    tenant_id: uuid.UUID,
    settings: WaSettings,
    raw: Dict[str, Any],
    statuses: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Match unsigned callbacks to outbound messages without trusting payload data.

    This fallback exists for WABIS-managed Meta apps where the app owner keeps
    the HMAC App Secret. A callback is eligible only when its sender phone ID,
    unguessable provider message ID, tenant, direction, and recipient all match
    an outbound message already stored by Miguel.
    """
    try:
        value = raw["entry"][0]["changes"][0]["value"]
        callback_phone_id = str(
            (value.get("metadata") or {}).get("phone_number_id") or ""
        ).strip()
    except (IndexError, KeyError, TypeError, AttributeError):
        return []

    expected_phone_ids = {
        str(value).strip()
        for value in (
            settings.meta_phone_number_id,
            settings.wabis_phone_number_id,
        )
        if str(value or "").strip()
    }
    if (
        not callback_phone_id
        or callback_phone_id not in expected_phone_ids
    ):
        return []

    provider_ids = {
        str(entry.get("id") or "").strip()
        for entry in statuses
        if isinstance(entry, dict) and entry.get("id")
    }
    if not provider_ids:
        return []

    known_rows = (
        db.query(
            WaMessage.provider_message_id,
            WaSubscriber.phone_number,
        )
        .join(
            WaConversation,
            WaConversation.id == WaMessage.conversation_id,
        )
        .join(
            WaSubscriber,
            WaSubscriber.id == WaConversation.subscriber_id,
        )
        .filter(
            WaMessage.tenant_id == tenant_id,
            WaMessage.direction == WaMessageDirection.outbound,
            WaMessage.provider_message_id.in_(provider_ids),
        )
        .all()
    )
    known_recipient_by_provider_id = {
        provider_message_id: "".join(
            character
            for character in (phone_number or "")
            if character.isdigit()
        )
        for provider_message_id, phone_number in known_rows
    }

    matched: List[Dict[str, Any]] = []
    for entry in statuses:
        provider_message_id = str(entry.get("id") or "").strip()
        known_recipient = known_recipient_by_provider_id.get(
            provider_message_id
        )
        callback_recipient = "".join(
            character
            for character in str(entry.get("recipient_id") or "")
            if character.isdigit()
        )
        if not known_recipient:
            continue
        if (
            callback_recipient
            and known_recipient[-10:] != callback_recipient[-10:]
        ):
            continue
        matched.append(entry)
    return matched


# ─────────────────────────────────────────────────────────────
# Settings
# ─────────────────────────────────────────────────────────────

@router.get("/settings", response_model=schemas.WaSettingsResponse)
def get_settings(
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    row = service.get_or_create_settings(db, current_user.tenant_id)
    return _build_settings_response(row, request)


@router.post("/settings", response_model=schemas.WaSettingsResponse)
def save_settings(
    data: schemas.WaSettingsSave,
    current_user=Depends(require_roles(RoleEnum.admin)),
    db: Session = Depends(get_db),
    request: Request = None,
):
    row = service.save_settings(db, current_user.tenant_id, data)
    db.commit()
    return _build_settings_response(row, request)


@router.post("/settings/test-connection", response_model=schemas.WaSettingsTestResponse)
async def test_connection(
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    success, message = await service.test_connection(db, current_user.tenant_id)
    return schemas.WaSettingsTestResponse(success=success, message=message)


@router.get("/settings/diagnostic")
def diagnostic_check(
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    """Diagnostic endpoint to identify why WABIS leads aren't syncing."""
    settings = service.get_or_create_settings(db, current_user.tenant_id)
    from app.models.wa_engine import WaSubscriber
    from app.models.lead import Lead
    
    # Count subscribers and leads
    subscriber_count = db.query(WaSubscriber).filter(
        WaSubscriber.tenant_id == current_user.tenant_id
    ).count()
    
    wa_leads = db.query(Lead).filter(
        Lead.tenant_id == current_user.tenant_id,
        Lead.source == "whatsapp",
    ).count()
    
    issues = []
    
    # Check 1: Provider
    if settings.provider.value != "wabis":
        issues.append(f"⚠️ Provider is '{settings.provider.value}', not 'wabis'")
    
    # Check 2: API Token
    if not settings.wabis_api_token:
        issues.append("❌ WABIS API Token is NOT set — cannot send outbound messages")
    
    # Check 3: Phone Number ID
    if not settings.wabis_phone_number_id:
        issues.append("❌ WABIS Phone Number ID is NOT set — cannot send outbound messages")
    
    # Check 4: Bot IDs
    bot_ids = []
    if settings.wabis_bot_id:
        bot_ids = [b.strip() for b in settings.wabis_bot_id.split(',') if b.strip()]
    
    if not bot_ids:
        issues.append("❌ NO Bot IDs configured — WABIS won't route messages to your webhook")
    
    # Check 5: Inbound Webhook Secret
    if not settings.inbound_secret:
        issues.append("⚠️ Inbound secret is empty — webhook security may be compromised")
    
    # Check 6: No subscribers (means webhook never fired)
    if subscriber_count == 0 and not issues:
        issues.append("ℹ️ No WABIS subscribers synced yet — WABIS webhook hasn't fired, or webhook URL not configured in WABIS dashboard")
    
    return {
        "provider": settings.provider.value,
        "has_api_token": bool(settings.wabis_api_token),
        "has_phone_number_id": bool(settings.wabis_phone_number_id),
        "bot_ids": bot_ids,
        "bot_count": len(bot_ids),
        "inbound_secret_set": bool(settings.inbound_secret),
        "subscriber_count": subscriber_count,
        "whatsapp_leads_count": wa_leads,
        "issues": issues if issues else ["✅ All checks passed! If no leads appear, make sure WABIS webhook is configured."],
    }


@router.post("/settings/sync-now")
def sync_subscribers_now(
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    """Manually trigger a sync of WABIS subscribers (normally runs every 30 sec)."""
    result = service.sync_subscribers_from_wabis(db, current_user.tenant_id)
    return result


@router.get("/settings/webhook-url")
def get_webhook_url(
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    row = service.get_or_create_settings(db, current_user.tenant_id)
    base = _build_base_url(request)
    return {
        "inbound_url":    f"{base}/api/wa/inbound/{current_user.tenant_id}",
        "inbound_secret": row.inbound_secret,
        "instructions": (
            "In WABIS → Settings → Out-bound Webhook, set the URL above "
            "and add header  X-Webhook-Secret: <inbound_secret>"
        ),
    }


# ─────────────────────────────────────────────────────────────
# Postback Rules
# ─────────────────────────────────────────────────────────────

@router.get("/postback-rules", response_model=List[schemas.WaPostbackRuleResponse])
def list_postback_rules(
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    return service.list_postback_rules(db, current_user.tenant_id)


@router.post(
    "/postback-rules",
    response_model=schemas.WaPostbackRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_postback_rule(
    data: schemas.WaPostbackRuleCreate,
    current_user=Depends(require_roles(RoleEnum.admin)),
    db: Session = Depends(get_db),
):
    row = service.create_postback_rule(db, current_user.tenant_id, data)
    db.commit()
    db.refresh(row)
    return row


@router.put("/postback-rules/{rule_id}", response_model=schemas.WaPostbackRuleResponse)
def update_postback_rule(
    rule_id: uuid.UUID,
    data: schemas.WaPostbackRuleUpdate,
    current_user=Depends(require_roles(RoleEnum.admin)),
    db: Session = Depends(get_db),
):
    try:
        row = service.update_postback_rule(db, current_user.tenant_id, rule_id, data)
        db.commit()
        db.refresh(row)
        return row
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/postback-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_postback_rule(
    rule_id: uuid.UUID,
    current_user=Depends(require_roles(RoleEnum.admin)),
    db: Session = Depends(get_db),
):
    ok = service.delete_postback_rule(db, current_user.tenant_id, rule_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Postback rule not found")
    db.commit()


# ─────────────────────────────────────────────────────────────
# Campaign Types
# ─────────────────────────────────────────────────────────────

@router.get("/campaign-types", response_model=List[schemas.WaCampaignTypeResponse])
def list_campaign_types(
    active_only: bool = Query(False),
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    return service.list_campaign_types(db, current_user.tenant_id, active_only)


@router.post(
    "/campaign-types",
    response_model=schemas.WaCampaignTypeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_campaign_type(
    data: schemas.WaCampaignTypeCreate,
    current_user=Depends(require_roles(RoleEnum.admin)),
    db: Session = Depends(get_db),
):
    row = service.create_campaign_type(
        db, current_user.tenant_id, data, current_user.id
    )
    db.commit()
    db.refresh(row)
    return row


@router.put("/campaign-types/{ct_id}", response_model=schemas.WaCampaignTypeResponse)
def update_campaign_type(
    ct_id: uuid.UUID,
    data: schemas.WaCampaignTypeUpdate,
    current_user=Depends(require_roles(RoleEnum.admin)),
    db: Session = Depends(get_db),
):
    try:
        row = service.update_campaign_type(db, current_user.tenant_id, ct_id, data)
        db.commit()
        db.refresh(row)
        return row
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/campaign-types/{ct_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign_type(
    ct_id: uuid.UUID,
    current_user=Depends(require_roles(RoleEnum.admin)),
    db: Session = Depends(get_db),
):
    ok = service.delete_campaign_type(db, current_user.tenant_id, ct_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Campaign type not found")
    db.commit()


# ─────────────────────────────────────────────────────────────
# Subscribers
# ─────────────────────────────────────────────────────────────

def _serialize_subscriber(db: Session, sub: WaSubscriber) -> Dict[str, Any]:
    lead_name = None
    if sub.lead_id:
        lead = db.query(Lead).filter(Lead.id == sub.lead_id).first()
        if lead:
            lead_name = lead.name

    return {
        "id": sub.id,
        "tenant_id": sub.tenant_id,
        "subscriber_id": sub.subscriber_id,
        "phone_number": sub.phone_number,
        "name": sub.name,
        "wabis_labels": sub.wabis_labels,
        "last_postback_id": sub.last_postback_id,
        "lead_id": sub.lead_id,
        "is_opted_out": sub.is_opted_out,
        "first_seen_at": sub.first_seen_at,
        "last_seen_at": sub.last_seen_at,
        "lead_name": lead_name,
        "wa_status": sub.wa_status.status if sub.wa_status else None,
    }

@router.get("/subscribers", response_model=List[schemas.WaSubscriberResponse])
def list_subscribers(
    skip:   int = Query(0, ge=0),
    limit:  int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    phone:  Optional[str] = Query(None),   # exact phone lookup for chat drawer
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    if phone:
        clean = "".join(c for c in phone if c.isdigit())
        rows = (
            db.query(WaSubscriber)
            .filter(
                WaSubscriber.tenant_id == current_user.tenant_id,
                WaSubscriber.phone_number == clean,
            )
            .limit(5)
            .all()
        )
        return [_serialize_subscriber(db, r) for r in rows]

    rows = service.list_subscribers(
        db, current_user.tenant_id, skip=skip, limit=limit, search=search
    )
    return [_serialize_subscriber(db, r) for r in rows]


@router.get("/subscribers/as-leads/list")
def list_subscribers_as_leads(
    page:    int = Query(1, ge=1),
    limit:   int = Query(100, ge=1, le=200),
    search:  Optional[str] = Query(None),
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    """
    Return WABIS subscribers for Audience tab display.
    
    Returns BOTH:
    - wabis_status: WhatsApp-specific status (new_message, replied, hot, cold, etc.)
    - lead_status: CRM lead status if linked (new_lead, interested, qualified, etc.)
    
    These are two completely separate status entities.
    
    Note: Subscribers only appear after they send a message via the webhook.
    If no subscribers exist, returns empty results (not an error).
    """
    try:
        from sqlalchemy.orm import joinedload
        
        query = db.query(WaSubscriber).filter(
            WaSubscriber.tenant_id == current_user.tenant_id
        ).options(
            joinedload(WaSubscriber.wa_status)  # Eagerly load WaStatus relationship
        )
        
        if search:
            query = query.filter(
                (WaSubscriber.name.ilike(f"%{search}%")) |
                (WaSubscriber.phone_number.ilike(f"%{search}%"))
            )
        
        total = query.count()
        subs = query.order_by(WaSubscriber.last_seen_at.desc()).offset(
            (page - 1) * limit
        ).limit(limit).all()
        
        # Convert to lead-like response with BOTH WABIS and CRM status
        results = []
        for sub in subs:
            # Get WABIS-specific status
            wa_status_record = sub.wa_status
            wabis_status = wa_status_record.status if wa_status_record else "new_message"
            
            # Get lead status if linked
            lead_status = None
            if sub.lead_id:
                # Load the lead to get its CRM status
                lead = db.query(Lead).filter(Lead.id == sub.lead_id).first()
                if lead:
                    lead_status = lead.status
            
            results.append({
                "id": str(sub.id),
                "name": sub.name or "Unknown",
                "phone": sub.phone_number,
                "email": None,
                "wabis_status": wabis_status,      # ← WhatsApp status (new_message, replied, hot, cold, etc.)
                "lead_status": lead_status,        # ← CRM status if linked (new_lead, interested, etc.) or None
                "city": None,
                "product_interest": None,
                "opted_out": sub.is_opted_out,
                "wabis_labels": sub.wabis_labels or [],
                "postback_ids": sub.postback_ids or [],
                "last_postback_id": sub.last_postback_id,
                "updated_at": sub.last_seen_at.isoformat() if sub.last_seen_at else None,
                "created_at": sub.first_seen_at.isoformat() if sub.first_seen_at else None,
            })
        
        return {
            "total": total,
            "page": page,
            "limit": limit,
            "results": results,
        }
    
    except Exception as e:
        log.exception(f"Failed to list WABIS subscribers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load WABIS subscribers: {str(e)}")


@router.get("/subscribers/{sub_id}", response_model=schemas.WaSubscriberResponse)
def get_subscriber(
    sub_id: uuid.UUID,
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(WaSubscriber)
        .filter(WaSubscriber.id == sub_id, WaSubscriber.tenant_id == current_user.tenant_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return _serialize_subscriber(db, row)


@router.patch("/subscribers/{sub_id}/labels")
def update_subscriber_labels(
    sub_id: uuid.UUID,
    body: Dict[str, Any],
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    """
    Replace the label list for a subscriber.
    Body: { "labels": ["Label1", "Label2", ...] }
    """
    row = (
        db.query(WaSubscriber)
        .filter(WaSubscriber.id == sub_id, WaSubscriber.tenant_id == current_user.tenant_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Subscriber not found")

    labels = body.get("labels")
    if not isinstance(labels, list):
        raise HTTPException(status_code=422, detail="labels must be a list")

    # Sanitise: trim, deduplicate, drop empties
    cleaned = list(dict.fromkeys(l.strip() for l in labels if str(l).strip()))
    row.wabis_labels = cleaned
    db.commit()
    db.refresh(row)
    return {"id": str(row.id), "labels": row.wabis_labels}


@router.get("/subscribers/{sub_id}/message-log")
def get_subscriber_message_log(
    sub_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    """
    Get message history for a subscriber with delivery status and pagination.
    """
    # Verify subscriber exists and belongs to tenant
    subscriber = (
        db.query(WaSubscriber)
        .filter(WaSubscriber.id == sub_id, WaSubscriber.tenant_id == current_user.tenant_id)
        .first()
    )
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    
    # Get message history
    logs, total = wa_service.get_subscriber_message_history(
        db=db,
        tenant_id=current_user.tenant_id,
        subscriber_id=sub_id,
        limit=limit,
        offset=skip,
    )
    
    return {
        "subscriber_id": sub_id,
        "total": total,
        "skip": skip,
        "limit": limit,
        "messages": [
            {
                "id": str(log.id),
                "message_text": log.message_text,
                "sent_at": log.sent_at.isoformat() if log.sent_at else None,
                "delivered_at": log.delivered_at.isoformat() if log.delivered_at else None,
                "read_at": log.read_at.isoformat() if log.read_at else None,
                "delivery_status": log.delivery_status,
                "failure_reason": log.failure_reason,
                "template_id": str(log.message_template_id) if log.message_template_id else None,
            }
            for log in logs
        ],
    }


# ─────────────────────────────────────────────────────────────
# Conversations
# ─────────────────────────────────────────────────────────────

@router.get("/conversations/inbox")
def list_conversations_inbox(
    page:   int = Query(1, ge=1),
    limit:  int = Query(50, ge=1, le=200),
    unread_only: bool = Query(False),
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    """
    Get WhatsApp inbox: all conversations with subscriber details and last message preview.
    
    Returns:
    - Conversations sorted by last_message_at (newest first)
    - Subscriber name and phone
    - Last message preview text
    - Unread count
    - Last message timestamp
    
    Optional filter: unread_only=true to show only conversations with unread_count > 0
    """
    try:
        from sqlalchemy import and_
        
        query = db.query(WaConversation).filter(
            WaConversation.tenant_id == current_user.tenant_id
        )
        
        if unread_only:
            query = query.filter(WaConversation.unread_count > 0)
        
        total = query.count()
        conversations = query.order_by(
            WaConversation.unread_count.desc(),  # Unread first
            WaConversation.last_message_at.desc().nullslast()  # Then by recency
        ).offset((page - 1) * limit).limit(limit).all()
        
        results = []
        for conv in conversations:
            # Get subscriber details
            subscriber = db.query(WaSubscriber).filter(
                WaSubscriber.id == conv.subscriber_id
            ).first()
            
            if not subscriber:
                continue
            
            # Get last message for preview
            last_message = None
            # Note: WaConversation doesn't have last_message_id, only last_message_at
            # To get message preview, query the latest message by conversation_id
            from app.models.wa_engine import WaMessage
            msg = db.query(WaMessage).filter(
                WaMessage.conversation_id == conv.id
            ).order_by(WaMessage.sent_at.desc()).first()
            if msg:
                last_message = msg.content[:100] if msg.content else "[no text]"
            
            results.append({
                "conversation_id": str(conv.id),
                "subscriber_id": str(subscriber.id),
                "subscriber_name": subscriber.name or "Unknown",
                "subscriber_phone": subscriber.phone_number,
                "subscriber_avatar": None,
                "last_message_preview": last_message or "(no messages yet)",
                "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else None,
                "last_message_direction": conv.last_message_direction,  # "inbound" or "outbound"
                "unread_count": conv.unread_count or 0,
                "wa_status": subscriber.wa_status.status if subscriber.wa_status else "new_message",
            })
        
        return {
            "total": total,
            "page": page,
            "limit": limit,
            "results": results,
        }
    
    except Exception as e:
        log.exception(f"Failed to load conversations inbox: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load inbox: {str(e)}")


@router.get("/conversations", response_model=List[schemas.WaConversationResponse])
def list_conversations(
    skip:          int           = Query(0, ge=0),
    limit:         int           = Query(50, ge=1, le=200),
    subscriber_id: Optional[str] = Query(None),   # filter by subscriber UUID for chat drawer
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    query = (
        db.query(WaConversation)
        .filter(WaConversation.tenant_id == current_user.tenant_id)
        .order_by(WaConversation.last_message_at.desc().nullslast())
    )
    if subscriber_id:
        import uuid as _uuid
        try:
            sid = _uuid.UUID(subscriber_id)
            query = query.filter(WaConversation.subscriber_id == sid)
        except ValueError:
            pass
    convs = query.offset(skip).limit(limit).all()
    enriched = []
    for conv in convs:
        sub = db.query(WaSubscriber).filter(WaSubscriber.id == conv.subscriber_id).first()
        item = schemas.WaConversationResponse.model_validate(conv)
        if sub:
            item.subscriber_name  = sub.name
            item.subscriber_phone = sub.phone_number
        enriched.append(item)
    return enriched



@router.get(
    "/conversations/{conv_id}/messages",
    response_model=List[schemas.WaMessageResponse],
)
def list_messages(
    conv_id: uuid.UUID,
    skip:    int = Query(0, ge=0),
    limit:   int = Query(100, ge=1, le=500),
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    return service.list_messages(db, current_user.tenant_id, conv_id, skip=skip, limit=limit)


@router.post(
    "/conversations/{conv_id}/send",
    response_model=schemas.WaMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conv_id: uuid.UUID,
    data:    schemas.WaMessageSend,
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    try:
        msg = await service.send_message(
            db, current_user.tenant_id, conv_id, data,
            employee_id=current_user.id,
        )
        db.commit()
        db.refresh(msg)
        return msg
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ─────────────────────────────────────────────────────────────
# WhatsApp Status
# ─────────────────────────────────────────────────────────────

@router.get("/statuses", response_model=List[schemas.WaStatusResponse])
def list_statuses(
    skip:  int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    return service.list_wa_statuses(db, current_user.tenant_id, skip=skip, limit=limit)


@router.put("/statuses/{subscriber_id}", response_model=schemas.WaStatusResponse)
def update_status(
    subscriber_id: uuid.UUID,
    data: schemas.WaStatusUpdate,
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    row = service.update_wa_status(
        db, current_user.tenant_id, subscriber_id, data,
        employee_id=current_user.id,
    )
    db.commit()
    db.refresh(row)
    return row


# ─────────────────────────────────────────────────────────────
# Campaigns
# ─────────────────────────────────────────────────────────────

@router.post(
    "/send-notification",
    response_model=schemas.SendNotificationResponse,
)
async def send_notification(
    data: schemas.SendNotificationRequest,
    current_user=Depends(require_roles(RoleEnum.admin)),
    db: Session = Depends(get_db),
):
    """Send a single outbound WhatsApp message via WABIS workflow URL."""
    result = await service.send_notification(
        db=db,
        tenant_id=current_user.tenant_id,
        phone=data.phone,
        campaign_type_id=data.campaign_type_id,
        workflow_url=data.workflow_url,
        variables=data.variables,
    )
    return schemas.SendNotificationResponse(
        success=result.get("success", False),
        message=result.get("message", ""),
        details=result,
    )


@router.post(
    "/send-direct",
    response_model=schemas.WaSendDirectResponse,
    status_code=status.HTTP_200_OK,
)
async def send_direct_message(
    data: schemas.WaSendDirectRequest,
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    """
    Send a plain text or media WhatsApp message directly to any phone number.
    Uses WABIS /api/v1/whatsapp/send — requires apiToken + phone_number_id in WA Settings.
    Supports: text, images, documents, voice notes (via base64 or URL)
    """
    result = await service.send_direct_message(
        db=db,
        tenant_id=current_user.tenant_id,
        phone_number=data.phone_number,
        message=data.message_text or data.message,  # fallback to deprecated field
        employee_id=current_user.id,
    )
    return schemas.WaSendDirectResponse(
        success=result.get("success", False),
        message=result.get("message", ""),
        wa_message_id=result.get("wa_message_id"),
        subscriber_id=result.get("subscriber_id"),
        raw_response=result.get("raw_response"),
    )


@router.post(
    "/trigger-bot",
    response_model=schemas.WaSendDirectResponse,
    status_code=status.HTTP_200_OK,
)
async def trigger_bot_flow(
    data: schemas.WaTriggerBotRequest,
    current_user=Depends(require_roles(RoleEnum.admin)),
    db: Session = Depends(get_db),
):
    """Trigger a WABIS bot flow for a specific phone number."""
    result = await service.trigger_bot_flow(
        db=db,
        tenant_id=current_user.tenant_id,
        phone_number=data.phone_number,
        bot_flow_unique_id=data.bot_flow_unique_id,
    )
    return schemas.WaSendDirectResponse(
        success=result.get("success", False),
        message=result.get("message", ""),
        raw_response=result.get("raw_response"),
    )


@router.get("/campaigns", response_model=List[schemas.WaCampaignResponse])
def list_campaigns(
    skip:  int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    return service.list_campaigns(db, current_user.tenant_id, skip=skip, limit=limit)


@router.post(
    "/campaigns",
    response_model=schemas.WaCampaignResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_campaign(
    data: schemas.WaCampaignCreate,
    current_user=Depends(require_roles(RoleEnum.admin)),
    db: Session = Depends(get_db),
):
    try:
        campaign = service.create_campaign(
            db, current_user.tenant_id, data,
            employee_id=current_user.id,
        )
        db.commit()
        db.refresh(campaign)
        return campaign
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/campaigns/{campaign_id}/start", response_model=schemas.WaCampaignResponse)
async def start_campaign(
    campaign_id: uuid.UUID,
    current_user=Depends(require_roles(RoleEnum.admin)),
    db: Session = Depends(get_db),
):
    try:
        campaign = await service.start_campaign(
            db, current_user.tenant_id, campaign_id,
            employee_id=current_user.id,
        )
        db.commit()
        db.refresh(campaign)
        return campaign
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/campaigns/{campaign_id}/report", response_model=schemas.WaCampaignDetail)
def campaign_report(
    campaign_id: uuid.UUID,
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    campaign = (
        db.query(WaCampaign)
        .filter(WaCampaign.id == campaign_id, WaCampaign.tenant_id == current_user.tenant_id)
        .first()
    )
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    recipients = (
        db.query(WaCampaignRecipient)
        .filter(WaCampaignRecipient.campaign_id == campaign_id)
        .all()
    )

    detail = schemas.WaCampaignDetail.model_validate(campaign)
    detail.recipients = [
        schemas.WaCampaignRecipientResponse.model_validate(r) for r in recipients
    ]
    return detail


@router.get("/templates")
async def get_templates(
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    """Fetch approved WhatsApp templates from WABIS."""
    settings = service.get_or_create_settings(db, current_user.tenant_id)
    if not settings.wabis_api_token or not settings.wabis_phone_number_id:
        raise HTTPException(status_code=422, detail="WABIS not configured — set API Token and Phone Number ID")
    try:
        async with __import__("httpx").AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://bot.wabis.in/api/v1/whatsapp/template/list",
                data={"apiToken": settings.wabis_api_token, "phone_number_id": settings.wabis_phone_number_id},
            )
            data = resp.json()
        if data.get("status") == "1":
            msg = data.get("message", {})
            templates = msg if isinstance(msg, list) else [msg] if msg else []
            return {"success": True, "templates": templates}
        return {"success": False, "templates": [], "error": data.get("message", "Failed to fetch templates")}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/send-template-direct")
async def send_template_direct(
    body: Dict[str, Any],
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    """
    Send a WhatsApp template message via Meta Cloud API (using creds from WABIS template list).
    Body: { phone_number, template_name, template_id, locale, access_token, components }
    Falls back to WABIS /whatsapp/send with body_content text if no Meta creds provided.
    """
    phone        = "".join(c for c in (body.get("phone_number") or "") if c.isdigit())
    tpl_name     = (body.get("template_name") or "").strip()
    tpl_id       = (body.get("template_id") or "").strip()
    locale       = (body.get("locale") or "en").strip()
    meta_token   = (body.get("access_token") or "").strip()
    body_text    = (body.get("body_text") or "").strip()       # fallback plain text
    components   = body.get("components") or []                # template variable components

    if not phone:
        raise HTTPException(status_code=422, detail="phone_number is required")
    if not tpl_name and not body_text:
        raise HTTPException(status_code=422, detail="template_name or body_text is required")

    settings = service.get_or_create_settings(db, current_user.tenant_id)

    # ── Strategy 1: Meta Cloud API (preferred — sends real template) ──
    if meta_token and tpl_name and settings.wabis_phone_number_id:
        try:
            meta_payload = {
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "template",
                "template": {
                    "name": tpl_name,
                    "language": {"code": locale},
                },
            }
            if components:
                meta_payload["template"]["components"] = components

            async with __import__("httpx").AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"https://graph.facebook.com/v18.0/{settings.wabis_phone_number_id}/messages",
                    headers={"Authorization": f"Bearer {meta_token}", "Content-Type": "application/json"},
                    json=meta_payload,
                )
                data = resp.json()
            log.info("Meta template send → %s body=%s", resp.status_code, data)
            if resp.status_code == 200 or data.get("messages"):
                msg_id = (data.get("messages") or [{}])[0].get("id", "")
                return {
                    "success":       True,
                    "wa_message_id": msg_id,
                    "message":       "Template sent via Meta API",
                    "raw":           data,
                }
            # Meta returned error
            err = data.get("error", {}).get("message", str(data))
            log.warning("Meta template send failed: %s", err)
            # Fall through to WABIS plain send
        except Exception as exc:
            log.warning("Meta template send exception: %s — falling back to WABIS", exc)

    # ── Strategy 2: WABIS /whatsapp/send (sends body_text as plain text) ──
    if not settings.wabis_api_token or not settings.wabis_phone_number_id:
        raise HTTPException(status_code=422, detail="WABIS not configured")

    text_to_send = body_text or f"[Template: {tpl_name}]"
    try:
        async with __import__("httpx").AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://bot.wabis.in/api/v1/whatsapp/send",
                data={
                    "apiToken":        settings.wabis_api_token,
                    "phone_number_id": settings.wabis_phone_number_id,
                    "message":         text_to_send,
                    "phone_number":    phone,
                },
            )
            data = resp.json()
        ok = data.get("status") == "1"
        return {
            "success":       ok,
            "wa_message_id": data.get("wa_message_id"),
            "message":       data.get("message", ""),
            "raw":           data,
            "via":           "wabis_fallback",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/conversation-by-phone")
async def get_conversation_by_phone(
    phone: str = Query(...),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    """Get conversation history for a phone number from WABIS."""
    from datetime import datetime, timezone, timedelta
    from app.models.wa_engine import WaSubscriber
    import logging

    settings = service.get_or_create_settings(db, current_user.tenant_id)
    if not settings.wabis_api_token or not settings.wabis_phone_number_id:
        return {"success": False, "messages": [], "error": "WABIS not configured"}

    clean = "".join(c for c in phone if c.isdigit())

    # ── Fallback: check our local WaSubscriber last_seen_at ──────────────────
    # When WABIS fires an inbound webhook, we record last_seen_at locally.
    # This is reliable even if WABIS returns no messages in the conversation API.
    local_last_seen = None
    try:
        sub = (
            db.query(WaSubscriber)
            .filter(
                WaSubscriber.tenant_id == current_user.tenant_id,
                WaSubscriber.phone_number.in_([clean, "+" + clean])
            )
            .order_by(WaSubscriber.last_seen_at.desc())
            .first()
        )
        if sub and sub.last_seen_at:
            local_last_seen = sub.last_seen_at
            if local_last_seen.tzinfo is None:
                local_last_seen = local_last_seen.replace(tzinfo=timezone.utc)
            logging.info(f"[24H WINDOW] Local subscriber found: phone={clean} last_seen_at={local_last_seen.isoformat()}")
    except Exception as e:
        logging.warning(f"[24H WINDOW] Could not query local subscriber: {e}")

    try:
        async with __import__("httpx").AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://bot.wabis.in/api/v1/whatsapp/get/conversation",
                data={
                    "apiToken":        settings.wabis_api_token,
                    "phone_number_id": settings.wabis_phone_number_id,
                    "phone_number":    clean,
                    "limit":           str(limit),
                    "offset":          "0",
                },
            )
            data = resp.json()
        msgs = data.get("message", []) if data.get("status") == "1" else []

        # ── Check 24h window from WABIS messages ─────────────────────────────
        window_open = False
        last_inbound_at = None
        if isinstance(msgs, list):
            for m in msgs:
                sender = m.get("sender", "")
                if sender not in ("bot", "agent", "automation"):
                    ts_str = m.get("conversation_time") or m.get("delivery_status_updated_at")
                    if ts_str:
                        try:
                            if "T" in ts_str:
                                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                            else:
                                ts = datetime.strptime(ts_str[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                            if not last_inbound_at or ts > last_inbound_at:
                                last_inbound_at = ts
                        except Exception:
                            pass

        # ── Fallback: use local last_seen_at if WABIS returned no messages ───
        # WABIS webhook fires when subscriber interacts with bot — that counts
        # as a customer-initiated message, opening the 24h window.
        if not last_inbound_at and local_last_seen:
            last_inbound_at = local_last_seen
            logging.info(f"[24H WINDOW] Using local last_seen_at as fallback: {last_inbound_at.isoformat()}")

        if last_inbound_at:
            now = datetime.now(timezone.utc)
            time_diff = now - last_inbound_at
            window_open = time_diff < timedelta(hours=24)
            logging.info(f"[24H WINDOW] phone={clean} last_inbound={last_inbound_at.isoformat()} diff={time_diff.total_seconds()//60:.0f}min window_open={window_open}")

        return {
            "success":         data.get("status") == "1",
            "messages":        msgs if isinstance(msgs, list) else [],
            "window_open":     window_open,
            "last_inbound_at": last_inbound_at.isoformat() if last_inbound_at else None,
            "window_source":   "wabis_messages" if msgs else ("local_subscriber" if local_last_seen else "none"),
        }
    except Exception as exc:
        return {"success": False, "messages": [], "error": str(exc), "window_open": False}


# ─────────────────────────────────────────────────────────────
# WA Media Send  — upload to Meta Media API, then send
# ─────────────────────────────────────────────────────────────

class MediaSendRequest(PydanticBaseModel):
    phone_number:  str
    media_url:     Optional[str] = None   # URL of file to download then upload
    media_type:    str = "document"       # document | image | video | audio
    filename:      Optional[str] = None
    caption:       Optional[str] = None


@router.post("/send-media")
async def send_media(
    body: MediaSendRequest,
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    """
    Upload a file to Meta Media API then send it as a WA message.

    Steps:
      1. Download file from media_url (authenticated via CRM)
      2. Upload to Meta Graph: POST /{phone_number_id}/media
      3. Use returned media_id to send: POST /{phone_number_id}/messages
    """
    settings = service.get_or_create_settings(db, current_user.tenant_id)
    if not settings.meta_phone_number_id or not settings.meta_access_token:
        raise HTTPException(status_code=422, detail="Meta Cloud API not configured (phone_number_id / access_token)")

    phone_id     = settings.meta_phone_number_id
    access_token = settings.meta_access_token
    phone        = "".join(c for c in body.phone_number if c.isdigit())

    if not body.media_url:
        raise HTTPException(status_code=400, detail="media_url is required")

    import httpx, mimetypes

    async with httpx.AsyncClient(timeout=60.0) as client:
        # ── Step 1: Download the file ────────────────────────
        try:
            dl = await client.get(body.media_url, follow_redirects=True)
            if dl.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Could not download media: HTTP {dl.status_code}")
        except httpx.HTTPError as e:
            raise HTTPException(status_code=400, detail=f"Download error: {e}")

        file_bytes   = dl.content
        content_type = dl.headers.get("content-type", "application/octet-stream").split(";")[0].strip()
        filename     = body.filename or body.media_url.split("/")[-1].split("?")[0] or "file"

        # ── Step 2: Upload to Meta Media API ─────────────────
        try:
            upload_resp = await client.post(
                f"https://graph.facebook.com/v20.0/{phone_id}/media",
                headers={"Authorization": f"Bearer {access_token}"},
                files={
                    "file":              (filename, file_bytes, content_type),
                    "type":              (None, content_type),
                    "messaging_product": (None, "whatsapp"),
                },
            )
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Meta upload error: {e}")

        upload_data = upload_resp.json()
        media_id    = upload_data.get("id")
        if not media_id:
            raise HTTPException(status_code=502, detail=f"Meta upload failed: {upload_data}")

        # ── Step 3: Send the media message ───────────────────
        media_block: dict = {"id": media_id}
        if body.caption and body.media_type in ("image", "document", "video"):
            media_block["caption"] = body.caption
        if body.filename and body.media_type == "document":
            media_block["filename"] = body.filename or filename

        message_payload = {
            "messaging_product": "whatsapp",
            "to":                phone,
            "type":              body.media_type,
            body.media_type:     media_block,
        }

        try:
            send_resp = await client.post(
                f"https://graph.facebook.com/v20.0/{phone_id}/messages",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type":  "application/json",
                },
                json=message_payload,
            )
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Meta send error: {e}")

        send_data    = send_resp.json()
        wa_msg_id    = (send_data.get("messages") or [{}])[0].get("id")
        success      = bool(wa_msg_id)
        return {
            "success":       success,
            "media_id":      media_id,
            "wa_message_id": wa_msg_id,
            "message":       "Media sent ✓" if success else "Send failed",
            "raw":           send_data,
        }


# ─────────────────────────────────────────────────────────────
# SMS fallback  — try WA, fall back to SMS if 24h window closed
# ─────────────────────────────────────────────────────────────

class SmsFallbackRequest(PydanticBaseModel):
    phone_number: str
    message_text: str
    sms_text: Optional[str] = None    # override SMS text (shorter version)
    force_sms:   bool = False         # skip WA entirely and send SMS


@router.post("/send-with-sms-fallback")
async def send_with_sms_fallback(
    body: SmsFallbackRequest,
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    """
    Attempts to send a WhatsApp message.
    If the 24-hour window is closed, automatically falls back to SMS.
    Requires SMS provider env vars (TWILIO_*, MSG91_*, or TEXTLOCAL_*).
    """
    from app.core.sms_fallback import SmsFallbackService

    settings = service.get_or_create_settings(db, current_user.tenant_id)
    phone    = "".join(c for c in body.phone_number if c.isdigit())
    svc      = SmsFallbackService(tenant_id=str(current_user.tenant_id))

    if body.force_sms:
        result = await svc.send(phone, body.sms_text or body.message_text)
        return {**result, "channel": "sms", "fallback_used": True}

    # Build WA send function
    async def _wa_send():
        try:
            async with __import__("httpx").AsyncClient(timeout=15) as client:
                resp = await client.post(
                    "https://bot.wabis.in/api/v1/whatsapp/send",
                    data={
                        "apiToken":        settings.wabis_api_token or "",
                        "phone_number_id": settings.wabis_phone_number_id or "",
                        "message":         body.message_text,
                        "phone_number":    phone,
                    },
                )
                data = resp.json()
            ok = data.get("status") == "1"
            # Map WABIS error to Meta-style error_code for window detection
            err_msg = data.get("message", "")
            meta_error = {}
            if not ok and ("window" in err_msg.lower() or "24" in err_msg):
                meta_error = {"code": 131047}   # treat as window-closed
            return {"success": ok, "error": err_msg if not ok else None, "meta_error": meta_error}
        except Exception as e:
            return {"success": False, "error": str(e)}

    result = await svc.send_wa_with_sms_fallback(
        phone=phone,
        message=body.message_text,
        wa_send_fn=_wa_send,
        sms_message=body.sms_text,
    )
    return result


# ─────────────────────────────────────────────────────────────
# Public inbound webhook  (no JWT auth — uses shared secret)
# ─────────────────────────────────────────────────────────────

@router.get("/inbound/{tenant_id}", include_in_schema=False)
def meta_hub_challenge(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    hub_mode:          Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token:  Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge:     Optional[str] = Query(None, alias="hub.challenge"),
):
    """Meta webhook hub.challenge verification."""
    row = db.query(WaSettings).filter(WaSettings.tenant_id == tenant_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Tenant WA settings not found")

    verify_token = row.meta_webhook_verify_token or ""
    challenge = MetaProvider.verify_challenge(
        hub_mode, hub_verify_token, hub_challenge, verify_token
    )
    if challenge is None:
        raise HTTPException(status_code=403, detail="Invalid verify token")
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(challenge)


@router.post("/inbound/{tenant_id}", include_in_schema=False)
async def inbound_webhook(
    tenant_id:  uuid.UUID,
    request:    Request,
    db: Session = Depends(get_db),
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret"),
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
):
    """
    Unified inbound webhook.
    WABIS fires this with X-Webhook-Secret header.
    Meta fires this with X-Hub-Signature-256 header.
    Always return 200 so the provider doesn't keep retrying.
    """
    body_bytes = await request.body()

    row = db.query(WaSettings).filter(WaSettings.tenant_id == tenant_id).first()

    if row is None:
        log.warning("Inbound webhook: unknown tenant_id=%s", tenant_id)
        return {"status": "ignored"}

    try:
        raw: Dict[str, Any] = json.loads(body_bytes)
    except Exception:
        log.warning("Inbound webhook: non-JSON body from tenant %s", tenant_id)
        return {"status": "ignored"}

    # ── Meta message-status callbacks (delivered/read/failed) ──────────────
    # These arrive in Meta's native webhook shape regardless of wa_settings.provider,
    # since template sends always go directly through Meta's Graph API (see
    # message_automation/service.py _send_meta_template). A payload never mixes
    # messages[] and statuses[], so handling this first and returning is safe.
    # Prefer Meta HMAC verification. For WABIS-managed apps whose App Secret
    # is not shared with Miguel, accept only callbacks that match an exact
    # stored outbound message, sender phone ID, tenant, and recipient.
    status_entries = MetaProvider.parse_statuses(raw)
    if status_entries:
        verified_entries: List[Dict[str, Any]] = []
        verification_mode = ""
        if (
            row.meta_app_secret
            and MetaProvider.verify_signature(
                body_bytes,
                x_hub_signature_256,
                row.meta_app_secret,
            )
        ):
            verified_entries = status_entries
            verification_mode = "hmac"
        else:
            verified_entries = _restricted_meta_status_entries(
                db,
                tenant_id,
                row,
                raw,
                status_entries,
            )
            if verified_entries:
                verification_mode = "stored-message-match"

        if not verified_entries:
            reason = (
                "no meta_app_secret is configured"
                if not row.meta_app_secret
                else "the Meta signature is invalid"
            )
            log.warning(
                "Inbound webhook: Meta status callback for tenant %s skipped because %s "
                "and it did not match a stored outbound message. "
                "Unverified diagnostics=%s",
                tenant_id,
                reason,
                _safe_meta_status_diagnostics(status_entries),
            )
        else:
            try:
                updated = service.apply_meta_status_update(
                    db,
                    tenant_id,
                    verified_entries,
                )
                db.commit()
                log.info(
                    "Inbound webhook: applied %d Meta status update(s) for tenant %s "
                    "using %s verification",
                    updated,
                    tenant_id,
                    verification_mode,
                )
            except Exception:
                log.exception("Error applying Meta status updates for tenant %s", tenant_id)
                db.rollback()
        return {"status": "ok"}

    if row.inbound_secret and x_webhook_secret:
        if x_webhook_secret != row.inbound_secret:
            log.warning("Inbound webhook: bad secret for tenant %s", tenant_id)
            return {"status": "ignored"}

    inbound = None
    if row.provider.value == "meta":
        inbound = MetaProvider.parse_inbound(raw)
    else:
        inbound = WabisProvider.parse_inbound(raw)

    if inbound is None:
        log.debug("Inbound webhook: no actionable event in payload")
        return {"status": "ok"}

    try:
        log.info(f"[WABIS INBOUND] Processing for tenant {tenant_id}: phone={inbound.phone_number}, name={inbound.subscriber_name}, labels={inbound.labels}")
        await service.process_inbound(db, tenant_id, inbound)
        db.commit()
        log.info(f"[WABIS INBOUND] ✓ Processed successfully")
    except Exception as exc:
        log.exception("Inbound processing error for tenant %s: %s", tenant_id, exc)
        db.rollback()

    return {"status": "ok"}


# ─────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────

def _build_base_url(request: Optional[Request]) -> str:
    """
    Build the base URL for webhook endpoints.
    Handles X-Forwarded-Proto header from reverse proxy (nginx).
    If behind HTTPS proxy, FastAPI sees HTTP but we need HTTPS in the URL.
    """
    if not request:
        return ""
    
    # Check for X-Forwarded-Proto header (set by nginx reverse proxy)
    forwarded_proto = request.headers.get("x-forwarded-proto", "").lower()
    if forwarded_proto in ("https", "http"):
        proto = forwarded_proto
    else:
        proto = request.url.scheme
    
    # Build URL with correct protocol
    host = request.headers.get("host") or request.url.netloc
    return f"{proto}://{host}".rstrip("/")


def _build_settings_response(
    row: WaSettings,
    request: Optional[Request],
) -> schemas.WaSettingsResponse:
    base = _build_base_url(request)
    resp = schemas.WaSettingsResponse.model_validate(row)
    resp.wabis_token_set      = bool(row.wabis_access_token)
    resp.wabis_api_token_set  = bool(row.wabis_api_token)
    resp.meta_token_set       = bool(row.meta_access_token)
    resp.meta_app_secret_set  = bool(row.meta_app_secret)
    resp.inbound_webhook_url  = f"{base}/api/wa/inbound/{row.tenant_id}"
    if row.meta_phone_number_id:
        pid = row.meta_phone_number_id
        resp.meta_phone_number_id_masked = f"...{pid[-4:]}" if len(pid) > 4 else pid
    return resp


# ─────────────────────────────────────────────────────────────
# Outbound Webhooks  —  /api/wa/outbound-webhooks
# ─────────────────────────────────────────────────────────────

@router.get("/outbound-webhooks")
def list_outbound_webhooks(
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    """List all outbound webhooks for this tenant."""
    rows = (
        db.query(WaOutboundWebhook)
        .filter(WaOutboundWebhook.tenant_id == current_user.tenant_id)
        .order_by(WaOutboundWebhook.created_at.asc())
        .all()
    )
    return [_webhook_to_dict(r) for r in rows]


@router.post("/outbound-webhooks", status_code=201)
def create_outbound_webhook(
    body: Dict[str, Any],
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    """Create a new outbound webhook."""
    name = (body.get("name") or "").strip()
    url  = (body.get("url")  or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="name is required")
    if not url or not url.startswith("http"):
        raise HTTPException(status_code=422, detail="A valid URL is required")

    row = WaOutboundWebhook(
        tenant_id      = current_user.tenant_id,
        name           = name,
        url            = url,
        is_active      = body.get("is_active", True),
        trigger_events = body.get("trigger_events", ["new_message", "postback"]),
        data_fields    = body.get("data_fields", [
            "subscriber_id", "name", "phone", "wabis_status", "labels", "postback_id"
        ]),
        postback_filter = body.get("postback_filter") or None,
        secret         = body.get("secret") or str(uuid.uuid4()).replace("-", "")[:32],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _webhook_to_dict(row)


@router.put("/outbound-webhooks/{webhook_id}")
def update_outbound_webhook(
    webhook_id: str,
    body: Dict[str, Any],
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    """Update an outbound webhook."""
    row = (
        db.query(WaOutboundWebhook)
        .filter(
            WaOutboundWebhook.id == webhook_id,
            WaOutboundWebhook.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Webhook not found")

    if "name"            in body: row.name            = (body["name"] or "").strip()
    if "url"             in body: row.url             = (body["url"]  or "").strip()
    if "is_active"       in body: row.is_active       = bool(body["is_active"])
    if "trigger_events"  in body: row.trigger_events  = body["trigger_events"]
    if "data_fields"     in body: row.data_fields     = body["data_fields"]
    if "postback_filter" in body: row.postback_filter = body["postback_filter"] or None
    if "secret"          in body: row.secret          = body["secret"]

    db.commit()
    db.refresh(row)
    return _webhook_to_dict(row)


@router.delete("/outbound-webhooks/{webhook_id}", status_code=204)
def delete_outbound_webhook(
    webhook_id: str,
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    """Delete an outbound webhook."""
    row = (
        db.query(WaOutboundWebhook)
        .filter(
            WaOutboundWebhook.id == webhook_id,
            WaOutboundWebhook.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Webhook not found")
    db.delete(row)
    db.commit()
    return None


@router.post("/outbound-webhooks/{webhook_id}/test")
async def test_outbound_webhook(
    webhook_id: str,
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    """Fire a test payload to the configured URL and return the HTTP status."""
    import httpx, datetime

    row = (
        db.query(WaOutboundWebhook)
        .filter(
            WaOutboundWebhook.id == webhook_id,
            WaOutboundWebhook.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Webhook not found")

    test_payload = {
        "event":         "test",
        "source":        "miguel",
        "tenant_id":     str(current_user.tenant_id),
        "webhook_name":  row.name,
        "timestamp":     datetime.datetime.utcnow().isoformat() + "Z",
        "subscriber": {
            "subscriber_id": "TEST-12345",
            "name":          "Test Subscriber",
            "phone":         "+919876543210",
            "email":         "test@example.com",
            "wabis_status":  "new_message",
            "labels":        ["test-label"],
            "postback_id":   "test_postback",
            "postback_title": "Test Postback",
            "date_of_birth": None,
            "location":      None,
            "wa_status_code": "new_message",
        },
    }
    headers = {"Content-Type": "application/json", "X-Miguel-Secret": row.secret or ""}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(row.url, json=test_payload, headers=headers)
        status_code = resp.status_code
        ok = 200 <= status_code < 300
    except Exception as exc:
        return {"ok": False, "status_code": None, "error": str(exc)}

    # Update stats
    row.last_fired_at    = datetime.datetime.utcnow()
    row.last_status_code = status_code
    row.total_fired      = (row.total_fired or 0) + 1
    if not ok:
        row.total_failed = (row.total_failed or 0) + 1
    db.commit()

    return {"ok": ok, "status_code": status_code}


def _webhook_to_dict(row: WaOutboundWebhook) -> dict:
    return {
        "id":             str(row.id),
        "name":           row.name,
        "url":            row.url,
        "is_active":      row.is_active,
        "trigger_events": row.trigger_events or [],
        "data_fields":    row.data_fields    or [],
        "postback_filter":row.postback_filter or [],
        "secret":         row.secret or "",
        "last_fired_at":  row.last_fired_at.isoformat()  if row.last_fired_at  else None,
        "last_status_code": row.last_status_code,
        "total_fired":    row.total_fired   or 0,
        "total_failed":   row.total_failed  or 0,
        "created_at":     row.created_at.isoformat()     if row.created_at     else None,
    }
