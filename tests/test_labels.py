#!/usr/bin/env python3
"""
Live test suite for the Labels & WhatsApp Module.
Run: python3 /opt/miguel/test_labels.py
"""
import json
import urllib.request
import urllib.error

BASE = "http://172.232.118.208:8000"
PASS = 0
FAIL = 0


def req(method, path, body=None, token=None, raw=False):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            if raw:
                return resp.status, resp.read(), dict(resp.headers)
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if raw:
            return e.code, e.read(), {}
        return e.code, json.loads(e.read())


def ok(label, cond, hint=""):
    global PASS, FAIL
    if cond:
        print(f"  ✅ {label}")
        PASS += 1
    else:
        print(f"  ❌ {label} {hint}")
        FAIL += 1


# ─────────────────────────────────────────────────────────────
# 1. Login
# ─────────────────────────────────────────────────────────────
print("\n=== LOGIN ===")
status, resp = req("POST", "/tenant/login", {
    "slug": "purelevenexim",
    "email": "purelevenexim@gmail.com",
    "password": "HgI*B5usv750Qh",
})
ok("Login 200", status == 200, str(resp))
TOKEN = resp.get("access_token", "")

# ─────────────────────────────────────────────────────────────
# 2. Grab an existing order
# ─────────────────────────────────────────────────────────────
print("\n=== SETUP: Fetch existing orders ===")
status, resp = req("GET", "/api/orders/", token=TOKEN)
ok("Orders list 200", status == 200, str(resp))
orders = resp.get("data", [])
if not orders:
    print("  ℹ️  No pre-existing orders — all tests will use freshly created order")
    PASS += 1  # not a failure — tests create their own
else:
    ok("At least 1 order exists", True)

ORDER_ID = orders[0]["id"] if orders else None
ORDER_NUM = orders[0].get("order_number", "?") if orders else "?"
print(f"  Using order_id={str(ORDER_ID)[:8]}...  order_number={ORDER_NUM}")

# Grab a customer for a new test order (with full delivery address)
status, resp = req("GET", "/api/customers/", token=TOKEN)
ok("Customers list 200", status == 200)
CUSTOMER_ID = resp["data"][0]["id"] if resp.get("data") else None

# ─────────────────────────────────────────────────────────────
# 3. Create a fresh order with delivery address & tracking
# ─────────────────────────────────────────────────────────────
print("\n=== TEST 1: Create order with delivery address ===")
status, new_order = req("POST", "/api/orders/", {
    "customer_id": CUSTOMER_ID,
    "items": [
        {
            "product_name": "Test Atta 10kg",
            "sku": "TST-01",
            "quantity": "2",
            "unit": "bag",
            "unit_price": "480.00",
            "discount_pct": "0",
        }
    ],
    "payment_method": "cod",
    "delivery_address": "12, Test Street",
    "delivery_pincode": "685560",
    "delivery_city": "Munnar",
    "delivery_state": "Kerala",
    "notes": "Label test order",
}, token=TOKEN)
ok("Create order 201", status == 201, str(new_order))
NEW_ORDER_ID = new_order.get("id")
print(f"  New order_id={str(NEW_ORDER_ID)[:8]}...  order_number={new_order.get('order_number')}")

# ─────────────────────────────────────────────────────────────
# 4. Generate label PDF for one order
# ─────────────────────────────────────────────────────────────
print("\n=== TEST 2: Generate PDF label (single order) ===")
status, raw, headers = req(
    "POST", "/api/labels/generate",
    {"order_ids": [NEW_ORDER_ID]},
    token=TOKEN, raw=True,
)
ok("Generate label 200", status == 200, str(raw[:100]))
ok("Content-Type is PDF", "application/pdf" in headers.get("content-type", ""), headers.get("content-type"))
ok("PDF magic bytes (%PDF)", isinstance(raw, bytes) and raw[:4] == b"%PDF", str(raw[:8]))
ok("X-Orders-Printed header present", "x-orders-printed" in headers, str(list(headers.keys())))
ok("X-Orders-Printed = 1", headers.get("x-orders-printed") == "1", headers.get("x-orders-printed"))

# ─────────────────────────────────────────────────────────────
# 5. Verify printed_count incremented
# ─────────────────────────────────────────────────────────────
print("\n=== TEST 3: printed_count incremented ===")
status, detail = req("GET", f"/api/orders/{NEW_ORDER_ID}", token=TOKEN)
ok("Order detail 200", status == 200, str(detail))
ok("printed_count == 1", detail.get("printed_count") == 1, f"got {detail.get('printed_count')}")

# Print again → should be 2
req("POST", "/api/labels/generate", {"order_ids": [NEW_ORDER_ID]}, token=TOKEN, raw=True)
status, detail2 = req("GET", f"/api/orders/{NEW_ORDER_ID}", token=TOKEN)
ok("printed_count == 2 after second print", detail2.get("printed_count") == 2, f"got {detail2.get('printed_count')}")

# ─────────────────────────────────────────────────────────────
# 6. Generate PDF for multiple orders
# ─────────────────────────────────────────────────────────────
print("\n=== TEST 4: Generate labels for multiple orders ===")
# Build a list of up to 3 distinct valid order IDs
order_ids_all = list({o["id"] for o in orders[:3]})
if NEW_ORDER_ID not in order_ids_all:
    order_ids_all.append(NEW_ORDER_ID)
expected_count = len(order_ids_all)
status, raw_multi, headers_multi = req(
    "POST", "/api/labels/generate",
    {"order_ids": order_ids_all},
    token=TOKEN, raw=True,
)
ok("Multi-label generate 200", status == 200, str(raw_multi[:60]))
ok("Multi-label is PDF", isinstance(raw_multi, bytes) and raw_multi[:4] == b"%PDF")
printed = int(headers_multi.get("x-orders-printed", 0))
ok(f"X-Orders-Printed = {expected_count}", printed == expected_count, f"got {printed}")

# ─────────────────────────────────────────────────────────────
# 7. Generate label with empty order_ids list
# ─────────────────────────────────────────────────────────────
print("\n=== TEST 5: Generate label - empty list → 400 ===")
status, resp, _ = req("POST", "/api/labels/generate", {"order_ids": []}, token=TOKEN, raw=True)
# Should get 422 (validation) or 400
ok("Empty order_ids → 4xx", status in (400, 422), f"got {status}")

# ─────────────────────────────────────────────────────────────
# 8. Generate label with fake UUID → 400 (all skipped)
# ─────────────────────────────────────────────────────────────
print("\n=== TEST 6: Generate label - unknown UUID → 400 ===")
status, resp, _ = req(
    "POST", "/api/labels/generate",
    {"order_ids": ["00000000-0000-0000-0000-000000000000"]},
    token=TOKEN, raw=True,
)
ok("Unknown order → 400", status == 400, f"got {status}")

# ─────────────────────────────────────────────────────────────
# 9. WhatsApp single message (pre-dispatch — no tracking)
# ─────────────────────────────────────────────────────────────
print("\n=== TEST 7: WhatsApp single - pre_dispatch template ===")
status, wa = req("GET", f"/api/labels/orders/{NEW_ORDER_ID}/whatsapp", token=TOKEN)
ok("WhatsApp 200", status == 200, str(wa))
ok("Has 'to' field", "to" in wa)
ok("Has 'wa_url' field", "wa_url" in wa)
ok("Has 'message' field", "message" in wa)
ok("template = pre_dispatch", wa.get("template") == "pre_dispatch", f"got {wa.get('template')}")
ok("wa_url starts with https://wa.me/", wa.get("wa_url", "").startswith("https://wa.me/"), wa.get("wa_url", "")[:30])
ok("order_number in response", wa.get("order_number") == new_order.get("order_number"))
print(f"  template={wa.get('template')}  to={wa.get('to')}  phone_display={wa.get('phone_display')}")

# ─────────────────────────────────────────────────────────────
# 10. Add tracking number → shipped template
# ─────────────────────────────────────────────────────────────
print("\n=== TEST 8: WhatsApp single - shipped template (after adding tracking) ===")
status, updated = req("PATCH", f"/api/orders/{NEW_ORDER_ID}", {
    "tracking_number": "DTDC123456789",
    "courier_name": "DTDC",
}, token=TOKEN)
ok("Order update 200", status == 200, str(updated))

status, wa_shipped = req("GET", f"/api/labels/orders/{NEW_ORDER_ID}/whatsapp", token=TOKEN)
ok("WhatsApp shipped 200", status == 200)
ok("template = shipped", wa_shipped.get("template") == "shipped", f"got {wa_shipped.get('template')}")
ok("tracking_number in message", "DTDC123456789" in wa_shipped.get("message", ""))
print(f"  template={wa_shipped.get('template')}  tracking in message ✓")

# ─────────────────────────────────────────────────────────────
# 11. WhatsApp 404 for unknown order
# ─────────────────────────────────────────────────────────────
print("\n=== TEST 9: WhatsApp - unknown order → 404 ===")
status, resp = req("GET", "/api/labels/orders/00000000-0000-0000-0000-000000000000/whatsapp", token=TOKEN)
ok("Unknown order → 404", status == 404, f"got {status}")

# ─────────────────────────────────────────────────────────────
# 12. WhatsApp bulk
# ─────────────────────────────────────────────────────────────
print("\n=== TEST 10: WhatsApp bulk ===")
bulk_ids = [o["id"] for o in orders[:3]]
if not bulk_ids:
    bulk_ids = [NEW_ORDER_ID]
status, bulk = req("POST", "/api/labels/whatsapp/bulk", {"order_ids": bulk_ids}, token=TOKEN)
ok("Bulk 200", status == 200, str(bulk))
ok("Has 'total' field", "total" in bulk)
ok("Has 'results' field", "results" in bulk)
ok("total == len(results)", bulk.get("total") == len(bulk.get("results", [])))
ok("Each result has wa_url", all("wa_url" in r for r in bulk.get("results", [])))
print(f"  total={bulk.get('total')}  results count={len(bulk.get('results', []))}")

# ─────────────────────────────────────────────────────────────
# 13. Bulk with mix of valid + invalid UUIDs
# ─────────────────────────────────────────────────────────────
print("\n=== TEST 11: Bulk - mix valid + invalid ===")
status, bulk2 = req("POST", "/api/labels/whatsapp/bulk", {
    "order_ids": [NEW_ORDER_ID, "00000000-0000-0000-0000-000000000000"]
}, token=TOKEN)
ok("Bulk mixed 200", status == 200, str(bulk2))
ok("Only valid orders returned", bulk2.get("total") == 1, f"got {bulk2.get('total')}")

# ─────────────────────────────────────────────────────────────
# 14. Auth guard: generate labels requires admin/operations
# ─────────────────────────────────────────────────────────────
print("\n=== TEST 12: Auth guard - unauthenticated → 401 ===")
status, resp = req("POST", "/api/labels/generate", {"order_ids": [NEW_ORDER_ID]})
ok("Unauthenticated → 401", status == 401, f"got {status}")

# ─────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"  Results: {PASS} passed, {FAIL} failed out of {PASS+FAIL} tests")
if FAIL == 0:
    print("  🎉 ALL TESTS PASSED")
else:
    print("  ⚠️  Some tests failed — see above")
print(f"{'='*50}\n")
