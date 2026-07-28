# Troubleshooting Guide: Draft Order Edit Changes Not Applied

## Problem
Changes made to order PRM-260225-040 (and possibly other orders) are not being saved.

## Root Cause Checklist

### 1. **Is the Order Actually in Edit Mode?**

Check the console logs:
```javascript
// You should see this when opening the order drawer:
🔍 Order Debug: {
  order_number: "PRM-260225-040",
  status: "draft",
  tracking_number: null,
  canEdit: true,
  reason: "editable"
}
```

**If canEdit = false:**
- ❌ Order has tracking number assigned
- ❌ Order status is "delivered"
- ✅ Check order details to confirm status/tracking

**If canEdit = true:**
- ✅ Order should be editable
- Proceed to step 2

### 2. **Are the Input Fields Rendering?**

When you look at the drawer:
- Check if "✏️ Editable" chip appears in header
- Check if Amount Paid field is an `<input>` element (not text)
- Right-click → Inspect Element on the field

**If fields are text (not inputs):**
- ❌ canEdit is false (see Step 1)

**If fields are inputs:**
- ✅ Form is rendering correctly
- Proceed to step 3

### 3. **Is the Save Request Being Sent?**

When you click "💾 Save Changes":
- Open console (F12)
- Look for `📤 Sending PATCH payload:`
- Should show something like:
```javascript
📤 Sending PATCH payload: {
  amount_paid: 200,
  amount_due: 280
}
```

**If you see this:**
- ✅ Frontend is sending the data correctly
- Proceed to step 4

**If you don't see this:**
- ❌ Check if button is actually being clicked
- Check browser console for JavaScript errors
- Try opening console BEFORE clicking save

### 4. **What is the Server Responding?**

Look for:
```javascript
📥 Response status: 200 OK
✅ Server response: {
  id: "...",
  order_number: "PRM-260225-040",
  amount_paid: 200,
  ...
}
```

**If status = 200:**
- ✅ Server accepted the update
- Check if order in table/drawer shows the new values

**If status = 400 or 422:**
- ❌ Server rejected the update
- Look for error message:
```javascript
❌ Error response: {
  detail: "..."  // Read this message for the reason
}
```

### 5. **Did the Table Reload?**

After save:
- Order drawer should close
- Order table should refresh
- New values should appear in table

**If drawer didn't close:**
- ❌ There was an error (check steps 3-4)

**If drawer closed but values are still old:**
- ❌ Backend accepted but didn't save
- ❌ Database not updating
- Check backend logs

---

## Quick Debugging Steps

### Step 1: Open Developer Console
```
Windows/Linux: F12
Mac: Cmd + Option + I
Or: Right-click → Inspect
```

### Step 2: Go to Console Tab
Look for our custom logs starting with emoji:
- 🔍 = Order debug info
- 📤 = Data being sent
- 📥 = Server response
- ✅ = Success
- ❌ = Error
- 💥 = Exception

### Step 3: Try Editing Again
1. Click order to open drawer
2. Look for 🔍 debug output
3. If canEdit=true, try editing a field
4. Click "💾 Save Changes"
5. Look for 📤 PATCH payload
6. Look for 📥 Response status

### Step 4: Copy Error Message
If you see an error, copy it and report:
- The full error message
- The payload that was sent
- The order ID (UUID from the URL)

---

## Common Issues & Solutions

### Issue 1: "Amounts cannot be negative"
**Problem:** You entered a negative number or empty field  
**Solution:** Enter a positive number >= 0

### Issue 2: Changes sent but order values not updating
**Problem:** Server says 200 OK but drawer shows old values  
**Solution:** 
- Hard refresh page (Ctrl+Shift+R)
- Clear browser cache
- Check that loadOrders() actually ran after save

### Issue 3: "Cannot edit" error message
**Problem:** Server rejecting edit because order has tracking or is delivered  
**Solution:**
- Check order status in table
- Check if tracking number is set
- Order can only be edited if: NO tracking AND status ≠ "delivered"

### Issue 4: Form fields not showing as inputs
**Problem:** Fields appear as text, not editable  
**Cause:** canEdit = false (order has tracking or is delivered)  
**Solution:** Find order without tracking first

### Issue 5: Network error when saving
**Problem:** "Network error" message shown  
**Solution:**
- Check if backend is running: `docker-compose ps`
- Check if you're still authenticated
- Check browser network tab for CORS errors

---

## Testing the Fix

### Good Order to Test With:
**Order PRM-260225-040**
- Status: draft
- Tracking: (should be empty/none)
- Payment: COD, amount ₹480

### Expected Behavior:
1. Open order → See "✏️ Editable" chip
2. Edit Amount Paid → Enter 200
3. Click Save
4. See success message
5. Drawer closes
6. Table reloads
7. Order shows Amount Paid = ₹200

---

## Backend Log Analysis

If frontend says 200 OK but nothing changed:

Check backend logs:
```bash
docker-compose logs backend 2>&1 | tail -50
```

Look for:
```
"PATCH /api/orders/[order-id] HTTP/1.1" 200 OK
```

If you see 400 or 422:
```
400 Bad Request
422 Unprocessable Entity
```

The error detail is in the response body, check the ❌ Error response in console.

---

## Database Check

If server says OK but database wasn't updated:

```bash
# Connect to postgres
docker-compose exec postgres psql -U miguel_user -d miguel_db

# Find the order
SELECT id, order_number, amount_paid, amount_due, status 
FROM orders 
WHERE order_number = 'PRM-260225-040';

# Check if amount_paid was actually updated
SELECT amount_paid, amount_due, updated_at 
FROM orders 
WHERE order_number = 'PRM-260225-040'
ORDER BY updated_at DESC LIMIT 1;
```

---

## What to Report If It's Still Not Working

Provide:
1. Browser console logs (copy the emoji logs)
2. The payload being sent (📤 line)
3. The server response (📥 line)
4. Backend logs if available
5. Exact steps you took
6. What value you tried to change

Example:
```
I tried to change Amount Paid from 0 to 200 on order PRM-260225-040.

Console shows:
🔍 Order Debug: canEdit=true, status=draft, tracking_number=null
📤 Sending PATCH payload: {amount_paid: 200}
📥 Response status: 200 OK
✅ Server response: {id: "...", amount_paid: 200, ...}

But the order still shows amount_paid: 0

When I reload the page, it still shows 0.
```

---

## Updated Code Summary

The following improvements were made to diagnose the issue:

### Frontend Changes:
1. **Added debug logging** to console showing order state
2. **Improved amount validation** to handle NaN values properly
3. **Added response logging** to see exactly what server returns
4. **Better error messages** to identify the issue

### What to Look For:
- 🔍 = Debug info about order editability
- 📤 = Exact PATCH payload being sent
- 📥 = Server's HTTP status code
- ✅ = Success response data
- ❌ = Error response details
- 💥 = JavaScript exception

---

## Next Steps

1. Try the steps above with browser console open
2. Look for the emoji logs
3. Report exactly what you see
4. If it works now, the fixes resolved it!
5. If still broken, the debug logs will show exactly where the problem is

---

Remember: **The emoji logs are your best friend** 🎯

Look for:
- 🔍 to see if order is editable
- 📤 to see what's being sent
- 📥 to see server's response

**Everything is logged now for easy debugging!**
