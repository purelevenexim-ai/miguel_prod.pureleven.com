#!/bin/bash

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

HOST="http://localhost:8000"
TOKEN=$(cat .env.test 2>/dev/null | grep ADMIN_TOKEN | cut -d= -f2 | tr -d '\"')

if [ -z "$TOKEN" ]; then
    echo -e "${YELLOW}⚠️ No token found. Using hardcoded test token.${NC}"
    TOKEN="test-token-admin"
fi

echo -e "${YELLOW}🔍 Testing Status Auto-Transition on Tracking Update${NC}"
echo "TOKEN: $TOKEN"
echo "HOST: $HOST"

# Step 1: Create a test customer
echo -e "\n${YELLOW}Step 1: Create test customer${NC}"
CUST=$(curl -s -X POST $HOST/api/customers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name":"Test Customer '$(date +%s)'",
    "phone":"9876543210",
    "email":"test@example.com",
    "address":"Test Address"
  }')

CUST_ID=$(echo $CUST | grep -o '"id":"[^"]*' | cut -d'"' -f4 | head -1)
echo "Customer created: $CUST_ID"
if [ -z "$CUST_ID" ]; then
    echo -e "${RED}✗ Failed to create customer${NC}"
    echo "Response: $CUST"
    exit 1
fi

# Step 2: Create an order in confirmed status
echo -e "\n${YELLOW}Step 2: Create order (should be confirmed)${NC}"
ORDER=$(curl -s -X POST $HOST/api/orders \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id":"'$CUST_ID'",
    "items":[{"product_name":"Test Item","quantity":1,"unit_price":100}],
    "delivery_address":"Test Address",
    "delivery_state":"Test State",
    "delivery_pincode":"123456"
  }')

ORDER_ID=$(echo $ORDER | grep -o '"id":"[^"]*' | cut -d'"' -f4 | head -1)
echo "Order created: $ORDER_ID"

# Check initial status
INITIAL_STATUS=$(echo $ORDER | grep -o '"status":"[^"]*' | cut -d'"' -f4 | head -1)
echo "Initial status: $INITIAL_STATUS"

if [ "$INITIAL_STATUS" != "confirmed" ]; then
    echo -e "${RED}✗ Expected confirmed, got $INITIAL_STATUS${NC}"
fi

# Step 3: Update tracking number
echo -e "\n${YELLOW}Step 3: Update tracking number (should auto-transition to shipped)${NC}"
TRACKING_UPDATE=$(curl -s -X PATCH $HOST/api/orders/$ORDER_ID/tracking \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tracking_number":"TEST123456789"
  }')

echo "Update response:"
echo $TRACKING_UPDATE | jq . 2>/dev/null || echo $TRACKING_UPDATE

# Check status after update
NEW_STATUS=$(echo $TRACKING_UPDATE | grep -o '"status":"[^"]*' | cut -d'"' -f4 | head -1)
TRACKING=$(echo $TRACKING_UPDATE | grep -o '"tracking_number":"[^"]*' | cut -d'"' -f4 | head -1)

echo "New status: $NEW_STATUS"
echo "Tracking number: $TRACKING"

if [ "$NEW_STATUS" = "shipped" ]; then
    echo -e "${GREEN}✓ Status correctly transitioned to shipped${NC}"
else
    echo -e "${RED}✗ Status NOT transitioned. Expected shipped, got $NEW_STATUS${NC}"
fi

if [ "$TRACKING" = "TEST123456789" ]; then
    echo -e "${GREEN}✓ Tracking number correctly set${NC}"
else
    echo -e "${RED}✗ Tracking number not set correctly${NC}"
fi

# Step 4: Get status history
echo -e "\n${YELLOW}Step 4: Check status history${NC}"
HISTORY=$(curl -s -X GET "$HOST/api/orders/$ORDER_ID/status-history" \
  -H "Authorization: Bearer $TOKEN")
echo "Status history:"
echo $HISTORY | jq . 2>/dev/null || echo $HISTORY

