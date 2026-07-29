#!/usr/bin/env python3
"""
Live test suite for Meta Ads Integration Module.
Run: python3 /opt/miguel/test_meta.py
"""
import json
import urllib.request
import urllib.error
import urllib.parse

BASE  = "http://172.232.118.208:8000"
PASS  = 0
FAIL  = 0

# ─── Helpers ─────────────────────────────────────────────────

def req(method, path, body=None, token=None):
    url  = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    hdrs = {"Content-Type": "application/json"}
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {}

def req_raw(method, path, body=None, token=None):
    """Return (status, raw_bytes, headers_dict)."""
    url  = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    hdrs = {"Content-Type": "application/json"}
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, resp.read(), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), {}

def ok(label, condition, got=None):
    global PASS, FAIL
    if condition:
        print(f"  ✅ {label}")
        PASS += 1
    else:
        print(f"  ❌ {label}" + (f" got {got}" if got is not None else ""))
        FAIL += 1

# ─── Login ───────────────────────────────────────────────────
print("=== LOGIN ===")
s, r = req("POST", "/tenant/login", {
    "slug": "purelevenexim",
    "email": "purelevenexim@gmail.com",
    "password": "HgI*B5usv750Qh",
})
assert s == 200, f"Login failed: {r}"
TOKEN = r["access_token"]
print(f"  ✅ {s} | role={r['role']}")

# Need a valid employee ID for default_assignee
print("\n=== SETUP: Get employee list ===")
s, r = req("GET", "/tenant/employees", token=TOKEN)
ok("Employees list 200", s == 200, r)
employees = r if isinstance(r, list) else r.get("employees", [])
EMPLOYEE_ID = employees[0]["id"] if employees else None
print(f"  ℹ️  employee_id = {str(EMPLOYEE_ID)[:8] if EMPLOYEE_ID else 'None'}...")

# ─── TEST 1: Create integration ───────────────────────────────
print("\n=== TEST 1: Create Meta integration ===")
s, r = req("POST", "/api/meta/integrations", {
    "page_id":             "111222333444555",
    "page_name":           "Pure Leven Exim — Facebook Page",
    "access_token":        "EAAB_FAKE_TOKEN_FOR_TESTING_12345",
    "default_assignee_id": EMPLOYEE_ID,
    "is_active":           True,
}, token=TOKEN)
ok("Create integration 201", s == 201, r)
if s == 201:
    INTEGRATION_ID = r["id"]
    ok("Has id", "id" in r)
    ok("Has page_id", r.get("page_id") == "111222333444555")
    ok("Has page_name", "page_name" in r)
    ok("access_token NOT in response", "access_token" not in r)
    ok("default_assignee_id set", r.get("default_assignee_id") == EMPLOYEE_ID)
    print(f"  integration_id = {INTEGRATION_ID[:8]}...")
else:
    INTEGRATION_ID = None
    print(f"  Detail: {r}")

# ─── TEST 2: Duplicate page_id → 409 ─────────────────────────
print("\n=== TEST 2: Duplicate page_id → 409 ===")
s, r = req("POST", "/api/meta/integrations", {
    "page_id":      "111222333444555",
    "access_token": "another_token",
}, token=TOKEN)
ok("Duplicate page_id → 409", s == 409, f"got {s}")

# ─── TEST 3: List integrations ────────────────────────────────
print("\n=== TEST 3: List integrations ===")
s, r = req("GET", "/api/meta/integrations", token=TOKEN)
ok("List 200", s == 200, r)
ok("Returns list", isinstance(r, list))
ok("At least 1 integration", len(r) >= 1)

# ─── TEST 4: Get single integration ──────────────────────────
print("\n=== TEST 4: Get integration by ID ===")
if INTEGRATION_ID:
    s, r = req("GET", f"/api/meta/integrations/{INTEGRATION_ID}", token=TOKEN)
    ok("Get 200", s == 200, r)
    ok("Correct ID returned", r.get("id") == INTEGRATION_ID)
else:
    ok("Skipped (no integration_id)", False, "create failed")

# ─── TEST 5: Update integration ───────────────────────────────
print("\n=== TEST 5: Update integration (change page_name + disable) ===")
if INTEGRATION_ID:
    s, r = req("PATCH", f"/api/meta/integrations/{INTEGRATION_ID}", {
        "page_name": "Updated Page Name",
        "is_active": False,
    }, token=TOKEN)
    ok("Update 200", s == 200, r)
    ok("page_name updated", r.get("page_name") == "Updated Page Name")
    ok("is_active now False", r.get("is_active") == False)
    # Re-enable for webhook test
    s2, r2 = req("PATCH", f"/api/meta/integrations/{INTEGRATION_ID}", {"is_active": True}, token=TOKEN)
    ok("Re-enabled for webhook test", s2 == 200 and r2.get("is_active") == True, r2)

# ─── TEST 6: Webhook verification ────────────────────────────
print("\n=== TEST 6: Webhook hub challenge verification ===")
params = urllib.parse.urlencode({
    "hub.mode":         "subscribe",
    "hub.verify_token": "miguel_crm_meta_verify_2026",
    "hub.challenge":    "abc123xyz",
})
s, body, hdrs = req_raw("GET", f"/api/meta/webhook?{params}")
ok("Verification 200", s == 200, s)
ok("Returns challenge text", b"abc123xyz" in body, body.decode())

# ─── TEST 7: Webhook verification — wrong token → 403 ─────────
print("\n=== TEST 7: Webhook verify — wrong token → 403 ===")
params_bad = urllib.parse.urlencode({
    "hub.mode":         "subscribe",
    "hub.verify_token": "wrong_token",
    "hub.challenge":    "abc123",
})
s, body, _ = req_raw("GET", f"/api/meta/webhook?{params_bad}")
ok("Wrong token → 403", s == 403, s)

# ─── TEST 8: Webhook lead ingestion ──────────────────────────
import time as _time
# Use a unique leadgen_id each run to avoid dedup from prior test runs
UNIQUE_LEADGEN_ID = f"meta_lead_test_{int(_time.time())}"

print("\n=== TEST 8: Webhook lead ingestion (simulated Meta payload) ===")
meta_payload = {
    "object": "page",
    "entry": [
        {
            "id": "111222333444555",   # matches our integration
            "changes": [
                {
                    "field": "leadgen",
                    "value": {
                        "leadgen_id": UNIQUE_LEADGEN_ID,
                        "form_id":    "form_abc_123",
                        "page_id":    "111222333444555",
                        "field_data": [
                            {"name": "full_name",     "values": ["Priya Sharma"]},
                            {"name": "phone_number",  "values": ["9876543210"]},
                            {"name": "email",         "values": ["priya@example.com"]},
                            {"name": "city",          "values": ["Kochi"]},
                            {"name": "message",       "values": ["Interested in 25kg flour pack"]},
                        ]
                    }
                }
            ]
        }
    ]
}
s, r = req("POST", "/api/meta/webhook", meta_payload)
ok("Webhook 200", s == 200, r)
ok("processed = 1", r.get("processed") == 1, r)
ok("skipped = 0", r.get("skipped") == 0, r)
ok("errors = 0", r.get("errors") == 0, r)

# Verify the lead was actually created
print("\n=== TEST 9: Lead created with source=meta ===")
s, r = req("GET", "/api/leads/?source=meta", token=TOKEN)
ok("Leads list 200", s == 200, r)
meta_leads = [l for l in r.get("results", r.get("data", [])) if l.get("source") == "meta"]
ok("At least 1 meta lead", len(meta_leads) >= 1, f"found {len(meta_leads)}, keys={list(r.keys())}")
if meta_leads:
    lead = meta_leads[0]
    ok("Lead name is Priya Sharma", lead.get("name") == "Priya Sharma", lead.get("name"))
    ok("Lead phone correct", lead.get("phone") == "9876543210", lead.get("phone"))
    ok("Lead source = meta", lead.get("source") == "meta")
    ok("Lead status = new", lead.get("status") == "new")
    assigned = lead.get("assigned_to_id")
    if EMPLOYEE_ID:
        ok("Lead assigned to default_assignee", assigned == EMPLOYEE_ID, assigned)

# ─── TEST 10: Duplicate leadgen_id → skip ─────────────────────
print("\n=== TEST 10: Duplicate leadgen_id → skipped ===")
s, r = req("POST", "/api/meta/webhook", meta_payload)  # exact same payload = same UNIQUE_LEADGEN_ID
ok("Webhook 200 (always)", s == 200, r)
ok("Duplicate skipped", r.get("skipped") == 1, r)
ok("processed = 0 (not re-processed)", r.get("processed") == 0, r)

# ─── TEST 11: Unknown page_id → skipped ───────────────────────
print("\n=== TEST 11: Unknown page_id → skipped (no integration) ===")
unknown_payload = {
    "object": "page",
    "entry": [{
        "id": "999888777666555",  # not registered
        "changes": [{
            "field": "leadgen",
            "value": {
                "leadgen_id": "meta_lead_unknown_001",
                "form_id": "form_xyz",
                "page_id": "999888777666555",
                "field_data": [
                    {"name": "full_name",    "values": ["Ghost User"]},
                    {"name": "phone_number", "values": ["9000000000"]},
                ]
            }
        }]
    }]
}
s, r = req("POST", "/api/meta/webhook", unknown_payload)
ok("Webhook 200", s == 200, r)
ok("Unknown page_id → skipped", r.get("skipped") == 1, r)

# ─── TEST 12: Non-leadgen field → ignored ─────────────────────
print("\n=== TEST 12: Non-leadgen field in webhook → no-op ===")
s, r = req("POST", "/api/meta/webhook", {
    "object": "page",
    "entry": [{"id": "111222333444555", "changes": [{"field": "feed", "value": {}}]}]
})
ok("Webhook 200", s == 200, r)
ok("processed = 0 for non-leadgen", r.get("processed") == 0, r)

# ─── TEST 13: Webhook log ─────────────────────────────────────
print("\n=== TEST 13: Webhook logs visible ===")
s, r = req("GET", "/api/meta/webhook-logs", token=TOKEN)
ok("Logs 200", s == 200, r)
ok("Has total", "total" in r, r)
ok("Has data array", isinstance(r.get("data"), list))
ok("At least 1 log entry", r.get("total", 0) >= 1, r.get("total"))

# ─── TEST 14: Invalid assignee → 404 ─────────────────────────
print("\n=== TEST 14: Invalid default_assignee_id → 404 ===")
import uuid as _uuid
s, r = req("POST", "/api/meta/integrations", {
    "page_id":             "FAKE_PAGE_999",
    "access_token":        "tok",
    "default_assignee_id": str(_uuid.uuid4()),
}, token=TOKEN)
ok("Bad assignee → 404", s == 404, f"got {s}")

# ─── TEST 15: Delete integration ──────────────────────────────
print("\n=== TEST 15: Delete integration ===")
if INTEGRATION_ID:
    s, body, _ = req_raw("DELETE", f"/api/meta/integrations/{INTEGRATION_ID}", token=TOKEN)
    ok("Delete 204", s == 204, s)
    s, r = req("GET", f"/api/meta/integrations/{INTEGRATION_ID}", token=TOKEN)
    ok("Deleted integration → 404", s == 404, s)

# ─── TEST 16: Auth guard ──────────────────────────────────────
print("\n=== TEST 16: Auth guard — unauthenticated → 401 ===")
s, _ = req("GET", "/api/meta/integrations")
ok("No token → 401", s == 401, s)

# ─── Summary ─────────────────────────────────────────────────
print("\n" + "="*50)
print(f"  Results: {PASS} passed, {FAIL} failed out of {PASS+FAIL} tests")
if FAIL == 0:
    print("  🎉 ALL TESTS PASSED")
else:
    print("  ⚠️  Some tests failed — see above")
print("="*50)
