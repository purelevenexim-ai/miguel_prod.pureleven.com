"""
test_vendors.py — Vendor Management Module Tests
Tests: create, list, get, update, soft-delete, search
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

# ── Create Vendor ─────────────────────────────────────────────────────────────
vendor_payload = {
    "company_name": "Alpha Supplies Pvt Ltd",
    "contact_person": "Ravi Kumar",
    "phone": "9876543210",
    "email": "ravi@alphasupplies.com",
    "address": "12 Industrial Area",
    "city": "Kochi",
    "state": "Kerala",
    "pincode": "682001",
    "gst_number": "32AABCA1234F1ZV",
    "pan_number": "AABCA1234F",
    "bank_account_name": "Alpha Supplies Pvt Ltd",
    "bank_account_number": "001234567890",
    "ifsc_code": "HDFC0001234",
}
r = requests.post(f"{BASE}/api/vendors/", json=vendor_payload, headers=H)
assert r.status_code == 201, f"Create vendor failed: {r.text}"
vendor = r.json()
vendor_id = vendor["id"]
assert vendor["vendor_code"].startswith("VEND-"), f"Bad vendor_code: {vendor['vendor_code']}"
assert vendor["company_name"] == "Alpha Supplies Pvt Ltd"
print(f"✅ Create vendor OK — {vendor['vendor_code']}")

# ── Create 2nd Vendor ─────────────────────────────────────────────────────────
r2 = requests.post(f"{BASE}/api/vendors/", json={**vendor_payload,
    "company_name": "Beta Traders",
    "gst_number": "32AABCB5678F1ZV",
    "pan_number": "AABCB5678F",
    "email": "beta@traders.com",
    "phone": "9000000001",
}, headers=H)
assert r2.status_code == 201, f"Create 2nd vendor failed: {r2.text}"
vendor2 = r2.json()
print(f"✅ Create 2nd vendor OK — {vendor2['vendor_code']}")

# Verify sequential codes
code1 = int(vendor["vendor_code"].split("-")[1])
code2 = int(vendor2["vendor_code"].split("-")[1])
assert code2 == code1 + 1, f"Vendor codes not sequential: {vendor['vendor_code']} / {vendor2['vendor_code']}"
print("✅ Sequential vendor codes OK")

# ── List Vendors ──────────────────────────────────────────────────────────────
r = requests.get(f"{BASE}/api/vendors/", headers=H)
assert r.status_code == 200, f"List vendors failed: {r.text}"
resp_data = r.json()
# Supports both paginated {data:[...]} and plain list responses
vendors = resp_data["data"] if isinstance(resp_data, dict) else resp_data
assert len(vendors) >= 2, f"Expected at least 2 vendors, got {len(vendors)}"
print(f"✅ List vendors OK — {len(vendors)} vendors")

# ── Search Vendors ────────────────────────────────────────────────────────────
r = requests.get(f"{BASE}/api/vendors/?search=Beta", headers=H)
assert r.status_code == 200, f"Search failed: {r.text}"
search_resp = r.json()
results = search_resp["data"] if isinstance(search_resp, dict) else search_resp
assert any(v["company_name"] == "Beta Traders" for v in results), "Search didn't find Beta Traders"
print("✅ Search vendors OK")

# ── Get Vendor ────────────────────────────────────────────────────────────────
r = requests.get(f"{BASE}/api/vendors/{vendor_id}", headers=H)
assert r.status_code == 200, f"Get vendor failed: {r.text}"
assert r.json()["id"] == vendor_id
print("✅ Get vendor OK")

# ── Update Vendor ─────────────────────────────────────────────────────────────
r = requests.patch(f"{BASE}/api/vendors/{vendor_id}", json={"city": "Thrissur", "pincode": "680001"}, headers=H)
assert r.status_code == 200, f"Update vendor failed: {r.text}"
assert r.json()["city"] == "Thrissur"
assert r.json()["pincode"] == "680001"
print("✅ Update vendor OK")

# ── Soft Delete Vendor ────────────────────────────────────────────────────────
r = requests.delete(f"{BASE}/api/vendors/{vendor2['id']}", headers=H)
assert r.status_code in (200, 204), f"Delete vendor failed: {r.text}"
# 200 returns body, 204 does not
if r.status_code == 200:
    assert r.json()["is_active"] is False
print("✅ Soft-delete vendor OK")

# Verify deleted vendor no longer appears in default list
r = requests.get(f"{BASE}/api/vendors/", headers=H)
list_resp = r.json()
active_list = list_resp["data"] if isinstance(list_resp, dict) else list_resp
active_ids = [v["id"] for v in active_list]
assert vendor2["id"] not in active_ids, "Deleted vendor still in active list"
print("✅ Deleted vendor excluded from list OK")

# ── 404 on missing vendor ─────────────────────────────────────────────────────
r = requests.get(f"{BASE}/api/vendors/00000000-0000-0000-0000-000000000000", headers=H)
assert r.status_code == 404, f"Expected 404, got {r.status_code}"
print("✅ 404 on missing vendor OK")

print("\n🎉 ALL VENDOR TESTS PASSED")
