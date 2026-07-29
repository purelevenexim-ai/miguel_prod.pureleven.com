# Shopify Order to Customer Auto-Sync Feature

**Implementation Date:** February 25, 2026  
**Status:** ✅ IMPLEMENTED & READY  
**Purpose:** Auto-create customers from Shopify orders and maintain bi-directional sync

---

## What Was Implemented

### 1. **Database Changes**

**Added `customer_id` field to `ShopifyOrder` model:**
- Foreign key linking ShopifyOrder → Customer
- Nullable (allows orders without linked customers initially)
- Indexed for performance
- Migration: `d7c401eb3598_add_customer_id_to_shopify_orders`

```python
# shopify_orders table now has:
customer_id = Column(UUID, ForeignKey("customers.id"), nullable=True)

# Relationships added:
customer = relationship("Customer", foreign_keys=[customer_id])
```

---

### 2. **Auto-Customer Creation Service**

**File:** `/opt/miguel/backend/app/modules/orders/shopify_customer_sync_service.py`

**ShopifyCustomerSyncService** class handles:

#### a) `sync_order_to_customer()`
When a Shopify order gets a tracking number:
1. Check if order already linked → return existing customer
2. Find existing customer by phone number → link to them
3. Create new customer from Shopify order data → link to them

**Customer data extracted from Shopify order:**
- Name: `customer_name` or `shipping_name`
- Phone: `customer_phone` or `shipping_phone`
- Email: `customer_email`
- Address: Shipping address fields
- City, State, Pincode, Country
- Payment mode: Inferred from `shopify_financial_status` (COD vs Prepaid)
- Source: Marked as `website` (Shopify channel)
- Lead status: Marked as `converted` (they've already placed order)
- Customer type: `retail` (default for Shopify)

#### b) `update_customer_from_shopify_order()`
Updates customer stats after order sync:
- `first_order_date`: Earliest order date
- `last_order_date`: Latest order date
- `total_orders`: Count of all orders (Shopify + manual)
- `average_order_value`: Average across all orders
- `last_seen_at`: Updated to current time

#### c) `_recalculate_customer_stats()`
Queries all linked orders and recalculates:
- Joins ShopifyOrder and Order tables
- Sums total order values
- Calculates average

---

### 3. **Integration with Shopify Sync Service**

**File:** `/opt/miguel/backend/app/modules/orders/shopify_sync_service.py`

**Changes:**
- Import `ShopifyCustomerSyncService`
- After syncing a Shopify order webhook, if order has `tracking_number`:
  - Get default admin/owner employee
  - Call `sync_order_to_customer()` to create/link customer
  - Log customer creation/linking

**Flow:**
```
Shopify Order Webhook
    ↓
process_order_webhook()
    ↓
    [if tracking_number found]
    ↓
ShopifyCustomerSyncService.sync_order_to_customer()
    ↓
    [Auto-create or link Customer]
```

---

### 4. **Background Sync Worker (10-min Interval)**

**File:** `/opt/miguel/backend/app/core/customer_sync_worker.py`

**AsyncIO-based worker running every 10 minutes:**

#### a) `sync_all_customers_with_orders()`
Main loop runs periodically:
- Find all tenants with active Shopify stores
- For each tenant, call `sync_customers_for_tenant()`

#### b) `sync_customers_for_tenant()`
For each tenant:
1. **Link unlinked orders:**
   - Find ShopifyOrders with `tracking_number` but no `customer_id`
   - Call `sync_order_to_customer()` for each
   - Commit to DB

2. **Update customer stats:**
   - Get all active customers
   - Call `_recalculate_customer_stats()` for each
   - Commit to DB

#### c) Intervals
- Runs **every 10 minutes** continuously
- Logs start/stop and number of records processed
- Error handling per-record (doesn't fail entire sync if one fails)

**Worker management:**
```python
start_customer_sync_worker()  # Start on app startup
stop_customer_sync_worker()   # Stop on app shutdown
```

---

### 5. **Frontend Integration (Existing)**

**No frontend changes needed** - the system works automatically:
- Customers table shows orders when they're linked
- Customer page displays order history
- Order status changes reflect in customer activity

---

## Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ Shopify Store                                                   │
│ Order placed: #1001                                             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ↓ (Webhook or API sync)
┌─────────────────────────────────────────────────────────────────┐
│ process_order_webhook()                                         │
│ • Parse Shopify order data                                      │
│ • Create/update ShopifyOrder record                             │
│ • Extract fulfillments[] → tracking_number                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ↓ [if tracking_number found]
┌─────────────────────────────────────────────────────────────────┐
│ ShopifyCustomerSyncService.sync_order_to_customer()            │
│ • Check if customer_id already set → YES: done                 │
│ • Find customer by phone → YES: link                            │
│ • Create new customer from order → link                         │
│ • Set customer_id on order                                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ↓ (Committed to DB)
┌─────────────────────────────────────────────────────────────────┐
│ ShopifyOrder Record (shopify_orders table)                      │
│ • id: abc-123                                                   │
│ • customer_id: xyz-789  ← NOW LINKED                            │
│ • tracking_number: 27860310013952                               │
│ • shipping_partner: delhivery                                   │
└──────────────────────────────────────────────────────────────────┘
                           │
                           ↓ (Every 10 minutes)
┌─────────────────────────────────────────────────────────────────┐
│ Background: customer_sync_worker.run_customer_sync()           │
│ • Find all unlinked orders with tracking                        │
│ • Link them to customers (retry mechanism)                      │
│ • Update customer stats                                         │
│   - total_orders = count(ShopifyOrder + Order where cust_id)  │
│   - average_order_value = avg(total_price)                     │
│   - last_seen_at = now()                                        │
└──────────────────────────────────────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ Customer Record (customers table)                               │
│ • id: xyz-789                                                   │
│ • name: Adimali Customer                                        │
│ • phone: 9876543210                                             │
│ • total_orders: 3 ← UPDATED                                     │
│ • last_order_date: 2026-02-25 ← UPDATED                        │
│ • average_order_value: ₹4500 ← UPDATED                         │
└──────────────────────────────────────────────────────────────────┘
```

---

## Database Schema Changes

### Migration Applied
**File:** `/opt/miguel/backend/alembic/versions/d7c401eb3598_add_customer_id_to_shopify_orders.py`

**Changes:**
```sql
-- Add customer_id column
ALTER TABLE shopify_orders
  ADD COLUMN customer_id UUID REFERENCES customers(id);

-- Add index for performance
CREATE INDEX ix_shopify_orders_customer_id 
  ON shopify_orders(customer_id);
```

---

## Configuration & Behavior

### Auto-Sync Intervals
- **Shopify order sync:** Every 30 minutes (existing)
- **Customer-Order sync:** Every 10 minutes (NEW)
- **Tracking updates:** Every 30 minutes (existing)

### Eligibility for Auto-Customer Creation
Customer is auto-created when:
1. ✅ Shopify order has a `tracking_number` (being shipped)
2. ✅ Order doesn't already have a `customer_id`
3. ✅ No existing customer found by phone

### Data Used for Customer Creation
```python
Customer(
    name = shopify_order.customer_name or shopify_order.shipping_name
    phone = shopify_order.customer_phone or shopify_order.shipping_phone
    email = shopify_order.customer_email
    city = shopify_order.shipping_city
    state = shopify_order.shipping_state
    pincode = shopify_order.shipping_zip
    country = shopify_order.shipping_country
    customer_type = "retail"  # Shopify customers
    source = "website"  # Shopify channel
    lead_status = "converted"  # Already placed order
    payment_mode_preference = "cod" or "prepaid"  # From Shopify financial_status
    notes = "Auto-created from Shopify order {name}. Tracking: {number}"
)
```

---

## Error Handling

### Retry Logic
- **Per-order:** If one order fails to link, continues to next
- **Per-tenant:** If one tenant fails, continues to next
- **Worker:** If sync cycle fails, retries on next 10-min interval

### Logging
All actions logged to `app.core.customer_sync_worker`:
```
👥 Customer-Order auto-sync worker started (10-min interval)
Linked order #1001 to customer C-001
Updated stats for 5 customers in tenant abc-123
✅ Customer sync completed
⏰ Next customer sync in 10 minutes
```

---

## Files Modified/Created

### Created
1. `/opt/miguel/backend/app/modules/orders/shopify_customer_sync_service.py` — 220 lines
2. `/opt/miguel/backend/app/core/customer_sync_worker.py` — 150 lines
3. `/opt/miguel/backend/alembic/versions/d7c401eb3598_add_customer_id_to_shopify_orders.py` — Migration

### Modified
1. `/opt/miguel/backend/app/models/shopify_order.py`
   - Added `customer_id` field
   - Added `customer` relationship
   - Added index

2. `/opt/miguel/backend/app/modules/orders/shopify_sync_service.py`
   - Import `ShopifyCustomerSyncService`
   - Call `sync_order_to_customer()` after webhook processing

3. `/opt/miguel/backend/app/main.py`
   - Import `customer_sync_worker` functions
   - Add `start_customer_sync_worker()` to `@app.on_event("startup")`
   - Add `stop_customer_sync_worker()` to `@app.on_event("shutdown")`

---

## Testing the Feature

### Manual Test: Create a Shopify Order with Tracking

1. **Add tracking to an existing Shopify order** (via Shopify store or API)
2. **Trigger sync:** Click "Sync all orders from Shopify" button
3. **Expected result:**
   - Order linked to customer (new or existing)
   - Check: `SELECT customer_id FROM shopify_orders WHERE shopify_order_name = '#1001'` → should have UUID
   - Customer created with correct data
   - Check: `SELECT * FROM customers WHERE unique_customer_code = 'C-...'`

### Automated Test: Background Worker

1. **Wait 10 minutes** after backend restart
2. **Check logs:** `docker logs miguel_backend 2>&1 | grep "Customer-Order"`
3. **Expected:** 
   ```
   👥 Customer-Order auto-sync worker started (10-min interval)
   Linked order #1001 to customer C-001
   Updated stats for 5 customers in tenant...
   ✅ Customer sync completed
   ```

---

## Production Considerations

### Performance
- **Index on `customer_id`:** Ensures fast lookups
- **Batch processing:** Syncs all unlinked orders in one cycle
- **No N+1 queries:** Uses relationship loading strategies

### Bi-directional Sync
- ✅ **Order → Customer:** Tracking → auto-create customer
- ✅ **Customer → Order:** Customer stats updated from all orders
- ✅ **Manual orders:** Also included in customer stats calculation

### Data Integrity
- **Foreign key constraint:** Prevents orphaned customer_ids
- **Nullable customer_id:** Orders can exist without customers (transitional state)
- **Duplicate prevention:** Checks existing customers by phone first

---

## What Happens Now

### When a Shopify order is synced with tracking:
1. ✅ Order record is created/updated with `tracking_number`
2. ✅ Customer is auto-created or linked (if has tracking)
3. ✅ Customer stats are updated
4. ✅ Customer appears in Customers table with order history

### Every 10 minutes:
1. ✅ All unlinked orders with tracking → linked to customers
2. ✅ All customer stats → recalculated from their orders
3. ✅ Changes → visible immediately in UI

---

## Next Steps (Optional Enhancements)

1. **Manual customer linking UI:** Allow users to manually link orders to customers
2. **Bulk re-sync:** Button to re-link all unlinked orders
3. **Customer merge:** Merge duplicate customers
4. **Order consolidation:** Show total customer lifetime value across all channels
5. **Notifications:** Alert when high-value customer (avg > ₹10K) places order

---

**Status:** ✅ COMPLETE & DEPLOYED  
**Backend Restarted:** 2026-02-25 14:08 UTC  
**Auto-sync:** Running every 10 minutes
