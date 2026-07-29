import requests, json

BASE = "http://localhost:8000"
resp = requests.post(f"{BASE}/tenant/login", json={
    "email": "purelevenexim@gmail.com",
    "password": "prfRwEoBep&Nw8",
    "slug": "purelevenexim",
})
TOKEN = resp.json()["access_token"]
H = {"Authorization": f"Bearer {TOKEN}"}

r = requests.get(f"{BASE}/api/products/", headers=H)
print("STATUS:", r.status_code)
d = r.json()
print("TYPE:", type(d).__name__)
if isinstance(d, dict):
    print("KEYS:", list(d.keys()))
    items = d.get("items") or d.get("products") or d.get("data") or []
    print("items count:", len(items))
    if items:
        print("First item keys:", list(items[0].keys()))
elif isinstance(d, list):
    print("LIST len:", len(d))
    if d:
        print("First item keys:", list(d[0].keys()))
