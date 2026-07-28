# WhatsApp Shipping Notification — Visual Guide

## Orders Table View

```
╔═════════════╦═══════════════╦════════════════╦═════════╦═════════╦═══════════════╦═════════════════╦═══════════════╦═════════╦═════════════╗
║  ☑          ║  ORDER        ║  CUSTOMER      ║  ITEMS  ║ AMOUNT  ║  PAYMENT      ║ STATUS          ║ COURIER       ║ WHATSAPP║ DATE  ║  ACTIONS  ║
╠═════════════╬═══════════════╬════════════════╬═════════╬═════════╬═══════════════╬═════════════════╬═══════════════╬═════════╬═════════════╣
║ ☐           ║ PRN-260312-003║ Sherly Tomichan║ Cardamom║ ₹845    ║ ⚡ Partial COD║ Confirmed ▼     ║ Indian Post   ║ 💬 Send ║ 12 Mar║ View Label ║
║             ║ 5m ago ✍️ man  ║ Kochi, Kerala  ║ 8mm    ║ Adv:₹60 ║ 🟠 Partial   ║                 ║               ║         ║       ║            ║
║             ║               ║                ║        ║         ║               ║                 ║               ║         ║       ║            ║
╠═════════════╬═══════════════╬════════════════╬═════════╬═════════╬═══════════════╬═════════════════╬═══════════════╬═════════╬═════════════╣
║ ☐           ║ PRN-260312-002║ Nadheera N K   ║ Pepper  ║ ₹540    ║ ⚡ Partial COD║ Confirmed ▼     ║ Indian Post   ║ 💬 Send ║ 12 Mar║ View Label ║
║             ║ 2h ago ✍️ man  ║ Calicut, Kerala ║ 500g   ║ Adv:₹100║ 🟠 Partial   ║                 ║               ║         ║       ║            ║
║             ║               ║                ║        ║         ║               ║                 ║               ║         ║       ║            ║
╠═════════════╬═══════════════╬════════════════╬═════════╬═════════╬═══════════════╬═════════════════╬═══════════════╬═════════╬═════════════╣
║ ☐           ║ PRN-260311-002║ Nowphal Hamza  ║ Cardamom║ ₹1899   ║ 🏦 UPI Paid   ║ Shipped ▼       ║ Indian Post   ║   —     ║ 11 Mar║ View       ║
║             ║ 22h ago ✍️ man ║ Thiruvanantha  ║ 8-200g ║        ║ ✅ Paid       ║                 ║ EL4843219IN   ║         ║       ║            ║
║             ║               ║ puram, Kerala  ║        ║         ║               ║                 ║               ║         ║       ║            ║
╚═════════════╩═══════════════╩════════════════╩═════════╩═════════╩═══════════════╩═════════════════╩═══════════════╩═════════╩═════════════╝

 ↑ Shows "Send" button only when:
   • Tracking number is assigned ✓
   • Customer has phone number ✓
```

---

## Order Drawer — Shipping Section

```
┌──────────────────────────────────────────────────────────────────────┐
│ SHIPPING & TRACKING                                                  │
│ ────────────────────────────────────────────────────────────────────│
│                                                                      │
│ Courier Partner                                                      │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ ▼ Select Courier                                                ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                      │
│ Tracking Number                                                      │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ EL4874321IN                                                      ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                      │
│ ┌──────────────────────────┐  ┌──────────────────────────────────┐ │
│ │ 💾 Update Tracking       │  │ 💬 Send on WhatsApp            │ │
│ └──────────────────────────┘  └──────────────────────────────────┘ │
│                                                                      │
│ ↑ "Send on WhatsApp" button shows when:                            │
│   • Tracking number is entered ✓                                   │
│   • Customer has phone ✓                                           │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## WhatsApp Web Message Preview

```
┌─────────────────────────────────────────────────────────────┐
│ Open WhatsApp Web ➜ https://web.whatsapp.com               │
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ Message Compose (Pre-filled):                           ││
│ ├──────────────────────────────────────────────────────────┤│
│ │                                                          ││
│ │ Hello Sherly Tomichan,                                 ││
│ │                                                          ││
│ │ Your Pure Leven order PRN-260312-003 has been         ││
│ │ shipped via Indian Post.                              ││
│ │                                                          ││
│ │ Tracking ID: EL4874321IN                              ││
│ │ Estimated Delivery: 4–5 days                          ││
│ │                                                          ││
│ │ Items: Cardamom 8mm - 100gm × 1                       ││
│ │ Delivery Address:                                      ││
│ │ Kochi, Kerala, PIN 685561                             ││
│ │                                                          ││
│ │ Payment: Cash on Delivery — Collect ₹785              ││
│ │                                                          ││
│ │ Track your shipment:                                   ││
│ │ https://www.indiapost.gov.in/_layouts/15/...         ││
│ │                                                          ││
│ │ [Send Button] [Attach] [+]                           ││
│ │                                                          ││
│ └──────────────────────────────────────────────────────────┘│
│                                                              │
│ User reviews & clicks "Send" to deliver message            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Customer's WhatsApp Chat

```
┌──────────────────────────────────────┐
│ Pure Leven Spices                    │
│ ══════════════════════════════════════│
│                                      │
│ [Customer]                           │
│ Hello, when will order arrive?       │
│ 2:15 PM                              │
│                                      │
│ [Bot Message - Shipped Notification] │
│                                      │
│ Hello Sherly Tomichan,               │
│                                      │
│ Your Pure Leven order PRN-260312-003 │
│ has been shipped via Indian Post.    │
│                                      │
│ Tracking ID: EL4874321IN             │
│ Estimated Delivery: 4–5 days         │
│                                      │
│ Items: Cardamom 8mm - 100gm × 1     │
│ Delivery Address:                    │
│ Kochi, Kerala, PIN 685561            │
│                                      │
│ Payment: Cash on Delivery —          │
│ Collect ₹785                         │
│                                      │
│ Track your shipment:                 │
│ [https://www.indiapost.gov.in/...]  │
│ 3:42 PM                              │
│                                      │
│ [Customer]                           │
│ Thank you! will track now            │
│ 3:43 PM                              │
│                                      │
└──────────────────────────────────────┘
```

---

## Button Color Coding

```
┌─────────────────────────────────────────────────────────────┐
│ Table Row WhatsApp Button                                   │
│                                                              │
│  Visible State (Green - Ready to Send):                    │
│  ┌─────────────┐                                            │
│  │ 💬 Send     │  ← Tracking present + Phone available    │
│  └─────────────┘                                            │
│  Color: #25d366 (WhatsApp Green)                           │
│                                                              │
│  Hidden State (Gray - Not Ready):                          │
│  ┌─────────────┐                                            │
│  │     —       │  ← No tracking OR No phone               │
│  └─────────────┘                                            │
│  Color: #999 (Gray)                                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Order Status Flow

```
                    Order Created
                         │
                         ↓
                  Draft → Confirmed
                         │
                         ↓
        ┌────────────────────────────────┐
        │    Processing / Packed         │
        │  (No WhatsApp yet)             │
        │                                │
        │ ☑ Add Tracking Number          │
        └────────────────────────────────┘
                         │
                         ↓
        ┌────────────────────────────────┐
        │       Shipped                  │
        │                                │
        │ ✓ Tracking Present             │
        │ ✓ Phone Present                │
        │                                │
        │ 💬 "Send" button NOW shows     │
        │   Click to send WhatsApp       │
        └────────────────────────────────┘
                         │
                    ┌────┴────┐
                    │          │
                    ↓          ↓
          Customer receives   Customer tracks
          WhatsApp message    order via link
                    │          │
                    └────┬────┘
                         ↓
              Out for Delivery
                         │
                         ↓
                   Delivered ✓
```

---

## Phone Number Formats

```
Input Format Examples → Conversion → WhatsApp Format
─────────────────────────────────────────────────────

9876543210        ─────────→  919876543210 ✓
(10 digits)

09876543210       ─────────→  919876543210 ✓
(0 + 10 digits)

+919876543210     ─────────→  919876543210 ✓
(+91 prefix)

+91 9876 543210   ─────────→  919876543210 ✓
(With spaces)

98765            ─────────→  ✗ INVALID
(Too few digits)

9876543210123    ─────────→  ✗ INVALID
(Too many digits)
```

---

## Feature Toggle Decision Tree

```
                    Order has tracking?
                          │
                    ┌─────┴─────┐
                   Yes         No
                    │           │
                    ↓           ↓
          Customer has phone?  Show: —
                    │
              ┌─────┴─────┐
             Yes          No
              │            │
              ↓            ↓
        Show: 💬 Send    Show: —
        Button visible  Button hidden
```

---

## Success Flow Diagram

```
1. User clicks "Send" or "Send on WhatsApp"
   │
   ↓
2. Fetch order details from API
   │
   ├─ Check tracking number exists
   │
   ├─ Check phone number exists
   │
   └─ Normalize phone to WhatsApp format
   │
   ↓
3. Compose message with:
   • Customer name, order number
   • Tracking ID, courier name
   • Items (first 3), delivery address
   • Payment status, tracking link
   │
   ↓
4. Generate WhatsApp URL:
   wa.me/91XXXXXXXXXX?text=[message]
   │
   ↓
5. Open in new tab
   │
   ↓
6. WhatsApp Web displays pre-filled message
   │
   ↓
7. User reviews (optional: edits) and sends
   │
   ↓
8. Show notification: ✅ Opening WhatsApp...
```

---

## Keyboard & Mouse Interactions

```
╔════════════════════════════════════════════════════════════╗
║ INTERACTION GUIDE                                          ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║ TABLE ROW:                                                 ║
║ ├─ Click Row         → Opens order drawer                 ║
║ └─ Click "Send"      → Opens WhatsApp Web (no drawer)    ║
║                                                            ║
║ DRAWER:                                                    ║
║ ├─ Input Tracking    → Enables "Send on WhatsApp"        ║
║ ├─ Click "Update"    → Saves tracking, shows button      ║
║ └─ Click "Send on WA"→ Opens WhatsApp Web with message   ║
║                                                            ║
║ WHATSAPP WEB:                                              ║
║ ├─ Message pre-filled (read-only display)                 ║
║ ├─ Edit text (optional) before sending                    ║
║ └─ Click "Send" or Ctrl+Enter → Delivers                 ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
```

---

## Error Scenarios

```
┌────────────────────────────────────────────────────────────┐
│ ERROR HANDLING                                             │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ ❌ No Tracking Number                                     │
│    Message: "Please add tracking number first"           │
│    Action: User adds tracking and tries again            │
│                                                            │
│ ❌ No Phone Number                                        │
│    Message: "No customer phone number"                   │
│    Action: User adds phone to order                      │
│                                                            │
│ ❌ Invalid Phone Format                                   │
│    Message: "Invalid phone number"                       │
│    Action: User corrects phone format                    │
│                                                            │
│ ❌ Failed to Fetch Order                                  │
│    Message: "Failed to fetch order details"              │
│    Action: Retry or refresh page                         │
│                                                            │
│ ⚠️  WhatsApp Web Not Logged In                            │
│    Message: Blank page or login screen                   │
│    Action: User logs into web.whatsapp.com first         │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

**Visual Guide Complete**  
For more details, see:
- `WHATSAPP_SHIPPING_FEATURE.md` (technical docs)
- `WHATSAPP_QUICK_REFERENCE.md` (user guide)
