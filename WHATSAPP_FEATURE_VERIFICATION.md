# WhatsApp Feature Verification & Troubleshooting

**Date**: March 12, 2026  
**Status**: ✅ DEPLOYED  
**Version**: v1.0

---

## ✅ Feature Completeness Checklist

### Implementation
- ✅ WhatsApp column added to orders table (line 579)
- ✅ Send button in table row (line 1842)
- ✅ Send button in order drawer (line 2113)
- ✅ `normalizePhoneForWhatsApp()` function (line 3695)
- ✅ `composeShippedOrderMessage()` function (line 3717)
- ✅ `sendWhatsAppShipped()` function (line 3770)
- ✅ `sendWhatsAppFromDrawer()` function (line 3820)

### Button Conditions
The Send button appears **ONLY WHEN**:
```
o.tracking_number AND (o.customer_phone OR o.delivery_phone2)
```

**Both conditions must be true:**
1. ✅ Tracking number is assigned to the order
2. ✅ Customer has a phone number (either customer_phone or delivery_phone2)

---

## 🔍 Why the Send Button Doesn't Appear

If you don't see the Send button in the WhatsApp column, it's because:

### Reason 1: No Tracking Number (Most Common)
- **Current State**: Orders show `—` in Courier & Tracking column = No tracking yet
- **Solution**: Add a tracking number:
  1. Click "View" on an order
  2. Scroll to "Tracking" section in drawer
  3. Select a courier OR enter custom courier name
  4. Enter tracking number
  5. Click "💾 Update Tracking"
  6. **Button will now appear!**

### Reason 2: No Phone Number
- **Current State**: Order has tracking but no customer phone
- **Solution**: Add customer phone:
  1. Click "View" on order
  2. Add/update phone number in "Delivery To" section
  3. Save the order
  4. **Button will now appear!**

### Reason 3: Phone Format Invalid
- **Current State**: Phone exists but in wrong format
- **Solution**: Phone must be normalized to:
  - 10 digits: `9876543210`
  - With leading 0: `09876543210`
  - With +91: `+919876543210`
  - The system auto-converts to `919876543210` for WhatsApp

---

## 🚀 How to Send WhatsApp Message

### Method 1: From Orders Table (Quick)
1. Find an order with:
   - ✅ Tracking number assigned (visible in table)
   - ✅ Valid phone number
2. Click **💬 Send** button in WhatsApp column
3. ✅ WhatsApp Web/App opens with pre-filled message
4. Adjust message if needed and send

### Method 2: From Order Drawer (With Attachments)
1. Click **View** on an order
2. Scroll to "Tracking" section
3. If tracking is set, you'll see: **💬 Send on WhatsApp** button
4. Click the button
5. ✅ WhatsApp Web/App opens with:
   - Pre-filled shipping message
   - Note about label/invoice (manual attachment instruction)
6. Manually attach label PDF and invoice if needed

---

## 📱 Message Format (B - WITH TRACKING)

When customer has a tracking number, the message includes:

```
Hello [Customer Name],

Your Pure Leven order [Order #] has been shipped via [Courier].

Tracking ID: [Tracking Number]
Estimated Delivery: 4–5 days

Items: [Product 1 × Qty], [Product 2 × Qty]...
Delivery Address:
[Address], PIN [Pincode]

Payment: Cash on Delivery — Collect ₹[Amount]
         OR
         Prepaid — Paid ₹[Amount]

Track your shipment:
https://www.indiapost.gov.in/_layouts/15/dop.portal.tracking/trackconsignment.aspx
```

---

## 🔧 Troubleshooting

### Issue: Button shows but WhatsApp doesn't open
**Cause**: Browser blocked popup  
**Fix**: 
- Allow popups for this domain
- Use a device with WhatsApp app installed (will auto-open app)
- Check browser popup blocker settings

### Issue: Message shows wrong amount
**Cause**: Payment method not correctly set  
**Fix**:
- Update payment type in order: "COD" or "Prepaid"
- Set advance_amount if partial COD
- Click "Update Tracking" again

### Issue: Items not showing in message
**Cause**: Items not properly formatted in items_summary  
**Fix**:
- Check order items in drawer
- Items should be separated by commas or newlines
- Re-save order to update summary

### Issue: Phone shows as invalid
**Cause**: Phone in wrong format  
**Fix**:
- Use 10-digit format: `9876543210`
- Or +91 format: `+919876543210`
- Remove spaces and special characters

---

## 📊 Technical Details

### Phone Normalization
```javascript
function normalizePhoneForWhatsApp(phone) {
  // Remove all non-digits
  let p = String(phone).replace(/\D/g, '');
  
  // Keep only last 10 digits
  if (p.length > 10) p = p.slice(-10);
  
  // Must be exactly 10 digits
  if (p.length !== 10) return '';
  
  // Add India country code
  return '91' + p;  // Result: 919876543210
}
```

### Button Rendering (Table)
```html
<td style="text-align:center;">
  ${o.tracking_number && (o.customer_phone||o.delivery_phone2)
    ?`<button ... onclick="sendWhatsAppShipped('${o.id}')">💬 Send</button>`
    :'<span style="color:var(--g-500);">—</span>'}
</td>
```

### Button Rendering (Drawer)
```html
${o.tracking_number && (o.customer_phone||o.delivery_phone2)
  ?`<button ... onclick="sendWhatsAppFromDrawer('${o.id}')">💬 Send on WhatsApp</button>`
  :''}
```

---

## ✅ Verification Steps

### Step 1: Verify Feature is Deployed
```bash
# Check if code is on production
ssh root@172.105.48.142
grep -n "SendWhatsApp\|💬 Send" /opt/pureleven/frontend/orders.html

# Should show:
# Line 1842: <button ... onclick="sendWhatsAppShipped...
# Line 2113: <button ... onclick="sendWhatsAppFromDrawer...
```

### Step 2: Test with a Sample Order
1. Go to Orders tab
2. Create or find an order with:
   - ✅ Customer name
   - ✅ Delivery address with pincode
   - ✅ Customer phone (10 digits)
   - ✅ Items with prices
   - ✅ Confirm order
3. Add tracking number (View order → Add tracking → Update)
4. Verify **💬 Send** button appears in WhatsApp column
5. Click Send and verify WhatsApp opens
6. Verify message has correct:
   - Customer name
   - Order number
   - Tracking ID
   - Items list
   - Address
   - Payment method + amount

### Step 3: Test Phone Normalization
Test phones:
- ✅ `9876543210` → Works
- ✅ `09876543210` → Works (removes leading 0)
- ✅ `+919876543210` → Works
- ✅ `+91 98765 43210` → Works (removes spaces)
- ❌ `1234567` → Fails (less than 10 digits)
- ❌ `98765432101` → Works (keeps last 10)

---

## 📝 Known Limitations

1. **No Programmatic File Attachment**: WhatsApp Web doesn't allow auto-attaching PDFs via URL parameters
   - Solution: Message includes note to "manually attach files"
   
2. **Desktop vs Mobile**: 
   - Desktop: Opens WhatsApp Web
   - Mobile: Redirects to WhatsApp App
   
3. **Message Length**: WhatsApp has ~4,096 character limit
   - Current format: ~600-800 chars ✅ Well within limit

4. **Emoji Support**: Some emojis may not render on older devices
   - Uses: 💬 📱 ✓ 📍 ₹ (all standard, widely supported)

---

## 🔄 Update Flow

When tracking is updated:
1. User clicks "💾 Update Tracking" in drawer
2. API endpoint: `PATCH /api/orders/{id}/tracking`
3. Backend updates order with tracking_number
4. Frontend calls:
   - `await openDrawer(orderId)` → Refreshes drawer
   - `await loadOrders()` → Refreshes table
5. **WhatsApp Send button now appears** (both in table and drawer)
6. User can immediately send message

---

## 📞 API Endpoints Used

### Fetch Order Details
```
GET /api/orders/{orderId}
Headers: { Authorization: Bearer {token} }
Returns: Order object with all fields
```

### Update Tracking
```
PATCH /api/orders/{orderId}/tracking
Body: {
  "tracking_number": "CL3688757117IN",
  "shipping_partner_id": "india_post",
  "courier_name": "India Post",
  "courier_code": "india_post"
}
```

### Get Label (for attachment)
```
GET /api/orders/{orderId}/label
Returns: PDF file
```

### Get Invoice (for attachment)
```
GET /api/orders/{orderId}/invoice
Returns: PDF file
```

---

## 🎯 Success Criteria

✅ Feature considered working when:
1. WhatsApp column visible in orders table
2. Send button appears after tracking number is added
3. Clicking Send opens WhatsApp with pre-filled message
4. Message contains: order #, tracking ID, items, address, payment info
5. Works on both desktop (WhatsApp Web) and mobile (WhatsApp App)

---

**Last Updated**: March 12, 2026  
**Deployed By**: Miguel AI Agent  
**Production Status**: ✅ LIVE
