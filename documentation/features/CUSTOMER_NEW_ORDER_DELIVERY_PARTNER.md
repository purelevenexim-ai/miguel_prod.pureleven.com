# Customer Page - New Order Delivery Partner Selection

**Version:** 1.0  
**Last Updated:** February 27, 2026  
**Status:** ✅ Deployed (commit b61443b)

---

## Overview

The **Customers** page "New Order" modal now includes **Delivery Partner** and **Service Type** selection, matching the functionality available in the Orders page. This ensures consistent shipping configuration across all order creation points in the system.

---

## Features

### 1. **Delivery Partner Selection**
- **Dropdown** in the "New Order" modal displays all active delivery partners
- Fetches from `/api/orders/couriers` endpoint
- Shows partner name for easy selection
- Supports default partner pre-selection

### 2. **Service Type Selection (India Post)**
- **Conditional field** that appears only when a delivery partner has multiple Customer IDs
- Allows selection of specific India Post service types (Customer IDs)
- Displays both ID and associated name (e.g., "1234 — Hyderabad Branch")

### 3. **Error Handling**
- Shows helpful error messages if API fails
- Displays guidance message if no delivery partners are configured
- Network errors caught and reported

---

## User Interface

### New Order Modal - Right Panel

```
📅 Delivery
├─ Expected Date [date picker]
│
🚚 Delivery Partner & Service
├─ Delivery Partner * [dropdown]
│  └─ Loading... → [fetches partners]
│     └─ Options: Select Delivery Partner...
│                 Partner A
│                 Partner B
│
└─ Service Type [hidden until selection]
   └─ Shows if partner has customer_ids
      └─ Options: Select Customer ID...
                  1234 — Hyderabad Branch
                  5678 — Delhi Branch
```

### Workflow
1. User clicks "New Order" button in customer detail view
2. Modal opens, courier dropdown auto-loads delivery partners
3. User selects a delivery partner
4. If partner has multiple Customer IDs, Service Type dropdown appears
5. User can select specific India Post service type
6. Order submission includes both `shipping_partner_id` and `india_post_customer_id`

---

## Technical Implementation

### HTML Changes
**File:** `/opt/miguel/frontend/customers.html`

Added new section in the New Order modal right panel:
```html
<div class="no-section">🚚 Delivery Partner &amp; Service</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px;">
  <div class="form-group" style="margin-bottom:0;">
    <label class="form-label">Delivery Partner *</label>
    <select class="form-select" id="no_courierSel" onchange="noOnCourierChange()">
      <option value="">Loading…</option>
    </select>
  </div>
  <div class="form-group" id="no_ipIdBox" style="margin-bottom:0;display:none;">
    <label class="form-label">Service Type</label>
    <select class="form-select" id="no_ipCustomerIdSel">
      <option value="">Select…</option>
    </select>
  </div>
</div>
```

### JavaScript Changes

#### 1. **Global Variables** (lines 1607-1610)
```javascript
let _noCouriers        = [];  // Array of delivery partners
let _noSelectedCourier = null; // Currently selected partner
```

#### 2. **Load Couriers on Modal Open** (line 1665)
```javascript
// In openNewOrderModal():
noLoadCouriers();
```

#### 3. **noLoadCouriers() Function** (lines 1946-1973)
```javascript
async function noLoadCouriers() {
  try {
    const r = await fetch('/api/orders/couriers', { headers:H});
    if (!r.ok) {
      console.error('Error loading couriers:', r.status, r.statusText);
      const sel = document.getElementById('no_courierSel');
      sel.innerHTML = '<option value="">⚠️ Error loading couriers</option>';
      return;
    }
    _noCouriers = await r.json();
    console.log('Loaded couriers:', _noCouriers);
    const sel = document.getElementById('no_courierSel');
    
    if (!_noCouriers || _noCouriers.length === 0) {
      sel.innerHTML = '<option value="">No delivery partners configured (Tenant Admin → Shipping Configuration)</option>';
    } else {
      sel.innerHTML = '<option value="">Select Delivery Partner…</option>' +
        _noCouriers.map(c =>
          `<option value="${c.id}" ${c.is_default?'selected':''}>${c.name}</option>`
        ).join('');
    }
    onCourierChange();
  } catch(e) {
    console.error('Error loading couriers:', e);
    const sel = document.getElementById('no_courierSel');
    sel.innerHTML = '<option value="">⚠️ Network error</option>';
  }
}
```

**Key Points:**
- Fetches delivery partners from `/api/orders/couriers` endpoint
- Handles API errors with user-friendly messages
- Pre-selects default partner if marked as such
- Calls `noOnCourierChange()` after loading

#### 4. **noOnCourierChange() Function** (lines 1975-1993)
```javascript
function noOnCourierChange() {
  const val = document.getElementById('no_courierSel').value;
  _noSelectedCourier = _noCouriers.find(c => c.code === val || c.id === val) || null;
  
  // Show customer ID selector for partners with customer IDs
  const ipIdBox = document.getElementById('no_ipIdBox');
  const sel = document.getElementById('no_ipCustomerIdSel');
  
  if (_noSelectedCourier && _noSelectedCourier.customer_ids && _noSelectedCourier.customer_ids.length > 0) {
    ipIdBox.style.display = '';
    sel.innerHTML = '<option value="">Select Customer ID…</option>' +
      _noSelectedCourier.customer_ids.map(cid =>
        `<option value="${cid.id}">${cid.id}${cid.name ? ' — ' + cid.name : ''}</option>`
      ).join('');
  } else {
    ipIdBox.style.display = 'none';
    sel.innerHTML = '<option value="">Select…</option>';
  }
}
```

**Key Points:**
- Triggered by `onchange` event on delivery partner dropdown
- Finds selected courier in `_noCouriers` array
- Shows/hides Service Type dropdown based on customer_ids
- Populates customer ID options from selected partner

#### 5. **Order Payload Changes** (lines 2019, 2039-2040)
```javascript
const courierCode = document.getElementById('no_courierSel').value;
const ipId = document.getElementById('no_ipCustomerIdSel').value;
const payload = {
  // ... other fields ...
  shipping_partner_id: courierCode || null,
  india_post_customer_id: ipId || null,
  // ... other fields ...
};
```

**Key Points:**
- Extracts partner ID and customer ID from dropdowns
- Includes both in order payload
- Allows backend to link order to specific partner and service type

---

## Data Flow

```
User opens New Order modal
    ↓
openNewOrderModal() called
    ↓
noLoadCouriers() fetches delivery partners from /api/orders/couriers
    ↓
Dropdown populated with partners
    ↓
User selects delivery partner
    ↓
noOnCourierChange() triggered
    ↓
If partner.customer_ids.length > 0:
  ├─ Show Service Type dropdown
  └─ Populate with partner's customer IDs
Else:
  └─ Hide Service Type dropdown
    ↓
User selects service type (if applicable)
    ↓
User submits order
    ↓
Payload includes:
├─ shipping_partner_id (partner ID)
├─ india_post_customer_id (service type ID)
└─ ...other fields...
    ↓
Order created with delivery partner linked
```

---

## API Integration

### Endpoint: GET `/api/orders/couriers`
**Returns:** Array of delivery partners with customer IDs

**Response Structure:**
```json
[
  {
    "id": "uuid",
    "name": "India Post",
    "code": "INDIA_POST",
    "partner_type": "india_post",
    "is_active": true,
    "is_default": false,
    "customer_ids": [
      { "id": "1234", "name": "Hyderabad Branch" },
      { "id": "5678", "name": "Delhi Branch" }
    ]
  },
  {
    "id": "uuid",
    "name": "Shiprocket",
    "code": "SHIPROCKET",
    "partner_type": "shiprocket",
    "is_active": true,
    "is_default": true,
    "customer_ids": []
  }
]
```

### Endpoint: POST `/api/orders/`
**Payload Includes:**
```json
{
  "shipping_partner_id": "partner-uuid",
  "india_post_customer_id": "1234",
  ...other fields...
}
```

---

## Consistency With Orders Page

This implementation **mirrors** the functionality in `/opt/miguel/frontend/orders.html`:

| Feature | Orders Page | Customers Page |
|---------|-------------|-----------------|
| Delivery Partner Selection | ✅ | ✅ |
| Service Type for India Post | ✅ | ✅ |
| Error Handling | ✅ | ✅ |
| Default Partner Selection | ✅ | ✅ |
| API Endpoint | `/api/orders/couriers` | `/api/orders/couriers` |

---

## Testing Checklist

- [ ] Open customer detail → "New Order" button
- [ ] Modal opens, dropdown shows "Loading..."
- [ ] Dropdown auto-populates with delivery partners
- [ ] Select a partner with multiple Customer IDs
- [ ] Service Type dropdown appears
- [ ] Service Type options show ID and name
- [ ] Select different partner without multiple IDs
- [ ] Service Type dropdown hides
- [ ] Fill in items and submit order
- [ ] Order created with `shipping_partner_id` populated in database

---

## Troubleshooting

### Dropdown Shows "No delivery partners configured"
**Solution:** Go to **Tenant Admin** → **Shipping Configuration** and create/activate delivery partners.

### Service Type Dropdown Doesn't Appear
**Cause:** Selected partner has no Customer IDs configured.  
**Solution:** Edit partner in Tenant Admin and add Customer IDs.

### "⚠️ Error loading couriers" Message
**Cause:** API endpoint error (likely permission or server issue).  
**Solution:** 
- Check browser console for detailed error
- Verify user has tenant admin permissions
- Check server logs

### "⚠️ Network error"
**Cause:** Network request failed before reaching server.  
**Solution:**
- Check internet connection
- Verify API endpoint is accessible
- Check browser network tab for status codes

---

## Related Files

- **Frontend:** `/opt/miguel/frontend/customers.html`
- **Frontend (Orders Page):** `/opt/miguel/frontend/orders.html`
- **Backend API:** `/opt/miguel/backend/app/modules/orders/router.py`
- **Backend Model:** `/opt/miguel/backend/app/models/shipping_config.py`
- **Backend Schema:** `/opt/miguel/backend/app/modules/shipping_config/schemas.py`

---

## Deployment Notes

**Commit:** `b61443b`  
**Files Modified:** 1
- `frontend/customers.html` (+75 lines, -0 lines)

**Breaking Changes:** None (new feature only)

**Dependencies:** None new (uses existing `/api/orders/couriers` endpoint)

**Database Migrations:** None required

---

## Future Enhancements

1. **Drag-to-reorder partners** in dropdown
2. **Search/filter** partners by name or type
3. **Quick partner configuration** modal from order form
4. **Partner availability** based on delivery address/pincode
5. **Auto-select** best partner based on order type

---

## Questions & Support

For issues or feature requests, refer to the main documentation or contact the development team.
