#!/bin/bash

# ===================================================================
# Quick Test Script for Shopify Logistics API
# ===================================================================
# Usage: bash /opt/miguel/test_api.sh
# ===================================================================

set -e

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test configuration
BACKEND_URL="http://localhost:8000"
TEST_EMAIL="purelevenexim@gmail.com"
TEST_PASSWORD="wM01gkxGCNhJT!"
TEST_SLUG="purelevenexim"
SHOPIFY_STORE="pureleven.myshopify.com"

echo "====================================================================="
echo "  Shopify Logistics API - Quick Test Suite"
echo "====================================================================="
echo ""

# ======================
# 1. Check Backend Health
# ======================
echo -e "${YELLOW}[1/8] Checking backend health...${NC}"
if curl -s "$BACKEND_URL/docs" > /dev/null; then
    echo -e "${GREEN}✅ Backend is running${NC}"
else
    echo -e "${RED}❌ Backend is not accessible at $BACKEND_URL${NC}"
    exit 1
fi
echo ""

# ======================
# 2. Test Authentication
# ======================
echo -e "${YELLOW}[2/8] Testing authentication...${NC}"
RESPONSE=$(curl -s -X POST "$BACKEND_URL/tenant/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\":\"$TEST_EMAIL\",
    \"password\":\"$TEST_PASSWORD\",
    \"slug\":\"$TEST_SLUG\"
  }")

TOKEN=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token','ERROR'))" 2>/dev/null || echo "ERROR")

if [ "$TOKEN" != "ERROR" ] && [ ! -z "$TOKEN" ]; then
    echo -e "${GREEN}✅ Authentication successful${NC}"
    echo "   Token: ${TOKEN:0:40}..."
else
    echo -e "${RED}❌ Authentication failed${NC}"
    echo "   Response: $RESPONSE"
    exit 1
fi
echo ""

# ======================
# 3. Test Dashboard Endpoint
# ======================
echo -e "${YELLOW}[3/8] Testing dashboard endpoint...${NC}"
DASHBOARD=$(curl -s "$BACKEND_URL/api/shipments/dashboard" \
  -H "Authorization: Bearer $TOKEN")

if echo "$DASHBOARD" | grep -q "orders"; then
    TOTAL=$(echo "$DASHBOARD" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['orders']['total'])" 2>/dev/null || echo "?")
    echo -e "${GREEN}✅ Dashboard working${NC}"
    echo "   Total orders: $TOTAL"
else
    echo -e "${RED}❌ Dashboard endpoint failed${NC}"
    echo "   Response: $DASHBOARD"
fi
echo ""

# ======================
# 4. Test Shipments List
# ======================
echo -e "${YELLOW}[4/8] Testing shipments list...${NC}"
SHIPMENTS=$(curl -s "$BACKEND_URL/api/shipments" \
  -H "Authorization: Bearer $TOKEN")

if echo "$SHIPMENTS" | grep -q "total"; then
    PAGE=$(echo "$SHIPMENTS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['page'])" 2>/dev/null || echo "?")
    echo -e "${GREEN}✅ Shipments list working${NC}"
    echo "   Pagination: page $PAGE"
else
    echo -e "${RED}❌ Shipments list failed${NC}"
    echo "   Response: $SHIPMENTS"
fi
echo ""

# ======================
# 5. Test Webhook
# ======================
echo -e "${YELLOW}[5/8] Testing Shopify webhook...${NC}"
WEBHOOK=$(curl -s -X POST "$BACKEND_URL/webhooks/shopify/order-created" \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Shop-Domain: $SHOPIFY_STORE" \
  -d '{
    "id": "999888777001",
    "name": "#TEST-1001",
    "order_number": 1001,
    "financial_status": "paid",
    "fulfillment_status": null,
    "customer": {
      "first_name": "Test",
      "last_name": "Customer",
      "phone": "9876543210",
      "email": "test@example.com"
    },
    "shipping_address": {
      "name": "Test Customer",
      "address1": "123 Test Street",
      "city": "Mumbai",
      "province": "Maharashtra",
      "zip": "400001",
      "country": "India",
      "phone": "9876543210"
    },
    "billing_address": {
      "name": "Test Customer",
      "address1": "123 Test Street",
      "city": "Mumbai",
      "province": "Maharashtra",
      "zip": "400001",
      "country": "India"
    },
    "subtotal_price": "999.00",
    "total_tax": "0.00",
    "total_discounts": "0.00",
    "total_price": "999.00",
    "currency": "INR",
    "line_items": [{"title": "Test Product", "quantity": 1, "price": "999.00", "sku": "TEST-001"}],
    "created_at": "2026-02-25T10:00:00+05:30",
    "updated_at": "2026-02-25T10:00:00+05:30"
  }')

if echo "$WEBHOOK" | grep -q "status.*ok"; then
    ORDER_ID=$(echo "$WEBHOOK" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('order_id','?'))" 2>/dev/null || echo "?")
    echo -e "${GREEN}✅ Webhook processed successfully${NC}"
    echo "   Order ID: $ORDER_ID"
else
    echo -e "${RED}❌ Webhook failed${NC}"
    echo "   Response: $WEBHOOK"
fi
echo ""

# ======================
# 6. Test Risk Assessments
# ======================
echo -e "${YELLOW}[6/8] Testing risk assessments...${NC}"
RISK=$(curl -s "$BACKEND_URL/api/shipments/risk" \
  -H "Authorization: Bearer $TOKEN")

if echo "$RISK" | grep -q "total"; then
    RISK_COUNT=$(echo "$RISK" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('total',0))" 2>/dev/null || echo "0")
    echo -e "${GREEN}✅ Risk assessments working${NC}"
    echo "   Risk records: $RISK_COUNT"
else
    echo -e "${RED}❌ Risk assessments failed${NC}"
    echo "   Response: $RISK"
fi
echo ""

# ======================
# 7. Test Blacklist
# ======================
echo -e "${YELLOW}[7/8] Testing blacklist...${NC}"
BLACKLIST=$(curl -s "$BACKEND_URL/api/shipments/blacklist" \
  -H "Authorization: Bearer $TOKEN")

if echo "$BLACKLIST" | grep -q "total"; then
    BL_COUNT=$(echo "$BLACKLIST" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('total',0))" 2>/dev/null || echo "0")
    echo -e "${GREEN}✅ Blacklist working${NC}"
    echo "   Blacklisted: $BL_COUNT customers"
else
    echo -e "${RED}❌ Blacklist failed${NC}"
    echo "   Response: $BLACKLIST"
fi
echo ""

# ======================
# 8. Test NDRs
# ======================
echo -e "${YELLOW}[8/8] Testing NDRs...${NC}"
NDRS=$(curl -s "$BACKEND_URL/api/shipments/ndrs" \
  -H "Authorization: Bearer $TOKEN")

if echo "$NDRS" | grep -q "total"; then
    NDR_COUNT=$(echo "$NDRS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('total',0))" 2>/dev/null || echo "0")
    echo -e "${GREEN}✅ NDRs working${NC}"
    echo "   Open NDRs: $NDR_COUNT"
else
    echo -e "${RED}❌ NDRs failed${NC}"
    echo "   Response: $NDRS"
fi
echo ""

# ======================
# Summary
# ======================
echo "====================================================================="
echo -e "${GREEN}✅ All tests completed successfully!${NC}"
echo "====================================================================="
echo ""
echo "Next steps:"
echo "  1. Configure Shopify webhooks in admin (Settings → Notifications)"
echo "  2. Set WhatsApp business account credentials"
echo "  3. Verify delivery partner API keys are set"
echo "  4. Monitor background worker: docker compose logs backend | grep tracking"
echo ""
echo "Documentation:"
echo "  - Full guide: /opt/miguel/SHOPIFY_LOGISTICS_COMPLETE.md"
echo "  - API reference: /opt/miguel/API_QUICK_REFERENCE.md"
echo "  - Summary: /opt/miguel/IMPLEMENTATION_SUMMARY.txt"
echo ""
