# 🎯 Production System Overview - Miguel CRM Platform
**Last Updated:** February 26, 2026  
**Environment:** Production (172.232.118.208)  
**Status:** 🟢 Live & Fully Operational

---

## 📋 Executive Summary

**Miguel** is a **multi-tenant SaaS CRM platform** designed for Indian e-commerce businesses and small companies. It integrates order management, logistics tracking, WhatsApp automation, and financial reporting with Shopify stores and delivery partners.

**Key Metrics:**
- **Architecture:** FastAPI backend + Vanilla JS frontend + PostgreSQL + Nginx + Docker
- **Deployment:** Docker Compose with 3 containers (db, backend, frontend)
- **Current Status:** 100% operational with active background workers
- **Last Session:** February 26, 2026 - Draft Order Edit Feature deployed
- **Uptime:** Running since deployment (container health: all green)

---

## 🏗️ Architecture Overview

### Tech Stack
```
Frontend:      HTML5 + CSS3 + Vanilla JavaScript (no frameworks)
Backend:       FastAPI 0.129 + SQLAlchemy 2.0 + Alembic migrations
Database:      PostgreSQL 15 with UUID primary keys
Server:        Nginx (reverse proxy + static file serving)
Containerization: Docker Compose
Message Queue: Background asyncio workers (no separate queue needed)
```

### Infrastructure
```
Server IP:     172.232.118.208
Web Port:      80 (HTTP frontend)
API Port:      8000 (Backend API)
DB Port:       5432 (Internal only)
Domain:        Direct IP access (no custom domain)
Certificates:  Configurable via docker-compose.yml
```

### Container Services
```yaml
pureleven_db       → PostgreSQL 15 database
pureleven_backend  → FastAPI uvicorn server (0.0.0.0:8000)
pureleven_frontend → Nginx (0.0.0.0:80 & 0.0.0.0:443)
```

---

## 🔑 Key Features (Current Implementation)

### 1. **Multi-Tenant Architecture** ✅
- Tenant isolation via `tenant_id` foreign key on all tables
- Each company/organization completely isolated
- Admin can create/delete employees per tenant
- Role-based access control (admin, sales, marketing, operations, support)

### 2. **Order Management** ✅
- Manual order creation (CSV import for India Post, Delhivery, Blue Dart)
- Shopify store integration (auto-sync orders from store)
- Order status tracking (draft → processing → shipped → out for delivery → delivered)
- Payment status tracking (pending → partial → paid)
- Draft order editing (new Feb 26, 2026)
  - Edit order details before tracking is assigned
  - Auto-calculate payment status based on amount paid
  - Prevents editing once tracking assigned or order delivered

### 3. **Logistics Integration** ✅
- **Shopify Stores:** Store management, order sync, fulfillment
- **Delivery Partners:** Delhivery, Blue Dart, DTDC, India Post, Amazon
- **Shipping Config:** Per-tenant partner API credentials (encrypted storage)
- **Tracking Sync:** Background worker syncs tracking every 15 minutes
- **Risk Assessment:** 4-factor scoring system (customer history, RTO risk, order value, COD flag)
- **India Post Excel Upload:** Bulk tracking number upload with column auto-detection

### 4. **Notification System** ✅
- WhatsApp Business API integration (2-way messaging)
- Auto-notifications: Order confirmed, shipped, out for delivery, delivered
- COD confirmation codes (6-digit, 30-min expiry)
- Non-delivery report (NDR) tracking and alerts
- Activity logging for all notifications (audit trail)

### 5. **Financial Reporting** ✅
- Profit & Loss dashboard (revenue, COGS, expenses, net profit)
- GST/Tax compliance tracking
- Vendor management (suppliers)
- Purchase order tracking
- Inventory management
- Invoice generation

### 6. **WhatsApp Engine v2** ✅ (Latest - Feb 23)
- WABIS (WhatsApp Business Integration Service) subscriber support
- Label/audience management for marketing campaigns
- Postback ID tracking for reply routing
- Bulk message sending
- Contact synchronization

### 7. **CRM Core Modules** ✅
- **Leads:** Lead capture, status tracking, conversion to customer
- **Customers:** Customer database, delivery history, RTO scores, blacklist management
- **Products:** Product catalog, pricing, categories
- **Vendors:** Supplier management, payment tracking
- **Marketing:** Campaign management, audience segmentation, WhatsApp integration

---

## 🔄 Recent Changes & Session History

### Latest Session: February 26, 2026 ✅ **DEPLOYED**
**Feature:** Draft Order Editing

**Changes:**
1. **Frontend (orders.html):** ~250 lines modified
   - Added edit mode detection: orders without tracking are fully editable
   - New `saveOrderEdit()` function to handle comprehensive order updates
   - Conditional input rendering (editable when draft, read-only when tracked/delivered)
   - Save/Cancel buttons shown in edit mode

2. **Backend Schema (orders/schemas.py):** +2 fields
   - Added `amount_paid` and `amount_due` to `OrderUpdate` model
   - Allows PATCH to accept manual payment amount edits

3. **Backend Logic (orders/service.py):** +18 lines
   - Auto-inference of payment status from amount_paid
   - Validation prevents negative amounts
   - Full backward compatibility

**Impact:**
- Orders without tracking: Fully editable (all fields)
- Orders with tracking: Read-only (prevents modifications)
- Delivered orders: Read-only (prevents modifications)
- Auto-calculation: When amount_paid updated, payment_status auto-infers

---

### Previous Session: February 25, 2026 ✅ **DEPLOYED**
**Features:** Multiple Critical Fixes

1. **Auto Pay Status on Delivery**
   - When order status → "Delivered", payment status → "Paid"
   - Applies to all payment methods (COD, UPI, Bank, Cheque)
   - Reasoning: Delivery implies payment was collected

2. **Order Creation Bug Fix**
   - Resolved: Order creation returning 500 error
   - Root cause: Missing `PaymentMethod` import in service.py
   - Status: Fixed and deployed

3. **Status/Pay Status Dropdowns**
   - Fixed: Dropdowns were blocked on terminal orders
   - Now: Editable on all order states (draft, processing, shipped, etc.)
   - Special rule: Locked only when delivered

4. **India Post Excel Upload Enhancement**
   - Fixed: 400 error on hyphenated column headers
   - Implemented: Content-based column detection (fallback scanning)
   - Support: Multiple header formats and layouts
   - Debug logging: Added for troubleshooting uploads

---

## 🗄️ Database Schema (Core Tables)

### Identity Tables
```
tenants                 → Organizations/Companies
employees               → Staff (with roles)
users                   → Platform super-admins
```

### Order & Logistics Tables
```
orders                  → Main order data (manual + Shopify)
shipping_info           → Tracking numbers, courier assignments
tracking_events         → Real-time tracking status history
shopify_orders          → Shopify order sync log
shipments               → Shipment metadata (from logistics)
```

### Financial Tables
```
invoices                → Generated invoices
purchases               → Vendor purchase orders
products                → Product catalog
inventory               → Stock levels
```

### Risk & Compliance Tables
```
customer_delivery_scores  → Per-customer delivery metrics
rto_zones                 → Pincode risk assessment
blacklisted_customers     → High-risk customers
order_risk_assessments    → Risk score per order
cod_transactions          → COD confirmation tracking
ndr_records               → Non-delivery reports
```

### CRM Tables
```
leads                   → Prospect pipeline
customers               → Customer master data
vendors                 → Supplier database
wa_engine_subscribers   → WABIS integration contacts
```

### Audit & Configuration Tables
```
activity_logs           → Complete audit trail (every API call)
shipping_config         → Encrypted credentials storage
                        (Shopify stores, Delivery partners, Notification channels)
notification_logs       → WhatsApp message delivery audit
```

---

## 🚀 Background Workers (Always Running)

### 1. **Tracking Sync Worker**
- **Runs:** Every 15 minutes (automatic)
- **Function:** Syncs tracking status from all logistics partners
- **Logic:**
  - Queries all active shipments across all tenants
  - Calls partner APIs for latest tracking
  - Updates status in database
  - Triggers event handlers (e.g., delivery → auto-mark paid)
  - Sends WhatsApp notifications on status change

### 2. **Shopify Sync Worker**
- **Runs:** Every 30 minutes (automatic)
- **Function:** Syncs new orders from Shopify stores
- **Logic:**
  - Queries Shopify Admin API for recent orders
  - Creates/updates orders in database
  - Associates with customer records
  - Triggers risk assessment and auto-shipment creation

### 3. **Customer Sync Worker**
- **Runs:** Every 30 minutes (automatic)
- **Function:** Syncs customer updates (WhatsApp, delivery scores)
- **Logic:**
  - Updates customer metadata from WhatsApp
  - Recalculates delivery scores
  - Updates RTO zone statistics
  - Auto-blacklists high-risk customers (RTO≥5 or NDR≥5)

### 4. **Activity Log Cleanup Scheduler**
- **Runs:** Daily at 2 AM UTC (automatic)
- **Function:** Removes old activity logs (>90 days)
- **Logic:**
  - Deletes old audit entries for performance
  - Keeps 90-day sliding window of activity
  - Per-tenant isolation maintained

---

## 🔐 Authentication & Authorization

### Tenant Employee Login
- **Endpoint:** POST `/api/employee-auth/login`
- **Credentials:** Email + Password
- **Token:** JWT (HS256, 24-hour expiry)
- **Roles:** admin, sales, marketing, operations, support
- **Scope:** Only see own tenant's data

### Platform Super-Admin Login
- **Endpoint:** POST `/platform/login`
- **Credentials:** Email + Password
- **Token:** JWT (separate token type)
- **Scope:** View all tenants, create/delete tenants

### Encryption
- **Method:** Fernet (symmetric encryption)
- **Key Source:** `ENCRYPTION_KEY` from `.env`
- **Encrypted Fields:**
  - Shopify: `api_access_token`, `api_client_secret`
  - Delivery Partners: `api_key`, `api_secret`
  - All credentials in `shipping_config` table

---

## 📊 Current API Endpoints (20+ Routers)

| Router | Base Path | Endpoints | Status |
|--------|-----------|-----------|--------|
| employee_auth | /api | login, logout, current user | ✅ |
| customers | /api/customers | CRUD, search, delivery scores | ✅ |
| leads | /api/leads | CRUD, conversion tracking | ✅ |
| orders | /api/orders | CRUD, status update, **edit (NEW)** | ✅ |
| products | /api/products | CRUD, inventory | ✅ |
| reporting | /api/reports | P&L, GST, analytics | ✅ |
| shipping_config | /api/config | Shopify stores, delivery partners | ✅ |
| shipments | /api/shipments | Tracking, fulfillment, webhooks | ✅ |
| whatsapp | /api/whatsapp | Message sending (legacy) | ✅ |
| wa_engine | /api/wa | WABIS integration, campaigns | ✅ |
| vendors | /api/vendors | Supplier CRUD | ✅ |
| purchases | /api/purchases | PO management | ✅ |
| inventory | /api/inventory | Stock tracking | ✅ |
| invoices | /api/invoices | Invoice generation | ✅ |
| gst | /api/gst | Tax compliance | ✅ |
| labels | /api/labels | PDF label generation | ✅ |
| logs | /platform/logs | Activity audit (super-admin only) | ✅ |
| meta | /api/meta | Meta webhook config | ✅ |
| platform | /platform | Tenant management, super-admin | ✅ |

---

## 🎯 User Access

### Test Credentials
```
Email:    purelevenexim@gmail.com
Password: wM01gkxGCNhJT!
Role:     Admin (tenant level)
```

### Access URLs
```
Frontend:      http://172.232.118.208/login
Tenant Admin:  http://172.232.118.208/tenant-admin
API Docs:      http://172.232.118.208:8000/docs
ReDoc:         http://172.232.118.208:8000/redoc
```

---

## 📁 Code Structure

```
/opt/pureleven/
├── backend/                          # FastAPI server
│   ├── app/
│   │   ├── main.py                   # FastAPI app, routers, startup
│   │   ├── core/                     # Utilities & background workers
│   │   │   ├── config.py             # Pydantic settings
│   │   │   ├── security.py           # JWT, password hashing
│   │   │   ├── auth/                 # Tenant & platform auth
│   │   │   ├── logger.py             # Activity logging
│   │   │   ├── tracking_worker.py    # 15-min sync
│   │   │   ├── shopify_sync_worker.py  # 30-min Shopify sync
│   │   │   ├── customer_sync_worker.py # 30-min customer sync
│   │   │   ├── notification_service.py # WhatsApp integration
│   │   │   ├── risk_engine.py        # Risk scoring
│   │   │   └── error_handlers.py     # Exception handling
│   │   ├── models/                   # SQLAlchemy ORM models
│   │   │   ├── tenant.py
│   │   │   ├── order.py
│   │   │   ├── customer.py
│   │   │   ├── shipping_config.py
│   │   │   ├── logistics.py
│   │   │   └── ... (15 total)
│   │   ├── modules/                  # Feature modules (router + service + schema)
│   │   │   ├── orders/               # Order CRUD & editing
│   │   │   ├── shipping_config/      # Shopify, delivery partners
│   │   │   ├── shipments/            # Tracking & fulfillment
│   │   │   ├── wa_engine/            # WhatsApp automation
│   │   │   └── ... (20 modules)
│   │   └── database/
│   │       └── session.py            # SQLAlchemy setup
│   ├── alembic/                      # Database migrations
│   └── requirements.txt
│
├── frontend/                         # Static files (Nginx)
│   ├── auth/                         # Login pages
│   │   ├── tenant-login.html
│   │   └── platform-login.html
│   ├── modules/                      # Main pages
│   │   ├── tenant-admin.html
│   │   └── wa-setup-guide.html
│   ├── pages/
│   │   └── index.html
│   ├── orders.html                   # Order management (edit new feature)
│   ├── leads.html
│   ├── customers.html
│   ├── products.html
│   ├── vendors.html
│   ├── purchases.html
│   ├── inventory.html
│   ├── invoices.html
│   ├── profit-loss.html
│   ├── gst.html
│   ├── marketing.html
│   └── styles/
│       └── ds.css                    # Design system
│
├── infra/
│   ├── nginx.conf                    # Reverse proxy, routing
│   └── README.md
│
├── docker-compose.yml                # 3 services
├── .env                              # Sensitive vars (ENCRYPTION_KEY, DB_PASSWORD)
├── .env.example                      # Template
└── docs/                             # Comprehensive documentation
```

---

## 🔧 Deployment & Operations

### Start Services
```bash
cd /opt/pureleven
docker compose up -d
```

### Stop Services
```bash
docker compose down
```

### Restart Backend (after code changes)
```bash
docker compose restart backend
```

### View Logs
```bash
docker logs pureleven_backend -f     # Backend logs
docker logs pureleven_frontend -f    # Nginx logs
docker logs pureleven_db -f          # Database logs
```

### Database Migrations
```bash
docker compose exec backend alembic upgrade head
```

### Apply Environment Variables
```bash
# Edit .env file
docker compose restart backend
```

---

## 🐛 Common Issues & Solutions

### Issue: Backend not responding (500 error)
**Solution:** Check logs with `docker logs pureleven_backend` and look for import errors

### Issue: Orders table showing errors
**Solution:** Verify ENCRYPTION_KEY is set in .env for credentials decryption

### Issue: Tracking sync not running
**Solution:** Check if worker started: `docker logs pureleven_backend | grep "tracking_worker"`

### Issue: WhatsApp notifications not sending
**Solution:** Verify WhatsApp API credentials in shipping_config table (must not be null)

### Issue: Port 80 in use
**Solution:** Stop system Nginx: `sudo systemctl stop nginx`

---

## 📚 Documentation Files

### Core Documentation
- **README.md** - Quick start & feature overview
- **CODEBASE_STRUCTURE.md** - Architecture deep-dive
- **PRODUCTION_SETUP.md** - Infrastructure & deployment
- **DOCUMENTATION_INDEX.md** - Navigation hub

### Recent Session Docs
- **DEPLOYMENT_COMPLETE_2026_02_26.txt** - Draft edit feature deployment
- **CHANGES_SUMMARY_2026_02_26.md** - Detailed code changes
- **DRAFT_ORDER_EDIT_FEATURE.md** - Technical implementation
- **DRAFT_ORDER_EDIT_VISUAL_GUIDE.md** - UI/UX flows

### Earlier Sessions
- **AUTO_PAY_STATUS_UPDATE_FIX.md** - Feb 25 delivery → paid logic
- **ORDERS_TABLE_FIX_SESSION_2026_02_25.md** - Bug fixes & xlsx upload
- **INDIA_POST_XLSX_UPLOAD_GUIDE.md** - User guide for tracking upload
- **SESSION_SUMMARY_2026_02_25.md** - Previous session overview

---

## ✅ Pre-Production Checklist

- [x] All services running and healthy
- [x] Database migrations applied
- [x] Encryption key configured
- [x] Backend API responding at port 8000
- [x] Frontend accessible at port 80
- [x] Background workers started (tracking, Shopify, customer sync)
- [x] Test login working with provided credentials
- [x] Recent features deployed (draft order editing)
- [x] No error alerts in logs
- [x] Docker compose configured for auto-restart

---

## 🎓 How to Proceed

### For Operations/Sales:
1. Read **README.md** - 5 minutes
2. Log in with test credentials
3. Create a test order and try the new editing feature
4. Upload India Post tracking via xlsx file

### For Backend Developers:
1. Read **CODEBASE_STRUCTURE.md** - 15 minutes
2. Check backend/app/modules structure
3. Review recent changes in CHANGES_SUMMARY_2026_02_26.md
4. Look at models/ for database schema

### For DevOps/SysAdmin:
1. Read **PRODUCTION_SETUP.md** - 5 minutes
2. Check container status: `docker ps`
3. Verify logs: `docker logs pureleven_backend`
4. Test connectivity: `curl http://localhost:8000/docs`

### For Project Managers:
1. Read this document - 10 minutes
2. Check DEPLOYMENT_COMPLETE_2026_02_26.txt for feature status
3. Review DOCUMENTATION_INDEX.md for complete feature list

---

## 📞 Key Contacts & Resources

- **Git Repository:** crm (owner: purelevenexim-ai, branch: main)
- **Last Commit:** Feb 26, 2026 - "Mask sensitive data and add .env.example + .gitignore"
- **Server IP:** 172.232.118.208
- **Database Backup:** /opt/pureleven/backups/ (latest: phase2_backup.sql)

---

**Generated:** February 26, 2026  
**Status:** ✅ Production Ready  
**Maintenance:** Active development (continuous improvements)
