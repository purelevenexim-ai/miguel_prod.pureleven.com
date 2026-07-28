# Miguel CRM Platform

[![Backend: FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Frontend: HTML5](https://img.shields.io/badge/Frontend-HTML5--CSS3--JavaScript-E34C26.svg)](https://developer.mozilla.org/en-US/docs/Web/HTML)
[![Database: PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%2015-336791.svg)](https://www.postgresql.org/)
[![Server: Nginx](https://img.shields.io/badge/Server-Nginx-009639.svg)](https://www.nginx.com/)
[![Docker: Compose](https://img.shields.io/badge/Deploy-Docker%20Compose-2496ED.svg)](https://www.docker.com/)

**Multi-tenant CRM platform** with Shopify integration, logistics provider support, WhatsApp automation, and comprehensive order/lead/vendor management.

**Hosted:** `172.232.118.208` | **Last Updated:** Feb 25, 2026

---

## **Quick Start**

### **Prerequisites**
- Docker & Docker Compose installed
- 2GB+ free disk space
- Ports 80, 443, 8000 available

### **1. Clone & Configure**

```bash
git clone <repo>
cd /opt/miguel
cp .env.example backend/.env
```

Update `backend/.env` and `docker-compose.yml` with your credentials (ENCRYPTION_KEY, WhatsApp tokens, etc.).

### **2. Build & Start**

```bash
docker compose build
docker compose up -d
```

Wait 10-15 seconds for services to initialize.

### **3. Apply Database Migrations**

```bash
docker compose exec backend alembic upgrade head
```

### **4. Access the System**

| Component | URL | Credentials |
|-----------|-----|-------------|
| **Frontend** | http://localhost | (redirects to login) |
| **Tenant Login** | http://localhost/login | `purelevenexim@gmail.com` / `wM01gkxGCNhJT!` |
| **Admin Dashboard** | http://localhost/tenant-admin | After login |
| **Backend API Docs** | http://localhost:8000/docs | Swagger UI |

### **5. Test Integration**

```bash
python3 scripts/test_shipping.py
```

Expected output:
```
✅ Login OK
✅ /api/config/shopify-stores → 0 items
🎉 All shipping config endpoints working!
```

---

## **📋 Recent Updates (Feb 25, 2026)**

### Latest: Auto Pay Status Update on Delivery
✅ **New Logic:** When order status → "Delivered", Pay Status automatically → "Paid"  
✅ **Works for:** All payment methods (COD, UPI, Bank Transfer, Cheque, etc.)  
✅ **Reasoning:** If parcel is delivered, payment must have been collected  
✅ **Behavior:** Full amount marked paid, amount due → 0  
📖 **Details:** See [AUTO_PAY_STATUS_UPDATE_FIX.md](./AUTO_PAY_STATUS_UPDATE_FIX.md)

### Previous Session: Orders Table & India Post xlsx Upload Fixes
✅ **Fixed:** Order creation returning 500 (missing `PaymentMethod` import)  
✅ **Fixed:** Pay Status & Status dropdowns blocked on terminal orders  
✅ **Fixed:** India Post xlsx upload returning 400 (hyphenated headers not supported)  
✅ **Enhanced:** Column detection with content-based fallback (scans for India Post article numbers)  
✅ **Added:** Status dropdown in orders table (interactive, all statuses changeable on terminal orders)  
✅ **Added:** Debug logging for xlsx header detection  
📖 **Full Details:** See [ORDERS_TABLE_FIX_SESSION_2026_02_25.md](./ORDERS_TABLE_FIX_SESSION_2026_02_25.md)

### Previous Updates
✅ **Fixed:** Password hash corruption on login  
✅ **Fixed:** ENCRYPTION_KEY configuration (docker-compose.yml)  
✅ **Fixed:** reportlab missing from Docker image  
✅ **Reorganized:** Frontend into auth/ modules/ pages/ styles/  
✅ **Archived:** 62 old documentation files to docs/archived/  
✅ **Added:** Nginx service with proper routing  
✅ **Updated:** Comprehensive documentation (CODEBASE_STRUCTURE.md)

---

## **Architecture Overview**

## 📁 Project Structure

```
/opt/miguel/
├── README.md                        ← You are here (master index)
├── docker-compose.yml
│
├── backend/                         ← FastAPI application (Python)
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── write_leads.py               ← Dev utility
│   ├── alembic/versions/            ← 17 migration files
│   └── app/
│       ├── main.py                  ← FastAPI entry + router registration
│       ├── core/                    ← Config, JWT, auth, utilities
│       ├── database/session.py
│       ├── models/                  ← SQLAlchemy ORM (13 model files)
│       └── modules/
│           ├── platform/
│           ├── employee_auth/
│           ├── customers/
│           ├── leads/
│           ├── orders/
│           ├── products/
│           ├── reporting/
│           ├── labels/
│           ├── meta/
│           ├── vendors/
│           ├── purchases/
│           ├── inventory/
│           ├── invoices/
│           └── wa_engine/           ← WhatsApp Engine v2 (Phase 12)
│               ├── schemas.py
│               ├── service.py       ← Business logic (~500 lines)
│               ├── router.py        ← 25 routes under /api/wa/*
│               └── providers/
│                   ├── base.py      ← Abstract provider interface
│                   ├── wabis.py     ← WABIS / BotSailor
│                   └── meta.py      ← Meta Cloud API
│
├── frontend/                        ← Static HTML + CSS
│   ├── ds.css                       ← M3 Design System
│   ├── index.html
│   ├── leads.html
│   ├── customers.html
│   ├── orders.html
│   ├── products.html
│   ├── vendors.html
│   ├── marketing.html               ← Audience, Campaigns, WA Inbox, Settings
│   ├── platform-login.html / platform-admin.html
│   └── tenant-login.html / tenant-admin.html
│
├── scripts/                         ← Standalone utility scripts
│   ├── seed_customers.py
│   └── check_products.py
│
├── backend/scripts/
│   ├── seed_superadmin.py
│   └── audit_phase2.py
│
├── tests/                           ← API test scripts (run against live server)
│   ├── test_leads.py / test_orders.py / test_products.py
│   ├── test_customers.py / test_inventory.py / test_invoices.py
│   ├── test_labels.py / test_meta.py / test_purchases.py
│   ├── test_reporting.py / test_vendors.py
│
├── backups/
│   ├── miguel_backup_20260220_erp.dump
│   └── phase2_backup.sql
│
├── deploy/nginx/miguel              ← Nginx site config
│
└── docs/
    ├── whatsapp/                    ← WA Engine v2 docs
    ├── marketing/                   ← Marketing module design
    ├── leads/                       ← Leads redesign docs
    ├── phase1/                      ← Phase 1 delivery docs
    ├── errors/                      ← Error code system docs
    ├── parser/                      ← Address parser V3 docs
    └── general/                     ← General dev notes + credentials (Pass file)
```

---

## 🏗️ Architecture

```
Platform (SuperAdmin)
    │ POST /platform/login → JWT type="platform"
    ▼
Tenant Layer  (Company → tenants table, UUID primary key)
    │ POST /tenant/login (slug at login only)
    ▼
Employee Layer  (JWT type="tenant", roles below)
    │
    ├── admin         Full access
    ├── sales         Leads, customers, orders
    ├── marketing     Read + WA blasts + campaigns
    ├── support       Read + log activities
    └── operations    Orders, products, ERP
    │
    ▼
Business Modules  (all filtered by tenant_id)
    ├── Customers · Leads · Orders · Products · Reporting
    ├── ERP: Vendors → Purchase Orders → Inventory → GST Invoices
    ├── Marketing: Audience · Campaigns · Analytics · Email Blast
    └── WA Engine v2: Settings · Subscribers · Conversations
                      Messages · Statuses · Postback Rules
                      Campaign Types · Campaigns
```

---

## 💬 WhatsApp Engine v2 (Phase 12)

### Providers Supported

| Provider | How it works |
|----------|-------------|
| **WABIS / BotSailor** | Outbound: POST JSON to Webhook Workflow URL. Inbound: WABIS fires POST to `/api/wa/inbound/{tenant_id}` |
| **Meta Cloud API** | Standard Graph API. Webhook: GET (hub.challenge) + POST (messages) to same inbound URL |

### Database Tables

| Table | Purpose |
|-------|---------|
| `wa_settings` | Per-tenant provider config (encrypted tokens) |
| `wa_subscribers` | WhatsApp contacts |
| `wa_conversations` | One per subscriber |
| `wa_messages` | Inbound + outbound messages |
| `wa_status` | WA-specific status per subscriber |
| `wa_status_history` | Full audit trail |
| `wa_postback_rules` | Auto-actions on WABIS button press |
| `wa_campaign_types` | Reusable templates with Workflow URLs |
| `wa_campaigns` | Campaign runs |
| `wa_campaign_recipients` | Per-recipient delivery tracking |

### WABIS → CRM Lead Sync

When a WABIS webhook is received (`/api/wa/inbound/{tenant_id}`), the engine automatically:

1. **Creates or updates a Lead** if the phone number matches / doesn't exist
2. **Merges WABIS labels** into `Lead.wabis_labels` (accumulated, not replaced)
3. **Sets source** to `whatsapp` and status to `new_lead`
4. **Links subscriber to lead** via `wa_subscribers.lead_id`

**WABIS webhook JSON:**
```json
{
  "subscriber_id": "919447480687-43011",
  "first_name": "Sajitha V V",
  "chat_id": "919447480687",
  "label_names": "Interested,Price_checked,Address_checked",
  "postbackid": "c9EyF70CGyzUFv0",
  "whatsapp_bot_username": "+91 88482 65849"
}
```

**What happens:**
- Subscriber created/updated in `wa_subscribers` table
- Labels merged: `["Interested", "Price_checked", "Address_checked"]`
- Postback ID stored: `"c9EyF70CGyzUFv0"`
- Lead created in `leads` table with phone `919447480687`
- Lead labels set to same array
- Subscriber linked to lead: `wa_subscribers.lead_id = leads.id`

**Frontend (Audience tab):**
- All WABIS contacts appear in "👥 All Contacts" sub-tab
- New "🏷 Labels" sub-tab shows all WABIS labels as cards
- Click a card to see subscribers with that label
- Edit labels directly from the table cell (blue chips)
- Labels can be added/removed per subscriber
- **Blast by Label** button sends WhatsApp to all subscribers with selected label

### 25 API Routes (`/api/wa/*`)

| Method | Path | Description |
|--------|------|-------------|
| GET/POST | `/settings` | Load / save provider config |
| POST | `/settings/test-connection` | Ping the provider |
| GET | `/settings/webhook-url` | Get webhook URL + secret |
| GET/POST | `/postback-rules` | List / create |
| PUT/DELETE | `/postback-rules/{id}` | Update / delete |
| GET/POST | `/campaign-types` | List / create |
| PUT/DELETE | `/campaign-types/{id}` | Update / delete |
| GET | `/subscribers` | List subscribers |
| GET | `/subscribers/{id}` | Subscriber detail |
| GET | `/conversations` | List all conversations |
| GET | `/conversations/{id}/messages` | Chat history |
| POST | `/conversations/{id}/send` | Send message |
| GET | `/statuses` | List WA statuses |
| PUT | `/statuses/{subscriber_id}` | Update WA status |
| GET/POST | `/campaigns` | List / create campaigns |
| POST | `/campaigns/{id}/start` | Launch campaign |
| GET | `/campaigns/{id}/report` | Delivery report |
| GET/POST | `/inbound/{tenant_id}` | Webhook receiver (hub.challenge + messages) |

---

## 🔐 Authentication

| Domain | Endpoint | JWT type | Dependency |
|--------|----------|----------|------------|
| Platform | `POST /platform/login` | `platform` | `get_current_platform_user()` |
| Employee | `POST /tenant/login` | `tenant` | `get_current_tenant_user()` |

Route guard: `require_roles(RoleEnum.admin, RoleEnum.sales)` from `app.core.auth.tenant`  
`RoleEnum` location: `app.models.employee`

---

## 🗄️ Database

```
Host: localhost:5432 (inside db container)
DB:   miguel_db
User: miguel_user / miguel_password
```

### Migration History (17 migrations)

| Revision | Description |
|----------|-------------|
| `d95234c14e2b` | Initial schema |
| `3d6a6d828e8c` | Add `support` role |
| `d7e8df45f5f5` | Customers module |
| `2938e3343f25` | Leads module |
| `e81d578ab548` | Orders module |
| `c9e214abce04` | Products module |
| `ab471d322171` | `printed_count` on orders |
| `0bc432954832` | Meta Ads module |
| `f3e4a5b6c7d8` | Leads redesign P1 columns |
| `g4f5b6c7d8e9` | `lead_messages` table |
| `h5g6c7d8e9f0` | WA dedup index |
| `i6h7i8j9k0l1` | Merge migration |
| `j7k8l9m0n1o2` | Lead status enum values |
| `k8l9m0n1o2p3` | Simplify lead status redesign |
| `l9m0n1o2p3q4` | Phase 5 lead-order integration |
| `m0n1o2p3q4r5` | Fix `lead_activities` columns |
| `n1o2p3q4r5s6` | **WA Engine v2** — 10 `wa_*` tables + 8 enums |

---

## 🌐 Key API Endpoints

### Leads (`/api/leads/*`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List with priority sort + filters |
| POST | `/` | Create lead |
| GET | `/{id}` | Detail + activities |
| PATCH | `/{id}` | Update |
| POST | `/{id}/contacted` | Contacted popup (save/remind/lost/create_order) |
| POST | `/{id}/success_won` | Convert → Order |
| GET | `/reminders/today` | Today's REMIND_LATER leads |
| GET | `/lost_leads/list` | Lost leads |
| GET/POST | `/{id}/messages` | WhatsApp chat |

### Orders, Products, ERP
> Full endpoint tables in old README are preserved in `docs/phase1/PHASE1_FILE_REFERENCE.md`

---

## 🔑 Role Permissions

| Action | admin | sales | marketing | support | operations |
|--------|:-----:|:-----:|:---------:|:-------:|:----------:|
| Manage employees | ✅ | | | | |
| Create customer / lead | ✅ | ✅ | | | |
| Update customer | ✅ | ✅ | ✅ | | |
| Log lead activity | ✅ | ✅ | | ✅ | |
| Convert lead → Order | ✅ | ✅ | | | |
| Create / update order | ✅ | ✅ | | | ✅ |
| Create / update product | ✅ | | | | ✅ |
| Generate PDF labels | ✅ | | | | ✅ |
| Vendors / Purchase Orders | ✅ | | | | ✅ |
| Manual stock adjust | ✅ | | | | ✅ |
| Finalize GST invoice | ✅ | | | | ✅ |
| WA Engine settings | ✅ | | | | |
| View all (read-only) | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 🚀 Common Commands

```bash
# Start all services
cd /opt/miguel && docker compose up -d

# Restart backend after code change
docker compose restart backend

# View logs
docker compose logs -f backend

# Run migrations
docker exec -e PYTHONPATH=/app miguel_backend alembic upgrade head

# Open DB shell
docker exec -it miguel_db psql -U miguel_user -d miguel_db

# Seed SuperAdmin
docker exec -e PYTHONPATH=/app miguel_backend python scripts/seed_superadmin.py
```

---

## 🌍 Access

| Resource | URL |
|----------|-----|
| Server IP | `172.232.118.208` |
| API | `http://172.232.118.208:8000` |
| Swagger | `http://172.232.118.208:8000/docs` |
| Frontend | `http://172.232.118.208` |

---

## 👤 Credentials

| Role | Email | Password |
|------|-------|----------|
| SuperAdmin | admin@platform.com | Admin@123 |
| Tenant Admin | purelevenexim@gmail.com | HgI*B5usv750Qh |
| Tenant slug | `purelevenexim` | — |
| Tenant ID | `3f7160e0-c6c3-4feb-bfff-b4eaed704110` | — |

> ⚠️ Full credentials in `docs/general/Pass`  
> ⚠️ Change all passwords before production!

---

## 📦 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI 0.129 |
| Database | PostgreSQL 15 |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic 1.18 |
| Auth | JWT (python-jose) + bcrypt |
| Validation | Pydantic v2 |
| HTTP Client | httpx 0.28 |
| Container | Docker + Docker Compose |
| Server | Uvicorn |
| Hosting | Linode (172.232.118.208) |

---

## � Marketing Module — Audience Tab (Latest)

### ✨ Latest Features (Feb 23, 2026)

#### 1. **Labels Sub-Tab** — Organize by WABIS Labels
- **Two sub-tabs**: "👥 All Contacts" (existing) + "🏷 Labels" (NEW)
- Label cards show count of subscribers with that label
- Click a card → see list of subscribers with that label
- Search labels by name
- "Blast this label" → sends WA message to all subscribers with that label

#### 2. **Labels Column** — In All Contacts Table
- Shows all labels as green chips next to contact name
- Click chips to open label editor modal
- Manually add/remove labels for any WABIS contact
- Labels MERGE across WABIS triggers (never replace)

#### 3. **WABIS Payload Parsing** (Feb 22 fix)
All WABIS subscribers now correctly parse:
```json
{
  "chat_id": "919447480687",           → phone_number
  "first_name": "Sajitha. V. V.",      → name
  "label_names": "Interested,Checked",  → wabis_labels (array)
  "postbackid": "c9EyF70CGyzUFv0"      → last_postback_id + postback_ids[]
}
```

#### 4. **Postback ID Tracking**
- `last_postback_id`: Most recent postback (string)
- `postback_ids`: ALL postbacks ever seen (JSONB array, accumulated)
- Used for: Send WhatsApp replies back to WABIS

#### 5. **WA Status Improvements**
- `WA Status` codes removed from sidebar filter
- All WABIS contacts show as "💬 New Lead" (no status pipeline codes)
- `WA Status` created only on first contact → never reset on repeat triggers
- Column shows: "💬 New Lead" (WABIS) | "👤 Customer" (converted) | "Lead Status" (plain leads)

### Backend Changes

**Model**: `WaSubscriber` (in `app/models/wa_engine.py`)
```python
wabis_labels: JSONB = Column(JSON, default=list)              # Merged labels from all triggers
postback_ids: JSONB = Column(JSON, default=list)              # All postback IDs (accumulated)
last_postback_id: str = Column(String, nullable=True)         # Most recent postback
```

**Migration**: `t7u8v9w0x1y2_add_postback_ids_to_wa_subscribers`
- Adds `postback_ids` column to `wa_subscribers` table

**Service**: `upsert_subscriber()` (in `app/modules/wa_engine/service.py`)
```python
# Labels: UNION (merge across multiple triggers)
if inbound.labels:
    existing = list(row.wabis_labels or [])
    merged = existing + [l for l in inbound.labels if l not in existing]
    row.wabis_labels = merged

# Postbacks: ACCUMULATE (keep all)
if inbound.postback_id:
    row.last_postback_id = inbound.postback_id
    existing_pbs = list(row.postback_ids or [])
    if inbound.postback_id not in existing_pbs:
        existing_pbs.append(inbound.postback_id)
    row.postback_ids = existing_pbs
```

**Router**: `PATCH /api/wa/subscribers/{sub_id}/labels`
```python
@router.patch("/subscribers/{sub_id}/labels")
def update_subscriber_labels(sub_id: uuid.UUID, body: Dict[str, Any], ...):
    # body: { "labels": ["Label1", "Label2", ...] }
    # Sanitizes: trim, deduplicate, drop empties
    row.wabis_labels = cleaned_labels
    db.commit()
    return {"id": str(row.id), "labels": row.wabis_labels}
```

### Frontend Changes

**HTML** (`marketing.html` lines 615-810)
- Audience tab has 2 sub-tabs with `.aud-sub-tabs` / `.aud-sub-tab` classes
- `#sec-aud-contacts` → existing audience table layout
- `#sec-aud-labels` → new label board + subscriber list

**CSS** (lines 142-168, 212-220, 225-243)
- `.aud-sub-tabs`, `.aud-sub-tab`, `.aud-sub-tab.active`
- `.lbl-board`, `.lbl-board-card`, `.lbl-card-name`, `.lbl-card-count`, `.lbl-card-sub`
- `.lbl-chip`, `.lbl-cell`, `.lbl-td`
- `#lblModal`, `.lbl-box`, `.lbl-edit-chip`

**JavaScript** (lines 1880-2010)
```javascript
// Sub-tab state
let _lblBoardData = [];      // [{label, count, subscribers:[]}]
let _lblActiveLabel = null;  // currently selected label
let _lblSelectedIds = new Set();

// Sub-tab functions
function switchAudSub(sub)           // Toggle sub-tabs
function loadLabelBoard()            // Fetch all subs, aggregate labels
function renderLabelBoard()          // Filter & display label cards
function showLblSubscribers(label)   // Show subscribers for clicked label
function clearLblSelection()         // Back button
function toggleLblRow(id, checked)   // Checkbox handler
function toggleLblSelectAll(checked) // Select-all checkbox
function blastByLabel()              // Add selected subs to blast
```

**Label Editor Modal** (lines 1462-1490, 2345-2410)
```javascript
let _lblSubId = null;
let _lblCurrent = [];

function editLabels(subId, cellEl)   // Open modal
function renderLblChips()            // Show current labels as chips
function removeLbl(i)                // Remove label from current
function addLblChip()                // Add new label from input
function saveLbls()                  // PATCH /api/wa/subscribers/{id}/labels
function closeLblModal()             // Close modal
```

### Workflow

1. **WABIS sends webhook** → `/api/wa/inbound/{tenant_id}`
2. **Parser extracts** `chat_id` → phone, `label_names` → labels, `postbackid` → postback
3. **upsert_subscriber()** → labels MERGE, postbacks ACCUMULATE
4. **Frontend loads audience** → fetches `/api/wa/subscribers/as-leads/list`
5. **All Contacts tab** → shows WABIS rows with label chips
6. **Click chip** → opens label editor modal
7. **Edit labels** → POST PATCH `/api/wa/subscribers/{id}/labels`
8. **Labels tab** → aggregates all labels, shows cards with subscriber counts
9. **Click card** → shows subscribers with that label
10. **Blast** → adds all label subscribers to selection → opens WA blast modal

### Testing Checklist ✅

- [x] WABIS parser correctly handles actual field names
- [x] Labels merge (union) across multiple WABIS triggers
- [x] Postback IDs accumulate (never reset)
- [x] WA Status created on first contact, never reset on repeat triggers
- [x] Label editor modal opens/closes correctly
- [x] Label save updates both local state and backend
- [x] Label filter works in All Contacts sidebar
- [x] Labels sub-tab loads all distinct labels
- [x] Label card click shows subscriber list
- [x] Blast by label pre-selects all subscribers

---

## �🛠️ Dev Notes

- VS Code lint errors on imports = **false positives** (packages are inside Docker)
- PostgreSQL enum changes are NOT auto-detected by Alembic — write `ALTER TYPE` manually
- Migration enum pattern: use `sa.String()` in `op.create_table`, then `ALTER COLUMN TYPE` after (avoid `sa.Enum()` with `create_type=False` — still fires `_on_table_create` event)
- Always use `-e PYTHONPATH=/app` when running alembic/scripts inside Docker
- JWT type for employees = `"tenant"` (not `"employee"`)
- `RoleEnum` is in `app.models.employee` — not `app.models.base`
- **ERP**: `record_movement()` is the ONLY allowed stock write path
- **ERP**: Invoice `finalized` = immutable, no updates/cancellations
- **ERP**: GST — same state → CGST+SGST; different state → IGST
- **WA Engine**: WA status is separate from Lead.status — never cross-write
- **WA Engine**: `webhook_secret` is auto-generated UUID on first save
- **Leads pipeline**: `order_intent:'confirmed'` + `lead_id` in `POST /api/orders/` → auto-creates customer, links order, archives lead
- **Leads priority sort**: Remind Today (0) → Remind Overdue (1) → Created (2) → New Lead (3) → Contacted (4) → Won (5) → Lost (6)

---

## ⏳ Roadmap

| # | Feature | Notes |
|---|---------|-------|
| 1 | WA Campaign Launch UI | Launch from `marketing.html` Campaigns tab |
| 2 | Lead Scoring | Auto-score by activity, source, engagement |
| 3 | SaaS Billing | Subscription tiers, usage limits |

---

*Last updated: February 23, 2026 — Phase 12 (WA Engine v2) complete.*
- *WABIS label parsing + label merge + postback accumulation*
- *Audience tab has Labels sub-tab (label cards, subscriber filtering, editor modal)*
- *All WABIS contacts show as "New Lead" (WA status codes removed)*
- *WABIS webhook creates/updates Lead records in CRM*
- *Labels from WABIS merged into Lead.wabis_labels (accumulated across all triggers)*
