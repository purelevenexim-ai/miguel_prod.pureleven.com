# WhatsApp Send Button - Quick Visual Guide

## 📸 What You Should See

### ✅ WHEN SEND BUTTON APPEARS (After Tracking Added)

```
┌─────────────────────────────────────────────────────────────┐
│ WHATSAPP Column                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 💬 Send  ← GREEN BUTTON (WhatsApp color #25d366)   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Conditions:                                                │
│  ✅ Has tracking number                                    │
│  ✅ Has customer phone                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### ❌ WHEN SEND BUTTON DOESN'T APPEAR (Before Tracking)

```
┌─────────────────────────────────────────────────────────────┐
│ WHATSAPP Column                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  —  ← DASH (indicating no action available yet)           │
│                                                             │
│  Missing one or both:                                      │
│  ❌ No tracking number                                     │
│  ❌ No customer phone                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Step-by-Step: Make Send Button Appear

### Step 1: Open Order
```
Orders Table
    ↓
[View] button
    ↓
Order Drawer Opens
```

### Step 2: Add Tracking Number
```
In Drawer → Scroll to "Tracking" section

  ▾ Courier Partner        [Select India Post ▼]
  
  Courier Name             [Auto-filled or enter custom]
  
  Tracking Number          [CL3688757117IN]
                           ↑
                    (REQUIRED - enter tracking ID)
  
  [💾 Update Tracking] ← Click this
```

### Step 3: Verify & Send
```
Table refreshes automatically
    ↓
Order row now shows "CL3688..." in Tracking column
    ↓
WhatsApp column now shows [💬 Send] button
    ↓
Click [💬 Send]
    ↓
WhatsApp Web/App opens with pre-filled message ✅
```

---

## 📱 Two Places to Send

### Place 1: From Table (Fastest)
```
Orders Table
    ↓
Find order with tracking + phone
    ↓
WhatsApp column → [💬 Send]
    ↓
WhatsApp opens immediately
```

### Place 2: From Drawer (Full Control)
```
Orders Table
    ↓
[View] button
    ↓
Order Drawer
    ↓
Tracking section → [💬 Send on WhatsApp]
    ↓
WhatsApp opens with full message
    ↓
(Can manually attach label/invoice)
```

---

## ✉️ Message Preview

When you click Send, customer receives:

```
Hello Sherly Tomichan,

Your Pure Leven order PRN-260312-003 has been shipped via 
India Post.

Tracking ID: CL3688757117IN
Estimated Delivery: 4–5 days

Items: Kerala Cardamom 8mm - 100gm × 1
Delivery Address:
Kochi, Kerala, PIN 682001

Payment: Cash on Delivery — Collect ₹845

Track your shipment:
https://www.indiapost.gov.in/_layouts/15/dop.portal.
tracking/trackconsignment.aspx
```

---

## 🚨 Common Issues & Fixes

### Issue 1: No Send Button Appears
```
Problem:  ❌ WhatsApp column shows "—"
Reason:   Missing tracking number
Fix:      Add tracking number → [💾 Update Tracking]
Expected: Button appears automatically ✅
```

### Issue 2: Phone Not Recognized
```
Problem:  ❌ Phone field shows error
Reason:   Invalid phone format
Fix:      Use one of these formats:
          ✅ 9876543210
          ✅ 09876543210  
          ✅ +919876543210
Expected: Button appears ✅
```

### Issue 3: Button Clicked But WhatsApp Didn't Open
```
Problem:  ❌ Nothing happened
Reason:   Popup blocked by browser
Fix:      Option 1: Allow popups for this site
          Option 2: Click again and check browser notifications
          Option 3: Use mobile device (auto-opens app)
Expected: WhatsApp opens with message ✅
```

### Issue 4: Wrong Amount in Message
```
Problem:  ❌ Message shows wrong payment amount
Reason:   Payment type not set correctly
Fix:      Check order payment method:
          - Is it "COD"?
          - Is advance_amount set?
          - Re-save order if needed
Expected: Correct amount appears in message ✅
```

---

## 🎯 Checklist Before Sending

Before clicking [💬 Send], verify order has:

```
☑️ Customer name (appears in greeting)
☑️ Delivery address with pincode (for delivery info)
☑️ Customer phone number (to open WhatsApp)
☑️ Tracking number (required for send button)
☑️ Items list (appears in message)
☑️ Payment method (COD or Prepaid)
☑️ Amount if COD (shows collect amount)
```

All checked? → Click [💬 Send] ✅

---

## 📊 Button State Diagram

```
                    ┌─────────────────────┐
                    │  New Order Created  │
                    └──────────┬──────────┘
                               │
                    ❌ NO TRACKING YET
                    Show: "—" in WhatsApp
                               │
                    Courier selected
                    Tracking added
                               │
                    ✅ TRACKING ADDED
                    Show: [💬 Send] button
                               │
                          Click Send
                               │
                    ┌─────────────────────┐
                    │ WhatsApp Opens with │
                    │  Pre-filled Message │
                    └─────────────────────┘
                               │
                          User sends
                               │
                    ✅ CUSTOMER RECEIVED
                      TRACKING INFO
```

---

## 🔐 Required Permissions

To use WhatsApp feature, ensure:

```
✅ Browser allows popups (for desktop)
✅ WhatsApp account linked to phone (desktop)
✅ WhatsApp app installed (mobile)
✅ Valid phone number format (system auto-corrects)
✅ Order fully created/confirmed
```

---

## 📲 Desktop vs Mobile

### Desktop (WhatsApp Web)
```
Click [💬 Send]
    ↓
Browser opens new tab → WhatsApp Web
    ↓
Message pre-filled
    ↓
Send through web interface
```

### Mobile (WhatsApp App)
```
Click [💬 Send]
    ↓
Browser redirects to WhatsApp app
    ↓
Chat window opens
    ↓
Message pre-filled
    ↓
Send through mobile app
```

---

## ⚡ Quick Commands (Developer)

### View Button HTML (Table)
```html
<button class="btn btn-outlined btn-xs" 
    style="background:#25d366;color:#fff;" 
    onclick="sendWhatsAppShipped('${o.id}')" 
    title="Send WhatsApp with tracking">
    💬 Send
</button>
```

### View Button HTML (Drawer)
```html
<button class="btn btn-sm" 
    style="background:#25d366;color:white;" 
    onclick="sendWhatsAppFromDrawer('${o.id}')" 
    title="Send WhatsApp with tracking">
    💬 Send on WhatsApp
</button>
```

### Check Console for Errors
```javascript
// Open browser DevTools (F12)
// Go to Console tab
// Click Send button
// Watch for error messages
// Common errors:
// - "No tracking number assigned"
// - "No customer phone number"
// - "Invalid phone number"
```

---

## 🎓 Training Scenario

### Real-World Example

```
1. Order PRN-260312-003 created
   Customer: Sherly Tomichan
   Phone: 9876543210
   Status: Confirmed
   
2. Order status changes to "Shipped"
   Tracking added: CL3688757117IN
   
3. Table now shows:
   Order | Customer | Items | ... | Tracking | WhatsApp | Actions
   PRN.. | Sherly.. | Card. | ... | CL3688.. | [💬Send] | [View]
   
4. You click [💬 Send]
   ↓
   WhatsApp opens showing:
   "Hello Sherly Tomichan, Your Pure Leven order PRN-260312-003..."
   
5. Customer clicks "Send"
   ↓
   Sherly instantly gets tracking info on WhatsApp ✅
```

---

**Last Updated**: March 12, 2026  
**Status**: ✅ Production Ready  
**Audience**: Support Team, Operations, Developers
