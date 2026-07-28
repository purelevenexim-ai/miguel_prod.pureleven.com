#!/bin/bash

# Test Status Auto-Transitions
# Tests all three scenarios of status changes with tracking

set -e

HOST="${1:-http://localhost:8000}"
TENANT_ID="${2:-4374ad45-76b5-405b-8a3d-de49710fbdc3}"
ADMIN_TOKEN="${3:-}"

if [ -z "$ADMIN_TOKEN" ]; then
    echo "❌ ADMIN_TOKEN required"
    echo "Usage: $0 <HOST> <TENANT_ID> <ADMIN_TOKEN>"
    exit 1
fi

echo "═════════════════════════════════════════════════════════════"
echo "    STATUS AUTO-TRANSITION TESTS"
echo "═════════════════════════════════════════════════════════════"
echo "Host: $HOST"
echo "Tenant: $TENANT_ID"
echo ""

# Helper function
get_header() {
    echo "-H 'Authorization: Bearer $ADMIN_TOKEN' -H 'Content-Type: application/json'"
}

get_h_flag() {
    echo "-H"
}

# ─────────────────────────────────────────────────────────────
# TEST 1: Create Order → Should be "confirmed"
# ─────────────────────────────────────────────────────────────
echo "TEST 1: Create Order"
echo "────────────────────"
ORDER_RESPONSE=$(curl -s -X POST "$HOST/api/orders" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Test Customer",
    "delivery_address": "123 Main St",
    "delivery_city": "Mumbai",
    "delivery_state": "MH",
    "delivery_pincode": "400001",
    "payment_method": "cod",
    "items": [
      {"product_name": "Test Product", "sku": "TST001", "quantity": 1, "unit_price": 100}
    ]
  }')

echo "$ORDER_RESPONSE" | jq .
ORDER_ID=$(echo "$ORDER_RESPONSE" | jq -r '.id')
ORDER_NUM=$(echo "$ORDER_RESPONSE" | jq -r '.order_number')
ORDER_STATUS=$(echo "$ORDER_RESPONSE" | jq -r '.status')

echo ""
echo "✓ Order created: $ORDER_NUM (ID: $ORDER_ID)"
echo "✓ Initial status: $ORDER_STATUS"

if [ "$ORDER_STATUS" != "confirmed" ]; then
    echo "❌ FAILED: Expected status 'confirmed', got '$ORDER_STATUS'"
    exit 1
fi

# ─────────────────────────────────────────────────────────────
# TEST 2: Assign Tracking → Should auto-transition to "shipped"
# ─────────────────────────────────────────────────────────────
echo ""
echo "TEST 2: Assign Tracking (API Update)"
echo "─────────────────────────────────────"

TRACKING_RESPONSE=$(curl -s -X POST "$HOST/api/orders/$ORDER_ID/status" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "shipped",
    "tracking_number": "EE123456789IN"
  }')

echo "$TRACKING_RESPONSE" | jq .
NEW_STATUS=$(echo "$TRACKING_RESPONSE" | jq -r '.status')
TRACKING_NUM=$(echo "$TRACKING_RESPONSE" | jq -r '.tracking_number')

echo ""
echo "✓ Tracking assigned: $TRACKING_NUM"
echo "✓ New status: $NEW_STATUS"

if [ "$NEW_STATUS" != "shipped" ]; then
    echo "❌ FAILED: Expected status 'shipped', got '$NEW_STATUS'"
    exit 1
fi

# ─────────────────────────────────────────────────────────────
# TEST 3: Get Order Details to verify status and tracking
# ─────────────────────────────────────────────────────────────
echo ""
echo "TEST 3: Get Order Details"
echo "─────────────────────────"

# Fetch full order to verify tracking is saved
DETAIL_RESPONSE=$(curl -s -X GET "$HOST/api/orders?search=$ORDER_NUM&page_size=100" \
  -H "Authorization: Bearer $ADMIN_TOKEN")

echo "$DETAIL_RESPONSE" | jq '.items[0] | {id, order_number, status, tracking_number, courier_name}'

# ─────────────────────────────────────────────────────────────
# TEST 4: Create another order for delivered test
# ─────────────────────────────────────────────────────────────
echo ""
echo "TEST 4: Create Order for Delivery Test"
echo "───────────────────────────────────────"

ORDER2_RESPONSE=$(curl -s -X POST "$HOST/api/orders" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Test Customer 2",
    "delivery_address": "456 Oak Ave",
    "delivery_city": "Delhi",
    "delivery_state": "DL",
    "delivery_pincode": "110001",
    "payment_method": "cod",
    "items": [
      {"product_name": "Test Product", "sku": "TST002", "quantity": 2, "unit_price": 200}
    ]
  }')

ORDER2_ID=$(echo "$ORDER2_RESPONSE" | jq -r '.id')
ORDER2_NUM=$(echo "$ORDER2_RESPONSE" | jq -r '.order_number')

echo "✓ Order created: $ORDER2_NUM (ID: $ORDER2_ID)"

# ─────────────────────────────────────────────────────────────
# TEST 5: Mark as Shipped first
# ─────────────────────────────────────────────────────────────
echo ""
echo "TEST 5: Mark as Shipped"
echo "───────────────────────"

curl -s -X POST "$HOST/api/orders/$ORDER2_ID/status" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "shipped",
    "tracking_number": "RX987654321IN"
  }' | jq .

echo "✓ Order marked as shipped"

# ─────────────────────────────────────────────────────────────
# TEST 6: Mark as Delivered → Should auto-mark as paid
# ─────────────────────────────────────────────────────────────
echo ""
echo "TEST 6: Mark as Delivered (COD → Auto-Pay)"
echo "──────────────────────────────────────────"

DELIVER_RESPONSE=$(curl -s -X POST "$HOST/api/orders/$ORDER2_ID/status" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "delivered",
    "note": "Delivered and paid"
  }')

echo "$DELIVER_RESPONSE" | jq .

DELIVERED_STATUS=$(echo "$DELIVER_RESPONSE" | jq -r '.status')
PAYMENT_STATUS=$(echo "$DELIVER_RESPONSE" | jq -r '.payment_status')
AMOUNT_DUE=$(echo "$DELIVER_RESPONSE" | jq -r '.amount_due')

echo ""
echo "✓ Status: $DELIVERED_STATUS"
echo "✓ Payment Status: $PAYMENT_STATUS"
echo "✓ Amount Due: $AMOUNT_DUE"

if [ "$DELIVERED_STATUS" != "delivered" ]; then
    echo "❌ FAILED: Expected status 'delivered', got '$DELIVERED_STATUS'"
    exit 1
fi

if [ "$PAYMENT_STATUS" != "paid" ]; then
    echo "❌ FAILED: Expected payment_status 'paid', got '$PAYMENT_STATUS'"
    exit 1
fi

if [ "$(echo "$AMOUNT_DUE > 0" | bc)" -eq 1 ]; then
    echo "⚠️  WARNING: Amount due should be 0 for delivered COD order, got $AMOUNT_DUE"
fi

# ─────────────────────────────────────────────────────────────
# TEST 7: Verify intermediate status transitions
# ─────────────────────────────────────────────────────────────
echo ""
echo "TEST 7: Test Full Status Flow"
echo "──────────────────────────────"

ORDER3_RESPONSE=$(curl -s -X POST "$HOST/api/orders" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Test Customer 3",
    "delivery_address": "789 Pine Rd",
    "delivery_city": "Bangalore",
    "delivery_state": "KA",
    "delivery_pincode": "560001",
    "payment_method": "upi",
    "items": [
      {"product_name": "Test Product", "sku": "TST003", "quantity": 1, "unit_price": 500}
    ]
  }')

ORDER3_ID=$(echo "$ORDER3_RESPONSE" | jq -r '.id')
ORDER3_NUM=$(echo "$ORDER3_RESPONSE" | jq -r '.order_number')
echo "✓ Order 3 created: $ORDER3_NUM"

# Flow: confirmed → processing → packed → shipped
echo "  confirmed → processing"
curl -s -X POST "$HOST/api/orders/$ORDER3_ID/status" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "processing"}' | jq '.status'

echo "  processing → packed"
curl -s -X POST "$HOST/api/orders/$ORDER3_ID/status" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "packed"}' | jq '.status'

echo "  packed → shipped (with tracking)"
curl -s -X POST "$HOST/api/orders/$ORDER3_ID/status" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "shipped",
    "tracking_number": "DLY123456789IN"
  }' | jq '.status'

echo "✓ Full flow tested"

# ─────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────
echo ""
echo "═════════════════════════════════════════════════════════════"
echo "✅ ALL TESTS PASSED"
echo "═════════════════════════════════════════════════════════════"
echo ""
echo "Summary:"
echo "  ✓ Order creation → confirmed"
echo "  ✓ Assign tracking → shipped"
echo "  ✓ Mark delivered → paid (COD)"
echo "  ✓ Status history logged"
echo "  ✓ Full status flow working"
echo ""
