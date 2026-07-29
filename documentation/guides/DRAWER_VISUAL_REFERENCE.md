# Lead Drawer - Visual Reference & Component Map

## 🎨 Drawer Layout

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ D-HEAD (Drawer Header)                                │ │
│  │                                                       │ │
│  │  LEAD-00123                                           │ │
│  │  John Doe (Lead Name)                                 │ │
│  │  +91 98765-43210  [📞] [💬]  [Status: New ▼]         │ │
│  │                                                       │ │
│  │  D-TABS (Tab Navigation)                              │ │
│  │  [Info] [Activity] [Orders] [💬 Chat]                │ │
│  │  ═══════════════════════════════════════════         │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ D-BODY (Content Area - Scrollable)                    │ │
│  │                                                       │ │
│  │  [Content changes based on selected tab]             │ │
│  │                                                       │ │
│  │  Info Tab Shows:                                      │ │
│  │  ──────────────                                       │ │
│  │  CONTACT                                              │ │
│  │  Name: John Doe                                       │ │
│  │  Phone: +91 98765-43210  [📞] [💬]                   │ │
│  │  Email: john@example.com                              │ │
│  │  ...more fields...                                    │ │
│  │                                                       │ │
│  │  LEAD DETAILS                                         │ │
│  │  Product: Black Pepper 500g                           │ │
│  │  Source: [WhatsApp]                                   │ │
│  │  ...more fields...                                    │ │
│  │                                                       │ │
│  │  (Activity/Orders/Chat tabs show different content)   │ │
│  │                                                       │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ D-FOOT (Footer with Action Buttons)                   │ │
│  │                                                       │ │
│  │  [🗑] [✏ Edit] [＋ Note] [📦 Order] [📞 Contacted]   │ │
│  │                            [🏆 Won]                   │ │
│  │                                                       │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  CONTACTED OUTCOME BANNER (shown when status=contacted)   │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ ✅ Contacted — Choose outcome                        │ │
│  │ [📦 Create Order] [⏰ Remind Later] [🚫 Mark Lost]  │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘

OVERLAY (OV)
─────────────────────────────────────────────────────────────
Semi-transparent dark background (rgba(0,0,0,.32))
Covers entire viewport behind drawer
Click to close drawer
```

---

## 📐 CSS Component Structure

```
HTML DOM Tree:
───────────────────────────────────────────────────────────

#app (Flex container)
├── .topbar
├── .page-content (Flex grow)
└── .ov (Overlay - position fixed)
    └── .drawer (Drawer panel - position fixed right)
        ├── .d-head (Header)
        │   ├── dNum (Lead number)
        │   ├── dName (Lead name)
        │   ├── dPhone (Lead phone)
        │   ├── dStatusSel (Status dropdown)
        │   └── .d-tabs (Tab buttons)
        │       ├── .d-tab (Info tab)
        │       ├── .d-tab (Activity tab)
        │       ├── .d-tab (Orders tab)
        │       └── .d-tab (Chat tab)
        ├── .d-body (Content area - scrollable)
        │   └── [Dynamic content based on tab]
        ├── .d-foot (Footer buttons)
        │   ├── Delete button
        │   ├── Edit button
        │   ├── Note button
        │   ├── Order button (conditional)
        │   ├── Contacted button (conditional)
        │   └── Won button (conditional)
        └── #contactedOutcomeBanner (Conditional)
            ├── Create Order button
            ├── Remind Later button
            └── Mark Lost button
```

---

## 🎨 Visual Component Sizes

### Drawer Dimensions
```
Width:     500px (or 100vw on mobile)
Height:    100% (Full viewport)
Position:  Fixed, right: 0, top: 0
Shadow:    Elevation 4 (Material Design)
Animation: 0.25s cubic-bezier(.4,0,.2,1)
```

### Header Section
```
d-head:        Padding 24px 28px
d-head:        Border-bottom: 1px solid outline-variant
dNum:          Font: 11px bold uppercase, color: outline
dName:         Font: 19px bold, color: on-surface
dPhone:        Font: 13px, color: on-surface-variant
dStatusSel:    Font: 12px, padding: 4px 12px
d-tabs:        Margin-top: 14px
d-tab:         Padding: 10px 18px, font: 13px 600
d-tab.active:  Border-bottom: 2px primary, color: primary
```

### Body Section
```
d-body:        Flex: 1, overflow-y: auto
d-body:        Padding: 24px 28px
Content:       Font: 13px, line-height: 1.5
sh (header):   Font: 12px bold uppercase, margin: 16px 0 10px
kv (grid):     grid-template-columns: 140px 1fr, gap: 8px 12px
```

### Footer Section
```
d-foot:        Padding: 14px 24px
d-foot:        Border-top: 1px solid outline-variant
d-foot:        Display: flex, gap: 8px, flex-wrap: wrap
Button:        Font: 12px, padding: 6px 12px
Button colors: Default (gray), Red (delete), Green (order), Blue (primary)
```

---

## 🎨 Color System

### Surfaces
```
.drawer background:     var(--md-sys-color-surface)
                       Light background color
d-head border:         var(--md-sys-color-outline-variant)
                       Light gray border
```

### Text Colors
```
Primary text:          var(--md-sys-color-on-surface)
                       Dark (for main content)
Secondary text:        var(--md-sys-color-on-surface-variant)
                       Gray (for labels)
Outline:               var(--md-sys-color-outline)
                       Lighter gray (for subtle text)
```

### Active States
```
Active tab text:       var(--md-sys-color-primary)
                       Blue
Active tab border:     var(--md-sys-color-primary)
                       Blue underline
Selected row:          var(--md-sys-color-primary-container)
                       Light blue background
```

### Status Colors
```
New Lead:              Light gray
Contacted:            Blue (#1976d2)
Remind Later:         Orange (#e65100)
Won:                  Green (#137333)
Lost:                 Red (#c5221f)
Overdue:              Red (#c5221f)
Draft:                Gray (#80868b)
Delivered:            Blue (#1a73e8)
```

---

## 📱 Responsive Behavior

### Desktop (> 900px)
```
┌─────────────────────────────────────────────────────┐
│              TABLE (full width)                     │
│                                                     │
│ ┌──────────────────────────────────────────────────┐│
│ │ Lead 1                                           ││
│ │ Lead 2                                           ││
│ │ Lead 3 ←────────────────────────┐                ││
│ └──────────────────────────────────┼────────────────┘│
│                                    │                 │
│                            ┌───────▼────────────┐    │
│                            │   DRAWER (500px)   │    │
│                            │   Info | Activity  │    │
│                            │ ┌──────────────┐   │    │
│                            │ │ Lead Details │   │    │
│                            │ │ ...          │   │    │
│                            │ └──────────────┘   │    │
│                            └────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

### Tablet (600px - 900px)
```
Drawer width: 500px or 80vw (whichever is smaller)
Table adjusts to available space
Drawer may overlap slightly
```

### Mobile (< 600px)
```
┌───────────────────┐
│     TABLE         │
│                   │
│ Lead 1            │
│ Lead 2            │
│ Lead 3            │
│                   │
└───────────────────┘
        │
        │ (drawer overlays full screen)
        │
     ┌──▼──────────┐
     │  DRAWER     │
     │ (full width)│
     │             │
     │ Info|Act..  │
     │             │
     │ [Content]   │
     │             │
     │ [Buttons]   │
     │             │
     └─────────────┘
```

---

## 🎬 Animation States

### Drawer State Flow

```
START (Closed)
─────────────
.drawer {
  transform: translateX(100%)    ← Off-screen right
  display: flex
}

.ov {
  display: none
}


OPENING (Animation)
──────────────────
User clicks lead
  ↓
openDrawer(id)
  ├─ Add class .open to drawer
  ├─ Add class .open to overlay
  ├─ Start animation

.drawer.open {
  transform: translateX(0)       ← Animate in
  transition: .25s ease          ← Smooth animation
}

.ov.open {
  display: block                 ← Overlay appears
}


OPEN (Complete)
───────────────
.drawer.open {
  transform: translateX(0)       ← Fully visible
}

.ov.open {
  display: block                 ← Overlay visible
}

Content shows with proper tab rendering


CLOSING (Animation)
──────────────────
User clicks overlay or closes modal
  ↓
closeDrawer()
  ├─ Remove class .open from drawer
  ├─ Remove class .open from overlay
  ├─ Start reverse animation

.drawer {
  transform: translateX(100%)    ← Animate out
  transition: .25s ease          ← Smooth animation
}

.ov {
  display: none                  ← Overlay disappears
}


END (Closed)
────────────
.drawer {
  transform: translateX(100%)    ← Off-screen right
}

.ov {
  display: none
}
```

---

## 📋 Tab Content Structure

### Info Tab Content
```
┌─ Contact Section ─────────────────┐
│ Name                              │
│ Phone [📞] [💬]                   │
│ Alternate Phone                   │
│ Email                             │
│ Company                           │
└───────────────────────────────────┘

┌─ Lead Details Section ────────────┐
│ Product Interest                  │
│ Source [Badge]                    │
│ City / State                      │
│ Created Date                      │
│ Follow-up Date [Overdue]          │
│ Remind On [⏰ Date]               │
│ Last Contact [2h ago]             │
│ Times Called [3]                  │
└───────────────────────────────────┘

┌─ WABIS Labels Section ────────────┐
│ [Premium] [Hot] [✎ Edit]          │
└───────────────────────────────────┘

┌─ Last Note Section ───────────────┐
│ "Customer requested sample..."    │
└───────────────────────────────────┘

┌─ Notes Section ───────────────────┐
│ "Full notes from lead data..."    │
└───────────────────────────────────┘

[＋ Log Call / Note Button]
```

### Activity Tab Content
```
[＋ Log Activity Button]

┌─ Activity Timeline ───────────────┐
│ [📞] Call                         │
│      Discussed pricing            │
│      2 hours ago                  │
├───────────────────────────────────┤
│ [📝] Note                         │
│      Waiting for quote            │
│      1 day ago                    │
├───────────────────────────────────┤
│ [🔄] Status Change                │
│      new_lead → contacted         │
│      3 days ago                   │
├───────────────────────────────────┤
│ [📞] Call                         │
│      First contact                │
│      1 week ago                   │
└───────────────────────────────────┘
```

### Orders Tab Content
```
┌─ Order 1 ────────────────────────┐
│ ORD-20260220-001                 │
│ Feb 20, 2026 · Cash              │
│ ₹4,500.00                        │
│ Status: [Confirmed]              │
└───────────────────────────────────┘

┌─ Order 2 ────────────────────────┐
│ ORD-20260215-003                 │
│ Feb 15, 2026 · Card              │
│ ₹8,750.00                        │
│ Status: [Delivered]              │
└───────────────────────────────────┘
```

### Chat Tab Content
```
┌─ Chat Messages ───────────────────┐
│                                   │
│         Hello! I'm interested     │
│         in bulk orders            │
│                        2h ago     │
│                                   │
│                      Sure! Send   │
│                    us your req.   │
│                         1h ago    │
│                                   │
└───────────────────────────────────┘

[Input Box] [Send Button]
```

---

## 🔘 Button States & Visibility

### Footer Buttons

```
Button: 🗑 Delete
├─ Visibility: Always shown
├─ Color: Red (#c5221f)
└─ Opacity: Full

Button: ✏ Edit
├─ Visibility: Always shown
├─ Color: Default (gray)
└─ Opacity: Full

Button: ＋ Note
├─ Visibility: Always shown
├─ Color: Default (gray)
└─ Opacity: Full

Button: 📦 Order
├─ Visibility: ONLY when status = 'contacted'
├─ Color: Green (#137333)
├─ Background: Light green
└─ Opacity: Full

Button: 📞 Contacted
├─ Visibility: ONLY when status != 'contacted' AND not done (won/lost)
├─ Color: Secondary blue
└─ Opacity: Full

Button: 🏆 Won
├─ Visibility: HIDDEN when status = 'success_won' or 'lost_lead'
├─ Color: Primary blue
└─ Opacity: Full
```

### Outcome Banner

```
Display: ONLY when status = 'contacted'

Button: 📦 Create Order
├─ Action: Opens order creation drawer
└─ Color: Green

Button: ⏰ Remind Later
├─ Action: Opens modal to set reminder date
└─ Color: Orange

Button: 🚫 Mark Lost
├─ Action: Marks lead as lost
└─ Color: Red
```

---

## 🎯 Interaction States

### Status Dropdown States

```
STATUS: new_lead
├─ Label: "New Lead"
├─ Footer: [Contacted btn] visible
├─ Footer: [Won btn] visible
├─ Footer: [Order btn] hidden
├─ Banner: hidden
└─ Row: default

STATUS: contacted
├─ Label: "📞 Contacted"
├─ Footer: [Contacted btn] hidden
├─ Footer: [Won btn] visible
├─ Footer: [Order btn] visible
├─ Banner: visible (choose outcome)
└─ Row: highlighted if same lead

STATUS: remind_later
├─ Label: "Remind Later"
├─ Footer: [Contacted btn] hidden
├─ Footer: [Won btn] visible
├─ Footer: [Order btn] hidden
├─ Banner: hidden
└─ Row: default

STATUS: success_won
├─ Label: "Won ✓"
├─ Footer: [Contacted btn] hidden
├─ Footer: [Won btn] hidden
├─ Footer: [Order btn] hidden
├─ Banner: hidden
└─ Row: default

STATUS: lost_lead
├─ Label: "Lost"
├─ Footer: [Contacted btn] hidden
├─ Footer: [Won btn] hidden
├─ Footer: [Order btn] hidden
├─ Banner: hidden
└─ Row: default
```

---

## 💾 Data Persistence

### Lead Object Properties
```
Lead {
  id: "string"
  lead_number: "LEAD-00001"
  name: "John Doe"
  phone: "+91 9876543210"
  alternate_phone: "+91 8765432109"
  email: "john@example.com"
  company_name: "ABC Corp"
  
  product_interest: "Black Pepper 500g"
  source: "whatsapp"
  city: "Bangalore"
  state: "Karnataka"
  
  status: "new_lead|contacted|remind_later|success_won|lost_lead|created"
  created_at: "2026-02-20T10:30:00Z"
  next_followup_date: "2026-02-25"
  last_contacted_at: "2026-02-23T14:00:00Z"
  contacted_count: 3
  
  notes: "Customer notes text"
  note_last: "Last note text"
  
  remind_later_date: "2026-02-28"
  
  activities: [{
    id: "string"
    activity_type: "call|note|status_change|whatsapp"
    note: "text"
    created_at: "timestamp"
    old_status: "previous"
    new_status: "new"
  }]
  
  wabis_labels: ["Premium", "Hot Lead"]
  
  converted_customer_id: "uuid|null"
}
```

---

## 🔗 Event Flow

### Open Drawer Flow
```
User clicks lead name
    ↓
onclick="openDrawer(leadId)"
    ↓
Fetch /api/leads/{leadId}
    ↓
lead = response.json()
    ↓
applyDHead() ← Update header
    ↓
renderTab('info') ← Render Info tab
    ↓
Add .open to drawer ← Start animation
    ↓
Add .open to overlay
    ↓
Drawer slides in (.25s)
    ↓
Add row-active to table row
    ↓
Display complete!
```

### Switch Tab Flow
```
User clicks tab button
    ↓
onclick="switchTab('tabName', this)"
    ↓
tab = 'tabName'
    ↓
Remove .active from all tabs
    ↓
Add .active to clicked tab
    ↓
renderTab('tabName')
    ↓
Call appropriate render function:
  - renderInfo()
  - renderActivity()
  - renderOrders()
  - renderChat()
    ↓
Update d-body innerHTML
    ↓
Tab content displays!
```

### Close Drawer Flow
```
User clicks overlay OR closes modal
    ↓
onclick="closeDrawer()"
    ↓
Remove .open from drawer
    ↓
Remove .open from overlay
    ↓
lead = null
    ↓
Drawer slides out (.25s)
    ↓
Overlay disappears
    ↓
Remove row-active from all rows
    ↓
Drawer fully closed!
```

---

*Last Updated: February 23, 2026*  
*Reference Version: 1.0*  
*Status: ✅ Complete*
