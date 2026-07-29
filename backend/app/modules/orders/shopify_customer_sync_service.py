"""
Shopify Order to Customer Sync Service
Auto-creates and links Customer records when Shopify orders are fulfilled/tracked
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.customer import Customer, LeadStatus, CustomerType, PaymentMode, SourceType
from app.models.shopify_order import ShopifyOrder
from app.modules.customers.service import generate_customer_code

logger = logging.getLogger(__name__)


class ShopifyCustomerSyncService:
    """
    Manages customer creation and linking when Shopify orders get tracking numbers.
    
    Flow:
    1. When a Shopify order is synced with tracking_number, auto-create a Customer
    2. Link the order to the customer (customer_id)
    3. Update customer stats (first_order_date, total_orders, average_order_value)
    4. Maintain bi-directional sync between customer and order records
    """

    def __init__(self, db: Session):
        self.db = db

    def sync_order_to_customer(
        self,
        shopify_order: ShopifyOrder,
        created_by_employee_id: UUID,
    ) -> Optional[Customer]:
        """
        Auto-create/link customer when Shopify order has tracking number.
        
        Args:
            shopify_order: The ShopifyOrder record with tracking info
            created_by_employee_id: Employee creating the customer record
        
        Returns:
            Customer record (new or existing), or None if not eligible
        """
        # Only create customer if order has a tracking number (i.e., it's being shipped)
        if not shopify_order.tracking_number:
            logger.info(f"Order {shopify_order.shopify_order_name}: No tracking yet, skipping customer creation")
            return None

        # Check if customer already linked
        if shopify_order.customer_id:
            logger.info(f"Order {shopify_order.shopify_order_name}: Already linked to customer {shopify_order.customer_id}")
            return self.db.query(Customer).get(shopify_order.customer_id)

        # Try to find existing customer by phone
        existing_customer = self.db.query(Customer).filter(
            Customer.tenant_id == shopify_order.tenant_id,
            Customer.phone == (shopify_order.customer_phone or shopify_order.shipping_phone),
            Customer.is_active == True,
        ).first()

        if existing_customer:
            logger.info(f"Found existing customer {existing_customer.unique_customer_code} for order {shopify_order.shopify_order_name}")
            shopify_order.customer_id = existing_customer.id
            return existing_customer

        # Create new customer
        customer = self._create_customer_from_shopify_order(
            shopify_order=shopify_order,
            created_by_employee_id=created_by_employee_id,
        )

        logger.info(f"Created customer {customer.unique_customer_code} for Shopify order {shopify_order.shopify_order_name}")
        shopify_order.customer_id = customer.id
        return customer

    def _create_customer_from_shopify_order(
        self,
        shopify_order: ShopifyOrder,
        created_by_employee_id: UUID,
    ) -> Customer:
        """Create a Customer record from Shopify order data."""
        code = generate_customer_code(self.db, shopify_order.tenant_id)

        customer = Customer(
            tenant_id=shopify_order.tenant_id,
            unique_customer_code=code,
            name=shopify_order.customer_name or shopify_order.shipping_name,
            phone=shopify_order.customer_phone or shopify_order.shipping_phone,
            email=shopify_order.customer_email,
            address=f"{shopify_order.shipping_address_line1}, {shopify_order.shipping_address_line2 or ''}",
            pincode=shopify_order.shipping_zip,
            city=shopify_order.shipping_city,
            state=shopify_order.shipping_state,
            country=shopify_order.shipping_country or "India",
            customer_type=CustomerType.retail,  # Shopify customers are typically retail
            payment_mode_preference=self._infer_payment_mode(shopify_order),
            source=SourceType.website,  # Shopify is a web channel
            lead_status=LeadStatus.converted,  # They've already placed an order
            created_by_employee_id=created_by_employee_id,
            first_order_date=shopify_order.created_at_shopify,
            last_order_date=shopify_order.created_at_shopify,
            last_seen_at=datetime.now(timezone.utc),
            total_orders=1,
            average_order_value=shopify_order.total_price,
            notes=f"Auto-created from Shopify order {shopify_order.shopify_order_name}. Tracking: {shopify_order.tracking_number}",
        )

        self.db.add(customer)
        self.db.flush()
        return customer

    def update_customer_from_shopify_order(
        self,
        customer: Customer,
        shopify_order: ShopifyOrder,
    ) -> Customer:
        """
        Update customer stats when a Shopify order is synced/updated.
        Called after status changes or order updates.
        """
        # Update first order date
        if not customer.first_order_date or shopify_order.created_at_shopify < customer.first_order_date:
            customer.first_order_date = shopify_order.created_at_shopify

        # Update last order date
        if not customer.last_order_date or shopify_order.created_at_shopify > customer.last_order_date:
            customer.last_order_date = shopify_order.created_at_shopify

        # Update last seen
        customer.last_seen_at = datetime.now(timezone.utc)

        # Recalculate total orders and average order value
        self._recalculate_customer_stats(customer)

        return customer

    def _recalculate_customer_stats(self, customer: Customer) -> None:
        """Recalculate total_orders and average_order_value from linked orders."""
        from app.models.order import Order
        from sqlalchemy import func as sa_func

        # Count all orders (both Shopify and manual) linked to this customer
        total_shopify = self.db.query(ShopifyOrder).filter(
            ShopifyOrder.tenant_id == customer.tenant_id,
            ShopifyOrder.customer_id == customer.id,
        ).count()

        total_manual = self.db.query(Order).filter(
            Order.tenant_id == customer.tenant_id,
            Order.customer_id == customer.id,
        ).count()

        customer.total_orders = total_shopify + total_manual

        # Calculate average order value using proper SQL aggregation
        if customer.total_orders > 0:
            total_shopify_value = (
                self.db.query(sa_func.sum(ShopifyOrder.total_price))
                .filter(
                    ShopifyOrder.tenant_id == customer.tenant_id,
                    ShopifyOrder.customer_id == customer.id,
                )
                .scalar() or Decimal("0")
            )

            total_manual_value = (
                self.db.query(sa_func.sum(Order.total_amount))
                .filter(
                    Order.tenant_id == customer.tenant_id,
                    Order.customer_id == customer.id,
                )
                .scalar() or Decimal("0")
            )

            combined = Decimal(str(total_shopify_value)) + Decimal(str(total_manual_value))
            customer.average_order_value = (combined / customer.total_orders).quantize(Decimal("0.01"))

    def _infer_payment_mode(self, shopify_order: ShopifyOrder) -> Optional[PaymentMode]:
        """Infer payment mode from Shopify financial_status."""
        financial_status = (shopify_order.shopify_financial_status or "").lower()

        # COD = pending payment
        if "pending" in financial_status:
            return PaymentMode.cod

        # Pre-paid = prepaid
        if "paid" in financial_status or "authorized" in financial_status:
            return PaymentMode.prepaid

        return None
