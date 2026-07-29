# Order Status Auto-Transition Guide

**Date:** February 25, 2026  
**Status:** ✅ Deployed  
**Scope:** Manual Orders & Shopify Orders

---

## Overview

The order module now implements **automatic status transitions** based on order lifecycle events:

1. **On Order Creation** → Status = `confirmed`
2. **When Tracking Assigned** → Status auto-transitions to `shipped`
3. **When Delivered** → Status auto-transitions to `delivered` + Pay Status = `paid`

---

## Order Creation Logic

### Manual Orders (Created via API)
When a new manual order is created:
```
POST /api/orders
{
  "customer_name": "John Doe",
  "delivery_address": "123 Main St",
  ...
}
```

**Result:**
- Order status = `confirmed` (default)
- Ready for shipping assignment

**Code Location:** `/opt/miguel/backend/app/modules/orders/service.py`, lines 558-564

```python
final_status = OrderStatus.confirmed if not is_not_confirmed else OrderStatus.draft

order = Order(
    status=final_status,  # = confirmed
    ...
)
```

### Shopify Orders (Synced from Shopify)
When Shopify orders are imported:
```
POST /api/shipments/shopify-csv-import (CSV/XLSX)
```

**Initial Status:** Based on Shopify fulfillment status:
- "fulfilled" / "shipped" → `fulfilled`
- "partial" → `confirmed`
- Empty / "unconfirmed" → `confirmed`

---

## Tracking Assignment Logic

### When Tracking Number is Assigned

#### Manual Orders — Via API Update
```
PATCH /api/orders/{order_id}
{
  "tracking_number": "EE123456789IN"
}
```

**Auto-Transition:**
- If current status = `confirmed` → advances to `shipped`
- Creates status history entry with note: "Auto-transitioned to shipped: tracking EE123456789IN assigned"
- If already in `shipped` or beyond → no change

**Code Location:** `/opt/miguel/backend/app/modules/orders/service.py`, lines 783-795

```python
# Auto-transition to shipped when tracking number is assigned
if "tracking_number" in updated and updated["tracking_number"] and order.status == OrderStatus.confirmed:
    order.status = OrderStatus.shipped
    history_entry = OrderStatusHistory(
        old_status=OrderStatus.confirmed,
        new_status=OrderStatus.shipped,
        note=f"Auto-transitioned to shipped: tracking {updated['tracking_number']} assigned",
    )
    db.add(history_entry)
```

#### Manual Orders — Via Excel Upload
```
POST /api/shipments/manual-orders/india-post-xlsx
(Excel file with Customer Name + Tracking Number columns)
```

**Auto-Transitions:**
1. **Tracking-only file** (no delivery status) → `confirmed` → `shipped`
2. **Delivery file** (has status="Delivered") → `confirmed` → `delivered` + marked `paid`
3. **Return file** (has status="Return/RTO") → `confirmed` → `returned`

**Code Location:** `/opt/miguel/backend/app/modules/shipments/router.py`, lines 2239-2242

```python
elif not status_val:
    # Tracking-only file: auto-advance to shipped if not already further along
    if order.status not in [OS.shipped, OS.out_for_delivery, OS.delivered, OS.returned]:
        order.status = OS.shipped
        action_taken = "tracking updated → shipped"
```

#### Shopify Orders — Via Excel Upload
```
POST /api/shipments/india-post-xlsx-v2
(Excel file with Order# + Tracking + optional Status columns)
```

**Auto-Transitions:**
1. **Tracking-only** → `confirmed` → `fulfilled`
2. **Delivered** → `confirmed` → `fulfilled` + financial_status = `paid`
3. **Returned** → `confirmed` → `cancelled`

**Code Location:** `/opt/miguel/backend/app/modules/shipments/router.py`, lines 1459-1484

```python
elif not status_val:
    # Tracking-only file: advance to fulfilled (shipped) if not already
    if order.shopify_fulfillment_status not in (
        ShopifyFulfillmentStatus.fulfilled,
        ShopifyFulfillmentStatus.delivered,
        ShopifyFulfillmentStatus.cancelled,
    ):
        order.shopify_fulfillment_status = ShopifyFulfillmentStatus.fulfilled
        order.shopify_status = ShopifyOrderStatus.fulfilled
        action_taken = "tracking updated → fulfilled"
```

---

## Delivery Status Logic

### Manual Orders
When a delivery xlsx is uploaded with "Delivered" status detected:

```
POST /api/shipments/manual-orders/india-post-xlsx
(Excel with Status column containing "Delivered")
```

**Result:**
- Status → `delivered`
- `delivered_at` → current timestamp
- **Payment:** If COD → automatically marked as `paid`, amount_due = 0
- Action logged: "delivered + COD paid ✅"

**Code Location:** `/opt/miguel/backend/app/modules/shipments/router.py`, lines 2227-2238

```python
elif is_delivered:
    order.status = OS.delivered
    order.delivered_at = datetime.now(timezone.utc)
    action_taken = "delivered"
    
    if order.payment_method in (PM.cod, PM.partial_cod, None):
        order.payment_status = PS.paid
        order.amount_paid = order.total_amount
        order.amount_due = _Dec("0")
        action_taken += " + COD paid ✅"
```

### Shopify Orders
When a delivery xlsx is uploaded with "Delivered" status:

```
POST /api/shipments/india-post-xlsx-v2
(Excel with Status column containing "Delivered")
```

**Result:**
- `shopify_fulfillment_status` → `delivered`
- `shopify_status` → `fulfilled`
- `delivered_at` → current timestamp
- **Payment:** `shopify_financial_status` → `"paid"`
- Action logged: "delivered + paid ✅"

**Code Location:** `/opt/miguel/backend/app/modules/shipments/router.py`, lines 1445-1456

```python
elif is_delivered:
    order.shopify_fulfillment_status = ShopifyFulfillmentStatus.delivered
    order.shopify_status = ShopifyOrderStatus.fulfilled
    order.delivered_at = datetime.now(timezone.utc)
    order.shopify_financial_status = "paid"
    action_taken = "delivered + paid ✅"
```

---

## Manual Status Override

Users can still **manually override** the status at any time:

```
PATCH /api/orders/{order_id}
{
  "status": "out_for_delivery"
}
```

**Behavior:**
- Manual status change takes priority
- Auto-transition to shipped does NOT override manual status
- If status is manually set to `delivered`, pay status auto-becomes `paid`

---

## Status Flow Diagram

### Manual Orders

```
┌─────────────┐
│   DRAFT     │ (not_confirmed orders only)
└──────┬──────┘
       │
       ↓
┌─────────────────────────┐
│   CONFIRMED  ◄────────┐ │ (default on creation)
│ (awaiting tracking)   │ │
└──────┬────────────────┤─┘
       │                │
   [Assign Tracking]    │
       │                │
       ↓                │
┌─────────────────────┐ │
│   SHIPPED  ◄────────┤─┤ (auto on tracking)
│ (in courier hands)  │ │
└──────┬──────────────┤─┘
       │              │
  [Report Delivery]   │
   or [Manual Update] │
       │              │
       ↓              │
┌──────────────────┐  │
│   OUT_FOR_DELIVERY ◄┤ (manual only)
└──────┬───────────┘  │
       │              │
  [Confirm Delivery]  │
       │              │
       ↓              │
┌──────────────────┐  │
│   DELIVERED ◄────┤──┤ (auto on delivery file OR manual)
│ (auto: COD paid) │  │
└──────┬───────────┘  │
       │              │
       ↓              │
  [END STATE]         │
                      │
    [Cancellation]────┘
       │
       ↓
┌──────────────────┐
│   CANCELLED      │
│ or RETURNED      │
└──────────────────┘
```

### Shopify Orders

```
┌──────────────────┐
│   CONFIRMED  ◄──┐ (default on creation/import)
│ (awaiting ship)  │
└──────┬───────────┤
       │           │
   [Assign Tracking]
       │           │
       ↓           │
┌──────────────────┤
│   FULFILLED      │ (auto on tracking)
│ (shipped)        │
└──────┬───────────┤
       │           │
  [Report Delivery]│
       │           │
       ↓           │
┌──────────────────┤
│   DELIVERED      │ (auto on delivery file)
│ (auto: paid)     │
└──────┬───────────┤
       │           │
       ↓           │
  [END STATE]      │
                   │
   [Return/RTO]────┘
       │
       ↓
┌──────────────────┐
│   CANCELLED      │
│ or RETURNED      │
└──────────────────┘
```

---

## Testing Scenarios

### Scenario 1: Manual Order Creation → Tracking Assignment
1. Create order via API
   - Status should be `confirmed`
2. Upload India Post xlsx with this order's tracking
   - Status should auto-transition to `shipped`
   - Status history should show "Auto-transitioned to shipped: tracking EE123456789IN assigned"

### Scenario 2: Manual Order Delivery Confirmation
1. Create order via API (status = `confirmed`)
2. Upload India Post xlsx with:
   - Same customer name / tracking
   - Status column = "Delivered"
3. Expected:
   - Status → `delivered`
   - Payment Status → `paid` (if COD)
   - delivered_at → set

### Scenario 3: Shopify Order Import → Tracking
1. Import Shopify CSV with orders (status = `confirmed`)
2. Upload India Post xlsx with Shopify order numbers
3. Expected:
   - shopify_fulfillment_status → `fulfilled`
   - shopify_status → `fulfilled`

### Scenario 4: Manual Override
1. Create order (status = `confirmed`)
2. Upload tracking xlsx (auto-transitions to `shipped`)
3. Manually PATCH with status = `out_for_delivery`
   - Status changes to `out_for_delivery`
   - Stays there (no auto-revert)
4. Manually PATCH with status = `delivered`
   - Status → `delivered`
   - Payment → `paid` (if COD)

---

## Excel File Formats Supported

### Format 1: Tracking Only
```
Column A: Customer Name      | Column B: Tracking Number
John Doe                     | EE123456789IN
Jane Smith                   | RX987654321IN
```

**Result:** Status → `shipped`

### Format 2: Tracking + Delivery Status
```
Column A: Customer Name | Column B: Tracking Number  | Column C: Status
John Doe               | EE123456789IN              | Delivered
Jane Smith            | RX987654321IN              | In Transit
```

**Result:** 
- John Doe: Status → `delivered`, Paid ✅
- Jane Smith: Status → `shipped` (no status detected)

### Format 3: India Post Bulk Report (Hyphenated Headers)
```
article-number | receiver-name | event-description | ...
EE123456789IN  | John Doe      | Delivered        | ...
RX987654321IN  | Jane Smith    | In Transit        | ...
```

**Result:** Auto-detected columns, same logic applies

---

## Configuration & Customization

### Order Status Enum
**File:** `/opt/miguel/backend/app/models/order.py`

```python
class OrderStatus(str, enum.Enum):
    draft = "draft"
    confirmed = "confirmed"
    processing = "processing"
    packed = "packed"
    shipped = "shipped"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    cancelled = "cancelled"
    returned = "returned"
```

To add new statuses, update this enum and database migrations.

### Valid Transitions
**File:** `/opt/miguel/backend/app/modules/orders/service.py`, lines ~1015-1040

```python
_ALLOWED_TRANSITIONS: dict[OrderStatus, list[OrderStatus]] = {
    OrderStatus.draft:            [OrderStatus.confirmed, OrderStatus.cancelled],
    OrderStatus.confirmed:        [OrderStatus.processing, OrderStatus.cancelled, OrderStatus.shipped],
    # ... etc
}
```

Auto-transitions MUST follow these rules or they will be blocked.

---

## API Response Examples

### Manual Order Create
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "order_number": "PRM-260225-001",
  "status": "confirmed",
  "tracking_number": null,
  "payment_status": "pending",
  "created_at": "2026-02-25T10:30:00Z"
}
```

### After Tracking Assigned (via PATCH)
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "order_number": "PRM-260225-001",
  "status": "shipped",  // AUTO-TRANSITIONED
  "tracking_number": "EE123456789IN",
  "updated_at": "2026-02-25T10:35:00Z"
}
```

### Excel Upload Response
```json
{
  "success": true,
  "updated_count": 2,
  "skipped_count": 0,
  "delivered_and_paid": 1,
  "updated": [
    {
      "order_number": "PRM-260225-001",
      "customer": "John Doe",
      "tracking": "EE123456789IN",
      "action": "tracking updated → shipped"
    },
    {
      "order_number": "PRM-260225-002",
      "customer": "Jane Smith",
      "tracking": "RX987654321IN",
      "action": "delivered + COD paid ✅"
    }
  ]
}
```

---

## Troubleshooting

### Issue: Status Not Transitioning to Shipped
**Cause:** Order status is not `confirmed` (already shipped, etc.)  
**Solution:** Check status history. Only `confirmed` orders auto-transition.

### Issue: Tracking Number Not Detected in Excel
**Cause:** Column header doesn't match expected names  
**Solution:** Use standard headers like:
- "Tracking Number"
- "Article Number"
- "AWB"
- "Consignment No"

Or India Post bulk headers:
- "article-number"

### Issue: Delivered But Not Marked Paid
**Cause:** Payment method is not COD  
**Solution:** Only COD/partial_cod auto-mark as paid. For other methods, manually update payment_status.

---

## Related Documentation

- [AUTO_PAY_STATUS_UPDATE_FIX.md](./AUTO_PAY_STATUS_UPDATE_FIX.md) — Payment status logic
- [INDIA_POST_XLSX_UPLOAD_GUIDE.md](./INDIA_POST_XLSX_UPLOAD_GUIDE.md) — Excel upload guide
- [ORDERS_TABLE_FIX_SESSION_2026_02_25.md](./ORDERS_TABLE_FIX_SESSION_2026_02_25.md) — Orders table fixes

---

## Deployment Notes

- **Backward Compatible:** ✅ Existing orders unaffected
- **Migrations:** ✅ No DB schema changes required
- **Rollback:** ✅ Can be disabled by removing auto-transition logic
- **Performance:** ✅ Minimal impact (simple status field update)

---

## Next Steps

1. **Test** with real orders and tracking assignments
2. **Monitor** status history entries for unexpected transitions
3. **Gather feedback** from operations team on auto-transition behavior
4. **Consider** adding UI notifications when status auto-advances
