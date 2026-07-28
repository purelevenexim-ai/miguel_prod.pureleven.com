#!/usr/bin/env python3
"""
Test suite for Order Payment Logic & Customer Name Sync.
Tests:
  1. Payment method → auto-derive payment_status (no manual pay status needed)
  2. COD → full amount_due, zero amount_paid, status=pending
  3. Partial COD → advance_amount sets amount_paid, cod_amount = total - advance
  4. UPI/Bank Transfer → status=paid, amount_paid=total, amount_due=0
  5. Changing payment method updates amounts correctly
  6. Editing advance_amount on partial_cod recalculates cod_amount
  7. Customer name change reflects in order's customer_name
  8. Product page: active, inactive, discontinued filters
"""
import json
import sys
import urllib.request
import urllib.error
import time

BASE = "http://localhost:8000"

passed = 0
failed = 0
errors = []

def req(method, path, body=None, token=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            body_text = e.read()
            return e.code, json.loads(body_text)
        except:
            return e.code, {"detail": str(e)}

def test(name, condition, msg=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        errors.append(f"{name}: {msg}")
        print(f"  ❌ {name} — {msg}")

# ─── Login ────────────────────────────────────────────────────
print("=== LOGIN ===")
status, resp = req("POST", "/tenant/login", {
    "slug": "purelevenexim",
    "email": "admin@purelevenexim.com",
    "password": "test1234",
})
if status != 200:
    print(f"  ❌ Login failed ({status}): {resp}")
    sys.exit(1)
TOKEN = resp["access_token"]
print(f"  ✅ Logged in as {resp['role']}")

# ─── Setup: get a customer ───────────────────────────────────
print("\n=== SETUP ===")
status, resp = req("GET", "/api/customers/?page_size=5", token=TOKEN)
if status != 200 or not resp.get("data"):
    print(f"  ❌ No customers found ({status})")
    sys.exit(1)
CUSTOMER = resp["data"][0]
CUSTOMER_ID = CUSTOMER["id"]
ORIGINAL_NAME = CUSTOMER["name"]
print(f"  Customer: {ORIGINAL_NAME} (id={CUSTOMER_ID[:8]}…)")

# ═════════════════════════════════════════════════════════════
# TEST GROUP 1: COD Payment Method
# ═════════════════════════════════════════════════════════════
print("\n=== GROUP 1: COD Orders ===")

status, order = req("POST", "/api/orders/", {
    "customer_id": CUSTOMER_ID,
    "items": [{"product_name": "Test COD Item", "quantity": "2", "unit_price": "500"}],
    "payment_method": "cod",
    "delivery_city": "Delhi",
    "delivery_state": "Delhi",
    "delivery_pincode": "110001",
    "customer_name": ORIGINAL_NAME,
    "customer_phone": CUSTOMER.get("phone", "9999999999"),
}, TOKEN)
test("T1.1 Create COD order", status == 201, f"status={status}, resp={order}")
if status == 201:
    COD_ORDER_ID = order["id"]
    test("T1.2 COD → payment_status=pending", order["payment_status"] == "pending",
         f"got {order['payment_status']}")
    test("T1.3 COD → amount_paid=0", float(order["amount_paid"]) == 0,
         f"got {order['amount_paid']}")
    test("T1.4 COD → amount_due=total", float(order["amount_due"]) == float(order["total_amount"]),
         f"due={order['amount_due']} vs total={order['total_amount']}")
    test("T1.5 COD → advance_amount=0", float(order.get("advance_amount", 0)) == 0,
         f"got {order.get('advance_amount')}")

# ═════════════════════════════════════════════════════════════
# TEST GROUP 2: Partial COD Payment Method
# ═════════════════════════════════════════════════════════════
print("\n=== GROUP 2: Partial COD Orders ===")

status, order = req("POST", "/api/orders/", {
    "customer_id": CUSTOMER_ID,
    "items": [
        {"product_name": "Kerala Cardamom 8mm", "quantity": "1", "unit_price": "750"},
        {"product_name": "Clove 100", "quantity": "1", "unit_price": "350"},
    ],
    "payment_method": "partial_cod",
    "advance_amount": "100",
    "delivery_city": "Mumbai",
    "delivery_state": "Maharashtra",
    "delivery_pincode": "400001",
    "customer_name": ORIGINAL_NAME,
    "customer_phone": CUSTOMER.get("phone", "9999999999"),
}, TOKEN)
test("T2.1 Create Partial COD order", status == 201, f"status={status}")
if status == 201:
    PCOD_ORDER_ID = order["id"]
    total = float(order["total_amount"])
    test("T2.2 Partial COD → total=1100", total == 1100, f"got {total}")
    test("T2.3 Partial COD → payment_status=partial", order["payment_status"] == "partial",
         f"got {order['payment_status']}")
    test("T2.4 Partial COD → amount_paid=advance(100)", float(order["amount_paid"]) == 100,
         f"got {order['amount_paid']}")
    test("T2.5 Partial COD → cod_amount=1000", float(order.get("cod_amount", 0)) == 1000,
         f"got {order.get('cod_amount')}")
    test("T2.6 Partial COD → advance_amount=100", float(order.get("advance_amount", 0)) == 100,
         f"got {order.get('advance_amount')}")

    # Update advance from 100 to 200
    print("\n  --- Update advance 100 → 200 ---")
    s2, r2 = req("PATCH", f"/api/orders/{PCOD_ORDER_ID}", {
        "advance_amount": 200,
    }, TOKEN)
    test("T2.7 Update advance_amount", s2 == 200, f"status={s2}, resp={r2}")
    if s2 == 200:
        test("T2.8 Updated advance=200", float(r2.get("advance_amount", 0)) == 200,
             f"got {r2.get('advance_amount')}")
        test("T2.9 Updated cod_amount=900", float(r2.get("cod_amount", 0)) == 900,
             f"got {r2.get('cod_amount')}")
        test("T2.10 Updated amount_paid=200", float(r2.get("amount_paid", 0)) == 200,
             f"got {r2.get('amount_paid')}")

# ═════════════════════════════════════════════════════════════
# TEST GROUP 3: Prepaid (UPI) Payment Method
# ═════════════════════════════════════════════════════════════
print("\n=== GROUP 3: UPI/Prepaid Orders ===")

status, order = req("POST", "/api/orders/", {
    "customer_id": CUSTOMER_ID,
    "items": [{"product_name": "Test UPI Item", "quantity": "1", "unit_price": "800"}],
    "payment_method": "upi",
    "delivery_city": "Bangalore",
    "delivery_state": "Karnataka",
    "delivery_pincode": "560001",
    "customer_name": ORIGINAL_NAME,
    "customer_phone": CUSTOMER.get("phone", "9999999999"),
}, TOKEN)
test("T3.1 Create UPI order", status == 201, f"status={status}")
if status == 201:
    UPI_ORDER_ID = order["id"]
    test("T3.2 UPI → payment_status=paid", order["payment_status"] == "paid",
         f"got {order['payment_status']}")
    test("T3.3 UPI → amount_paid=total", float(order["amount_paid"]) == float(order["total_amount"]),
         f"paid={order['amount_paid']} vs total={order['total_amount']}")
    test("T3.4 UPI → amount_due=0", float(order["amount_due"]) == 0,
         f"got {order['amount_due']}")

# ═════════════════════════════════════════════════════════════
# TEST GROUP 4: Bank Transfer Payment Method
# ═════════════════════════════════════════════════════════════
print("\n=== GROUP 4: Bank Transfer Orders ===")

status, order = req("POST", "/api/orders/", {
    "customer_id": CUSTOMER_ID,
    "items": [{"product_name": "Test Bank Item", "quantity": "1", "unit_price": "1500"}],
    "payment_method": "bank_transfer",
    "delivery_city": "Chennai",
    "delivery_state": "Tamil Nadu",
    "delivery_pincode": "600001",
    "customer_name": ORIGINAL_NAME,
    "customer_phone": CUSTOMER.get("phone", "9999999999"),
}, TOKEN)
test("T4.1 Create bank_transfer order", status == 201, f"status={status}")
if status == 201:
    BT_ORDER_ID = order["id"]
    test("T4.2 bank_transfer → payment_status=paid", order["payment_status"] == "paid",
         f"got {order['payment_status']}")
    test("T4.3 bank_transfer → amount_paid=total", float(order["amount_paid"]) == float(order["total_amount"]),
         f"paid={order['amount_paid']} vs total={order['total_amount']}")

# ═════════════════════════════════════════════════════════════
# TEST GROUP 5: Change payment method on existing order
# ═════════════════════════════════════════════════════════════
print("\n=== GROUP 5: Change Payment Method ===")

if 'COD_ORDER_ID' in dir() or 'COD_ORDER_ID' in globals():
    # Change COD → UPI (should auto-mark as paid)
    s, r = req("PATCH", f"/api/orders/{COD_ORDER_ID}", {
        "payment_method": "upi",
    }, TOKEN)
    test("T5.1 COD→UPI update", s == 200, f"status={s}")
    if s == 200:
        test("T5.2 COD→UPI → status=paid", r["payment_status"] == "paid",
             f"got {r['payment_status']}")
        test("T5.3 COD→UPI → amount_paid=total", float(r["amount_paid"]) == float(r["total_amount"]),
             f"paid={r['amount_paid']} vs total={r['total_amount']}")
        test("T5.4 COD→UPI → amount_due=0", float(r["amount_due"]) == 0,
             f"got {r['amount_due']}")

    # Change back to COD
    s, r = req("PATCH", f"/api/orders/{COD_ORDER_ID}", {
        "payment_method": "cod",
    }, TOKEN)
    test("T5.5 UPI→COD update", s == 200, f"status={s}")

    # Change to partial_cod with advance
    s, r = req("PATCH", f"/api/orders/{COD_ORDER_ID}", {
        "payment_method": "partial_cod",
        "advance_amount": 300,
    }, TOKEN)
    test("T5.6 COD→Partial COD update", s == 200, f"status={s}")
    if s == 200:
        test("T5.7 → payment_status=partial", r["payment_status"] == "partial",
             f"got {r['payment_status']}")
        test("T5.8 → advance_amount=300", float(r.get("advance_amount", 0)) == 300,
             f"got {r.get('advance_amount')}")

# ═════════════════════════════════════════════════════════════
# TEST GROUP 6: Edit items → recalculate totals + cod_amount
# ═════════════════════════════════════════════════════════════
print("\n=== GROUP 6: Edit Items Recalculation ===")

if 'PCOD_ORDER_ID' in dir() or 'PCOD_ORDER_ID' in globals():
    # Edit items on partial_cod order — should recalculate totals
    s, r = req("PATCH", f"/api/orders/{PCOD_ORDER_ID}", {
        "items": [
            {"product_name": "Kerala Cardamom 8mm", "quantity": 1, "unit_price": 800},
            {"product_name": "Clove 100", "quantity": 1, "unit_price": 400},
        ],
    }, TOKEN)
    test("T6.1 Edit items on Partial COD", s == 200, f"status={s}, resp={r}")
    if s == 200:
        new_total = float(r["total_amount"])
        test("T6.2 New total=1200", new_total == 1200, f"got {new_total}")
        test("T6.3 cod_amount=1200-200=1000", float(r.get("cod_amount", 0)) == 1000,
             f"got {r.get('cod_amount')}")
        test("T6.4 advance_amount still 200", float(r.get("advance_amount", 0)) == 200,
             f"got {r.get('advance_amount')}")

# ═════════════════════════════════════════════════════════════
# TEST GROUP 7: Customer name change → order list reflects it
# ═════════════════════════════════════════════════════════════
print("\n=== GROUP 7: Customer Name Sync ===")

# Update customer name
TEST_NAME = f"TestName_{int(time.time())}"
s, r = req("PATCH", f"/api/customers/{CUSTOMER_ID}", {
    "name": TEST_NAME,
}, TOKEN)
test("T7.1 Update customer name", s == 200, f"status={s}")

if s == 200:
    # Fetch order list — customer_name should reflect new name
    s2, r2 = req("GET", "/api/orders/?page_size=5", token=TOKEN)
    test("T7.2 Load orders", s2 == 200, f"status={s2}")
    if s2 == 200:
        # Find an order for this customer
        matching = [o for o in r2.get("results", []) if o.get("customer_id") == CUSTOMER_ID]
        if matching:
            test("T7.3 customer_name updated in order list",
                 matching[0].get("customer_name") == TEST_NAME,
                 f"expected '{TEST_NAME}', got '{matching[0].get('customer_name')}'")
        else:
            test("T7.3 customer_name updated (no matching order)", False,
                 "No orders found for this customer")

    # Restore original name
    req("PATCH", f"/api/customers/{CUSTOMER_ID}", {"name": ORIGINAL_NAME}, TOKEN)

# ═════════════════════════════════════════════════════════════
# TEST GROUP 8: Product status filters
# ═════════════════════════════════════════════════════════════
print("\n=== GROUP 8: Product Status Filters ===")

s, r = req("GET", "/api/products/?status=active", token=TOKEN)
test("T8.1 Filter active products", s == 200, f"status={s}")
active_count = r.get("total", 0) if s == 200 else 0
print(f"       Active products: {active_count}")

s, r = req("GET", "/api/products/?status=inactive", token=TOKEN)
test("T8.2 Filter inactive products", s == 200, f"status={s}")
inactive_count = r.get("total", 0) if s == 200 else 0
print(f"       Inactive products: {inactive_count}")

s, r = req("GET", "/api/products/?status=discontinued", token=TOKEN)
test("T8.3 Filter discontinued products", s == 200, f"status={s}")
disc_count = r.get("total", 0) if s == 200 else 0
print(f"       Discontinued products: {disc_count}")

s, r = req("GET", "/api/products/", token=TOKEN)
test("T8.4 All products (no filter)", s == 200, f"status={s}")
all_count = r.get("total", 0) if s == 200 else 0
print(f"       All products: {all_count}")

# ═════════════════════════════════════════════════════════════
# CLEANUP: Delete test orders
# ═════════════════════════════════════════════════════════════
print("\n=== CLEANUP ===")
for oid_name in ['COD_ORDER_ID', 'PCOD_ORDER_ID', 'UPI_ORDER_ID', 'BT_ORDER_ID']:
    oid = globals().get(oid_name)
    if oid:
        # Cancel first, then delete
        req("PATCH", f"/api/orders/{oid}", {"status": "cancelled"}, TOKEN)
        s, _ = req("DELETE", f"/api/orders/{oid}", token=TOKEN)
        print(f"  Cleanup {oid_name}: {'✅' if s == 200 else '⚠️ ' + str(s)}")

# ═════════════════════════════════════════════════════════════
# SUMMARY
# ═════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print(f"  RESULTS: {passed} passed, {failed} failed")
if errors:
    print(f"  FAILURES:")
    for e in errors:
        print(f"    ❌ {e}")
print(f"{'='*60}")
sys.exit(0 if failed == 0 else 1)
