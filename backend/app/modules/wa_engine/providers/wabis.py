"""
WABIS Provider  (bot.wabis.in API)
====================================
Outbound direct  → POST https://bot.wabis.in/api/v1/whatsapp/send
                   Params: apiToken, phone_number_id, message, phone_number
                   Used from: chat inbox (send_text), any direct message

Outbound workflow → POST to a WABIS Webhook Workflow URL (bot flow trigger)
                    Used for order notifications / blasts via campaign-type

Trigger bot flow  → POST https://bot.wabis.in/api/v1/whatsapp/trigger-bot
                    Params: apiToken, phone_number_id, bot_flow_unique_id, phone_number

Subscriber        → GET  https://bot.wabis.in/api/v1/whatsapp/subscriber/get
                    POST https://bot.wabis.in/api/v1/whatsapp/subscriber/create

Inbound           → WABIS fires POST to /api/wa/inbound/{tenant_id}
Test connection   → GET  https://bot.wabis.in/api/v1/whatsapp/subscriber/list
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from .base import InboundMessage, SendResult, WaProviderBase

log = logging.getLogger(__name__)

WABIS_API_BASE = "https://bot.wabis.in/api/v1"


class WabisProvider(WaProviderBase):
    """WABIS / BotSailor outbound + inbound provider using the public REST API."""

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @property
    def _api_base(self) -> str:
        return WABIS_API_BASE

    @property
    def _workflow_base(self) -> str:
        url = (self._settings.wabis_api_base_url or "https://admin.workpex.com").rstrip("/")
        return url

    @property
    def _api_token(self) -> Optional[str]:
        return self._settings.wabis_api_token

    @property
    def _phone_number_id(self) -> Optional[str]:
        return self._settings.wabis_phone_number_id

    @property
    def _bot_id(self) -> Optional[str]:
        """Legacy: returns first bot ID (comma-separated string)."""
        bot_ids = self.get_bot_ids()
        return bot_ids[0] if bot_ids else None

    def get_bot_ids(self) -> List[str]:
        """Get all configured Bot IDs (comma-separated)."""
        if not self._settings.wabis_bot_id:
            return []
        return [bid.strip() for bid in self._settings.wabis_bot_id.split(',') if bid.strip()]

    @property
    def _access_token(self) -> Optional[str]:
        return self._settings.wabis_access_token

    def _api_ready(self) -> bool:
        return bool(self._api_token and self._phone_number_id)

    # ------------------------------------------------------------------
    # WABIS v1 API helpers
    # ------------------------------------------------------------------

    async def _v1_post(self, path: str, data: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        url = f"{self._api_base}/{path.lstrip('/')}"
        resp = await client.post(url, data=data, timeout=15)
        resp.raise_for_status()
        return _safe_json(resp)

    async def _v1_get(self, path: str, params: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        url = f"{self._api_base}/{path.lstrip('/')}"
        resp = await client.get(url, params=params, timeout=15)
        resp.raise_for_status()
        return _safe_json(resp)

    # ------------------------------------------------------------------
    # Subscriber management
    # ------------------------------------------------------------------

    async def ensure_subscriber(self, *, phone_number: str, name: str = "") -> Optional[str]:
        """
        Ensure subscriber exists in WABIS. Creates if not found.
        Returns subscriber_id / chat_id, or None on failure.
        Phone must be digits only with country code (no +).
        """
        if not self._api_ready():
            return None

        clean = "".join(c for c in phone_number if c.isdigit())

        async with httpx.AsyncClient(timeout=15) as client:
            # Check if exists
            try:
                body = await self._v1_get(
                    "whatsapp/subscriber/get",
                    params={"apiToken": self._api_token, "phone_number_id": self._phone_number_id, "phone_number": clean},
                    client=client,
                )
                if body.get("status") == "1":
                    subs = body.get("message", [])
                    if isinstance(subs, list) and subs:
                        sid = str(subs[0].get("subscriber_id") or subs[0].get("chat_id") or clean)
                        log.debug("WABIS subscriber found: %s → id=%s", clean, sid)
                        return sid
            except Exception as e:
                log.debug("WABIS subscriber get: %s (will create)", e)

            # Create new subscriber
            try:
                body = await self._v1_post(
                    "whatsapp/subscriber/create",
                    data={"apiToken": self._api_token, "phoneNumberID": self._phone_number_id, "name": name or "Customer", "phoneNumber": clean},
                    client=client,
                )
                if body.get("status") == "1":
                    log.info("WABIS subscriber created: %s", clean)
                    return clean
                log.warning("WABIS subscriber create failed: %s", body.get("message"))
                return None
            except Exception as e:
                log.warning("WABIS subscriber create error: %s", e)
                return None

    # ------------------------------------------------------------------
    # Direct text message  (chat inbox → real WABIS send)
    # ------------------------------------------------------------------

    async def send_text(self, *, phone: str, text: str, name: str = "") -> SendResult:
        """
        Send a plain text message via WABIS API.
        POST https://bot.wabis.in/api/v1/whatsapp/send
        """
        if not self._api_ready():
            return SendResult(
                success=False,
                error="WABIS not configured — set API Token and Phone Number ID in WA Settings",
            )

        clean = "".join(c for c in phone if c.isdigit())
        await self.ensure_subscriber(phone_number=clean, name=name)

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                body = await self._v1_post(
                    "whatsapp/send",
                    data={"apiToken": self._api_token, "phone_number_id": self._phone_number_id, "message": text, "phone_number": clean},
                    client=client,
                )
                if body.get("status") == "1":
                    return SendResult(success=True, provider_message_id=body.get("wa_message_id"), raw_response=body)
                err = body.get("message", "WABIS send returned status=0")
                log.warning("WABIS send_text failed: %s", err)
                return SendResult(success=False, error=err, raw_response=body)
        except httpx.HTTPStatusError as exc:
            err = f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"
            log.warning("WABIS send_text HTTP error: %s", err)
            return SendResult(success=False, error=err)
        except Exception as exc:
            log.exception("WABIS send_text unexpected error")
            return SendResult(success=False, error=str(exc))

    # ------------------------------------------------------------------
    # Trigger bot flow
    # ------------------------------------------------------------------

    async def trigger_bot(self, *, phone: str, bot_flow_unique_id: str, name: str = "") -> SendResult:
        """Trigger a WABIS bot flow: POST /api/v1/whatsapp/trigger-bot"""
        if not self._api_ready():
            return SendResult(success=False, error="WABIS not configured — set apiToken + phone_number_id")

        clean = "".join(c for c in phone if c.isdigit())
        await self.ensure_subscriber(phone_number=clean, name=name)

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                body = await self._v1_post(
                    "whatsapp/trigger-bot",
                    data={"apiToken": self._api_token, "phone_number_id": self._phone_number_id, "bot_flow_unique_id": bot_flow_unique_id, "phone_number": clean},
                    client=client,
                )
                if body.get("status") == "1":
                    return SendResult(success=True, raw_response=body)
                err = body.get("message", "trigger-bot status=0")
                return SendResult(success=False, error=err, raw_response=body)
        except httpx.HTTPStatusError as exc:
            err = f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"
            log.warning("WABIS trigger_bot HTTP error: %s", err)
            return SendResult(success=False, error=err)
        except Exception as exc:
            log.exception("WABIS trigger_bot unexpected error")
            return SendResult(success=False, error=str(exc))

    # ------------------------------------------------------------------
    # Workflow URL send  (order notifications / blasts)
    # ------------------------------------------------------------------

    async def send_template(self, *, phone: str, workflow_url: str, payload: Dict[str, Any]) -> SendResult:
        """POST JSON payload to a WABIS Webhook Workflow URL (for order notifications / blasts)."""
        if not workflow_url:
            return SendResult(success=False, error="workflow_url is required for WABIS")

        payload.setdefault("phone", phone)
        payload.setdefault("phone_number", phone)

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(workflow_url, json=payload)
                resp.raise_for_status()
                body = _safe_json(resp)
                log.debug("WABIS send_template → %s body=%s", resp.status_code, body)
                return SendResult(success=True, provider_message_id=body.get("message_id") or body.get("id"), raw_response=body)
        except httpx.HTTPStatusError as exc:
            err = f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"
            log.warning("WABIS send_template error: %s", err)
            return SendResult(success=False, error=err, raw_response=_safe_json(exc.response))
        except Exception as exc:
            log.exception("WABIS send_template unexpected error")
            return SendResult(success=False, error=str(exc))

    # ------------------------------------------------------------------
    # Connection test
    # ------------------------------------------------------------------

    async def test_connection(self) -> tuple[bool, str]:
        if self._api_ready():
            try:
                # Test connection by attempting to ensure a test subscriber (will succeed if auth is valid)
                async with httpx.AsyncClient(timeout=10) as client:
                    body = await self._v1_post(
                        "whatsapp/subscriber/get",
                        data={"apiToken": self._api_token, "phone_number_id": self._phone_number_id, "phone_number": "1234567890"},
                        client=client,
                    )
                    # Both success and not-found are valid — means API is responding
                    if body and isinstance(body, dict):
                        return True, "✅ WABIS API connected successfully"
                    return False, f"WABIS API error: {body}"
            except httpx.ConnectError:
                return False, f"Cannot reach WABIS API at {self._api_base}"
            except Exception as exc:
                return False, str(exc)
        elif self._bot_id and self._access_token:
            url = f"{self._workflow_base}/api/bot/{self._bot_id}/subscriber/list"
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(url, headers={"Authorization": f"Bearer {self._access_token}", "Accept": "application/json"})
                    if resp.status_code == 200:
                        return True, "Connected (legacy mode — set apiToken + phone_number_id for full features)"
                    return False, f"Status {resp.status_code}"
            except Exception as exc:
                return False, str(exc)
        else:
            return False, "WABIS not configured — set API Token and Phone Number ID in WA Settings"

    # ------------------------------------------------------------------
    # Inbound parsing
    # ------------------------------------------------------------------

    @classmethod
    def parse_inbound(cls, raw: Dict[str, Any]) -> Optional[InboundMessage]:
        """
        Parse a WABIS Out-bound Webhook POST body.

        WABIS actual payload fields (as fired from their platform):
          subscriber_id        → e.g. "919447480687-43011"
          first_name           → subscriber display name
          chat_id              → phone number (digits only, no +)
          birthdate            → date of birth
          user_location_gps    → location string
          label_names          → comma-separated labels, e.g. "Price_checked"
          postbackid           → postback ID (note: no underscore)
          whatsapp_bot_username → the bot's WA number

        Also handles generic / legacy field names as fallback.
        """
        # ── subscriber identity ────────────────────────────────────────
        subscriber_id = (
            raw.get("subscriber_id")
            or raw.get("id")
            or raw.get("user_id")
        )
        # chat_id is the phone number in WABIS payloads
        phone = (
            raw.get("chat_id")            # WABIS actual field
            or raw.get("phone_number")
            or raw.get("phone")
            or raw.get("mobile")
            or ""
        )
        if not subscriber_id and not phone:
            return None

        # ── name ──────────────────────────────────────────────────────
        name = (
            raw.get("first_name")         # WABIS actual field
            or raw.get("subscriber_name")
            or raw.get("name")
        )

        # ── labels ────────────────────────────────────────────────────
        labels: List[str] = []
        raw_labels = (
            raw.get("label_names")        # WABIS actual field
            or raw.get("labels")
        )
        if isinstance(raw_labels, list):
            labels = [str(l) for l in raw_labels if l]
        elif isinstance(raw_labels, str) and raw_labels.strip():
            labels = [l.strip() for l in raw_labels.split(",") if l.strip()]

        # ── postback ──────────────────────────────────────────────────
        postback_id = (
            raw.get("postbackid")         # WABIS actual field (no underscore)
            or raw.get("postback_id")
            or raw.get("postback")
            or raw.get("quick_reply_id")
        )

        # ── message text ──────────────────────────────────────────────
        message_text = raw.get("message") or raw.get("text")
        # If only a postback fired (no free text), synthesise a readable label
        if not message_text and postback_id:
            message_text = f"[postback: {postback_id}]"

        return InboundMessage(
            subscriber_id=str(subscriber_id or phone),
            phone_number=str(phone),
            subscriber_name=name,
            postback_id=postback_id,
            labels=labels,
            message_text=message_text,
            raw_payload=raw,
        )


# ─── helpers ─────────────────────────────────────────────────────────────────

def _safe_json(resp: httpx.Response) -> Dict[str, Any]:
    try:
        return resp.json()
    except Exception:
        return {"raw": resp.text[:500]}

