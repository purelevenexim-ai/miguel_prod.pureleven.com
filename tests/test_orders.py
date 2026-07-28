#!/usr/bin/env python3
"""
Live test suite for the Orders Module.
Run: python3 /opt/miguel/test_orders.py
"""
import json
import urllib.request
import urllib.error

BASE = "http://172.232.118.208:8000"

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
        return e.code, json.loads(e.read())

# ─── Login ────────────────────────────────────────────────────
print("=== LOGIN ===")
status, resp = req("POST", "/tenant/login", {
    "slug": "purelevenexim",
    "email": "purelevenexim@gmail.com",
    "password": "HgI*B5usv750Qh",
})
assert status == 200, f"Login failed: {resp}"
TOKEN = resp["access_token"]
print(f"  ✅ {status} | role={resp['role']}")

# ─── Get a customer to use ───────────────────────────────────
print("\n=== SETUP: Get existing customer ===")
status, resp = req("GET", "/api/customers/", token=TOKEN)
assert status == 200 and resp["total"] > 0, f"Need at least 1 customer: {resp}"
CUSTOMER_ID = resp["data"][0]["id"]
print(f"  ✅ Using customer_id={CUSTOMER_ID[:8]}...")

# ─── TEST 1: Create Order ─────────────────────────────────────
print("\n=== TEST 1: Create Order (2 line items) ===")
status, order = req("POST", "/api/orders/", {
    "customer_id": CUSTOMER_ID,
    "items": [
        {
            "product_name": "Chakki Fresh Atta 10kg",
            "sku": "CFA-10KG",
            "quantity": "5",
            "unit": "bag",
            "unit_price": "450.00",
            "discount_pct": "5"
        },
        {
            "product_name": "Besan 5kg",
            "sku": "BES-5KG",
            "quantity": "10",
            "unit": "bag",
            "unit_price": "280.00",
            "discount_pct": "0"
        }
    ],
    "payment_method": "upi",
    "discount_amount": "100",
    "shipping_charge": "50",
    "delivery_city": "Mumbai",
    "expected_delivery": "2026-02-27",
    "notes": "Deliver before noon"
}, TOKEN)
assert status == 201, f"Create failed: {resp}"
ORDER_ID = order["id"]
# expected: subtotal = (5*450*0.95) + (10*280) = 2137.5 + 2800 = 4937.5
# total = 4937.5 - 100 + 50 = 4887.5
print(f"  ✅ {status} | order_number={order['order_number']} | subtotal={order['subtotal']}")
print(f"           | total={order['total_amount']} | amount_due={order['amount_due']} | items={len(order['items'])}")

# ─── TEST 2: List Orders ──────────────────────────────────────
print("\n=== TEST 2: List Orders ===")
status, resp = req("GET", "/api/orders/", token=TOKEN)
assert status == 200, f"List failed: {resp}"
print(f"  ✅ {status} | total={resp['total']}")

# ─── TEST 3: Filter by status=draft ───────────────────────────
print("\n=== TEST 3: Filter status=draft ===")
status, resp = req("GET", "/api/orders/?status=draft", token=TOKEN)
assert status == 200
print(f"  ✅ {status} | draft orders={resp['total']}")

# ─── TEST 4: Get Order Detail ─────────────────────────────────
print("\n=== TEST 4: Get Order Detail ===")
status, resp = req("GET", f"/api/orders/{ORDER_ID}", token=TOKEN)
assert status == 200, f"Get failed: {resp}"
print(f"  ✅ {status} | items={len(resp['items'])} | payments={len(resp['payments'])} | history={len(resp['status_history'])}")

# ─── TEST 5: Advance status draft→confirmed ───────────────────
print("\n=== TEST 5: Status draft → confirmed ===")
status, resp = req("POST", f"/api/orders/{ORDER_ID}/status", {
    "status": "confirmed",
    "note": "Customer confirmed via phone"
}, TOKEN)
assert status == 200, f"Status failed: {resp}"
print(f"  ✅ {status} | status={resp['status']}")

# ─── TEST 6: Bad transition confirmed→delivered ───────────────
print("\n=== TEST 6: Invalid transition (confirmed→delivered) blocked ===")
status, resp = req("POST", f"/api/orders/{ORDER_ID}/status", {"status": "delivered"}, TOKEN)
assert status == 400, f"Expected 400, got {status}: {resp}"
print(f"  ✅ {status} | detail='{resp['detail']}'")

# ─── TEST 7: Advance through pipeline ────────────────────────
print("\n=== TEST 7: Full pipeline walk ===")
for next_status, note in [
    ("processing",       "Started packing"),
    ("packed",           "Packed and ready"),
    ("shipped",          "Handed to courier"),
    ("out_for_delivery", "Out for delivery"),
    ("delivered",        "Customer received"),
]:
    s, r = req("POST", f"/api/orders/{ORDER_ID}/status", {"status": next_status, "note": note}, TOKEN)
    assert s == 200, f"Failed at {next_status}: {r}"
    print(f"  ✅ → {r['status']}")

# ─── TEST 8: Record partial payment ──────────────────────────
print("\n=== TEST 8: Record partial payment ===")
status, resp = req("POST", f"/api/orders/{ORDER_ID}/payments", {
    "amount": "2000",
    "method": "upi",
    "reference": "UPI-TXN-001",
    "note": "First instalment"
}, TOKEN)
assert status == 201, f"Payment failed: {resp}"
print(f"  ✅ {status} | paid={resp['amount']} | method={resp['method']}")

# ─── TEST 9: Check payment_status = partial ───────────────────
print("\n=== TEST 9: Verify payment_status = partial ===")
status, resp = req("GET", f"/api/orders/{ORDER_ID}", token=TOKEN)
assert status == 200
assert resp["payment_status"] == "partial", f"Expected partial: {resp['payment_status']}"
print(f"  ✅ {status} | payment_status={resp['payment_status']} | amount_paid={resp['amount_paid']} | amount_due={resp['amount_due']}")

# ─── TEST 10: Pay the remainder ───────────────────────────────
print("\n=== TEST 10: Pay remainder → status becomes paid ===")
amount_due = float(resp["amount_due"])
s, r = req("POST", f"/api/orders/{ORDER_ID}/payments", {
    "amount": str(amount_due),
    "method": "bank_transfer",
    "reference": "NEFT-20260220"
}, TOKEN)
assert s == 201, f"Second payment failed: {r}"
print(f"  ✅ {s} | paid={r['amount']}")

# ─── TEST 11: Verify fully paid ──────────────────────────────
print("\n=== TEST 11: Verify payment_status = paid ===")
status, resp = req("GET", f"/api/orders/{ORDER_ID}", token=TOKEN)
assert status == 200
assert resp["payment_status"] == "paid", f"Expected paid: {resp['payment_status']}"
print(f"  ✅ {status} | payment_status={resp['payment_status']} | amount_due={resp['amount_due']}")
print(f"           | payments recorded={len(resp['payments'])} | history entries={len(resp['status_history'])}")

# ─── TEST 12: Overpayment blocked ────────────────────────────
print("\n=== TEST 12: Overpayment blocked ===")
status, resp = req("POST", f"/api/orders/{ORDER_ID}/payments", {"amount": "1", "method": "cash"}, TOKEN)
assert status == 400, f"Expected 400, got {status}"
print(f"  ✅ {status} | detail='{resp['detail']}'")

# ─── TEST 13: Stats ───────────────────────────────────────────
print("\n=== TEST 13: Order Stats ===")
status, resp = req("GET", "/api/orders/stats", token=TOKEN)
assert status == 200, f"Stats failed: {resp}"
print(f"  ✅ {status} | total={resp['total_orders']} | revenue={resp['total_revenue']} | outstanding={resp['total_outstanding']}")
print(f"           | by_status={resp['by_status']}")

# ─── TEST 14: Create + cancel a draft ────────────────────────
print("\n=== TEST 14: Cancel a draft order ===")
_, cancel_order = req("POST", "/api/orders/", {
    "customer_id": CUSTOMER_ID,
    "items": [{"product_name": "Test Item", "quantity": "1", "unit": "piece", "unit_price": "100"}]
}, TOKEN)
CANCEL_ID = cancel_order["id"]
s, r = req("POST", f"/api/orders/{CANCEL_ID}/status", {"status": "cancelled", "note": "Customer changed mind"}, TOKEN)
assert s == 200 and r["status"] == "cancelled"
print(f"  ✅ {s} | status={r['status']}")

# ─── TEST 15: Delete cancelled order ─────────────────────────
print("\n=== TEST 15: Delete cancelled order ===")
status, resp = req("DELETE", f"/api/orders/{CANCEL_ID}", token=TOKEN)
assert status == 200, f"Delete failed: {resp}"
print(f"  ✅ {status} | {resp['message']}")

print("\n" + "="*50)
print("✅ ALL TESTS PASSED — Orders Module is LIVE")
print("="*50)
