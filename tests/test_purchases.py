"""
test_purchases.py — Purchase Orders Module Tests
Tests: create PO, list, get, update, advance status through draft→sent→received
Verifies stock is automatically created in inventory on receipt.
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

# ── Get a vendor ID ───────────────────────────────────────────────────────────
r = requests.get(f"{BASE}/api/vendors/", headers=H)
assert r.status_code == 200
vendor_resp = r.json()
vendor_list = vendor_resp["data"] if isinstance(vendor_resp, dict) else vendor_resp
assert vendor_list, "Need at least 1 vendor — run test_vendors.py first"
VENDOR_ID = vendor_list[0]["id"]
print(f"✅ Using vendor: {vendor_list[0]['company_name']}")

# ── Get a product ID ──────────────────────────────────────────────────────────
r = requests.get(f"{BASE}/api/products/", headers=H)
assert r.status_code == 200
prod_resp = r.json()
prod_list = prod_resp.get("results") or prod_resp.get("data") or (prod_resp if isinstance(prod_resp, list) else [])
assert prod_list, "Need at least 1 product — create one first"
product = prod_list[0]
PRODUCT_ID = product["id"]
print(f"✅ Using product: {product['name']}")

# ── Get stock BEFORE PO receipt ───────────────────────────────────────────────
r = requests.get(f"{BASE}/api/inventory/stock/{PRODUCT_ID}", headers=H)
stock_before = float(r.json().get("current_stock", 0)) if r.status_code == 200 else 0.0
print(f"✅ Stock before PO receive: {stock_before}")

# ── Create Purchase Order ─────────────────────────────────────────────────────
po_payload = {
    "vendor_id": VENDOR_ID,
    "expected_date": "2026-03-15",
    "notes": "Test PO from automated tests",
    "items": [
        {
            "product_id": PRODUCT_ID,
            "product_name": product["name"],
            "quantity": "10",
            "unit_cost": "150.00",
            "tax_percent": "18",
        }
    ],
}
r = requests.post(f"{BASE}/api/purchases/", json=po_payload, headers=H)
assert r.status_code == 201, f"Create PO failed: {r.text}"
po = r.json()
PO_ID = po["id"]
assert po["status"] == "draft"
assert po["po_number"].startswith("PO-"), f"Bad PO number: {po['po_number']}"
# Items may be in detail view only; verify totals on PO header
assert float(po["grand_total"]) == 1770.00, f"grand_total: {po['grand_total']}"
assert float(po["tax_amount"]) == 270.00, f"tax_amount: {po['tax_amount']}"
assert float(po["total_amount"]) == 1500.00, f"total_amount (taxable): {po['total_amount']}"
print(f"✅ Create PO OK — {po['po_number']}, grand_total: {po['grand_total']}")

# ── Verify items in detail ────────────────────────────────────────────────────
r_detail = requests.get(f"{BASE}/api/purchases/{PO_ID}", headers=H)
assert r_detail.status_code == 200
po_detail = r_detail.json()
if "items" in po_detail:
    assert len(po_detail["items"]) == 1
    item = po_detail["items"][0]
    assert float(item["quantity"]) == 10.0
    assert float(item["unit_cost"]) == 150.00
    assert float(item["tax_amount"]) == 270.00
    assert float(item["line_total"]) == 1770.00
    print("✅ PO items detail OK")
else:
    print("ℹ️  Items not in PO list response (in detail only)")

# ── List POs ──────────────────────────────────────────────────────────────────
r = requests.get(f"{BASE}/api/purchases/", headers=H)
assert r.status_code == 200
po_resp = r.json()
pos = po_resp.get("data") or (po_resp if isinstance(po_resp, list) else [])
assert any(p["id"] == PO_ID for p in pos), "PO not in list"
print(f"✅ List POs OK — {len(pos)} orders")

# ── Get PO detail ─────────────────────────────────────────────────────────────
r = requests.get(f"{BASE}/api/purchases/{PO_ID}", headers=H)
assert r.status_code == 200
assert r.json()["id"] == PO_ID
print("✅ Get PO detail OK")

# ── Update PO (while draft) ───────────────────────────────────────────────────
r = requests.patch(f"{BASE}/api/purchases/{PO_ID}", json={"notes": "Updated notes"}, headers=H)
assert r.status_code == 200, f"Update PO failed: {r.text}"
assert r.json()["notes"] == "Updated notes"
print("✅ Update PO OK")

# ── Advance status: draft → sent ─────────────────────────────────────────────
r = requests.post(f"{BASE}/api/purchases/{PO_ID}/status?new_status=sent", headers=H)
assert r.status_code == 200, f"Advance to sent failed: {r.text}"
assert r.json()["status"] == "sent"
print("✅ Status draft → sent OK")

# ── Advance status: sent → received ──────────────────────────────────────────
r = requests.post(f"{BASE}/api/purchases/{PO_ID}/status?new_status=received", headers=H)
assert r.status_code == 200, f"Advance to received failed: {r.text}"
po_received = r.json()
assert po_received["status"] == "received"
assert po_received["received_at"] is not None, "received_at should be set"
print("✅ Status sent → received OK (stock-in triggered)")

# ── Verify stock increased ────────────────────────────────────────────────────
r = requests.get(f"{BASE}/api/inventory/stock/{PRODUCT_ID}", headers=H)
assert r.status_code == 200, f"Get stock failed: {r.text}"
stock_after = float(r.json()["current_stock"])
expected = stock_before + 10.0
assert stock_after == expected, f"Stock after PO receive: expected {expected}, got {stock_after}"
print(f"✅ Stock after receive: {stock_before} → {stock_after} (+10) ✓")

# ── Cannot advance received PO further ───────────────────────────────────────
r = requests.post(f"{BASE}/api/purchases/{PO_ID}/status?new_status=sent", headers=H)
assert r.status_code == 400, f"Expected 400 on invalid advance, got {r.status_code}: {r.text}"
print("✅ Cannot advance received PO OK")

# ── Cannot update a received PO ──────────────────────────────────────────────
r = requests.patch(f"{BASE}/api/purchases/{PO_ID}", json={"notes": "Should fail"}, headers=H)
assert r.status_code == 400, f"Expected 400 updating non-draft PO, got {r.status_code}"
print("✅ Update locked after receipt OK")

# ── 404 on missing PO ────────────────────────────────────────────────────────
r = requests.get(f"{BASE}/api/purchases/00000000-0000-0000-0000-000000000000", headers=H)
assert r.status_code == 404
print("✅ 404 on missing PO OK")

print("\n🎉 ALL PURCHASE ORDER TESTS PASSED")
