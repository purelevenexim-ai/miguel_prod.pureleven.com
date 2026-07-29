# Shopify Order Sync Options — Complete Guide

## Overview
There are **3 main approaches** to sync Shopify orders into Miguel CRM:

1. **Webhooks** (Real-time, Event-driven)
2. **REST API Polling** (Scheduled, Batch)
3. **Hybrid** (Webhooks + Polling)

---

## Option 1: Webhooks (Real-time) ✅ ALREADY IMPLEMENTED

### How It Works
Shopify **pushes** order data to Miguel whenever an event occurs.

```
Shopify Event → Shopify Sends HTTP POST → Miguel Webhook Endpoint → Order Created in DB
```

### Advantages
- ✅ **Real-time**: Orders appear instantly in Miguel (within milliseconds)
- ✅ **Fast**: No polling delay
- ✅ **Efficient**: Only processes actual events (no wasted API calls)
- ✅ **Reliable**: Shopify retries if webhook fails

### Disadvantages
- ❌ **Network dependent**: Requires Shopify to reach your server
- ❌ **Firewall issues**: May not work behind corporate firewall
- ❌ **Public endpoint**: Your webhook URL must be publicly accessible
- ❌ **No historical sync**: Won't fetch old orders automatically

### Current Implementation in Miguel

**Endpoint**: `POST /webhooks/shopify/order-created`

**Events subscribed to:**
- `orders/create` — New order placed
- `orders/updated` — Order details changed
- `orders/paid` — Payment confirmed
- `orders/fulfilled` — Order shipped

**Setup in Shopify:**
1. Go to **Shipping Config** → **Shopify Stores**
2. Enter your **Webhook URL** (e.g., `https://yourdomain.com/webhooks/shopify/order-created`)
3. Shopify will send POST requests whenever events occur

**Status**: ✅ **Available but requires public URL**

---

## Option 2: REST API Polling (Scheduled) ✅ NOW WORKING

### How It Works
Miguel **pulls** order data from Shopify on a regular schedule.

```
Miguel (every 30 min) → Query Shopify REST API → Fetch New/Updated Orders → Save to DB
```

### Advantages
- ✅ **Works offline**: No webhooks needed
- ✅ **Firewall-safe**: You initiate the requests (outbound only)
- ✅ **Historical sync**: Can fetch old orders
- ✅ **Controlled**: You decide when to sync
- ✅ **No URL exposure**: Your server doesn't need to be public

### Disadvantages
- ❌ **Delayed**: Orders appear 1-30 minutes late (depends on polling interval)
- ❌ **API quota**: Each sync uses Shopify API calls (limited per store)
- ❌ **Extra load**: Regular polling even if no new orders
- ❌ **Scalability**: More stores = more API calls

### Current Implementation in Miguel

**Interval**: Every 30 minutes (configurable)

**What it fetches:**
- Orders updated since last sync
- Abandoned checkouts → converted to Leads
- Delhivery shipments for tracking

**Sync Service**: `app/core/shopify_sync_worker.py`

**Manual Trigger**: 
- Orders page → 🛍️ Shopify tab → "Sync Shopify only" button
- Or use API: `POST /api/shipments/sync-shopify`

**Status**: ✅ **NOW WORKING (once you update API token)**

---

## Option 3: Hybrid Approach ✅ RECOMMENDED

### How It Works
Use **both webhooks + polling** together:

```
Real-time Events → Webhooks (instant)
Missed Events → Polling (safety net, every 30 min)
```

### Advantages
- ✅ **Best of both**: Real-time + safety net
- ✅ **Resilient**: If webhooks fail, polling catches missed orders
- ✅ **No data loss**: Nothing falls through the cracks
- ✅ **Fast + Safe**: Instant when webhook works, guaranteed sync via polling
- ✅ **Deduplication**: System automatically prevents duplicate syncs

### Disadvantages
- ⚠️ **Slightly more complex**: Two sync mechanisms
- ⚠️ **More API calls**: Polling runs even if webhooks work (but smart deduplication prevents issues)

### How Miguel Currently Implements This

**Polling Worker** (`shopify_sync_worker.py`):
```python
# Fetches orders updated since last_sync
# Intelligent: Only fetches what changed since last sync
# Includes: abandoned carts, Delhivery auto-detection
```

**Webhook Handler** (`shipments/router.py`):
```python
# POST /webhooks/shopify/order-created
# Processes instant events from Shopify
# Validates HMAC signature
```

**Deduplication**:
```python
# Uses Shopify order ID as unique key
# If order exists, updates instead of creating duplicate
# Merges data from webhook + polling intelligently
```

---

## Comparison Table

| Feature | Webhooks | Polling | Hybrid |
|---|---|---|---|
| **Real-time?** | ✅ Yes (instant) | ❌ No (delayed) | ✅ Yes (webhooks) + ❌ Fallback (polling) |
| **Works offline?** | ❌ No | ✅ Yes | ✅ Yes |
| **Public endpoint?** | ⚠️ Required | ❌ No | ⚠️ Optional (polling works without it) |
| **Firewall-safe?** | ❌ No | ✅ Yes | ✅ Yes (polling) |
| **Historical sync?** | ❌ No | ✅ Yes | ✅ Yes |
| **API quota cost** | ✅ Low | ⚠️ Medium | ⚠️ Medium |
| **Reliability** | ⚠️ Network dependent | ✅ Guaranteed | ✅ Very high |
| **Data loss risk** | ⚠️ If webhook fails | ❌ None | ❌ None |

---

## Recommended Setup for Production

```
┌─────────────────────────────────────────┐
│         SHOPIFY ADMIN PANEL              │
│  Configure Webhook + API Access Token   │
└──────┬──────────────────────────┬────────┘
       │                          │
       ▼                          ▼
 [Webhook]                  [REST API]
 Real-time events           Polling every 30min
 POST /webhooks/shopify/    GET /orders?updated_at_min=X
 order-created
       │                          │
       └──────────┬───────────────┘
                  ▼
        ┌──────────────────────┐
        │  MIGUEL CRM DATABASE │
        │   (shopify_orders)   │
        │  (smart dedup)       │
        └──────────────────────┘
```

**Best Practice:**
1. ✅ Configure both webhook + polling
2. ✅ Set polling to every 30 minutes (default)
3. ✅ Webhooks handle real-time (if you have public URL)
4. ✅ Polling ensures nothing is missed (even if webhooks fail)

---

## How to Enable/Configure Each Option

### Enable REST API Polling (Currently Recommended)

1. **Update Shopify API Token**:
   - Shipping Config → Shopify Stores
   - Paste valid access token
   - Make sure token has these scopes:
     - `read_orders`
     - `read_checkouts`
     - `read_fulfillments` (optional)

2. **Verify Worker is Running**:
   - Backend logs should show: `✅ shopify_sync_worker started`
   - Check: **Orders** → **🛍️ Shopify** → **Test Fetch**

3. **Adjust Polling Interval** (optional):
   - Edit: `app/core/shopify_sync_worker.py`
   - Change: `await asyncio.sleep(30 * 60)` — in seconds
   - Default: 30 minutes
   - Common: 15 min (more real-time), 60 min (less API calls)

### Enable Webhooks (Advanced)

1. **Make Your Server Public**:
   - Deploy to public domain (not localhost)
   - Example: `https://yourcompany.com/webhooks/shopify/order-created`

2. **Configure in Shopify Admin**:
   - Settings → Apps and integrations → Your app
   - Add webhook subscriptions:
     - Topic: `orders/create` → URL: `https://yourcompany.com/webhooks/shopify/order-created`
     - Topic: `orders/updated` → Same URL
     - Topic: `checkout/create` → Same URL

3. **Verify Webhooks Work**:
   - Go to Shopify: Settings → Apps → Your app → Webhooks
   - Place a test order
   - Check backend logs for: `Webhook received from`

---

## Current Issues & Solutions

### Problem: "Shopify orders API 401"
- **Cause**: Invalid/expired API token
- **Solution**: Update token in Shipping Config (see above)

### Problem: "Webhook not triggering"
- **Cause**: Public URL not reachable, or webhook URL not configured
- **Solution**: 
  1. Test with curl: `curl https://yourdomain.com/`
  2. Verify webhook URL in Shopify admin
  3. Check firewall/NAT rules

### Problem: "Orders duplicated"
- **Cause**: Both webhook + polling syncing same order
- **Solution**: This is normal! System deduplicates automatically by Shopify order ID

### Problem: "Polling never runs"
- **Cause**: API token invalid, or worker didn't start
- **Solution**: 
  1. Check backend logs: `docker compose logs backend | grep -i shopify`
  2. Should see: `🔥 [STARTUP] shopify_sync_worker started`
  3. If not: restart backend

---

## Shopify API Limits

### Rate Limits
- **REST API**: 2 requests per second (120 per minute) per app
- Each polling sync ≈ 2-3 API calls
- 30-min interval = 48-72 calls/day = **Well within limits**

### Query Limits
- Can fetch max 250 orders per API call
- If you have thousands of orders, pagination automatically handles it

---

## API Scopes Required

Your Shopify app **MUST have these scopes**:

```
read_orders           — Fetch order data
read_checkouts        — Fetch abandoned carts
read_fulfillments     — (Optional) Track shipment status
read_products         — (Optional) Product lookups
```

If token is missing scopes:
1. Go to Shopify app configuration
2. Update scopes
3. Request re-authorization from store
4. Generate new access token

---

## Summary: Which Should You Use?

| Your Situation | Recommendation |
|---|---|
| **Small business, want simplicity** | REST API Polling (every 30 min) |
| **Need real-time orders + have public URL** | Webhooks + Polling (hybrid) |
| **Behind corporate firewall** | REST API Polling only |
| **High volume store (1000+ orders/day)** | Webhooks only (to save API calls) |
| **Want guaranteed sync, don't care about delay** | REST API Polling only |
| **Want best of everything** | Hybrid (webhooks + 30-min polling) |

**Current Miguel Setup**: ✅ **REST API Polling (30 min)** + 🔧 **Webhooks available** = Hybrid-ready

---

## Next Steps

1. **Immediate**: Update your Shopify API token in Shipping Config
2. **Verify**: Go to Orders → 🛍️ Shopify → Test Fetch (should show real data)
3. **Optional**: Set up webhooks if you have a public URL
4. **Monitor**: Check backend logs for sync success messages

See: `/opt/miguel/SHOPIFY_SYNC_TROUBLESHOOTING.md` for detailed setup guide.
