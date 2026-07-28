# WhatsApp Shipping Notification — Quick Reference

## At a Glance

✅ **Feature:** Send WhatsApp messages to customers with tracking info  
✅ **When:** After tracking number is added to order  
✅ **Where:** Table row button or order drawer  
✅ **How:** Click → WhatsApp Web opens → User sends  

---

## 2-Minute Walkthrough

### Step 1: Add Tracking Number
1. Open order (click row or View button)
2. Scroll to "Shipping & Tracking" section
3. Select Courier Partner or enter Courier Name
4. Enter Tracking Number
5. Click **"💾 Update Tracking"**

### Step 2: Send WhatsApp
**Option A (From Table):**
- Locate order row
- Find "WhatsApp" column (after Courier & Tracking)
- Click green **"💬 Send"** button

**Option B (From Drawer):**
- After tracking added, green **"💬 Send on WhatsApp"** button appears
- Click it
- Both buttons do the same thing

### Step 3: In WhatsApp Web
- New tab opens with pre-filled message
- Review the text (customer name, tracking, address, etc.)
- Click Send ✓

**Done!** Customer receives shipping notification.

---

## Message Preview

```
Hello [Name],

Your Pure Leven order [ORDER#] has been shipped via India Post.

Tracking ID: [TRACKING#]
Estimated Delivery: 4–5 days

Items: Cardamom × 1, Black Pepper × 1
Delivery Address:
Kochi, Kerala, PIN 685561

Payment: Cash on Delivery — Collect ₹1200

Track your shipment:
https://www.indiapost.gov.in/_layouts/15/...
```

---

## When Button Appears

**✅ SHOWS "Send" button when:**
- Order has tracking number ✓
- Customer has phone number ✓

**❌ HIDES when:**
- No tracking assigned yet
- No customer phone
- Order is deleted/inactive

---

## Phone Numbers

**Supported Formats:**
- `9876543210` ✓
- `09876543210` ✓
- `+919876543210` ✓
- `+91 9876 543210` ✓

**Converted to:** `919876543210` (WhatsApp format)

---

## Payment Types in Message

| Type | Message |
|------|---------|
| COD | "Cash on Delivery — Collect ₹1200" |
| Partial COD | "Cash on Delivery — Collect ₹[balance due]" |
| Prepaid | "Prepaid" |

---

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Update Tracking | `Ctrl+Enter` (in drawer) |
| Send WhatsApp | Click button (no shortcut yet) |

---

## Troubleshooting

**Q: Button doesn't show?**  
A: Add tracking number first.

**Q: WhatsApp tab blank?**  
A: Log into https://web.whatsapp.com

**Q: Message doesn't look right?**  
A: Copy it, edit in WhatsApp before sending.

**Q: Want to add attachments?**  
A: Right now manual — you attach label PDF after message opens.

---

## URLs & Resources

- **WhatsApp Web:** https://web.whatsapp.com
- **India Post Tracking:** https://www.indiapost.gov.in (in message)
- **Feature Docs:** See WHATSAPP_SHIPPING_FEATURE.md

---

## Pro Tips

1. **Batch Send:** Open one order at a time, send to each customer
2. **Custom Message:** Edit in WhatsApp before sending (user can customize)
3. **Test First:** Send to yourself to see message format
4. **Check Phone:** Always verify customer phone before sending
5. **Time Zone:** Send during business hours in customer's region

---

**Last Updated:** March 12, 2026 (v1.0)
