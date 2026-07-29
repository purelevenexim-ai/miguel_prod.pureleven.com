# Delivery Partner Enhancements

**Date:** February 27, 2026  
**Version:** 1.0  
**Status:** ✅ Production Ready  
**Commit:** b06c07b

---

## Overview

Enhanced the Delivery Partner configuration system to support:
1. **Optional API Keys** — Allow partnerships where API is not available
2. **Multiple Customer IDs** — Manage different service types (Parcel, Prepaid, etc.) for the same partner

---

## Feature 1: Optional API Key

### Problem
Previously, API Key was **required** for all delivery partners. This created issues for:
- Partners who don't provide API access
- Testing configurations before API is available
- Integrations that use alternative authentication methods

### Solution
API Key is now **fully optional**:
- Can be left blank when creating a partner
- Can be left blank when updating a partner
- Form shows hint: `(Leave blank if not available)`
- Placeholder updated to show it's optional

### How It Works

#### Creating a Partner WITHOUT API Key
```
Partner Type: India Post ✓ (required)
Display Name: India Post Adimali ✓ (required)
API Key: [BLANK] ✓ (optional - leave empty)
API Secret: [BLANK] ✓ (optional)
Client Name: Pure Leven Exim ✓ (optional)
Pickup Location: ADIMALI ✓ (optional)
```

#### Updating a Partner
When editing, you can:
- Leave API Key blank to keep the current value
- Enter a new API Key to update it
- This preserves backward compatibility

### Backend Changes

**Model Update:**
```python
api_key = Column(Text, nullable=True)   # Changed from nullable=False
```

**Schema Update:**
```python
class DeliveryPartnerCreate(BaseModel):
    api_key: Optional[str] = None   # Changed from required str
```

**Validation:**
- Partner Type: Required ✓
- Display Name: Required ✓
- API Key: Optional ✓ (NEW)
- API Secret: Optional ✓
- Client Name: Optional ✓

---

## Feature 2: Multiple Customer IDs

### Problem
Many delivery partners (especially India Post) have **multiple service types** that require different Customer IDs:

- **India Post Parcel** — Customer ID: 12345
- **India Post Prepaid** — Customer ID: 67890
- **India Post Speed Post** — Customer ID: 54321

Previously, you could only store **one** customer ID in the `client_id` field. This was limiting.

### Solution
Added **`customer_ids`** field that stores **multiple** Customer IDs with labels:

```json
[
  { "id": "12345", "name": "Indian Post Parcel" },
  { "id": "67890", "name": "Indian Post Prepaid" }
]
```

Each Customer ID has:
- **Customer ID Number** — The actual ID (e.g., "12345")
- **Service Name** — What service this ID is for (e.g., "Indian Post Parcel")

### How It Works

#### Adding Customer IDs in the Form

1. **Open Delivery Partner Edit Form**
2. **Scroll to "Customer IDs" section**
3. **Click "+ Add ID" button**
4. **Enter Customer ID and Service Name:**
   ```
   Customer ID: 12345
   Service Name: Indian Post Parcel
   ```
5. **Add more as needed:**
   ```
   Customer ID: 67890
   Service Name: Indian Post Prepaid
   ```
6. **Remove any ID by clicking ✕ button**
7. **Save Partner**

#### Visual Layout
```
Customer IDs (for multi-service partners)

┌─────────────────┬──────────────────────────┬───┐
│  Customer ID    │   Service Name           │ ✕ │
├─────────────────┼──────────────────────────┼───┤
│ 12345           │ Indian Post Parcel       │ ✕ │
├─────────────────┼──────────────────────────┼───┤
│ 67890           │ Indian Post Prepaid      │ ✕ │
└─────────────────┴──────────────────────────┴───┘

        [+ Add ID]
```

### Real-World Examples

#### Example 1: India Post with Multiple Services
```
Partner Type: India Post
Display Name: India Post Adimali

Customer IDs:
  ├─ 12345 → Indian Post Parcel
  ├─ 67890 → Indian Post Prepaid
  └─ 54321 → Indian Post Speed Post
```

When sending a shipment, the system can:
- Select which Customer ID to use based on service type
- Apply correct rates and pickup rules for each service

#### Example 2: Delhivery (Standard Usage)
```
Partner Type: Delhivery
Display Name: Primary Delhivery
API Key: your_api_key_here

Customer IDs: (optional - leave empty if not needed)
```

#### Example 3: Bluedart with Bulk Services
```
Partner Type: Blue Dart
Display Name: Blue Dart Mumbai

Customer IDs:
  ├─ ABC123 → Blue Dart Express
  └─ DEF456 → Blue Dart Economy
```

### Backend Implementation

**Model Update:**
```python
class DeliveryPartner(Base):
    # ... existing fields ...
    
    # Customer IDs for different service types
    # Format: [{"id": "12345", "name": "Indian Post Parcel"}, ...]
    customer_ids = Column(JSON, nullable=True, default=list)
```

**Schema Update:**
```python
class DeliveryPartnerCreate(BaseModel):
    # ... existing fields ...
    customer_ids: Optional[List[Dict[str, str]]] = None

class DeliveryPartnerUpdate(BaseModel):
    # ... existing fields ...
    customer_ids: Optional[List[Dict[str, str]]] = None
```

**Storage Format:**
```json
{
  "id": "uuid-here",
  "partner_type": "india_post",
  "display_name": "India Post Adimali",
  "customer_ids": [
    { "id": "12345", "name": "Indian Post Parcel" },
    { "id": "67890", "name": "Indian Post Prepaid" }
  ]
}
```

### Frontend Implementation

**JavaScript Functions:**

| Function | Purpose |
|----------|---------|
| `addCustomerIdField()` | Add empty row for new Customer ID |
| `addCustomerIdRow(id, name, idx)` | Create a Customer ID input row |
| `removeCustomerIdRow(rowId)` | Delete a Customer ID row |
| `loadCustomerIdsToForm(customerIds)` | Load existing IDs when editing |
| `clearCustomerIdsList()` | Reset all Customer IDs when adding new partner |
| `getCustomerIdsFromForm()` | Extract Customer IDs from form before saving |

**Form Integration:**
- When creating partner: Starts empty
- When editing partner: Loads existing Customer IDs
- When submitting: Collects all rows into array format
- Validation: Both ID and Name must be filled to save

---

## API Endpoints

### Create Delivery Partner (POST)
```
POST /api/config/delivery-partners
Content-Type: application/json

{
  "partner_type": "india_post",
  "display_name": "India Post Adimali",
  "api_key": null,                          # Optional
  "api_secret": null,
  "client_name": "Pure Leven Exim",
  "pickup_location_code": "ADIMALI",
  "warehouse_name": "Adimali Hub",
  "customer_ids": [                          # NEW
    { "id": "12345", "name": "Parcel" },
    { "id": "67890", "name": "Prepaid" }
  ],
  "is_primary": false
}
```

### Update Delivery Partner (PUT)
```
PUT /api/config/delivery-partners/{id}
Content-Type: application/json

{
  "display_name": "India Post Adimali Updated",
  "api_key": "new_api_key_or_null",         # Optional
  "customer_ids": [                          # NEW - can update
    { "id": "12345", "name": "Parcel" },
    { "id": "99999", "name": "New Service" }
  ],
  "is_primary": true
}
```

### Response Format
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "partner_type": "india_post",
  "display_name": "India Post Adimali",
  "api_key": null,                    # Null if not provided
  "customer_ids": [
    { "id": "12345", "name": "Parcel" },
    { "id": "67890", "name": "Prepaid" }
  ],
  "is_connected": false,
  "is_primary": false,
  "created_at": "2026-02-27T10:30:00Z"
}
```

---

## Usage Guide

### Step 1: Open Delivery Partners Configuration
1. Go to **Tenant Admin** → **Shipping Configuration**
2. Click **"Delivery Partners"** tab
3. Click **"+ Add Partner"** button

### Step 2: Fill Partner Details
1. **Partner Type:** Select from dropdown (India Post, Delhivery, etc.)
2. **Display Name:** e.g., "India Post Adimali"
3. **API Key:** Leave blank if not available
4. **Client Name:** e.g., "Pure Leven Exim"
5. **Pickup Location:** e.g., "ADIMALI"
6. **Warehouse Name:** e.g., "Adimali Hub"

### Step 3: Add Customer IDs (if needed)
1. Scroll to **"Customer IDs"** section
2. Click **"+ Add ID"**
3. Enter **Customer ID Number:** e.g., "12345"
4. Enter **Service Name:** e.g., "Indian Post Parcel"
5. Click **"+ Add ID"** to add more
6. Remove rows with **✕** button if needed

### Step 4: Save Partner
1. Click **"Save"** button
2. Partner is created with all Customer IDs

### Step 5: Edit Existing Partner
1. Click **"Edit"** on partner row
2. Modify any field (including Customer IDs)
3. Click **"Save"**

---

## Migration & Backward Compatibility

### Existing Data
- Existing delivery partners **continue to work**
- `api_key` can be NULL for new partners
- `customer_ids` defaults to empty list

### Database Migration
No migration needed! Changes are backward compatible:
- `api_key` nullable change: ✓ Works with existing data
- `customer_ids` new column: ✓ Defaults to empty list

### API Compatibility
- **Old requests still work:** API key can be omitted
- **New format supported:** Customer IDs array is optional
- **No breaking changes:** All existing integrations continue functioning

---

## Validation Rules

### Creating a Partner
| Field | Required | Notes |
|-------|----------|-------|
| Partner Type | ✅ Yes | Must select from dropdown |
| Display Name | ✅ Yes | Unique identifier for UI |
| API Key | ❌ No | Can be left blank |
| API Secret | ❌ No | Optional |
| Client Name | ❌ No | Optional |
| Pickup Location | ❌ No | Optional |
| Warehouse Name | ❌ No | Optional |
| Customer IDs | ❌ No | Optional |

### Customer ID Validation
- **Both fields required:** ID AND Name must be filled
- **Empty rows ignored:** Rows with empty ID or Name are skipped
- **Duplicates allowed:** Can have multiple entries with same ID/Name
- **Max length:** No limit on number of Customer IDs

---

## Troubleshooting

### Issue: "API Key Required" Error
**Solution:** Feature updated — API Key is now optional. Try again.

### Issue: Customer IDs Not Saving
**Problem:** Rows with empty fields are skipped  
**Solution:** Ensure both Customer ID and Service Name are filled in each row

### Issue: Customer IDs Not Showing When Editing
**Problem:** Form didn't load existing data  
**Solution:** The IDs should auto-load. Try refreshing the page and editing again.

### Issue: API Connection Still Fails
**Problem:** API Key is blank  
**Solution:** This is expected. Add API Key if the partner provides one, or use alternative authentication.

---

## Future Enhancements (Optional)

Potential improvements for future versions:

1. **Customer ID Validation**
   - Validate format based on partner type
   - Show warnings for suspicious IDs

2. **Duplicate Detection**
   - Warn if Customer ID already exists in another partner
   - Prevent accidental duplicates

3. **Bulk Import**
   - Import multiple Customer IDs from CSV
   - Export existing IDs for backup

4. **Service Type Mapping**
   - Link each Customer ID to shipment types it supports
   - Auto-select correct ID based on service

5. **Usage Analytics**
   - Track which Customer ID is used most frequently
   - Show stats per service type

---

## File Changes Summary

| File | Changes |
|------|---------|
| `backend/app/models/shipping_config.py` | Made api_key nullable; added customer_ids JSON field |
| `backend/app/modules/shipping_config/schemas.py` | Updated schemas to make api_key optional; added customer_ids support |
| `frontend/tenant-admin.html` | Added Customer IDs UI section; added JS functions for management |

---

## Testing Checklist

- [x] Create partner without API Key
- [x] Create partner with API Key
- [x] Edit partner without API Key
- [x] Add single Customer ID
- [x] Add multiple Customer IDs
- [x] Edit Customer IDs
- [x] Remove Customer ID row
- [x] Save and reload partner
- [x] Verify Customer IDs persist in database
- [x] API endpoint accepts customer_ids
- [x] Backward compatibility with existing partners

---

## Support & Questions

For issues or questions:
1. Check the **Troubleshooting** section above
2. Review **Real-World Examples** for configuration patterns
3. Contact development team if issue persists

---

**Status:** ✅ Production Ready  
**Tested:** February 27, 2026  
**Last Updated:** February 27, 2026
