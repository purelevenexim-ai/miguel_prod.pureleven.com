#!/usr/bin/env python3
"""
Products Module — Live Test Suite
Tests: create, list, search, filter, get, update, soft-delete, categories
"""

import requests, sys

BASE    = "http://172.232.118.208:8000"
LOGIN   = f"{BASE}/tenant/login"
SLUG    = "purelevenexim"
EMAIL   = "purelevenexim@gmail.com"
PASSWORD = "HgI*B5usv750Qh"

passed = 0
failed = 0

def ok(label, condition, extra=""):
    global passed, failed
    if condition:
        print(f"  ✅  {label}")
        passed += 1
    else:
        print(f"  ❌  {label}  {extra}")
        failed += 1

# ── Auth ──────────────────────────────────────────────────────
r = requests.post(LOGIN, json={"slug": SLUG, "email": EMAIL, "password": PASSWORD})
ok("Login", r.status_code == 200)
token = r.json().get("access_token", "")
H = {"Authorization": f"Bearer {token}"}

# ── 1. Create product ─────────────────────────────────────────
print("\n── Create Products ──────────────────────────────────────")
r = requests.post(f"{BASE}/api/products", json={
    "name": "Ceylon Cinnamon C5",
    "sku": "SKU-CIN-C5",
    "description": "Premium grade Ceylon cinnamon, 500g pack",
    "category": "Spices",
    "unit_price": "450.00",
    "cost_price": "280.00",
    "mrp": "500.00",
    "unit": "gram",
    "unit_value": "500",
    "unit_label": "500g",
    "status": "active"
}, headers=H)
ok("Create product (cinnamon)", r.status_code == 201, r.text[:120])
p1 = r.json()
ok("  product_code starts PROD-", p1.get("product_code","").startswith("PROD-"))
ok("  unit_price correct", str(p1.get("unit_price","")) == "450.00")
p1_id = p1.get("id")

r = requests.post(f"{BASE}/api/products", json={
    "name": "Black Pepper (Bulk)",
    "sku": "SKU-BLK-PEP",
    "category": "Spices",
    "unit_price": "320.00",
    "unit": "kg",
    "unit_label": "1kg",
}, headers=H)
ok("Create product (black pepper)", r.status_code == 201, r.text[:120])
p2_id = r.json().get("id")

r = requests.post(f"{BASE}/api/products", json={
    "name": "Cardamom Premium",
    "category": "Spices",
    "unit_price": "220.00",
    "unit": "gram",
    "unit_label": "250g",
}, headers=H)
ok("Create product (cardamom, no SKU)", r.status_code == 201, r.text[:120])
p3_id = r.json().get("id")

r = requests.post(f"{BASE}/api/products", json={
    "name": "Coconut Oil",
    "category": "Oils",
    "unit_price": "180.00",
    "unit": "litre",
    "unit_label": "1L",
    "status": "active"
}, headers=H)
ok("Create product (different category)", r.status_code == 201, r.text[:120])
p4_id = r.json().get("id")

# ── 2. Duplicate name blocked ─────────────────────────────────
print("\n── Duplicate Checks ─────────────────────────────────────")
r = requests.post(f"{BASE}/api/products", json={
    "name": "Ceylon Cinnamon C5",
    "unit_price": "400.00",
}, headers=H)
ok("Duplicate name blocked (409)", r.status_code == 409, r.text[:80])

r = requests.post(f"{BASE}/api/products", json={
    "name": "Something Else",
    "sku": "SKU-CIN-C5",
    "unit_price": "100.00",
}, headers=H)
ok("Duplicate SKU blocked (409)", r.status_code == 409, r.text[:80])

# ── 3. List products ──────────────────────────────────────────
print("\n── List & Filter ────────────────────────────────────────")
r = requests.get(f"{BASE}/api/products", headers=H)
ok("List all products", r.status_code == 200)
data = r.json()
ok("  total >= 4", data.get("total", 0) >= 4)
ok("  results is list", isinstance(data.get("results"), list))

# Search by name
r = requests.get(f"{BASE}/api/products?search=cinnamon", headers=H)
ok("Search by name (cinnamon)", r.status_code == 200)
ok("  found 1 result", r.json().get("total") == 1)

# Filter by category
r = requests.get(f"{BASE}/api/products?category=Spices", headers=H)
ok("Filter by category (Spices)", r.status_code == 200)
ok("  spices count >= 3", r.json().get("total", 0) >= 3)

r = requests.get(f"{BASE}/api/products?category=Oils", headers=H)
ok("Filter by category (Oils)", r.status_code == 200)
ok("  oils count == 1", r.json().get("total") == 1)

# Search by SKU
r = requests.get(f"{BASE}/api/products?search=SKU-BLK", headers=H)
ok("Search by SKU", r.status_code == 200)
ok("  found 1 result", r.json().get("total") == 1)

# ── 4. Get single product ─────────────────────────────────────
print("\n── Get Single Product ───────────────────────────────────")
r = requests.get(f"{BASE}/api/products/{p1_id}", headers=H)
ok("Get product by ID", r.status_code == 200)
ok("  name matches", r.json().get("name") == "Ceylon Cinnamon C5")
ok("  unit_label = 500g", r.json().get("unit_label") == "500g")
ok("  sku correct", r.json().get("sku") == "SKU-CIN-C5")

# ── 5. List categories ────────────────────────────────────────
print("\n── Categories ───────────────────────────────────────────")
r = requests.get(f"{BASE}/api/products/categories", headers=H)
ok("List categories", r.status_code == 200)
cats = r.json()
ok("  Spices in categories", "Spices" in cats)
ok("  Oils in categories", "Oils" in cats)

# ── 6. Update product ─────────────────────────────────────────
print("\n── Update Product ───────────────────────────────────────")
r = requests.patch(f"{BASE}/api/products/{p1_id}", json={
    "unit_price": "480.00",
    "mrp": "550.00",
    "description": "Updated: finest Ceylon cinnamon",
}, headers=H)
ok("Update price + description", r.status_code == 200, r.text[:120])
ok("  unit_price updated", str(r.json().get("unit_price","")) == "480.00")
ok("  description updated", "finest" in (r.json().get("description") or ""))

# Update status to inactive
r = requests.patch(f"{BASE}/api/products/{p3_id}", json={"status": "inactive"}, headers=H)
ok("Set product inactive", r.status_code == 200)
ok("  status = inactive", r.json().get("status") == "inactive")

# Filter by status
r = requests.get(f"{BASE}/api/products?status=inactive", headers=H)
ok("Filter by status=inactive", r.status_code == 200)
ok("  1 inactive product", r.json().get("total") == 1)

r = requests.get(f"{BASE}/api/products?status=active", headers=H)
ok("Filter by status=active", r.status_code == 200)
ok("  active count >= 3", r.json().get("total", 0) >= 3)

# ── 7. Soft delete ────────────────────────────────────────────
print("\n── Soft Delete ──────────────────────────────────────────")
r = requests.delete(f"{BASE}/api/products/{p4_id}", headers=H)
ok("Soft delete product", r.status_code == 200)
ok("  success message", "discontinued" in r.json().get("message","").lower())

# Verify discontinued in DB
r = requests.get(f"{BASE}/api/products/{p4_id}", headers=H)
ok("Get discontinued product still returns 200", r.status_code == 200)
ok("  status = discontinued", r.json().get("status") == "discontinued")

# Discontinued not in active list
r = requests.get(f"{BASE}/api/products?status=active", headers=H)
active_ids = [p["id"] for p in r.json().get("results", [])]
ok("Discontinued not in active list", str(p4_id) not in active_ids)

# ── 8. 404 for unknown product ────────────────────────────────
print("\n── Error Cases ──────────────────────────────────────────")
r = requests.get(f"{BASE}/api/products/00000000-0000-0000-0000-000000000000", headers=H)
ok("404 for unknown product ID", r.status_code == 404)

# ── Summary ───────────────────────────────────────────────────
print(f"\n{'='*52}")
print(f"  Results: {passed} passed, {failed} failed out of {passed+failed} tests")
print(f"{'='*52}")
if failed:
    sys.exit(1)
