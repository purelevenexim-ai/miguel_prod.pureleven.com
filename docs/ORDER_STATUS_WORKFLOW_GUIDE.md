# 📦 Order Status Workflow & Tracking Guide

**File:** `/opt/miguel/docs/ORDER_STATUS_WORKFLOW_GUIDE.md`  
**Updated:** 2026-02-24  
**Status:** ✅ ACTIVE

---

## 📋 Overview

This guide explains the complete order status flow, how to advance orders through the pipeline, and how to track orders from different shipping providers.

### Order Status Pipeline

```
CREATION              FULFILLMENT              DELIVERY              FINAL
┌────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  draft → confirmed → processing → packed → shipped → out_for_delivery → delivered
│                                                                      ↓
│                                                                   returned
│  [cancelled - can be done from draft/confirmed/processing/packed]
│                                                                          │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Status Descriptions & Actions

### 1. **DRAFT** (Order Created but Not Confirmed)
- **When:** New not-confirmed order created (customer is a Lead)
- **Next Status:** `confirmed` or `cancelled`
- **Actions Available:**
  - ✓ Confirm Order (when customer confirms)
  - ✗ Cancel Order

### 2. **CONFIRMED** (Order Confirmed, Ready for Processing)
- **When:** Customer confirms they want to order
- **What Happens:**
  - Inventory is automatically reserved/reduced
  - Customer record is created if new
  - WhatsApp confirmation sent to customer
- **Next Status:** `processing` or `cancelled`
- **Actions Available:**
  - 📤 Mark Processing (start picking items)
  - 🏷 Print Label (optional - for internal reference)

### 3. **PROCESSING** (Picking & Packing in Progress)
- **When:** Staff starts picking items from inventory
- **What Happens:**
  - Items are being gathered for the order
  - QC check may be performed
- **Next Status:** `packed` or `cancelled`
- **Actions Available:**
  - 📦 Mark Packed (when all items picked and ready)
  - 🏷 Print Label (shipping label)

### 4. **PACKED** (Ready for Handoff to Courier)
- **When:** All items packed, ready for courier pickup
- **What Happens:**
  - Package is ready at warehouse
  - Awaiting courier pickup or manual shipment
- **Next Status:** `shipped` or `cancelled`
- **Actions Available:**
  - 🚚 Mark Shipped (add tracking number)
  - 🏷 Print Label (final shipping label)

### 5. **SHIPPED** (In Transit with Courier)
- **When:** Package handed to courier, tracking number assigned
- **What Happens:**
  - Customer gets WhatsApp with tracking details
  - Tracking number + courier name stored in system
- **Next Status:** `out_for_delivery` or `returned`
- **Actions Available:**
  - 🚛 Out for Delivery (update from Delhivery/India Post)
  - Update Tracking (if tracking number changes)

### 6. **OUT_FOR_DELIVERY** (Last Mile - Rider Has It)
- **When:** Package is with delivery partner, in their vehicle
- **What Happens:**
  - Tracked via Delhivery/India Post tracking ID
  - Delivery expected today/tomorrow
- **Next Status:** `delivered` or `returned`
- **Actions Available:**
  - ✅ Mark Delivered (when customer confirms receipt)

### 7. **DELIVERED** ✅ (Order Complete)
- **When:** Customer receives package
- **What Happens:**
  - `delivered_at` timestamp recorded
  - Payment status updated if needed
  - Appears in P&L reports as completed revenue
  - WhatsApp delivery notification sent
- **Next Status:** `returned` (if customer initiates return)
- **Actions Available:**
  - Create Return (if customer requests)

### 8. **RETURNED** (Product Sent Back)
- **When:** Customer initiates return after delivery
- **What Happens:**
  - Inventory restored
  - Refund may be processed
  - Order marked as non-revenue
- **Next Status:** None (final state)

### 9. **CANCELLED** (Order Not Fulfilled)
- **When:** Cancelled at any point before shipping
- **What Happens:**
  - Inventory restored if was confirmed
  - Revenue not counted in P&L
  - Customer notified
- **Next Status:** None (final state)

---

## 📱 How to Advance Order Status

### From Orders List
1. Open the **Orders** tab
2. Find the order in the list
3. Click on it to open the drawer (right panel)
4. Look at the **Status section** to see current status
5. Click the **blue action button** (varies by status):
   - ✓ Confirm Order
   - 📤 Mark Processing
   - 📦 Mark Packed
   - 🚚 Mark Shipped
   - 🚛 Out for Delivery
   - ✅ Mark Delivered

### When Marking Shipped
- A prompt appears: **"Enter tracking number (optional):"**
- Enter the tracking ID from your courier (Delhivery, India Post, etc.)
- If you leave it blank, you can add it later

### Status History
- Bottom of the drawer shows **Status History**
- Shows all status changes with timestamps
- Shows who made the change and any notes

---

## 🚚 Tracking Orders by Courier

### **India Post (Speed Post / Parcel)**

**When to use:**
- COD (Cash on Delivery) orders
- Orders going to smaller cities/villages
- Default for our Indian postal service

**How to get tracking:**
1. After handoff to India Post, ask for **Tracking/Reference Number**
2. Format: Usually 13 digits (e.g., `RK123456789IN`)
3. Enter in order: "Mark Shipped" → paste tracking number

**Track shipment:**
- Visit: **https://www.indiapost.gov.in/vas/trackingservice**
- Enter tracking number
- See: Dispatch → In Transit → Out for Delivery → Delivered

**Status mapping:**
- India Post "In Transit" = Order Status: **shipped**
- India Post "Out for Delivery" = Order Status: **out_for_delivery**
- India Post "Delivered" = Order Status: **delivered**

---

### **Delhivery (Private Courier)**

**When to use:**
- Prepaid orders (faster service)
- Orders to major metros
- Time-sensitive deliveries

**How to get tracking:**
1. After handing package to Delhivery, get **AWB Number** (Air Waybill)
2. Format: Usually 10 digits (e.g., `1234567890`)
3. Enter in order: "Mark Shipped" → paste AWB number

**Track shipment:**
- Visit: **https://www.delhivery.com/tracking/**
- Enter AWB number
- See: Booked → In Transit → Out for Delivery → Delivered

**Status mapping:**
- Delhivery "In Transit" = Order Status: **shipped**
- Delhivery "Out for Delivery" = Order Status: **out_for_delivery**
- Delhivery "Delivered" = Order Status: **delivered**

---

### **Shopify Orders (Via Tracking Link)**

**When to use:**
- Orders sync'd from Shopify store
- Tracking automatically linked

**How to track:**
- Order tracking link sent to customer in WhatsApp
- Tracking managed through Shopify's system
- Manual update: After Delhivery delivery, click "Mark Delivered" in Miguel

---

## 📊 Order Tracking Workflow (Manual Reference)

Use this workflow as a **manual checklist** when processing orders:

```
╔════════════════════════════════════════════════════════════════════════════╗
║                     ORDER PROCESSING WORKFLOW                              ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║ STEP 1: ORDER RECEIVED (Status: draft or confirmed)                        ║
║ ─────────────────────────────────────────────────────────────────────────  ║
║ □ Customer places order (online, phone, WhatsApp)                          ║
║ □ Employee creates order in Miguel                                         ║
║ □ Order marked as: 'draft' (not confirmed) or 'confirmed' (ready)         ║
║ □ If not confirmed, lead created for follow-up                           ║
║ □ If confirmed, inventory automatically reduced                          ║
║                                                                              ║
║ STEP 2: CONFIRMATION (Only if Draft)                                      ║
║ ─────────────────────────────────────────────────────────────────────────  ║
║ □ Customer confirms via call/WhatsApp                                      ║
║ □ Click "✓ Confirm Order" button in Miguel                               ║
║ □ Status changes to: confirmed                                           ║
║ □ Inventory reserved                                                     ║
║ □ Customer gets WhatsApp confirmation                                    ║
║                                                                              ║
║ STEP 3: PICKING & PACKING (Status: confirmed → processing)               ║
║ ─────────────────────────────────────────────────────────────────────────  ║
║ □ Warehouse staff receives confirmed order                               ║
║ □ Click "📤 Mark Processing" in Miguel                                    ║
║ □ Staff picks items from inventory                                       ║
║ □ Quality check performed on items                                       ║
║ □ Package assembled and ready                                           ║
║ □ Click "📦 Mark Packed" in Miguel                                       ║
║ □ Status changes to: packed                                             ║
║                                                                              ║
║ STEP 4: GENERATE SHIPPING LABEL (Status: packed)                         ║
║ ─────────────────────────────────────────────────────────────────────────  ║
║ □ Click "🏷 Print Label" button                                           ║
║ □ Select courier: India Post or Delhivery                                ║
║ □ Label printed and affixed to package                                   ║
║ □ Barcode scanned for sortation                                          ║
║                                                                              ║
║ STEP 5: HANDOFF TO COURIER (Status: packed → shipped)                    ║
║ ─────────────────────────────────────────────────────────────────────────  ║
║ □ Package handed to courier (India Post or Delhivery)                    ║
║ □ Get TRACKING NUMBER from courier:                                      ║
║   ├─ India Post: 13-digit reference (RK1234567890IN)                   ║
║   └─ Delhivery: 10-digit AWB (1234567890)                              ║
║ □ Click "🚚 Mark Shipped" in Miguel                                      ║
║ □ Paste tracking number in prompt                                        ║
║ □ Status changes to: shipped                                            ║
║ □ Customer gets WhatsApp with tracking info                             ║
║                                                                              ║
║ STEP 6: TRACK IN TRANSIT (Status: shipped)                               ║
║ ─────────────────────────────────────────────────────────────────────────  ║
║ For INDIA POST orders:                                                      ║
║   □ Visit: https://www.indiapost.gov.in/vas/trackingservice              ║
║   □ Enter: 13-digit tracking number                                       ║
║   □ See: Dispatch → In Transit → Out for Delivery → Delivered           ║
║                                                                              ║
║ For DELHIVERY orders:                                                       ║
║   □ Visit: https://www.delhivery.com/tracking/                            ║
║   □ Enter: 10-digit AWB number                                           ║
║   □ See: Booked → In Transit → Out for Delivery → Delivered             ║
║                                                                              ║
║ STEP 7: OUT FOR DELIVERY (Status: shipped → out_for_delivery)            ║
║ ─────────────────────────────────────────────────────────────────────────  ║
║ □ Track via courier website, see "Out for Delivery" status               ║
║ □ Click "🚛 Out for Delivery" in Miguel                                  ║
║ □ Status changes to: out_for_delivery                                   ║
║ □ Delivery expected same/next day                                        ║
║                                                                              ║
║ STEP 8: DELIVERY CONFIRMATION (Status: out_for_delivery → delivered)    ║
║ ─────────────────────────────────────────────────────────────────────────  ║
║ Option A: Customer Confirms                                                ║
║   □ Customer receives package, confirms via WhatsApp/call                ║
║   □ Click "✅ Mark Delivered" in Miguel                                   ║
║   □ Paste message: "Package received - thank you!"                      ║
║                                                                              ║
║ Option B: Track Shows Delivered                                             ║
║   □ Courier's tracking shows "Delivered"                                 ║
║   □ Click "✅ Mark Delivered" in Miguel                                   ║
║   □ System auto-records delivery_at timestamp                           ║
║                                                                              ║
║ □ Status changes to: delivered                                           ║
║ □ Order appears in P&L reports as completed revenue                     ║
║ □ Customer gets delivery WhatsApp notification                          ║
║                                                                              ║
║ STEP 9: POST-DELIVERY (Status: delivered) [OPTIONAL]                     ║
║ ─────────────────────────────────────────────────────────────────────────  ║
║ □ Send thank you message via WhatsApp                                     ║
║ □ Request review/feedback                                                ║
║ □ Process refund if COD payment due                                      ║
║ □ If return request: Click "returned" → refund process                  ║
║                                                                              ║
╚════════════════════════════════════════════════════════════════════════════╝
```

---

## ✅ TEST CASES

### Test Case 1: Full Order Flow (Confirmed → Delivered)

**Scenario:** Customer orders 2 kg turmeric, COD via India Post

**Steps:**
1. Create order in Miguel: Status = `confirmed`
2. Open order drawer
   - Verify button shows: "📤 Mark Processing"
3. Click "📤 Mark Processing"
   - Verify status changed to: `processing`
   - Click refresh, verify persists
4. Click "📦 Mark Packed"
   - Verify status changed to: `packed`
   - Verify button now shows: "🚚 Mark Shipped"
5. Click "🚚 Mark Shipped"
   - Prompt appears: "Enter tracking number (optional):"
   - Enter: `RK123456789IN`
   - Verify status changed to: `shipped`
6. Visit India Post website, verify "In Transit"
7. Click "🚛 Out for Delivery"
   - Verify status changed to: `out_for_delivery`
8. Click "✅ Mark Delivered"
   - Verify status changed to: `delivered`
   - Verify in P&L overview: order appears in revenue

**Expected Result:** ✅ PASS - Order shows as delivered revenue in P&L

---

### Test Case 2: Delhivery Order with AWB

**Scenario:** Prepaid order, Delhivery shipping

**Steps:**
1. Create order: Status = `confirmed`
2. Click "📤 Mark Processing" → status = `processing`
3. Click "📦 Mark Packed" → status = `packed`
4. Click "🚚 Mark Shipped"
   - Enter: `1234567890` (Delhivery AWB)
   - Verify status = `shipped`
5. Visit https://www.delhivery.com/tracking
   - Enter AWB: `1234567890`
   - See in-transit status
6. When Delhivery shows "Out for Delivery"
   - Click "🚛 Out for Delivery" in Miguel
7. When Delhivery shows "Delivered"
   - Click "✅ Mark Delivered" in Miguel

**Expected Result:** ✅ PASS - Tracking synced, P&L reflects delivery

---

### Test Case 3: Draft → Confirmed Workflow

**Scenario:** Customer creates not-confirmed order (lead), then confirms later

**Steps:**
1. Create order with `order_intent='not_confirmed'`
   - Verify status = `draft`
   - Verify button shows: "✓ Confirm Order"
   - Verify Lead is created
2. Customer calls to confirm
3. Click "✓ Confirm Order"
   - Verify status = `confirmed`
   - Verify Customer is created/linked
   - Verify inventory reserved
4. Continue with normal processing flow

**Expected Result:** ✅ PASS - Lead converted to customer + order

---

### Test Case 4: Status History Tracking

**Scenario:** Verify all status transitions are logged

**Steps:**
1. Create confirmed order
2. Advance through all statuses (processing → packed → shipped)
3. Open order drawer
4. Scroll to "Status History" section
5. Verify each transition shows:
   - Date/time
   - Old status → New status
   - Employee who made change

**Expected Result:** ✅ PASS - All transitions logged with timestamps

---

### Test Case 5: Error Handling - Invalid Status

**Scenario:** Try to advance order to invalid status

**Steps:**
1. Create order with status = `confirmed`
2. Open browser DevTools → Network tab
3. Click "📤 Mark Processing"
4. Verify API call shows: `POST /api/orders/{id}/status`
5. Body: `{ "status": "processing" }`
6. Response: 200 OK

**Now test invalid transition:**
1. Order is `confirmed`
2. Try to set status to `delivered` directly (cheat via API)
3. API response should be: `400 Bad Request`
4. Message: `"Cannot move from 'confirmed' to 'delivered'. Allowed: ['processing', 'cancelled']"`

**Expected Result:** ✅ PASS - Backend blocks invalid transition

---

### Test Case 6: Profit & Loss Report

**Scenario:** Verify P&L only counts delivered orders

**Steps:**
1. Create 3 turmeric orders:
   - Order A: Status = `delivered` (revenue = ₹500)
   - Order B: Status = `shipped` (revenue = ₹500)
   - Order C: Status = `confirmed` (revenue = ₹500)
2. Open **Profit & Loss** tab → **Overview**
3. Filter: Period = "Today"
4. Verify stat card "Total Revenue" shows: ₹500 (only Order A)
5. Mark Order B as delivered
6. Refresh P&L
7. Verify "Total Revenue" now shows: ₹1000

**Expected Result:** ✅ PASS - P&L only counts delivered

---

## 🐛 Troubleshooting

### Problem: "Mark Shipped" button doesn't work
**Solution:**
- Verify order status = `packed` (not `confirmed`)
- Check browser console for errors
- Ensure you have Sales/Operations role

### Problem: Tracking number not saved
**Solution:**
- Verify number was pasted (not typed mid-change)
- Refresh order drawer
- Check order status changed to `shipped`

### Problem: Order not appearing in P&L
**Solution:**
- Verify order status = `delivered` (not `shipped`)
- Check delivery date is within filtered period
- Refresh P&L page (Ctrl+Shift+R)

---

## 📞 Support

For issues, contact support with:
- Order number (e.g., PLX-260224-001)
- Current status
- Last action attempted
- Error message (if any)

---

**Last Updated:** 2026-02-24  
**Version:** 1.0  
**Status:** ✅ LIVE
