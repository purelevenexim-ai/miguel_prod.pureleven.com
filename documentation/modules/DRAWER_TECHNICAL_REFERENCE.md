# Lead Drawer - Complete Technical Reference

## 📋 Table of Contents
1. [HTML Structure](#html-structure)
2. [CSS Styling](#css-styling)
3. [JavaScript Functions](#javascript-functions)
4. [API Endpoints](#api-endpoints)
5. [Drawer Content Details](#drawer-content-details)
6. [State Management](#state-management)

---

## HTML Structure

### Overlay Element
```html
<!-- Semi-transparent backdrop, click to close drawer -->
<div class="ov" id="dOv" onclick="closeDrawer()"></div>
```

**Properties:**
- `position: fixed` - Covers entire viewport
- `inset: 0` - Stretches to all edges
- `background: rgba(0,0,0,.32)` - Dark semi-transparent
- `z-index: 200` - Behind drawer
- `display: none` (default) / `display: block` (when `.open` class added)

---

### Drawer Container
```html
<div class="drawer" id="drawer">
  <!-- Header with lead info and tabs -->
  <div class="d-head" id="dHead">
    <!-- Header content -->
  </div>
  
  <!-- Scrollable content area -->
  <div class="d-body" id="dBody">
    <!-- Info, Activity, Orders, or Chat content -->
  </div>
  
  <!-- Action buttons footer -->
  <div class="d-foot">
    <!-- Footer buttons -->
  </div>
  
  <!-- Special banner for contacted leads -->
  <div id="contactedOutcomeBanner">
    <!-- Outcome selection buttons -->
  </div>
</div>
```

**Properties:**
- `position: fixed` - Floats above all content
- `right: 0` - Positioned at right edge
- `width: 500px` - Standard drawer width
- `max-width: 100vw` - Responsive on mobile
- `height: 100%` - Full viewport height
- `z-index: 201` - Above overlay, below modals
- `display: flex` - Vertical flex layout
- `flex-direction: column` - Stack sections vertically

---

### Drawer Header
```html
<div class="d-head" id="dHead" style="display:none;">
  <div style="...">
    <!-- Lead number (LEAD-00001) -->
    <div id="dNum" style="...">—</div>
    
    <!-- Lead name (large) -->
    <div id="dName" style="...">—</div>
    
    <!-- Phone with action buttons -->
    <div id="dPhone" style="...">—</div>
    
    <!-- Status dropdown -->
    <select class="st-sel" id="dStatusSel" onchange="drawerStatusChange(this.value)">
      <option value="created">Created (via Order)</option>
      <option value="new_lead">New Lead</option>
      <option value="contacted">📞 Contacted</option>
      <option value="remind_later">Remind Later</option>
      <option value="success_won">Won ✓</option>
      <option value="lost_lead">Lost</option>
    </select>
  </div>
  
  <!-- Tab buttons -->
  <div class="d-tabs">
    <div class="d-tab active" onclick="switchTab('info',this)">Info</div>
    <div class="d-tab" onclick="switchTab('activity',this)">Activity</div>
    <div class="d-tab" onclick="switchTab('orders',this)">Orders</div>
    <div class="d-tab" onclick="switchTab('chat',this)">💬 Chat</div>
  </div>
</div>
```

---

### Drawer Content Area
```html
<div class="d-body" id="dBody">
  <!-- Dynamic content inserted by renderTab() -->
  <!-- Shows Info, Activity, Orders, or Chat content -->
</div>
```

**Behavior:**
- `flex: 1` - Takes remaining space
- `overflow-y: auto` - Scrollable if content exceeds height
- Content changes when switching tabs
- Different rendering function for each tab

---

### Drawer Footer
```html
<div class="d-foot" style="display:none;">
  <!-- Delete button (always red) -->
  <button class="btn btn-ghost btn-sm" style="color:#c5221f;" onclick="deleteLead()" title="Delete">🗑</button>
  
  <!-- Spacer -->
  <div style="flex:1;"></div>
  
  <!-- Edit button -->
  <button class="btn btn-ghost btn-sm" onclick="editLead()">✏ Edit</button>
  
  <!-- Add note button -->
  <button class="btn btn-ghost btn-sm" onclick="openNoteModal()">＋ Note</button>
  
  <!-- Create order (only when contacted) -->
  <button class="btn btn-ghost btn-sm" style="..." id="btnMoveToOrder" onclick="openMoveToOrder(lead&&lead.id)">📦 Order</button>
  
  <!-- Mark contacted (only for active leads) -->
  <button class="btn btn-secondary btn-sm" id="btnContacted" onclick="openContactedPopup()">📞 Contacted</button>
  
  <!-- Mark won (only when not done) -->
  <button class="btn btn-primary btn-sm" id="btnWon" onclick="openWonModal()">🏆 Won</button>
</div>
```

---

### Contacted Outcome Banner
```html
<div id="contactedOutcomeBanner" style="display:none;...">
  <div style="...">✅ Contacted — Choose outcome</div>
  <div style="display:flex;">
    <!-- Create order button -->
    <button onclick="openContactedPopup()">
      <span>📦</span>Create Order
    </button>
    
    <!-- Remind later button -->
    <button onclick="quickOutcome('remind_later')">
      <span>⏰</span>Remind Later
    </button>
    
    <!-- Mark lost button -->
    <button onclick="quickOutcome('lost_lead')">
      <span>🚫</span>Mark Lost
    </button>
  </div>
</div>
```

---

## CSS Styling

### Overlay Styles
```css
.ov {
  display: none;              /* Hidden by default */
  position: fixed;
  inset: 0;                   /* Cover entire viewport */
  background: rgba(0,0,0,.32); /* 32% black overlay */
  z-index: 200;
}

.ov.open {
  display: block;             /* Show when drawer is open */
}
```

---

### Drawer Container Styles
```css
.drawer {
  position: fixed;
  right: 0;
  top: 0;
  height: 100%;
  width: 500px;
  max-width: 100vw;           /* Full screen on mobile */
  
  background: var(--md-sys-color-surface);
  box-shadow: var(--md-sys-elevation-4);
  z-index: 201;
  
  transform: translateX(100%); /* Hidden off-screen right */
  transition: transform .25s cubic-bezier(.4,0,.2,1); /* Smooth animation */
  
  display: flex;
  flex-direction: column;      /* Vertical layout */
  border-left: 1px solid var(--md-sys-color-outline-variant);
}

.drawer.open {
  transform: translateX(0);    /* Slide in animation */
}
```

---

### Drawer Section Styles
```css
/* Header section */
.d-head {
  padding: 24px 28px 0;
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
}

/* Tab buttons container */
.d-tabs {
  display: flex;
  margin-top: 14px;
}

/* Individual tab button */
.d-tab {
  padding: 10px 18px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  color: var(--md-sys-color-on-surface-variant);
  white-space: nowrap;
}

/* Active tab styling */
.d-tab.active {
  border-bottom-color: var(--md-sys-color-primary);
  color: var(--md-sys-color-primary);
}

/* Scrollable content area */
.d-body {
  flex: 1;                    /* Take remaining space */
  overflow-y: auto;           /* Scrollable if needed */
  padding: 24px 28px;
}

/* Footer with buttons */
.d-foot {
  padding: 14px 24px;
  border-top: 1px solid var(--md-sys-color-outline-variant);
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
```

---

### Content Styling
```css
/* Key-value pairs (in Info tab) */
.kv {
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 8px 12px;
  font-size: 13px;
}

.kl {
  color: var(--md-sys-color-on-surface-variant);
  font-weight: 500;
}

.kv-val {
  color: var(--md-sys-color-on-surface);
  font-weight: 500;
  word-break: break-word;
}

/* Section headers */
.sh {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .4px;
  color: var(--md-sys-color-on-surface-variant);
  margin: 16px 0 10px;
}

/* Activity items */
.ai {
  display: flex;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
}

.ai-ic {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
  background: var(--md-sys-color-surface-container);
}

.ai-tp {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--md-sys-color-on-surface-variant);
  letter-spacing: .4px;
}

.ai-nt {
  font-size: 13px;
  color: var(--md-sys-color-on-surface);
  margin-top: 2px;
}

.ai-tm {
  font-size: 12px;
  color: var(--md-sys-color-outline);
  margin-top: 2px;
}

/* Order chip */
.och {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-radius: var(--r-sm);
  background: var(--md-sys-color-surface-container);
  cursor: pointer;
  transition: background .2s;
}

.och:hover {
  background: var(--md-sys-color-surface-container-high);
}

/* Row highlighting (table) */
tr.row-active td {
  background: var(--md-sys-color-primary-container) !important;
}

tr.row-active td:first-child {
  border-left: 3px solid var(--md-sys-color-primary) !important;
}
```

---

## JavaScript Functions

### Core Drawer Functions

#### `openDrawer(id)`
Opens drawer for specified lead

```javascript
async function openDrawer(id){
  try{
    // 1. Highlight selected row
    document.querySelectorAll('#leadsBody tr').forEach(r=>r.classList.remove('row-active'));
    const activeRow=document.querySelector(`#leadsBody tr[data-id="${id}"]`);
    if(activeRow) activeRow.classList.add('row-active');

    // 2. Fetch lead data
    const r=await fetch(`${API}/leads/${id}`,{headers:hdr()});
    if(!r.ok) return;
    lead=await r.json();
    
    // 3. Reset to Info tab
    tab='info';
    document.querySelectorAll('.d-tab').forEach((t,i)=>t.classList.toggle('active',i===0));
    
    // 4. Render drawer header and content
    applyDHead();
    renderTab('info');
    
    // 5. Show drawer with animation
    document.getElementById('dOv').classList.add('open');
    document.getElementById('drawer').classList.add('open');
  }catch(e){console.error('openDrawer',e);}
}
```

**Triggers:**
- Click on lead name in table
- Click → button in table
- Via `openMoveToOrder()` for quick order creation

**Parameters:**
- `id` (string) - Lead ID to open

**Behavior:**
1. Removes `row-active` class from all rows
2. Adds `row-active` class to clicked row
3. Fetches lead data from API
4. Resets tab to 'info'
5. Updates drawer header with lead details
6. Renders Info tab content
7. Adds `.open` class to drawer and overlay (triggers animation)

---

#### `closeDrawer()`
Closes the drawer

```javascript
function closeDrawer(){
  document.getElementById('dOv').classList.remove('open');
  document.getElementById('drawer').classList.remove('open');
  lead=null; 
  tab='info';
}
```

**Triggers:**
- Click on overlay/backdrop
- Click close button in modals
- After successful operations (save, delete, etc.)

**Behavior:**
1. Removes `.open` class from drawer and overlay (triggers animation out)
2. Clears `lead` variable
3. Resets tab to 'info'
4. Drawer slides out to right

---

#### `switchTab(tabName, element)`
Switch between drawer tabs

```javascript
function switchTab(t,el){
  tab=t;
  document.querySelectorAll('.d-tab').forEach(x=>x.classList.remove('active'));
  el.classList.add('active');
  renderTab(t);
}
```

**Parameters:**
- `t` (string) - Tab name: 'info', 'activity', 'orders', 'chat'
- `el` (HTMLElement) - Tab button element

**Behavior:**
1. Sets global `tab` variable
2. Removes `active` class from all tabs
3. Adds `active` class to clicked tab
4. Calls `renderTab()` to update content

---

#### `renderTab(tabName)`
Render content for current tab

```javascript
function renderTab(t){
  const b=document.getElementById('dBody');
  const foot=document.querySelector('.d-foot');
  const dHead=document.getElementById('dHead');
  const dEmptyHead=document.getElementById('dEmptyHead');
  
  if(!lead){
    // Show empty state
    b.innerHTML=`<div class="empty" style="...">👈 Click a lead to view details</div>`;
    if(foot) foot.style.display='none';
    if(dHead) dHead.style.display='none';
    if(dEmptyHead) dEmptyHead.style.display='';
    return;
  }
  
  // Show header and footer
  if(foot) foot.style.display='flex';
  if(dHead) dHead.style.display='';
  if(dEmptyHead) dEmptyHead.style.display='none';
  
  // Render appropriate tab
  if(t==='info')     renderInfo(b);
  else if(t==='activity') renderActivity(b);
  else if(t==='orders')   renderOrders(b);
  else if(t==='chat')     renderChat(b);
}
```

**Parameters:**
- `t` (string) - Tab name

**Behavior:**
1. If no lead selected:
   - Show empty state message
   - Hide header and footer
2. If lead selected:
   - Show header and footer
   - Call appropriate render function based on tab

---

### Tab Rendering Functions

#### `renderInfo(container)`
Renders the Info tab

**Displays:**
- **Contact Section:** Name, phone, email, company
- **Lead Details:** Product, source, city, created date, follow-up date, contact count
- **WABIS Labels:** If available, with edit button
- **Last Note & Notes:** Styled note displays
- **Quick Action:** "Log Call / Note" button

```javascript
function renderInfo(b){
  if(!lead) return;
  const l=lead, ov=l.next_followup_date&&l.next_followup_date<TODAY;
  b.innerHTML=`
    <div class="sh">Contact</div>
    <div class="kv">
      <span class="kl">Name</span><span class="kv-val">${esc(l.name)}</span>
      <span class="kl">Phone</span>
      <span class="kv-val">${esc(l.phone)}
        <button class="qa" onclick="callLead('${esc(l.phone)}')">📞</button>
        <button class="qa" onclick="waLead('${esc(l.phone)}','${esc(l.name)}')">💬</button>
      </span>
      ...
    </div>
    ...
  `;
}
```

---

#### `renderActivity(container)`
Renders the Activity tab

**Displays:**
- Timeline of all activities (calls, notes, status changes)
- Activity type with icon
- Activity description
- Relative timestamp
- "Log Activity" button at top

**API Call:**
- `GET /api/leads/{id}` (lead object includes activities array)

```javascript
function renderActivity(b){
  if(!lead) return;
  const acts=(lead.activities||[]).slice().reverse();
  if(!acts.length){
    b.innerHTML=`<div class="empty">📋 No activity yet</div>`;
    return;
  }
  
  const AICO={call:'📞',note:'📝',status_change:'🔄'};
  b.innerHTML=`<div style="...">
    <button class="btn btn-ghost btn-sm" onclick="openNoteModal()">＋ Log Activity</button>
  </div>
  ${acts.map(a=>`<div class="ai">
    <div class="ai-ic">${AICO[a.activity_type]||'📝'}</div>
    <div>
      <div class="ai-tp">${a.activity_type}</div>
      <div class="ai-nt">${esc(a.note||'')}</div>
      <div class="ai-tm">${ago(a.created_at)}</div>
    </div>
  </div>`).join('')}`;
}
```

---

#### `renderOrders(container)`
Renders the Orders tab

**Displays:**
- List of all orders created from this lead
- Order number, date, payment method
- Order total (₹ currency)
- Status with color coding
- Click to view order details

**API Call:**
- `GET /api/leads/{id}/orders`

```javascript
async function renderOrders(b){
  if(!lead) return;
  b.innerHTML=`<div style="...">Loading…</div>`;
  try{
    const r=await fetch(`${API}/leads/${lead.id}/orders`,{headers:hdr()});
    const orders=r.ok?await r.json():[];
    if(!orders.length){
      b.innerHTML=`<div class="empty">📦 No orders yet</div>`;
      return;
    }
    
    const sc={confirmed:'#137333',draft:'#80868b',delivered:'#1a73e8',cancelled:'#c5221f'};
    b.innerHTML=`${orders.map(o=>`<div class="och" onclick="location.href='orders.html'">
      <div>
        <div style="...">${esc(o.order_number)}</div>
        <div style="...">${fmtD(o.created_at)} · ${o.payment_method||''}</div>
      </div>
      <div style="...">
        <div style="...">₹${Number(o.total_amount||0).toLocaleString('en-IN')}</div>
        <div style="...;color:${sc[o.status]||'#80868b'};">${o.status||'—'}</div>
      </div>
    </div>`).join('')}`;
  }catch(e){
    b.innerHTML=`<div class="empty">⚠ Failed to load orders</div>`;
  }
}
```

---

#### `renderChat(container)`
Renders the Chat tab

**Displays:**
- WhatsApp message history (inbound & outbound)
- Messages styled with left/right positioning
- Timestamps on each message
- Compose box to send new messages

**API Call:**
- `GET /api/leads/{id}/messages`

**Send Function:**
- `POST /api/leads/{id}/activities` with activity_type='whatsapp'

```javascript
async function renderChat(b){
  if(!lead) return;
  try{
    const r=await fetch(`${API}/leads/${lead.id}/messages`,{headers:hdr()});
    const data=r.ok?await r.json():{};
    const msgs=data.messages||[];
    
    const chatHtml=msgs.length
      ?`<div id="chatBox" style="...">
        ${msgs.map(m=>`<div class="cbub ${m.direction==='outbound'?'out':'in'}">
          <div>${esc(m.message_body||m.body||m.message||'')}</div>
          <span class="ctm">${ago(m.created_at)}</span>
        </div>`).join('')}
      </div>`
      :`<div style="...">💬 No messages yet</div>`;
    
    b.innerHTML=chatHtml+`<div style="...">
      <input class="form-input" id="chatIn" placeholder="Type a message…" onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendChat();}">
      <button class="btn btn-primary btn-sm" onclick="sendChat()">Send</button>
    </div>`;
  }catch(e){
    b.innerHTML=`<div class="empty">⚠ Failed to load</div>`;
  }
}

async function sendChat(){
  if(!lead) return;
  const inp=document.getElementById('chatIn');
  const msg=inp.value.trim();
  if(!msg) return;
  inp.value='';
  try{
    await fetch(`${API}/leads/${lead.id}/activities`,{
      method:'POST',
      headers:hdr(),
      body:JSON.stringify({activity_type:'whatsapp',note:msg})
    });
    renderChat(document.getElementById('dBody'));
  }catch(e){ alert('Failed to send'); }
}
```

---

### Header Management Functions

#### `applyDHead()`
Updates drawer header with current lead data

```javascript
function applyDHead(){
  if(!lead) return;
  const dHead=document.getElementById('dHead');
  const dEmptyHead=document.getElementById('dEmptyHead');
  if(dHead) dHead.style.display='';
  if(dEmptyHead) dEmptyHead.style.display='none';
  
  document.getElementById('dNum').textContent=lead.lead_number||'—';
  document.getElementById('dName').textContent=lead.name;
  document.getElementById('dPhone').textContent=lead.phone||'—';
  
  const s=document.getElementById('dStatusSel');
  s.value=lead.status;
  s.className='st-sel s-'+lead.status;
  
  _applyFooterState();
}
```

**Called:**
- When drawer opens
- After status changes
- After lead updates

---

#### `_applyFooterState()`
Shows/hides footer buttons based on status

```javascript
function _applyFooterState(){
  if(!lead) return;
  const s = lead.status;
  const contacted  = s === 'contacted';
  const won        = s === 'success_won';
  const lost       = s === 'lost_lead';
  const done       = won || lost;

  // Order button ONLY when contacted
  document.getElementById('btnMoveToOrder').style.display = contacted ? '' : 'none';

  // Contacted button visible for active leads NOT yet contacted/won/lost
  document.getElementById('btnContacted').style.display = (!contacted && !done) ? '' : 'none';

  // Won button hidden when done
  document.getElementById('btnWon').style.display = done ? 'none' : '';

  // Outcome banner only when contacted
  const banner = document.getElementById('contactedOutcomeBanner');
  if(banner) banner.style.display = contacted ? 'flex' : 'none';
}
```

**Shows:**
- Order button: Only when status = 'contacted'
- Contacted button: Only for active leads (not contacted/won/lost)
- Won button: Always visible unless already won/lost
- Outcome banner: Only when status = 'contacted'

---

### Status Management Functions

#### `drawerStatusChange(newStatus)`
Handle status dropdown changes

```javascript
async function drawerStatusChange(ns){
  if(!lead) return;
  // Already contacted + selecting contacted again -> open outcome popup
  if(ns === 'contacted' && lead.status === 'contacted'){
    document.getElementById('dStatusSel').value = 'contacted';
    openContactedPopup();
    return;
  }
  await patch(lead.id, {status: ns});
  lead.status = ns;
  document.getElementById('dStatusSel').className = 'st-sel s-' + ns;
  _applyFooterState();
  loadLeads(); 
  loadStats();
}
```

**Special Cases:**
- If already contacted and reselecting "contacted", opens outcome modal instead
- Updates UI and reloads table/stats

---

#### `openContactedPopup()`
Mark lead as contacted

```javascript
function openContactedPopup(){
  if(!lead) return;
  cpMode = (lead.status === 'contacted') ? 'outcome' : 'first';
  
  // Clear form
  document.getElementById('cpNote').value='';
  document.getElementById('cpRemindDate').value='';
  document.getElementById('cpDateField').style.display='none';
  document.getElementById('cpName').textContent=lead.name+' · '+(lead.phone||'');

  // If already contacted, show outcome options
  if(cpMode === 'outcome'){
    titleEl.textContent = 'Outcome — What happened?';
    outcomeSection.style.display = 'block';
  } else {
    titleEl.textContent = 'Mark as Contacted';
    outcomeSection.style.display = 'none';
  }

  document.getElementById('contactedModal').classList.add('open');
}
```

**Two Modes:**
1. **First contact:** Just logs the contact, sets status to contacted
2. **Outcome:** When already contacted, must choose outcome:
   - Create Order
   - Remind Later (with date)
   - Mark Lost

---

#### `openWonModal()`
Mark lead as won and create order

**Opens modal to:**
- Confirm lead name and phone
- Add order items (description, quantity, price)
- Set payment method
- Apply discount
- Add notes

**On Save:**
- Creates order via `POST /api/leads/{id}/success_won`
- Updates lead status to 'success_won'
- Closes drawer

---

### Action Button Functions

#### `editLead()`
Opens lead edit modal

```javascript
function editLead(){ 
  if(lead) openLeadModal(lead); 
}
```

Opens modal to edit:
- Name, phone
- City, state
- Product interest
- Notes
- Status
- Follow-up date
- Source

---

#### `deleteLead()`
Delete lead with confirmation

```javascript
async function deleteLead(){
  if(!lead) return;
  if(!confirm(`Delete lead "${lead.name}"? This cannot be undone.`)) return;
  try{
    const r=await fetch(`${API}/leads/${lead.id}`,{method:'DELETE',headers:hdr()});
    if(r.ok){ closeDrawer(); loadLeads(); loadStats(); }
    else{ alert('Delete failed'); }
  }catch(e){ alert('Network error'); }
}
```

---

#### `openNoteModal()`
Log activity/note

Opens modal to add:
- Activity type (call, note, status change)
- Description/note
- New status (if status change)

---

#### `openMoveToOrder(leadId)`
Create order from lead

Opens drawer to:
- Confirm lead details
- Add order items
- Set payment, discount, shipping
- Create order and close lead

---

## API Endpoints

### Used in Drawer

| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/api/leads/{id}` | GET | Fetch full lead data | Lead object with all details, activities |
| `/api/leads/{id}` | PATCH | Update lead (status, etc.) | Updated lead object |
| `/api/leads/{id}` | DELETE | Delete lead | Success/error response |
| `/api/leads/{id}/activities` | GET | Fetch activities | Activities array (included in lead) |
| `/api/leads/{id}/activities` | POST | Add new activity | New activity object |
| `/api/leads/{id}/orders` | GET | Fetch linked orders | Orders array |
| `/api/leads/{id}/messages` | GET | Fetch WhatsApp messages | Messages array |
| `/api/leads/{id}/contacted` | POST | Log contact & outcome | Response with activity |
| `/api/leads/{id}/success_won` | POST | Mark won & create order | Order object |

---

## Drawer Content Details

### Info Tab - Contact Section
```
Name          → lead.name
Phone         → lead.phone (with call/WhatsApp buttons)
Alternate     → lead.alternate_phone (if present)
Email         → lead.email (if present)
Company       → lead.company_name (if present)
```

### Info Tab - Lead Details Section
```
Product       → lead.product_interest
Source        → lead.source (visual badge)
City/State    → lead.city, lead.state
Created       → lead.created_at (formatted date)
Follow-up     → lead.next_followup_date (with overdue flag)
Remind On     → lead.remind_later_date (if set)
Last Contact  → lead.last_contacted_at (relative time)
Times Called  → lead.contacted_count
```

### Info Tab - Additional Sections
```
WABIS Labels  → lead.wabis_labels[] (green chips)
Last Note     → lead.note_last (highlighted box)
Notes         → lead.notes (full notes section)
```

### Activity Tab
```
Activity Array (reversed chronologically):
  - activity_type (call, note, status_change, etc.)
  - note (description)
  - created_at (timestamp)
  - old_status, new_status (if status change)
```

### Orders Tab
```
Order Array from GET /api/leads/{id}/orders:
  - order_number (formatted as ORD-DATE-ID)
  - created_at (date)
  - payment_method (cash, card, check, etc.)
  - total_amount (₹ currency)
  - status (confirmed, draft, delivered, cancelled)
```

### Chat Tab
```
Messages Array from GET /api/leads/{id}/messages:
  - message_body / body / message (text content)
  - direction (inbound / outbound)
  - created_at (timestamp)
```

---

## State Management

### Global Variables
```javascript
let lead = null;        // Current lead object
let tab = 'info';       // Current tab (info|activity|orders|chat)
let lead = null;        // Cleared on closeDrawer()
```

### CSS Classes for State
```
.drawer        - Container (always present)
.drawer.open   - Drawer visible (animation in)
.ov            - Overlay (always present)
.ov.open       - Overlay visible
.row-active    - Selected row in table
.d-tab.active  - Active tab button
```

### Data Flow
```
User clicks lead
    ↓
openDrawer(id)
    ↓
Fetch /api/leads/{id}
    ↓
Set lead = leadData
    ↓
applyDHead() - Update header
    ↓
renderTab('info') - Show Info tab
    ↓
Add .open classes - Trigger animation
    ↓
Drawer slides in
```

---

## Responsive Behavior

### Desktop (500px drawer)
- Full 500px width drawer
- Semi-transparent overlay
- Smooth animations
- All content visible

### Tablet (> 600px)
- 500px drawer (may adjust to 80vw)
- Same functionality
- Slightly smaller on narrow tablets

### Mobile (< 600px)
- `max-width: 100vw` makes drawer full width
- Full screen drawer experience
- All buttons and content still accessible
- Overlay still functional

---

## Testing Scenarios

1. **Open Drawer**
   - Click lead → drawer slides in
   - Overlay appears
   - Row highlights
   - Header shows lead data

2. **Tab Switching**
   - Click Activity → shows timeline
   - Click Orders → shows orders
   - Click Chat → shows messages
   - Tab styling updates

3. **Status Change**
   - Select new status from dropdown
   - Footer buttons update
   - If contacted, outcome banner appears

4. **Log Activity**
   - Click ＋ Note → modal opens
   - Add activity → Activity tab updates

5. **Create Order**
   - Click 📦 Order → order drawer opens
   - Add items → order created
   - Drawer closes, Status → Won

6. **Close Drawer**
   - Click overlay → drawer closes
   - Animation slides out
   - Row unhighlights

---

## Debugging

### Check Console
```javascript
// Check current lead
console.log(lead);

// Check current tab
console.log(tab);

// Check drawer visibility
console.log(document.getElementById('drawer').classList);

// Check if overlay exists
console.log(document.getElementById('dOv'));
```

### Common Issues
1. **Drawer won't open:** Check if `lead` is set, check for JS errors
2. **Content not showing:** Check if `renderTab()` function exists
3. **Overlay not clickable:** Check if element has `id="dOv"`
4. **Animations not working:** Check CSS transitions enabled

---

*Last Updated: February 23, 2026*
*Status: ✅ Production Ready*
