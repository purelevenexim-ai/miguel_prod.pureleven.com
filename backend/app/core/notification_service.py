"""
Notification Service — Phase 3
Sends WhatsApp notifications for order lifecycle events by leveraging
the existing wa_engine module (send_order_notification + send_notification).

Trigger events used (WaTriggerEvent enum):
  - order_confirmed   → order just placed
  - order_shipped     → shipment created + tracking number assigned
  - order_delivered   → delivered by courier
  - order_packed      → re-used for "out for delivery" alert
  - manual            → COD confirmation, NDR alerts, admin alerts (direct message)
"""
import logging
import uuid as _uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.logistics import NotificationLog
from app.models.shopify_order import ShopifyOrder

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Sends notifications via WhatsApp using the existing wa_engine module.
    - Lifecycle events (order_confirmed, order_shipped, order_delivered, order_packed)
      are routed through wa_engine.send_order_notification() which looks up the
      WABIS workflow URL from wa_campaign_types table.
    - Direct alerts (COD, NDR, RTO, high-risk) use wa_engine.send_notification()
      with a freeform message variable.
    All attempts are logged to notification_logs table.
    If no campaign type / wa_settings are configured, the send is logged as
    'skipped' (non-fatal) so the rest of the order flow continues unaffected.
    """

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = _uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id

    # ── Customer Lifecycle (wa_engine campaign templates) ─────

    async def send_order_confirmed(self, order: ShopifyOrder) -> bool:
        """Notify customer their order is confirmed."""
        return await self._send_lifecycle(
            order=order,
            trigger_event="order_confirmed",
            variables={
                "order_number":  order.shopify_order_name,
                "customer_name": order.customer_name or "Customer",
                "total_price":   str(order.total_price),
                "currency":      order.currency or "INR",
            },
        )

    async def send_shipment_created(self, order: ShopifyOrder, tracking_number: str, tracking_url: str) -> bool:
        """Notify customer their shipment has been created."""
        partner = (order.shipping_partner.value.replace("_", " ").title()
                   if order.shipping_partner else "Courier")
        return await self._send_lifecycle(
            order=order,
            trigger_event="order_shipped",
            variables={
                "order_number":    order.shopify_order_name,
                "customer_name":   order.customer_name or "Customer",
                "tracking_number": tracking_number,
                "tracking_url":    tracking_url,
                "courier":         partner,
            },
        )

    async def send_out_for_delivery(self, order: ShopifyOrder, tracking_number: str) -> bool:
        """Notify customer their order is out for delivery."""
        return await self._send_lifecycle(
            order=order,
            trigger_event="order_packed",
            variables={
                "order_number":    order.shopify_order_name,
                "customer_name":   order.customer_name or "Customer",
                "tracking_number": tracking_number,
            },
        )

    async def send_delivered(self, order: ShopifyOrder) -> bool:
        """Notify customer their order has been delivered."""
        return await self._send_lifecycle(
            order=order,
            trigger_event="order_delivered",
            variables={
                "order_number":  order.shopify_order_name,
                "customer_name": order.customer_name or "Customer",
            },
        )

    # ── Direct Alerts (wa_engine freeform, no campaign template needed) ─

    async def send_cod_confirmation(self, order: ShopifyOrder, confirmation_code: str) -> bool:
        """Ask customer to confirm COD order before shipping."""
        phone = order.customer_phone or order.shipping_phone
        name  = order.customer_name or "Customer"
        msg = (
            f"Hi {name}! Your COD order *{order.shopify_order_name}* worth "
            f"₹{order.total_price:,.0f} needs confirmation.\n"
            f"Reply with code *{confirmation_code}* (valid 30 min) to confirm, "
            f"or *CANCEL* to cancel."
        )
        return await self._send_direct(phone=phone, message=msg,
                                       message_type="cod_confirmation", order=order)

    async def send_ndr_customer_alert(self, order: ShopifyOrder, ndr_reason: str, attempt: int) -> bool:
        """Notify customer about failed delivery attempt."""
        phone = order.customer_phone or order.shipping_phone
        msg = (
            f"Hi {order.customer_name or 'Customer'}! Delivery of "
            f"*{order.shopify_order_name}* failed (Attempt #{attempt}). "
            f"Reason: {ndr_reason}. Re-attempt scheduled — please be available."
        )
        return await self._send_direct(phone=phone, message=msg,
                                       message_type="ndr_alert", order=order)

    async def send_rto_admin_alert(self, order: ShopifyOrder, admin_phone: str) -> bool:
        """Alert admin that an order is being returned to origin."""
        msg = (
            f"🚨 RTO — {order.shopify_order_name}\n"
            f"Customer: {order.customer_name} | {order.customer_phone}\n"
            f"City: {order.shipping_city}, {order.shipping_zip} | "
            f"₹{order.total_price:,.0f}"
        )
        return await self._send_direct(phone=admin_phone, message=msg,
                                       message_type="rto_admin_alert", order=order)

    async def send_high_risk_order_alert(self, order: ShopifyOrder, admin_phone: str, risk_reasons: list) -> bool:
        """Alert admin about a high-risk order requiring review."""
        reasons = "\n".join(f"• {r}" for r in risk_reasons)
        msg = (
            f"⚠️ High-Risk Order — {order.shopify_order_name}\n"
            f"{order.customer_name} | {order.customer_phone} | "
            f"₹{order.total_price:,.0f}\n{reasons}"
        )
        return await self._send_direct(phone=admin_phone, message=msg,
                                       message_type="high_risk_alert", order=order)

    # ── Internal ───────────────────────────────────────────────

    async def _send_lifecycle(self, order: ShopifyOrder, trigger_event: str, variables: dict) -> bool:
        """Route lifecycle event through wa_engine campaign template."""
        phone = order.customer_phone or order.shipping_phone
        if not phone:
            logger.warning(f"No phone for {trigger_event} (order {order.shopify_order_name})")
            return False
        phone = self._normalize_phone(phone)

        log = NotificationLog(
            tenant_id=self.tenant_id,
            shopify_order_id=order.id,
            channel="whatsapp",
            recipient=phone,
            message_type=trigger_event,
            message_body=str(variables),
            status="pending",
        )
        self.db.add(log)

        try:
            from app.modules.wa_engine.service import send_order_notification

            result = await send_order_notification(
                db=self.db,
                tenant_id=self.tenant_id,
                trigger_event=trigger_event,
                phone=phone,
                variables=variables,
            )

            if result is None:
                # No WaCampaignType configured — non-fatal, skip gracefully
                log.status        = "skipped"
                log.error_message = f"No WaCampaignType for trigger_event={trigger_event}"
                self.db.commit()
                logger.info(f"Notification skipped — no campaign type for {trigger_event}")
                return False

            if result.get("success"):
                log.status            = "sent"
                log.provider_id       = result.get("provider_message_id")
                log.sent_at           = datetime.now(timezone.utc)
                log.provider_response = result
                self.db.commit()
                return True

            log.status        = "failed"
            log.error_message = result.get("message")
            self.db.commit()
            return False

        except Exception as e:
            log.status        = "failed"
            log.error_message = str(e)
            self.db.commit()
            logger.error(f"Lifecycle notification error ({trigger_event}→{phone}): {e}")
            return False

    async def _send_direct(self, phone: Optional[str], message: str,
                           message_type: str, order: Optional[ShopifyOrder] = None) -> bool:
        """Send a freeform WhatsApp message via wa_engine.send_notification()."""
        if not phone:
            logger.warning(f"No phone for direct notification ({message_type})")
            return False
        phone = self._normalize_phone(phone)

        log = NotificationLog(
            tenant_id=self.tenant_id,
            shopify_order_id=order.id if order else None,
            channel="whatsapp",
            recipient=phone,
            message_type=message_type,
            message_body=message,
            status="pending",
        )
        self.db.add(log)

        try:
            from app.modules.wa_engine.service import send_notification

            result = await send_notification(
                db=self.db,
                tenant_id=self.tenant_id,
                phone=phone,
                variables={"message": message},
            )

            if result and result.get("success"):
                log.status            = "sent"
                log.sent_at           = datetime.now(timezone.utc)
                log.provider_response = result
                self.db.commit()
                return True

            log.status        = "skipped"
            log.error_message = (result.get("message", "No workflow URL") if result
                                 else "No wa_settings configured")
            self.db.commit()
            return False

        except Exception as e:
            log.status        = "failed"
            log.error_message = str(e)
            self.db.commit()
            logger.error(f"Direct notification error ({message_type}→{phone}): {e}")
            return False

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Normalize Indian phone numbers to E.164 (+91XXXXXXXXXX) format."""
        phone = (phone.strip()
                 .replace(" ", "").replace("-", "")
                 .replace("(", "").replace(")", ""))
        if phone.startswith("0"):
            phone = "+91" + phone[1:]
        elif phone.startswith("91") and len(phone) == 12:
            phone = "+" + phone
        elif len(phone) == 10 and phone.isdigit():
            phone = "+91" + phone
        elif not phone.startswith("+"):
            phone = "+" + phone
        return phone
