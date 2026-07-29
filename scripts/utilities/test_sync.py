#!/usr/bin/env python3
"""Test script to check order fulfillment statuses in database"""
import sys
sys.path.insert(0, "/opt/miguel/backend")

from app.database.session import SessionLocal
from app.models.shopify_order import ShopifyOrder

session = SessionLocal()
orders = session.query(ShopifyOrder).order_by(ShopifyOrder.id.desc()).limit(15).all()

print("Order ID | Order Name | DB Fulfillment | Shopify Fulfillment | Has Fulfillments")
print("─" * 80)

for o in orders:
    db_status = o.shopify_fulfillment_status or "—"
    shopify_status = None
    fulfillment_count = 0
    
    if o.raw_shopify_data:
        shopify_status = o.raw_shopify_data.get("fulfillment_status")
        fulfillments = o.raw_shopify_data.get("fulfillments") or []
        fulfillment_count = len(fulfillments)
    
    shopify_str = str(shopify_status) if shopify_status else "None(unfulfilled)"
    print(f"{o.id:8d} | {o.shopify_order_name:10s} | {db_status:14s} | {shopify_str:19s} | {fulfillment_count}")

session.close()
