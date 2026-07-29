# Option 4 Visual Reference & User Guide

## UI Overview

### Collapsed View (Default)
```
┌──────────────────────────────────────────────────────────────────────────────┐
│ LEADS                                                                    [+] New │
├──────────────────────────────────────────────────────────────────────────────┤
│ ⚪ 100  ⚪ 200  ⚪ 300  ⚪ 400  ⚪ 500  ⚪ Won  ⚪ Lost  ⚫ Overdue              │
├──────────────────────────────────────────────────────────────────────────────┤
│ 🔍 Search... │ [All Status ▼] │ [All Sources ▼]                             │
├───┬────────┬──────────────────┬──────────────────┬────────┬───────┬────┬────┤
│ ▼ │Lead # │ Name & Phone     │ Product Interest │ Status │Follow-│Src │Act │
├───┼────────┼──────────────────┼──────────────────┼────────┼───────┼────┼────┤
│▼  │L-0001 │ Alice Johnson    │ Product A        │ New    │ —     │ WA │📞💬│
│   │2h ago │ +1-555-0123      │ Cairo, Egypt     │ [▼]    │        │    │    │
├───┼────────┼──────────────────┼──────────────────┼────────┼───────┼────┼────┤
│►  │L-0002 │ Bob Smith        │ Product B        │ Won ✓  │ —     │Manual│📞💬│
│   │4h ago │ +1-555-0456      │ Alexandria, EGY  │ [▼]    │        │    │    │
├───┼────────┼──────────────────┼──────────────────┼────────┼───────┼────┼────┤
│►  │L-0003 │ Carol Davis      │ Product C        │ Contact│ 2d    │Meta │📞💬│
│   │1d ago │ +1-555-0789      │ Giza, Egypt      │ [▼]    │        │    │    │
├───┴────────┴──────────────────┴──────────────────┴────────┴───────┴────┴────┤
│ ◀ Prev │ Page 1 of 5 │ Next ▶                                                │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Expanded View (First Row)
```
┌──────────────────────────────────────────────────────────────────────────────┐
│ LEADS                                                                    [+] New │
├──────────────────────────────────────────────────────────────────────────────┤
│ ⚪ 100  ⚪ 200  ⚪ 300  ⚪ 400  ⚪ 500  ⚪ Won  ⚪ Lost  ⚫ Overdue              │
├──────────────────────────────────────────────────────────────────────────────┤
│ 🔍 Search... │ [All Status ▼] │ [All Sources ▼]                             │
├───┬────────┬──────────────────┬──────────────────┬────────┬───────┬────┬────┤
│ ▼ │Lead # │ Name & Phone     │ Product Interest │ Status │Follow-│Src │Act │
├───┼────────┼──────────────────┼──────────────────┼────────┼───────┼────┼────┤
│▼  │L-0001 │ Alice Johnson    │ Product A        │ New    │ —     │ WA │📞💬│ ← Row 1
│   │2h ago │ +1-555-0123      │ Cairo, Egypt     │ [▼]    │        │    │    │
├───┼────────┴──────────────────┴──────────────────┴────────┴───────┴────┴────┤
│   │ EXPANDED ACCORDION SECTION                                              │
│   ├──────────────────┬──────────────────────────┬──────────────────────────┤
│   │ LEAD INFO        │ DETAILS CONTENT          │ ACTIONS                  │
│   │                  │ [ℹ️ Info 📋 Activity... │                          │
│   │ Lead Info        │                          │ 🗑 Delete                │
│   │ Alice Johnson    │ Lead Details:            │                          │
│   │ +1-555-0123      │ • Email: alice@abc.com   │ ✏️ Edit                  │
│   │ alice@abc.com    │ • Created: 2d ago        │                          │
│   │                  │ • Notes: Interested      │ ➕ Note                  │
│   │ [New Lead ▼]     │   in product delivery   │                          │
│   │                  │                          │ 📦 Order                 │
│   │                  │ Activity Summary:        │                          │
│   │                  │ • Last contact: 4h ago   │ 📞 Contacted             │
│   │                  │ • Next follow-up: 2d    │                          │
│   │                  │ • Status history visible │ 🏆 Won                   │
│   │                  │   (scroll for more)      │                          │
│   └──────────────────┴──────────────────────────┴──────────────────────────┘
├───┼────────┼──────────────────┼──────────────────┼────────┼───────┼────┼────┤
│►  │L-0002 │ Bob Smith        │ Product B        │ Won ✓  │ —     │Manual│📞💬│ ← Row 2 (collapsed)
│   │4h ago │ +1-555-0456      │ Alexandria, EGY  │ [▼]    │        │    │    │
├───┼────────┼──────────────────┼──────────────────┼────────┼───────┼────┼────┤
│►  │L-0003 │ Carol Davis      │ Product C        │ Contact│ 2d    │Meta │📞💬│ ← Row 3 (collapsed)
│   │1d ago │ +1-555-0789      │ Giza, Egypt      │ [▼]    │        │    │    │
├───┴────────┴──────────────────┴──────────────────┴────────┴───────┴────┴────┤
│ ◀ Prev │ Page 1 of 5 │ Next ▶                                                │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Detailed Layout: Expanded Row

### Structure
```
┌─ 40px ─┬─ Remaining Space (9 columns) ─────────────────────────────────────┐
│        │                                                                      │
│ [▼]    │ L-0001 │ Alice │ Product A │ New │ — │ WA │ Labels │ 📞💬      │
│        │        │ +555  │ Cairo      │ [▼] │   │    │        │           │
└────────┴────────┴───────┴────────────┴─────┴───┴────┴────────┴───────────┘
        ↓
        Expand Row (Accordion)
        
┌────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│ ┌───── Left Panel (400px) ──────┬─ Middle Panel (flex-1) ─┬ Right ────────┐
│ │                               │                         │ Panel  (140px) │
│ │  LEAD INFO                    │  DETAILS (Scrollable)   │                │
│ │                               │ Max-height: 300px       │ 🗑 Delete      │
│ │  Lead Info                    │                         │                │
│ │  ─────────────────────        │ [ℹ️][📋][📦][💬]       │ ✏️ Edit        │
│ │                               │                         │                │
│ │  Alice Johnson                │ LEAD DETAILS            │ ➕ Note        │
│ │  +1-555-0123                  │ ──────────────────      │                │
│ │  alice@abc.com                │                         │ 📦 Order       │
│ │                               │ Email: alice@abc.com    │                │
│ │  [New Lead ▼]                 │ Phone: +1-555-0123      │ 📞 Contacted   │
│ │                               │ Source: WhatsApp        │                │
│ │                               │ Created: 2 days ago     │ 🏆 Won         │
│ │                               │ Last Contact: 4h ago    │                │
│ │                               │ Next Follow-up: 2d      │                │
│ │                               │                         │                │
│ │                               │ (Scroll for more) ↓     │                │
│ │                               │                         │                │
│ └───────────────────────────────┴─────────────────────────┴────────────────┘
│
└────────────────────────────────────────────────────────────────────────────┘
```

### Three Panel System

#### Left Panel (400px Fixed)
- **Lead Number Label** - Uppercase "LEAD INFO"
- **Lead Name** - Large, bold text
- **Phone** - Contact number
- **Email** - Email address
- **Status Selector** - Dropdown to change status
- Compact, left-aligned layout
- Static, no scrolling

#### Middle Panel (Flexible)
- **Tab Navigation** - 4 tabs (Info, Activity, Orders, Chat)
- **Content Area** - Dynamic content based on selected tab
- **Scrollable** - max-height: 300px, overflow-y: auto
- Shows current tab content
- Reuses existing render functions

#### Right Panel (140px Fixed)
- **Action Buttons** (vertical stack)
  - 🗑 Delete (red)
  - ✏️ Edit
  - ➕ Note
  - 📦 Order (green background)
  - 📞 Contacted (secondary)
  - 🏆 Won (primary)
- Each button opens relevant modal
- Vertical spacing: 8px between buttons

---

## User Interactions

### Opening an Accordion

**User Action:** Click expand button (▼) or lead name

```
1. Click Event
   └─ toggleExpandRow('123')
   
2. Close Other Rows
   └─ Remove .open from any other .expand-row elements
   
3. Toggle Current Row
   └─ Add .open class to expand-row
   
4. Animate Expansion
   └─ max-height: 0 → 800px (0.3s)
   └─ Smooth slide-down animation
   
5. Fetch Data
   └─ API call: GET /leads/123
   └─ lead = await response.json()
   
6. Render Content
   └─ renderDetailTab('info')
   └─ Insert into expand-content-123
   
7. Ready for Interaction
   └─ All buttons functional
   └─ Tabs clickable
   └─ Status selector works
```

### Viewing Different Content

**User Action:** Click tab inside expanded row

```
1. Click Tab
   └─ switchDetailTab('activity')
   
2. Update Tab Styling
   └─ Add .active to clicked tab
   └─ Remove .active from others
   
3. Render New Content
   └─ renderDetailTab('activity')
   └─ Display activity timeline
   
4. Update Display
   └─ Insert into expand-content-ID
   └─ Automatic scroll reset
```

### Closing Accordion

**User Action 1:** Click expand button again (toggle)
```
1. Click Event
   └─ toggleExpandRow('123')
   
2. Remove .open Class
   └─ Remove .open from expand-row
   
3. Animate Collapse
   └─ max-height: 800px → 0 (0.3s)
   └─ Smooth slide-up animation
   
4. Cleanup
   └─ closeDrawer() called
   └─ lead = null
   └─ tab = 'info'
```

**User Action 2:** Click different row's expand button
```
1. Click Event
   └─ toggleExpandRow('456')
   
2. Close Previous
   └─ Remove .open from expand-123
   └─ Remove .open from expand-456 (if was open)
   
3. Open New
   └─ Add .open to expand-456
   └─ Animate expansion
   
4. Fetch New Lead
   └─ API call: GET /leads/456
   └─ Render new details
```

---

## Comparison Scenarios

### Scenario 1: Comparing Two Leads

Without modification (current):
1. Open Lead A (expand-A opens)
2. View Lead A details
3. Click Lead B expand button (expand-A closes, expand-B opens)
4. View Lead B details

Optional modification (allow multiple):
1. Open Lead A (expand-A opens)
2. View Lead A details
3. Click Lead B expand button (expand-B opens, expand-A stays open)
4. Scroll to compare both simultaneously

### Scenario 2: Quick Actions

1. Scan table for lead
2. Click expand button
3. View details
4. Click "Contacted" button
5. Modal opens, record action
6. Return to expanded row
7. Status updates in real-time

### Scenario 3: Following Up

1. Open lead with follow-up due today
2. Expand row
3. View activity and notes
4. Click "Note" to add follow-up note
5. Click "Contacted" to record interaction
6. Status updates

---

## Animation Sequence

### Expansion Animation (0-300ms)

```
Time:  0ms   100ms   200ms   300ms
Max:   0px   200px   600px   800px
       ▂      ▆       ▊       █

Visual Effect: Smooth slide-down with easing
Easing: cubic-bezier(.4, 0, .2, 1) - Material Design "enter"

Frame 0: Accordion hidden (max-height:0)
Frame 1: Content appearing (max-height:200px)
Frame 2: Almost fully visible (max-height:600px)
Frame 3: Fully expanded (max-height:800px)
```

### Collapse Animation (300-600ms)

```
Time:  300ms  400ms   500ms   600ms
Max:   800px  600px   200px   0px
       █       ▊       ▆       ▂

Visual Effect: Smooth slide-up with easing
Direction: Reverse of expansion
```

---

## Mobile Responsiveness

### On Portrait Mobile (< 768px)

```
Expanded View (Mobile):

┌────────────────────────────────┐
│ [▼] L-001 │ Alice │ Product   │
│    2h ago │ +555  │ Cairo     │
├────────────────────────────────┤
│ EXPANDED CONTENT (Full Width)  │
│ ┌──────────────────────────────┐
│ │ LEAD INFO                    │
│ │ Alice Johnson                │
│ │ +1-555-0123                  │
│ │ alice@abc.com                │
│ │ [New Lead ▼]                 │
│ └──────────────────────────────┘
│ ┌──────────────────────────────┐
│ │ [ℹ️][📋][📦][💬]              │
│ │                              │
│ │ Lead Details                 │
│ │ • Email: alice@abc.com       │
│ │ • Created: 2d ago            │
│ │ • Source: WhatsApp           │
│ │                              │
│ │ (Scroll for more)            │
│ └──────────────────────────────┘
│ ┌──────────────────────────────┐
│ │ 🗑 Delete  ✏️ Edit           │
│ │ ➕ Note    📦 Order          │
│ │ 📞 Contacted  🏆 Won         │
│ └──────────────────────────────┘
└────────────────────────────────┘
```

### Responsive Changes Needed (CSS)
```css
@media (max-width: 768px) {
  .expand-row > td > div {
    flex-direction: column;
    gap: 12px;
  }
  
  .expand-row > td > div > div {
    flex: none;
    width: 100%;
  }
}
```

---

## Keyboard Navigation (Optional Enhancement)

Potential additions:
- **Arrow Up/Down** - Navigate between rows
- **Space/Enter** - Toggle expand/collapse
- **Tab** - Move between expandable elements within row
- **Escape** - Close expanded row
- **Ctrl+Click** - Toggle multiple rows (if allowing multiple)

---

## Accessibility Considerations

### Current
- Expand button is keyboard accessible
- Status selector keyboard accessible
- Action buttons keyboard accessible
- All text visible (no hidden content)

### Recommended Enhancements
- Add `aria-expanded` to expand button
- Use `role="region"` for expanded content
- Add `aria-label` to accordion sections
- Ensure sufficient color contrast
- Support keyboard navigation within expanded row

---

## Performance Tips

### For Large Lists
- Lazy load expanded content only when opened
- Limit expanded row height to prevent DOM thrashing
- Use CSS animation (not JavaScript)
- Debounce resize events if any

### For Mobile
- Consider virtual scrolling for 1000+ leads
- Reduce animation duration on slower devices
- Lazy load images in details
- Optimize API calls

---

## Troubleshooting

### Issue: Expanded Row Not Showing
- Check `.expand-row` has correct ID format: `expand-{leadId}`
- Verify CSS `.expand-row.open { display:table-row; }`
- Check browser console for JavaScript errors
- Verify API call succeeded

### Issue: Animation Not Smooth
- Check if `transition` CSS is applied
- Verify `cubic-bezier` timing function
- Check for JavaScript animations interfering
- Check browser hardware acceleration

### Issue: Multiple Rows Won't Stay Open
- This is by design (accordion behavior)
- To allow multiple: Remove accordion close logic
- Or add toggle modifier key (Ctrl+Click to open multiple)

### Issue: Content Not Appearing in Expanded Row
- Check API response contains expected data
- Verify `renderDetailTab()` function works
- Check `expand-content-{id}` exists in DOM
- Verify JavaScript no errors in console

---

## Design Notes

### Why This Layout Works

✅ **Compact Default** - Table headers only visible when collapsed
✅ **Progressive Disclosure** - Details appear on demand
✅ **Context Preserved** - Always see full lead list
✅ **Natural Scrolling** - Expands downward naturally on mobile
✅ **Comparison Ready** - Can open multiple rows (with modification)
✅ **Animation Satisfying** - Smooth 0.3s accordion effect

### UI Psychology

- **Expand Button**: Clear affordance that row is interactive
- **Animation**: Helps user understand state change (collapsing/expanding)
- **3-Panel Layout**: Familiar mental model (info-content-actions)
- **Tab Navigation**: Efficient way to explore detail types
- **Action Buttons**: Easy to find and use common workflows

---

## Next Steps & Customization

### To Allow Multiple Rows Open
```javascript
function toggleExpandRow(id){
  const row = document.getElementById(`expand-${id}`);
  if(!row) return;
  
  // Remove this block to allow multiple:
  // document.querySelectorAll('.expand-row.open').forEach(r => {
  //   if(r.id !== `expand-${id}`) r.classList.remove('open');
  // });
  
  row.classList.toggle('open');
  if(row.classList.contains('open')){
    openDrawer(id);
  }
}
```

### To Add Click-Outside to Close
```javascript
document.addEventListener('click', (e) => {
  if(!e.target.closest('.expand-row') && 
     !e.target.closest('button[onclick*="toggleExpand"]')) {
    closeDrawer();
  }
});
```

### To Add Keyboard Support
```javascript
document.addEventListener('keydown', (e) => {
  if(e.key === 'Escape') closeDrawer();
  if(e.key === 'ArrowDown') selectNextLead();
  if(e.key === 'ArrowUp') selectPrevLead();
});
```

---

**Status:** ✅ READY FOR TESTING

This design pattern is production-ready and can be further customized based on user feedback and specific requirements.
