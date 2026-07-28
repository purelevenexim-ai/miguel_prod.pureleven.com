# PureLevenExim CRM

**Version:** 2.4.0  
**Status:** ✅ Production Ready  
**Last Updated:** March 8, 2026 (Dashboard/P&L/Reporting Fixes + Orders Column Merging)  
**Production Server:** `root@172.105.48.142`  
**GitHub:** `purelevenexim-ai/crm`  
**📱 Mobile CSS v1.0 Status:** See `MOBILE_CSS_v1.0_STATUS.md` for comprehensive documentation of the unified mobile stylesheet (16 sections, 362 lines, all 15 pages covered, commit `c355878`)

---

## 🏗️ Architecture

| Layer | Stack | Container |
|---|---|---|
| Frontend | Vanilla HTML/CSS/JS | `pureleven_frontend` (nginx) |
| Backend | FastAPI + SQLAlchemy + Alembic | `pureleven_backend` (uvicorn :8000) |
| Database | PostgreSQL 15 | `pureleven_db` |
| Reverse Proxy | Nginx | host nginx on port 80 |

Multi-tenant SaaS — every DB row is scoped by `tenant_id`. Platform admin at `/platform-admin.html`.

---

## 🚀 Deploy to Production

**⚠️ REQUIRED: All pushes to `main` branch are protected by pre-deployment checks.**

### Setup (first time only)
```bash
bash scripts/init-hooks.sh
```
This installs git hooks that verify production safety before push.

### Deployment Process

**Option 1: Manual (recommended for single changes)**
```bash
# Local: commit and push (checks run automatically)
git add .
git commit -m "feat: description"
git push origin main

# Production server will auto-pull on webhook (if configured)
# OR manually:
ssh root@172.105.48.142 "cd /opt/pureleven && git pull && docker-compose -f config/docker-compose.prod.yml --env-file .env up -d --no-deps frontend"
```

**Option 2: Automated Script (recommended for multiple changes)**
```bash
bash scripts/deploy.sh
# This does: commit → push → pull on prod → recreate containers → verify
```

### ⚠️ CRITICAL: Container Restart Rules

**❌ NEVER use:**
```bash
docker restart pureleven_frontend  # Will crash!
docker restart pureleven_backend   # May break networking!
```

**✅ ALWAYS use:**
```bash
# Single container:
docker-compose -f config/docker-compose.prod.yml --env-file .env up -d --no-deps <service>

# Multiple containers:
docker-compose -f config/docker-compose.prod.yml --env-file .env up -d --build --force-recreate
```

**Why?** Direct `docker restart` can break Docker network DNS resolution, causing nginx to crash with `host not found in upstream "backend"`. The compose file uses `resolver 127.0.0.11` which requires proper network membership.

---

## 🔐 Pre-Deployment Checklist

Before every push to `main`, git hooks automatically verify:

1. **No uncommitted changes** — working tree must be clean
2. **Commit signatures** — all commits should be GPG signed (optional warning)
3. **No sensitive files** — `.env`, secrets, passwords, private keys cannot be pushed
4. **Docker files present** — `docker-compose.prod.yml`, `nginx-prod.conf`, `Dockerfile`
5. **Nginx config syntax** — validated with `nginx -t`
6. **Python syntax** — all `.py` files compile without errors
7. **Frontend validity** — HTML/CSS/JS balanced brackets (braces, backticks, parens, brackets)
8. **Commit format** — messages follow conventional commits (`feat:`, `fix:`, `docs:`, etc.)
9. **Database migrations** — tracked and documented
10. **Documentation** — README/CHANGELOG updated when code changes

**All checks must pass before push completes.**

To bypass (use with extreme caution):
```bash
git push --no-verify
```

---

## 📋 Deployment History

| Commit | Date | Changes | Status |
|---|---|---|---|
| (pending) | Mar 8, 2026 | Dashboard/P&L reporting fix: date filters, revenue accuracy, charts, orders column merging | 🔄 Staging |
| `3d0b2d4` | Mar 3, 2026 | Nginx dynamic DNS + docker-compose healthchecks + deploy script | ✅ Production |
| `05d87e5` | Mar 3, 2026 | Customer page fixes: restore print buttons, remove tiers, add row colors | ✅ Production |
| `0e95901` | Mar 2, 2026 | Orders/Customers redesign: auto-status, row coloring, bulk bar | ✅ Production |
| `35e8f1a` | Feb 27, 2026 | 195-test comprehensive test suite + validators | ✅ Production |

---

## 🚀 Deploy to Production

## 📦 Modules

| Module | Page | Backend |
|---|---|---|
| Orders | `orders.html` | `app/modules/orders/` |
| Customers | `customers.html` | `app/modules/customers/` |
| Leads | `leads.html` | `app/modules/leads/` |
| Invoices | `invoices.html` | `app/modules/invoices/` |
| GST / P&L | `gst.html` | `app/modules/gst/` |
| Products | `products.html` | `app/modules/products/` |
| Vendors | `vendors.html` | `app/modules/vendors/` |
| Marketing | `marketing.html` | `app/modules/whatsapp/` |
| WhatsApp Engine | `wa-setup-guide.html` | `app/modules/wa_engine/` |
| Platform Admin | `platform-admin.html` | `app/modules/platform/` |
| Reporting | (tenant-admin.html, profit-loss.html) | `app/modules/reporting/` |

---

## 💬 WhatsApp Chatbox (`frontend/modules/wa-chatbox.js`)

Shared slide-in panel injected into Orders, Customers, Leads, Invoices, GST pages.  
Opened via `WaChatbox.open({ phone, name, contextType, contextId })`.

**Tabs:**
- **Chat** — live history + send text (WABIS API or WhatsApp Web)
- **Templates** — approved WABIS templates → sent via Meta Cloud API (real templates, not plain text)
- **Quick** — quick reply shortcuts
- **File** — attach images/files
- **Docs** — auto-generates Tax Invoice + Shipping Label for order context
- **Config** — opens `/wa-setup-guide.html` for template configuration

**Template sending flow:**
1. `GET /api/wa/templates` → WABIS `/template/list`
2. Each template has `template_json` containing `access_token` (Meta WABA Bearer token)
3. Send: `POST https://graph.facebook.com/v18.0/{phone_number_id}/messages` with Bearer token
4. Fallback: WABIS plain text send if Meta API fails

**24h window:** `GET /api/wa/conversation-by-phone` returns `window_open: bool`. When `false`, textarea is disabled.

---

## 🗄️ Database

- **Migrations:** Alembic (`backend/alembic/`)
- **Run migration:** `docker exec pureleven_backend alembic upgrade head`

---

## ✅ Completed Features

- [x] Multi-tenant platform with per-tenant slug login
- [x] Orders — CRUD, status workflow, COD/Prepaid/Partial COD, Shopify sync
- [x] Customers — profiles, order history, notes
- [x] Leads pipeline — 6-stage workflow, reminders, label tags
- [x] Invoices — PDF generation, GST invoice, quick-PDF by order
- [x] GST / Profit & Loss reporting
- [x] Reporting — date-range filters on all endpoints, delivered vs order-book revenue tracking
- [x] Dashboard — revenue/outstanding KPIs, chart month labels, lead funnel, top products
- [x] Orders — source/age display, status enrichment, not-confirmed reason, ETA display
- [x] Products — inventory, SKU, pricing
- [x] Vendors — vendor directory (direct access, no sub-tabs)
- [x] Marketing — WhatsApp campaigns, bulk send, automation rules
- [x] WhatsApp Engine — WABIS API, inbound webhook, conversation tracking
- [x] Shipping labels — India Post + courier integration
- [x] Shopify multi-tenant isolation (per-tenant `store_url` uniqueness)
- [x] WA Chatbox — slide-in panel on all 5 main pages with 6 tabs
- [x] WA Template send — real Meta Cloud API (not plain text)
- [x] WA Docs tab — auto-generates invoice + label for order context
- [x] WA Config tab — link to template configuration page
- [x] Activity logs — error codes stored in DB, TTL-based cleanup
- [x] Favicon — real squirrel brand mascot PNG (`miguel_favicon.png`, 512×512, 108KB)
- [x] **Shared auth module** — `modules/auth.js` — unified logout, token helpers, 401 handling
- [x] **Session best practices** — no-cache headers on all HTML pages, versioned CSS/JS assets
- [x] **Logout function** — all 13 pages have proper `logout()` that clears all storage
- [x] **Mobile hamburger menu** — light pastel (#f5f5f5) on all 13 pages, quick navigation
- [x] **Mobile UX** — 46px form inputs, blue focus glow, enhanced topbar, 44px touch targets
- [x] **Order auto-status transitions** — tracking number auto-moves orders to "shipped" (confirmed→shipped, processing→shipped, packed→shipped)
- [x] **Order row coloring** — shipped=yellow, delivered=green, cancelled/returned=red fade on orders page
- [x] **Customer row coloring** — same color theme applied to customer table rows based on latest order status
- [x] **Priority order sorting** — confirmed/processing/packed orders float to top in orders table
- [x] **Customer page redesign** — combined Payment & Value column, combined Tracking & Status column, removed Actions column, fade inactive customers
- [x] **Bulk bar actions** — Print Labels + Print Invoices buttons in customer bulk selection bar
- [x] **Tier badges removed** — removed all customer tier labels (Gold/Diamond/Bronze/Green/Blue) from table, detail view, WA share

---

## 🔄 Recent update — Orders & Customers Redesign (March 7, 2026)

### Session 17: Feature Implementation (`0e95901`)

**Orders page (`orders.html`):**
- Added priority sorting — confirmed/processing/packed orders float to top
- Added row coloring — shipped=pastel yellow, delivered=pastel green, cancelled/returned=pastel red with fade
- Backend auto-transition: setting tracking number auto-moves order to "shipped" status

**Customers page (`customers.html`):**
- Restructured columns: combined Payment & Value, combined Tracking & Status, removed Actions column
- Added bulk bar with WhatsApp, Call, Edit, Activate/Deactivate, Delete buttons
- Fade inactive customers (opacity 0.45)
- Backend: added `order_status` field to customers with-orders API response

### Session 18: Bug Fixes (`current`)

| Bug | Root Cause | Fix |
|---|---|---|
| Missing Label/Invoice print buttons in bulk bar | Session 17 redesigned bulk bar and accidentally removed Print Labels & Print Invoices buttons | Added both buttons back — `bulkPrintLabels()` and `bulkPrintInvoices()` functions were intact |
| Tier badges (Blue, Green, etc.) still showing | Session 17 combined Payment & Value column but left tier badges in 6 places | Removed all 6 tier references: table row, detail meta, hero badges, detail info panel, detail orders, WA share |
| Orders with tracking still in "confirmed" status | Auto-transition code only fires on `update_order()`, not retroactively | Direct SQL fix on production DB: 4 orders (PRN-260302-011, PRN-260303-013, PRN-260303-015, PRN-260303-022) updated to "shipped" |
| No color theme in customer table | Row coloring was added to orders.html but not customers.html | Added `rowBg` logic using `order_status` with same color scheme as orders page |

**Files modified:** `frontend/customers.html`  
**Production DB:** 4 orders fixed via SQL UPDATE  
**Tests:** 26 API tests pass, HTML syntax validated

---

## 📋 Recent update — Invoices redesign (Feb 28, 2026)

Summary: the `invoices.html` page was redesigned for better desktop and mobile UX. Key points:

- Left-side scrollable customer list (mobile: slide-in panel) restored — customers are no longer a single top pill.
- Invoice view now renders per-order "invoice cards" with quick actions: Download (Tax / Proforma / Retail), Print, WhatsApp (opens `WaChatbox`), and Email (POST `/api/invoices/order/{id}/send-email`).
- Label view now lists all eligible orders with full FROM/TO preview cards, Print/Download/WhatsApp actions and a bulk "Print All Labels" action.
- Orders tab uses responsive card layout on mobile for easier reading and actions.

Files and artifacts:

- Page updated: `frontend/invoices.html`
- Backup (pre-change): `/opt/miguel/frontend/invoices.html.bak`
- Commit: `e5a6f6d` (pushed to `main`) — change deployed to production (`root@172.105.48.142`).

WhatsApp chatbox notes (integration points):

- `frontend/modules/wa-chatbox.js` exposes `WaChatbox.open({phone,name,contextType,contextId,invoiceUrl,labelUrl})` — invoices/labels can pass `invoiceUrl`/`labelUrl` to surface docs in the Docs tab.
- Chatbox supports preview of protected PDFs using `previewAuthPdf(url)` (fetch with Bearer token and open blob URL) and sending via WABIS or WhatsApp Web. It falls back to a text notification if direct media send isn't configured.

Deployment / rollback quick commands:

1. Push changes to repo (already done):

```bash
cd /opt/miguel
git add frontend/invoices.html
git commit -m "feat: invoices redesign — cards, WA/email share, label bulk print"
git push origin main
```

2. Pull on production (already executed):

```bash
ssh root@172.105.48.142 "cd /opt/pureleven && git pull origin main"
```

3. Rollback (restore backup):

```bash
cp /opt/miguel/frontend/invoices.html.bak /opt/miguel/frontend/invoices.html
cd /opt/miguel && git add frontend/invoices.html && git commit -m "revert: restore invoices backup" && git push origin main
ssh root@172.105.48.142 "cd /opt/pureleven && git pull origin main"
```

Verification notes:

- The WaChatbox Docs tab now auto-generates doc entries when opened from an order context (invoice URL or label generation).
- If PDF endpoints require auth, `previewAuthPdf` fetches the PDF using the current token and opens it as a blob URL so the chatbox can preview/provide links.


---

## �🔄 Pending / Future Work

- [ ] **WA Templates with variables** — templates using `{{1}}`, `{{2}}` need an input form before sending
- [ ] **Invoice PDF open-in-browser** — `/api/invoices/order/{id}/quick-pdf` needs JWT; `window.open()` won't pass Bearer token (needs blob fetch or signed URL)
- [ ] **WA media messages** — send actual PDF/image via WhatsApp (requires Meta Media API upload)
- [ ] **Shopify webhook live sync** — switch from polling to push webhooks for real-time order sync
- [ ] **Employee mobile app / PWA** — field staff access on mobile
- [ ] **Payment gateway integration** — Razorpay/PhonePe for online COD advance
- [ ] **SMS fallback** — order updates via SMS when WA 24h window is closed
- [ ] **Dashboard charts** — visual analytics for revenue, lead funnel, top products
- [ ] **Customer self-service portal** — order tracking link via WhatsApp

---

## 🐛 Bugs Fixed (Feb 27, 2026)

| Bug | Root Cause | Fix |
|---|---|---|
| `orders.html` → "Failed to load orders" | `esc()` called but only `escapeHtml()` exists in orders.html | Renamed to `escapeHtml()` in WA button onclick |
| `GET /api/reports/dashboard` → 500 | `LeadPipelineStatus.won` / `.lost` don't exist in enum | Changed to `.success_won` / `.lost_lead` |
| `GET /api/reports/dashboard` → 500 (employee report) | Same wrong enum | Fixed in employee performance query |
| Lead funnel endpoint 500 | Stage order used `new`, `qualified`, `proposal_sent`, `negotiation`, `on_hold` (all invalid) | Replaced with actual enum values: `created`, `new_lead`, `contacted`, `remind_later`, `success_won`, `lost_lead` |
| Meta lead gen inbound crash | `LeadPipelineStatus.new` doesn't exist | Changed to `.new_lead` |
| `log_activity() unexpected keyword 'error_code'` | `error_code` param missing from signature | Added param + store in `ActivityLog.error_code` column |

---

## 📁 Project Structure

```
/opt/miguel/
├── README_MAIN.md          ← You are here
├── backend/
│   ├── app/
│   │   ├── core/           # Auth, error handlers, logger, tenant utils
│   │   ├── models/         # SQLAlchemy models
│   │   ├── modules/        # Feature modules (orders, leads, wa_engine…)
│   │   └── main.py
│   ├── alembic/            # DB migrations
│   └── requirements.txt
├── frontend/
│   ├── *.html              # Page files
│   ├── ds.css              # Design system stylesheet (v20260228)
│   ├── miguel_favicon.png  # Brand favicon — 512×512 squirrel PNG
│   └── modules/
│       ├── auth.js         # Shared auth module (logout, guards, 401 handling)
│       ├── wa-chatbox.js   # Shared WA chatbox component
│       └── mobile-nav.js   # Mobile hamburger navigation
├── config/
│   ├── docker-compose.yml
│   └── docker-compose.prod.yml
├── infra/
│   └── nginx*.conf
└── scripts/
    └── pull_to_prod.sh
```
