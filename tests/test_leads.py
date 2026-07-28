#!/usr/bin/env python3
"""
Live test suite for the Leads Module.
Run: python3 /opt/miguel/test_leads.py
"""
import json
import urllib.request
import urllib.error

BASE = "http://172.232.118.208:8000"

def req(method, path, body=None, token=None):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
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
print(f"  ✅ {status} | role={resp['role']} | employee_id={resp['employee_id'][:8]}...")

# ─── Create Lead ─────────────────────────────────────────────
print("\n=== TEST 1: Create Lead ===")
status, lead = req("POST", "/api/leads/", {
    "name": "Sunita Devi",
    "phone": "9812345678",
    "email": "sunita@example.com",
    "company_name": "Devi Traders",
    "city": "Delhi",
    "source": "meta",
    "priority": "high",
    "status": "new",
    "estimated_value": 125000,
    "product_interest": "Besan 25kg bags",
    "next_followup_date": "2026-02-26",
    "notes": "Wants trial order first",
}, TOKEN)
assert status == 201, f"Create failed: {lead}"
LEAD_ID = lead["id"]
print(f"  ✅ {status} | lead_number={lead['lead_number']} | id={LEAD_ID[:8]}...")

# ─── List Leads ───────────────────────────────────────────────
print("\n=== TEST 2: List Leads ===")
status, resp = req("GET", "/api/leads/", token=TOKEN)
assert status == 200, f"List failed: {resp}"
print(f"  ✅ {status} | total={resp['total']} | page={resp['page']} | results={len(resp['results'])}")

# ─── Filter by priority ───────────────────────────────────────
print("\n=== TEST 3: Filter by priority=high ===")
status, resp = req("GET", "/api/leads/?priority=high", token=TOKEN)
assert status == 200, f"Filter failed: {resp}"
print(f"  ✅ {status} | found {resp['total']} high-priority leads")

# ─── Filter by status ─────────────────────────────────────────
print("\n=== TEST 4: Filter by status=new ===")
status, resp = req("GET", "/api/leads/?status=new", token=TOKEN)
assert status == 200, f"Filter failed: {resp}"
print(f"  ✅ {status} | found {resp['total']} new leads")

# ─── Get Single Lead ──────────────────────────────────────────
print("\n=== TEST 5: Get Lead Detail ===")
status, resp = req("GET", f"/api/leads/{LEAD_ID}", token=TOKEN)
assert status == 200, f"Get failed: {resp}"
print(f"  ✅ {status} | name={resp['name']} | activities={len(resp['activities'])}")

# ─── Log Activity ─────────────────────────────────────────────
print("\n=== TEST 6: Log Activity (call + status change) ===")
status, resp = req("POST", f"/api/leads/{LEAD_ID}/activities", {
    "activity_type": "call",
    "note": "Called, they are interested. Will send samples.",
    "new_status": "contacted",
}, TOKEN)
assert status == 201, f"Activity failed: {resp}"
print(f"  ✅ {status} | type={resp['activity_type']} | old={resp['old_status']} → new={resp['new_status']}")

# ─── Confirm Status Updated ───────────────────────────────────
print("\n=== TEST 7: Confirm status changed to 'contacted' ===")
status, resp = req("GET", f"/api/leads/{LEAD_ID}", token=TOKEN)
assert status == 200
assert resp["status"] == "contacted", f"Status not updated: {resp['status']}"
print(f"  ✅ {status} | status={resp['status']} | activities={len(resp['activities'])}")

# ─── Update Lead ──────────────────────────────────────────────
print("\n=== TEST 8: Update Lead ===")
status, resp = req("PATCH", f"/api/leads/{LEAD_ID}", {
    "estimated_value": 150000,
    "priority": "high",
    "next_followup_date": "2026-02-28",
}, TOKEN)
assert status == 200, f"Update failed: {resp}"
print(f"  ✅ {status} | estimated_value={resp['estimated_value']} | priority={resp['priority']}")

# ─── Stats ────────────────────────────────────────────────────
print("\n=== TEST 9: Lead Stats ===")
status, resp = req("GET", "/api/leads/stats", token=TOKEN)
assert status == 200, f"Stats failed: {resp}"
print(f"  ✅ {status} | total={resp['total']} | by_status={resp['by_status']}")
print(f"           | pipeline_value={resp['total_pipeline_value']} | overdue={resp['overdue_followups']}")

# ─── Convert Lead to Customer ─────────────────────────────────
print("\n=== TEST 10: Convert Lead to Customer ===")
status, resp = req("POST", f"/api/leads/{LEAD_ID}/convert", {
    "customer_type": "wholesaler",
    "payment_mode_preference": "prepaid",
    "notes": "Converted after sample order confirmed",
}, TOKEN)
assert status == 201, f"Convert failed: {resp}"
print(f"  ✅ {status} | {resp['message']}")
print(f"           | customer_id={resp['customer_id'][:8]}... | customer_code={resp['customer_code']}")

# ─── Verify lead is now 'won' ─────────────────────────────────
print("\n=== TEST 11: Verify lead status = won ===")
status, resp = req("GET", f"/api/leads/{LEAD_ID}", token=TOKEN)
assert status == 200
assert resp["status"] == "won", f"Expected won, got: {resp['status']}"
assert resp["converted_customer_id"] is not None
print(f"  ✅ {status} | status={resp['status']} | converted_customer_id={resp['converted_customer_id'][:8]}...")

# ─── Double-convert blocked ───────────────────────────────────
print("\n=== TEST 12: Double-convert blocked ===")
status, resp = req("POST", f"/api/leads/{LEAD_ID}/convert", {}, TOKEN)
assert status == 400, f"Expected 400, got {status}: {resp}"
print(f"  ✅ {status} | detail='{resp['detail']}'")

print("\n" + "="*50)
print("✅ ALL TESTS PASSED — Leads Module is LIVE")
print("="*50)
