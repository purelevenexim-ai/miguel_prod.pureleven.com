"""
Customer-Order Auto-Sync Service
Runs every 10 minutes to keep customers and orders in sync:
  1. Links new Shopify orders to customers
  2. Updates customer stats (total_orders, average_order_value, last_seen_at)
  3. Syncs order status changes to customer engagement tracking
"""
import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session, sessionmaker

from app.database.session import engine
from app.models.customer import Customer
from app.models.shopify_order import ShopifyOrder
from app.models.order import Order
from app.modules.orders.shopify_customer_sync_service import ShopifyCustomerSyncService

logger = logging.getLogger(__name__)

_customer_sync_running = False
_customer_sync_task = None


async def run_customer_sync():
    """
    Background worker: sync customers and orders every 10 minutes.
    """
    global _customer_sync_running
    logger.info("👥 Customer-Order auto-sync worker started (10-min interval)")

    while _customer_sync_running:
        try:
            await sync_all_customers_with_orders()
        except Exception as e:
            logger.error(f"Customer sync cycle error: {e}")

        logger.info("⏰ Next customer sync in 10 minutes")
        await asyncio.sleep(10 * 60)

    logger.info("👥 Customer-Order auto-sync worker stopped")


async def sync_all_customers_with_orders():
    """
    Sync all customers and their linked orders.
    """
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        # Get all distinct tenants with active Shopify orders
        from app.models.shipping_config import ShopifyStore
        
        stores = db.query(ShopifyStore).filter(
            ShopifyStore.is_active == True,
        ).distinct(ShopifyStore.tenant_id).all()

        logger.info(f"👥 Syncing customers for {len(stores)} tenant(s)")

        for store in stores:
            try:
                await sync_customers_for_tenant(db, store.tenant_id)
            except Exception as e:
                db.rollback()
                logger.error(f"Error syncing customers for tenant {store.tenant_id}: {e}")

        logger.info("✅ Customer sync completed")
    except Exception as e:
        db.rollback()
        logger.error(f"sync_all_customers_with_orders error: {e}")
    finally:
        db.close()


async def sync_customers_for_tenant(db: Session, tenant_id):
    """
    For a specific tenant:
    1. Link unlinked Shopify orders with tracking to customers
    2. Update customer stats
    3. Mark sync timestamp
    """
    customer_sync = ShopifyCustomerSyncService(db)

    # Find ShopifyOrders with tracking but no customer_id
    unlinked_orders = db.query(ShopifyOrder).filter(
        ShopifyOrder.tenant_id == tenant_id,
        ShopifyOrder.tracking_number != None,
        ShopifyOrder.customer_id == None,
    ).all()

    linked_count = 0
    for order in unlinked_orders:
        try:
            # Get default employee (first admin)
            from app.models.employee import Employee, RoleEnum
            default_emp = db.query(Employee).filter(
                Employee.tenant_id == tenant_id,
                Employee.role == RoleEnum.admin
            ).order_by(Employee.created_at).first()

            if default_emp:
                customer = customer_sync.sync_order_to_customer(order, default_emp.id)
                if customer:
                    linked_count += 1
                    logger.info(f"Linked order {order.shopify_order_name} to customer {customer.unique_customer_code}")
        except Exception as e:
            logger.error(f"Error linking order {order.shopify_order_name}: {e}")

    if linked_count > 0:
        db.commit()
        logger.info(f"Linked {linked_count} orders to customers for tenant {tenant_id}")

    # Update stats for all active customers in this tenant
    customers = db.query(Customer).filter(
        Customer.tenant_id == tenant_id,
        Customer.is_active == True,
    ).all()

    updated_count = 0
    for customer in customers:
        try:
            customer_sync._recalculate_customer_stats(customer)
            updated_count += 1
        except Exception as e:
            logger.error(f"Error updating stats for customer {customer.unique_customer_code}: {e}")

    if updated_count > 0:
        db.commit()
        logger.info(f"Updated stats for {updated_count} customers in tenant {tenant_id}")


def start_customer_sync_worker():
    """Start the background customer-order sync worker."""
    global _customer_sync_running, _customer_sync_task

    if _customer_sync_running:
        logger.warning("Customer sync worker already running")
        return

    _customer_sync_running = True
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    _customer_sync_task = loop.create_task(run_customer_sync())
    logger.info("✅ Customer sync worker started")


def stop_customer_sync_worker():
    """Stop the background customer-order sync worker."""
    global _customer_sync_running

    _customer_sync_running = False
    logger.info("🛑 Customer sync worker stopping...")
