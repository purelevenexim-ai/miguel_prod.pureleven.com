"""
Background Tracking Sync Worker — Phase 3
Polls Delhivery & India Post every 15 minutes for tracking updates.
Handles delivery events, NDR events, RTO events.
Updates customer scores and RTO zones automatically.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine

from app.database.session import engine
from app.models.shopify_order import ShopifyOrder, ShippingInfo, TrackingStatus, ShippingPartner, ShopifyFulfillmentStatus
from app.models.shipping_config import DeliveryPartner, ShippingBusinessRules
from app.models.logistics import NdrRecord, NdrReason, NdrStatus
from app.modules.orders.shopify_sync_service import ShopifyOrderSyncService
from app.core.risk_engine import RiskEngine
from app.core.notification_service import NotificationService
from app.core.shipping.delhivery_client import DelhiveryAPIClient
from app.core.shipping.india_post_client import IndiaPostAPIClient
from app.modules.orders import tracking_sync_service

logger = logging.getLogger(__name__)

# Global flag to stop worker
_worker_running = False
_worker_task = None
MANUAL_ORDER_SYNC_INTERVAL = timedelta(minutes=30)


async def run_tracking_sync():
    """
    Main background worker loop.
    Runs every 15 minutes, syncing tracking for all active shipments.
    """
    global _worker_running
    logger.info("📦 Tracking sync worker started")
    last_manual_order_sync = None

    while _worker_running:
        try:
            await sync_all_active_shipments()
            now = datetime.now(timezone.utc)
            if last_manual_order_sync is None or (now - last_manual_order_sync) >= MANUAL_ORDER_SYNC_INTERVAL:
                await sync_all_manual_india_post_orders()
                last_manual_order_sync = now
        except Exception as e:
            logger.error(f"Tracking sync cycle error: {e}")

        # Wait 15 minutes before next cycle
        logger.info("⏰ Next tracking sync in 15 minutes; India Post manual orders every 30 minutes")
        await asyncio.sleep(15 * 60)

    logger.info("📦 Tracking sync worker stopped")


async def sync_all_manual_india_post_orders():
    """Refresh manual CRM order tracking from India Post every 30 minutes."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        summary = await tracking_sync_service.sync_all_tenants_india_post_orders(db, days=7, limit=50)
        logger.info(
            "India Post manual order sync complete: tenants=%s updated=%s",
            summary.get("tenants_checked", 0),
            summary.get("orders_updated", 0),
        )
    except Exception as e:
        db.rollback()
        logger.error(f"India Post manual order sync error: {e}")
    finally:
        db.close()


async def sync_all_active_shipments():
    """
    Fetch all active (undelivered) shipments across all tenants.
    Pull tracking for each and process events.
    """
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Find all orders with tracking that aren't delivered or returned
        active_shipping = (
            db.query(ShippingInfo)
            .join(ShopifyOrder, ShippingInfo.shopify_order_id == ShopifyOrder.id)
            .filter(
                ShippingInfo.is_delivered == False,
                ShippingInfo.tracking_status.notin_([
                    TrackingStatus.delivered,
                    TrackingStatus.returned,
                    TrackingStatus.cancelled,
                ])
            )
            .all()
        )

        logger.info(f"🔄 Syncing tracking for {len(active_shipping)} active shipments")

        for shipping_info in active_shipping:
            try:
                await process_single_shipment(db, shipping_info)
                # Small delay between API calls to avoid rate limiting
                await asyncio.sleep(0.5)
            except Exception as e:
                db.rollback()
                logger.error(f"Error processing shipment {shipping_info.tracking_number}: {e}")

    except Exception as e:
        db.rollback()
        logger.error(f"sync_tracking_for_all_orders error: {e}")
    finally:
        db.close()


async def process_single_shipment(db: Session, shipping_info: ShippingInfo):
    """
    Fetch and process tracking update for a single shipment.
    """
    order = db.query(ShopifyOrder).filter(
        ShopifyOrder.id == shipping_info.shopify_order_id
    ).first()
    if not order:
        return

    # Get delivery partner credentials
    partner = db.query(DeliveryPartner).filter(
        DeliveryPartner.tenant_id == order.tenant_id,
        DeliveryPartner.partner_type == (
            "delhivery" if shipping_info.shipping_partner == ShippingPartner.delhivery else "india_post"
        ),
        DeliveryPartner.is_active == True,
    ).first()

    if not partner:
        logger.warning(f"No active partner configured for {shipping_info.shipping_partner}")
        return

    # Decrypt API key (using existing credential service pattern)
    try:
        from app.modules.shipping_config.service import decrypt_credential
        api_key = decrypt_credential(partner.api_key)
    except Exception:
        api_key = partner.api_key  # fallback to plain text

    # Fetch tracking
    result = None
    try:
        if shipping_info.shipping_partner == ShippingPartner.delhivery:
            client = DelhiveryAPIClient(api_key=api_key, client_name=partner.client_name or "")
            result = await client.get_tracking_status(shipping_info.tracking_number)
        elif shipping_info.shipping_partner == ShippingPartner.india_post:
            cust_id = (partner.customer_ids[0]["id"] if partner.customer_ids else "") or ""
            use_sandbox = (partner.client_name or "sandbox") != "production"
            client = IndiaPostAPIClient(
                username=partner.client_id or "",
                password=api_key,
                customer_id=cust_id,
                sandbox=use_sandbox,
            )
            result = await client.track_article(shipping_info.tracking_number)
    except Exception as e:
        logger.error(f"API call failed for {shipping_info.tracking_number}: {e}")
        return

    if not result or not result.get("success"):
        return

    new_status_str = result.get("status", "in_transit")
    try:
        new_status = TrackingStatus(new_status_str)
    except ValueError:
        new_status = TrackingStatus.in_transit

    old_status = shipping_info.tracking_status
    status_changed = (old_status != new_status)

    # Update ShippingInfo
    shipping_info.tracking_status    = new_status
    shipping_info.last_tracking_update = datetime.now(timezone.utc)
    shipping_info.courier_api_response  = result.get("raw") or result.get("raw_data") or result

    if new_status == TrackingStatus.delivered:
        shipping_info.is_delivered = True
        shipping_info.delivered_at = datetime.now(timezone.utc)
        order.shopify_fulfillment_status = ShopifyFulfillmentStatus.delivered

    # Sync service to save tracking events
    sync_svc = ShopifyOrderSyncService(db)
    key_kwarg = {}
    if shipping_info.shipping_partner == ShippingPartner.delhivery:
        key_kwarg = {"delhivery_key": api_key}
    else:
        key_kwarg = {
            "ip_username": partner.client_id or "",
            "ip_password": api_key,
            "ip_customer_id": (partner.customer_ids[0]["id"] if partner.customer_ids else "") or "",
            "ip_sandbox": (partner.client_name or "sandbox") != "production",
        }
    await sync_svc.fetch_tracking_updates(order, **key_kwarg)

    db.commit()

    # ── Event-driven actions ───────────────────────────────────
    if status_changed:
        await handle_status_change(db, order, shipping_info, old_status, new_status)


async def handle_status_change(
    db: Session,
    order: ShopifyOrder,
    shipping_info: ShippingInfo,
    old_status: TrackingStatus,
    new_status: TrackingStatus,
):
    """React to significant tracking status changes."""
    notif = NotificationService(db, str(order.tenant_id))
    risk  = RiskEngine(db)
    phone = order.customer_phone or order.shipping_phone or ""

    # ── Out for delivery ───────────────────────────────────────
    if new_status == TrackingStatus.out_for_delivery:
        await notif.send_out_for_delivery(order, shipping_info.tracking_number)

    # ── Delivered ──────────────────────────────────────────────
    elif new_status == TrackingStatus.delivered:
        await notif.send_delivered(order)
        # Update customer score and RTO zone
        if phone:
            risk.update_customer_score(str(order.tenant_id), phone, "delivered")
        risk.update_rto_zone(
            str(order.tenant_id),
            order.shipping_zip or "",
            order.shipping_city or "",
            order.shipping_state or "",
            "delivered",
        )

    # ── RTO initiated / returned ───────────────────────────────
    elif new_status in (TrackingStatus.returned, TrackingStatus.failed):
        # Update customer score
        if phone:
            risk.update_customer_score(str(order.tenant_id), phone, "rto")
        risk.update_rto_zone(
            str(order.tenant_id),
            order.shipping_zip or "",
            order.shipping_city or "",
            order.shipping_state or "",
            "rto",
        )

        # Auto-blacklist if threshold exceeded
        if phone:
            risk.auto_blacklist_customer(
                str(order.tenant_id),
                phone,
                f"Auto-blacklisted: excessive RTOs"
            )

        # Notify admin
        rules = db.query(ShippingBusinessRules).filter(
            ShippingBusinessRules.tenant_id == order.tenant_id
        ).first()
        if rules and rules.admin_alert_on_rto and rules.admin_emails:
            admin_phones = _extract_admin_phones(rules)
            for admin_phone in admin_phones:
                await notif.send_rto_admin_alert(order, admin_phone)

    # ── NDR (Non-Delivery Report) ──────────────────────────────
    elif new_status == TrackingStatus.failed:
        await handle_ndr_event(db, order, shipping_info, notif, risk)


async def handle_ndr_event(
    db: Session,
    order: ShopifyOrder,
    shipping_info: ShippingInfo,
    notif: NotificationService,
    risk: RiskEngine,
):
    """
    Handle a Non-Delivery Report event.
    Creates NDR record, notifies customer, updates attempt count.
    """
    shipping_info.delivery_attempt_count = (shipping_info.delivery_attempt_count or 0) + 1

    # Create NDR record
    ndr = NdrRecord(
        tenant_id=order.tenant_id,
        shopify_order_id=order.id,
        tracking_number=shipping_info.tracking_number,
        courier_name=shipping_info.courier_name or "Courier",
        ndr_date=datetime.now(timezone.utc),
        reason=NdrReason.other,
        attempt_number=shipping_info.delivery_attempt_count,
        status=NdrStatus.pending,
        customer_phone=order.customer_phone or order.shipping_phone,
    )
    db.add(ndr)

    # Update customer score
    phone = order.customer_phone or order.shipping_phone or ""
    if phone:
        risk.update_customer_score(str(order.tenant_id), phone, "ndr")
    risk.update_rto_zone(
        str(order.tenant_id),
        order.shipping_zip or "",
        order.shipping_city or "",
        order.shipping_state or "",
        "ndr",
    )

    db.commit()

    # Notify customer
    await notif.send_ndr_customer_alert(
        order,
        ndr_reason="Delivery attempted but unsuccessful",
        attempt=shipping_info.delivery_attempt_count,
    )


def _extract_admin_phones(rules) -> List[str]:
    """Extract admin phone numbers from business rules."""
    if not rules or not rules.admin_emails:
        return []
    # admin_emails field is JSON — may contain phones too
    items = rules.admin_emails if isinstance(rules.admin_emails, list) else []
    phones = [i for i in items if i.startswith("+") or i.isdigit()]
    return phones


# ── Worker Lifecycle ───────────────────────────────────────────

def start_tracking_worker():
    """Start the background tracking sync worker."""
    global _worker_running, _worker_task

    if _worker_running:
        logger.warning("Tracking worker already running")
        return

    _worker_running = True

    loop = asyncio.get_event_loop()
    if loop.is_running():
        _worker_task = loop.create_task(run_tracking_sync())
    else:
        loop.run_until_complete(run_tracking_sync())

    logger.info("✅ Tracking sync worker started")


def stop_tracking_worker():
    """Stop the background tracking sync worker."""
    global _worker_running, _worker_task

    _worker_running = False
    if _worker_task and not _worker_task.done():
        _worker_task.cancel()
    logger.info("🛑 Tracking sync worker stopped")


async def trigger_manual_sync(tenant_id: str = None):
    """
    Manually trigger a tracking sync (e.g. from admin dashboard).
    Optional: filter by tenant_id.
    """
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        query = (
            db.query(ShippingInfo)
            .join(ShopifyOrder, ShippingInfo.shopify_order_id == ShopifyOrder.id)
            .filter(
                ShippingInfo.is_delivered == False,
                ShippingInfo.tracking_status.notin_([
                    TrackingStatus.delivered,
                    TrackingStatus.returned,
                    TrackingStatus.cancelled,
                ])
            )
        )
        if tenant_id:
            query = query.filter(ShopifyOrder.tenant_id == tenant_id)

        shipments = query.all()
        logger.info(f"Manual sync: {len(shipments)} shipments for tenant {tenant_id or 'ALL'}")

        for s in shipments:
            try:
                await process_single_shipment(db, s)
                await asyncio.sleep(0.3)
            except Exception as e:
                db.rollback()
                logger.error(f"Manual sync error for {s.tracking_number}: {e}")

        return len(shipments)
    except Exception as e:
        db.rollback()
        logger.error(f"trigger_tracking_sync error: {e}")
        return 0
    finally:
        db.close()
