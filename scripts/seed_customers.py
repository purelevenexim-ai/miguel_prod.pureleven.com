"""
Seed test customers + orders + products for purelevenexim.
"""
import requests, sys

BASE = "http://localhost:8000"

resp = requests.post(f"{BASE}/tenant/login", json={
    "email": "purelevenexim@gmail.com",
    "password": "prfRwEoBep&Nw8",
    "slug": "purelevenexim",
})
if not resp.ok:
    print("Login failed:", resp.text); sys.exit(1)
TOKEN = resp.json()["access_token"]
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
print("Logged in OK")

def post(path, body):
    r = requests.post(f"{BASE}{path}", headers=H, json=body)
    if not r.ok:
        print(f"  FAIL {path}: {r.status_code} {r.text[:200]}")
        return None
    return r.json()

def get(path):
    r = requests.get(f"{BASE}{path}", headers=H)
    return r.json() if r.ok else None

# Products
print("\n-- Products --")
pd = get("/api/products/?page=1&page_size=50")
products = pd.get("results",[]) if pd else []

if not products:
    for p in [
        {"name":"PureLeven Turmeric Powder","sku":"PLV-TUR-100G","category":"Spices","unit":"gram","unit_value":"100","unit_label":"100g","unit_price":80,"mrp":90,"cost_price":45,"hsn_code":"0910","gst_rate":5,"tax_inclusive":False,"status":"active"},
        {"name":"PureLeven Red Chilli Powder","sku":"PLV-CHI-100G","category":"Spices","unit":"gram","unit_value":"100","unit_label":"100g","unit_price":95,"mrp":110,"cost_price":52,"hsn_code":"0904","gst_rate":5,"tax_inclusive":False,"status":"active"},
        {"name":"PureLeven Coriander Powder","sku":"PLV-COR-100G","category":"Spices","unit":"gram","unit_value":"100","unit_label":"100g","unit_price":70,"mrp":80,"cost_price":38,"hsn_code":"0909","gst_rate":5,"tax_inclusive":False,"status":"active"},
        {"name":"PureLeven Garam Masala","sku":"PLV-GAR-100G","category":"Masala Blends","unit":"gram","unit_value":"100","unit_label":"100g","unit_price":120,"mrp":140,"cost_price":68,"hsn_code":"0910","gst_rate":5,"tax_inclusive":False,"status":"active"},
        {"name":"PureLeven Combo Pack (4-in-1)","sku":"PLV-COMBO-4","category":"Combo Packs","unit":"pack","unit_value":"4","unit_label":"4x100g","unit_price":340,"mrp":380,"cost_price":190,"hsn_code":"0910","gst_rate":5,"tax_inclusive":False,"status":"active"},
    ]:
        r = post("/api/products/", p)
        if r: products.append(r); print(f"  Created: {r['name']}")
print(f"  Total products: {len(products)}")

if not products:
    print("No products! Cannot seed orders."); sys.exit(1)

# Customers + Orders
SEED = [
    {"cust":{"name":"Priya Sharma","phone":"9876543210","address":"12 Rose Garden Colony","city":"Mumbai","state":"Maharashtra","pincode":"400001","customer_type":"retail","source":"whatsapp"},
     "orders":[{"items":[{"p":0,"q":2},{"p":2,"q":1}],"pay":"cod"},{"items":[{"p":4,"q":1}],"pay":"prepaid","tr":"EE123456789IN","co":"India Post"}]},
    {"cust":{"name":"Rahul Mehta","phone":"9123456780","address":"45 MG Road","city":"Bangalore","state":"Karnataka","pincode":"560001","customer_type":"wholesale","source":"meta_ads"},
     "orders":[{"items":[{"p":0,"q":10},{"p":1,"q":10},{"p":2,"q":10}],"pay":"prepaid","tr":"EE987654321IN","co":"DTDC"}]},
    {"cust":{"name":"Sunita Verma","phone":"9988776655","address":"78 Gandhi Nagar","city":"Jaipur","state":"Rajasthan","pincode":"302001","customer_type":"retail","source":"manual"},
     "orders":[{"items":[{"p":3,"q":2}],"pay":"cod"}]},
    {"cust":{"name":"Arun Pillai","phone":"9444333222","address":"23 Nehru Street","city":"Chennai","state":"Tamil Nadu","pincode":"600001","customer_type":"distributor","source":"website"},
     "orders":[{"items":[{"p":0,"q":20},{"p":1,"q":20},{"p":2,"q":20},{"p":3,"q":20}],"pay":"prepaid","tr":"EE112233445IN","co":"Blue Dart"},{"items":[{"p":4,"q":5}],"pay":"cod"}]},
    {"cust":{"name":"Deepa Nair","phone":"9666555444","address":"5 Patel Chowk","city":"Ahmedabad","state":"Gujarat","pincode":"380001","customer_type":"retail","source":"whatsapp"},
     "orders":[{"items":[{"p":1,"q":2},{"p":3,"q":1}],"pay":"cod"}]},
    {"cust":{"name":"Vikram Singh","phone":"9711223344","address":"67 Civil Lines","city":"Lucknow","state":"Uttar Pradesh","pincode":"226001","customer_type":"retail","source":"meta_ads"},
     "orders":[{"items":[{"p":4,"q":2}],"pay":"prepaid","tr":"EE556677889IN","co":"Delhivery"}]},
]

print("\n-- Customers + Orders --")
for entry in SEED:
    cd = entry["cust"]
    cust = post("/api/customers/", cd)
    if not cust: continue
    cid = cust["id"]
    print(f"  Customer: {cd['name']} [{cid[:8]}]")
    for od in entry["orders"]:
        items = []
        total = 0
        for it in od["items"]:
            pidx = min(it["p"], len(products)-1)
            pr = products[pidx]
            qty = it["q"]
            price = float(pr["unit_price"])
            line = round(qty * price, 2)
            total += line
            items.append({"product_id":pr["id"],"product_name":pr["name"],"quantity":qty,"unit":pr["unit"],"unit_price":price,"line_total":line})
        ob = {"customer_id":cid,"items":items,"payment_method":od["pay"],"delivery_address":cd.get("address",""),"delivery_city":cd.get("city",""),"delivery_state":cd.get("state",""),"delivery_pincode":cd.get("pincode",""),"notes":"Test order"}
        if od.get("tr"): ob["tracking_number"] = od["tr"]
        if od.get("co"): ob["courier_name"] = od["co"]
        order = post("/api/orders/", ob)
        if order: print(f"    Order: {order.get('order_number','?')} Rs.{total:.0f} {od['pay'].upper()}")

# Stock
print("\n-- Initial Stock --")
for i, p in enumerate(products):
    qty = [500,400,600,300,150][i%5]
    r = post("/api/inventory/adjust",{"product_id":p["id"],"quantity_change":qty,"note":"Initial stock"})
    if r: print(f"  {p['name']}: +{qty}")

print("\nDone!")
