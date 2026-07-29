# 📣 Miguel CRM — Marketing Module: Full Design Document
**Version:** 1.0 | **Date:** 2026-02-22 | **Author:** System Design

---

## 🎯 What This Module Does
The Marketing Module lets your team:
1. **Segment** leads + customers using rich filters (status, region, purchase history, product interest, etc.)
2. **Send bulk campaigns** — WhatsApp (already wired!), Email, SMS — to any segment
3. **Track campaign performance** (sent, delivered, replied, converted to order)
4. **View geographic + purchase analytics** (orders per customer, AOV, profit, pincode heatmap)
5. **Manage individual 1:1 WhatsApp chats** via live chatbox

---

## ✅ MASTER CHECKLIST (Priority Order)

### 🟢 TIER 1 — MUST HAVE (Core Functionality)

#### 1. Audience Segmentation Panel
- [ ] Filter by **Lead status** (`created`, `new_lead`, `contacted`, `remind_later`, `success_won`, `lost_lead`)
- [ ] Filter by **Customer lead_status** (`new`, `called`, `interested`, `not_interested`, `converted`, `lost`)
- [ ] Filter by **Interest status** (`hot`, `warm`, `cold`)
- [ ] Filter by **City / State / Pincode** (geo-region filters)
- [ ] Filter by **Customer type** (`retail`, `wholesale`, `distributor`)
- [ ] Filter by **Source** (`manual`, `whatsapp`, `meta`, `website`, `referral`)
- [ ] Filter by **Last order date** (e.g. "no order in 30/60/90 days")
- [ ] Filter by **Min/Max total spend** (lifetime value filter)
- [ ] Filter by **Product interest** / product bought (text search)
- [ ] Filter by **Assigned employee**
- [ ] Filter by **Date range** (created_at, last_order_date)
- [ ] **Combine filters** with AND logic
- [ ] **Save a segment** with a name for reuse

#### 2. Audience Table
- [ ] Columns: Name, Phone, City/State, Status, Source, Last Order, Total Spend, Orders Count
- [ ] **Checkbox per row** for manual selection
- [ ] **Select all in segment** button
- [ ] **Live result count** (e.g. "147 contacts match")
- [ ] Pagination (page_size 50)
- [ ] Quick link to open full Lead/Customer profile

#### 3. WhatsApp Bulk Sender (TOP PRIORITY)
- [ ] Uses existing `/api/whatsapp/send` endpoint per lead
- [ ] **Select template or type custom message** (plain text, within 24h window)
- [ ] **Batch queue** (send 1 per second to avoid Meta rate limits)
- [ ] **Preview** message before sending
- [ ] **Progress bar** while sending ("Sending 45 / 147…")
- [ ] **Per-lead status log** (sent ✅ / failed ❌ / skipped)
- [ ] **Opt-out flag** on lead (`whatsapp_opted_out`) — skip those leads
- [ ] Result summary: total sent, total failed

#### 4. WhatsApp Chatbox (1:1 Live Chat — already partially built in leads.html)
- [ ] Full chat panel accessible from marketing audience table
- [ ] Load chat history from `/api/leads/{id}/messages`
- [ ] Send message via `/api/whatsapp/send`
- [ ] Show inbound bubbles (left, blue) / outbound (right, green)
- [ ] Unread message badge on lead row
- [ ] Auto-scroll to latest message

#### 5. Campaign Record (Log Each Blast)
- [ ] Create a Campaign record when a blast is initiated
- [ ] Fields: `campaign_name`, `channel`, `audience_count`, `message_content`, `created_at`, `created_by`
- [ ] Track per-campaign: `sent`, `failed`, `delivered` (webhook updates)
- [ ] Campaign history table

---

### 🟡 TIER 2 — SHOULD HAVE (Analytics & Intelligence)

#### 6. Customer Analytics Dashboard
- [ ] **Orders per customer** (bar chart top 10)
- [ ] **Total spend per customer** (sortable list)
- [ ] **Average Order Value** by city/state
- [ ] **Profit per order** = `total_amount - sum(item.quantity × product.cost_price)`
- [ ] **Region heatmap** — customers by state (bar chart, not a map, easier to build)
- [ ] **Top pincodes** — top 10 pincodes by order count
- [ ] **Dormant customers** — last order > 60 days (filter-ready segment)
- [ ] **New this month vs returning** pie chart

#### 7. Lead Funnel Analytics
- [ ] Use existing `/api/reports/leads/funnel`
- [ ] Show pipeline conversion: new → contacted → won (%)
- [ ] Leads by source (Meta vs WhatsApp vs Manual)
- [ ] Overdue reminders count (action prompt: "14 leads need follow-up today")

#### 8. Email Campaign Integration
- [ ] Email provider config (SMTP or SendGrid API Key in settings)
- [ ] **Compose email** with subject + HTML/plain body
- [ ] **Template variables**: `{{name}}`, `{{city}}`, `{{product_interest}}`
- [ ] Send to selected segment (backend queues per email)
- [ ] Track: sent, bounced, unsubscribed (via webhook from provider)
- [ ] **Unsubscribe link** auto-included in footer
- [ ] `email_opted_out` flag on customer/lead

#### 9. SMS Campaign Integration
- [ ] SMS provider config (Twilio or Indian SMS aggregator — e.g. MSG91, Textlocal)
- [ ] Compose short SMS (160 char limit enforced)
- [ ] Send to segment (phone numbers)
- [ ] **DND check** warning (required in India)
- [ ] `sms_opted_in` flag required before sending
- [ ] Track: sent, failed, delivery receipt

---

### 🔵 TIER 3 — NICE TO HAVE (Future / Advanced)

#### 10. Saved Segments
- [ ] Save a filter combination with a name (e.g. "Kerala Hot Customers")
- [ ] List saved segments, apply in 1 click
- [ ] Show count on segment card (refreshed on load)

#### 11. Campaign Scheduling
- [ ] Schedule a campaign for a future date/time
- [ ] Backend cron job runs at that time
- [ ] Show scheduled campaigns in campaign history

#### 12. WhatsApp Template Support
- [ ] Manage pre-approved Meta Business templates
- [ ] Select template + fill variables when sending outside 24h window
- [ ] Submit template to Meta for approval (external link or form)

#### 13. Data Export
- [ ] Export filtered audience to CSV
- [ ] Fields: Name, Phone, Email, City, State, Pincode, Status, Last Order, Spend

#### 14. Bulk WhatsApp via 360dialog / Twilio (Scale)
- [ ] Second WA provider support if volume exceeds current Meta API limits
- [ ] Provider selection in config

---

## 🗺️ PAGE LAYOUT DESIGN (UI Wireframe Description)

```
┌─────────────────────────────────────────────────────────────────────┐
│ TOPBAR: ← Dashboard | 📣 Marketing |  [tenant badge]               │
├─────────────────────────────────────────────────────────────────────┤
│ TABS: [Audience] [Campaigns] [Analytics] [Settings]                 │
├────────────────┬────────────────────────────────────────────────────┤
│ FILTER PANEL   │ MAIN PANEL                                         │
│ (left, 260px)  │                                                    │
│                │  ┌─ STAT STRIP ──────────────────────────────┐    │
│ ─ STATUS ─     │  │ 📊 Total | 🔥 Hot | ⏰ Remind | ✅ Won   │    │
│ □ new_lead     │  └──────────────────────────────────────────┘    │
│ □ contacted    │                                                    │
│ □ remind_later │  ┌─ ACTION BAR ──────────────────────────────┐   │
│ □ won / lost   │  │ [✓ Select All 147] [💬 WhatsApp Blast]    │   │
│                │  │ [📧 Email Blast] [📱 SMS Blast] [⬇ CSV]  │   │
│ ─ INTEREST ─   │  └──────────────────────────────────────────┘   │
│ □ Hot          │                                                    │
│ □ Warm         │  ┌─ AUDIENCE TABLE ──────────────────────────┐   │
│ □ Cold         │  │ □ | Name  | Phone | City | Status | Spend │   │
│                │  │ ──────────────────────────────────────────│   │
│ ─ REGION ─     │  │ □ | Ravi  | 9876… | Kochi | Hot | ₹4,200 │   │
│ State: [▼]     │  │ □ | Meena | 9871… | Pune  | Warm| ₹1,800 │   │
│ City: [input]  │  │ □ | …     | …     | …     | …   | …      │   │
│ Pincode: [  ]  │  └──────────────────────────────────────────┘   │
│                │  [← Prev]  Page 1 of 5 (147 contacts)  [Next →]  │
│ ─ ORDERS ─     │                                                    │
│ Min orders: [1]│                                                    │
│ Last order:    │                                                    │
│ [within 30d ▼] │                                                    │
│                │                                                    │
│ ─ SOURCE ─     │                                                    │
│ □ WhatsApp     │                                                    │
│ □ Meta         │                                                    │
│ □ Manual       │                                                    │
│                │                                                    │
│ [Apply] [Clear]│                                                    │
└────────────────┴────────────────────────────────────────────────────┘
```

### Campaigns Tab Layout
```
┌─────────────────────────────────────────────────────────────────────┐
│ [+ New Campaign]                    [Search campaigns…]             │
├─────┬──────────────────┬──────────┬──────────┬──────────┬──────────┤
│ #   │ Campaign Name    │ Channel  │ Audience │ Sent     │ Date     │
├─────┼──────────────────┼──────────┼──────────┼──────────┼──────────┤
│ 001 │ Feb Offer        │ 💬 WA    │ 147      │ 145 ✅   │ Feb 22   │
│ 002 │ Diwali Email     │ 📧 Email │ 320      │ 318 ✅   │ Jan 15   │
└─────┴──────────────────┴──────────┴──────────┴──────────┴──────────┘
```

### WhatsApp Blast Modal
```
┌─────────────────────────────────────────────────────────────────────┐
│  💬 WhatsApp Bulk Campaign                              [✕ Close]   │
│  Audience: 147 contacts selected                                    │
├─────────────────────────────────────────────────────────────────────┤
│  Campaign Name: [ February Offer Campaign          ]               │
│  Message:                                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Hello {{name}}, exciting offer on Black Pepper this month!  │   │
│  │ Order now: https://wa.me/919999999999                       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  Characters: 142/4096                                               │
│  ⚠️ WhatsApp: 24h window rule applies. Outside window = template.  │
│                                                                     │
│  Preview for Ravi Kumar:                                            │
│  "Hello Ravi Kumar, exciting offer on Black Pepper…"               │
│                                                                     │
│  [Cancel]                          [🚀 Send to 147 contacts]       │
│  ─────────────────────────────────────────────────────────────     │
│  ▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░  Sending 62/147…                       │
│  ✅ 60 sent  ❌ 2 failed  ⏭ 0 skipped                             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔌 API ENDPOINTS TO USE (Existing — Zero New Backend Needed for Tier 1)

| Action | Method | Endpoint | Notes |
|--------|--------|----------|-------|
| Get leads (audience) | GET | `/api/leads/` | filters: status, source, city, search, assigned_to_id |
| Get customers (audience) | GET | `/api/customers/` | filters: lead_status, interest_status, city, source |
| Customers with order data | GET | `/api/customers/with-orders` | includes order counts, spend |
| Lead stats | GET | `/api/leads/stats` | pipeline counts |
| Customer stats | GET | `/api/customers/stats` | totals |
| Top customers | GET | `/api/reports/customers/top` | top by spend |
| Lead funnel | GET | `/api/reports/leads/funnel` | by source, by stage |
| Revenue report | GET | `/api/reports/revenue` | monthly revenue |
| Product report | GET | `/api/reports/products` | top products |
| Dashboard stats | GET | `/api/reports/dashboard` | all KPIs |
| Send WA message | POST | `/api/whatsapp/send` | `{lead_id, message}` |
| WA chat history | GET | `/api/leads/{id}/messages` | per-lead messages |
| WA config status | GET | `/api/whatsapp/config` | is configured? |
| Log activity | POST | `/api/leads/{id}/activities` | log campaign send |
| Orders list | GET | `/api/orders/` | filter by customer_id, dates |
| Products list | GET | `/api/products/` | for profit calculation |

### 🆕 New Backend Endpoints Needed (Tier 1 Critical)

| Action | Method | Endpoint | Why |
|--------|--------|----------|-----|
| Create campaign record | POST | `/api/marketing/campaigns/` | log every bulk send |
| List campaigns | GET | `/api/marketing/campaigns/` | campaign history tab |
| Update campaign stats | PATCH | `/api/marketing/campaigns/{id}` | update sent/failed counts |
| Bulk WA send (queue) | POST | `/api/marketing/whatsapp/blast` | server-side batching |
| Get segment count | POST | `/api/marketing/segment/count` | live count before send |
| Leads + orders joined | GET | `/api/marketing/audience` | combined: lead + order stats per person |

---

## 🏗️ BACKEND MODULE NEEDED: `backend/app/modules/marketing/`

### Files to create:
```
backend/app/modules/marketing/
├── __init__.py
├── router.py          ← 6 new endpoints
├── schemas.py         ← Campaign, Segment, BlastRequest schemas  
└── service.py         ← audience query, bulk WA sender, campaign CRUD
```

### `CampaignModel` (new DB table `marketing_campaigns`):
```python
id                UUID  PK
tenant_id         UUID  FK(tenants)
campaign_name     String(255)
channel           Enum("whatsapp", "email", "sms")
audience_filters  JSON          # the filter snapshot
audience_count    Integer
message_content   Text
status            Enum("draft", "sending", "completed", "failed")
sent_count        Integer default 0
failed_count      Integer default 0
delivered_count   Integer default 0
created_by_id     UUID  FK(employees)
created_at        DateTime
completed_at      DateTime nullable
```

### Key Service Logic:

#### `build_audience(db, tenant_id, filters)` → list of (lead_id, name, phone)
```python
# Queries leads table with all filters
# Joins with orders to get order count + total spend
# Returns list ready for bulk send
```

#### `bulk_whatsapp_blast(db, campaign_id, audience, message_template)`
```python
# For each lead in audience:
#   1. Replace {{name}} with lead.name
#   2. Call send_text_message(phone, message)  ← core/whatsapp_api.py
#   3. Log to lead_messages (direction=outbound)
#   4. Log activity (type=recovery_campaign)  
#   5. Update campaign sent/failed count
#   6. Sleep 1 second (Meta rate limit safe)
```

---

## 📊 DATA FOR "ORDERS + CUSTOMERS" ANALYTICS

### Profit per order formula:
```
profit = order.total_amount 
       - sum(item.quantity × product.cost_price for item in order.items)
       - order.shipping_charge
```
**Note:** `product.cost_price` already exists in `products` table. Need to join `order_items → products`.

### Key metrics per customer (already in `Customer` model!):
| Field | Source |
|-------|--------|
| `total_orders` | Customer.total_orders (updated on order events) |
| `average_order_value` | Customer.average_order_value |
| `first_order_date` | Customer.first_order_date |
| `last_order_date` | Customer.last_order_date |
| Total spend | Query `SUM(orders.total_amount)` by customer_id |

### Regional analytics queries:
```sql
-- Top states by customer count
SELECT state, COUNT(*) as count FROM customers 
WHERE tenant_id=? GROUP BY state ORDER BY count DESC LIMIT 10;

-- Top pincodes by order count
SELECT c.pincode, COUNT(o.id) as orders FROM orders o 
JOIN customers c ON o.customer_id=c.id 
WHERE o.tenant_id=? GROUP BY c.pincode ORDER BY orders DESC LIMIT 10;

-- Orders per customer (top 20)
SELECT c.name, c.phone, COUNT(o.id) as orders, SUM(o.total_amount) as spend
FROM customers c JOIN orders o ON o.customer_id=c.id 
WHERE c.tenant_id=? GROUP BY c.id ORDER BY spend DESC LIMIT 20;
```

---

## 📧 EMAIL INTEGRATION PLAN

### Option A: SMTP (Simple, works with Gmail/Outlook/Any SMTP)
```python
# Config (env vars):
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@pureleven.com
SMTP_PASS=...
SMTP_FROM_NAME="Pureleven Team"

# Python: smtplib + email.mime (no extra package needed)
```

### Option B: SendGrid (Better for bulk, tracking, deliverability)
```python
# pip install sendgrid
# Config: SENDGRID_API_KEY=SG.xxx
# Supports: templates, open tracking, unsubscribe groups, webhooks
```

**Recommended for Pureleven: Start with SMTP → upgrade to SendGrid when volume > 500/day**

### Template variable system:
```
{{name}}            → lead.name or customer.name  
{{city}}            → lead.city
{{product_interest}} → lead.product_interest
{{phone}}           → lead.phone
{{company}}         → lead.company_name
```

---

## 📱 WHATSAPP INTEGRATION (Already Partially Built!)

### Current State (already working):
- ✅ `POST /api/whatsapp/send` — sends 1:1 message to a lead
- ✅ `POST /api/whatsapp/webhook` — receives inbound messages
- ✅ Lead messages stored in `lead_messages` table
- ✅ WhatsApp chat widget in `leads.html` (Info/Activity/Orders/💬 Chat tabs)
- ✅ Auto-reply on inbound message

### What needs to be added for Marketing:
- 🔲 **Bulk sender**: loop over audience, call `/api/whatsapp/send` per lead (or new `/api/marketing/whatsapp/blast`)
- 🔲 **Template message support**: for leads outside 24h window
- 🔲 **`whatsapp_opted_out` flag** on Lead model (skip those in bulk)
- 🔲 **WhatsApp chatbox in Marketing page** (reuse leads.html chat code)
- 🔲 **Unread message count badge** per lead (query unread messages)

### WhatsApp 24h Window Rule (Important!):
```
✅ Within 24h of last customer message  → any text message allowed
❌ Outside 24h window                  → MUST use approved template
```
For bulk marketing: use **template messages** (pre-approved by Meta) OR target only leads who messaged within 24h.

### Template Message API call:
```python
# POST https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages
{
  "messaging_product": "whatsapp",
  "to": "919876543210",
  "type": "template",
  "template": {
    "name": "monthly_offer",
    "language": {"code": "en"},
    "components": [{"type": "body", "parameters": [{"type": "text", "text": "Ravi"}]}]
  }
}
```

---

## 📱 SMS INTEGRATION PLAN

### Recommended: MSG91 (India-focused, DLT-registered)
```python
# Config:
MSG91_API_KEY=...
MSG91_SENDER_ID=PURLEV      # 6-char registered sender ID
MSG91_TEMPLATE_ID=...        # DLT template ID (required in India)

# API: POST https://api.msg91.com/api/v5/flow/
# Body: {"flow_id": "...", "sender": "PURLEV", "mobiles": "919876543210", "VAR1": "Ravi"}
```

### India SMS Compliance (DLT — Mandatory):
- Register on **DLT portal** (any telecom operator)
- Register your **sender ID** (6 chars, e.g. PURLEV)
- Register each **SMS template** (get Template ID)
- Include template ID in every API call
- **No DLT = messages blocked by telecom** ⚠️

---

## 🔐 COMPLIANCE CHECKLIST

### WhatsApp
- [ ] Only send to leads who have interacted (or use approved templates)
- [ ] Add `whatsapp_opted_out` flag on Lead model
- [ ] Respect Meta rate limits (80 messages/sec, 250 unique users/day on unverified biz)
- [ ] Include contact name + purpose in message

### Email
- [ ] Add `email_opt_out` flag on Customer/Lead
- [ ] Auto-include unsubscribe link in every email
- [ ] Handle bounce + unsubscribe webhooks (update DB immediately)
- [ ] SPF / DKIM / DMARC records set on domain

### SMS (India)
- [ ] Add `sms_opted_in` flag on Customer/Lead
- [ ] DLT registration complete
- [ ] Sender ID registered
- [ ] Templates pre-approved before use
- [ ] Include opt-out instruction in SMS

---

## 📁 FILES TO CREATE

### Frontend:
```
frontend/marketing.html     ← Main marketing page (single file)
```

### Backend:
```
backend/app/modules/marketing/__init__.py
backend/app/modules/marketing/router.py
backend/app/modules/marketing/schemas.py
backend/app/modules/marketing/service.py
backend/alembic/versions/k8_add_marketing_campaigns.py   ← migration
```

### Docs:
```
docs/marketing/MARKETING_MODULE_DESIGN.md   ← This file
docs/marketing/WHATSAPP_BLAST_GUIDE.md
docs/marketing/EMAIL_SETUP_GUIDE.md
docs/marketing/SMS_DLT_GUIDE.md
```

---

## 🚀 IMPLEMENTATION ORDER (Sprint Plan)

### Sprint 1 — Audience + WhatsApp Blast (This Week)
1. Create `frontend/marketing.html` with filter panel + audience table
2. Wire filters to `/api/leads/` + `/api/customers/with-orders`
3. Add stat strip using `/api/reports/dashboard`
4. Build WhatsApp blast modal (client-side loop calling `/api/whatsapp/send`)
5. Add campaign log (localStorage or simple backend table)

### Sprint 2 — Analytics + Campaign History (Next Week)
1. Create `backend/app/modules/marketing/` module
2. `POST /api/marketing/campaigns/` — create campaign record
3. `GET /api/marketing/campaigns/` — list past campaigns
4. Analytics tab: orders per customer, regional bars, top pincodes
5. Profit per order chart (needs cost_price join)

### Sprint 3 — Email + SMS (Week 3)
1. SMTP email sender in backend
2. Email compose modal on marketing page
3. SMS integration (MSG91 or Twilio)
4. Opt-out flags added to Lead + Customer models (Alembic migration)
5. Unsubscribe endpoint: `POST /api/marketing/unsubscribe`

### Sprint 4 — Advanced (Week 4+)
1. Saved segments
2. Campaign scheduling
3. WhatsApp template message support
4. CSV export of audience
5. Open/click tracking via SendGrid webhooks

---

## 🔗 RELEVANT EXISTING CODE TO REUSE

| Feature | Reuse From |
|---------|-----------|
| WhatsApp chat widget | `frontend/leads.html` → Chat tab (lines ~856-890) |
| WA send logic | `backend/app/core/whatsapp_api.py` → `send_text_message()` |
| Customer filter query | `backend/app/modules/customers/service.py` → `list_customers()` |
| Lead filter query | `backend/app/modules/leads/service.py` → `list_leads()` |
| Order stats | `backend/app/modules/orders/service.py` → `get_order_stats()` |
| Top customers | `backend/app/modules/reporting/service.py` → `get_top_customers()` |
| Auth token header | All pages → `localStorage.getItem('token')` + `Authorization: Bearer` |
| Design system | `frontend/ds.css` → all classes (btn, form-input, chip, etc.) |
| Stat strip component | `frontend/customers.html` → stat-strip HTML pattern |
| Filter selects | `frontend/leads.html` → toolbar + filter-select pattern |

---

## ⚡ QUICK WIN: WhatsApp Blast with Existing APIs

You can ship a working WhatsApp bulk sender **today** using only existing endpoints:

```javascript
// Marketing page — bulk WA sender (no new backend needed!)
async function sendWhatsAppBlast(leadIds, messageTemplate) {
  const results = { sent: 0, failed: 0 };
  for (const id of leadIds) {
    const lead = audience.find(l => l.id === id);
    const msg = messageTemplate.replace('{{name}}', lead.name);
    try {
      const r = await fetch('/api/whatsapp/send', {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json' },
        body: JSON.stringify({ lead_id: id, message: msg })
      });
      if (r.ok) results.sent++;
      else results.failed++;
    } catch { results.failed++; }
    await new Promise(r => setTimeout(r, 1000)); // 1 per second rate limit
    updateProgress(results);
  }
}
```

**This works right now.** The Marketing page just needs the UI shell + this JS loop.

---

*Last updated: 2026-02-22 | Next page to build: `frontend/marketing.html`*
