"""
Perfect WhatsApp Message Journey Model
=====================================

One message per checkpoint:
1. Order Created → Immediate (within 24h window)
2. Tracking Added → Immediate (within 24h window)
3. Tracking Update → +3 days after tracking added (ONCE ONLY)
4. Delivery Thanks → After delivery status (ONCE ONLY)
5. Review Request → +15 days after delivery (ONCE ONLY)
6. Product Promo → +60 days after last purchase (ONCE ONLY)

Safeguards:
- Cancelled/deleted orders → cancel all pending messages
- Only 1 message per checkpoint (deduplication)
- Uses conversation_window to determine message type
- Proper state tracking to prevent duplicates
"""

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional
import uuid

UTC = timezone.utc


class JourneyCheckpoint(str, Enum):
    """Customer journey checkpoints - one message each"""
    ORDER_CREATED = "order_created"  # Immediate
    TRACKING_ADDED = "tracking_added"  # Immediate
    TRACKING_UPDATE = "tracking_update_3day"  # +3 days (ONCE)
    DELIVERY_THANKS = "delivery_thanks"  # After delivery (ONCE)
    REVIEW_REQUEST = "review_request_15day"  # +15 days (ONCE)
    PRODUCT_PROMO = "product_promo_60day"  # +60 days (ONCE)
    WEBSITE_REMINDER = "website_reminder_90day"  # +90 days (ONCE)


class MessageTemplateType(str, Enum):
    """WhatsApp template types and costs"""
    AUTHENTICATION = "authentication"  # ₹0.50 (auth codes)
    UTILITY = "utility"  # ₹0.75 (order, tracking, delivery)
    MARKETING = "marketing"  # ₹1.00 (promo, review request)


class MessageScheduleRule:
    """Defines when and how a message is scheduled"""

    checkpoint: JourneyCheckpoint
    template_key: str
    template_type: MessageTemplateType

    # Trigger: when to schedule this message
    trigger_event: str  # "order_created", "tracking_added", "order_delivered", "days_since_delivery"
    trigger_days: Optional[int] = None  # Days offset from trigger_event

    # Deduplication
    dedupe_scope: str  # "order:once" or "customer:once" or "customer:monthly"

    # Cancellation rules
    cancel_on_order_status: list = None  # Cancel if order status becomes one of these

    def __init__(
        self,
        checkpoint: JourneyCheckpoint,
        template_key: str,
        template_type: MessageTemplateType,
        trigger_event: str,
        trigger_days: Optional[int] = None,
        dedupe_scope: str = "order:once",
        cancel_on_order_status: Optional[list] = None,
    ):
        self.checkpoint = checkpoint
        self.template_key = template_key
        self.template_type = template_type
        self.trigger_event = trigger_event
        self.trigger_days = trigger_days or 0
        self.dedupe_scope = dedupe_scope
        self.cancel_on_order_status = cancel_on_order_status or ["cancelled", "returned"]


# Perfect Journey Definition
JOURNEY_RULES = {
    JourneyCheckpoint.ORDER_CREATED: MessageScheduleRule(
        checkpoint=JourneyCheckpoint.ORDER_CREATED,
        template_key="order_created",
        template_type=MessageTemplateType.UTILITY,
        trigger_event="order_created",
        trigger_days=0,
        dedupe_scope="order:once",
    ),

    JourneyCheckpoint.TRACKING_ADDED: MessageScheduleRule(
        checkpoint=JourneyCheckpoint.TRACKING_ADDED,
        template_key="tracking_added",
        template_type=MessageTemplateType.UTILITY,
        trigger_event="tracking_added",
        trigger_days=0,
        dedupe_scope="order:once",
    ),

    JourneyCheckpoint.TRACKING_UPDATE: MessageScheduleRule(
        checkpoint=JourneyCheckpoint.TRACKING_UPDATE,
        template_key="tracking_update_3day",  # NEW: renamed from tracking_followup_3_day
        template_type=MessageTemplateType.UTILITY,
        trigger_event="tracking_added",
        trigger_days=3,  # 3 days after tracking added
        dedupe_scope="order:once",  # CRITICAL: only ONCE per order
    ),

    JourneyCheckpoint.DELIVERY_THANKS: MessageScheduleRule(
        checkpoint=JourneyCheckpoint.DELIVERY_THANKS,
        template_key="delivery_thanks",  # NEW: thank you after delivery
        template_type=MessageTemplateType.UTILITY,
        trigger_event="order_delivered",
        trigger_days=0,
        dedupe_scope="order:once",
    ),

    JourneyCheckpoint.REVIEW_REQUEST: MessageScheduleRule(
        checkpoint=JourneyCheckpoint.REVIEW_REQUEST,
        template_key="review_request",
        template_type=MessageTemplateType.MARKETING,
        trigger_event="order_delivered",
        trigger_days=15,  # 15 days after delivery
        dedupe_scope="order:once",  # CRITICAL: only ONCE per order
        # Note: Sent to ALL orders (no minimum order value filter)
    ),

    JourneyCheckpoint.PRODUCT_PROMO: MessageScheduleRule(
        checkpoint=JourneyCheckpoint.PRODUCT_PROMO,
        template_key="product_promo_60day",  # NEW: ask for repurchase
        template_type=MessageTemplateType.MARKETING,
        trigger_event="order_delivered",
        trigger_days=60,  # 60 days after delivery
        dedupe_scope="customer:once",  # CRITICAL: once per customer per 60-day window
    ),

    JourneyCheckpoint.WEBSITE_REMINDER: MessageScheduleRule(
        checkpoint=JourneyCheckpoint.WEBSITE_REMINDER,
        template_key="website_reminder_90day",  # NEW: remind to order from website
        template_type=MessageTemplateType.MARKETING,
        trigger_event="order_delivered",
        trigger_days=90,  # 90 days after delivery
        dedupe_scope="customer:once",  # CRITICAL: once per customer per 90-day window
    ),
}


def get_scheduled_at(trigger_event: str, trigger_days: int, reference_time: datetime) -> datetime:
    """Calculate scheduled_at based on trigger event and days offset"""
    if trigger_days > 0:
        return reference_time + timedelta(days=trigger_days)
    return reference_time


def get_dedupe_key(
    checkpoint: JourneyCheckpoint,
    order_id: Optional[uuid.UUID] = None,
    customer_id: Optional[uuid.UUID] = None,
    scheduled_date: Optional[str] = None,
) -> str:
    """
    Generate deduplication key to ensure ONE message per checkpoint.

    Examples:
    - order:uuid:checkpoint:order_created → only once per order
    - customer:uuid:checkpoint:review_request → only once per customer
    - customer:uuid:checkpoint:product_promo:2026-06 → once per month
    """
    if order_id:
        return f"order:{order_id}:checkpoint:{checkpoint.value}"
    elif customer_id:
        if checkpoint == JourneyCheckpoint.PRODUCT_PROMO and scheduled_date:
            # Product promo: once per customer per 60-day window (use year-month)
            return f"customer:{customer_id}:checkpoint:{checkpoint.value}:{scheduled_date[:7]}"
        else:
            return f"customer:{customer_id}:checkpoint:{checkpoint.value}"
    return f"checkpoint:{checkpoint.value}"


def should_skip_message(
    order_status: str,
    cancel_on_statuses: list,
) -> bool:
    """Check if message should be cancelled due to order status"""
    return order_status in cancel_on_statuses


def is_within_24h_window(
    trigger_time: datetime,
    current_time: datetime,
) -> bool:
    """
    Check if current time is within 24 hours of trigger time.
    Used to determine if template is free (within 24h) or paid (outside 24h).
    """
    elapsed = (current_time - trigger_time).total_seconds() / 3600
    return 0 <= elapsed <= 24


def get_template_cost(
    checkpoint: JourneyCheckpoint,
    template_type: MessageTemplateType,
    within_24h: bool = False,
) -> float:
    """
    Get message cost in INR based on template type and timing.

    Within 24h of conversation start: free or cheaper
    Outside 24h: paid template rates
    """
    # Template type rates (outside 24h window)
    rates = {
        MessageTemplateType.AUTHENTICATION: 0.50,
        MessageTemplateType.UTILITY: 0.75,
        MessageTemplateType.MARKETING: 1.00,
    }

    base_cost = rates[template_type]

    # Within 24h window: 80% of cost (cheaper)
    if within_24h:
        return base_cost * 0.8

    return base_cost
