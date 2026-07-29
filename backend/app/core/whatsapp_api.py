"""
Meta Business WhatsApp API — Core Client
-----------------------------------------
Sends messages via the Meta Cloud API (v19.0).
Used by:
  - Outbound message sending (text, template)
  - Auto-reply to inbound messages

Environment variables expected:
  WHATSAPP_PHONE_NUMBER_ID   — Your WhatsApp Business phone number ID
  WHATSAPP_ACCESS_TOKEN      — Permanent system-user token
  WHATSAPP_AUTO_REPLY_MSG    — Auto-reply text (optional, falls back to default)
  META_WEBHOOK_VERIFY_TOKEN  — Shared secret for webhook verification
  WHATSAPP_API_VERSION       — API version (default: v19.0)

All functions are synchronous (use httpx blocking client) since FastAPI
endpoints calling them already run inside a thread-pool for sync routes.
"""

from __future__ import annotations

import os
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Config (from env)
# ─────────────────────────────────────────────────────────────

WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_ACCESS_TOKEN    = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_API_VERSION     = os.getenv("WHATSAPP_API_VERSION", "v19.0")
WHATSAPP_AUTO_REPLY_MSG  = os.getenv(
    "WHATSAPP_AUTO_REPLY_MSG",
    "Hi! Thank you for reaching out. Our team will get back to you shortly. 😊"
)
META_WEBHOOK_VERIFY_TOKEN = os.getenv("META_WEBHOOK_VERIFY_TOKEN", "miguel_crm_wa_verify_2026")

GRAPH_API_BASE = "https://graph.facebook.com"


def _graph_url(path: str) -> str:
    return f"{GRAPH_API_BASE}/{WHATSAPP_API_VERSION}/{path}"


def _auth_headers() -> dict:
    return {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }


def is_configured() -> bool:
    """Returns True if WhatsApp API credentials are set."""
    return bool(WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_ACCESS_TOKEN)


# ─────────────────────────────────────────────────────────────
# Send text message
# ─────────────────────────────────────────────────────────────

def send_text_message(to_phone: str, message: str) -> dict:
    """
    Send a plain text WhatsApp message via Cloud API.

    Args:
        to_phone: Recipient phone number in E.164 format (e.g. "919876543210")
        message:  Text body (max 4096 chars)

    Returns:
        Meta API response dict on success.

    Raises:
        RuntimeError if not configured or API call fails.
    """
    if not is_configured():
        raise RuntimeError(
            "WhatsApp API not configured. "
            "Set WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_ACCESS_TOKEN env vars."
        )

    # Ensure no + prefix — Meta expects numeric E.164 without leading +
    phone = to_phone.lstrip("+")

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": message[:4096],
        },
    }

    url = _graph_url(f"{WHATSAPP_PHONE_NUMBER_ID}/messages")

    try:
        resp = httpx.post(url, json=payload, headers=_auth_headers(), timeout=15)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as exc:
        body = exc.response.text
        logger.error("WhatsApp send failed: %s — %s", exc.response.status_code, body)
        raise RuntimeError(f"WhatsApp API error {exc.response.status_code}: {body}") from exc
    except httpx.RequestError as exc:
        logger.error("WhatsApp network error: %s", exc)
        raise RuntimeError(f"WhatsApp network error: {exc}") from exc


# ─────────────────────────────────────────────────────────────
# Mark message as read
# ─────────────────────────────────────────────────────────────

def mark_message_read(whatsapp_message_id: str) -> bool:
    """
    Mark an incoming message as read (sends read receipt).
    Best-effort — failure is logged but not raised.
    """
    if not is_configured():
        return False

    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": whatsapp_message_id,
    }
    url = _graph_url(f"{WHATSAPP_PHONE_NUMBER_ID}/messages")

    try:
        resp = httpx.post(url, json=payload, headers=_auth_headers(), timeout=10)
        return resp.status_code == 200
    except Exception as exc:
        logger.warning("Failed to mark message read: %s", exc)
        return False


# ─────────────────────────────────────────────────────────────
# Auto-reply
# ─────────────────────────────────────────────────────────────

def send_auto_reply(to_phone: str, custom_message: Optional[str] = None) -> dict | None:
    """
    Send the configured auto-reply message to a phone number.
    Returns API response or None if not configured / on error.
    """
    if not is_configured():
        logger.info("WhatsApp not configured — auto-reply skipped for %s", to_phone)
        return None

    msg = custom_message or WHATSAPP_AUTO_REPLY_MSG
    try:
        return send_text_message(to_phone, msg)
    except Exception as exc:
        logger.error("Auto-reply failed for %s: %s", to_phone, exc)
        return None


# ─────────────────────────────────────────────────────────────
# Webhook signature verification
# ─────────────────────────────────────────────────────────────

def verify_webhook_token(
    hub_mode: str,
    hub_verify_token: str,
    hub_challenge: str,
) -> str | None:
    """
    Verify Meta webhook hub challenge.
    Returns the challenge string if valid, None otherwise.
    """
    if hub_mode == "subscribe" and hub_verify_token == META_WEBHOOK_VERIFY_TOKEN:
        return hub_challenge
    return None


# ─────────────────────────────────────────────────────────────
# Parse inbound webhook payload
# ─────────────────────────────────────────────────────────────

def parse_inbound_messages(payload: dict) -> list[dict]:
    """
    Parse Meta WhatsApp Business webhook payload and extract inbound messages.

    Returns a list of dicts with:
      - from_phone:   str  (E.164 without +)
      - wa_message_id: str (Meta message ID, for dedup)
      - message_body: str  (text content)
      - timestamp:    str  (unix timestamp string)
      - display_phone_number: str (the receiving WA Business number)
      - profile_name: str  (sender's display name if available)

    Only "text" type messages are returned (voice, image etc. are skipped).
    """
    results = []

    entries = payload.get("entry", [])
    for entry in entries:
        for change in entry.get("changes", []):
            value = change.get("value", {})
            if change.get("field") != "messages":
                continue

            messages = value.get("messages", [])
            contacts = {c["wa_id"]: c.get("profile", {}).get("name", "") for c in value.get("contacts", [])}
            meta_data = value.get("metadata", {})

            for msg in messages:
                if msg.get("type") != "text":
                    # Skip non-text messages (images, audio, etc.)
                    continue

                from_phone = msg.get("from", "")
                wa_id = msg.get("id", "")
                text_body = msg.get("text", {}).get("body", "")
                ts = msg.get("timestamp", "")

                results.append({
                    "from_phone":            from_phone,
                    "wa_message_id":         wa_id,
                    "message_body":          text_body,
                    "timestamp":             ts,
                    "display_phone_number":  meta_data.get("display_phone_number", ""),
                    "phone_number_id":       meta_data.get("phone_number_id", ""),
                    "profile_name":          contacts.get(from_phone, ""),
                })

    return results
