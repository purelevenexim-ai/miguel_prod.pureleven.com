# Draft Order Edit Feature - Visual Guide

## 🎯 What Changed

### BEFORE: Orders Without Tracking (Read-Only)
```
┌─────────────────────────────────────────┐
│ Order PRM-260225-040                    │
├─────────────────────────────────────────┤
│ Draft  | 💵 Pending  | Not Confirmed    │
├─────────────────────────────────────────┤
│ Order ID:      PRM-260225-040 (read-only) │
│ Date:          2026-02-25              │
│ Total:         ₹480.00                 │
│ Payment Method: COD                    │
│ Pay Status:    [Dropdown]  ← Only this editable!
│ Amount Due:    ₹480.00 (read-only)      │
│ Amount Paid:   ₹0.00 (read-only)        │
│ Delivery:      John Doe (read-only)     │
│ Address:       123 Main St (read-only)  │
│ Shipping:      India Post (read-only)   │
├─────────────────────────────────────────┤
│ [✏️ Edit Payment] [✓ Confirm Order]     │ ← Limited options
└─────────────────────────────────────────┘
```

### AFTER: Orders Without Tracking (FULLY EDITABLE! ✏️)
```
┌──────────────────────────────────────────────┐
│ Order PRM-260225-040                         │
├──────────────────────────────────────────────┤
│ Draft | 💵 Pending | Not Confirmed | ✏️ Edit │ ← Editable indicator!
├──────────────────────────────────────────────┤
│ Order ID:        [PRM-260225-040_______]      │ ← EDITABLE input
│ Date:            2026-02-25                 │
│ Total:           ₹480.00                    │
│ Payment Method:  [COD ▼]                    │ ← EDITABLE dropdown
│ Pay Status:      [💵 Pending ▼]  Dropdown   │
│ Amount Paid:     [0.00_________]            │ ← EDITABLE input
│ Amount Due:      [480.00________]           │ ← EDITABLE input
│                                              │
│ ── Delivery ──────────────────────────────  │
│ Recipient Name:  [John Doe________]         │ ← EDITABLE
│ Address:         [123 Main St_______]       │ ← EDITABLE textarea
│ City:            [Mumbai____] District: [__] │ ← EDITABLE
│ State:           [Maharashtra_]  Pincode: [] │ ← EDITABLE
│ Alt Phone:       [9876543210_]              │ ← EDITABLE
│                                              │
│ ── Shipping ──────────────────────────────  │
│ Courier:         [India Post ▼]             │ ← EDITABLE dropdown
│ Service:         [Speed Post ▼]             │ ← EDITABLE
│ IP Customer ID:  [12345_____]               │ ← EDITABLE
│                                              │
│ Items...                                     │
├──────────────────────────────────────────────┤
│ [💾 Save Changes]  [✕ Cancel]               │ ← NEW buttons!
└──────────────────────────────────────────────┘
```

---

## 📋 Edit Mode Rules

### ✅ ORDER IS EDITABLE IF:
- ✓ No tracking number assigned yet
- ✓ Order status ≠ "delivered"
- ✓ Both manual AND Shopify orders

### 🔒 ORDER IS READ-ONLY IF:
- ✗ Tracking number already assigned
- ✗ Order status = "delivered"
- ✗ (Future: Role-based restrictions)

---

## 🎮 User Interactions

### Scenario: Customer Requests Address Change
```
1. User opens order drawer
   ↓
2. Sees "✏️ Editable" chip (indicator!)
   ↓
3. Clicks on any delivery field (input active)
   ↓
4. Types new address
   ↓
5. Changes state/city/pincode
   ↓
6. Clicks "💾 Save Changes"
   ↓
7. Backend validates & saves
   ↓
8. "✅ Order updated successfully" toast
   ↓
9. Drawer closes, table refreshes
   ↓
10. Order now shows new address ✓
```

### Scenario: Partial COD Payment Received
```
1. User opens PRM-260225-040 (draft, no tracking)
   ↓
2. Sees "✏️ Editable" chip
   ↓
3. Clicks "Amount Paid" field
   ↓
4. Enters "200.00" (customer paid ₹200)
   ↓
5. Clicks "💾 Save Changes"
   ↓
6. Backend:
   - Sets amount_paid = 200.00
   - amount_due = 280.00 (480 - 200)
   - Auto-infers payment_status = "partial" ✓
   ↓
7. Order drawer refreshes showing:
   - Pay Status: "🔶 Partial"
   - Amount Paid: ₹200.00
   - Amount Due: ₹280.00
   ↓
8. User tracks this is partial payment ✓
```

### Scenario: Order with Tracking (LOCKED)
```
1. User opens order with tracking number
   ↓
2. NO "✏️ Editable" chip shown
   ↓
3. All fields display as read-only text
   ↓
4. No Save/Cancel buttons
   ↓
5. Only status progression buttons shown
   ↓
6. Order cannot be edited ✓
```

---

## 🧪 Testing Checklist - What to Try

### Test Case 1: Draft Order (No Tracking)
- [ ] Open order without tracking_number
- [ ] Verify "✏️ Editable" appears
- [ ] Click order number field, edit it, save
- [ ] Check table shows updated order number
- [ ] Click amount paid field, enter 200, save
- [ ] Verify payment_status changed to "partial"
- [ ] Verify amount_due auto-calculated

### Test Case 2: Order with Tracking (Locked)
- [ ] Open order with tracking_number set
- [ ] Verify NO "✏️ Editable" chip
- [ ] Verify all fields are plain text (not inputs)
- [ ] Verify "Save/Cancel" buttons don't appear
- [ ] Verify only "Mark [Status]" buttons show

### Test Case 3: Delivered Order (Locked)
- [ ] Open order with status = "delivered"
- [ ] Verify NO "✏️ Editable" chip
- [ ] Verify all fields read-only
- [ ] Verify no edit buttons in footer

### Test Case 4: Payment Inference
- [ ] Edit order, set amount_paid = 0 → save
- [ ] Check payment_status = "pending"
- [ ] Edit order, set amount_paid = 100 → save
- [ ] Check payment_status = "partial"
- [ ] Edit order, set amount_paid = total → save
- [ ] Check payment_status = "paid"

### Test Case 5: Address Changes
- [ ] Edit delivery name, address, city, state
- [ ] Save all changes
- [ ] Verify delivery section shows updates
- [ ] Verify saved to database

### Test Case 6: Courier Changes
- [ ] Edit courier from India Post to Delhivery
- [ ] Change shipping service to Parcel
- [ ] Save
- [ ] Verify shipping info updated

---

## 💡 Key Features

### Auto-Inference
When you edit amount_paid:
```
amount_paid = 0      → payment_status = "pending" 💵
amount_paid = 200    → payment_status = "partial" 🔶 (total is 480)
amount_paid = 480    → payment_status = "paid"    ✅
```

### Validation
- Amounts must be ≥ 0 (frontend prevents negatives)
- Order number must be unique (backend check)
- Tracking prevents all edits (order.tracking_number check)
- Delivered status prevents all edits (order.status check)

### Visual Feedback
- Input fields have light borders → clearly editable
- "✏️ Editable" chip → shows edit mode active
- "💾 Save Changes" button → green, prominent
- Cancel button → outlined, secondary
- Success toast → "✅ Order updated successfully"
- Error messages → shown immediately if validation fails

---

## 🔄 What Happens When You Save

### Behind the Scenes:
```
Frontend saveOrderEdit()
  ↓
  Gathers all field values:
  - orderNumber, paymentMethod
  - amountPaid, amountDue
  - deliveryName, address, city, state, pincode, phone
  - courierCode, shippingService, indiaPostCustomerId
  ↓
PATCH /api/orders/{orderId}
  ↓
Backend update_order()
  ↓
  Validates:
  - Amounts ≥ 0 ✓
  - No tracking prevents edits ✓
  - Not delivered prevents edits ✓
  ↓
  Updates database fields
  ↓
  Auto-infers payment_status from amount_paid
  ↓
  Creates status history if status changed
  ↓
  Returns updated Order object
  ↓
Frontend success handler
  ↓
  Shows "✅ Order updated successfully"
  ↓
  Closes drawer
  ↓
  Reloads order table
  ↓
  User sees updated order ✓
```

---

## 🎯 Success Criteria

✅ Orders without tracking can be completely edited  
✅ Payment amounts can be updated with auto-status-inference  
✅ Delivery addresses can be edited  
✅ Shipping partner/service can be changed  
✅ Once tracking assigned → fully locked  
✅ Once delivered → fully locked  
✅ Works for both manual and Shopify orders  
✅ All changes saved to database  
✅ Status history records status changes only  
✅ Error handling for validation failures  
✅ Intuitive UI with clear edit indicators  

---

## 🚀 Deployment Summary

| Component | Status | Notes |
|-----------|--------|-------|
| Frontend HTML | ✅ Updated | New edit UI, Save/Cancel buttons |
| Backend Schema | ✅ Updated | Added amount_paid, amount_due fields |
| Backend Logic | ✅ Updated | Auto-inference, validation, update |
| Docker | ✅ Running | Backend restarted, all changes live |
| Testing | ⏳ Ready | Test with order PRM-260225-040 |

**Ready for production testing! 🎉**
