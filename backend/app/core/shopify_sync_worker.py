"""
Shopify Auto-Sync Service
Polls Shopify every 30 minutes for:
  1. New/updated orders  → saved to shopify_orders table
  2. Abandoned checkouts → saved as Leads (source=website, notes contain cart details)
Also detects new Delhivery shipments for orders and auto-links them.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.orm import Session, sessionmaker

from app.database.session import engine
from app.models.shopify_order import ShopifyOrder, ShippingPartner
from app.models.shipping_config import ShopifyStore, DeliveryPartner
from app.modules.orders.shopify_sync_service import ShopifyOrderSyncService

logger = logging.getLogger(__name__)

_shopify_sync_running = False
_shopify_sync_task    = None

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _decrypt(value: str) -> str:
    """Decrypt a credential — falls back to plain text."""
    try:
        from app.modules.shipping_config.service import decrypt_credential
        return decrypt_credential(value)
    except Exception:
        return value


# ─────────────────────────────────────────────────────────────
# Main sync loop
# ─────────────────────────────────────────────────────────────

async def run_shopify_sync():
    """
    Background worker: poll Shopify every 30 minutes.
    """
    global _shopify_sync_running
    logger.info("🛍️  Shopify auto-sync worker started (30-min interval)")

    while _shopify_sync_running:
        try:
            await sync_all_stores()
        except Exception as e:
            logger.error(f"Shopify sync cycle error: {e}")

        logger.info("⏰ Next Shopify sync in 30 minutes")
        await asyncio.sleep(30 * 60)

    logger.info("🛍️  Shopify auto-sync worker stopped")


async def sync_all_stores():
    """Sync all active Shopify stores for all tenants."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        stores = db.query(ShopifyStore).filter(
            ShopifyStore.is_active == True,
            ShopifyStore.api_access_token != None,
        ).all()

        logger.info(f"🛍️  Syncing {len(stores)} Shopify store(s)")

        for store in stores:
            try:
                await sync_single_store(db, store)
            except Exception as e:
                db.rollback()
                logger.error(f"Error syncing store {store.store_url}: {e}")
    except Exception as e:
        db.rollback()
        logger.error(f"sync_all_stores error: {e}")
    finally:
        db.close()


async def sync_single_store(db: Session, store: ShopifyStore):
    """
    Sync one Shopify store:
    - Fetch orders updated since last_sync (or past 30 days if never synced)
    - Fetch abandoned checkouts since last_sync
    - Auto-detect Delhivery shipments for unshipped orders
    """
    from app.core.shipping.shopify_api_client import ShopifyAPIClient

    # Decrypt token
    access_token = _decrypt(store.api_access_token)

    logger.info(f"🛍️  Syncing {store.store_url} | token={access_token[:12]}…")

    client = ShopifyAPIClient(
        store_url=store.store_url,
        access_token=access_token,
        api_version=store.api_version or "2024-01",
    )

    # Calculate since when to sync
    is_first_sync = store.last_sync is None
    since = store.last_sync or (datetime.now(timezone.utc) - timedelta(days=30))

    # ── 1. Sync orders ─────────────────────────────────────────
    if is_first_sync:
        # First ever sync: fetch only the most recent 5 orders
        orders_result = await client.get_last_n_orders(n=5)
    else:
        orders_result = await client.get_orders_since(since)
    if orders_result["success"]:
        sync_svc = ShopifyOrderSyncService(db)
        new_count = 0
        for order_data in orders_result["orders"]:
            result = sync_svc.process_order_webhook(store, order_data)
            if result["success"]:
                new_count += 1
        if new_count:
            logger.info(f"✅ {store.store_url}: synced {new_count} orders")

    # ── 2. Sync abandoned checkouts → leads ────────────────────
    checkouts_result = await client.get_abandoned_checkouts(
        limit=100,
        created_at_min=since,
    )
    if checkouts_result["success"]:
        lead_count = _process_abandoned_carts(db, store, checkouts_result["checkouts"])
        if lead_count:
            logger.info(f"🛒 {store.store_url}: created/updated {lead_count} leads from abandoned carts")

    # ── 3. Auto-detect Delhivery shipments ─────────────────────
    await _auto_detect_delhivery_shipments(db, store)

    # ── Update last_sync ───────────────────────────────────────
    store.last_sync = datetime.now(timezone.utc)
    db.commit()


def _process_abandoned_carts(db: Session, store: ShopifyStore, checkouts: list) -> int:
    """
    Convert Shopify abandoned checkouts to CRM Leads.
    Skips checkouts that already have a corresponding order (they converted).
    Returns the count of leads created.
    """
    from app.models.lead import Lead, LeadPipelineStatus, LeadSource, LeadPriority
    from sqlalchemy import func as sqlfunc

    count = 0
    for checkout in checkouts:
        shopify_checkout_id = str(checkout.get("id", ""))
        if not shopify_checkout_id:
            continue

        # Skip if checkout already converted to order
        if checkout.get("completed_at"):
            continue

        # Extract contact info
        phone = _extract_checkout_phone(checkout)
        email = (checkout.get("email") or "").strip()

        # Need at least phone or email
        if not phone and not email:
            continue

        # Skip if we already created a lead for this checkout ID (stored in notes)
        ref_tag = f"[shopify_checkout:{shopify_checkout_id}]"
        existing = db.query(Lead).filter(
            Lead.tenant_id == store.tenant_id,
            Lead.notes.contains(ref_tag),
        ).first()
        if existing:
            continue

        # Extract customer name
        customer = checkout.get("customer") or {}
        billing  = checkout.get("billing_address") or {}
        first_name = (customer.get("first_name") or billing.get("first_name") or "").strip()
        last_name  = (customer.get("last_name")  or billing.get("last_name")  or "").strip()
        name = f"{first_name} {last_name}".strip() or email or phone or "Shopify Lead"

        city  = (billing.get("city")     or "").strip() or None
        state = (billing.get("province") or "").strip() or None

        # Cart value
        try:
            total_value = float(checkout.get("total_price") or 0)
        except (ValueError, TypeError):
            total_value = 0.0

        # Products summary
        line_items = checkout.get("line_items") or []
        items_summary = ", ".join(
            f"{li.get('title', '')} x{li.get('quantity', 1)}"
            for li in line_items[:3]
        ) or "unknown"

        # Generate lead number
        lead_count = (
            db.query(sqlfunc.count(Lead.id))
            .filter(Lead.tenant_id == store.tenant_id)
            .scalar()
        ) or 0
        lead_number = f"LEAD-{str(lead_count + count + 1).zfill(5)}"

        new_lead = Lead(
            tenant_id=store.tenant_id,
            lead_number=lead_number,
            name=name,
            phone=phone or "unknown",   # phone is NOT NULL in schema
            email=email or None,
            city=city,
            state=state,
            source=LeadSource.shopify,
            status=LeadPipelineStatus.new_lead,
            priority=LeadPriority.medium,
            estimated_value=total_value if total_value > 0 else None,
            product_interest=items_summary,
            notes=(
                f"Shopify abandoned cart.\n"
                f"Items: {items_summary}\n"
                f"Cart value: ₹{total_value:,.0f}\n"
                f"{ref_tag}"
            ),
            created_by_id=None,   # system-created; will be set to first admin below
        )

        # Set created_by_id to any admin of the tenant (required FK)
        from app.models.employee import Employee, RoleEnum
        admin = db.query(Employee).filter(
            Employee.tenant_id == store.tenant_id,
            Employee.role == RoleEnum.admin,
            Employee.is_active == True,
        ).first()
        if admin:
            new_lead.created_by_id = admin.id
        else:
            # Skip if no admin found (can't satisfy FK)
            continue

        db.add(new_lead)
        count += 1

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving abandoned cart leads: {e}")

    return count


def _extract_checkout_phone(checkout: dict) -> str:
    """Extract best phone from a Shopify checkout."""
    phone = (
        checkout.get("phone")
        or (checkout.get("customer") or {}).get("phone")
        or (checkout.get("billing_address") or {}).get("phone")
        or (checkout.get("shipping_address") or {}).get("phone")
        or ""
    )
    return phone.strip()


async def _auto_detect_delhivery_shipments(db: Session, store: ShopifyStore):
    """
    For orders that have no courier set yet, check if Delhivery has a shipment
    by order reference and auto-link it.
    Only runs if a Delhivery partner is configured for the tenant.
    """
    from app.core.shipping.delhivery_client import DelhiveryAPIClient

    delhivery = db.query(DeliveryPartner).filter(
        DeliveryPartner.tenant_id == store.tenant_id,
        DeliveryPartner.partner_type == "delhivery",
        DeliveryPartner.is_active == True,
    ).first()

    if not delhivery:
        return

    # Find orders with no tracking number
    unshipped = db.query(ShopifyOrder).filter(
        ShopifyOrder.tenant_id == store.tenant_id,
        ShopifyOrder.shopify_store_id == store.id,
        ShopifyOrder.tracking_number == None,
        ShopifyOrder.shopify_order_id != None,
    ).limit(50).all()

    if not unshipped:
        return

    api_key = _decrypt(delhivery.api_key)
    client  = DelhiveryAPIClient(api_key=api_key, client_name=delhivery.client_name or "")

    for order in unshipped:
        try:
            # Query Delhivery by order reference ID
            result = await client.get_tracking_by_reference(order.shopify_order_id)
            if result.get("success") and result.get("waybill"):
                waybill = result["waybill"]
                order.shipping_partner = ShippingPartner.delhivery
                order.tracking_number  = waybill
                order.tracking_url     = f"https://track.delhivery.com/tracking/shipments/{waybill}"
                logger.info(f"Auto-linked Delhivery waybill {waybill} → {order.shopify_order_name}")
        except Exception as e:
            logger.debug(f"Delhivery lookup skipped for {order.shopify_order_name}: {e}")

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Auto-detect delhivery commit error: {e}")


# ─────────────────────────────────────────────────────────────
# Manual sync trigger
# ─────────────────────────────────────────────────────────────

async def trigger_shopify_sync(tenant_id: Optional[str] = None):
    """
    Manually trigger a full Shopify sync (called from API endpoint).
    """
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        query = db.query(ShopifyStore).filter(
            ShopifyStore.is_active == True,
            ShopifyStore.api_access_token != None,
        )
        if tenant_id:
            import uuid as _uuid
            query = query.filter(ShopifyStore.tenant_id == _uuid.UUID(tenant_id))

        stores = query.all()
        for store in stores:
            try:
                await sync_single_store(db, store)
            except Exception as e:
                db.rollback()
                logger.error(f"Manual sync error for {store.store_url}: {e}")

        return {"success": True, "stores_synced": len(stores)}
    except Exception as e:
        db.rollback()
        logger.error(f"trigger_shopify_sync error: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────
# Worker lifecycle
# ─────────────────────────────────────────────────────────────

def start_shopify_sync_worker():
    """Start the 30-min Shopify auto-sync background worker."""
    global _shopify_sync_running, _shopify_sync_task
    import sys

    if _shopify_sync_running:
        logger.warning("Shopify sync worker already running")
        return

    _shopify_sync_running = True

    # Create new event loop for the background task
    try:
        loop = asyncio.get_running_loop()
        # We're already in an async context (e.g., triggered by an endpoint)
        _shopify_sync_task = asyncio.ensure_future(run_shopify_sync())
        logger.info("✅ Shopify auto-sync worker started (30-min interval, async)")
    except RuntimeError:
        # No running loop - startup context
        # Use a thread with its own event loop
        import threading
        
        def _run_worker():
            try:
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                new_loop.run_until_complete(run_shopify_sync())
            except Exception as e:
                logger.error(f"Shopify sync worker thread error: {e}")
            finally:
                new_loop.close()
        
        thread = threading.Thread(daemon=True, target=_run_worker, name="shopify-sync-worker")
        thread.start()
        logger.info("✅ Shopify auto-sync worker started (30-min interval, thread mode)")




def stop_shopify_sync_worker():
    """Stop the Shopify auto-sync worker."""
    global _shopify_sync_running, _shopify_sync_task

    _shopify_sync_running = False
    if _shopify_sync_task and not _shopify_sync_task.done():
        _shopify_sync_task.cancel()
    logger.info("🛑 Shopify auto-sync worker stopped")
