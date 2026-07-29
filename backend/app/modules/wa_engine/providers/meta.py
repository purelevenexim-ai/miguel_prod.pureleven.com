"""
Meta Cloud API Provider
=========================
Handles outbound via Meta's Graph API and inbound via Meta's webhook
(hub.challenge verification + message events).
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any, Dict, List, Optional

import httpx

from .base import InboundMessage, SendResult, WaProviderBase

log = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.facebook.com"


class MetaProvider(WaProviderBase):
    """Meta Cloud API (WhatsApp Business Platform) provider."""

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @property
    def _version(self) -> str:
        return self._settings.meta_api_version or "v19.0"

    @property
    def _phone_id(self) -> Optional[str]:
        return self._settings.meta_phone_number_id

    @property
    def _token(self) -> Optional[str]:
        return self._settings.meta_access_token

    def _messages_url(self) -> str:
        return f"{GRAPH_BASE}/{self._version}/{self._phone_id}/messages"

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type":  "application/json",
        }

    # ------------------------------------------------------------------
    # outbound
    # ------------------------------------------------------------------

    async def send_template(
        self,
        *,
        phone:        str,
        workflow_url: str,
        payload:      Dict[str, Any],
    ) -> SendResult:
        """
        Send a Meta-approved message template.
        `payload` must contain:
            template_name, language_code (optional), components (optional)
        `workflow_url` is ignored for Meta — templates go via Graph API.
        """
        if not self._phone_id or not self._token:
            return SendResult(success=False, error="meta_phone_number_id or access_token not configured")

        template_name = payload.get("template_name", "hello_world")
        language_code = payload.get("language_code", "en")
        components    = payload.get("components", [])

        body: Dict[str, Any] = {
            "messaging_product": "whatsapp",
            "to":                _normalise_phone(phone),
            "type":              "template",
            "template": {
                "name":     template_name,
                "language": {"code": language_code},
            },
        }
        if components:
            body["template"]["components"] = components

        return await self._post_message(body)

    async def send_text(
        self,
        *,
        phone: str,
        text:  str,
        name:  str = "",        # accepted for API compatibility with WabisProvider; unused by Meta
    ) -> SendResult:
        if not self._phone_id or not self._token:
            return SendResult(success=False, error="meta_phone_number_id or access_token not configured")

        body: Dict[str, Any] = {
            "messaging_product": "whatsapp",
            "to":                _normalise_phone(phone),
            "type":              "text",
            "text":              {"body": text},
        }
        return await self._post_message(body)

    async def _post_message(self, body: Dict[str, Any]) -> SendResult:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    self._messages_url(), json=body, headers=self._headers()
                )
                resp.raise_for_status()
                rjson = _safe_json(resp)
                msg_id = None
                messages = rjson.get("messages", [])
                if messages:
                    msg_id = messages[0].get("id")
                return SendResult(
                    success=True,
                    provider_message_id=msg_id,
                    raw_response=rjson,
                )
        except httpx.HTTPStatusError as exc:
            err_body = _safe_json(exc.response)
            err_msg  = (
                err_body.get("error", {}).get("message")
                or f"HTTP {exc.response.status_code}"
            )
            log.warning("Meta send error: %s", err_msg)
            return SendResult(success=False, error=err_msg, raw_response=err_body)
        except Exception as exc:
            log.exception("Meta send unexpected error")
            return SendResult(success=False, error=str(exc))

    # ------------------------------------------------------------------
    # connection test
    # ------------------------------------------------------------------

    async def test_connection(self) -> tuple[bool, str]:
        if not self._phone_id or not self._token:
            return False, "meta_phone_number_id or access_token not configured"

        url = f"{GRAPH_BASE}/{self._version}/{self._phone_id}"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, headers=self._headers())
                if resp.status_code == 200:
                    data = resp.json()
                    display = data.get("display_phone_number", "")
                    return True, f"Connected — {display}"
                body = _safe_json(resp)
                err  = body.get("error", {}).get("message", resp.text[:200])
                return False, err
        except Exception as exc:
            return False, str(exc)

    # ------------------------------------------------------------------
    # inbound parsing  (Meta webhook event)
    # ------------------------------------------------------------------

    @classmethod
    def parse_statuses(cls, raw: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract message-status callbacks (sent/delivered/read/failed) from a
        Meta webhook POST body. These arrive in entry → changes → value →
        statuses[], as a separate webhook delivery from messages[] — a
        message send and its later delivery/read receipt are never in the
        same payload.
        """
        try:
            entry  = raw.get("entry", [{}])[0]
            change = entry.get("changes", [{}])[0]
            value  = change.get("value", {})
            statuses = value.get("statuses", [])
        except (IndexError, AttributeError):
            return []
        return statuses if isinstance(statuses, list) else []

    @classmethod
    def parse_inbound(cls, raw: Dict[str, Any]) -> Optional[InboundMessage]:
        """
        Parse a Meta webhook POST body.  Meta sends batched events inside
        entry → changes → value → messages[].
        """
        try:
            entry   = raw.get("entry", [{}])[0]
            change  = entry.get("changes", [{}])[0]
            value   = change.get("value", {})
            messages: List[Dict] = value.get("messages", [])
            contacts: List[Dict] = value.get("contacts", [])
        except (IndexError, AttributeError):
            return None

        if not messages:
            return None

        msg      = messages[0]
        phone    = msg.get("from", "")
        msg_type = msg.get("type", "text")
        text     = ""

        if msg_type == "text":
            text = msg.get("text", {}).get("body", "")
        elif msg_type == "interactive":
            inter = msg.get("interactive", {})
            if inter.get("type") == "button_reply":
                text = inter["button_reply"].get("title", "")
            elif inter.get("type") == "list_reply":
                text = inter["list_reply"].get("title", "")

        name = ""
        if contacts:
            name = contacts[0].get("profile", {}).get("name", "")

        wa_id = contacts[0].get("wa_id", phone) if contacts else phone

        return InboundMessage(
            subscriber_id=wa_id or phone,
            phone_number=phone,
            subscriber_name=name or None,
            postback_id=None,           # Meta doesn't use postback_id
            labels=[],
            message_text=text or None,
            raw_payload=raw,
        )

    # ------------------------------------------------------------------
    # webhook hub.challenge verification (called from router)
    # ------------------------------------------------------------------

    @classmethod
    def verify_challenge(
        cls,
        mode:        Optional[str],
        token:       Optional[str],
        challenge:   Optional[str],
        verify_token: str,
    ) -> Optional[str]:
        """
        Return the challenge string if valid, else None.
        """
        if mode == "subscribe" and token == verify_token:
            return challenge
        return None

    @classmethod
    def verify_signature(
        cls,
        body_bytes:    bytes,
        sig_header:    Optional[str],
        app_secret:    str,
    ) -> bool:
        """
        Validate X-Hub-Signature-256 header.
        """
        if not sig_header or not sig_header.startswith("sha256="):
            return False
        expected = hmac.new(
            app_secret.encode(), body_bytes, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(sig_header[7:], expected)


# ─── helpers ─────────────────────────────────────────────────────────────────

def _normalise_phone(phone: str) -> str:
    """Strip leading + so Meta receives digit-only E.164."""
    return phone.lstrip("+").replace(" ", "").replace("-", "")


def _safe_json(resp: httpx.Response) -> Dict[str, Any]:
    try:
        return resp.json()
    except Exception:
        return {"raw": resp.text[:500]}
