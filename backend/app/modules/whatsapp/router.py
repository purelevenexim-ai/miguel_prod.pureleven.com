"""
WhatsApp Business Webhook — Router
------------------------------------
GET  /api/whatsapp/webhook   — Meta hub.challenge verification (no auth)
POST /api/whatsapp/webhook   — Receive inbound WhatsApp messages (no auth, verified by token)
POST /api/whatsapp/send      — Send outbound WhatsApp message to a lead (auth required)
GET  /api/whatsapp/config    — Get WhatsApp integration status (admin only)
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.core.auth.tenant import get_current_tenant_user, require_roles
from app.models.employee import Employee, RoleEnum
from app.modules.whatsapp import service
from app.modules.whatsapp.schemas import (
    SendMessageRequest,
    SendMessageResponse,
    WhatsAppConfigResponse,
)

router = APIRouter(prefix="/api/whatsapp", tags=["WhatsApp Business"])


# ─────────────────────────────────────────────────────────────
# Webhook — Public (no auth)
# ─────────────────────────────────────────────────────────────

@router.get("/webhook", response_class=PlainTextResponse)
def webhook_verify(
    hub_mode:         str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge:    str = Query(..., alias="hub.challenge"),
):
    """
    Meta sends GET to verify the webhook endpoint.
    Returns hub.challenge if token matches.
    """
    from app.core.whatsapp_api import verify_webhook_token
    challenge = verify_webhook_token(hub_mode, hub_verify_token, hub_challenge)
    if challenge:
        return PlainTextResponse(challenge)
    return PlainTextResponse("Forbidden", status_code=403)


@router.post("/webhook", status_code=200)
async def webhook_receive(request: Request, db: Session = Depends(get_db)):
    """
    Receive inbound WhatsApp messages from Meta Business Platform.

    Flow for each inbound text message:
    1. Parse the payload to extract message(s)
    2. Find or auto-create a Lead by phone number (tenant-matched via phone_number_id)
    3. Store the message in lead_messages table
    4. Send auto-reply (configurable via WHATSAPP_AUTO_REPLY_MSG env var)
    5. Mark message as read
    6. Always return 200 (Meta will retry on non-200)
    """
    try:
        payload = await request.json()
    except Exception:
        return {"status": "ignored", "reason": "invalid JSON"}

    results = service.ingest_whatsapp_webhook(db, payload)
    return {"status": "ok", **results}


# ─────────────────────────────────────────────────────────────
# Send message (auth required)
# ─────────────────────────────────────────────────────────────

@router.post("/send", response_model=SendMessageResponse, status_code=201)
def send_message(
    data: SendMessageRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(
        require_roles(RoleEnum.admin, RoleEnum.sales, RoleEnum.support)
    ),
):
    """
    Send a WhatsApp text message to a lead.
    Stores it in lead_messages as 'outbound'.
    Admin, Sales, Support only.
    """
    return service.send_message_to_lead(db, data, current_user)


# ─────────────────────────────────────────────────────────────
# Config / Status
# ─────────────────────────────────────────────────────────────

@router.get("/config", response_model=WhatsAppConfigResponse)
def get_config(
    current_user: Employee = Depends(require_roles(RoleEnum.admin)),
):
    """
    Get current WhatsApp API configuration status.
    Shows whether credentials are set, phone number ID, auto-reply text.
    Admin only.
    """
    return service.get_whatsapp_config()
