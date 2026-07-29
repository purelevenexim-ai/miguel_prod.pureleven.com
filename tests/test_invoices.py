"""
test_invoices.py — GST Invoice Engine Tests
Tests: create draft, GST split (intra/inter state), invoice numbering,
       finalize (immutable), cancel (draft only), stock-out on finalize
"""
import requests
from decimal import Decimal

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

# ── Get a customer ────────────────────────────────────────────────────────────
r = requests.get(f"{BASE}/api/customers/", headers=H)
assert r.status_code == 200
cust_resp = r.json()
cust_list = cust_resp.get("data") or (cust_resp if isinstance(cust_resp, list) else [])
assert cust_list, "Need at least 1 customer"
customer = cust_list[0]
CUSTOMER_ID = customer["id"]
print(f"✅ Using customer: {customer.get('name', customer.get('full_name', CUSTOMER_ID))}")

# ── Get a product ─────────────────────────────────────────────────────────────
r = requests.get(f"{BASE}/api/products/", headers=H)
assert r.status_code == 200
prod_resp = r.json()
prod_list = prod_resp.get("results") or prod_resp.get("data") or (prod_resp if isinstance(prod_resp, list) else [])
assert prod_list, "Need at least 1 product"
product = prod_list[0]
PRODUCT_ID = product["id"]
print(f"✅ Using product: {product['name']}")

# ── Get stock before finalize ─────────────────────────────────────────────────
r = requests.get(f"{BASE}/api/inventory/stock/{PRODUCT_ID}", headers=H)
stock_before = float(r.json().get("current_stock", 0)) if r.status_code == 200 else 0.0
print(f"✅ Stock before finalize: {stock_before}")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 1 — Intra-state invoice (Kerala → Kerala → CGST + SGST)
# ═══════════════════════════════════════════════════════════════════════════════
intra_payload = {
    "customer_id": CUSTOMER_ID,
    "invoice_date": "2026-02-20",
    "supply_state": "Kerala",
    "customer_state": "Kerala",
    "customer_gst": "32AABCA1234F1ZV",
    "billing_address": "MG Road, Kochi, Kerala 682001",
    "notes": "Test intra-state invoice",
    "items": [
        {
            "product_id": PRODUCT_ID,
            "product_name": product["name"],
            "hsn_code": "62101000",
            "quantity": "2",
            "unit_price": "1000.00",
            "tax_percent": "12",
        }
    ],
}
r = requests.post(f"{BASE}/api/invoices/", json=intra_payload, headers=H)
assert r.status_code == 201, f"Create intra invoice failed: {r.text}"
inv_intra = r.json()
INV_INTRA_ID = inv_intra["id"]

# Verify invoice number format
assert inv_intra["invoice_number"].startswith("INV-"), f"Bad invoice_number: {inv_intra['invoice_number']}"
parts = inv_intra["invoice_number"].split("-")
assert len(parts) == 3, f"Format should be INV-YYYY-NNNNN: {inv_intra['invoice_number']}"
assert len(parts[2]) == 5, f"Sequence should be 5 digits: {parts[2]}"
print(f"✅ Invoice number format OK — {inv_intra['invoice_number']}")

# Verify FY
assert inv_intra["financial_year"] == "2025-26", f"FY: {inv_intra['financial_year']}"
assert inv_intra["status"] == "draft"
print(f"✅ Financial year OK — {inv_intra['financial_year']}")

# Verify GST split: intra-state → CGST + SGST (each 6%), IGST = 0
item = inv_intra["items"][0]
assert float(item["cgst_percent"]) == 6.0,  f"CGST% should be 6: {item['cgst_percent']}"
assert float(item["sgst_percent"]) == 6.0,  f"SGST% should be 6: {item['sgst_percent']}"
assert float(item["igst_percent"]) == 0.0,  f"IGST% should be 0 (intra): {item['igst_percent']}"
taxable = 2 * 1000.0
assert float(item["taxable_amount"]) == taxable, f"taxable: {item['taxable_amount']}"
assert float(item["cgst_amount"]) == taxable * 0.06, f"cgst_amount: {item['cgst_amount']}"
assert float(item["sgst_amount"]) == taxable * 0.06, f"sgst_amount: {item['sgst_amount']}"
assert float(item["igst_amount"]) == 0.0, f"igst_amount should be 0: {item['igst_amount']}"
assert float(inv_intra["cgst_amount"]) == taxable * 0.06
assert float(inv_intra["sgst_amount"]) == taxable * 0.06
assert float(inv_intra["igst_amount"]) == 0.0
grand = taxable + taxable * 0.12
assert float(inv_intra["grand_total"]) == grand, f"grand_total: {inv_intra['grand_total']}, expected {grand}"
print(f"✅ Intra-state GST split OK — CGST={item['cgst_amount']}, SGST={item['sgst_amount']}, IGST=0")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 2 — Inter-state invoice (Kerala → Maharashtra → IGST only)
# ═══════════════════════════════════════════════════════════════════════════════
inter_payload = {
    "customer_id": CUSTOMER_ID,
    "invoice_date": "2026-02-20",
    "supply_state": "Kerala",
    "customer_state": "Maharashtra",
    "notes": "Test inter-state invoice",
    "items": [
        {
            "product_id": None,
            "product_name": "Export Item",
            "hsn_code": "62101000",
            "quantity": "5",
            "unit_price": "500.00",
            "tax_percent": "18",
        }
    ],
}
r = requests.post(f"{BASE}/api/invoices/", json=inter_payload, headers=H)
assert r.status_code == 201, f"Create inter invoice failed: {r.text}"
inv_inter = r.json()
INV_INTER_ID = inv_inter["id"]

item_inter = inv_inter["items"][0]
assert float(item_inter["cgst_percent"]) == 0.0, f"CGST% should be 0 (inter): {item_inter['cgst_percent']}"
assert float(item_inter["sgst_percent"]) == 0.0, f"SGST% should be 0 (inter): {item_inter['sgst_percent']}"
assert float(item_inter["igst_percent"]) == 18.0, f"IGST% should be 18: {item_inter['igst_percent']}"
taxable_inter = 5 * 500.0
assert float(inv_inter["cgst_amount"]) == 0.0
assert float(inv_inter["sgst_amount"]) == 0.0
assert float(inv_inter["igst_amount"]) == taxable_inter * 0.18
print(f"✅ Inter-state GST split OK — CGST=0, SGST=0, IGST={inv_inter['igst_amount']}")

# ── Invoice number sequential ─────────────────────────────────────────────────
seq1 = int(inv_intra["invoice_number"].split("-")[2])
seq2 = int(inv_inter["invoice_number"].split("-")[2])
assert seq2 == seq1 + 1, f"Invoice numbers not sequential: {inv_intra['invoice_number']} / {inv_inter['invoice_number']}"
print(f"✅ Sequential invoice numbers OK — {inv_intra['invoice_number']} → {inv_inter['invoice_number']}")

# ── List invoices ─────────────────────────────────────────────────────────────
r = requests.get(f"{BASE}/api/invoices/", headers=H)
assert r.status_code == 200
inv_resp = r.json()
invoices = (inv_resp.get("data") if isinstance(inv_resp, dict) else None) or (inv_resp if isinstance(inv_resp, list) else [])
ids = [i["id"] for i in invoices]
assert INV_INTRA_ID in ids and INV_INTER_ID in ids
print(f"✅ List invoices OK — {len(invoices)} invoices")

# ── Filter by status ──────────────────────────────────────────────────────────
r = requests.get(f"{BASE}/api/invoices/?invoice_status=draft", headers=H)
assert r.status_code == 200
filter_resp = r.json()
filter_list = (filter_resp.get("data") if isinstance(filter_resp, dict) else None) or (filter_resp if isinstance(filter_resp, list) else [])
assert all(i["status"] == "draft" for i in filter_list)
print("✅ Filter invoices by status OK")

# ── Get invoice detail ────────────────────────────────────────────────────────
r = requests.get(f"{BASE}/api/invoices/{INV_INTRA_ID}", headers=H)
assert r.status_code == 200
assert r.json()["id"] == INV_INTRA_ID
assert len(r.json()["items"]) == 1
print("✅ Get invoice detail OK")

# ── Update draft invoice ──────────────────────────────────────────────────────
r = requests.patch(f"{BASE}/api/invoices/{INV_INTRA_ID}", json={"notes": "Updated before finalize"}, headers=H)
assert r.status_code == 200, f"Update draft failed: {r.text}"
assert r.json()["notes"] == "Updated before finalize"
print("✅ Update draft invoice OK")

# ── Cancel inter-state invoice (draft → cancelled) ────────────────────────────
r = requests.post(f"{BASE}/api/invoices/{INV_INTER_ID}/cancel", headers=H)
assert r.status_code == 200, f"Cancel failed: {r.text}"
assert r.json()["status"] == "cancelled"
print("✅ Cancel draft invoice OK")

# ── Cannot cancel already-cancelled invoice ───────────────────────────────────
r = requests.post(f"{BASE}/api/invoices/{INV_INTER_ID}/cancel", headers=H)
assert r.status_code == 400, f"Expected 400, got {r.status_code}"
print("✅ Double-cancel blocked OK")

# ── Finalize intra-state invoice → stock-out triggered ───────────────────────
r = requests.post(f"{BASE}/api/invoices/{INV_INTRA_ID}/finalize", headers=H)
assert r.status_code == 200, f"Finalize failed: {r.text}"
finalized = r.json()
assert finalized["status"] == "finalized"
print(f"✅ Finalize invoice OK — {finalized['invoice_number']} → finalized")

# Verify stock decreased by 2 (quantity on invoice)
r = requests.get(f"{BASE}/api/inventory/stock/{PRODUCT_ID}", headers=H)
stock_after = float(r.json().get("current_stock", 0))
expected_stock = stock_before - 2.0
assert stock_after == expected_stock, \
    f"Stock after finalize: expected {expected_stock}, got {stock_after}"
print(f"✅ Stock-out on finalize: {stock_before} → {stock_after} (-2) ✓")

# ── Cannot update finalized invoice ──────────────────────────────────────────
r = requests.patch(f"{BASE}/api/invoices/{INV_INTRA_ID}", json={"notes": "Should fail"}, headers=H)
assert r.status_code == 400, f"Expected 400 updating finalized, got {r.status_code}"
print("✅ Finalized invoice locked from updates OK")

# ── Cannot cancel finalized invoice ──────────────────────────────────────────
r = requests.post(f"{BASE}/api/invoices/{INV_INTRA_ID}/cancel", headers=H)
assert r.status_code == 400, f"Expected 400 cancelling finalized, got {r.status_code}"
print("✅ Finalized invoice cannot be cancelled OK")

# ── Cannot re-finalize ────────────────────────────────────────────────────────
r = requests.post(f"{BASE}/api/invoices/{INV_INTRA_ID}/finalize", headers=H)
assert r.status_code == 400, f"Expected 400 re-finalizing, got {r.status_code}"
print("✅ Double-finalize blocked OK")

# ── Filter by FY ──────────────────────────────────────────────────────────────
r = requests.get(f"{BASE}/api/invoices/?financial_year=2025-26", headers=H)
assert r.status_code == 200
fy_resp = r.json()
fy_list = (fy_resp.get("data") if isinstance(fy_resp, dict) else None) or (fy_resp if isinstance(fy_resp, list) else [])
assert all(i["financial_year"] == "2025-26" for i in fy_list)
print("✅ Filter by financial year OK")

# ── 404 on missing invoice ────────────────────────────────────────────────────
r = requests.get(f"{BASE}/api/invoices/00000000-0000-0000-0000-000000000000", headers=H)
assert r.status_code == 404
print("✅ 404 on missing invoice OK")

# ── GST engine: zero-tax item ─────────────────────────────────────────────────
r = requests.post(f"{BASE}/api/invoices/", json={
    "customer_id": CUSTOMER_ID,
    "invoice_date": "2026-02-21",
    "supply_state": "Kerala",
    "customer_state": "Kerala",
    "items": [
        {"product_name": "Exempt Item", "quantity": "1", "unit_price": "200.00", "tax_percent": "0"},
    ],
}, headers=H)
assert r.status_code == 201, f"Zero-tax invoice failed: {r.text}"
zero = r.json()
assert float(zero["total_tax"]) == 0.0
assert float(zero["grand_total"]) == 200.0
print("✅ Zero-tax invoice OK")

print("\n🎉 ALL INVOICE TESTS PASSED")
