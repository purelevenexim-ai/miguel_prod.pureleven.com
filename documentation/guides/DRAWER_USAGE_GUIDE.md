# Lead Drawer - Quick Start Guide

## 🎯 Quick Access

Click any **lead name** in the table → Drawer slides in from the right ✨

---

## 📍 What You'll See

### **Drawer Header**
```
┌────────────────────────────────┐
│ LEAD-00123                     │
│ John Doe                       │
│ +91 98765-43210  [📞] [💬]    │
│ [Status: New Lead ▼]           │
└────────────────────────────────┘
```

### **Drawer Tabs**
```
┌────────────────────────────────┐
│ Info | Activity | Orders | 💬  │
└────────────────────────────────┘
```

Click any tab to switch views instantly.

---

## 📊 Info Tab (Default)

Shows comprehensive lead profile:

```
╔════════════════════════════════╗
║ CONTACT                        ║
║ Name: John Doe                 ║
║ Phone: +91 98765-43210 [📞💬]  ║
║ Alternate: +91 87654-32109     ║
║ Email: john@example.com        ║
║ Company: ABC Corp              ║
╟────────────────────────────────╢
║ LEAD DETAILS                   ║
║ Product: Black Pepper 500g     ║
║ Source: [WhatsApp]             ║
║ City: Bangalore, Karnataka     ║
║ Created: Feb 20, 2026          ║
║ Follow-up: Feb 25, 2026        ║
║ Times Called: 3                ║
╟────────────────────────────────╢
║ 🏷 WABIS LABELS                ║
║ [Premium] [Hot Lead] [✎ Edit]  ║
╟────────────────────────────────╢
║ LAST NOTE                      ║
║ "Customer interested in bulk"  ║
╟────────────────────────────────╢
║ ＋ Log Call / Note             ║
╚════════════════════════════════╝
```

**Quick Actions:**
- 📞 Click phone button to call
- 💬 Click WhatsApp button to message
- ✎ Click "Edit" to modify details
- 🗑 Click "Delete" to remove lead
- ＋ Click "Note" to log activity

---

## 📋 Activity Tab

Timeline of all interactions:

```
╔════════════════════════════════╗
║ ＋ Log Activity                 ║
╟────────────────────────────────╢
║ [📞] Call — Interested         ║
║      Called and discussed bulk ║
║      2 hours ago               ║
╟────────────────────────────────╢
║ [📝] Note — Requested Quote    ║
║      Waiting for customer list ║
║      1 day ago                 ║
╟────────────────────────────────╢
║ [🔄] Status: new_lead → ...   ║
║      Contacted                 ║
║      3 days ago                ║
╟────────────────────────────────╢
║ [📞] Call — Follow-up          ║
║      First contact call        ║
║      1 week ago                ║
╚════════════════════════════════╝
```

**Click "＋ Log Activity"** to add:
- Phone calls
- Notes
- Status changes
- Custom activities

---

## 📦 Orders Tab

All orders created from this lead:

```
╔════════════════════════════════╗
║ 2 linked orders                ║
╟────────────────────────────────╢
║ ORD-20260220-001               ║
║ Feb 20, 2026 · Cash            ║
║                      ₹4,500.00 ║
║                      [Confirmed]║
╟────────────────────────────────╢
║ ORD-20260215-003               ║
║ Feb 15, 2026 · Card            ║
║                      ₹8,750.00 ║
║                      [Delivered]║
╚════════════════════════════════╝
```

**Click any order** to view full order details.

---

## 💬 Chat Tab

WhatsApp conversation:

```
╔════════════════════════════════╗
║                                ║
║         Hello! I'm interested  ║
║         in bulk orders         ║
║                      2h ago    ║
║                                ║
║                        Sure!   ║
║                  Send us your  ║
║                   requirements ║
║                        1h ago  ║
║                                ║
╟────────────────────────────────╢
║ [Type a message...         ][Send]║
╚════════════════════════════════╝
```

**Compose new message:**
1. Type your message
2. Press Enter or click Send
3. Message sent to WhatsApp

---

## 🎬 Actions from Drawer

### **Status Dropdown** (in header)
Change lead status:
- New Lead
- Created (via Order)
- 📞 Contacted ← *Shows outcome options*
- ⏰ Remind Later
- ✓ Won
- Lost

### **When Status = "Contacted"**
Special options appear:

```
┌──────────────────────────────────┐
│ ✅ Contacted — Choose outcome    │
├────────────────────────────────────┤
│  [📦]         [⏰]         [🚫]    │
│ Create Order | Remind Later | Lost │
└──────────────────────────────────┘
```

### **Footer Buttons**
```
┌──────────────────────────────────────┐
│ [🗑] | [✏ Edit] | [＋ Note]          │
│      [📦 Order] [📞 Contacted] [🏆 Won]
└──────────────────────────────────────┘
```

**Button Behavior:**
- 🗑 **Delete** - Remove the lead (red, always visible)
- ✏ **Edit** - Modify lead details (always visible)
- ＋ **Note** - Log activity/call (always visible)
- 📦 **Order** - Create order (only when status = contacted)
- 📞 **Contacted** - Mark as contacted (only for active leads)
- 🏆 **Won** - Mark won & create order (hidden when already done)

---

## 🔄 Complete Flow Example

### Step 1: Open Drawer
Click "Sarah Johnson" in the leads table

→ Drawer slides in from right
→ Overlay darkens background
→ Row highlights in blue
→ Info tab shows Sarah's details

### Step 2: Check Activity
Click **Activity** tab

→ See all calls and notes with Sarah
→ See she was called 3 days ago
→ See last note: "Interested in bulk"

### Step 3: Log New Contact
Click **＋ Log Activity** button in Activity tab

→ Modal opens
→ Select "Call" as type
→ Enter note: "Discussed pricing, waiting for quote"
→ Click "Save"
→ Activity added to timeline
→ Info tab shows updated "Last Contact"

### Step 4: Mark as Contacted
Click **📞 Contacted** button in footer

→ Modal opens asking for contact notes
→ Enter: "First discussion, sending quote"
→ Click "Save"
→ Status changes to "Contacted"
→ Special **outcome banner** appears with options:
  - [📦] Create Order
  - [⏰] Remind Later
  - [🚫] Mark Lost

### Step 5: Create Order
Click **[📦] Create Order** from outcome banner

→ Order creation drawer opens
→ Pre-filled with Sarah's details
→ Add order items, quantity, price
→ Click "Confirm Order"
→ Order created
→ Sarah's status becomes "Won"
→ Order appears in Orders tab

### Step 6: Close Drawer
Click outside drawer (on overlay)

→ Drawer slides out to right
→ Overlay disappears
→ Row unhighlights
→ Back to normal table view

---

## 💡 Pro Tips

1. **Quick Phone Call:** Click the 📞 button to dial immediately
2. **Send WhatsApp:** Click 💬 button to open WhatsApp Web
3. **Log Activity:** Use "＋ Log Activity" to track all interactions
4. **Change Status:** Use dropdown in header to quickly update status
5. **Create Order:** Only available when status = "Contacted"
6. **Check Orders:** Switch to Orders tab to see sales from this lead
7. **Review Chat:** Chat tab shows full WhatsApp conversation

---

## ⌨️ Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Send message | Enter in Chat tab |
| Focus search | Ctrl+F (browser default) |
| Close drawer | Escape (click overlay) |
| Log activity | ＋ button in Activity tab |

---

## 📱 Mobile Behavior

On smaller screens:
- Drawer width reduces to 100vw (full screen)
- All functionality remains the same
- Easier to read on mobile
- Swipe left to close (on some browsers)

---

## ✨ Animation Details

**Drawer Opens:**
- Duration: 0.25 seconds
- Easing: Smooth cubic-bezier curve
- Starts: Off-screen to the right
- Ends: Slides to left edge

**Drawer Closes:**
- Duration: 0.25 seconds
- Easing: Same smooth curve
- Starts: At left edge
- Ends: Off-screen to the right

**Overlay:**
- Fades in/out with drawer
- Click to close drawer
- Semi-transparent dark (32% opacity)

---

## 🚫 Troubleshooting

| Issue | Solution |
|-------|----------|
| Drawer doesn't open | Refresh page, check browser console |
| Overlay not clickable | Check if JavaScript is enabled |
| Status changes not saving | Check network connection |
| Messages not showing | Refresh Chat tab, check API connection |
| Order creation fails | Verify all required fields filled |

---

## 📞 Need Help?

Refer to:
- **Complete Reference:** `/opt/miguel/DRAWER_RESTORED_COMPLETE.md`
- **Code Details:** Look at `renderInfo()`, `renderActivity()`, `renderOrders()`, `renderChat()` in `leads.html`
- **API Docs:** Check `/api/leads/` endpoints in backend

---

*Last Updated: February 23, 2026*
*Status: ✅ Fully Functional*
