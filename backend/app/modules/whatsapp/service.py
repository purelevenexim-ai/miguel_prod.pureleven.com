"""
WhatsApp Business — Service
-----------------------------
Business logic for:
  1. Inbound webhook ingestion (parse → match lead → store → auto-reply)
  2. Outbound message sending (staff → lead)
  3. Config/status reporting
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core import whatsapp_api
from app.core.whatsapp_api import (
    parse_inbound_messages,
    send_text_message,
    send_auto_reply,
    mark_message_read,
    WHATSAPP_AUTO_REPLY_MSG,
    WHATSAPP_PHONE_NUMBER_ID,
    WHATSAPP_API_VERSION,
    META_WEBHOOK_VERIFY_TOKEN,
)
from app.models.lead import (
    Lead,
    LeadMessage,
    LeadActivity,
    LeadPipelineStatus,
    LeadSource,
    LeadPriority,
    LeadActivityType,
)
from app.models.employee import Employee
from app.modules.whatsapp.schemas import (
    SendMessageRequest,
    SendMessageResponse,
    WhatsAppConfigResponse,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _normalize_phone(phone: str) -> str:
    """Strip non-digits, ensure 10-digit Indian number for DB match."""
    import re
    digits = re.sub(r"\D", "", phone)
    # Strip country code prefix
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return digits  # 10 digits


def _find_lead_by_phone(db: Session, phone_digits: str) -> Optional[Lead]:
    """Find an active lead by last-10-digits phone match across all tenants."""
    return (
        db.query(Lead)
        .filter(
            Lead.is_active == True,
            Lead.phone.like(f"%{phone_digits}"),
        )
        .order_by(Lead.created_at.desc())
        .first()
    )


def _next_lead_number(db: Session, tenant_id) -> str:
    count = (
        db.query(func.count(Lead.id)).filter(Lead.tenant_id == tenant_id).scalar()
    ) or 0
    return f"LEAD-{str(count + 1).zfill(5)}"


def _get_system_employee(db: Session, tenant_id) -> Optional[Employee]:
    """Get any admin employee for the tenant to use as system actor."""
    from app.models.employee import RoleEnum
    return (
        db.query(Employee)
        .filter(
            Employee.tenant_id == tenant_id,
            Employee.role == RoleEnum.admin,
            Employee.is_active == True,
        )
        .first()
    )


# ─────────────────────────────────────────────────────────────
# Inbound Webhook Ingestion
# ─────────────────────────────────────────────────────────────

def ingest_whatsapp_webhook(db: Session, payload: dict) -> dict:
    """
    Process an inbound WhatsApp Business webhook payload.

    For each inbound text message:
    1. Parse phone number
    2. Find matching Lead (by phone, across all tenants)
    3. If no lead found → create a new Lead (source=whatsapp, status=new_lead)
    4. Store message in lead_messages (direction=inbound)
    5. Send auto-reply via WhatsApp API
    6. Mark message as read
    """
    messages_processed = 0
    leads_matched      = 0
    leads_created      = 0
    auto_replies_sent  = 0
    errors             = []

    try:
        inbound = parse_inbound_messages(payload)
    except Exception as exc:
        logger.error("Failed to parse WhatsApp webhook: %s", exc)
        return {"messages_processed": 0, "error": str(exc)}

    for msg in inbound:
        from_phone   = msg["from_phone"]
        wa_msg_id    = msg["wa_message_id"]
        message_body = msg["message_body"]
        profile_name = msg.get("profile_name", "")

        # ── Dedup: skip if already stored ─────────────────────
        existing = (
            db.query(LeadMessage)
            .filter(LeadMessage.whatsapp_message_id == wa_msg_id)
            .first()
        )
        if existing:
            logger.info("Duplicate WA message %s — skipped", wa_msg_id)
            continue

        try:
            phone_digits = _normalize_phone(from_phone)

            # ── Match or create lead ───────────────────────────
            lead = _find_lead_by_phone(db, phone_digits)
            if lead:
                leads_matched += 1
            else:
                # Auto-create lead from WhatsApp message
                lead = _auto_create_lead(
                    db=db,
                    phone=from_phone,
                    name=profile_name or f"WhatsApp {phone_digits[-4:]}",
                )
                leads_created += 1

            # ── Store message ──────────────────────────────────
            lm = LeadMessage(
                tenant_id           = lead.tenant_id,
                lead_id             = lead.id,
                direction           = "inbound",
                message_body        = message_body,
                whatsapp_message_id = wa_msg_id,
            )
            db.add(lm)

            # ── Log activity ───────────────────────────────────
            system_employee = _get_system_employee(db, lead.tenant_id)
            if system_employee:
                activity = LeadActivity(
                    tenant_id     = lead.tenant_id,
                    lead_id       = lead.id,
                    employee_id   = system_employee.id,
                    activity_type = LeadActivityType.message_received,
                    note          = f"WhatsApp inbound: {message_body[:200]}",
                )
                db.add(activity)

            # ── Update last_contacted_at ───────────────────────
            lead.last_contacted_at = datetime.now(timezone.utc)

            db.commit()
            messages_processed += 1

            # ── Auto-reply ─────────────────────────────────────
            reply_result = send_auto_reply(from_phone)
            if reply_result:
                auto_replies_sent += 1

                # Store auto-reply as outbound message
                wa_reply_id = None
                try:
                    msgs = reply_result.get("messages", [])
                    if msgs:
                        wa_reply_id = msgs[0].get("id")
                except Exception:
                    pass

                outbound = LeadMessage(
                    tenant_id           = lead.tenant_id,
                    lead_id             = lead.id,
                    direction           = "outbound",
                    message_body        = WHATSAPP_AUTO_REPLY_MSG,
                    whatsapp_message_id = wa_reply_id,
                )
                db.add(outbound)
                db.commit()

            # ── Mark read ──────────────────────────────────────
            if wa_msg_id:
                mark_message_read(wa_msg_id)

        except Exception as exc:
            db.rollback()
            logger.error("Error processing WA message from %s: %s", from_phone, exc)
            errors.append(f"{from_phone}: {str(exc)}")

    return {
        "messages_processed": messages_processed,
        "leads_matched":      leads_matched,
        "leads_created":      leads_created,
        "auto_replies_sent":  auto_replies_sent,
        "errors":             errors,
    }


def _auto_create_lead(db: Session, phone: str, name: str) -> Lead:
    """
    Create a Lead record from an inbound WhatsApp message.
    Attaches to the first active tenant (single-tenant mode).
    For multi-tenant, you'd match by WhatsApp phone_number_id to a Meta integration.
    """
    from app.models.tenant import Tenant

    # Find the first active tenant
    tenant = db.query(Tenant).filter(Tenant.is_active == True).first()
    if not tenant:
        raise RuntimeError("No active tenant found to assign inbound WhatsApp lead")

    lead_number = _next_lead_number(db, tenant.id)

    # Get any admin employee to use as created_by
    admin = _get_system_employee(db, tenant.id)
    if not admin:
        raise RuntimeError(f"No admin employee found for tenant {tenant.id}")

    lead = Lead(
        tenant_id    = tenant.id,
        lead_number  = lead_number,
        name         = name,
        phone        = phone,
        source       = LeadSource.whatsapp,
        status       = LeadPipelineStatus.new_lead,
        priority     = LeadPriority.medium,
        created_by_id = admin.id,
        assigned_to_id = admin.id,
    )
    db.add(lead)
    db.flush()

    # Log creation
    activity = LeadActivity(
        tenant_id     = tenant.id,
        lead_id       = lead.id,
        employee_id   = admin.id,
        activity_type = LeadActivityType.note,
        note          = f"Lead auto-created from inbound WhatsApp message.",
        new_status    = LeadPipelineStatus.new_lead,
    )
    db.add(activity)
    db.commit()
    db.refresh(lead)

    logger.info("Auto-created lead %s for WhatsApp %s", lead.lead_number, phone)
    return lead


# ─────────────────────────────────────────────────────────────
# Send Outbound Message (staff → lead)
# ─────────────────────────────────────────────────────────────

def send_message_to_lead(
    db: Session,
    data: SendMessageRequest,
    current_user: Employee,
) -> SendMessageResponse:
    """
    Send a WhatsApp message from staff to a lead.
    Stores in lead_messages as outbound.
    """
    from app.core.tenant_utils import assert_tenant_ownership

    # Get and validate lead
    lead = db.query(Lead).filter(Lead.id == data.lead_id).first()
    if not lead or not lead.is_active:
        raise HTTPException(status_code=404, detail="Lead not found")
    assert_tenant_ownership(lead, current_user)

    if not lead.phone:
        raise HTTPException(status_code=422, detail="Lead has no phone number")

    wa_message_id = None
    error_msg = None

    # Send via API
    try:
        result = send_text_message(lead.phone, data.message)
        # Extract Meta's message ID
        msgs = result.get("messages", [])
        if msgs:
            wa_message_id = msgs[0].get("id")
    except Exception as exc:
        error_msg = str(exc)
        logger.error("Failed to send WA message to lead %s: %s", lead.id, exc)
        raise HTTPException(
            status_code=502,
            detail=f"Failed to send WhatsApp message: {error_msg}",
        )

    # Store as outbound
    lm = LeadMessage(
        tenant_id           = current_user.tenant_id,
        lead_id             = lead.id,
        direction           = "outbound",
        message_body        = data.message,
        whatsapp_message_id = wa_message_id,
    )
    db.add(lm)

    # Log activity
    activity = LeadActivity(
        tenant_id     = current_user.tenant_id,
        lead_id       = lead.id,
        employee_id   = current_user.id,
        activity_type = LeadActivityType.whatsapp,
        note          = f"WhatsApp sent: {data.message[:200]}",
    )
    db.add(activity)

    # Update last_contacted_at
    lead.last_contacted_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(lm)

    return SendMessageResponse(
        success       = True,
        message_id    = str(lm.id),
        wa_message_id = wa_message_id,
    )


# ─────────────────────────────────────────────────────────────
# Config / Status
# ─────────────────────────────────────────────────────────────

def get_whatsapp_config() -> WhatsAppConfigResponse:
    """Return current WhatsApp API config status (no secrets exposed)."""
    configured = whatsapp_api.is_configured()

    # Mask phone_number_id — show last 4 digits only
    masked_pid = None
    if WHATSAPP_PHONE_NUMBER_ID:
        pid = WHATSAPP_PHONE_NUMBER_ID
        masked_pid = ("*" * (len(pid) - 4) + pid[-4:]) if len(pid) > 4 else "****"

    return WhatsAppConfigResponse(
        is_configured            = configured,
        phone_number_id          = masked_pid,
        auto_reply_enabled       = configured,
        auto_reply_message       = WHATSAPP_AUTO_REPLY_MSG,
        api_version              = WHATSAPP_API_VERSION,
        webhook_verify_token_set = bool(META_WEBHOOK_VERIFY_TOKEN),
    )
