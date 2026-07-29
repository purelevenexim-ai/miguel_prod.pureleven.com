"""
SMS Fallback Service
--------------------
Sends SMS when WhatsApp message delivery fails (24h window closed or
Meta API returns a non-session-window error code).

Supported providers (configured per tenant via wa_settings or env vars):
  - twilio      : International, best deliverability
  - msg91       : India-specific, low cost
  - textlocal   : India bulk SMS

Priority order:
  1. Try WA send
  2. On failure with error_code in WINDOW_CLOSED_CODES → SMS fallback
  3. Log both attempts to wa_messages / activity_log
"""
import logging
import os
from typing import Optional, Dict, Any

import httpx

logger = logging.getLogger(__name__)

# Meta API error codes that mean the 24-hour window is closed
WINDOW_CLOSED_CODES = {
    131047,  # Re-engagement message — not allowed outside window
    131026,  # Message undeliverable — contact has not messaged in 24h
    131049,  # Message failed to send — WhatsApp Pay policy issue (rare, treat as closed)
    131021,  # Recipient phone number not in allowed list (test numbers)
}

# Numeric string versions
WINDOW_CLOSED_CODE_STRS = {str(c) for c in WINDOW_CLOSED_CODES}


def is_window_closed_error(meta_error: Dict) -> bool:
    """Return True if the Meta API error indicates the 24-hour window is closed."""
    code = meta_error.get("code") or meta_error.get("error_code") or ""
    sub  = meta_error.get("error_subcode") or meta_error.get("error_data", {}).get("details", "")
    return str(code) in WINDOW_CLOSED_CODE_STRS or code in WINDOW_CLOSED_CODES


# ══════════════════════════════════════════════════════════════
# Provider clients
# ══════════════════════════════════════════════════════════════

class TwilioSMSClient:
    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self.account_sid = account_sid
        self.auth_token  = auth_token
        self.from_number = from_number

    async def send(self, to: str, body: str) -> Dict[str, Any]:
        """Send SMS via Twilio REST API."""
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.post(
                    url,
                    auth=(self.account_sid, self.auth_token),
                    data={"To": f"+{to.lstrip('+')}", "From": self.from_number, "Body": body},
                )
                data = resp.json()
                if resp.status_code in (200, 201):
                    return {"success": True, "sid": data.get("sid"), "provider": "twilio"}
                return {"success": False, "provider": "twilio", "error": data.get("message", str(resp.text[:200]))}
            except Exception as e:
                return {"success": False, "provider": "twilio", "error": str(e)}


class MSG91SMSClient:
    def __init__(self, api_key: str, sender_id: str, route: str = "4"):
        self.api_key   = api_key
        self.sender_id = sender_id
        self.route     = route  # 4 = transactional

    async def send(self, to: str, body: str) -> Dict[str, Any]:
        """Send SMS via MSG91 API."""
        phone = to.lstrip("+").lstrip("91")  # strip country code for MSG91
        url   = "https://api.msg91.com/api/v5/flow/"
        # Use legacy single SMS API for simplicity
        sms_url = "https://api.msg91.com/api/sendhttp.php"
        params = {
            "authkey": self.api_key,
            "mobiles": to.lstrip("+"),
            "message": body,
            "sender":  self.sender_id,
            "route":   self.route,
            "country": "0",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(sms_url, params=params)
                text = resp.text.strip()
                success = resp.status_code == 200 and not text.startswith("ERROR")
                return {"success": success, "provider": "msg91",
                        "response": text, "error": None if success else text}
            except Exception as e:
                return {"success": False, "provider": "msg91", "error": str(e)}


class TextLocalSMSClient:
    def __init__(self, api_key: str, sender: str = "TXTLCL"):
        self.api_key = api_key
        self.sender  = sender

    async def send(self, to: str, body: str) -> Dict[str, Any]:
        """Send SMS via TextLocal API."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.post(
                    "https://api.textlocal.in/send/",
                    data={
                        "apikey": self.api_key,
                        "numbers": to.lstrip("+"),
                        "message": body,
                        "sender":  self.sender,
                    },
                )
                data = resp.json()
                success = data.get("status") == "success"
                return {"success": success, "provider": "textlocal",
                        "response": data, "error": data.get("errors") if not success else None}
            except Exception as e:
                return {"success": False, "provider": "textlocal", "error": str(e)}


# ══════════════════════════════════════════════════════════════
# Main fallback service
# ══════════════════════════════════════════════════════════════

class SmsFallbackService:
    """
    Orchestrates SMS fallback for a tenant.

    Priority: env vars → wa_settings SMS fields (future).
    Tries providers in order until one succeeds.
    """

    def __init__(self, tenant_id=None):
        self.tenant_id = tenant_id
        self._clients = self._build_clients()

    def _build_clients(self):
        clients = []

        # Twilio
        twilio_sid    = os.environ.get("TWILIO_ACCOUNT_SID", "")
        twilio_token  = os.environ.get("TWILIO_AUTH_TOKEN", "")
        twilio_from   = os.environ.get("TWILIO_FROM_NUMBER", "")
        if twilio_sid and twilio_token and twilio_from:
            clients.append(TwilioSMSClient(twilio_sid, twilio_token, twilio_from))

        # MSG91
        msg91_key     = os.environ.get("MSG91_API_KEY", "")
        msg91_sender  = os.environ.get("MSG91_SENDER_ID", "MIGUEL")
        if msg91_key:
            clients.append(MSG91SMSClient(msg91_key, msg91_sender))

        # TextLocal
        tl_key        = os.environ.get("TEXTLOCAL_API_KEY", "")
        tl_sender     = os.environ.get("TEXTLOCAL_SENDER", "MIGUEL")
        if tl_key:
            clients.append(TextLocalSMSClient(tl_key, tl_sender))

        return clients

    def is_configured(self) -> bool:
        return len(self._clients) > 0

    async def send(self, phone: str, message: str) -> Dict[str, Any]:
        """
        Send SMS via first available configured provider.
        Returns {"success": bool, "provider": str, "error": str|None}
        """
        if not self._clients:
            return {"success": False, "provider": None,
                    "error": "No SMS provider configured. Set TWILIO_*, MSG91_*, or TEXTLOCAL_* env vars."}

        last_error = None
        for client in self._clients:
            result = await client.send(phone, message)
            if result["success"]:
                logger.info(f"SMS sent via {result['provider']} to {phone[:6]}***")
                return result
            last_error = result
            logger.warning(f"SMS via {result['provider']} failed: {result.get('error')}")

        return last_error or {"success": False, "error": "All SMS providers failed"}

    async def send_wa_with_sms_fallback(
        self,
        phone: str,
        message: str,
        wa_send_fn,          # async callable → dict with "success" and optional "meta_error"
        sms_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Try WhatsApp first; fall back to SMS if window is closed.

        Args:
            phone:       Recipient phone (E.164 without +)
            message:     Message to send
            wa_send_fn:  Async function that sends WA and returns result dict
            sms_message: Optional different text for SMS (defaults to same as WA)
        """
        wa_result = await wa_send_fn()
        if wa_result.get("success"):
            return {**wa_result, "channel": "whatsapp", "fallback_used": False}

        # Check if it's a window-closed error
        meta_error = wa_result.get("meta_error") or {}
        if is_window_closed_error(meta_error):
            logger.info(f"WA 24h window closed for {phone[:6]}*** — trying SMS fallback")
            sms_text = sms_message or message
            sms_result = await self.send(phone, sms_text)
            return {
                **sms_result,
                "channel": "sms",
                "fallback_used": True,
                "wa_error": wa_result.get("error") or meta_error,
            }

        # Non-window error — don't SMS
        return {**wa_result, "channel": "whatsapp", "fallback_used": False}
