# Courier/Delivery Partner Dropdown - Troubleshooting Guide

**Date:** February 27, 2026  
**Status:** 🔴 Issue Identified - Need Delivery Partners Configuration

---

## Problem Summary

The **Delivery Partner** dropdown shows "No delivery partners configured" or is empty in:
- ✅ Orders page → "New Order" form
- ✅ Customers page → "New Order" modal
- ✅ Leads page → "Won" modal

**Root Cause:** No active delivery partners exist in your tenant's Shipping Configuration.

---

## Step 1: Check the Browser Console

**Action:** Open Developer Tools and look for logging with `[Orders]`, `[Customers]`, or `[Leads]` prefixes.

**Expected Logs When Working:**
```
[Orders] Loading couriers...
[Orders] API response: 200 OK
[Orders] Loaded couriers: [
  {
    "id": "abc123...",
    "name": "India Post",
    "code": "INDIA_POST",
    "is_active": true,
    "is_default": true,
    "partner_type": "india_post",
    "customer_ids": [
      {"id": "1234", "name": "Hyderabad Branch"},
      {"id": "5678", "name": "Delhi Branch"}
    ]
  }
]
[Orders] Successfully populated 1 partners
```

**If You See:**
```
[Orders] Loaded couriers: []
[Orders] No delivery partners found - please configure in Tenant Admin
```

**Solution:** → Go to **Step 2** (Configure Delivery Partners)

**If You See:**
```
[Orders] API Error: 401 Unauthorized
```

**Solution:** → Your session is expired. Log out and log back in.

**If You See:**
```
[Orders] API Error: 500 Internal Server Error
```

**Solution:** → Check backend logs on production server:
```bash
ssh root@172.105.48.142
tail -f /opt/pureleven/logs/app.log
# Look for errors related to "delivery_partners"
```

---

## Step 2: Configure Delivery Partners in Tenant Admin

### Path: Tenant Admin → Shipping Configuration

**Actions:**
1. Go to **Tenant Admin** page
2. Find **Shipping Configuration** section (or **Delivery Partners**)
3. Check if any partners are listed
4. If none exist, click **"+ Add Delivery Partner"**

### Create India Post Partner:

1. **Name:** "India Post" (or your preferred name)
2. **Partner Type:** "india_post"
3. **API Key:** Leave blank (optional for India Post)
4. **Status:** Toggle **✅ Active** (IMPORTANT!)
5. **Customer IDs** (if applicable):
   - Click **"+ Add Customer ID"**
   - **ID:** "1234" (your actual IP customer ID number)
   - **Name:** "Hyderabad Branch" (optional, for reference)
   - Click **Save**

6. **Mark as Default** (optional):
   - Toggle "Default Partner" if this should be pre-selected

7. Click **"Save Delivery Partner"**

### Create Other Partners (Optional):

Repeat for Shiprocket, Delhivery, etc. with their specific:
- API Keys (if required)
- Customer IDs (if applicable)

---

## Step 3: Verify in Database (Optional - Advanced)

If you want to verify delivery partners are in the database:

```bash
# SSH to production server
ssh root@172.105.48.142 -t "cd /opt/pureleven && psql -U erp erp_db"

# Then run:
SELECT id, display_name, partner_type, is_active, is_primary, customer_ids 
FROM delivery_partners 
WHERE tenant_id = (SELECT id FROM tenants LIMIT 1)
ORDER BY created_at DESC;

# Exit with: \q
```

**Expected Output:**
```
                  id                  | display_name | partner_type | is_active | is_primary | customer_ids
--------------------------------------+--------------+--------------+-----------+------------+---------------------
 a1b2c3d4-e5f6-47g8-h9i0-j1k2l3m4n5   | India Post   | india_post   | t         | t          | [{"id":"1234","name":"Hyderabad"}]
```

---

## Step 4: Test the Dropdown

### Test in Orders Page:

1. Go to **Orders** page
2. Click **"New Order"** button
3. Check **"Courier & Service"** section
4. Open browser console (F12)
5. Verify logs show `[Orders] Successfully populated X partners`
6. Dropdown should now show your delivery partners

### Test in Customers Page:

1. Go to **Customers** page
2. Click on any customer detail
3. Scroll down, click **"New Order"** button
4. Check modal for **"Delivery Partner & Service"** section
5. Verify logs show `[Customers] Successfully populated X partners`

### Test in Leads Page:

1. Go to **Leads** page
2. Click on any lead
3. Click **"🏆 Won"** button (top right)
4. Check modal for **"Delivery Partner"** dropdown
5. Verify logs show `[Leads] Successfully populated X partners`

---

## Step 5: Verify API Directly

**Action:** Test the API endpoint directly to confirm data is being returned:

```bash
# From your browser console:
fetch('/api/orders/couriers', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('token')}`
  }
}).then(r => {
  console.log('Status:', r.status);
  return r.json();
}).then(data => {
  console.log('Couriers:', JSON.stringify(data, null, 2));
});
```

**Expected Response:**
```javascript
[
  {
    "id": "uuid-string",
    "name": "India Post",
    "code": "INDIA_POST",
    "is_active": true,
    "is_default": true,
    "partner_type": "india_post",
    "customer_ids": [
      {"id": "1234", "name": "Branch A"}
    ]
  }
]
```

**If empty array `[]`:**
- Your delivery partners are not being saved correctly
- Check: Are you saving them? Is "Active" toggle enabled?

---

## Checklist for Resolution

- [ ] Opened browser console (F12) to check logs
- [ ] Found `[Orders] Loaded couriers: []` (confirming no data)
- [ ] Went to **Tenant Admin → Shipping Configuration**
- [ ] Created at least one delivery partner with:
  - [ ] Display Name (e.g., "India Post")
  - [ ] Partner Type (e.g., "india_post")
  - [ ] Marked as **✅ Active**
  - [ ] (Optional) Added Customer IDs if needed
- [ ] Clicked **"Save Delivery Partner"**
- [ ] Returned to Orders/Customers/Leads page
- [ ] Clicked "New Order" button again
- [ ] Verified dropdown now shows partners
- [ ] Selected a partner and saw the dropdown populate

---

## Common Issues & Solutions

### Issue: Dropdown Shows but Partner is Grayed Out

**Cause:** Partner is marked as **inactive** (Active toggle OFF)  
**Solution:** Go to Tenant Admin → Edit partner → Toggle **✅ Active** → Save

### Issue: "Select" Shows but No Options Appear

**Cause:** Partners exist but `is_active` is False in database  
**Solution:** Update in database:
```sql
UPDATE delivery_partners SET is_active = true WHERE tenant_id = '<your-tenant-id>';
```

### Issue: Service Type Doesn't Show for India Post

**Cause:** No Customer IDs added to the partner  
**Solution:** 
1. Go to Tenant Admin
2. Edit the India Post partner
3. Click **"+ Add Customer ID"**
4. Enter your India Post Customer ID (numeric)
5. Save

### Issue: Selected Partner Not Saving to Order

**Cause:** API endpoint updated but old cache  
**Solution:** 
1. Hard refresh browser: **Ctrl+Shift+R** (Windows) or **Cmd+Shift+R** (Mac)
2. Clear browser cache
3. Check browser console for errors

### Issue: "401 Unauthorized" Error in Console

**Cause:** Session expired  
**Solution:**
1. Log out
2. Log back in
3. Try again

---

## Backend Debug Info

If the issue persists, check server logs:

```bash
ssh root@172.105.48.142
cd /opt/pureleven
tail -100 logs/app.log | grep -i "courier\|delivery_partner\|order/couriers"
```

**Look for:**
- `[DEBUG] Fetching couriers for tenant: <tenant-id>`
- `[DEBUG] Found X active delivery partners`
- `[DEBUG]   - <partner-name> (<partner-type>)`

---

## Success Indicators

✅ **When Everything is Working:**

1. **Console logs show:**
   - `[Orders] Successfully populated 2 partners`
   
2. **Dropdown displays:**
   - "✓ Select Delivery Partner..." placeholder
   - Your configured partners as options
   - Default partner pre-selected (if configured)

3. **When selecting a partner:**
   - If partner has customer_ids, Service Type dropdown appears
   - Customer IDs populate with ID and name
   - Can submit order with both fields

4. **Order is created with:**
   - `shipping_partner_id` set to selected partner
   - `india_post_customer_id` set if India Post with Service Type selected

---

## Contact Support

If you've followed all steps and couriers still don't appear:

1. **Collect debug info:**
   ```bash
   # From browser console, run:
   fetch('/api/orders/couriers', {headers: {'Authorization': `Bearer ${localStorage.getItem('token')}`}})
     .then(r => r.json())
     .then(d => console.log(JSON.stringify(d, null, 2)))
   
   # Copy the output
   ```

2. **Check server logs:**
   ```bash
   ssh root@172.105.48.142 -t "tail -50 /opt/pureleven/logs/app.log"
   ```

3. **Report with:**
   - Browser console output
   - Server logs
   - Screenshot of Tenant Admin Shipping Configuration
   - Your tenant name

---

## Files Modified for Debugging

- `frontend/orders.html` - Enhanced `loadCouriers()` with detailed logging
- `frontend/customers.html` - Enhanced `noLoadCouriers()` with detailed logging
- `frontend/leads.html` - Enhanced `wonLoadCouriers()` with detailed logging
- `backend/app/modules/orders/router.py` - Added debug prints to `/api/orders/couriers`

All changes deployed in commit: **afc9a3a**

---

## Summary

**The courier dropdown won't show partners because:**
1. ❌ No delivery partners created in Tenant Admin
2. ❌ Partners created but not marked Active
3. ❌ Wrong tenant ID in configuration
4. ❌ Session expired (401 error)
5. ❌ Server error (check logs)

**Fix Priority:**
1. **First:** Create delivery partner in Tenant Admin → Shipping Configuration
2. **Second:** Mark it as **✅ Active**
3. **Third:** Add Customer IDs (if using India Post)
4. **Fourth:** Refresh browser and test

Once partners are configured and active, the dropdown will auto-populate on all three pages!
