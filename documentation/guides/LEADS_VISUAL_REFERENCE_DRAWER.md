# Leads Page - Visual Design Reference

## 🎨 Right-Side Drawer with Tabs

### Desktop View
```
┌────────────────────────────────────────────────────────────────────────────┐
│  TOPBAR (Fixed top)                                                        │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  LEADS TABLE (Scrollable)                      ┌──────────────────────┐   │
│  ┌──────────────────────────────────────┐      │ DRAWER (Slides in)   │   │
│  │ # │ Name & Phone │ Product │ Status │      ├──────────────────────┤   │
│  ├──────────────────────────────────────┤      │                      │   │
│  │L1 │ John Doe     │ Pepper  │ Contacted    │ Lead: LEAD-00001      │   │
│  │   │ +91 98765... │  200g   │ 5 days  │    │ John Doe             │   │
│  │   │              │         │        │      │ +91 98765-43210      │   │
│  ├──────────────────────────────────────┤      │ [✕ Close]            │   │
│  │L2 │ Jane Smith   │ Cumin   │ New    │    │ Status: [Contacted ▼]│   │
│  │   │ +91 87654... │  100g   │ New    │    │                      │   │
│  │   │              │         │        │      ├──────────────────────┤   │
│  └──────────────────────────────────────┘      │ ℹ️ Info │ 📋 Activity │   │
│                                               │ 📦 Orders │ 💬 Chat      │   │
│  ▓▓▓▓ DARK OVERLAY                            ├──────────────────────┤   │
│  ▓ (rgba(0,0,0,.4))                           │                      │   │
│  ▓ (Click to close)                           │ Tab Content Here:    │   │
│  ▓▓▓▓                                          │ (scrollable)         │   │
│                                               │                      │   │
│                                               ├──────────────────────┤   │
│                                               │ [🗑] [✏️] [➕] [📦] │   │
│                                               │ [📞] [🏆]            │   │
│                                               └──────────────────────┘   │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

### Mobile View
```
┌──────────────────────┐
│  TOPBAR              │
├──────────────────────┤
│  DRAWER (Full Width) │
│  ┌────────────────┐  │
│  │ LEAD-00001     │  │
│  │ John Doe       │  │
│  │ +91 987654...  │  │
│  │ [✕ Close]      │  │
│  │ Status: [▼]    │  │
│  │ [ℹ️] [📋] [📦] │  │
│  │ [💬]           │  │
│  │                │  │
│  │ Tab Content    │  │
│  │ (scrolls)      │  │
│  │                │  │
│  │ [Actions]      │  │
│  └────────────────┘  │
│                      │
│ ▓▓ Overlay ▓▓        │
│                      │
│ TABLE (Below)        │
│                      │
└──────────────────────┘
```

---

## 📐 Component Dimensions

### Drawer
- **Width:** 500px (fixed)
- **Height:** 100vh (full viewport)
- **Position:** Fixed, right edge
- **Border:** 1px left border (outline-variant)
- **Shadow:** Standard material shadow

### Overlay
- **Size:** Full viewport (100vw x 100vh)
- **Color:** Black with 40% opacity (rgba(0,0,0,.4))
- **Position:** Behind drawer (z-index: 299)

### Header Section
- **Padding:** 20px all
- **Border-bottom:** 1px outline-variant
- **Content:**
  - Lead number: 11px, uppercase, gray
  - Lead name: 18px, bold, black
  - Phone: 13px, gray
  - Close button: 32px square, top-right corner
  - Status dropdown: Full width below close button

### Tabs Section
- **Padding:** 0 (connected to header border)
- **Border-bottom:** 1px outline-variant
- **Layout:** Flex row, space-around
- **Tab Height:** 48px
- **Tab Padding:** 12px horizontal, 16px vertical
- **Tab Text:** 13px, uppercase, medium weight
- **Active Indicator:** 2px bottom border, primary color

### Body Section
- **Padding:** 20px
- **Flex:** 1 (fills available space)
- **Overflow:** Auto (scrollable if needed)
- **Max height:** 100% of remaining space

### Footer Section
- **Padding:** 16px 20px
- **Border-top:** 1px outline-variant
- **Layout:** Flex row, wrap enabled
- **Gap:** 8px between buttons
- **Button Height:** 32px (small)
- **Button Padding:** 8px 12px

---

## 🎬 Animation States

### State 1: Closed (Default)
```css
.ov {
  opacity: 0;
  pointer-events: none;
}

.detail-panel {
  transform: translateX(100%);  /* Off-screen right */
  pointer-events: none;
}
```

### State 2: Opening
```css
/* Transition starts */
.ov {
  opacity: 0 → 1;
  transition: opacity .25s;
}

.detail-panel {
  transform: translateX(100%) → translateX(0);
  transition: transform .25s cubic-bezier(.4,0,.2,1);
}

/* Duration: 250ms */
/* Easing: Smooth acceleration curve */
```

### State 3: Open
```css
.ov.open {
  opacity: 1;
  pointer-events: auto;
}

.detail-panel.open {
  transform: translateX(0);  /* Fully visible */
  pointer-events: auto;
}
```

### State 4: Closing
```css
/* Transition starts */
.ov {
  opacity: 1 → 0;
  transition: opacity .25s;
}

.detail-panel {
  transform: translateX(0) → translateX(100%);
  transition: transform .25s cubic-bezier(.4,0,.2,1);
}

/* Ends in State 1 (Closed) */
```

---

## 🎨 Color Palette

| Element | Color | Role |
|---------|-------|------|
| **Drawer BG** | Surface (white) | Main background |
| **Header Text** | On-surface (black) | Primary text |
| **Subtext** | On-surface-variant (gray) | Secondary text |
| **Border** | Outline-variant (light gray) | Dividers |
| **Tab Active** | Primary (blue) | Active indicator |
| **Tab Hover** | Primary (blue) | Interactive state |
| **Overlay** | Black 40% | Focus overlay |
| **Delete Button** | #c5221f (red) | Destructive action |
| **Order Button** | #137333 (green) | Positive action |
| **Won Button** | Primary (blue) | Success state |

---

## 📋 Content Areas

### Info Tab
```
Lead Details
├── Lead Number: LEAD-00001
├── Contact Info
│   ├── Name: John Doe
│   ├── Phone: +91 98765-43210
│   └── Email: john@example.com
├── Product Interest
│   └── Black Pepper 200g
├── Notes
│   └── [User notes here]
└── Labels
    └── [Tag 1, Tag 2, Tag 3]
```

### Activity Tab
```
Activity Timeline
├── [Today 2:30 PM] → Status changed to Contacted
├── [Today 11:45 AM] → Note added
├── [Yesterday 4:20 PM] → Lead created
└── [Load more...]
```

### Orders Tab
```
Linked Orders
├── Order #ORD-00123
│   ├── Date: Feb 20, 2026
│   ├── Status: Completed
│   └── Amount: ₹1,500
├── Order #ORD-00110
│   ├── Date: Feb 10, 2026
│   ├── Status: Pending
│   └── Amount: ₹2,300
└── [No more orders]
```

### Chat Tab
```
WhatsApp Messages
├── [2:15 PM] You: Hi John!
├── [2:18 PM] John: Hello!
├── [2:20 PM] You: Can I help you?
└── [Scroll for more...]
```

---

## 🔌 Interaction Flow

### Opening the Drawer
```
1. User clicks lead name
   ↓
2. openDrawer(leadId) called
   ↓
3. Fetch lead data from API
   ↓
4. Add 'open' class to overlay
   → Overlay fades in (0.25s)
   ↓
5. Add 'open' class to drawer
   → Drawer slides in (0.25s)
   ↓
6. Update header with lead info
   ↓
7. Render info tab content
   ↓
8. Drawer fully visible
```

### Switching Tabs
```
1. User clicks tab button
   ↓
2. switchDetailTab(tabName) called
   ↓
3. Remove 'active' class from old tab
   ↓
4. Add 'active' class to new tab
   → Tab indicator updates (underline)
   ↓
5. renderDetailTab(tabName) called
   ↓
6. Appropriate render function executes
   (renderInfo, renderActivity, renderOrders, or renderChat)
   ↓
7. New content displays in body
   ↓
8. Body scrolls to top
```

### Closing the Drawer
```
1. User clicks close button OR overlay
   ↓
2. closeDrawer() called
   ↓
3. Remove 'open' class from overlay
   → Overlay fades out (0.25s)
   ↓
4. Remove 'open' class from drawer
   → Drawer slides out (0.25s)
   ↓
5. Clear lead data
   ↓
6. Reset tab to 'info'
   ↓
7. Drawer fully hidden
```

### Changing Status
```
1. User selects status from dropdown
   ↓
2. detailPanelStatusChange(newStatus) called
   ↓
3. PATCH /leads/{id} with new status
   ↓
4. Update lead status class on dropdown
   → Color changes to match new status
   ↓
5. Call applyDetailPanelFooterState()
   → Show/hide buttons based on new status
   ↓
6. Footer updates immediately
```

---

## 🧪 Test Scenarios

### Test 1: Open Drawer
1. Click any lead name in table
2. ✅ Overlay should fade in (dark background)
3. ✅ Drawer should slide in from right
4. ✅ Animation should take exactly 0.25 seconds
5. ✅ Header should show correct lead data
6. ✅ Info tab should be active with content

### Test 2: Switch Tabs
1. With drawer open, click "📋 Activity" tab
2. ✅ Old tab should lose underline
3. ✅ Activity tab should gain blue underline
4. ✅ Content should change to activity timeline
5. ✅ Repeat for Orders and Chat tabs

### Test 3: Close Drawer
1. With drawer open, click close button (✕)
2. ✅ Drawer should slide out to right
3. ✅ Overlay should fade out
4. ✅ Animation should take exactly 0.25 seconds
5. ✅ Table should be fully visible again

### Test 4: Overlay Click
1. With drawer open, click on dark overlay area
2. ✅ Drawer should close (same as close button)
3. ✅ Overlay should disappear

### Test 5: Status Change
1. With drawer open, change status dropdown
2. ✅ Status should update in API
3. ✅ Dropdown color should reflect new status
4. ✅ Footer buttons should show/hide appropriately

### Test 6: Mobile Responsiveness
1. Open on mobile device (< 600px)
2. ✅ Drawer should appear full-width
3. ✅ All content should be readable
4. ✅ Tab buttons should be tappable
5. ✅ Scrolling should work smoothly

---

## ✨ Polish Details

- **Smooth animations** (not instant)
- **Clear focus state** (overlay helps)
- **Proper z-index** (drawer overlays everything)
- **GPU acceleration** (will-change:transform)
- **Responsive design** (works on all sizes)
- **Accessible** (proper button labels, semantic HTML)
- **Touch-friendly** (large button targets on mobile)
- **Professional appearance** (polished transitions)

---

**Status:** ✅ Ready for production  
**Last Updated:** February 23, 2026
