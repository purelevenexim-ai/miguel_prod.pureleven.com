# WhatsApp Shipping Notification Feature

**Date:** March 12, 2026  
**Status:** ✅ Deployed to Production  
**Commit:** `0325cbb`

---

## Overview

Added WhatsApp messaging capability to the Orders tab. When a tracking number is assigned to an order, users can send an automated WhatsApp message to the customer with:
- Order number
- Tracking ID
- Courier name
- Items list
- Delivery address
- Payment status
- India Post tracking link

---

## Features

### 1. **New "WhatsApp" Column in Orders Table**
- Located between "Courier & Tracking" and "Date" columns
- Shows **"Send"** button (green WhatsApp icon) when:
  - Order has a tracking number assigned ✅
  - Customer has a phone number ✅
- Shows **"—"** (dash) when conditions not met

### 2. **Send Button Locations**

#### A. Orders Table Row
```
PRN-260312-003 | Customer | Items | Amount | Payment | Status | Courier | [WhatsApp] | Date | Actions
                                                                                    💬 Send
```
- Click **"💬 Send"** to open WhatsApp Web with pre-filled message
- Stops event propagation (doesn't open order drawer)

#### B. Order Drawer (Shipping Section)
```
Courier Partner     [Dropdown]
Courier Name        [Input]
Tracking Number     [Input]
[💾 Update Tracking] [💬 Send on WhatsApp]
```
- **"💬 Send on WhatsApp"** button appears after tracking is added
- Sits next to "Update Tracking" button
- Opens WhatsApp Web with pre-filled message + attachment hints

---

## Message Format

Based on "B) WITH TRACKING (Order shipped)" from `shipping_label.py`:

```
Hello [Customer Name],

Your Pure Leven order [ORDER_NUMBER] has been shipped via [COURIER_NAME].

Tracking ID: [TRACKING_ID]
Estimated Delivery: 4–5 days

Items: [PRODUCT_1 × QTY_1], [PRODUCT_2 × QTY_2], ...
Delivery Address:
[ADDRESS], PIN [PINCODE]

Payment: [Cash on Delivery — Collect ₹XXX] OR [Prepaid]

Track your shipment:
https://www.indiapost.gov.in/_layouts/15/dop.portal.tracking/trackconsignment.aspx
```

### Message Fields

| Field | Source | Notes |
|-------|--------|-------|
| Customer Name | `order.customer_name` or `order.delivery_name` | Personalized greeting |
| Order Number | `order.order_number` | Order ID from system |
| Courier | `order.courier_name` | "India Post" if not set |
| Tracking ID | `order.tracking_number` | Must be present to show button |
| Items | `order.items_summary` or `order.items[]` | Shows first 3 items max |
| Address | `order.delivery_address` | Full delivery address |
| Pincode | `order.delivery_pincode` | 6-digit postal code |
| Payment | `order.payment_method` | Calculated balance for partial COD |

---

## Phone Number Handling

### Normalization Function
```javascript
normalizePhoneForWhatsApp(phone)
```

**Input Formats Accepted:**
- 10 digits: `9876543210` → `919876543210`
- Leading 0: `09876543210` → `919876543210`
- +91 prefix: `+919876543210` → `919876543210`
- With spaces: `+91 9876 543210` → `919876543210`

**Output:** `91` + 10-digit number (WhatsApp format)

---

## User Workflow

### Scenario: Send Shipping Notification

1. **User adds tracking number:**
   - Opens order drawer
   - Fills in Courier Partner (or Courier Name)
   - Enters Tracking Number
   - Clicks **"💾 Update Tracking"**
   - Order updates in backend

2. **User sends WhatsApp:**
   - Option A: Click **"💬 Send"** button in table row
   - Option B: Click **"💬 Send on WhatsApp"** in drawer
   - WhatsApp Web opens in new tab
   - Pre-filled message visible in compose box
   - User reviews + sends message
   - Browser shows notification confirmation

3. **What customer receives:**
   - WhatsApp message with complete order details
   - Tracking link ready to use
   - Can reply with questions

---

## Technical Implementation

### Frontend (orders.html)

#### New Functions

**1. `normalizePhoneForWhatsApp(phone)`**
- Cleans phone number to 10 digits
- Adds "91" prefix for India
- Returns empty string if invalid

**2. `composeShippedOrderMessage(order)`**
- Takes order object from API
- Constructs human-readable message
- Handles items parsing (summary or array)
- Calculates COD balance for partial payments
- Returns complete message string

**3. `sendWhatsAppShipped(orderId)`** (Table Row)
- Fetches order details from `/api/orders/{orderId}`
- Validates: tracking number + phone
- Normalizes phone number
- Composes message
- Opens: `https://wa.me/{phone}?text={encoded_message}`
- Shows success notification

**4. `sendWhatsAppFromDrawer(orderId)`** (Drawer)
- Same as above
- Additionally shows note about manual file attachments
- Suggests label/invoice URLs (can be pasted)
- Message includes attachment hints

#### UI Changes

**Table Header:**
```html
<th>WhatsApp</th>  <!-- Added between Courier & Tracking, Date -->
```

**Table Row:**
```html
<td style="text-align:center;">
  ${o.tracking_number && (o.customer_phone||o.delivery_phone2)
    ?`<button ... onclick="sendWhatsAppShipped('${o.id}')">💬 Send</button>`
    :'<span>—</span>'}
</td>
```

**Drawer Buttons:**
```html
<div style="display:flex;gap:8px;">
  <button onclick="updateOrderTracking('${o.id}')">💾 Update Tracking</button>
  ${o.tracking_number && (o.customer_phone||o.delivery_phone2)
    ?`<button onclick="sendWhatsAppFromDrawer('${o.id}')">💬 Send on WhatsApp</button>`
    :''}
</div>
```

---

## Limitations & Notes

### WhatsApp Web Only
- Opens WhatsApp Web, not native app on desktop
- Mobile browsers automatically open WhatsApp app
- Requires WhatsApp Web to be previously logged in
- No API integration (manual send by user)

### No Programmatic Attachments
- WhatsApp Web API doesn't support file attachments via URL
- Solution: User manually attaches label PDF + invoice
- Message includes links to files as reference
- Drawer version includes URLs in message hints

### Phone Number Validation
- Only Indian phone numbers supported (9X format)
- 10 digits required
- Supports: 9876543210, 09876543210, +919876543210

### Items Display
- Shows first 3 items maximum (to keep message short)
- Parses from `items_summary` or `items[]` array
- Handles both comma and line-separated formats

### Payment Types
- **Prepaid:** Shows "Prepaid"
- **COD:** Shows "Cash on Delivery — Collect ₹XXXX"
- **Partial COD:** Calculates balance: `amount - advance_paid`
- **UPI/Bank:** Shows "Prepaid" (non-COD)

---

## Testing Checklist

- [ ] Table shows WhatsApp column in correct position
- [ ] Send button appears only when: tracking + phone ✅
- [ ] Send button is hidden when: no tracking OR no phone
- [ ] Clicking table Send button opens WhatsApp Web
- [ ] Drawer shows Send button after tracking added
- [ ] Drawer button opens WhatsApp with same message
- [ ] Message includes all required fields
- [ ] Items show correctly (comma-separated, max 3)
- [ ] Indian phone numbers normalize correctly
- [ ] +91 prefix handled properly
- [ ] Payment status calculates for partial COD
- [ ] India Post tracking link valid
- [ ] Message sends without errors

---

## Production Deployment

**File:** `/opt/pureleven/frontend/orders.html`  
**Method:** SCP + Git Pull  
**Commit:** `0325cbb`

**Verification:**
```bash
# Check file deployed
ls -lh /opt/pureleven/frontend/orders.html

# Verify git history
cd /opt/pureleven && git log --oneline -1
# Output: 0325cbb feat: add WhatsApp shipping notification column...
```

---

## Future Enhancements

1. **WhatsApp Business API Integration**
   - Direct API instead of Web
   - Programmatic file attachments
   - Message templates for compliance

2. **Auto-Send on Status Change**
   - Automatically send when tracking added
   - Setting: "Auto-send WhatsApp on shipped"

3. **Message Templates**
   - Customizable message text
   - Brand name/signature
   - Multiple language support

4. **Attachment Automation**
   - Generate QR code for tracking
   - Attach actual PDFs via API
   - Label + Invoice inline

5. **Bulk Send**
   - Select multiple orders
   - Send to all at once
   - Progress tracker

---

## Troubleshooting

**Issue:** "WhatsApp opened but message is empty"
- **Cause:** Message encoding failed
- **Solution:** Check phone number and order details in console

**Issue:** "WhatsApp doesn't open"
- **Cause:** WhatsApp Web not logged in
- **Solution:** User must log in at https://web.whatsapp.com

**Issue:** "Button doesn't appear in table"
- **Cause:** No tracking number or phone missing
- **Solution:** Add tracking number and ensure customer phone exists

**Issue:** "Phone number not recognized"
- **Cause:** Invalid format (too many digits, wrong prefix)
- **Solution:** Use 10-digit format (9876543210)

---

## Files Changed

```
frontend/orders.html
├── Added WhatsApp column header
├── Added table cell with Send button
├── Added drawer Send on WhatsApp button
└── Added 4 new functions:
    ├── normalizePhoneForWhatsApp()
    ├── getFirstItemLine()
    ├── composeShippedOrderMessage()
    ├── sendWhatsAppShipped()
    └── sendWhatsAppFromDrawer()
```

**Total Changes:** 195 insertions(+), 1 deletion(-)

---

**End of Document**
