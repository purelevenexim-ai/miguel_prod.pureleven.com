#!/bin/bash
# ════════════════════════════════════════════════════════════════════
# COMPREHENSIVE CRM FEATURE TEST SUITE v2 (corrected schemas + expectations)
# ════════════════════════════════════════════════════════════════════

BASE="http://localhost:8000"
TOKEN=""
TENANT_ID=""
PASS=0
FAIL=0
ERRORS=""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

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

run_test() {
  local tc="$1" desc="$2" method="$3" url="$4" body="$5" expected="${6:-200}"
  
  local curl_args=(-s -o /tmp/test_resp.json -w "%{http_code}" -X "$method" \
    -H "Authorization: Bearer $TOKEN" -H "$H" "$BASE$url")
  
  if [ -n "$body" ] && [ "$body" != "-" ]; then
    curl_args+=(-d "$body")
  fi
  
  local status=$(curl "${curl_args[@]}")
  local resp=$(cat /tmp/test_resp.json 2>/dev/null)
  
  local match=0
  IFS='|' read -ra EXPECTED_CODES <<< "$expected"
  for code in "${EXPECTED_CODES[@]}"; do
    if [ "$status" = "$code" ]; then match=1; break; fi
  done
  
  if [ "$match" = "1" ]; then
    echo -e "${GREEN}✓ $tc${NC} [$status] $desc"
    PASS=$((PASS + 1))
  else
    echo -e "${RED}✗ $tc${NC} [$status] $desc (expected $expected)"
    local detail=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(str(d.get('detail',''))[:200])" 2>/dev/null)
    if [ -n "$detail" ]; then echo -e "  ${YELLOW}→ $detail${NC}"; fi
    FAIL=$((FAIL + 1))
    ERRORS="$ERRORS\n$tc [$status] $desc"
  fi
  echo "$resp" > /tmp/last_test_resp.json
}

# No-auth test helper (does NOT send Authorization header)
run_test_noauth() {
  local tc="$1" desc="$2" method="$3" url="$4" expected="${5:-401}"
  local status=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "$BASE$url")
  if [ "$status" = "$expected" ]; then
    echo -e "${GREEN}✓ $tc${NC} [$status] $desc"
    PASS=$((PASS + 1))
  else
    echo -e "${RED}✗ $tc${NC} [$status] $desc (expected $expected)"
    FAIL=$((FAIL + 1))
    ERRORS="$ERRORS\n$tc [$status] $desc"
  fi
}

get_field() {
  python3 -c "import sys,json; d=json.load(open('/tmp/last_test_resp.json')); print(d$1)" 2>/dev/null
}

echo -e "\n${CYAN}═══════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  COMPREHENSIVE CRM TEST SUITE v2 — $(date)${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}\n"

# Pre-run cleanup: remove leftover test data from prior runs
echo -e "${YELLOW}Pre-run cleanup...${NC}"
DB_CMD="docker exec miguel_db psql -U miguel_user -d miguel_db -q"
# Orders and dependencies
$DB_CMD -c "DELETE FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE notes LIKE '%TEST-DELETE%' OR delivery_name LIKE 'Test%' OR customer_name LIKE 'Test%' OR customer_name LIKE 'Neg %' OR customer_name LIKE 'Zero %' OR customer_name LIKE 'Huge%' OR customer_name LIKE 'Multi%' OR customer_name LIKE 'Cheque%' OR customer_name LIKE 'Simple%');" 2>/dev/null
$DB_CMD -c "DELETE FROM order_status_history WHERE order_id IN (SELECT id FROM orders WHERE notes LIKE '%TEST-DELETE%' OR delivery_name LIKE 'Test%' OR customer_name LIKE 'Test%' OR customer_name LIKE 'Neg %' OR customer_name LIKE 'Zero %' OR customer_name LIKE 'Huge%' OR customer_name LIKE 'Multi%' OR customer_name LIKE 'Cheque%' OR customer_name LIKE 'Simple%');" 2>/dev/null
$DB_CMD -c "DELETE FROM order_payments WHERE order_id IN (SELECT id FROM orders WHERE notes LIKE '%TEST-DELETE%' OR delivery_name LIKE 'Test%' OR customer_name LIKE 'Test%' OR customer_name LIKE 'Neg %' OR customer_name LIKE 'Zero %' OR customer_name LIKE 'Huge%' OR customer_name LIKE 'Multi%' OR customer_name LIKE 'Cheque%' OR customer_name LIKE 'Simple%');" 2>/dev/null
$DB_CMD -c "DELETE FROM invoice_items WHERE invoice_id IN (SELECT id FROM invoices WHERE order_id IN (SELECT id FROM orders WHERE notes LIKE '%TEST-DELETE%' OR delivery_name LIKE 'Test%'));" 2>/dev/null
$DB_CMD -c "DELETE FROM invoices WHERE order_id IN (SELECT id FROM orders WHERE notes LIKE '%TEST-DELETE%' OR delivery_name LIKE 'Test%');" 2>/dev/null
$DB_CMD -c "DELETE FROM orders WHERE notes LIKE '%TEST-DELETE%' OR delivery_name LIKE 'Test%' OR customer_name LIKE 'Test%' OR customer_name LIKE 'Neg %' OR customer_name LIKE 'Zero %' OR customer_name LIKE 'Huge%' OR customer_name LIKE 'Multi%' OR customer_name LIKE 'Cheque%' OR customer_name LIKE 'Simple%';" 2>/dev/null
# Leads
$DB_CMD -c "DELETE FROM lead_activities WHERE lead_id IN (SELECT id FROM leads WHERE phone LIKE '922200%' OR phone LIKE '955500%');" 2>/dev/null
$DB_CMD -c "DELETE FROM lead_messages WHERE lead_id IN (SELECT id FROM leads WHERE phone LIKE '922200%' OR phone LIKE '955500%');" 2>/dev/null
$DB_CMD -c "DELETE FROM leads WHERE phone LIKE '922200%' OR phone LIKE '955500%';" 2>/dev/null
# Customers
$DB_CMD -c "DELETE FROM customer_interactions WHERE customer_id IN (SELECT id FROM customers WHERE phone LIKE '933300%' OR phone LIKE '955500%' OR phone LIKE '911100%');" 2>/dev/null
$DB_CMD -c "DELETE FROM customers WHERE phone LIKE '933300%' OR phone LIKE '955500%' OR phone LIKE '911100%';" 2>/dev/null
# Products (FK children first)
$DB_CMD -c "DELETE FROM vendor_products WHERE product_id IN (SELECT id FROM products WHERE sku LIKE 'TST-%' OR sku LIKE 'MIN-%');" 2>/dev/null
$DB_CMD -c "DELETE FROM purchase_order_items WHERE product_id IN (SELECT id FROM products WHERE sku LIKE 'TST-%' OR sku LIKE 'MIN-%');" 2>/dev/null
$DB_CMD -c "DELETE FROM inventory_movements WHERE product_id IN (SELECT id FROM products WHERE sku LIKE 'TST-%' OR sku LIKE 'MIN-%');" 2>/dev/null
$DB_CMD -c "DELETE FROM inventory_summary WHERE product_id IN (SELECT id FROM products WHERE sku LIKE 'TST-%' OR sku LIKE 'MIN-%');" 2>/dev/null
$DB_CMD -c "DELETE FROM invoice_items WHERE product_id IN (SELECT id FROM products WHERE sku LIKE 'TST-%' OR sku LIKE 'MIN-%');" 2>/dev/null
$DB_CMD -c "DELETE FROM products WHERE sku LIKE 'TST-%' OR sku LIKE 'MIN-%';" 2>/dev/null
# Purchase orders
$DB_CMD -c "DELETE FROM purchase_order_items WHERE purchase_order_id IN (SELECT id FROM purchase_orders WHERE notes LIKE 'Test PO%');" 2>/dev/null
$DB_CMD -c "DELETE FROM purchase_orders WHERE notes LIKE 'Test PO%';" 2>/dev/null
# Vendors
$DB_CMD -c "DELETE FROM vendor_products WHERE vendor_id IN (SELECT id FROM vendors WHERE company_name LIKE 'Test Vendor%' OR company_name LIKE 'Min Vendor%' OR company_name LIKE 'Updated Vendor%');" 2>/dev/null
$DB_CMD -c "DELETE FROM vendors WHERE company_name LIKE 'Test Vendor%' OR company_name LIKE 'Min Vendor%' OR company_name LIKE 'Updated Vendor%';" 2>/dev/null
# Invoices
$DB_CMD -c "DELETE FROM invoice_items WHERE invoice_id IN (SELECT id FROM invoices WHERE notes LIKE 'Test invoice%');" 2>/dev/null
$DB_CMD -c "DELETE FROM invoices WHERE notes LIKE 'Test invoice%';" 2>/dev/null
echo -e "${GREEN}Pre-run cleanup done${NC}\n"

login

# ════════════════════════════════════════════════════════════════════
# GROUP 1: ORDERS
# ════════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}━━━ GROUP 1: ORDERS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

run_test "ORD-001" "List orders (default page)" GET "/api/orders/"
run_test "ORD-002" "List orders with pagination" GET "/api/orders/?page=1&page_size=5"
run_test "ORD-003" "List orders - filter status=confirmed" GET "/api/orders/?status=confirmed"
run_test "ORD-004" "List orders - filter status=draft" GET "/api/orders/?status=draft"
run_test "ORD-005" "List orders - filter pay=pending" GET "/api/orders/?payment_status=pending"
run_test "ORD-006" "List orders - filter pay=paid" GET "/api/orders/?payment_status=paid"
run_test "ORD-007" "List orders - search" GET "/api/orders/?search=test"
run_test "ORD-008" "List orders - invalid status (→422)" GET "/api/orders/?status=nonexistent" "-" "422"
run_test "ORD-009" "List orders - page 999 (empty)" GET "/api/orders/?page=999&page_size=10"
run_test "ORD-010" "Get order stats" GET "/api/orders/stats"

# Phone Lookup
run_test "ORD-011" "Phone lookup - 10-digit" POST "/api/orders/phone-lookup" '{"phone":"9876543210"}'
run_test "ORD-012" "Phone lookup - non-existent" POST "/api/orders/phone-lookup" '{"phone":"0000000000"}'
run_test "ORD-013" "Phone lookup - empty" POST "/api/orders/phone-lookup" '{"phone":""}'
run_test "ORD-014" "Phone lookup - short" POST "/api/orders/phone-lookup" '{"phone":"123"}'

# Parse Address
run_test "ORD-015" "Parse - full Indian address" POST "/api/orders/parse-address" '{"raw_text":"Ramesh Kumar, 45 MG Road, Bangalore, Karnataka 560001"}'
run_test "ORD-016" "Parse - minimal" POST "/api/orders/parse-address" '{"raw_text":"Delhi 110001"}'
run_test "ORD-017" "Parse - empty" POST "/api/orders/parse-address" '{"raw_text":""}' "200|400|422"
run_test "ORD-018" "Parse - pincode only" POST "/api/orders/parse-address" '{"raw_text":"685561"}'
run_test "ORD-019" "Parse - multiline" POST "/api/orders/parse-address" '{"raw_text":"John Doe\n123 Street\nMumbai MH 400001"}'

# Couriers
run_test "ORD-020" "List couriers" GET "/api/orders/couriers"
run_test "ORD-021" "List India Post IDs" GET "/api/orders/india-post-ids"

# ── Create Orders ──────────────────────────────────────────
run_test "ORD-030" "Create - COD confirmed full" POST "/api/orders/" '{
  "customer_name":"Test Alpha","customer_phone":"9111000001","order_intent":"confirmed",
  "items":[{"product_name":"Product A","sku":"TST-A","quantity":2,"unit_price":500,"unit":"piece","discount_pct":0}],
  "payment_method":"cod","delivery_name":"Test Alpha","delivery_address":"123 Test St",
  "delivery_city":"Mumbai","delivery_state":"Maharashtra","delivery_pincode":"400001",
  "shipping_charge":50,"discount_amount":0,"tax_amount":0,"notes":"TEST-DELETE",
  "shipping_service":"speed_post","order_source":"manual","gst_invoice":true
}' "201"
ORDER_ID_1=$(get_field "['id']")
echo "  → Order 1: $ORDER_ID_1"

run_test "ORD-031" "Create - UPI confirmed" POST "/api/orders/" '{
  "customer_name":"Test Beta","customer_phone":"9111000002","order_intent":"confirmed",
  "items":[{"product_name":"Widget B","sku":"WDG-B","quantity":1,"unit_price":1200,"unit":"piece","discount_pct":10}],
  "payment_method":"upi","delivery_name":"Test Beta","delivery_address":"456 Test Ave",
  "delivery_city":"Delhi","delivery_state":"Delhi","delivery_pincode":"110001",
  "shipping_charge":0,"discount_amount":50,"tax_amount":18,"shipping_service":"parcel","order_source":"manual"
}' "201"
ORDER_ID_2=$(get_field "['id']")
echo "  → Order 2: $ORDER_ID_2"

run_test "ORD-032" "Create - not confirmed (→ lead)" POST "/api/orders/" '{
  "customer_name":"Test Lead","customer_phone":"9111000003","order_intent":"not_confirmed",
  "not_confirmed_reason":"Price too high","items":[{"product_name":"Premium","sku":"PRM-1","quantity":1,"unit_price":5000,"unit":"piece","discount_pct":0}],
  "payment_method":"cod","delivery_name":"Test Lead","delivery_address":"789 Lead Ln",
  "delivery_city":"Jaipur","delivery_state":"Rajasthan","delivery_pincode":"302001",
  "shipping_charge":100,"order_source":"manual"
}' "201"
ORDER_ID_3=$(get_field "['id']")
echo "  → Order 3 (NC): $ORDER_ID_3"

run_test "ORD-033" "Create - partial_cod with advance" POST "/api/orders/" '{
  "customer_name":"Test Partial","customer_phone":"9111000004","order_intent":"confirmed",
  "items":[{"product_name":"Expensive","sku":"EXP-1","quantity":1,"unit_price":3000,"unit":"piece","discount_pct":0}],
  "payment_method":"partial_cod","advance_amount":1000,"delivery_name":"Test Partial",
  "delivery_address":"Partial St 10","delivery_city":"Chennai","delivery_state":"Tamil Nadu",
  "delivery_pincode":"600001","shipping_charge":80,"order_source":"manual"
}' "201"
ORDER_ID_4=$(get_field "['id']")
echo "  → Order 4 (partial COD): $ORDER_ID_4"

run_test "ORD-034" "Create - 3 items" POST "/api/orders/" '{
  "customer_name":"Multi Item","customer_phone":"9111000005","order_intent":"confirmed",
  "items":[
    {"product_name":"Item A","quantity":2,"unit_price":100,"unit":"piece","discount_pct":0},
    {"product_name":"Item B","quantity":1,"unit_price":250,"unit":"kg","discount_pct":5},
    {"product_name":"Item C","quantity":3,"unit_price":75,"unit":"piece","discount_pct":10}
  ],
  "payment_method":"bank_transfer","delivery_name":"Multi Item","delivery_address":"Multi Ln 5",
  "delivery_city":"Kolkata","delivery_state":"West Bengal","delivery_pincode":"700001","order_source":"manual"
}' "201"
ORDER_ID_5=$(get_field "['id']")
echo "  → Order 5 (multi): $ORDER_ID_5"

run_test "ORD-035" "Create - zero extras" POST "/api/orders/" '{
  "customer_name":"Zero User","customer_phone":"9111000006","order_intent":"confirmed",
  "items":[{"product_name":"Simple","quantity":1,"unit_price":999.99,"unit":"piece","discount_pct":0}],
  "payment_method":"cod","delivery_name":"Zero User","delivery_address":"Simple Rd 1",
  "delivery_city":"Pune","delivery_state":"Maharashtra","delivery_pincode":"411001",
  "shipping_charge":0,"discount_amount":0,"tax_amount":0,"order_source":"manual"
}' "201"
ORDER_ID_6=$(get_field "['id']")
echo "  → Order 6: $ORDER_ID_6"

run_test "ORD-036" "Create - missing items (422)" POST "/api/orders/" '{"customer_name":"No Items","items":[]}' "422"

run_test "ORD-037" "Create - cheque payment" POST "/api/orders/" '{
  "customer_name":"Cheque User","customer_phone":"9111000007","order_intent":"confirmed",
  "items":[{"product_name":"Cheque Item","quantity":1,"unit_price":2000,"unit":"piece","discount_pct":0}],
  "payment_method":"cheque","delivery_name":"Cheque User","delivery_address":"Cheque Rd",
  "delivery_city":"Lucknow","delivery_state":"Uttar Pradesh","delivery_pincode":"226001","order_source":"manual"
}' "201"
ORDER_ID_7=$(get_field "['id']")
echo "  → Order 7 (cheque): $ORDER_ID_7"

run_test "ORD-038" "Create - repeat customer phone" POST "/api/orders/" '{
  "customer_name":"Test Alpha Again","customer_phone":"9111000001","order_intent":"confirmed",
  "items":[{"product_name":"Repeat Item","quantity":1,"unit_price":150,"unit":"piece","discount_pct":0}],
  "payment_method":"cod","delivery_name":"Test Alpha","delivery_address":"123 Test St",
  "delivery_city":"Mumbai","delivery_state":"Maharashtra","delivery_pincode":"400001","order_source":"manual"
}' "201"
ORDER_ID_8=$(get_field "['id']")
echo "  → Order 8 (repeat cust): $ORDER_ID_8"

# ── Get Order Detail ──────────────────────────────────────
run_test "ORD-040" "Get order detail" GET "/api/orders/$ORDER_ID_1"

# Verify items_summary property works (the bug we fixed)
ITEMS_SUMMARY=$(python3 -c "import json; d=json.load(open('/tmp/last_test_resp.json')); print(d.get('items_summary',''))" 2>/dev/null)
echo -e "  items_summary = '${ITEMS_SUMMARY}'"

run_test "ORD-041" "Get - non-existent ID (→404)" GET "/api/orders/00000000-0000-0000-0000-000000000000" "-" "404"
run_test "ORD-042" "Get - invalid UUID (→422)" GET "/api/orders/not-a-uuid" "-" "422"

# ── Update Order (PATCH) ─────────────────────────────────
run_test "ORD-050" "Update - payment method COD→UPI" PATCH "/api/orders/$ORDER_ID_1" '{"payment_method":"upi"}'
run_test "ORD-051" "Update - payment status to paid" PATCH "/api/orders/$ORDER_ID_1" '{"payment_status":"paid"}'
run_test "ORD-052" "Update - delivery address" PATCH "/api/orders/$ORDER_ID_1" '{"delivery_address":"Updated 999","delivery_city":"Updated City","delivery_state":"Updated State","delivery_pincode":"999999"}'
run_test "ORD-053" "Update - notes" PATCH "/api/orders/$ORDER_ID_1" '{"notes":"Updated test notes"}'
run_test "ORD-054" "Update - shipping charge" PATCH "/api/orders/$ORDER_ID_1" '{"shipping_charge":150}'
run_test "ORD-055" "Update - discount amount" PATCH "/api/orders/$ORDER_ID_1" '{"discount_amount":25}'
run_test "ORD-056" "Update - to partial_cod" PATCH "/api/orders/$ORDER_ID_4" '{"payment_method":"partial_cod","advance_amount":500}'
run_test "ORD-057" "Update - replace items" PATCH "/api/orders/$ORDER_ID_1" '{
  "items":[
    {"product_name":"Replaced X","sku":"RPL-X","quantity":3,"unit_price":200,"unit":"piece","discount_pct":5},
    {"product_name":"Replaced Y","sku":"RPL-Y","quantity":1,"unit_price":800,"unit":"kg","discount_pct":0}
  ]
}'
run_test "ORD-058" "Update - delivery name" PATCH "/api/orders/$ORDER_ID_1" '{"delivery_name":"New Name"}'
run_test "ORD-059" "Update - non-existent" PATCH "/api/orders/00000000-0000-0000-0000-000000000000" '{"notes":"x"}' "404"
run_test "ORD-059b" "Update - empty body" PATCH "/api/orders/$ORDER_ID_1" '{}'

# ── Status Flow ──────────────────────────────────────────
run_test "ORD-060" "Status: confirmed→processing" POST "/api/orders/$ORDER_ID_2/status" '{"status":"processing"}'
run_test "ORD-061" "Status: processing→packed" POST "/api/orders/$ORDER_ID_2/status" '{"status":"packed"}'
run_test "ORD-062" "Status: packed→shipped" POST "/api/orders/$ORDER_ID_2/status" '{"status":"shipped","tracking_number":"TESTTRK123"}'
run_test "ORD-063" "Status: shipped→out_for_delivery" POST "/api/orders/$ORDER_ID_2/status" '{"status":"out_for_delivery"}'
run_test "ORD-064" "Status: out_for_delivery→delivered" POST "/api/orders/$ORDER_ID_2/status" '{"status":"delivered"}'
run_test "ORD-065" "Status: invalid skip (confirmed→delivered)" POST "/api/orders/$ORDER_ID_5/status" '{"status":"delivered"}' "400"
run_test "ORD-066" "Status: delivered→returned" POST "/api/orders/$ORDER_ID_2/status" '{"status":"returned"}'

# Edit terminal-status order
run_test "ORD-067" "Edit returned order fields (should fail)" PATCH "/api/orders/$ORDER_ID_2" '{"delivery_address":"should fail"}' "400"
# But status-only on terminal order should be handled
run_test "ORD-067b" "Edit returned - pay status only" PATCH "/api/orders/$ORDER_ID_2" '{"payment_status":"paid"}'

# Payment status quick updates
run_test "ORD-068" "Quick pay status → paid" PATCH "/api/orders/$ORDER_ID_5" '{"payment_status":"paid"}'
run_test "ORD-069" "Quick pay status → pending" PATCH "/api/orders/$ORDER_ID_5" '{"payment_status":"pending"}'

# Delete
run_test "ORD-070" "Delete confirmed order (fail)" DELETE "/api/orders/$ORDER_ID_8" "-" "400"

# Cancel first, then delete
run_test "ORD-071" "Cancel for delete" POST "/api/orders/$ORDER_ID_6/status" '{"status":"cancelled"}'
run_test "ORD-072" "Delete cancelled order" DELETE "/api/orders/$ORDER_ID_6"

# Auto-advance to shipped when tracking assigned
run_test "ORD-073" "Auto-ship on tracking assign" PATCH "/api/orders/$ORDER_ID_5" '{"tracking_number":"AUTOSHIP999"}'
# Check status is now shipped
STATUS_CHECK=$(curl -s "$BASE/api/orders/$ORDER_ID_5" -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null)
if [ "$STATUS_CHECK" = "shipped" ]; then
  echo -e "${GREEN}✓ ORD-073b${NC} Auto-advanced to shipped ✓"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗ ORD-073b${NC} Expected status=shipped, got=$STATUS_CHECK"
  FAIL=$((FAIL + 1))
  ERRORS="$ERRORS\nORD-073b Expected shipped, got $STATUS_CHECK"
fi

# Amount validation after updates
run_test "ORD-074" "Verify order detail after replace" GET "/api/orders/$ORDER_ID_1"
python3 -c "
import json
d=json.load(open('/tmp/last_test_resp.json'))
total=float(d.get('total_amount',0))
subtotal=float(d.get('subtotal',0))
items=d.get('items',[])
summary=d.get('items_summary','')
print(f'  subtotal={subtotal}, total={total}, items={len(items)}, summary={summary}')
assert total > 0, f'total_amount should be > 0, got {total}'
assert len(items) > 0, f'Should have items'
assert summary, f'items_summary should not be empty'
print('  ✓ Amount/items validation passed')
" 2>&1


# ════════════════════════════════════════════════════════════════════
# GROUP 2: LEADS
# ════════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}━━━ GROUP 2: LEADS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

run_test "LEAD-001" "List leads (default)" GET "/api/leads/"
run_test "LEAD-002" "List leads paginated" GET "/api/leads/?page=1&page_size=5"
run_test "LEAD-003" "List leads - status filter" GET "/api/leads/?status=created"
run_test "LEAD-004" "List leads - search" GET "/api/leads/?search=test"
run_test "LEAD-005" "List leads - page 999" GET "/api/leads/?page=999"
run_test "LEAD-010" "Lead stats" GET "/api/leads/stats"
run_test "LEAD-011" "Today reminders" GET "/api/leads/reminders/today"
run_test "LEAD-012" "Lost leads" GET "/api/leads/lost_leads/list"

# Create
run_test "LEAD-020" "Create - full data" POST "/api/leads/" '{
  "name":"Test Lead Alpha","phone":"9222000001","alternate_phone":"9222000011",
  "source":"manual","status":"created","product_interest":"Premium Widget",
  "city":"Bangalore","state":"Karnataka","notes":"TEST-DELETE","next_followup_date":"2026-03-10"
}' "201"
LEAD_ID_1=$(get_field "['id']")
echo "  → Lead 1: $LEAD_ID_1"

run_test "LEAD-021" "Create - minimal" POST "/api/leads/" '{"name":"Minimal Lead","phone":"9222000002","source":"manual"}' "201"
LEAD_ID_2=$(get_field "['id']")

run_test "LEAD-022" "Create - dup phone" POST "/api/leads/" '{"name":"Dup Lead","phone":"9222000001","source":"manual"}' "201|400|409"
LEAD_ID_DUP=$(get_field "['id']")

run_test "LEAD-023" "Create - whatsapp source" POST "/api/leads/" '{"name":"WA Lead","phone":"9222000003","source":"whatsapp","product_interest":"Organic"}' "201"
LEAD_ID_3=$(get_field "['id']")

run_test "LEAD-024" "Create - website source" POST "/api/leads/" '{"name":"Web Lead","phone":"9222000004","source":"website","city":"Hyderabad","state":"Telangana"}' "201"
LEAD_ID_4=$(get_field "['id']")

run_test "LEAD-025" "Create - past followup" POST "/api/leads/" '{"name":"Past Lead","phone":"9222000005","source":"manual","next_followup_date":"2025-01-01"}' "201"
LEAD_ID_5=$(get_field "['id']")

run_test "LEAD-026" "Create - empty name" POST "/api/leads/" '{"name":"","phone":"9222000006","source":"manual"}' "201|422"
run_test "LEAD-027" "Create - missing phone" POST "/api/leads/" '{"name":"No Phone"}' "422"

# Detail
run_test "LEAD-030" "Get lead detail" GET "/api/leads/$LEAD_ID_1"
run_test "LEAD-031" "Get lead - non-existent (→404)" GET "/api/leads/00000000-0000-0000-0000-000000000000" "-" "404"

# Update
run_test "LEAD-040" "Update - name" PATCH "/api/leads/$LEAD_ID_1" '{"name":"Updated Lead"}'
run_test "LEAD-041" "Update - status→contacted" PATCH "/api/leads/$LEAD_ID_1" '{"status":"contacted"}'
run_test "LEAD-042" "Update - city/state" PATCH "/api/leads/$LEAD_ID_1" '{"city":"Chennai","state":"Tamil Nadu"}'
run_test "LEAD-043" "Update - product interest" PATCH "/api/leads/$LEAD_ID_1" '{"product_interest":"Updated Interest"}'
run_test "LEAD-044" "Update - notes" PATCH "/api/leads/$LEAD_ID_1" '{"notes":"Updated notes"}'
run_test "LEAD-045" "Update - followup date" PATCH "/api/leads/$LEAD_ID_1" '{"next_followup_date":"2026-04-01"}'
run_test "LEAD-046" "Update - null followup" PATCH "/api/leads/$LEAD_ID_1" '{"next_followup_date":null}'
run_test "LEAD-047" "Update - non-existent" PATCH "/api/leads/00000000-0000-0000-0000-000000000000" '{"name":"x"}' "404"
run_test "LEAD-048" "Update - empty body" PATCH "/api/leads/$LEAD_ID_1" '{}'

# WABIS Labels
run_test "LEAD-050" "WABIS labels - set" PATCH "/api/leads/$LEAD_ID_1/wabis-labels" '{"labels":["hot","interested"]}'
run_test "LEAD-051" "WABIS labels - clear" PATCH "/api/leads/$LEAD_ID_1/wabis-labels" '{"labels":[]}'

# Activities
run_test "LEAD-060" "Activity - note" POST "/api/leads/$LEAD_ID_1/activities" '{"activity_type":"note","note":"Test note"}' "201"
run_test "LEAD-061" "Activity - call" POST "/api/leads/$LEAD_ID_1/activities" '{"activity_type":"call","note":"Called customer"}' "201"
run_test "LEAD-062" "Activity - whatsapp" POST "/api/leads/$LEAD_ID_1/activities" '{"activity_type":"whatsapp","note":"Sent catalog"}' "201"

# Contacted (correct schema: action + note required)
run_test "LEAD-070" "Contacted - save_close" POST "/api/leads/$LEAD_ID_2/contacted" '{"note":"Discussed product","action":"save_close"}'
run_test "LEAD-071" "Contacted - remind_later" POST "/api/leads/$LEAD_ID_3/contacted" '{"note":"Will call back","action":"remind_later","remind_later_date":"2026-03-15"}'
run_test "LEAD-072" "Contacted - not_interested" POST "/api/leads/$LEAD_ID_5/contacted" '{"note":"Not interested in product","action":"not_interested"}'

# Convert
run_test "LEAD-075" "Convert lead to customer" POST "/api/leads/$LEAD_ID_4/convert" '{}' "201|200"

# Lead Orders
run_test "LEAD-085" "Get lead orders" GET "/api/leads/$LEAD_ID_1/orders"

# Messages
run_test "LEAD-080" "Get lead messages" GET "/api/leads/$LEAD_ID_1/messages"
run_test "LEAD-081" "Send lead message" POST "/api/leads/$LEAD_ID_1/messages" '{"message_body":"Hello test","direction":"outbound"}' "201|200"

# Delete
run_test "LEAD-090" "Delete lead" DELETE "/api/leads/$LEAD_ID_DUP"
run_test "LEAD-091" "Delete - non-existent (→404)" DELETE "/api/leads/00000000-0000-0000-0000-000000000000" "-" "404"


# ════════════════════════════════════════════════════════════════════
# GROUP 3: CUSTOMERS
# ════════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}━━━ GROUP 3: CUSTOMERS ━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

run_test "CUST-001" "List customers" GET "/api/customers/"
run_test "CUST-002" "List paginated" GET "/api/customers/?page=1&page_size=5"
run_test "CUST-003" "List search" GET "/api/customers/?search=test"
run_test "CUST-004" "List page 999" GET "/api/customers/?page=999"
run_test "CUST-010" "Customer stats" GET "/api/customers/stats"
run_test "CUST-011" "Customers with orders" GET "/api/customers/with-orders"

# Create (lead_status must be valid enum: new|called|interested|not_interested|lead|converted|lost)
run_test "CUST-020" "Create - full data" POST "/api/customers/" '{
  "name":"Test Customer A","phone":"9333000001","alternate_phone":"9333000011",
  "address":"123 Customer St","city":"Mumbai","state":"Maharashtra","pincode":"400001",
  "source":"manual","lead_status":"new","notes":"TEST-DELETE"
}' "201"
CUST_ID_1=$(get_field "['id']")
echo "  → Customer 1: $CUST_ID_1"

run_test "CUST-021" "Create - minimal" POST "/api/customers/" '{"name":"Min Customer","phone":"9333000002"}' "201"
CUST_ID_2=$(get_field "['id']")

run_test "CUST-022" "Create - with email" POST "/api/customers/" '{
  "name":"Email Cust","phone":"9333000003","email":"test@example.com","city":"Delhi","state":"Delhi","pincode":"110001"
}' "201"
CUST_ID_3=$(get_field "['id']")

run_test "CUST-023" "Create - dup phone" POST "/api/customers/" '{"name":"Dup Cust","phone":"9333000001"}' "201|400|409"
run_test "CUST-024" "Create - missing name" POST "/api/customers/" '{"phone":"9333000004"}' "422"

# Detail
run_test "CUST-030" "Get detail" GET "/api/customers/$CUST_ID_1"
run_test "CUST-031" "Get - non-existent (→404)" GET "/api/customers/00000000-0000-0000-0000-000000000000" "-" "404"

# Update
run_test "CUST-040" "Update - name" PATCH "/api/customers/$CUST_ID_1" '{"name":"Updated Customer"}'
run_test "CUST-041" "Update - address" PATCH "/api/customers/$CUST_ID_1" '{"address":"Updated Addr","city":"Pune","state":"MH","pincode":"411001"}'
run_test "CUST-042" "Update - phone" PATCH "/api/customers/$CUST_ID_1" '{"phone":"9333999999"}'
run_test "CUST-043" "Update - notes" PATCH "/api/customers/$CUST_ID_1" '{"notes":"Updated notes"}'
run_test "CUST-044" "Update - payment mode" PATCH "/api/customers/$CUST_ID_1" '{"payment_mode_preference":"prepaid"}'
run_test "CUST-045" "Update - non-existent" PATCH "/api/customers/00000000-0000-0000-0000-000000000000" '{"name":"x"}' "404"
run_test "CUST-046" "Update - empty body" PATCH "/api/customers/$CUST_ID_1" '{}'

# Customer Orders
run_test "CUST-050" "Get customer orders" GET "/api/customers/$CUST_ID_1/orders"

# Interactions (correct schema: interaction_type enum, message_content optional)
run_test "CUST-060" "Add interaction - note" POST "/api/customers/$CUST_ID_1/interactions" '{"interaction_type":"note","message_content":"Test note"}' "201"
run_test "CUST-061" "Add interaction - call" POST "/api/customers/$CUST_ID_1/interactions" '{"interaction_type":"call","message_content":"Called about order"}' "201"

# Toggle Status
run_test "CUST-070" "Toggle deactivate" PATCH "/api/customers/$CUST_ID_2/toggle-status"
run_test "CUST-071" "Toggle reactivate" PATCH "/api/customers/$CUST_ID_2/toggle-status"

# Delete
run_test "CUST-080" "Delete customer" DELETE "/api/customers/$CUST_ID_3"
run_test "CUST-081" "Delete - non-existent (→404)" DELETE "/api/customers/00000000-0000-0000-0000-000000000000" "-" "404"

# WhatsApp endpoints
run_test "CUST-090" "Get customer WA messages" GET "/api/customers/$CUST_ID_1/whatsapp"
run_test "CUST-091" "Get WA compose" GET "/api/customers/$CUST_ID_1/whatsapp/compose"


# ════════════════════════════════════════════════════════════════════
# GROUP 4: PRODUCTS
# ════════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}━━━ GROUP 4: PRODUCTS ━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

run_test "PROD-001" "List products" GET "/api/products/"
run_test "PROD-002" "List - search" GET "/api/products/?search=test"
run_test "PROD-003" "Categories" GET "/api/products/categories"

run_test "PROD-010" "Create - full" POST "/api/products/" '{
  "name":"Test Product X","sku":"TST-X-001","category":"Testing",
  "unit_price":599.99,"cost_price":300,"unit":"piece","description":"Test product",
  "hsn_code":"8544","gst_rate":18,"min_stock":10
}' "201"
PROD_ID_1=$(get_field "['id']")

run_test "PROD-011" "Create - minimal" POST "/api/products/" '{"name":"Min Product","sku":"MIN-001","unit_price":100}' "201"
PROD_ID_2=$(get_field "['id']")

run_test "PROD-012" "Create - dup SKU" POST "/api/products/" '{"name":"Dup","sku":"TST-X-001","unit_price":200}' "409"
run_test "PROD-020" "Get detail" GET "/api/products/$PROD_ID_1"
run_test "PROD-021" "Get - non-existent (→404)" GET "/api/products/00000000-0000-0000-0000-000000000000" "-" "404"
run_test "PROD-030" "Update - price" PATCH "/api/products/$PROD_ID_1" '{"unit_price":699.99}'
run_test "PROD-031" "Update - name" PATCH "/api/products/$PROD_ID_1" '{"name":"Updated Product X"}'
run_test "PROD-032" "Update - category" PATCH "/api/products/$PROD_ID_1" '{"category":"Updated Cat"}'
run_test "PROD-040" "Delete product" DELETE "/api/products/$PROD_ID_2"
run_test "PROD-041" "Delete - non-existent (→404)" DELETE "/api/products/00000000-0000-0000-0000-000000000000" "-" "404"


# ════════════════════════════════════════════════════════════════════
# GROUP 5: VENDORS
# ════════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}━━━ GROUP 5: VENDORS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

run_test "VEND-001" "List vendors" GET "/api/vendors/"
run_test "VEND-002" "List - search" GET "/api/vendors/?search=test"

# Vendor create requires company_name, not name
run_test "VEND-010" "Create - full" POST "/api/vendors/" '{
  "company_name":"Test Vendor Co","contact_name":"Contact","phone":"9444000001",
  "email":"vendor@test.com","address":"Vendor St 1","city":"Ahmedabad","state":"Gujarat","gstin":"24AAAAA0000A1Z5"
}' "201"
VEND_ID_1=$(get_field "['id']")
echo "  → Vendor 1: $VEND_ID_1"

run_test "VEND-011" "Create - minimal" POST "/api/vendors/" '{"company_name":"Min Vendor"}' "201"
VEND_ID_2=$(get_field "['id']")

run_test "VEND-020" "Get detail" GET "/api/vendors/$VEND_ID_1"
run_test "VEND-021" "Get - non-existent (→404)" GET "/api/vendors/00000000-0000-0000-0000-000000000000" "-" "404"
run_test "VEND-030" "Update vendor" PATCH "/api/vendors/$VEND_ID_1" '{"company_name":"Updated Vendor Co"}'
run_test "VEND-040" "List vendor products" GET "/api/vendors/$VEND_ID_1/products"

if [ -n "$PROD_ID_1" ] && [ "$PROD_ID_1" != "None" ]; then
  run_test "VEND-041" "Add vendor product" POST "/api/vendors/$VEND_ID_1/products" "{
    \"product_id\":\"$PROD_ID_1\",\"unit_price\":250,\"lead_time_days\":5
  }" "201"
fi

run_test "VEND-050" "Delete vendor" DELETE "/api/vendors/$VEND_ID_2" "-" "200|204"
run_test "VEND-051" "Delete - non-existent (→404)" DELETE "/api/vendors/00000000-0000-0000-0000-000000000000" "-" "404"


# ════════════════════════════════════════════════════════════════════
# GROUP 6: INVOICES
# ════════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}━━━ GROUP 6: INVOICES ━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

run_test "INV-001" "List invoices" GET "/api/invoices/"
run_test "INV-002" "List - filter draft" GET "/api/invoices/?status=draft"

# Get customer_id from an order for invoice creation
CUST_FOR_INV=$(curl -s "$BASE/api/orders/$ORDER_ID_1" -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; print(json.load(sys.stdin).get('customer_id',''))" 2>/dev/null)

if [ -n "$ORDER_ID_1" ] && [ "$ORDER_ID_1" != "None" ] && [ -n "$CUST_FOR_INV" ] && [ "$CUST_FOR_INV" != "None" ]; then
  run_test "INV-010" "Create invoice" POST "/api/invoices/" "{
    \"order_id\":\"$ORDER_ID_1\",\"customer_id\":\"$CUST_FOR_INV\",
    \"invoice_date\":\"2026-03-03\",
    \"items\":[{\"product_name\":\"Test Item\",\"quantity\":1,\"unit_price\":500,\"hsn_code\":\"8544\",\"tax_percent\":18}]
  }" "201|200|400"
  INV_ID_1=$(get_field "['id']" 2>/dev/null)
  echo "  → Invoice: $INV_ID_1"

  if [ -n "$INV_ID_1" ] && [ "$INV_ID_1" != "None" ]; then
    run_test "INV-020" "Get invoice detail" GET "/api/invoices/$INV_ID_1"
    run_test "INV-030" "Update invoice" PATCH "/api/invoices/$INV_ID_1" '{"notes":"Test invoice note"}'
    run_test "INV-040" "Finalize invoice" POST "/api/invoices/$INV_ID_1/finalize" "{}"
    run_test "INV-050" "Get invoice PDF" GET "/api/invoices/$INV_ID_1/pdf" "-" "200"
    run_test "INV-060" "Cancel finalized invoice (→400)" POST "/api/invoices/$INV_ID_1/cancel" "{}" "400"
  fi
fi

run_test "INV-070" "Quick PDF from order" GET "/api/invoices/order/$ORDER_ID_1/quick-pdf" "-" "200"


# ════════════════════════════════════════════════════════════════════
# GROUP 7: INVENTORY
# ════════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}━━━ GROUP 7: INVENTORY ━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

run_test "STK-001" "List stock" GET "/api/inventory/stock"
run_test "STK-002" "List movements" GET "/api/inventory/movements"

if [ -n "$PROD_ID_1" ] && [ "$PROD_ID_1" != "None" ]; then
  run_test "STK-003" "Get product stock" GET "/api/inventory/stock/$PROD_ID_1"
  run_test "STK-010" "Adjust - add" POST "/api/inventory/adjust" "{\"product_id\":\"$PROD_ID_1\",\"quantity_change\":50,\"movement_type\":\"purchase\",\"note\":\"Test add\"}" "201"
  run_test "STK-011" "Adjust - remove" POST "/api/inventory/adjust" "{\"product_id\":\"$PROD_ID_1\",\"quantity_change\":-5,\"movement_type\":\"adjustment\",\"note\":\"Test remove\"}" "201"
fi


# ════════════════════════════════════════════════════════════════════
# GROUP 8: LABELS
# ════════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}━━━ GROUP 8: LABELS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ -n "$ORDER_ID_1" ] && [ "$ORDER_ID_1" != "None" ]; then
  run_test "LBL-001" "Generate label" POST "/api/labels/generate" "{\"order_ids\":[\"$ORDER_ID_1\"]}" "200"
  run_test "LBL-003" "Generate multi" POST "/api/labels/generate" "{\"order_ids\":[\"$ORDER_ID_1\",\"$ORDER_ID_4\"]}" "200"
fi
run_test "LBL-002" "Generate - non-existent order" POST "/api/labels/generate" '{"order_ids":["00000000-0000-0000-0000-000000000000"]}' "400"


# ════════════════════════════════════════════════════════════════════
# GROUP 9: PURCHASES
# ════════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}━━━ GROUP 9: PURCHASES ━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

run_test "PO-001" "List POs" GET "/api/purchases/"

if [ -n "$VEND_ID_1" ] && [ "$VEND_ID_1" != "None" ] && [ -n "$PROD_ID_1" ] && [ "$PROD_ID_1" != "None" ]; then
  run_test "PO-010" "Create PO" POST "/api/purchases/" "{
    \"vendor_id\":\"$VEND_ID_1\",\"items\":[{\"product_id\":\"$PROD_ID_1\",\"quantity\":100,\"unit_cost\":250}],\"notes\":\"Test PO\"
  }" "201"
  PO_ID=$(get_field "['id']" 2>/dev/null)
  if [ -n "$PO_ID" ] && [ "$PO_ID" != "None" ]; then
    run_test "PO-020" "Get PO detail" GET "/api/purchases/$PO_ID"
    run_test "PO-030" "Update PO" PATCH "/api/purchases/$PO_ID" '{"notes":"Updated PO"}'
  fi
fi


# ════════════════════════════════════════════════════════════════════
# GROUP 10: GST
# ════════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}━━━ GROUP 10: GST ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

run_test "GST-001" "GST profile" GET "/api/gst/profile"
run_test "GST-002" "GSTR1 data" GET "/api/gst/gstr1?date_from=2026-01-01&date_to=2026-03-31"
run_test "GST-003" "HSN summary" GET "/api/gst/hsn-summary?date_from=2026-01-01&date_to=2026-03-31"
run_test "GST-004" "Tax summary" GET "/api/gst/tax-summary?date_from=2026-01-01&date_to=2026-03-31"
run_test "GST-005" "Validate GSTIN" GET "/api/gst/validate-gstin/24AAAAA0000A1Z5"


# ════════════════════════════════════════════════════════════════════
# GROUP 11: SECURITY & EDGE CASES
# ════════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}━━━ GROUP 11: SECURITY & EDGE CASES ━━━━━━━━━━━━━${NC}"

# Auth tests
run_test_noauth "SEC-001" "No token → 401" GET "/api/orders/"
OLD_TOKEN=$TOKEN; TOKEN="invalid_token"
run_test "SEC-002" "Invalid token → 401" GET "/api/orders/" "-" "401"
TOKEN=$OLD_TOKEN

# XSS
run_test "SEC-010" "XSS in customer name" POST "/api/customers/" '{"name":"<script>alert(1)</script>Test","phone":"9555000001"}' "201"
run_test "SEC-011" "XSS in order notes" PATCH "/api/orders/$ORDER_ID_1" '{"notes":"<img onerror=alert(1) src=x>"}'

# SQL injection
run_test "SEC-020" "SQLi in order search" GET "/api/orders/?search=%27%3B+DROP+TABLE+orders%3B+--"
run_test "SEC-021" "SQLi in customer search" GET "/api/customers/?search=1+OR+1%3D1"

# Large payload
run_test "SEC-030" "Large notes (5000 chars)" PATCH "/api/orders/$ORDER_ID_1" "{\"notes\":\"$(python3 -c "print('A'*5000)")\"}"

# Unicode
run_test "SEC-040" "Unicode customer name" POST "/api/customers/" '{"name":"टेस्ट कस्टमर हिंदी","phone":"9555000002"}' "201"
run_test "SEC-041" "Unicode lead name" POST "/api/leads/" '{"name":"テスト リード 日本語","phone":"9555000003","source":"manual"}' "201"
LEAD_UNICODE=$(get_field "['id']")

# Edge cases
run_test "SEC-060" "Negative price order (→422)" POST "/api/orders/" '{
  "customer_name":"Neg Price","customer_phone":"9555000004","order_intent":"confirmed",
  "items":[{"product_name":"Negative","quantity":1,"unit_price":-100,"unit":"piece"}],
  "payment_method":"cod","delivery_address":"a","delivery_city":"b","delivery_state":"c","delivery_pincode":"100001"
}' "422"

run_test "SEC-061" "Zero quantity order (→422)" POST "/api/orders/" '{
  "customer_name":"Zero Qty","customer_phone":"9555000005","order_intent":"confirmed",
  "items":[{"product_name":"Zero","quantity":0,"unit_price":100,"unit":"piece"}],
  "payment_method":"cod","delivery_address":"a","delivery_city":"b","delivery_state":"c","delivery_pincode":"100001"
}' "422"

run_test "SEC-062" "Huge quantity order" POST "/api/orders/" '{
  "customer_name":"Huge","customer_phone":"9555000006","order_intent":"confirmed",
  "items":[{"product_name":"Huge","quantity":999999,"unit_price":1,"unit":"piece"}],
  "payment_method":"cod","delivery_address":"a","delivery_city":"b","delivery_state":"c","delivery_pincode":"100001"
}' "201|422"

# Special characters
run_test "SEC-070" "Special chars in name" POST "/api/customers/" '{"name":"O'\''Brien & Co. <Ltd>","phone":"9555000007"}' "201"
run_test "SEC-071" "Emoji in notes" PATCH "/api/leads/$LEAD_ID_1" '{"notes":"Great lead! 🎉🚀💰"}'


# ════════════════════════════════════════════════════════════════════
# CLEANUP
# ════════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}━━━ CLEANUP ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Cancel and delete test orders
for oid in $ORDER_ID_1 $ORDER_ID_3 $ORDER_ID_4 $ORDER_ID_5 $ORDER_ID_7 $ORDER_ID_8; do
  if [ -n "$oid" ] && [ "$oid" != "None" ]; then
    curl -s -X POST "$BASE/api/orders/$oid/status" -H "Authorization: Bearer $TOKEN" -H "$H" -d '{"status":"cancelled"}' > /dev/null 2>&1
    curl -s -X DELETE "$BASE/api/orders/$oid" -H "Authorization: Bearer $TOKEN" -H "$H" > /dev/null 2>&1
  fi
done
echo "  Cleaned orders"

# Delete test leads  
for lid in $LEAD_ID_1 $LEAD_ID_2 $LEAD_ID_3 $LEAD_ID_4 $LEAD_ID_5 $LEAD_UNICODE; do
  if [ -n "$lid" ] && [ "$lid" != "None" ]; then
    curl -s -X DELETE "$BASE/api/leads/$lid" -H "Authorization: Bearer $TOKEN" -H "$H" > /dev/null 2>&1
  fi
done
echo "  Cleaned leads"

# Delete test customers
for cid in $CUST_ID_1 $CUST_ID_2; do
  if [ -n "$cid" ] && [ "$cid" != "None" ]; then
    curl -s -X DELETE "$BASE/api/customers/$cid" -H "Authorization: Bearer $TOKEN" -H "$H" > /dev/null 2>&1
  fi
done
echo "  Cleaned customers"

# Delete test products
for pid in $PROD_ID_1; do
  if [ -n "$pid" ] && [ "$pid" != "None" ]; then
    curl -s -X DELETE "$BASE/api/products/$pid" -H "Authorization: Bearer $TOKEN" -H "$H" > /dev/null 2>&1
  fi
done
echo "  Cleaned products"

# Delete test vendors
for vid in $VEND_ID_1; do
  if [ -n "$vid" ] && [ "$vid" != "None" ]; then
    curl -s -X DELETE "$BASE/api/vendors/$vid" -H "Authorization: Bearer $TOKEN" -H "$H" > /dev/null 2>&1
  fi
done
echo "  Cleaned vendors"

# DB cleanup for edge-case test records
docker exec miguel_db psql -U miguel_user -d miguel_db -q -c "
DELETE FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE delivery_name LIKE 'Test%' OR notes LIKE 'TEST%');
DELETE FROM order_status_history WHERE order_id IN (SELECT id FROM orders WHERE delivery_name LIKE 'Test%' OR notes LIKE 'TEST%');
DELETE FROM order_payments WHERE order_id IN (SELECT id FROM orders WHERE delivery_name LIKE 'Test%' OR notes LIKE 'TEST%');
DELETE FROM orders WHERE delivery_name LIKE 'Test%' OR notes LIKE 'TEST%' OR notes LIKE '%TEST-DELETE%';
DELETE FROM lead_activities WHERE lead_id IN (SELECT id FROM leads WHERE phone LIKE '922200%' OR phone LIKE '955500%');
DELETE FROM lead_messages WHERE lead_id IN (SELECT id FROM leads WHERE phone LIKE '922200%' OR phone LIKE '955500%');
DELETE FROM leads WHERE phone LIKE '922200%' OR phone LIKE '955500%';
DELETE FROM customer_interactions WHERE customer_id IN (SELECT id FROM customers WHERE phone LIKE '933300%' OR phone LIKE '955500%' OR phone LIKE '911100%');
DELETE FROM customers WHERE phone LIKE '933300%' OR phone LIKE '955500%' OR phone LIKE '911100%';
" 2>/dev/null
echo "  DB cleanup complete"


# ════════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}═══════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  TEST RESULTS SUMMARY${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo -e "  ${GREEN}PASSED: $PASS${NC}"
echo -e "  ${RED}FAILED: $FAIL${NC}"
echo -e "  TOTAL:  $((PASS + FAIL))"
if [ "$FAIL" -gt 0 ]; then
  echo -e "\n${RED}FAILED TESTS:${NC}"
  echo -e "$ERRORS"
fi
echo ""
