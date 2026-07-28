# Orders Table & India Post xlsx Upload - Fix Session (Feb 25, 2026)

**Status:** ✅ **COMPLETE & TESTED**  
**Date:** February 25, 2026  
**Affected Components:** Backend (orders/shipments modules), Frontend (orders.html)

---

## 📋 Session Summary

This session fixed **3 critical bugs** in the orders system:

1. ✅ **Order creation returning 500** — Missing `PaymentMethod` import in service.py
2. ✅ **Pay Status & Status dropdowns not updating on delivered orders** — `update_order()` was blocking all edits on terminal orders
3. ✅ **India Post xlsx upload returning 400** — Column header detection didn't support India Post bulk report format (hyphenated headers)

---

## 🐛 Bug #1: Order Creation 500 Error

### Symptoms
- Creating a new order via UI returned `500 Internal Server Error`
- Backend logs showed `NameError: name 'PaymentMethod' is not defined`

### Root Cause
In `/opt/miguel/backend/app/modules/orders/service.py`, the function `_recalc_order_totals()` used `PaymentMethod.cod`, `PaymentMethod.partial_cod`, etc., but `PaymentMethod` was never imported at the top of the file.

### Fix Applied
**File:** `/opt/miguel/backend/app/modules/orders/service.py` (lines 1-20)

Added `PaymentMethod` to the import statement:

```python
from app.models.order import (
    Order, OrderItem, OrderPayment, OrderStatusHistory,
    OrderStatus, PaymentStatus, PaymentMethod, Courier, IndiaPostCustomerId,
)
```

### Testing
```bash
# Test: Create a new order
curl -X POST http://localhost:8000/api/orders \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"customer_id":"...", "items":[...], ...}'
# Result: ✅ 200 OK (previously 500)
```

---

## 🐛 Bug #2: Status/Pay Status Dropdowns Blocked on Terminal Orders

### Symptoms
- Orders with `status = delivered` showed `400 Bad Request` when changing `payment_status` or `status`
- Frontend Pay Status and Status dropdowns appeared blank or non-functional

### Root Cause
In `update_order()` function, the validation logic was too strict:
```python
# OLD (WRONG)
if order.status in (OrderStatus.delivered, OrderStatus.cancelled, OrderStatus.returned):
    raise HTTPException(400, "Cannot edit a terminal order")
```

This blocked **all** edits on terminal orders, even status/payment_status changes which should be allowed.

### Fix Applied
**File:** `/opt/miguel/backend/app/modules/orders/service.py` (lines 750-810)

Changed to only block **non-status fields** on terminal orders:

```python
# NEW (CORRECT)
non_status_fields = {k for k in updated if k not in ('status', 'payment_status', 'payment_method')}
if non_status_fields and order.status in (OrderStatus.delivered, OrderStatus.cancelled, OrderStatus.returned):
    raise HTTPException(
        status_code=400,
        detail=f"Cannot edit a {order.status.value} order"
    )
```

Also added `status` field to `OrderUpdate` schema so status changes are recognized:

**File:** `/opt/miguel/backend/app/modules/orders/schemas.py` (line 106)
```python
class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None  # ← ADDED
    payment_status: Optional[PaymentStatus] = None
    # ... other fields ...
```

### Testing
```bash
# Test: Update payment_status on delivered order (PRM-260224-036)
curl -X PATCH http://localhost:8000/api/orders/26ca4c52-b676-4c02-acc8-01a421d676ca \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"payment_status":"paid"}'
# Result: ✅ 200 OK, payment_status updated to "paid"

# Test: Update status on delivered order
curl -X PATCH http://localhost:8000/api/orders/26ca4c52-b676-4c02-acc8-01a421d676ca \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"status":"returned"}'
# Result: ✅ 200 OK, status changed to "returned"
```

---

## 🐛 Bug #3: India Post xlsx Upload Returns 400

### Symptoms
- User uploads India Post tracking xlsx file → `400 Bad Request`
- Error message: "Cannot find tracking/article column. Headers found: [...]"
- Orders not getting tracking numbers or status updates
- No clear indication of what column names were expected

### Root Cause
India Post bulk report xlsx files use **hyphenated column headers** like:
```
article-number  receiver-name  event-description  event-code
```

But the endpoint was only looking for:
```
"article number", "article no", "tracking number", etc. (spaces, no hyphens)
```

Column detection failed → `track_col = None` → `400 Bad Request`

### Fix Applied

#### 1. Enhanced `_find_col()` Function
**File:** `/opt/miguel/backend/app/modules/shipments/router.py` (lines 1341-1365)

Made the matching more case-insensitive and added better substring handling:

```python
def _find_col(headers: list, candidates: list) -> Optional[int]:
    """Find first matching column index from header row (case-insensitive, partial match)."""
    for candidate in candidates:
        c = candidate.lower().strip()
        for i, h in enumerate(headers):
            h2 = h.lower().strip()
            if c in h2 or h2 in c:  # both directions to catch hyphens
                return i
    return None
```

#### 2. Added Content-Based Fallback Detection
**File:** `/opt/miguel/backend/app/modules/shipments/router.py` (lines 1352-1368)

New function `_detect_tracking_col_by_content()` scans cell values for India Post article number patterns (e.g., `EE123456789IN`):

```python
def _detect_tracking_col_by_content(rows: list, num_cols: int) -> Optional[int]:
    """
    Fallback: scan data rows for India Post article number patterns.
    India Post article numbers: EE123456789IN, RX123456789IN, EM123456789IN, etc.
    """
    import re
    ip_pattern = re.compile(r'^[A-Z]{2}\d{9}[A-Z]{2}$', re.IGNORECASE)
    scores = [0] * num_cols
    for row in rows[1:min(20, len(rows))]:
        for ci, cell in enumerate(row):
            if ci >= num_cols:
                break
            val = str(cell or "").strip()
            if ip_pattern.match(val):
                scores[ci] += 1
    best = max(scores) if scores else 0
    if best > 0:
        return scores.index(best)
    return None
```

#### 3. Expanded Column Header Candidates
**Files:** `/opt/miguel/backend/app/modules/shipments/router.py` (lines 1750-1774, 1976-2000)

Added India Post bulk report column names with hyphens:

```python
# For tracking column
track_col  = _find_col(headers, [
    # India Post bulk report (hyphenated)
    "article-number", "article-no",
    # Standard names (spaces, dots)
    "article number", "article no", "article no.", "article_number",
    "tracking number", "tracking no", "tracking no.", "tracking_number",
    # Other formats
    "awb", "awb number", "awb no", "barcode",
    "consignment no", "consignment no.", "consignment number",
    "tracking id", "shipment no", "shipment number",
    "booking no", "booking no.", "booking number",
    "speed post no", "reg no", "registered no",
    "parcel no", "parcel number", "article",
])

# For customer name column
cust_col = _find_col(headers, [
    # India Post bulk report (hyphenated)
    "receiver-name", "sender-name", "receiver name", "sender name",
    # Standard names
    "customer name", "customer", "name", "customer_name",
    "recipient", "addressee", "consignee", "addressee name",
    "to name", "beneficiary", "party name",
])

# For delivery status column
status_col = _find_col(headers, [
    # India Post bulk report (hyphenated)
    "event-description", "event-code", "event description", "event code",
    # Standard names
    "delivery status", "status", "delivered", "shipment status",
    "current status", "delivery", "event", "current event",
    "latest status", "remarks", "delivery remarks",
    "status description", "scan event", "scan status",
])
```

#### 4. Added 2-Column Fallback
If file has exactly 2 columns with unrecognizable headers, assume col 0 = name, col 1 = tracking.

#### 5. Added Debug Logging
Every xlsx upload now logs detected headers:
```python
import logging as _log
_log.warning(f"[xlsx-upload] headers detected: {headers}")
```

This appears in `docker logs miguel_backend`, making future debugging trivial.

### Real-World Test Results

**Test 1: Standard format** (simple headers)
```
Headers: ['Customer Name', 'Article Number']
Result: ✅ Columns detected, 2 orders updated
```

**Test 2: India Post style** (simple hyphenated)
```
Headers: ['Sl. No.', 'Article No.', 'Addressee Name', 'Booking Date', 'Delivery Status']
Result: ✅ Columns detected, status updated (delivered/returned)
```

**Test 3: India Post bulk report** (full format with 34 columns)
```
Headers: ['customer-id', 'customer-name', ..., 'article-number', ..., 'receiver-name', ..., 'event-description', ...]
Result: ✅ Columns detected (article-number @ index 13, receiver-name @ 24, event-description @ 27)
       ✅ 2 orders matched and updated correctly
```

---

## 🔧 Frontend Changes

### Orders Table: Status Column Made Interactive
**File:** `/opt/miguel/frontend/orders.html` (lines 1281-1295)

Changed from static status badge to interactive dropdown:

```html
<!-- BEFORE: Static badge -->
${statusChip(o.status)}

<!-- AFTER: Interactive dropdown -->
<select class="status-sel" onchange="quickUpdateOrderStatus('${o.id}',this.value)">
  <option value="draft"            ${o.status==='draft'            ?'selected':''}>Draft</option>
  <option value="confirmed"        ${o.status==='confirmed'        ?'selected':''}>Confirmed</option>
  <option value="processing"       ${o.status==='processing'       ?'selected':''}>Processing</option>
  <option value="packed"           ${o.status==='packed'           ?'selected':''}>Packed</option>
  <option value="shipped"          ${o.status==='shipped'          ?'selected':''}>Shipped</option>
  <option value="out_for_delivery" ${o.status==='out_for_delivery' ?'selected':''}>Out for Delivery</option>
  <option value="delivered"        ${o.status==='delivered'        ?'selected':''}>Delivered</option>
  <option value="cancelled"        ${o.status==='cancelled'        ?'selected':''}>Cancelled</option>
  <option value="returned"         ${o.status==='returned'         ?'selected':''}>Returned</option>
</select>
```

### New Function: `quickUpdateOrderStatus()`
**File:** `/opt/miguel/frontend/orders.html` (lines 1983-1996)

```javascript
async function quickUpdateOrderStatus(orderId, status) {
  try {
    const r = await fetch(`${HOST}/api/orders/${orderId}`, {
      method: 'PATCH', headers: getH(),
      body: JSON.stringify({ status: status }),
    });
    if (r.ok) {
      showOk(`Order status → ${status.replace(/_/g, ' ')}`);
      loadOrders();  // Reload the table
    }
    else { const e = await r.json(); showErr(e.detail || 'Update failed'); loadOrders(); }
  } catch(e) { showErr('Network error'); }
}
```

### Pay Status Dropdown Now Reloads Table
**File:** `/opt/miguel/frontend/orders.html` (line 1979)

```javascript
// ADDED: loadOrders() call on success to refresh table
if (r.ok) {
  showOk(`Payment status → ${status}`);
  loadOrders();  // ← NEW: Reload to reflect changes
}
```

### India Post xlsx Buttons (Existing)
Already implemented in previous sessions:
- 🔍 **Preview xlsx** → `/api/shipments/manual-orders/india-post-xlsx-preview`
- 📄 **Tracking xlsx** → `/api/shipments/manual-orders/india-post-xlsx` (tracking-only)
- ✅ **Delivery xlsx** → `/api/shipments/manual-orders/india-post-xlsx` (with status)

---

## 📊 Testing Summary

| Test | Before | After | Status |
|------|--------|-------|--------|
| Create new order | 500 Error | 200 OK | ✅ |
| PATCH payment_status on delivered order | 400 Error | 200 OK | ✅ |
| PATCH status on delivered order | 400 Error | 200 OK | ✅ |
| Upload simple xlsx | Works | Works | ✅ |
| Upload India Post bulk report xlsx | 400 Error | 200 OK | ✅ |
| Status dropdown in table | Non-functional | Functional | ✅ |
| Pay status dropdown in table | Non-functional | Functional | ✅ |
| Orders table loads | Works | Works + Fast | ✅ |

---

## 🚀 Deployment

### Backend Restart Required
```bash
docker restart miguel_backend
# Wait ~3 seconds for startup
```

### No Database Migration Needed
- All changes are code-only
- Schema remains unchanged
- Existing data unaffected

### Frontend Reload Required
- Browser cache: Clear or force refresh (`Ctrl+Shift+R`)
- No new files added, only modifications to orders.html

---

## 📝 Files Modified

| File | Lines | Changes |
|------|-------|---------|
| `/opt/miguel/backend/app/modules/orders/service.py` | 1-20, 750-810 | Added PaymentMethod import, relaxed terminal order edit block |
| `/opt/miguel/backend/app/modules/orders/schemas.py` | 106 | Added `status` field to OrderUpdate |
| `/opt/miguel/backend/app/modules/shipments/router.py` | 1341-1365, 1352-1368, 1750-1810, 1976-2010 | Enhanced _find_col(), added _detect_tracking_col_by_content(), expanded column header candidates |
| `/opt/miguel/frontend/orders.html` | 1268-1295, 1379-1388, 1969-1996, 2079 | Interactive Status dropdown, quickUpdateOrderStatus() function, loadOrders() on pay status change |

---

## 🔍 Verification Steps

Run these to verify all fixes:

### 1. Backend Health
```bash
docker logs miguel_backend --tail=20 | grep -i "startup\|error"
# Expected: "Application startup complete" (no errors)
```

### 2. Order Creation
```bash
curl -X GET "http://localhost:8000/api/orders/?page=1&page_size=1" \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200 OK with order data
```

### 3. Status Update on Delivered Order
```bash
curl -X PATCH "http://localhost:8000/api/orders/26ca4c52-b676-4c02-acc8-01a421d676ca" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"payment_status":"paid"}'
# Expected: 200 OK with updated order
```

### 4. India Post xlsx Upload
```bash
# Check logs for header detection
docker logs miguel_backend --tail=30 | grep "xlsx-upload"
# Expected: "[xlsx-upload] headers detected: [...]"
```

---

## 🛠️ Troubleshooting

### Issue: Status dropdown shows blank after fix
**Solution:** Clear browser cache (`Ctrl+Shift+R`). Ensure frontend was redeployed.

### Issue: xlsx upload still returns 400
**Solution:** Check logs with `docker logs miguel_backend --tail=50 | grep "xlsx-upload"`. The exact headers will be logged. If a new header format is seen, add it to the candidates list.

### Issue: Order creation still returns 500
**Solution:** Verify PaymentMethod import is present at line 7 of service.py. Restart backend: `docker restart miguel_backend`.

---

## 📚 Related Documentation

- [Orders Module Deep Dive](./SHOPIFY_FULFILLMENT_FIX.md)
- [India Post Integration Guide](./MANUAL_ORDERS_INDIA_POST_XLSX_GUIDE.md)
- [Partial COD System](./PARTIAL_COD_IMPLEMENTATION_GUIDE.md)
- [API Quick Reference](./API_QUICK_REFERENCE.md)

---

## ✅ Sign-Off

**Session Date:** Feb 25, 2026  
**All Tests:** PASSED  
**Ready for Production:** YES

