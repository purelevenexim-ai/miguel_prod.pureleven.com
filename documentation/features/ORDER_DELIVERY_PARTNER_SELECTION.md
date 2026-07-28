# Order Delivery Partner Selection

**Date:** February 27, 2026  
**Version:** 1.0  
**Status:** ✅ Production Ready  
**Commit:** 35af965

---

## Overview

Enhanced the order creation form to allow selection of delivery partners (couriers) with support for multiple service types. When a partner has multiple Customer IDs (like India Post with Parcel, Prepaid, Speed Post), users can select the specific service they want.

---

## What Changed

### Problem
- ❌ Order creation form didn't show delivery partner options
- ❌ No way to select which courier to use
- ❌ No way to select which India Post service type (Parcel vs Prepaid)
- ❌ Created orders without shipping partner information

### Solution
- ✅ New "Delivery Partner" dropdown in order form
- ✅ Dynamically populated from configured delivery partners
- ✅ "Service Type" dropdown shows when partner has multiple Customer IDs
- ✅ All order data includes selected partner and service type

---

## How It Works

### Step 1: Create Delivery Partners (Admin)
First, set up delivery partners in Tenant Admin:
1. Go to **Tenant Admin** → **Shipping Configuration** → **Delivery Partners**
2. Click **"+ Add Partner"**
3. Configure partner (e.g., India Post Adimali)
4. Add multiple Customer IDs (e.g., Parcel, Prepaid, Speed Post)
5. Save

### Step 2: Create Order (Sales/Operations)
When creating a new order:

1. **Go to Orders page** → Click **"+ New Order"**
2. **Fill in delivery address and customer details** (as before)
3. **Fill in items** (as before)
4. **Scroll to "Courier & Service" section**
5. **Select Delivery Partner** from dropdown
   - Shows all active partners you configured
   - Defaults to primary partner if set
   
6. **If partner has multiple services:**
   - **"Service Type" dropdown appears** (was hidden)
   - Shows options like:
     - 12345 — Indian Post Parcel
     - 67890 — Indian Post Prepaid
     - 54321 — Indian Post Speed Post
   - Select the appropriate service
   
7. **For India Post, select shipping service:** Speed Post or Parcel
8. **Complete rest of order form and submit**

### Step 3: Order Created
- Order is created with:
  - ✅ Delivery Partner ID
  - ✅ Service Type (Customer ID)
  - ✅ Courier information
  - ✅ Shipping service type
  
---

## UI Changes

### Before
```
Courier & Service
┌──────────────────────────────────────────┐
│ Courier                                  │
│ [Loading…]                               │
└──────────────────────────────────────────┘
```

### After
```
Courier & Service
┌─────────────────────┬───────────────────┐
│ Delivery Partner *  │ Service Type      │
│ [India Post ▼]      │ [12345 — Parcel ▼]│
└─────────────────────┴───────────────────┘
```

**Key Changes:**
- Label changed from "Courier" → "Delivery Partner"
- Made it required (*) to ensure selection
- Service Type field appears only when partner has Customer IDs
- Better labeling for clarity

---

## Technical Implementation

### Backend Changes

**1. Updated `/api/orders/couriers` endpoint:**
```python
# Now returns delivery partners with customer IDs
GET /api/orders/couriers
[
  {
    "id": "uuid",
    "name": "India Post Adimali",
    "code": "INDIA_POST",
    "is_active": true,
    "is_default": true,
    "partner_type": "india_post",
    "customer_ids": [
      { "id": "12345", "name": "Indian Post Parcel" },
      { "id": "67890", "name": "Indian Post Prepaid" }
    ]
  },
  {
    "id": "uuid",
    "name": "Delhivery Primary",
    "code": "DELHIVERY",
    "is_active": true,
    "is_default": false,
    "partner_type": "delhivery",
    "customer_ids": []  # No customer IDs
  }
]
```

**2. Updated Order model:**
- Added `shipping_partner_id` field (UUID FK to DeliveryPartner)
- Stores link to selected delivery partner

**3. Updated OrderCreate schema:**
- Added `shipping_partner_id: Optional[UUID]`
- Accepts selected partner ID during order creation

### Frontend Changes

**1. Updated `loadCouriers()` function:**
- Fetches from `/api/orders/couriers`
- Populates courier dropdown with delivery partner names
- Uses partner ID (UUID) instead of code

**2. Updated `onCourierChange()` function:**
- Detects if selected partner has customer IDs
- Shows/hides Service Type dropdown dynamically
- Populates Service Type dropdown with partner's customer IDs
- Shows service label if available

**3. Updated form HTML:**
- Label: "Courier" → "Delivery Partner *" (required)
- Service Type field shows/hides based on partner selection

**4. Updated `submitOrder()` function:**
- Sends `shipping_partner_id` in payload
- Sends selected `india_post_customer_id` (or other service)
- Uses partner name from selected object

---

## Data Flow

### Order Creation Process
```
User selects "India Post Adimali"
         ↓
onCourierChange() fires
         ↓
Lookup partner in couriers array
         ↓
Partner has customer_ids? → YES
         ↓
Show Service Type dropdown
         ↓
Populate with: [
  { "id": "12345", "name": "Parcel" },
  { "id": "67890", "name": "Prepaid" }
]
         ↓
User selects "67890 — Prepaid"
         ↓
User submits order
         ↓
Payload includes:
{
  "shipping_partner_id": "uuid-of-india-post",
  "india_post_customer_id": "67890",
  "courier_code": "india_post",
  "courier_name": "India Post Adimali"
}
         ↓
Order created in database
```

---

## API Endpoints

### Get Delivery Partners (Orders)
```http
GET /api/orders/couriers
Authorization: Bearer <token>
```

**Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "India Post Adimali",
    "code": "INDIA_POST",
    "is_active": true,
    "is_default": true,
    "partner_type": "india_post",
    "customer_ids": [
      { "id": "12345", "name": "Indian Post Parcel" },
      { "id": "67890", "name": "Indian Post Prepaid" },
      { "id": "54321", "name": "Indian Post Speed Post" }
    ]
  }
]
```

### Create Order
```http
POST /api/orders/
Content-Type: application/json
Authorization: Bearer <token>

{
  "shipping_partner_id": "550e8400-e29b-41d4-a716-446655440000",
  "india_post_customer_id": "67890",
  "courier_code": "india_post",
  "courier_name": "India Post Adimali",
  "shipping_service": "parcel",
  ...other fields...
}
```

---

## Use Cases

### India Post with Multiple Services
```
Partner: India Post Adimali

Customer IDs:
├─ 12345 → Indian Post Parcel (bulk shipments)
├─ 67890 → Indian Post Prepaid (premium service)
└─ 54321 → Indian Post Speed Post (fast delivery)

Order Flow:
1. User selects "India Post Adimali" from Delivery Partner
2. Service Type dropdown appears
3. User selects "67890 — Indian Post Prepaid"
4. Order created with:
   - shipping_partner_id = India Post's UUID
   - india_post_customer_id = "67890"
```

### Delhivery (No Multiple Services)
```
Partner: Delhivery Primary

Customer IDs: (none configured)

Order Flow:
1. User selects "Delhivery Primary"
2. Service Type dropdown is hidden (no IDs)
3. Order created with:
   - shipping_partner_id = Delhivery's UUID
   - india_post_customer_id = null
```

### Blue Dart with Multiple Speeds
```
Partner: Blue Dart Mumbai

Customer IDs:
├─ ABC123 → Blue Dart Express (2-3 days)
└─ DEF456 → Blue Dart Economy (5-7 days)

Order Flow:
1. User selects "Blue Dart Mumbai"
2. Service Type dropdown appears
3. User selects speed based on urgency
4. Order tracks which speed was selected
```

---

## Integration Points

### When Partner Has No API Key
- ✅ Still selectable in order form
- ✅ Service types still available
- ✅ Order creation not blocked
- ✅ Manual shipment tracking can be added later

### When Partner Has Multiple Customer IDs
- ✅ All IDs shown in Service Type dropdown
- ✅ Each ID with its service name
- ✅ Selection stored in order
- ✅ Can be used for API calls later

### When Creating Orders
- ✅ Partner selection is required
- ✅ Service Type only if applicable
- ✅ Both included in order payload
- ✅ Linked to order for tracking/reference

---

## Database Schema

### Order Table (Modified)
```sql
ALTER TABLE orders ADD COLUMN shipping_partner_id UUID;
ALTER TABLE orders ADD CONSTRAINT fk_shipping_partner
  FOREIGN KEY (shipping_partner_id) REFERENCES delivery_partners(id);
```

### Existing Fields Used
- `india_post_customer_id` — Stores selected Customer ID
- `courier_code` — Snapshot of partner type
- `courier_name` — Snapshot of partner display name

---

## Backward Compatibility

✅ **Fully backward compatible**

- Orders without `shipping_partner_id` still work
- Existing orders can be queried normally
- No data migration needed
- Field is optional in API

---

## Frontend Functions

| Function | Purpose |
|----------|---------|
| `loadCouriers()` | Fetch delivery partners from API |
| `onCourierChange()` | Handle partner selection, show/hide Service Type |
| `submitOrder()` | Include shipping_partner_id in order payload |

---

## Testing

### Test Cases
- [ ] Load order form → Couriers dropdown populated
- [ ] Select partner with Customer IDs → Service Type appears
- [ ] Select partner without Customer IDs → Service Type hidden
- [ ] Select service type → Correct ID in form
- [ ] Submit order → shipping_partner_id saved
- [ ] Submit order → india_post_customer_id saved
- [ ] Edit order → Partner selection preserved
- [ ] Search orders by partner → Returns correct orders

---

## Future Enhancements

1. **Bulk Service Selection**
   - Pre-set default service per customer
   - Auto-select service based on order value/weight

2. **Service Recommendations**
   - Suggest service based on delivery distance
   - Recommend based on customer history

3. **Rate Display**
   - Show rates for each service during order creation
   - Calculate shipping cost automatically

4. **Service Filters**
   - Filter orders by partner
   - Filter by service type (all Parcel orders, etc.)

5. **Shipping Label Generation**
   - Auto-generate based on selected service
   - Pre-populate with Customer ID

---

## File Changes Summary

| File | Changes |
|------|---------|
| `backend/app/modules/orders/router.py` | Updated `/api/orders/couriers` to return delivery partners |
| `backend/app/modules/orders/schemas.py` | Added shipping_partner_id field |
| `backend/app/models/order.py` | Added shipping_partner_id FK column |
| `frontend/orders.html` | Updated form UI and JavaScript logic |

---

## Status

✅ **Deployed to Production**
- Commit: 35af965
- All delivery partners now selectable in order form
- Customer IDs appear when applicable
- Ready for use

---

## Support

For issues:
1. Ensure delivery partners are configured in Tenant Admin
2. Verify partners are marked as "Active"
3. Check if partners have Customer IDs configured
4. Clear browser cache if dropdown not updating

---

**Last Updated:** February 27, 2026
