# ⚡ Quick Reference: Draft Order Editing

## 🎯 What's New

Orders **without tracking numbers** can now be **completely edited**:
- Order number, payment amounts, delivery address
- Shipping partner, courier service, customer details
- Once tracking is assigned → **completely locked** 🔒

---

## 🔥 Quick Test

### Test with Order PRM-260225-040
1. Open orders table
2. Find order **PRM-260225-040** (draft, no tracking)
3. Click to open drawer
4. Look for **"✏️ Editable"** chip
5. Edit "Amount Paid" field → enter 200
6. Click **"💾 Save Changes"**
7. Verify:
   - ✅ Amount Paid = ₹200.00
   - ✅ Amount Due = ₹280.00 (auto-calc)
   - ✅ Pay Status = "🔶 Partial" (auto-inferred)

---

## 📋 Edit Mode Rules

### Order IS Editable ✏️
```
✓ No tracking_number assigned
✓ Status ≠ "delivered"
✓ Shows "✏️ Editable" chip
✓ All fields render as inputs
```

### Order IS Locked 🔒
```
✗ Has tracking_number
✗ Status = "delivered"
✗ No "✏️ Editable" chip
✗ All fields read-only
```

---

## 🎮 Editable Fields

When edit mode is active:

| Field | Type | Auto-Behavior |
|-------|------|---|
| Order Number | Text Input | — |
| Payment Method | Dropdown | — |
| **Amount Paid** | Number | Auto-infers payment_status |
| Amount Due | Number | — |
| Recipient Name | Text Input | — |
| Address | Textarea | — |
| City/District/State/Pin | Text Inputs | — |
| Alt Phone | Text Input | — |
| Courier Partner | Dropdown | — |
| Shipping Service | Dropdown | — |
| IP Customer ID | Text Input | — |

---

## 💰 Payment Status Auto-Inference

Edit Amount Paid field? Payment status updates automatically:

```
Amount Paid = 0      → Payment Status = "💵 Pending"
Amount Paid > 0      → Payment Status = "🔶 Partial"
Amount Paid >= Total → Payment Status = "✅ Paid"
```

---

## 🔄 Typical Workflows

### Workflow 1: Partial Payment Tracking
```
1. Customer calls: "I paid ₹200"
2. Open order drawer → See "✏️ Editable" chip
3. Click Amount Paid field → Enter 200
4. Click "💾 Save Changes"
5. Order now shows "🔶 Partial" payment status
6. Track remaining ₹280 for collection
```

### Workflow 2: Address Correction
```
1. Customer calls: "Address is wrong"
2. Open order drawer → See "✏️ Editable" chip
3. Edit delivery address, city, state, pincode
4. Click "💾 Save Changes"
5. Order reflects correct delivery address
```

### Workflow 3: Courier Change
```
1. Need to use different courier
2. Open order drawer → See "✏️ Editable" chip
3. Click Courier Partner dropdown
4. Select different partner
5. Click "💾 Save Changes"
6. Shipping info updated
```

---

## ✅ Buttons & Actions

### When Order is Editable (no tracking)
```
┌─────────────────────────────────────────┐
│ [✏️ Editable] ← Chip indicator          │
├─────────────────────────────────────────┤
│ [Order fields as editable inputs]       │
├─────────────────────────────────────────┤
│ [💾 Save Changes]  [✕ Cancel]           │
└─────────────────────────────────────────┘
```

### When Order is Locked (has tracking)
```
┌─────────────────────────────────────────┐
│ [Draft] [Pending]  ← No edit chip       │
├─────────────────────────────────────────┤
│ Order ID: PRM-260225-040 (read-only)    │
│ Amount: ₹480.00 (read-only)             │
├─────────────────────────────────────────┤
│ [✓ Confirm Order]  [Mark Processing]    │
└─────────────────────────────────────────┘
```

---

## 🛡️ Safety Features

✅ **Negative amounts blocked** - Frontend validation  
✅ **Tracking locks editing** - No exceptions  
✅ **Delivered locks editing** - No exceptions  
✅ **All-or-nothing saves** - No partial updates  
✅ **No concurrent conflicts** - Last write wins  

---

## 🔍 Troubleshooting

| Problem | Solution |
|---------|----------|
| Can't see edit fields | Check if order has tracking or is delivered |
| Changes didn't save | Check for error toast (shows validation errors) |
| Payment status didn't update | Reload page and check if amount was actually saved |
| Order suddenly locked | Tracking number was assigned after you opened it |

---

## 📊 Payment Status Inference Example

**Scenario:** Order total = ₹480

| Amount Paid | Amount Due | Status | Why |
|------------|-----------|--------|-----|
| ₹0.00 | ₹480.00 | 💵 Pending | No payment yet |
| ₹100.00 | ₹380.00 | 🔶 Partial | Partial amount received |
| ₹200.00 | ₹280.00 | 🔶 Partial | Still partial |
| ₹480.00 | ₹0.00 | ✅ Paid | Full amount received |
| ₹500.00 | ₹0.00 | ✅ Paid | Overpaid, marked as paid |

---

## ⚡ Key Shortcuts

**Save edits:** Click "💾 Save Changes" button  
**Discard edits:** Click "✕ Cancel" button  
**Close drawer:** Click X or Cancel  

**Tip:** If you're not sure if order is editable, look for **"✏️ Editable"** chip!

---

## 🎯 Files Modified

- ✅ `/opt/miguel/frontend/orders.html` (edit UI & save function)
- ✅ `/opt/miguel/backend/app/modules/orders/schemas.py` (amount fields)
- ✅ `/opt/miguel/backend/app/modules/orders/service.py` (auto-inference logic)

---

## 📚 Full Documentation

For detailed info, see:
- **DRAFT_ORDER_EDIT_FEATURE.md** - Technical details
- **DRAFT_ORDER_EDIT_VISUAL_GUIDE.md** - UI mockups & workflows
- **IMPLEMENTATION_VERIFICATION.txt** - Testing checklist
- **DRAFT_ORDER_EDIT_COMPLETE.md** - Full summary

---

## 🚀 Status

**Implemented:** ✅  
**Deployed:** ✅  
**Running:** ✅  
**Ready to Test:** ✅  

**Start testing with order PRM-260225-040 now!**

---

*Last Updated: 2026-02-26*  
*Implementation Time: This session*  
*Status: LIVE 🎉*
