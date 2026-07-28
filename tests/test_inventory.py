"""
test_inventory.py — Inventory & Stock Engine Tests
Tests: movement ledger, summary, manual adjustment, stock validation
"""
import requests

BASE = "http://172.232.118.208:8000"
TENANT_SLUG = "purelevenexim"
EMAIL = "purelevenexim@gmail.com"
PASSWORD = "HgI*B5usv750Qh"

# ── Auth ──────────────────────────────────────────────────────────────────────
resp = requests.post(f"{BASE}/tenant/login", json={"slug": TENANT_SLUG, "email": EMAIL, "password": PASSWORD})
assert resp.status_code == 200, f"Login failed: {resp.text}"
TOKEN = resp.json()["access_token"]
H = {"Authorization": f"Bearer {TOKEN}"}
print("✅ Auth OK")

# ── Get a product ─────────────────────────────────────────────────────────────
r = requests.get(f"{BASE}/api/products/", headers=H)
assert r.status_code == 200
prod_resp = r.json()
prod_list = prod_resp.get("results") or prod_resp.get("data") or (prod_resp if isinstance(prod_resp, list) else [])
assert prod_list, "Need at least 1 product"
product = prod_list[0]
PRODUCT_ID = product["id"]
print(f"✅ Using product: {product['name']} (id: {PRODUCT_ID})")

# ── Get current stock ─────────────────────────────────────────────────────────
r = requests.get(f"{BASE}/api/inventory/stock/{PRODUCT_ID}", headers=H)
assert r.status_code == 200, f"Get stock failed: {r.text}"
stock_data = r.json()
assert "current_stock" in stock_data
stock_before = float(stock_data["current_stock"])
print(f"✅ Get single stock OK — current: {stock_before}")

# ── List stock summary ────────────────────────────────────────────────────────
r = requests.get(f"{BASE}/api/inventory/stock", headers=H)
assert r.status_code == 200, f"List stock failed: {r.text}"
summary = r.json()
assert isinstance(summary, list), "Expected list"
print(f"✅ List stock summary OK — {len(summary)} products with stock records")

# ── List movements ────────────────────────────────────────────────────────────
r = requests.get(f"{BASE}/api/inventory/movements", headers=H)
assert r.status_code == 200, f"List movements failed: {r.text}"
mov_resp = r.json()
movements = mov_resp.get("data") or (mov_resp if isinstance(mov_resp, list) else [])
movements_before = len(movements)
print(f"✅ List movements OK — {movements_before} total movements")

# ── Filter movements by product ───────────────────────────────────────────────
r = requests.get(f"{BASE}/api/inventory/movements?product_id={PRODUCT_ID}", headers=H)
assert r.status_code == 200, f"Filter movements failed: {r.text}"
pm_resp = r.json()
prod_movements = pm_resp.get("data") or (pm_resp if isinstance(pm_resp, list) else [])
print(f"✅ Filter movements by product OK — {len(prod_movements)} for this product")

# ── Manual stock adjustment (add) ─────────────────────────────────────────────
adjust_payload = {
    "product_id": PRODUCT_ID,
    "quantity_change": "5",
    "note": "Opening stock adjustment — test",
}
r = requests.post(f"{BASE}/api/inventory/adjust", json=adjust_payload, headers=H)
assert r.status_code in (200, 201), f"Adjust stock failed: {r.text}"
adj_movement = r.json()
assert adj_movement["movement_type"] == "adjustment"
assert float(adj_movement["quantity_change"]) == 5.0
print("✅ Manual stock adjustment (+5) OK")

# ── Verify stock increased ────────────────────────────────────────────────────
r = requests.get(f"{BASE}/api/inventory/stock/{PRODUCT_ID}", headers=H)
stock_after_add = float(r.json()["current_stock"])
assert stock_after_add == stock_before + 5.0, f"Expected {stock_before + 5}, got {stock_after_add}"
print(f"✅ Stock after +5 adjustment: {stock_before} → {stock_after_add} ✓")

# ── Manual stock adjustment (remove) ─────────────────────────────────────────
r = requests.post(f"{BASE}/api/inventory/adjust", json={
    "product_id": PRODUCT_ID,
    "quantity_change": "-3",
    "note": "Write-off — test",
}, headers=H)
assert r.status_code in (200, 201), f"Negative adjust failed: {r.text}"
print("✅ Manual stock adjustment (-3) OK")

r = requests.get(f"{BASE}/api/inventory/stock/{PRODUCT_ID}", headers=H)
stock_after_remove = float(r.json()["current_stock"])
assert stock_after_remove == stock_after_add - 3.0, f"Expected {stock_after_add - 3}, got {stock_after_remove}"
print(f"✅ Stock after -3 adjustment: {stock_after_add} → {stock_after_remove} ✓")

# ── Movement count increased ──────────────────────────────────────────────────
r = requests.get(f"{BASE}/api/inventory/movements", headers=H)
new_mov_resp = r.json()
new_movements = new_mov_resp.get("data") or (new_mov_resp if isinstance(new_mov_resp, list) else [])
movements_after = len(new_movements)
assert movements_after == movements_before + 2, \
    f"Expected {movements_before + 2} movements, got {movements_after}"
print(f"✅ Movement count increased: {movements_before} → {movements_after} ✓")

# ── Filter by movement type ───────────────────────────────────────────────────
r = requests.get(f"{BASE}/api/inventory/movements?movement_type=adjustment", headers=H)
assert r.status_code == 200, f"Filter by type failed: {r.text}"
adj_resp = r.json()
adj_movements = adj_resp.get("data") or (adj_resp if isinstance(adj_resp, list) else [])
assert all(m["movement_type"] == "adjustment" for m in adj_movements), "Non-adjustment in filtered list"
print(f"✅ Filter movements by type OK — {len(adj_movements)} adjustment records")

# ── 404 on missing product stock ─────────────────────────────────────────────
r = requests.get(f"{BASE}/api/inventory/stock/00000000-0000-0000-0000-000000000000", headers=H)
# Returns 0 or 404 — both acceptable; check it doesn't 500
assert r.status_code in (200, 404), f"Unexpected status: {r.status_code}"
print("✅ Missing product stock handled OK")

print("\n🎉 ALL INVENTORY TESTS PASSED")
