#!/usr/bin/env python3
import requests

BASE = "http://localhost:8000"

# Login
r = requests.post(f"{BASE}/tenant/login", json={
    "email": "purelevenexim@gmail.com",
    "password": "wM01gkxGCNhJT!",
    "slug": "purelevenexim"
})
token = r.json().get("access_token")
if not token:
    print("LOGIN FAILED:", r.json())
    exit(1)
print(f"✅ Login OK")

headers = {"Authorization": f"Bearer {token}"}

tests = [
    ("GET", "/api/config/shopify-stores"),
    ("GET", "/api/config/delivery-partners"),
    ("GET", "/api/config/notification-channels"),
    ("GET", "/api/config/business-rules"),
]

all_ok = True
for method, path in tests:
    resp = requests.request(method, BASE + path, headers=headers)
    if resp.status_code in (200, 201):
        d = resp.json()
        if isinstance(d, list):
            print(f"✅ {path} → {len(d)} items")
        elif isinstance(d, dict):
            # For business rules check key fields
            keys = list(d.keys())[:5]
            print(f"✅ {path} → {{{', '.join(keys)}, ...}}")
    else:
        print(f"❌ {path} → HTTP {resp.status_code}: {resp.text[:200]}")
        all_ok = False

if not all_ok:
    print("\n⚠️  GET endpoints failed. Aborting.")
    exit(1)

print("\n--- Testing CREATE (POST) operations ---")

# Test POST delivery partner (uses encryption)
r = requests.post(f"{BASE}/api/config/delivery-partners", headers=headers, json={
    "partner_type": "delhivery",
    "display_name": "Test Delhivery",
    "api_key": "test_api_key_12345",
    "is_primary": False
})
if r.status_code == 201:
    partner_id = r.json().get("id")
    print(f"✅ POST /api/config/delivery-partners → Created (id={str(partner_id)[:8]}...)")
else:
    print(f"❌ POST /api/config/delivery-partners → HTTP {r.status_code}: {r.text[:300]}")
    all_ok = False
    partner_id = None

# Test POST shopify store (uses encryption)
r = requests.post(f"{BASE}/api/config/shopify-stores", headers=headers, json={
    "store_name": "Test Store",
    "store_url": "teststore.myshopify.com",
    "api_access_token": "shpat_test_token_abc123",
    "api_client_id": "test_client_id",
    "api_client_secret": "test_client_secret",
    "is_primary": False
})
if r.status_code == 201:
    store_id = r.json().get("id")
    print(f"✅ POST /api/config/shopify-stores → Created (id={str(store_id)[:8]}...)")
else:
    print(f"❌ POST /api/config/shopify-stores → HTTP {r.status_code}: {r.text[:300]}")
    all_ok = False
    store_id = None

# Test POST notification channel
r = requests.post(f"{BASE}/api/config/notification-channels", headers=headers, json={
    "channel_type": "whatsapp",
    "provider": "meta",
    "api_key": "test_notif_key_xyz",
    "is_primary": False
})
if r.status_code == 201:
    channel_id = r.json().get("id")
    print(f"✅ POST /api/config/notification-channels → Created (id={str(channel_id)[:8]}...)")
else:
    print(f"❌ POST /api/config/notification-channels → HTTP {r.status_code}: {r.text[:300]}")
    all_ok = False
    channel_id = None

print("\n--- Testing UPDATE (PUT) operations ---")

# Test PUT delivery partner
if partner_id:
    r = requests.put(f"{BASE}/api/config/delivery-partners/{partner_id}", headers=headers, json={
        "display_name": "Test Delhivery Updated",
        "api_key": "updated_key_99999"
    })
    if r.status_code == 200:
        print(f"✅ PUT /api/config/delivery-partners/{{id}} → Updated")
    else:
        print(f"❌ PUT /api/config/delivery-partners/{{id}} → HTTP {r.status_code}: {r.text[:300]}")
        all_ok = False

print("\n--- Testing DELETE operations ---")

# Cleanup: delete created records
for resource, rid, label in [
    ("delivery-partners", partner_id, "delivery partner"),
    ("shopify-stores", store_id, "shopify store"),
    ("notification-channels", channel_id, "notification channel"),
]:
    if rid:
        r = requests.delete(f"{BASE}/api/config/{resource}/{rid}", headers=headers)
        if r.status_code in (200, 204):
            print(f"✅ DELETE /api/config/{resource}/{{id}} → Deleted {label}")
        else:
            print(f"❌ DELETE /api/config/{resource}/{{id}} → HTTP {r.status_code}: {r.text[:200]}")
            all_ok = False

if all_ok:
    print("\n🎉 All shipping config endpoints working! (GET + POST + PUT + DELETE)")
else:
    print("\n⚠️  Some endpoints failed.")
