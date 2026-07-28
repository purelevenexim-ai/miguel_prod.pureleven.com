"""
Labels & WhatsApp Schemas
--------------------------
Request/Response shapes for the labels and WhatsApp endpoints.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID
from pydantic import BaseModel


# ─────────────────────────────────────────────────────────────
# Label Generation
# ─────────────────────────────────────────────────────────────

class LabelRequest(BaseModel):
    """Request a PDF label for a list of order IDs."""
    order_ids: list[UUID]


class LabelResponse(BaseModel):
    """Returned after generating PDF — confirms what was printed."""
    orders_printed: int
    skipped:        int
    message:        str


# ─────────────────────────────────────────────────────────────
# WhatsApp Message
# ─────────────────────────────────────────────────────────────

class WhatsAppMessageResponse(BaseModel):
    """Single order → WhatsApp message payload."""
    order_id:       str
    order_number:   str
    to:             str             # E.164 e.g. 919876543210
    phone_display:  str             # +91 98765 43210
    template:       str             # "pre_dispatch" | "shipped"
    message:        str             # plain text
    wa_url:         str             # https://wa.me/...?text=...


class WhatsAppBulkResponse(BaseModel):
    """Batch of WhatsApp messages for selected orders."""
    total:      int
    results:    list[WhatsAppMessageResponse]
