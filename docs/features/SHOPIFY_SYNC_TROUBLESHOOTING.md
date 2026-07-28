# Shopify Sync Troubleshooting Guide

## Problem: Shopify Orders Not Syncing

### ✅ Confirmed: Shopify Sync Worker IS Running

The backend logs show:
```
🔥 [STARTUP] Starting background workers...
✅ shopify_sync_worker started
🔥 [STARTUP] All workers started
```

The worker is running successfully! But orders aren't syncing because:

```
Shopify orders API 401: {"errors":"[API] Invalid API key or access token"}
```

This means **the Shopify API credentials stored in the database are either:**
1. **Expired** — Shopify access tokens can expire
2. **Revoked** — You may have regenerated the app token in Shopify admin
3. **Invalid** — The token was entered incorrectly
4. **Wrong permissions** — Token doesn't have `read_orders`, `read_checkouts` scopes

---

## Solution: Update Shopify API Credentials

### Step 1: Verify Your Shopify App Configuration

Go to your Shopify Admin:
1. **Settings** → **Apps and integrations**
2. Find your app (e.g., "Miguel CRM" or similar)
3. Click on it
4. Go to **Configuration**
5. Copy the **Access Token** (if visible)
   - If you don't see it, regenerate: Click **Admin API access token** → **Regenerate**

### Step 2: Update Credentials in Miguel Admin

Go to **Miguel Admin Panel** → **Shipping Config** → **Shopify Stores**:

1. Click on the store to edit
2. Paste the **new/valid Access Token**
3. Save changes
4. The token will be automatically encrypted

### Step 3: Verify Connection

The system will automatically:
- ✅ Encrypt the token in the database
- ✅ Start syncing after ~30 seconds (or next 30-min cycle)
- ✅ Fetch orders and abandoned carts

### Step 4: Test Sync Manually

Go to **Orders** page → **🛍️ Shopify** tab:
- Click **⬆️ Sync All Sources ▾** → **Sync Shopify only**
- Or click **Test Fetch** to see last 5 orders/carts

---

## Required Shopify App Scopes

Your Shopify app must have these permissions:

```
read_orders           — fetch order data
read_checkouts        — fetch abandoned carts
read_fulfillments     — (optional) track shipment status
read_products         — (optional) for product lookups
```

If your token is missing these scopes, you need to:
1. Update the app's scope configuration in Shopify
2. Request re-authorization from your store
3. Generate a new access token with the updated scopes

---

## Auto-Sync Behavior

Once credentials are valid:

| Action | Frequency |
|---|---|
| Automatic sync | Every 30 minutes (background worker) |
| Manual sync | Click "Sync Shopify only" button |
| Full sync | Click "Sync All Sources" (includes Delhivery, etc.) |

Each sync:
- Fetches new/updated orders since last sync
- Fetches abandoned checkouts
- Auto-detects Delhivery shipments for existing orders
- Updates local database

---

## What Gets Synced

### Orders
- Shopify order number
- Customer name, phone, email
- Shipping address
- Order total, items
- Order status (awaiting_shipment, confirmed, fulfilled, etc.)
- Financial status (pending, paid, etc.)

### Abandoned Checkouts
- Converted to **Leads** (source: `website`)
- Customer info from checkout
- Cart contents in notes
- Marked with `[shopify_checkout:id]` tag for deduplication

### Delhivery Auto-Detect
- If order has a Delhivery shipment (by reference), auto-links waybill
- Sets shipping partner to Delhivery
- Fetches tracking status

---

## Checking Sync Status

### In Database
```bash
docker exec miguel_db psql -U miguel_user -d miguel_db -c \
  "SELECT store_url, is_active, last_sync FROM shopify_stores;"
```

### In Backend Logs
```bash
docker compose logs backend --tail=100 | grep -i shopify
```

Look for:
- ✅ `Syncing X Shopify store(s)` — sync started
- ✅ `Processed X orders` — success
- ❌ `API 401` — invalid credentials
- ❌ `Error syncing store` — other errors

---

## Still Not Working?

If sync still fails after updating credentials, check:

1. **Is the backend worker running?**
   ```bash
   docker compose logs backend | grep "Shopify auto-sync"
   ```
   Should show: `🛍️ Shopify auto-sync worker started`

2. **Are there database errors?**
   ```bash
   docker compose logs backend | grep -i "error" | head -20
   ```

3. **Is the store marked active?**
   ```bash
   docker exec miguel_db psql -U miguel_user -d miguel_db -c \
     "SELECT store_url, is_active, api_access_token FROM shopify_stores;"
   ```
   Should show `is_active = t`

4. **Check the sync service directly:**
   - Go to **Orders** → **🛍️ Shopify** tab
   - Click **Test Fetch** button
   - See detailed error message

---

## Manual Sync Without Waiting

Don't want to wait 30 minutes? Use the **Sync Shopify only** button:

1. **Orders** page → **🛍️ Shopify** tab
2. Click **⬆️ Sync All Sources ▾** dropdown
3. Select **Sync Shopify only**
4. Orders sync immediately (no background task)

---

## Contact Support

If you've verified credentials and sync still fails:
- Check the **Test Fetch** error message for clues
- Verify Shopify app has correct scopes
- Ensure API access token is currently valid in Shopify admin
- Check network connectivity (if behind proxy/firewall)
