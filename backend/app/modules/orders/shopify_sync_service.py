"""
Shopify Order Sync Service
Handles webhook processing and order synchronization
"""
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.shopify_order import (
    ShopifyOrder, ShippingInfo, TrackingEvent,
    ShopifyOrderStatus, ShopifyFulfillmentStatus, ShippingPartner, TrackingStatus
)
from app.models.shipping_config import ShopifyStore
from app.core.shipping.delhivery_client import DelhiveryAPIClient
from app.core.shipping.india_post_client import IndiaPostAPIClient
from app.modules.orders.shopify_customer_sync_service import ShopifyCustomerSyncService

logger = logging.getLogger(__name__)


class ShopifyOrderSyncService:
    """Syncs Shopify orders to local database"""

    def __init__(self, db: Session):
        self.db = db

    def process_order_webhook(
        self,
        shopify_store: ShopifyStore,
        webhook_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Process incoming Shopify order webhook
        Creates or updates ShopifyOrder record
        """
        try:
            shopify_order_id = str(webhook_data.get("id", ""))
            shopify_order_name = webhook_data.get("name", "")
            shopify_order_number = webhook_data.get("order_number", "")

            if not shopify_order_id:
                return {"success": False, "error": "Missing order ID"}

            # Check if order already exists
            existing = self.db.query(ShopifyOrder).filter(
                ShopifyOrder.shopify_store_id == shopify_store.id,
                ShopifyOrder.shopify_order_id == shopify_order_id,
            ).first()

            if existing:
                # Update existing order
                order = existing
            else:
                # Create new order
                order = ShopifyOrder(
                    tenant_id=shopify_store.tenant_id,
                    shopify_store_id=shopify_store.id,
                )

            # ── Basic info ─────────────────────────────────────
            order.shopify_order_id = shopify_order_id
            order.shopify_order_name = shopify_order_name
            order.shopify_order_number = shopify_order_number
            order.raw_shopify_data = webhook_data

            # ── Status ─────────────────────────────────────────
            order.shopify_status = self._map_order_status(webhook_data.get("financial_status"))
            order.shopify_fulfillment_status = self._map_fulfillment_status(
                webhook_data.get("fulfillment_status")
            )
            order.shopify_financial_status = webhook_data.get("financial_status", "pending")

            # ── Customer ───────────────────────────────────────
            customer = webhook_data.get("customer", {})
            order.customer_name = customer.get("first_name", "") + " " + customer.get("last_name", "")
            order.customer_email = customer.get("email", "")
            order.customer_phone = customer.get("phone", "")

            # ── Billing Address ────────────────────────────────
            billing = webhook_data.get("billing_address", {})
            if billing:
                order.billing_name = billing.get("name", "")
                order.billing_address_line1 = billing.get("address1", "")
                order.billing_address_line2 = billing.get("address2", "")
                order.billing_city = billing.get("city", "")
                order.billing_state = billing.get("province", "")
                order.billing_zip = billing.get("zip", "")
                order.billing_country = billing.get("country", "")

            # ── Shipping Address ───────────────────────────────
            shipping = webhook_data.get("shipping_address", {})
            if shipping:
                order.shipping_name = shipping.get("name", "")
                order.shipping_address_line1 = shipping.get("address1", "")
                order.shipping_address_line2 = shipping.get("address2", "")
                order.shipping_city = shipping.get("city", "")
                order.shipping_state = shipping.get("province", "")
                order.shipping_zip = shipping.get("zip", "")
                order.shipping_country = shipping.get("country", "")
                order.shipping_phone = shipping.get("phone", "")

            # ── Amounts ────────────────────────────────────────
            order.currency = webhook_data.get("currency", "INR")
            order.subtotal = Decimal(webhook_data.get("subtotal_price", 0))
            order.taxes = Decimal(webhook_data.get("total_tax", 0))
            order.discounts = Decimal(webhook_data.get("total_discounts", 0))
            order.shipping_cost = self._extract_shipping_cost(webhook_data)
            order.total_price = Decimal(webhook_data.get("total_price", 0))

            # ── Items ──────────────────────────────────────────
            line_items = webhook_data.get("line_items", [])
            order.line_items_count = len(line_items)
            order.line_items_json = line_items

            # ── Fulfillments → Courier + Tracking ──────────────
            # Shopify stores courier/tracking inside fulfillments[]
            fulfillments = webhook_data.get("fulfillments") or []
            if fulfillments:
                # Use the first (or most recent) fulfillment with a tracking number
                tracking_ful = next(
                    (f for f in fulfillments if f.get("tracking_number")),
                    fulfillments[0]  # fallback: first fulfillment even without tracking
                )
                raw_tracking   = tracking_ful.get("tracking_number") or ""
                raw_company    = (tracking_ful.get("tracking_company") or "").strip()
                raw_ship_status = tracking_ful.get("shipment_status") or ""

                # Only set if not already manually assigned
                if raw_tracking and not order.tracking_number:
                    order.tracking_number = raw_tracking
                    urls = tracking_ful.get("tracking_urls") or []
                    if not order.tracking_url and urls:
                        order.tracking_url = urls[0]

                if raw_company and not order.shipping_partner:
                    co_lower = raw_company.lower()
                    if "delhivery" in co_lower:
                        order.shipping_partner = "delhivery"
                    elif "india post" in co_lower or "indiapost" in co_lower or "speed post" in co_lower:
                        order.shipping_partner = "india_post"
                    elif "bluedart" in co_lower or "blue dart" in co_lower:
                        order.shipping_partner = "bluedart"
                    else:
                        order.shipping_partner = "manual"

                # Map Shopify shipment_status to fulfillment status
                if raw_ship_status and raw_ship_status != "null":
                    ship_status_map = {
                        "delivered":        "delivered",
                        "out_for_delivery": "out_for_delivery",
                        "in_transit":       "in_transit",
                        "attempted_delivery": "in_transit",
                        "ready_for_pickup": "in_transit",
                        "confirmed":        "unfulfilled",
                        "failure":          "failure",
                    }
                    mapped = ship_status_map.get(raw_ship_status, raw_ship_status)
                    order.shopify_fulfillment_status = mapped

            # ── Timeline ───────────────────────────────────────
            order.created_at_shopify = self._parse_shopify_datetime(webhook_data.get("created_at"))
            order.updated_at_shopify = self._parse_shopify_datetime(webhook_data.get("updated_at"))

            # ── Timestamps ─────────────────────────────────────
            order.synced_at = datetime.now(timezone.utc)

            self.db.add(order)
            self.db.flush()

            # ── Auto-create customer when order has tracking ────
            # When a Shopify order gets a tracking number, auto-create a Customer
            if order.tracking_number:
                customer_sync = ShopifyCustomerSyncService(self.db)
                # Get a default employee ID (use tenant's first admin)
                from app.models.employee import Employee, RoleEnum
                default_emp = self.db.query(Employee).filter(
                    Employee.tenant_id == shopify_store.tenant_id,
                    Employee.role == RoleEnum.admin
                ).first()
                if default_emp:
                    customer = customer_sync.sync_order_to_customer(order, default_emp.id)
                    if customer:
                        logger.info(f"Created/linked customer {customer.unique_customer_code} for order {order.shopify_order_name}")
                else:
                    logger.warning(f"No admin employee found for tenant {shopify_store.tenant_id}, skipping customer sync")

            self.db.commit()

            return {
                "success": True,
                "order_id": str(order.id),
                "shopify_order_id": shopify_order_id,
                "message": "Order synced successfully",
            }

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Integrity error syncing order: {str(e)}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error syncing Shopify order: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def _map_order_status(financial_status: Optional[str]) -> ShopifyOrderStatus:
        """Map Shopify financial_status to OrderStatus"""
        status_map = {
            "authorized": ShopifyOrderStatus.confirmed,
            "pending": ShopifyOrderStatus.awaiting_shipment,
            "paid": ShopifyOrderStatus.awaiting_shipment,
            "refunded": ShopifyOrderStatus.returned,
            "voided": ShopifyOrderStatus.cancelled,
            "partially_refunded": ShopifyOrderStatus.partially_fulfilled,
        }
        return status_map.get(financial_status, ShopifyOrderStatus.unconfirmed)

    @staticmethod
    def _map_fulfillment_status(fulfillment_status: Optional[str]) -> ShopifyFulfillmentStatus:
        """
        Map Shopify fulfillment_status from order level.
        Shopify order.fulfillment_status can be: null/"" (unfulfilled), "fulfilled", or "partial"
        Note: Fulfillment shipment_status (in fulfillments[] array) tracks shipment lifecycle
        """
        if fulfillment_status is None or fulfillment_status == "":
            return ShopifyFulfillmentStatus.unfulfilled
        
        # Map Shopify's order-level fulfillment_status
        status_map = {
            "fulfilled":  ShopifyFulfillmentStatus.fulfilled,
            "partial":    ShopifyFulfillmentStatus.partial,
            "unconfirmed": ShopifyFulfillmentStatus.unfulfilled,  # Legacy fallback
        }
        return status_map.get(fulfillment_status, ShopifyFulfillmentStatus.unfulfilled)

    @staticmethod
    def _extract_shipping_cost(webhook_data: Dict) -> Decimal:
        """Extract shipping cost from Shopify order"""
        shipping_lines = webhook_data.get("shipping_lines", [])
        total = Decimal(0)
        for line in shipping_lines:
            total += Decimal(line.get("price", 0))
        return total

    @staticmethod
    def _parse_shopify_datetime(dt_str: Optional[str]) -> datetime:
        """Parse Shopify ISO datetime"""
        if not dt_str:
            return datetime.now(timezone.utc)
        try:
            # Shopify returns: "2024-02-25T10:30:45-05:00"
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except:
            return datetime.now(timezone.utc)

    async def sync_tracking_with_delhivery(
        self,
        shopify_order: ShopifyOrder,
        delhivery_key: str,
        delhivery_client_name: str,
    ) -> Dict[str, Any]:
        """
        Create Delhivery waybill and update shipping info
        """
        try:
            client = DelhiveryAPIClient(
                api_key=delhivery_key,
                client_name=delhivery_client_name,
            )

            # Create waybill
            result = await client.create_waybill(
                order_id=shopify_order.shopify_order_number,
                customer_name=shopify_order.shipping_name,
                customer_phone=shopify_order.shipping_phone or "",
                customer_email=shopify_order.customer_email or "",
                shipping_address=shopify_order.shipping_address_line1,
                city=shopify_order.shipping_city,
                state=shopify_order.shipping_state,
                pincode=shopify_order.shipping_zip,
                weight_kg=1.0,  # Default, should be calculated from items
                amount=shopify_order.total_price,
                reference_id=shopify_order.shopify_order_id,
            )

            if result["success"]:
                waybill = result["tracking_number"]

                # Update ShopifyOrder
                shopify_order.shipping_partner = ShippingPartner.delhivery
                shopify_order.tracking_number = waybill
                shopify_order.tracking_url = f"https://track.delhivery.com/tracking/shipments/{waybill}"

                # Create ShippingInfo
                shipping_info = ShippingInfo(
                    tenant_id=shopify_order.tenant_id,
                    shopify_order_id=shopify_order.id,
                    shipping_partner=ShippingPartner.delhivery,
                    courier_name="Delhivery",
                    courier_code="DHL",
                    tracking_number=waybill,
                    tracking_url=shopify_order.tracking_url,
                    tracking_status=TrackingStatus.pending,
                    courier_api_response={"waybill": waybill},
                )

                self.db.add(shipping_info)
                self.db.commit()

                return {
                    "success": True,
                    "tracking_number": waybill,
                    "message": "Delhivery waybill created",
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Failed to create waybill"),
                }

        except Exception as e:
            logger.error(f"Delhivery sync error: {str(e)}")
            return {"success": False, "error": str(e)}

    async def sync_tracking_with_india_post(
        self,
        shopify_order: ShopifyOrder,
        ip_api_key: str,
        ip_client_id: str,
        ip_customer_id: str,
    ) -> Dict[str, Any]:
        """
        Create India Post Speed Post and update shipping info
        """
        try:
            client = IndiaPostAPIClient(
                username=ip_client_id,
                password=ip_api_key,
                customer_id=ip_customer_id,
            )

            # Book Speed Post
            result = await client.book_speed_post(
                shipper_name="Your Store",
                shipper_address="Store Address",
                shipper_phone="Store Phone",
                receiver_name=shopify_order.shipping_name,
                receiver_address=shopify_order.shipping_address_line1,
                receiver_phone=shopify_order.shipping_phone or "",
                receiver_city=shopify_order.shipping_city,
                receiver_state=shopify_order.shipping_state,
                receiver_pincode=shopify_order.shipping_zip,
                weight_grams=500,
                amount=shopify_order.total_price,
            )

            if result["success"]:
                article_number = result["tracking_number"]

                # Update ShopifyOrder
                shopify_order.shipping_partner = ShippingPartner.india_post
                shopify_order.tracking_number = article_number
                shopify_order.tracking_url = f"https://tracking.indiapost.gov.in/status/{article_number}"

                # Create ShippingInfo
                shipping_info = ShippingInfo(
                    tenant_id=shopify_order.tenant_id,
                    shopify_order_id=shopify_order.id,
                    shipping_partner=ShippingPartner.india_post,
                    courier_name="India Post",
                    courier_code="INDIAPOST",
                    tracking_number=article_number,
                    tracking_url=shopify_order.tracking_url,
                    tracking_status=TrackingStatus.pending,
                    courier_api_response={"article_number": article_number},
                )

                self.db.add(shipping_info)
                self.db.commit()

                return {
                    "success": True,
                    "tracking_number": article_number,
                    "message": "India Post Speed Post booked",
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Failed to book Speed Post"),
                }

        except Exception as e:
            logger.error(f"India Post sync error: {str(e)}")
            return {"success": False, "error": str(e)}

    async def fetch_tracking_updates(
        self,
        shopify_order: ShopifyOrder,
        delhivery_key: Optional[str] = None,
        ip_api_key: Optional[str] = None,
        ip_username: Optional[str] = None,
        ip_password: Optional[str] = None,
        ip_customer_id: Optional[str] = None,
        ip_sandbox: bool = True,
    ) -> Dict[str, Any]:
        """
        Fetch latest tracking updates from courier
        """
        if not shopify_order.shipping_partner or not shopify_order.tracking_number:
            return {"success": False, "error": "No shipping info"}

        try:
            if shopify_order.shipping_partner == ShippingPartner.delhivery and delhivery_key:
                client = DelhiveryAPIClient(
                    api_key=delhivery_key,
                    client_name="",
                )
                result = await client.get_tracking_status(shopify_order.tracking_number)
            elif shopify_order.shipping_partner == ShippingPartner.india_post and (ip_password or ip_api_key):
                client = IndiaPostAPIClient(
                    username=ip_username or "",
                    password=ip_password or ip_api_key or "",
                    customer_id=ip_customer_id or "",
                    sandbox=ip_sandbox,
                )
                result = await client.track_article(shopify_order.tracking_number)
            else:
                return {"success": False, "error": "Unsupported courier"}

            if result["success"]:
                # Update shipping info
                shipping_info = shopify_order.shipping_info
                if shipping_info:
                    try:
                        shipping_info.tracking_status = TrackingStatus(result.get("status", "in_transit"))
                    except ValueError:
                        shipping_info.tracking_status = TrackingStatus.in_transit
                    shipping_info.last_tracking_update = datetime.now(timezone.utc)
                    shipping_info.courier_api_response = result.get("raw") or result.get("raw_data") or result

                    # Create tracking events
                    for event in result.get("events", []):
                        try:
                            event_status = TrackingStatus(event.get("status", "in_transit"))
                        except ValueError:
                            event_status = TrackingStatus.in_transit
                        tracking_event = TrackingEvent(
                            tenant_id=shopify_order.tenant_id,
                            shopify_order_id=shopify_order.id,
                            event_status=event_status,
                            event_time=self._parse_shopify_datetime(event.get("time")),
                            location=event.get("location", ""),
                            description=event.get("description", ""),
                            raw_tracking_data=event,
                        )
                        self.db.add(tracking_event)

                    self.db.commit()

                return {
                    "success": True,
                    "status": result.get("status", "in_transit"),
                    "events": result.get("events", []),
                }
            else:
                return {"success": False, "error": result.get("error")}

        except Exception as e:
            logger.error(f"Tracking fetch error: {str(e)}")
            return {"success": False, "error": str(e)}
