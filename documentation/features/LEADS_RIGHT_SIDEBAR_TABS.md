# ✅ Leads Page - Right-Side Tab Drawer

**Date:** February 23, 2026  
**Status:** ✅ **CONVERTED TO RIGHT-SIDE DRAWER WITH TABS**  
**Previous Design:** Tab panel below table  
**New Design:** Sliding drawer on right with 4 tabs inside

---

## 🎨 New Layout

```
┌─────────────────────────────────────────────────────────────┐
│                         TOPBAR                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  LEADS TABLE                        ┌────────────────────┐ │
│  ──────────────────────────────    │ Lead Details Panel │ │
│  Lead 1          Created        Phone    │ (Right side)    │ │
│  Lead 2 ← Click  contacted      Contact  │                │ │
│  Lead 3          Follow          data    │ ℹ️ Activity     │ │
│                                          │ 📋 Orders      │ │
│                          [Dark Overlay]  │ 📦 Chat        │ │
│                                          │                │ │
│                                          │ [Details here] │ │
│                                          │                │ │
│                                          │ [Buttons]      │ │
│                                          └────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📐 Drawer Specifications

### **Position & Dimensions**
- **Position:** Fixed on right side of screen
- **Width:** 500px
- **Height:** 100% (full viewport height)
- **Animation:** Slides in from right (transform: translateX(100%) → translateX(0))
- **Duration:** 0.25s with cubic-bezier easing
- **Z-index:** 300 (above all other content)

### **Overlay**
- **Position:** Fixed, full screen
- **Background:** Semi-transparent black (rgba(0,0,0,.4))
- **Opacity Animation:** 0 → 1 (0.25s)
- **Clickable:** Clicking closes the drawer
- **Z-index:** 299 (behind drawer, above content)

### **Layout Sections**
1. **Header** (20px padding, border-bottom)
   - Lead number (11px, uppercase, gray)
   - Lead name (18px, bold, black)
   - Phone number (13px, gray)
   - Close button (✕)
   - Status dropdown (full width)

2. **Tabs** (border-bottom, flex row)
   - ℹ️ Info
   - 📋 Activity
   - 📦 Orders
   - 💬 Chat
   - Tab buttons have underline active indicator (primary color)

3. **Body** (20px padding, scrollable)
   - Content area for selected tab
   - Flex: 1 (fills available space)
   - Max scrollable height

4. **Footer** (16px padding, border-top, flex row)
   - Action buttons
   - Conditional visibility based on lead status

---

## 🔧 CSS Classes

### **New CSS**
```css
.ov {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.4);
  z-index: 299;
  opacity: 0;
  transition: opacity .25s;
}

.ov.open {
  display: block;
  opacity: 1;
}

.detail-panel {
  position: fixed;
  right: 0;
  top: 0;
  width: 500px;
  height: 100vh;
  background: surface color;
  border-left: 1px solid outline-variant;
  display: flex;
  flex-direction: column;
  z-index: 300;
  transform: translateX(100%);  /* Hidden off-screen */
  transition: transform .25s cubic-bezier(.4,0,.2,1);
  overflow: hidden;
  will-change: transform;
}

.detail-panel.open {
  transform: translateX(0);  /* Slide in */
}

.dp-header {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 20px;
  border-bottom: 1px solid outline-variant;
  flex-shrink: 0;
}

.dp-tabs {
  display: flex;
  gap: 0;
  border-bottom: 1px solid outline-variant;
  flex-wrap: wrap;
}

.dp-tab {
  background: transparent;
  border: none;
  padding: 12px 16px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  color: on-surface-variant;
  border-bottom: 2px solid transparent;
  white-space: nowrap;
  transition: all .2s;
  flex: 1;
  text-align: center;
}

.dp-tab:hover {
  color: primary;
}

.dp-tab.active {
  color: primary;
  border-bottom-color: primary;
}

.dp-body {
  padding: 20px;
  flex: 1;
  overflow-y: auto;
}

.dp-footer {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  padding: 16px 20px;
  border-top: 1px solid outline-variant;
  flex-shrink: 0;
}
```

---

## 🎯 How It Works

### **1. Click a Lead Name**
```
Click lead → openDrawer(id) → Fetch lead data
```

### **2. Panel Slides In**
```
.detail-panel.open {
  transform: translateX(0);  ← Slides from right
}
```

### **3. Header Updates**
```
Lead Number: LEAD-00001
Lead Name: John Doe
Phone: +91 98765-43210
[✕ Close Button]
[Status Dropdown ▼]
```

### **4. Tabs Display Content**
```
[ℹ️ Info] [📋 Activity] [📦 Orders] [💬 Chat]
─────────────────────────────────────────────
(Active tab content displays here, scrolls if needed)
```

### **5. Footer Shows Buttons**
```
[🗑] [✏️ Edit] [➕ Note] [📦 Order] [📞 Contacted] [🏆 Won]
```

### **6. Close Panel**
```
Click close button OR click overlay → closeDrawer()
```

---

## ⚙️ JavaScript Functions

### **Core Functions**

**openDrawer(id)**
- Fetch lead data from API
- Show overlay (.ov.open)
- Show drawer (.detail-panel.open)
- Update header with lead info
- Render default tab (info)

**closeDrawer()**
- Hide overlay (.ov.open removed)
- Hide drawer (.detail-panel.open removed)
- Clear lead data

**switchDetailTab(t, el)**
- Update active tab class
- Call renderDetailTab()

**renderDetailTab(t)**
- Dispatch to correct render function
- renderInfo, renderActivity, renderOrders, renderChat

**updateDetailPanelHeader()**
- Set lead number, name, phone
- Set status dropdown value
- Apply status-specific footer button visibility

**applyDetailPanelFooterState()**
- Show/hide buttons based on lead status
- Order button: only if contacted
- Contacted button: hide if already contacted
- Won button: hide if done

**detailPanelStatusChange(ns)**
- Handle status dropdown changes
- Update lead status via API
- Trigger appropriate popups/modals

---

## 🎨 Visual Flow

### **Default State**
```
┌─ Drawer Hidden (100% off-screen right)
│  transform: translateX(100%)
│
└─ Overlay Hidden
   opacity: 0
```

### **Opening**
```
┌─ User clicks lead name
│
├─ API fetches lead data
│
├─ Overlay fades in (opacity: 0 → 1)
│
└─ Drawer slides in (translateX(100%) → 0)
   Takes 0.25s with smooth easing
```

### **Tab Switching**
```
User clicks tab
  ↓
Old tab loses .active class
New tab gains .active class
Content renders instantly
```

### **Closing**
```
User clicks overlay OR close button
  ↓
Drawer slides out (translateX(0) → 100%)
Overlay fades out (opacity: 1 → 0)
Takes 0.25s smooth animation
```

---

## 📊 State Transitions

| State | Display | Opacity | Transform | Overlay |
|-------|---------|---------|-----------|---------|
| **Closed** | hidden | 0 | translateX(100%) | hidden |
| **Opening** | visible | 0→1 | translateX(100%)→0 | visible |
| **Open** | visible | 1 | translateX(0) | visible |
| **Closing** | visible | 1→0 | translateX(0)→100% | hidden |

---

## ✅ Implementation Checklist

- [x] CSS for overlay (.ov)
- [x] CSS for drawer (.detail-panel)
- [x] CSS for tabs (.dp-tabs, .dp-tab)
- [x] CSS for header (.dp-header)
- [x] CSS for body (.dp-body)
- [x] CSS for footer (.dp-footer)
- [x] Overlay HTML element
- [x] Drawer HTML structure
- [x] Tab buttons with onclick handlers
- [x] Status dropdown
- [x] Footer buttons with correct IDs
- [x] openDrawer() function
- [x] closeDrawer() function
- [x] switchDetailTab() function
- [x] renderDetailTab() function
- [x] updateDetailPanelHeader() function
- [x] applyDetailPanelFooterState() function
- [x] detailPanelStatusChange() function
- [x] Animation timings (0.25s)
- [x] Z-index layering (overlay 299, drawer 300)
- [x] Overlay click closes drawer

---

## 🚀 Benefits of Right-Side Drawer

✅ **Classic Pattern**
- Proven mobile/web design pattern
- Users familiar with this UX

✅ **Better Screen Usage**
- Table remains fully visible and usable
- Can compare lead data while drawer open
- Responsive to mobile/tablet screens

✅ **Smooth Animation**
- Satisfying slide-in animation
- Professional appearance
- Clear open/close states

✅ **Flexible Content**
- Large content area (500px wide)
- Scrollable body for long content
- Organized sections (header/tabs/footer)

✅ **Modal Experience**
- Overlay focuses attention
- Clear intent to view lead details
- Prevents accidental actions

✅ **Works on All Devices**
- Desktop: Full-size drawer on right
- Tablet: Still appears on right
- Mobile: Becomes full-screen drawer

---

## 📱 Responsive Behavior

### **Desktop (> 900px)**
- Drawer: 500px fixed width on right
- Table: Full width on left
- Both visible simultaneously

### **Tablet (600-900px)**
- Drawer: 500px (may take 60-70% of screen)
- Table: Scrolls horizontally
- Both visible but tight

### **Mobile (< 600px)**
- Drawer: 100vw (full screen)
- Table: Below, not visible
- Overlay ensures focus

---

## 🎨 Color Scheme

- **Background:** Surface color (white/light)
- **Border:** Outline variant (gray)
- **Text:** On-surface (black/dark)
- **Tabs Active:** Primary color (blue)
- **Overlay:** Black with 40% opacity
- **Delete Button:** Red (#c5221f)
- **Order Button:** Green (#137333)
- **Won Button:** Primary color (blue)

---

## 🔌 API Integration

All existing API functions continue to work:
- `fetch(${API}/leads/${id})` - Get lead data
- `PATCH /leads/${id}` - Update status
- `POST /leads` - Create lead
- `DELETE /leads/${id}` - Delete lead

---

## 🎬 Animation Details

### **Drawer Slide-In**
```css
transform: translateX(100%) → translateX(0)
transition: transform .25s cubic-bezier(.4,0,.2,1)
```
- Easing: cubic-bezier(.4,0,.2,1) = smooth acceleration
- Duration: 250ms
- GPU accelerated with will-change:transform

### **Overlay Fade**
```css
opacity: 0 → 1
transition: opacity .25s
```
- Synchronized with drawer animation
- Creates elegant combined effect

---

## 🧪 Testing Checklist

- [ ] Click lead name → drawer slides in
- [ ] All 4 tabs switch content smoothly
- [ ] Status dropdown updates lead status
- [ ] Footer buttons show/hide correctly
- [ ] Close button works
- [ ] Overlay click closes drawer
- [ ] Lead data displays correctly in all tabs
- [ ] Edit/Delete/Note/Order modals open correctly
- [ ] Animation is smooth (60fps)
- [ ] Works on mobile/tablet
- [ ] No console errors
- [ ] Previous lead data clears on new selection

---

## 📝 Recent Changes

**From:** Tab panel below table  
**To:** Right-side sliding drawer with tabs inside

**CSS Changes:**
- Removed bottom placement styles
- Added fixed positioning (right: 0, top: 0)
- Added transform animation (translateX)
- Changed width to 500px
- Full height instead of limited height
- Added border-left instead of border-top

**HTML Changes:**
- Added overlay element (.ov)
- Restructured panel as fixed drawer
- Added close button
- Moved status dropdown to header
- Reordered sections (header→tabs→body→footer)

**JavaScript Changes:**
- Updated openDrawer() to use classList.add('open')
- Updated closeDrawer() to use classList.remove('open')
- Added overlay management
- Maintained all tab rendering functions

---

*Last Updated: February 23, 2026*  
*Design: Right-Side Drawer with Tabs*  
*Status: ✅ COMPLETE*
