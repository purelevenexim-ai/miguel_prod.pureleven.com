"""
WhatsApp Provider — Abstract Base
====================================
All provider implementations must subclass WaProviderBase and implement
every abstract method.  The service layer talks only to this interface,
making it trivial to swap or add providers without touching business logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SendResult:
    """Normalised result returned by every provider after a send attempt."""
    success:            bool
    provider_message_id: Optional[str] = None
    raw_response:       Optional[Dict[str, Any]] = None
    error:              Optional[str] = None


@dataclass
class InboundMessage:
    """Normalised inbound event parsed from a provider's webhook payload."""
    subscriber_id:   str
    phone_number:    str
    subscriber_name: Optional[str]
    postback_id:     Optional[str]
    labels:          List[str]          = field(default_factory=list)
    message_text:    Optional[str]      = None
    raw_payload:     Dict[str, Any]     = field(default_factory=dict)


class WaProviderBase(ABC):
    """
    Abstract interface every WhatsApp provider must implement.

    Parameters passed to __init__:
        settings_row  — the WaSettings ORM object for this tenant
    """

    def __init__(self, settings_row: Any) -> None:
        self._settings = settings_row

    # ── outbound ─────────────────────────────────────────────

    @abstractmethod
    async def send_template(
        self,
        *,
        phone: str,
        workflow_url: str,
        payload: Dict[str, Any],
    ) -> SendResult:
        """
        Send a WhatsApp message/template to `phone`.

        For WABIS  : POST `payload` to `workflow_url` (Webhook Workflow).
        For Meta   : call Graph API send-message endpoint; `workflow_url`
                     is ignored (template name lives inside `payload`).
        """

    @abstractmethod
    async def send_text(
        self,
        *,
        phone: str,
        text:  str,
    ) -> SendResult:
        """Send a free-form text message (used for auto-reply and 1:1 chat)."""

    # ── connection test ───────────────────────────────────────

    @abstractmethod
    async def test_connection(self) -> tuple[bool, str]:
        """
        Verify credentials are valid.
        Returns (success: bool, message: str).
        """

    # ── inbound parsing ───────────────────────────────────────

    @classmethod
    @abstractmethod
    def parse_inbound(cls, raw: Dict[str, Any]) -> Optional[InboundMessage]:
        """
        Parse a raw webhook POST body into a normalised InboundMessage.
        Return None if the payload is not a recognisable inbound event
        (e.g. a status-update ping that should be silently ignored).
        """
