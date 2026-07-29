# Shopify Sync Architecture — Visual Guide

## Architecture Diagram

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                          SHOPIFY STORE                                     ║
║                    (pureleven.myshopify.com, etc)                          ║
╚═══════════════════════════════════════════════════════════════════════════╝
                    ▲                                    ▲
                    │                                    │
         ┌──────────┴──────────┐          ┌──────────────┴─────────────┐
         │                     │          │                            │
         │                     │          │                            │
    [OPTION 1]            [OPTION 2]   [OPTION 3]
    WEBHOOKS              POLLING      BOTH
    Real-time            Scheduled    (Recommended)
         │                     │          │
         │                     │          │
         ▼                     ▼          ▼
    POST Event          GET /orders?    Both paths
    (Instant)          updated_at=X     converge
                      (Every 30 min)
         │                     │          │
         └──────────┬──────────┘          │
                    │◄─────────────────────┘
                    │
         ┌──────────▼──────────────────┐
         │                             │
         │  MIGUEL CRM WEBHOOK         │
         │  POST /webhooks/shopify/    │
         │  order-created              │
         │  (Validates HMAC)           │
         │                             │
         │  OR                         │
         │                             │
         │  SHOPIFY SYNC WORKER        │
         │  (Every 30 minutes)         │
         │  REST API polling           │
         │                             │
         └──────────┬──────────────────┘
                    │
         ┌──────────▼──────────────────┐
         │                             │
         │  DEDUPLICATION ENGINE       │
         │  (Check if order exists)    │
         │  - By Shopify Order ID      │
         │  - Merge new data           │
         │  - Prevent duplicates       │
         │                             │
         └──────────┬──────────────────┘
                    │
         ┌──────────▼──────────────────────────────┐
         │                                         │
         │  MIGUEL DATABASE                        │
         │  ┌─────────────────────────────────┐   │
         │  │ shopify_orders                  │   │
         │  │ - order_id (Shopify)            │   │
         │  │ - customer_name, phone, email   │   │
         │  │ - items, total price            │   │
         │  │ - status, fulfillment           │   │
         │  │ - created_at, updated_at        │   │
         │  └─────────────────────────────────┘   │
         │  ┌─────────────────────────────────┐   │
         │  │ shipping_info                   │   │
         │  │ - tracking_number               │   │
         │  │ - courier (Delhivery, etc)      │   │
         │  │ - delivery status               │   │
         │  └─────────────────────────────────┘   │
         │                                         │
         └─────────────────────────────────────────┘
                    │
                    │ (Frontend queries)
                    │
         ┌──────────▼──────────────────┐
         │                             │
         │  MIGUEL FRONTEND            │
         │  Orders → 🛍️ Shopify Tab   │
         │  - Display orders           │
         │  - Manage tracking          │
         │  - Assign couriers          │
         │                             │
         └─────────────────────────────┘
```

---

## Data Flow: Webhooks (Real-time)

```
Customer Places Order in Shopify
        │
        ▼
Shopify: Order Created Event
        │
        ├─ Generate HMAC signature
        ├─ Prepare JSON payload
        │
        ▼
Shopify sends POST to:
https://yourcompany.com/webhooks/shopify/order-created
        │
        ▼
Miguel Webhook Endpoint
        │
        ├─ Verify HMAC signature (security)
        ├─ Check if order exists
        ├─ If new: Create shopify_order record
        ├─ If exists: Update with new data
        │
        ▼
Response: 200 OK
(Shopify marks delivery as successful)
        │
        ▼
Order visible in Miguel
(within seconds)
```

---

## Data Flow: REST API Polling

```
Miguel Background Worker
(Starts at app boot)
        │
        ▼
Every 30 minutes:
        │
        ├─ Query database for last sync time
        ├─ Calculate: last_sync = now() - 30 minutes
        │
        ▼
Call Shopify REST API:
GET https://pureleven.myshopify.com/admin/api/2024-01/orders.json
    ?updated_at_min=2026-02-25T10:00:00Z
    &status=any
    &fields=id,name,email,customer,total_price,...
        │
        ├─ Verify API token (Bearer token in header)
        │
        ▼
Shopify returns:
{
  "orders": [
    {
      "id": 123456,
      "name": "#1001",
      "email": "customer@example.com",
      "customer": {...},
      "total_price": "5000.00",
      ...
    },
    ...
  ]
}
        │
        ▼
Process Each Order:
        │
        ├─ Check if order exists (by shopify_id)
        ├─ If new: INSERT into shopify_orders
        ├─ If exists: UPDATE with latest data
        ├─ Auto-detect Delhivery shipments
        ├─ Create/update shipping_info
        │
        ▼
Update last_sync timestamp
        │
        ▼
Sleep 30 minutes
        │
        ▼
Repeat...
```

---

## Data Flow: Hybrid (Recommended)

```
                    Shopify Events
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    New Order      Order Updated    Abandoned Cart
         │               │               │
         ├─ Webhook      │ Webhook      ├─ Polling
         │ (instant)     │ (instant)    │ (30 min)
         │               │              │
         ▼               ▼              ▼
    ┌────────────────────────────────────────┐
    │  MIGUEL CRM SYNC ENGINE                │
    │  ┌──────────────────────────────────┐  │
    │  │ Is this order already in DB?     │  │
    │  │ (Check by Shopify Order ID)      │  │
    │  └──┬───────────────────────────────┘  │
    │     │                                   │
    │  ┌──┴──────────────────────────────┐  │
    │  │                                  │  │
    │  ▼ (No)                             ▼ (Yes)
    │ CREATE new record          MERGE: Update existing +
    │ + All order data           add new data from webhook
    │ + Set created_at           + Update updated_at
    │                            + Keep existing tracking
    │                            (if webhook has no tracking)
    │
    └──────────────┬───────────────────┘
                   │
         ┌─────────▼──────────┐
         │  Result: Single    │
         │  canonical record  │
         │  for each order    │
         │  (No duplicates!)  │
         │                    │
         └────────────────────┘
```

---

## Sync Timing Comparison

```
SCENARIO: Customer places order at 10:15 AM

Option 1: WEBHOOKS ONLY
─────────────────────────
10:15:00 - Order placed in Shopify
10:15:01 - Webhook fires
10:15:02 - Order appears in Miguel ✅
          (2 seconds delay)

Option 2: POLLING ONLY (every 30 min)
─────────────────────────────────────
10:15:00 - Order placed in Shopify
10:15:01 - Polling script next runs at...
10:45:00 - Order synced to Miguel ✅
          (30 minutes delay)

Option 3: HYBRID (RECOMMENDED)
──────────────────────────────
10:15:00 - Order placed in Shopify
10:15:01 - Webhook fires
10:15:02 - Order appears in Miguel ✅
          (2 seconds delay via webhook)
10:45:00 - Polling runs (finds no new orders)
          ✅ Acts as safety net
```

---

## API Call Volume Comparison

```
SCENARIO: 100 new Shopify orders placed in 24 hours

Option 1: WEBHOOKS ONLY
────────────────────────
API Calls: 100 (one per order event)
Cost: Very low
Quota: ✅ Well within limits (120/min)

Option 2: POLLING ONLY (every 30 min)
──────────────────────────────────────
Polling cycles in 24h: 48 (every 30 min)
API calls per cycle: ~2 (pagination for 100 orders)
Total API calls: 96
Cost: Low
Quota: ✅ Well within limits

Option 3: HYBRID (WEBHOOKS + POLLING)
──────────────────────────────────────
Webhook calls: 100
Polling calls: 96 (safety net)
Total: 196 calls
Cost: Still low (rate limit is 7200/day)
Quota: ✅ Still 35x within limits
Benefit: Guaranteed sync + real-time
```

---

## Error Recovery: What Happens If...

```
Scenario 1: WEBHOOK FAILS (network issue)
──────────────────────────────────────────
10:15:00 - Order placed
10:15:01 - Webhook fails (network timeout)
10:15:02 - Shopify retries (up to 5 times)
10:16:00 - Still fails after retries
10:45:00 - Polling sync runs
10:45:30 - Order synced by polling ✅
Result: No data loss, order eventually synced

Scenario 2: API TOKEN EXPIRED
──────────────────────────────
Orders placed in Shopify: ✅ Yes
Webhook attempts: ✅ Yes (still fires)
Webhook processing: ❌ Fails (401 Unauthorized)
Result: Webhook backs up, order not synced yet
Fix: Update API token → Resume sync

Scenario 3: DATABASE DOWN
────────────────────────
Webhook received: ✅ Yes
Database insert: ❌ Fails
Webhook retry: ✅ Shopify retries
Result: Eventually synced once DB is up

Scenario 4: PUBLIC URL NOT REACHABLE
────────────────────────────────────
Webhooks configured: ✅ Yes
Webhook fires: ❌ Cannot reach URL
Shopify retries: ❌ Still fails
10:45:00 - Polling runs: ✅ Works!
Result: Polling catches all orders ✅
Benefit: Hybrid is resilient!
```

---

## Configuration Checklist

### For Polling (Current Setup)

- [ ] Shopify API access token obtained
- [ ] Token pasted in Shipping Config
- [ ] Token has `read_orders` scope
- [ ] Backend running (`docker compose up`)
- [ ] Worker logged in logs: `✅ shopify_sync_worker started`
- [ ] Test Fetch shows real orders
- [ ] Orders appearing in Miguel (check after 5 min)

### For Webhooks (Optional, Advanced)

- [ ] Server has public URL (not localhost)
- [ ] Webhook URL configured in Shopify admin
- [ ] Shopify can reach your server (test with curl)
- [ ] Endpoint `/webhooks/shopify/order-created` exists
- [ ] HMAC signature verification working
- [ ] Test order placed, order appears in 2-5 seconds

### For Hybrid (Recommended)

- [ ] ✅ Polling configured (see above)
- [ ] ✅ Webhooks configured (see above)
- [ ] Orders sync via webhook (instant)
- [ ] Orders sync via polling (fallback)
- [ ] No duplicates (deduplication working)
- [ ] Both mechanisms in Shipping Config UI

---

## Troubleshooting Quick Reference

| Problem | Solution |
|---|---|
| No orders syncing | Update API token in Shipping Config |
| "API 401" errors | Token expired/invalid, regenerate in Shopify admin |
| Webhook not firing | Check public URL is reachable |
| Orders duplicated | Normal! System deduplicates automatically |
| Slow sync (30+ min) | Using polling only; enable webhooks for instant sync |
| Worker not running | Check logs: `docker compose logs backend \| grep shopify` |
| Only old orders, no new ones | Polling only sees orders since last_sync; use webhook for instant updates |

---

## Quick Start: Next 5 Minutes

```
1. Go to your Shopify admin
   → Get fresh API access token

2. Go to Miguel Admin
   → Shipping Config → Shopify Stores
   → Paste new token
   → Save

3. Check backend logs
   → docker compose logs backend | grep shopify

4. Go to Orders page
   → 🛍️ Shopify tab
   → Click "Test Fetch"
   → See real orders appear

5. Place test order in Shopify
   → Check Miguel within 30 seconds
   → If using webhooks: ~2 seconds
   → If polling only: wait for next sync cycle
```

**Done!** Your Shopify sync is now working! 🎉
