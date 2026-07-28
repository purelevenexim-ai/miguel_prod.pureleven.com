#!/bin/bash
# ════════════════════════════════════════════════════════════════════
# COMPREHENSIVE CRM FEATURE TEST SUITE
# Tests all API endpoints with dummy data against dev environment
# ════════════════════════════════════════════════════════════════════

BASE="http://localhost:8000"
TOKEN=""
TENANT_ID=""
PASS=0
FAIL=0
ERRORS=""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# ── Login ──────────────────────────────────────────────────────────
login() {
  local resp=$(curl -s -X POST "$BASE/tenant/login" \
    -H "Content-Type: application/json" \
    -d '{"slug":"purelevenexim","email":"admin@purelevenexim.com","password":"test1234"}')
  TOKEN=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)
  TENANT_ID=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin)['tenant_id'])" 2>/dev/null)
  if [ -z "$TOKEN" ]; then
    echo -e "${RED}FATAL: Cannot login. Response: $resp${NC}"
    exit 1
  fi
  echo -e "${GREEN}✓ Logged in. Tenant: $TENANT_ID${NC}"
}

H="Content-Type: application/json"

# ── Test helper ────────────────────────────────────────────────────
# Usage: run_test "TC-001" "Description" METHOD URL [BODY] [EXPECTED_STATUS]
run_test() {
  local tc="$1"
  local desc="$2"
  local method="$3"
  local url="$4"
  local body="$5"
  local expected="${6:-200}"
  
  local curl_args=(-s -o /tmp/test_resp.json -w "%{http_code}" -X "$method" \
    -H "Authorization: Bearer $TOKEN" -H "$H" "$BASE$url")
  
  if [ -n "$body" ] && [ "$body" != "-" ]; then
    curl_args+=(-d "$body")
  fi
  
  local status=$(curl "${curl_args[@]}")
  local resp=$(cat /tmp/test_resp.json 2>/dev/null)
  
  # Handle multiple expected statuses (e.g. "200|201")
  local match=0
  IFS='|' read -ra EXPECTED_CODES <<< "$expected"
  for code in "${EXPECTED_CODES[@]}"; do
    if [ "$status" = "$code" ]; then
      match=1
      break
    fi
  done
  
  if [ "$match" = "1" ]; then
    echo -e "${GREEN}✓ $tc${NC} [$status] $desc"
    PASS=$((PASS + 1))
  else
    echo -e "${RED}✗ $tc${NC} [$status] $desc (expected $expected)"
    # Show error detail
    local detail=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('detail','')[:200])" 2>/dev/null)
    if [ -n "$detail" ]; then
      echo -e "  ${YELLOW}→ $detail${NC}"
    fi
    FAIL=$((FAIL + 1))
    ERRORS="$ERRORS\n$tc [$status] $desc"
  fi
  
  # Return response for chaining
  echo "$resp" > /tmp/last_test_resp.json
}

# Helper to extract field from last response
get_field() {
  python3 -c "import sys,json; d=json.load(open('/tmp/last_test_resp.json')); print(d$1)" 2>/dev/null
}

get_field_from() {
  python3 -c "import sys,json; d=json.load(open('$1')); print(d$2)" 2>/dev/null
}

# ════════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}═══════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  COMPREHENSIVE CRM TEST SUITE — $(date)${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}\n"

login

# ════════════════════════════════════════════════════════════════════
# GROUP 1: ORDERS (Priority 1)
# ════════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}━━━ GROUP 1: ORDERS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 1.1 List Orders
run_test "ORD-001" "List orders (default page)" GET "/api/orders/"
run_test "ORD-002" "List orders with pagination" GET "/api/orders/?page=1&page_size=5"
run_test "ORD-003" "List orders - filter by status=confirmed" GET "/api/orders/?status=confirmed"
run_test "ORD-004" "List orders - filter by status=draft" GET "/api/orders/?status=draft"
run_test "ORD-005" "List orders - filter by payment_status=pending" GET "/api/orders/?payment_status=pending"
run_test "ORD-006" "List orders - filter by payment_status=paid" GET "/api/orders/?payment_status=paid"
run_test "ORD-007" "List orders - search by text" GET "/api/orders/?search=test"
run_test "ORD-008" "List orders - invalid status" GET "/api/orders/?status=nonexistent" "200|422"
run_test "ORD-009" "List orders - page 999 (empty)" GET "/api/orders/?page=999&page_size=10"

# 1.2 Order Stats
run_test "ORD-010" "Get order stats" GET "/api/orders/stats"

# 1.3 Phone Lookup
run_test "ORD-011" "Phone lookup - valid 10-digit" POST "/api/orders/phone-lookup" '{"phone":"9876543210"}'
run_test "ORD-012" "Phone lookup - non-existent phone" POST "/api/orders/phone-lookup" '{"phone":"0000000000"}'
run_test "ORD-013" "Phone lookup - empty phone" POST "/api/orders/phone-lookup" '{"phone":""}' "200|422"
run_test "ORD-014" "Phone lookup - short phone" POST "/api/orders/phone-lookup" '{"phone":"123"}' "200|422"

# 1.4 Parse Address
run_test "ORD-015" "Parse address - full Indian address" POST "/api/orders/parse-address" '{"raw_text":"Ramesh Kumar, 45 MG Road, Bangalore, Karnataka 560001"}'
run_test "ORD-016" "Parse address - minimal address" POST "/api/orders/parse-address" '{"raw_text":"Delhi 110001"}'
run_test "ORD-017" "Parse address - empty string" POST "/api/orders/parse-address" '{"raw_text":""}' "200|400|422"
run_test "ORD-018" "Parse address - only pincode" POST "/api/orders/parse-address" '{"raw_text":"685561"}'
run_test "ORD-019" "Parse address - multi-line address" POST "/api/orders/parse-address" '{"raw_text":"John Doe\n123 Street\nMumbai MH 400001\nPh: 9876543210"}'

# 1.5 Couriers
run_test "ORD-020" "List couriers" GET "/api/orders/couriers"

# 1.6 India Post IDs
run_test "ORD-021" "List India Post IDs" GET "/api/orders/india-post-ids"

# 1.7 Create Order - COD Confirmed
run_test "ORD-030" "Create order - COD confirmed, full data" POST "/api/orders/" '{
  "customer_name": "Test User Alpha",
  "customer_phone": "9111000001",
  "order_intent": "confirmed",
  "items": [{"product_name": "Test Product A", "sku": "TST-A", "quantity": 2, "unit_price": 500, "unit": "piece", "discount_pct": 0}],
  "payment_method": "cod",
  "delivery_name": "Test User Alpha",
  "delivery_address": "123 Test Street",
  "delivery_city": "Mumbai",
  "delivery_state": "Maharashtra",
  "delivery_pincode": "400001",
  "shipping_charge": 50,
  "discount_amount": 0,
  "tax_amount": 0,
  "notes": "TEST ORDER - DELETE ME",
  "shipping_service": "speed_post",
  "order_source": "manual",
  "gst_invoice": true
}' "201"
ORDER_ID_1=$(get_field "['id']")
ORDER_NUM_1=$(get_field "['order_number']")
echo "  Created order: $ORDER_NUM_1 ($ORDER_ID_1)"

# 1.8 Create Order - UPI Confirmed
run_test "ORD-031" "Create order - UPI confirmed" POST "/api/orders/" '{
  "customer_name": "Test User Beta",
  "customer_phone": "9111000002",
  "order_intent": "confirmed",
  "items": [{"product_name": "Widget B", "sku": "WDG-B", "quantity": 1, "unit_price": 1200, "unit": "piece", "discount_pct": 10}],
  "payment_method": "upi",
  "delivery_name": "Test User Beta",
  "delivery_address": "456 Test Avenue",
  "delivery_city": "Delhi",
  "delivery_state": "Delhi",
  "delivery_pincode": "110001",
  "shipping_charge": 0,
  "discount_amount": 50,
  "tax_amount": 18,
  "shipping_service": "parcel",
  "order_source": "manual"
}' "201"
ORDER_ID_2=$(get_field "['id']")
ORDER_NUM_2=$(get_field "['order_number']")
echo "  Created order: $ORDER_NUM_2 ($ORDER_ID_2)"

# 1.9 Create Order - Not Confirmed (creates lead)
run_test "ORD-032" "Create order - Not confirmed (→ lead)" POST "/api/orders/" '{
  "customer_name": "Test Lead Person",
  "customer_phone": "9111000003",
  "order_intent": "not_confirmed",
  "not_confirmed_reason": "Price too high, will call back",
  "items": [{"product_name": "Premium Item", "sku": "PRM-1", "quantity": 1, "unit_price": 5000, "unit": "piece", "discount_pct": 0}],
  "payment_method": "cod",
  "delivery_name": "Test Lead Person",
  "delivery_address": "789 Lead Lane",
  "delivery_city": "Jaipur",
  "delivery_state": "Rajasthan",
  "delivery_pincode": "302001",
  "shipping_charge": 100,
  "order_source": "manual"
}' "201"
ORDER_ID_3=$(get_field "['id']")
echo "  Created not-confirmed order: $ORDER_ID_3"

# 1.10 Create Order - Partial COD
run_test "ORD-033" "Create order - Partial COD with advance" POST "/api/orders/" '{
  "customer_name": "Test Partial User",
  "customer_phone": "9111000004",
  "order_intent": "confirmed",
  "items": [{"product_name": "Expensive Thing", "sku": "EXP-1", "quantity": 1, "unit_price": 3000, "unit": "piece", "discount_pct": 0}],
  "payment_method": "partial_cod",
  "advance_amount": 1000,
  "delivery_name": "Test Partial User",
  "delivery_address": "Partial Street 10",
  "delivery_city": "Chennai",
  "delivery_state": "Tamil Nadu",
  "delivery_pincode": "600001",
  "shipping_charge": 80,
  "order_source": "manual"
}' "201"
ORDER_ID_4=$(get_field "['id']")
echo "  Created partial COD order: $ORDER_ID_4"

# 1.11 Create Order - Multiple items
run_test "ORD-034" "Create order - multiple items (3)" POST "/api/orders/" '{
  "customer_name": "Multi Item User",
  "customer_phone": "9111000005",
  "order_intent": "confirmed",
  "items": [
    {"product_name": "Item A", "quantity": 2, "unit_price": 100, "unit": "piece", "discount_pct": 0},
    {"product_name": "Item B", "quantity": 1, "unit_price": 250, "unit": "kg", "discount_pct": 5},
    {"product_name": "Item C", "quantity": 3, "unit_price": 75, "unit": "piece", "discount_pct": 10}
  ],
  "payment_method": "bank_transfer",
  "delivery_name": "Multi Item User",
  "delivery_address": "Multi Lane 5",
  "delivery_city": "Kolkata",
  "delivery_state": "West Bengal",
  "delivery_pincode": "700001",
  "order_source": "manual"
}' "201"
ORDER_ID_5=$(get_field "['id']")
echo "  Created multi-item order: $ORDER_ID_5"

# 1.12 Create Order - Edge cases
run_test "ORD-035" "Create order - zero discount/shipping/tax" POST "/api/orders/" '{
  "customer_name": "Zero Extras User",
  "customer_phone": "9111000006",
  "order_intent": "confirmed",
  "items": [{"product_name": "Simple Item", "quantity": 1, "unit_price": 999.99, "unit": "piece", "discount_pct": 0}],
  "payment_method": "cod",
  "delivery_name": "Zero Extras User",
  "delivery_address": "Simple Road 1",
  "delivery_city": "Pune",
  "delivery_state": "Maharashtra",
  "delivery_pincode": "411001",
  "shipping_charge": 0,
  "discount_amount": 0,
  "tax_amount": 0,
  "order_source": "manual"
}' "201"
ORDER_ID_6=$(get_field "['id']")

run_test "ORD-036" "Create order - missing required fields" POST "/api/orders/" '{
  "customer_name": "No Items User",
  "items": []
}' "422"

run_test "ORD-037" "Create order - no customer info at all" POST "/api/orders/" '{
  "items": [{"product_name": "X", "quantity": 1, "unit_price": 100, "unit": "piece"}],
  "payment_method": "cod",
  "delivery_address": "addr",
  "delivery_city": "city",
  "delivery_state": "state",
  "delivery_pincode": "000000"
}' "201|422"

# 1.13 Get Order Detail
run_test "ORD-040" "Get order detail" GET "/api/orders/$ORDER_ID_1"
run_test "ORD-041" "Get order detail - non-existent ID" GET "/api/orders/00000000-0000-0000-0000-000000000000" "404"
run_test "ORD-042" "Get order detail - invalid UUID" GET "/api/orders/not-a-uuid" "404|422"

# 1.14 Update Order (PATCH) - the bug we fixed!
run_test "ORD-050" "Update order - change payment method COD→UPI" PATCH "/api/orders/$ORDER_ID_1" '{"payment_method": "upi"}'
run_test "ORD-051" "Update order - change payment status to paid" PATCH "/api/orders/$ORDER_ID_1" '{"payment_status": "paid"}'
run_test "ORD-052" "Update order - change delivery address" PATCH "/api/orders/$ORDER_ID_1" '{
  "delivery_address": "Updated Address 999",
  "delivery_city": "Updated City",
  "delivery_state": "Updated State",
  "delivery_pincode": "999999"
}'
run_test "ORD-053" "Update order - change notes" PATCH "/api/orders/$ORDER_ID_1" '{"notes": "Updated test notes"}'
run_test "ORD-054" "Update order - change shipping charge" PATCH "/api/orders/$ORDER_ID_1" '{"shipping_charge": 150}'
run_test "ORD-055" "Update order - change discount amount" PATCH "/api/orders/$ORDER_ID_1" '{"discount_amount": 25}'
run_test "ORD-056" "Update order - change payment to partial_cod" PATCH "/api/orders/$ORDER_ID_4" '{"payment_method": "partial_cod", "advance_amount": 500}'
run_test "ORD-057" "Update order - replace items" PATCH "/api/orders/$ORDER_ID_1" '{
  "items": [
    {"product_name": "Replaced Item X", "sku": "RPL-X", "quantity": 3, "unit_price": 200, "unit": "piece", "discount_pct": 5},
    {"product_name": "Replaced Item Y", "sku": "RPL-Y", "quantity": 1, "unit_price": 800, "unit": "kg", "discount_pct": 0}
  ]
}'
run_test "ORD-058" "Update order - change delivery name" PATCH "/api/orders/$ORDER_ID_1" '{"delivery_name": "New Delivery Name"}'
run_test "ORD-059" "Update order - non-existent order" PATCH "/api/orders/00000000-0000-0000-0000-000000000000" '{"notes":"x"}' "404"

# 1.15 Order Status Flow
run_test "ORD-060" "Status: confirmed → processing" POST "/api/orders/$ORDER_ID_2/status" '{"status": "processing"}'
run_test "ORD-061" "Status: processing → packed" POST "/api/orders/$ORDER_ID_2/status" '{"status": "packed"}'
run_test "ORD-062" "Status: packed → shipped" POST "/api/orders/$ORDER_ID_2/status" '{"status": "shipped", "tracking_number": "TEST123456789"}'
run_test "ORD-063" "Status: shipped → out_for_delivery" POST "/api/orders/$ORDER_ID_2/status" '{"status": "out_for_delivery"}'
run_test "ORD-064" "Status: out_for_delivery → delivered" POST "/api/orders/$ORDER_ID_2/status" '{"status": "delivered"}'
run_test "ORD-065" "Status: invalid transition (confirmed → delivered)" POST "/api/orders/$ORDER_ID_1/status" '{"status": "delivered"}' "400"
run_test "ORD-066" "Status: delivered → returned" POST "/api/orders/$ORDER_ID_2/status" '{"status": "returned"}'

# 1.16 Edit delivered/cancelled order (should fail for non-status fields)
run_test "ORD-067" "Edit delivered order - should fail" PATCH "/api/orders/$ORDER_ID_2" '{"delivery_address": "should fail"}' "400"

# 1.17 Quick payment status update
run_test "ORD-068" "Quick update pay status to paid" PATCH "/api/orders/$ORDER_ID_5" '{"payment_status": "paid"}'
run_test "ORD-069" "Quick update pay status to pending" PATCH "/api/orders/$ORDER_ID_5" '{"payment_status": "pending"}'

# 1.18 Delete Order (only draft/cancelled)
run_test "ORD-070" "Delete confirmed order (should fail)" DELETE "/api/orders/$ORDER_ID_1" "-" "400"
# Cancel first, then delete
run_test "ORD-071" "Cancel order for delete test" POST "/api/orders/$ORDER_ID_6/status" '{"status": "cancelled"}'
run_test "ORD-072" "Delete cancelled order" DELETE "/api/orders/$ORDER_ID_6"

# 1.19 Verify items_summary property works after update
run_test "ORD-075" "Verify order detail after item replace" GET "/api/orders/$ORDER_ID_1"
ITEMS_SUMMARY=$(python3 -c "import json; d=json.load(open('/tmp/last_test_resp.json')); print(d.get('items_summary',''))" 2>/dev/null)
echo "  items_summary = '$ITEMS_SUMMARY'"
if [ -z "$ITEMS_SUMMARY" ]; then
  echo -e "  ${YELLOW}⚠ items_summary is empty (might be expected if property returns empty)${NC}"
fi

# ════════════════════════════════════════════════════════════════════
# GROUP 2: LEADS (Priority 1)
# ════════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}━━━ GROUP 2: LEADS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 2.1 List Leads
run_test "LEAD-001" "List leads (default)" GET "/api/leads/"
run_test "LEAD-002" "List leads with pagination" GET "/api/leads/?page=1&page_size=5"
run_test "LEAD-003" "List leads - filter by status" GET "/api/leads/?status=created"
run_test "LEAD-004" "List leads - search" GET "/api/leads/?search=test"
run_test "LEAD-005" "List leads - page 999" GET "/api/leads/?page=999"

# 2.2 Lead Stats
run_test "LEAD-010" "Get lead stats" GET "/api/leads/stats"

# 2.3 Reminders
run_test "LEAD-011" "Get today's reminders" GET "/api/leads/reminders/today"

# 2.4 Lost leads
run_test "LEAD-012" "List lost leads" GET "/api/leads/lost_leads/list"

# 2.5 Create Lead
run_test "LEAD-020" "Create lead - full data" POST "/api/leads/" '{
  "name": "Test Lead Alpha",
  "phone": "9222000001",
  "alternate_phone": "9222000011",
  "source": "manual",
  "status": "created",
  "product_interest": "Premium Widget",
  "city": "Bangalore",
  "state": "Karnataka",
  "notes": "TEST LEAD - DELETE ME",
  "next_followup_date": "2026-03-10"
}' "201"
LEAD_ID_1=$(get_field "['id']")
LEAD_NUM_1=$(get_field "['lead_number']")
echo "  Created lead: $LEAD_NUM_1 ($LEAD_ID_1)"

run_test "LEAD-021" "Create lead - minimal data" POST "/api/leads/" '{
  "name": "Minimal Lead",
  "phone": "9222000002",
  "source": "manual"
}' "201"
LEAD_ID_2=$(get_field "['id']")
echo "  Created lead: $LEAD_ID_2"

run_test "LEAD-022" "Create lead - duplicate phone (same phone)" POST "/api/leads/" '{
  "name": "Duplicate Phone Lead",
  "phone": "9222000001",
  "source": "manual"
}' "201|400|409"
LEAD_ID_DUP=$(get_field "['id']")

run_test "LEAD-023" "Create lead - WhatsApp source" POST "/api/leads/" '{
  "name": "WhatsApp Lead",
  "phone": "9222000003",
  "source": "whatsapp",
  "status": "created",
  "product_interest": "Organic Products",
  "notes": "Came from WA"
}' "201"
LEAD_ID_3=$(get_field "['id']")

run_test "LEAD-024" "Create lead - website source" POST "/api/leads/" '{
  "name": "Website Lead",
  "phone": "9222000004",
  "source": "website",
  "status": "created",
  "city": "Hyderabad",
  "state": "Telangana"
}' "201"
LEAD_ID_4=$(get_field "['id']")

run_test "LEAD-025" "Create lead - with followup date in past" POST "/api/leads/" '{
  "name": "Past Followup Lead",
  "phone": "9222000005",
  "source": "manual",
  "next_followup_date": "2025-01-01"
}' "201"
LEAD_ID_5=$(get_field "['id']")

run_test "LEAD-026" "Create lead - empty name" POST "/api/leads/" '{
  "name": "",
  "phone": "9222000006",
  "source": "manual"
}' "201|422"

run_test "LEAD-027" "Create lead - missing phone" POST "/api/leads/" '{
  "name": "No Phone Lead"
}' "201|422"

# 2.6 Get Lead Detail
run_test "LEAD-030" "Get lead detail" GET "/api/leads/$LEAD_ID_1"
run_test "LEAD-031" "Get lead detail - non-existent" GET "/api/leads/00000000-0000-0000-0000-000000000000" "404"

# 2.7 Update Lead
run_test "LEAD-040" "Update lead - change name" PATCH "/api/leads/$LEAD_ID_1" '{"name": "Updated Lead Name"}'
run_test "LEAD-041" "Update lead - change status to contacted" PATCH "/api/leads/$LEAD_ID_1" '{"status": "contacted"}'
run_test "LEAD-042" "Update lead - change city/state" PATCH "/api/leads/$LEAD_ID_1" '{"city": "Chennai", "state": "Tamil Nadu"}'
run_test "LEAD-043" "Update lead - change product interest" PATCH "/api/leads/$LEAD_ID_1" '{"product_interest": "Updated Interest"}'
run_test "LEAD-044" "Update lead - change notes" PATCH "/api/leads/$LEAD_ID_1" '{"notes": "Updated notes for testing"}'
run_test "LEAD-045" "Update lead - change followup date" PATCH "/api/leads/$LEAD_ID_1" '{"next_followup_date": "2026-04-01"}'
run_test "LEAD-046" "Update lead - null followup date" PATCH "/api/leads/$LEAD_ID_1" '{"next_followup_date": null}'
run_test "LEAD-047" "Update lead - non-existent" PATCH "/api/leads/00000000-0000-0000-0000-000000000000" '{"name":"x"}' "404"

# 2.8 Lead WABIS Labels
run_test "LEAD-050" "Update lead WABIS labels" PATCH "/api/leads/$LEAD_ID_1/wabis-labels" '{"labels": ["hot", "interested"]}'
run_test "LEAD-051" "Update lead WABIS labels - empty" PATCH "/api/leads/$LEAD_ID_1/wabis-labels" '{"labels": []}'

# 2.9 Lead Activities
run_test "LEAD-060" "Add lead activity - note" POST "/api/leads/$LEAD_ID_1/activities" '{
  "activity_type": "note",
  "note": "Test note activity"
}' "201"

run_test "LEAD-061" "Add lead activity - call" POST "/api/leads/$LEAD_ID_1/activities" '{
  "activity_type": "call",
  "note": "Called customer, interested in product"
}' "201"

run_test "LEAD-062" "Add lead activity - whatsapp" POST "/api/leads/$LEAD_ID_1/activities" '{
  "activity_type": "whatsapp",
  "note": "Sent product catalog via WA"
}' "201"

# 2.10 Lead Contacted
run_test "LEAD-070" "Mark lead as contacted" POST "/api/leads/$LEAD_ID_2/contacted" '{"note": "Called and discussed"}'

# 2.11 Lead Convert
run_test "LEAD-071" "Convert lead to customer" POST "/api/leads/$LEAD_ID_4/convert" '{}' "201|200"

# 2.12 Lead Success Won
run_test "LEAD-072" "Mark lead as success won" POST "/api/leads/$LEAD_ID_3/success_won" '{}' "201|200"

# 2.13 Lead Messages
run_test "LEAD-080" "Get lead messages" GET "/api/leads/$LEAD_ID_1/messages"
run_test "LEAD-081" "Send lead message" POST "/api/leads/$LEAD_ID_1/messages" '{"message": "Hello, this is a test message", "direction": "outbound"}' "201|200|422"

# 2.14 Lead Orders
run_test "LEAD-085" "Get lead orders" GET "/api/leads/$LEAD_ID_1/orders"

# 2.15 Delete Lead
run_test "LEAD-090" "Delete lead" DELETE "/api/leads/$LEAD_ID_5"
run_test "LEAD-091" "Delete lead - non-existent" DELETE "/api/leads/00000000-0000-0000-0000-000000000000" "404"


# ════════════════════════════════════════════════════════════════════
# GROUP 3: CUSTOMERS (Priority 1)
# ════════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}━━━ GROUP 3: CUSTOMERS ━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 3.1 List Customers
run_test "CUST-001" "List customers (default)" GET "/api/customers/"
run_test "CUST-002" "List customers with pagination" GET "/api/customers/?page=1&page_size=5"
run_test "CUST-003" "List customers - search" GET "/api/customers/?search=test"
run_test "CUST-004" "List customers - page 999" GET "/api/customers/?page=999"

# 3.2 Customer Stats
run_test "CUST-010" "Get customer stats" GET "/api/customers/stats"

# 3.3 Customers With Orders
run_test "CUST-011" "List customers with orders" GET "/api/customers/with-orders"

# 3.4 Create Customer
run_test "CUST-020" "Create customer - full data" POST "/api/customers/" '{
  "name": "Test Customer Alpha",
  "phone": "9333000001",
  "alternate_phone": "9333000011",
  "address": "123 Customer St",
  "city": "Mumbai",
  "state": "Maharashtra",
  "pincode": "400001",
  "source": "manual",
  "lead_status": "active",
  "notes": "TEST CUSTOMER - DELETE ME"
}' "201"
CUST_ID_1=$(get_field "['id']")
echo "  Created customer: $CUST_ID_1"

run_test "CUST-021" "Create customer - minimal data" POST "/api/customers/" '{
  "name": "Minimal Customer",
  "phone": "9333000002"
}' "201"
CUST_ID_2=$(get_field "['id']")

run_test "CUST-022" "Create customer - with email" POST "/api/customers/" '{
  "name": "Email Customer",
  "phone": "9333000003",
  "email": "test@example.com",
  "city": "Delhi",
  "state": "Delhi",
  "pincode": "110001"
}' "201"
CUST_ID_3=$(get_field "['id']")

run_test "CUST-023" "Create customer - duplicate phone" POST "/api/customers/" '{
  "name": "Dup Phone Customer",
  "phone": "9333000001"
}' "201|400|409"

run_test "CUST-024" "Create customer - missing name" POST "/api/customers/" '{
  "phone": "9333000004"
}' "422"

# 3.5 Get Customer Detail
run_test "CUST-030" "Get customer detail" GET "/api/customers/$CUST_ID_1"
run_test "CUST-031" "Get customer detail - non-existent" GET "/api/customers/00000000-0000-0000-0000-000000000000" "404"

# 3.6 Update Customer
run_test "CUST-040" "Update customer - change name" PATCH "/api/customers/$CUST_ID_1" '{"name": "Updated Customer Name"}'
run_test "CUST-041" "Update customer - change address" PATCH "/api/customers/$CUST_ID_1" '{"address": "Updated Addr", "city": "Pune", "state": "MH", "pincode": "411001"}'
run_test "CUST-042" "Update customer - change phone" PATCH "/api/customers/$CUST_ID_1" '{"phone": "9333999999"}'
run_test "CUST-043" "Update customer - add notes" PATCH "/api/customers/$CUST_ID_1" '{"notes": "Updated test notes"}'
run_test "CUST-044" "Update customer - change payment mode" PATCH "/api/customers/$CUST_ID_1" '{"payment_mode_preference": "prepaid"}'
run_test "CUST-045" "Update customer - non-existent" PATCH "/api/customers/00000000-0000-0000-0000-000000000000" '{"name":"x"}' "404"

# 3.7 Customer Orders
run_test "CUST-050" "Get customer orders" GET "/api/customers/$CUST_ID_1/orders"

# 3.8 Customer Interactions
run_test "CUST-060" "Add customer interaction" POST "/api/customers/$CUST_ID_1/interactions" '{
  "interaction_type": "note",
  "note": "Test interaction note",
  "channel": "phone"
}' "201"

# 3.9 Toggle Customer Status
run_test "CUST-070" "Toggle customer status (deactivate)" PATCH "/api/customers/$CUST_ID_2/toggle-status"
run_test "CUST-071" "Toggle customer status (reactivate)" PATCH "/api/customers/$CUST_ID_2/toggle-status"

# 3.10 Delete Customer
run_test "CUST-080" "Delete customer" DELETE "/api/customers/$CUST_ID_3"
run_test "CUST-081" "Delete customer - non-existent" DELETE "/api/customers/00000000-0000-0000-0000-000000000000" "404"


# ════════════════════════════════════════════════════════════════════
# GROUP 4: PRODUCTS
# ════════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}━━━ GROUP 4: PRODUCTS ━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

run_test "PROD-001" "List products" GET "/api/products/"
run_test "PROD-002" "List products with search" GET "/api/products/?search=test"
run_test "PROD-003" "Get product categories" GET "/api/products/categories"

run_test "PROD-010" "Create product - full data" POST "/api/products/" '{
  "name": "Test Product X",
  "sku": "TST-X-001",
  "category": "Testing",
  "unit_price": 599.99,
  "cost_price": 300,
  "unit": "piece",
  "description": "A test product",
  "hsn_code": "8544",
  "gst_rate": 18,
  "min_stock": 10
}' "201"
PROD_ID_1=$(get_field "['id']")
echo "  Created product: $PROD_ID_1"

run_test "PROD-011" "Create product - minimal" POST "/api/products/" '{
  "name": "Minimal Product",
  "sku": "MIN-001",
  "unit_price": 100
}' "201"
PROD_ID_2=$(get_field "['id']")

run_test "PROD-012" "Create product - duplicate SKU" POST "/api/products/" '{
  "name": "Dup SKU Product",
  "sku": "TST-X-001",
  "unit_price": 200
}' "201|400|409"

run_test "PROD-020" "Get product detail" GET "/api/products/$PROD_ID_1"
run_test "PROD-021" "Get product - non-existent" GET "/api/products/00000000-0000-0000-0000-000000000000" "404"

run_test "PROD-030" "Update product - change price" PATCH "/api/products/$PROD_ID_1" '{"unit_price": 699.99}'
run_test "PROD-031" "Update product - change name" PATCH "/api/products/$PROD_ID_1" '{"name": "Updated Product X"}'
run_test "PROD-032" "Update product - change category" PATCH "/api/products/$PROD_ID_1" '{"category": "Updated Category"}'

run_test "PROD-040" "Delete product" DELETE "/api/products/$PROD_ID_2"
run_test "PROD-041" "Delete product - non-existent" DELETE "/api/products/00000000-0000-0000-0000-000000000000" "404"


# ════════════════════════════════════════════════════════════════════
# GROUP 5: VENDORS
# ════════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}━━━ GROUP 5: VENDORS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

run_test "VEND-001" "List vendors" GET "/api/vendors/"
run_test "VEND-002" "List vendors - search" GET "/api/vendors/?search=test"

run_test "VEND-010" "Create vendor - full data" POST "/api/vendors/" '{
  "name": "Test Vendor Co",
  "contact_name": "Vendor Contact",
  "phone": "9444000001",
  "email": "vendor@test.com",
  "address": "Vendor Street 1",
  "city": "Ahmedabad",
  "state": "Gujarat",
  "gstin": "24AAAAA0000A1Z5"
}' "201"
VEND_ID_1=$(get_field "['id']")
echo "  Created vendor: $VEND_ID_1"

run_test "VEND-011" "Create vendor - minimal" POST "/api/vendors/" '{
  "name": "Minimal Vendor"
}' "201"
VEND_ID_2=$(get_field "['id']")

run_test "VEND-020" "Get vendor detail" GET "/api/vendors/$VEND_ID_1"
run_test "VEND-021" "Get vendor - non-existent" GET "/api/vendors/00000000-0000-0000-0000-000000000000" "404"

run_test "VEND-030" "Update vendor" PATCH "/api/vendors/$VEND_ID_1" '{"name": "Updated Vendor Co"}'

# Vendor Products
run_test "VEND-040" "List vendor products" GET "/api/vendors/$VEND_ID_1/products"
run_test "VEND-041" "Add vendor product" POST "/api/vendors/$VEND_ID_1/products" "{
  \"product_id\": \"$PROD_ID_1\",
  \"vendor_sku\": \"V-TST-X\",
  \"vendor_price\": 250,
  \"lead_time_days\": 5
}" "201"

run_test "VEND-050" "Delete vendor" DELETE "/api/vendors/$VEND_ID_2" "204"
run_test "VEND-051" "Delete vendor - non-existent" DELETE "/api/vendors/00000000-0000-0000-0000-000000000000" "404"


# ════════════════════════════════════════════════════════════════════
# GROUP 6: INVOICES
# ════════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}━━━ GROUP 6: INVOICES ━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

run_test "INV-001" "List invoices" GET "/api/invoices/"
run_test "INV-002" "List invoices - filter by status" GET "/api/invoices/?status=draft"

run_test "INV-010" "Create invoice from order" POST "/api/invoices/" "{\"order_id\": \"$ORDER_ID_1\"}" "201|200|400"
INV_ID_1=$(get_field "['id']" 2>/dev/null)
echo "  Created invoice: $INV_ID_1"

if [ -n "$INV_ID_1" ] && [ "$INV_ID_1" != "None" ]; then
  run_test "INV-020" "Get invoice detail" GET "/api/invoices/$INV_ID_1"
  run_test "INV-030" "Update invoice" PATCH "/api/invoices/$INV_ID_1" '{"notes": "Test invoice note"}'
  run_test "INV-040" "Finalize invoice" POST "/api/invoices/$INV_ID_1/finalize" "{}" "200"
  run_test "INV-050" "Get invoice PDF" GET "/api/invoices/$INV_ID_1/pdf" "-" "200"
  run_test "INV-060" "Cancel invoice" POST "/api/invoices/$INV_ID_1/cancel" "{}" "200"
fi

run_test "INV-070" "Quick PDF from order" GET "/api/invoices/order/$ORDER_ID_1/quick-pdf" "-" "200"


# ════════════════════════════════════════════════════════════════════
# GROUP 7: INVENTORY
# ════════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}━━━ GROUP 7: INVENTORY ━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

run_test "INV-101" "List inventory stock" GET "/api/inventory/stock"
run_test "INV-102" "List inventory movements" GET "/api/inventory/movements"

if [ -n "$PROD_ID_1" ] && [ "$PROD_ID_1" != "None" ]; then
  run_test "INV-103" "Get product stock" GET "/api/inventory/stock/$PROD_ID_1"
  run_test "INV-110" "Adjust inventory - add stock" POST "/api/inventory/adjust" "{
    \"product_id\": \"$PROD_ID_1\",
    \"quantity_change\": 50,
    \"movement_type\": \"purchase\",
    \"note\": \"Test stock addition\"
  }" "201"
  run_test "INV-111" "Adjust inventory - remove stock" POST "/api/inventory/adjust" "{
    \"product_id\": \"$PROD_ID_1\",
    \"quantity_change\": -5,
    \"movement_type\": \"adjustment\",
    \"note\": \"Test stock removal\"
  }" "201"
fi


# ════════════════════════════════════════════════════════════════════
# GROUP 8: LABELS
# ════════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}━━━ GROUP 8: LABELS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

run_test "LBL-001" "Generate label for order" POST "/api/labels/generate" "{\"order_ids\": [\"$ORDER_ID_1\"]}" "200"
run_test "LBL-002" "Generate label - non-existent order" POST "/api/labels/generate" '{"order_ids": ["00000000-0000-0000-0000-000000000000"]}' "200|404|400"
run_test "LBL-003" "Generate label - multiple orders" POST "/api/labels/generate" "{\"order_ids\": [\"$ORDER_ID_1\", \"$ORDER_ID_4\"]}" "200"


# ════════════════════════════════════════════════════════════════════
# GROUP 9: PURCHASES
# ════════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}━━━ GROUP 9: PURCHASES ━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

run_test "PO-001" "List purchase orders" GET "/api/purchases/"

if [ -n "$VEND_ID_1" ] && [ "$VEND_ID_1" != "None" ]; then
  run_test "PO-010" "Create purchase order" POST "/api/purchases/" "{
    \"vendor_id\": \"$VEND_ID_1\",
    \"items\": [{\"product_id\": \"$PROD_ID_1\", \"quantity\": 100, \"unit_price\": 250}],
    \"notes\": \"Test PO\"
  }" "201"
  PO_ID=$(get_field "['id']" 2>/dev/null)
  echo "  Created PO: $PO_ID"
  
  if [ -n "$PO_ID" ] && [ "$PO_ID" != "None" ]; then
    run_test "PO-020" "Get purchase order detail" GET "/api/purchases/$PO_ID"
    run_test "PO-030" "Update purchase order" PATCH "/api/purchases/$PO_ID" '{"notes": "Updated PO notes"}'
  fi
fi


# ════════════════════════════════════════════════════════════════════
# GROUP 10: GST
# ════════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}━━━ GROUP 10: GST ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

run_test "GST-001" "Get GST profile" GET "/api/gst/profile"
run_test "GST-002" "Get GSTR1 data" GET "/api/gst/gstr1"
run_test "GST-003" "Get HSN summary" GET "/api/gst/hsn-summary"
run_test "GST-004" "Get tax summary" GET "/api/gst/tax-summary"
run_test "GST-005" "Validate GSTIN" GET "/api/gst/validate-gstin/24AAAAA0000A1Z5"


# ════════════════════════════════════════════════════════════════════
# GROUP 11: INDIA POST
# ════════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}━━━ GROUP 11: INDIA POST ━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

run_test "IP-001" "Pincode lookup" GET "/api/india-post/pincode?pincode=685561"
run_test "IP-002" "Pincode lookup - invalid" GET "/api/india-post/pincode?pincode=000000" "200|400|404"
run_test "IP-003" "Tariff check" GET "/api/india-post/tariff?source_pincode=685561&dest_pincode=400001&weight=500&service_type=speed_post&cod_amount=0" "200|400|500"


# ════════════════════════════════════════════════════════════════════
# GROUP 12: EDGE CASES & SECURITY
# ════════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}━━━ GROUP 12: EDGE CASES & SECURITY ━━━━━━━━━━━━━${NC}"

# No auth
run_test "SEC-001" "Access without token" GET "/api/orders/" "-" "401"
# Temporarily override TOKEN
OLD_TOKEN=$TOKEN
TOKEN="invalid_token_12345"
run_test "SEC-002" "Access with invalid token" GET "/api/orders/" "-" "401"
TOKEN=$OLD_TOKEN

# XSS in data fields
run_test "SEC-010" "XSS in customer name" POST "/api/customers/" '{
  "name": "<script>alert(1)</script>Test",
  "phone": "9555000001"
}' "201"
CUST_XSS=$(get_field "['name']" 2>/dev/null)
echo "  Stored name: $CUST_XSS"

run_test "SEC-011" "XSS in order notes" PATCH "/api/orders/$ORDER_ID_1" '{"notes": "<img onerror=alert(1) src=x>"}'

# SQL injection attempts
run_test "SEC-020" "SQL injection in search" GET "/api/orders/?search='; DROP TABLE orders; --"
run_test "SEC-021" "SQL injection in customer search" GET "/api/customers/?search=1 OR 1=1"

# Large payload
run_test "SEC-030" "Large notes field (5000 chars)" PATCH "/api/orders/$ORDER_ID_1" "{\"notes\": \"$(python3 -c "print('A'*5000)")\"}"

# Unicode
run_test "SEC-040" "Unicode in customer name" POST "/api/customers/" '{
  "name": "टेस्ट कस्टमर हिंदी",
  "phone": "9555000002"
}' "201"
run_test "SEC-041" "Unicode in lead name" POST "/api/leads/" '{
  "name": "テスト リード 日本語",
  "phone": "9555000003",
  "source": "manual"
}' "201"

# Empty body
run_test "SEC-050" "PATCH order with empty body" PATCH "/api/orders/$ORDER_ID_1" '{}' "200"
run_test "SEC-051" "PATCH customer with empty body" PATCH "/api/customers/$CUST_ID_1" '{}' "200"
run_test "SEC-052" "PATCH lead with empty body" PATCH "/api/leads/$LEAD_ID_1" '{}' "200"

# Negative amounts
run_test "SEC-060" "Order with negative price" POST "/api/orders/" '{
  "customer_name": "Negative Price User",
  "customer_phone": "9555000004",
  "order_intent": "confirmed",
  "items": [{"product_name": "Negative", "quantity": 1, "unit_price": -100, "unit": "piece"}],
  "payment_method": "cod",
  "delivery_address": "a", "delivery_city": "b", "delivery_state": "c", "delivery_pincode": "100001"
}' "201|422|400"

run_test "SEC-061" "Order with zero quantity" POST "/api/orders/" '{
  "customer_name": "Zero Qty User",
  "customer_phone": "9555000005",
  "order_intent": "confirmed",
  "items": [{"product_name": "Zero", "quantity": 0, "unit_price": 100, "unit": "piece"}],
  "payment_method": "cod",
  "delivery_address": "a", "delivery_city": "b", "delivery_state": "c", "delivery_pincode": "100001"
}' "201|422|400"

run_test "SEC-062" "Order with huge quantity" POST "/api/orders/" '{
  "customer_name": "Huge Qty User",
  "customer_phone": "9555000006",
  "order_intent": "confirmed",
  "items": [{"product_name": "Huge", "quantity": 999999, "unit_price": 1, "unit": "piece"}],
  "payment_method": "cod",
  "delivery_address": "a", "delivery_city": "b", "delivery_state": "c", "delivery_pincode": "100001"
}' "201|422"


# ════════════════════════════════════════════════════════════════════
# CLEANUP: Delete all test data
# ════════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}━━━ CLEANUP: Removing test data ━━━━━━━━━━━━━━━━━${NC}"

# Delete test orders (cancel first if needed)
for oid in $ORDER_ID_1 $ORDER_ID_3 $ORDER_ID_4 $ORDER_ID_5; do
  if [ -n "$oid" ] && [ "$oid" != "None" ]; then
    # Try cancel first
    curl -s -X POST "$BASE/api/orders/$oid/status" -H "Authorization: Bearer $TOKEN" -H "$H" -d '{"status":"cancelled"}' > /dev/null 2>&1
    # Then delete
    curl -s -X DELETE "$BASE/api/orders/$oid" -H "Authorization: Bearer $TOKEN" -H "$H" > /dev/null 2>&1
  fi
done
echo "  Cleaned up test orders"

# Delete test customers
for cid in $CUST_ID_1 $CUST_ID_2; do
  if [ -n "$cid" ] && [ "$cid" != "None" ]; then
    curl -s -X DELETE "$BASE/api/customers/$cid" -H "Authorization: Bearer $TOKEN" -H "$H" > /dev/null 2>&1
  fi
done
echo "  Cleaned up test customers"

# Delete test leads
for lid in $LEAD_ID_1 $LEAD_ID_2 $LEAD_ID_3 $LEAD_ID_DUP; do
  if [ -n "$lid" ] && [ "$lid" != "None" ]; then
    curl -s -X DELETE "$BASE/api/leads/$lid" -H "Authorization: Bearer $TOKEN" -H "$H" > /dev/null 2>&1
  fi
done
echo "  Cleaned up test leads"

# Delete test products
if [ -n "$PROD_ID_1" ] && [ "$PROD_ID_1" != "None" ]; then
  curl -s -X DELETE "$BASE/api/products/$PROD_ID_1" -H "Authorization: Bearer $TOKEN" -H "$H" > /dev/null 2>&1
fi
echo "  Cleaned up test products"

# Delete test vendors
if [ -n "$VEND_ID_1" ] && [ "$VEND_ID_1" != "None" ]; then
  curl -s -X DELETE "$BASE/api/vendors/$VEND_ID_1" -H "Authorization: Bearer $TOKEN" -H "$H" > /dev/null 2>&1
fi
echo "  Cleaned up test vendors"

# Clean up XSS test customers and Unicode customers
# Query for test phone numbers and delete
for phone in 9555000001 9555000002 9555000003 9555000004 9555000005 9555000006; do
  docker exec miguel_db psql -U miguel_user -d miguel_db -c "DELETE FROM customers WHERE phone='$phone';" > /dev/null 2>&1
done

# Clean up test leads by phone
for phone in 9222000001 9222000002 9222000003 9222000004 9222000005 9222000006 9555000003; do
  docker exec miguel_db psql -U miguel_user -d miguel_db -c "DELETE FROM lead_activities WHERE lead_id IN (SELECT id FROM leads WHERE phone='$phone');" > /dev/null 2>&1
  docker exec miguel_db psql -U miguel_user -d miguel_db -c "DELETE FROM leads WHERE phone='$phone';" > /dev/null 2>&1
done

# Clean up test customers auto-created by orders
for phone in 9111000001 9111000002 9111000003 9111000004 9111000005 9111000006; do
  docker exec miguel_db psql -U miguel_user -d miguel_db -c "DELETE FROM customers WHERE phone='$phone';" > /dev/null 2>&1
done

echo "  Database cleanup complete"


# ════════════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}═══════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  TEST RESULTS SUMMARY${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo -e "  ${GREEN}PASSED: $PASS${NC}"
echo -e "  ${RED}FAILED: $FAIL${NC}"
echo -e "  TOTAL:  $((PASS + FAIL))"
echo ""
if [ "$FAIL" -gt 0 ]; then
  echo -e "${RED}FAILED TESTS:${NC}"
  echo -e "$ERRORS"
fi
echo ""
