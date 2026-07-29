# PureLevenExim CRM - Complete Documentation

**Version:** 2.4.0 | **Status:** Production Ready | **Last Updated:** June 20, 2026

> A multi-tenant SaaS CRM platform for e-commerce order management, WhatsApp automation, logistics, and business analytics.

---

## 📋 Table of Contents

1. [System Architecture](#-system-architecture)
2. [Tech Stack](#-tech-stack)
3. [Project Structure](#-project-structure)
4. [Module Documentation](#-module-documentation)
5. [Setup & Deployment](#-setup--deployment)
6. [API Reference](#-api-reference)
7. [Database Schema](#-database-schema)
8. [Integration Guides](#-integration-guides)
9. [Token Optimization Guide](#-token-optimization-guide)

---

## 🏗️ System Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────┐
│                   MULTI-TENANT SAAS                      │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  Tenant A    │  │  Tenant B    │  │  Tenant N    │   │
│  │  (Isolated)  │  │  (Isolated)  │  │  (Isolated)  │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
│         │                  │                  │            │
│         └──────────────────┴──────────────────┘            │
│                      │                                     │
│         ┌────────────▼────────────┐                       │
│         │   Nginx (Reverse Proxy) │                       │
│         │   Port 80/443           │                       │
│         └────────────┬────────────┘                       │
│                      │                                     │
│    ┌─────────────────┴─────────────────┐                 │
│    │                                   │                 │
│ ┌──▼──────────────────┐    ┌──────────▼──────┐          │
│ │  Frontend (Nginx)   │    │  Backend (Uvicorn)         │
│ │  Port 80/443        │    │  FastAPI        │          │
│ │  19 HTML Pages      │    │  Port 8000      │          │
│ │  Vanilla JS/CSS     │    │  29 API Routes  │          │
│ └─────────────────────┘    └────────┬────────┘          │
│                                    │                      │
│                       ┌────────────▼───────────┐          │
│                       │  PostgreSQL 15         │          │
│                       │  22 Models             │          │
│                       │  63 Migrations         │          │
│                       │  Multi-Tenant Scoping  │          │
│                       └────────────────────────┘          │
└─────────────────────────────────────────────────────────┘
```

### Key Design Principles

✅ **Multi-Tenant Isolation:** All data scoped by `tenant_id`  
✅ **Separation of Concerns:** Frontend (Vanilla JS) + Backend (FastAPI) + DB (PostgreSQL)  
✅ **Modularity:** 29 independent API modules, each with models → services → routers  
✅ **Stateless Design:** Horizontal scalability possible (just add more backend instances)  
✅ **Event-Driven:** Message automation, webhooks, background workers  

---

## 💻 Tech Stack

### Frontend
- **Framework:** Vanilla HTML/CSS/JavaScript (no framework overhead)
- **Server:** Nginx (reverse proxy + static file serving)
- **Styling:** CSS Variables + responsive design
- **Size:** 49K LOC across 19 pages

### Backend
- **Framework:** FastAPI (async Python web framework)
- **ORM:** SQLAlchemy 2.0 (async SQL toolkit)
- **Migrations:** Alembic (schema versioning)
- **Validation:** Pydantic (data validation + serialization)
- **Server:** Uvicorn (ASGI server)
- **Size:** 47K LOC across 29 modules

### Database
- **Engine:** PostgreSQL 15
- **Models:** 22 ORM entities
- **Migrations:** 63 versioned schema changes
- **Scaling:** Connection pooling ready

### DevOps
- **Containerization:** Docker Compose
- **Orchestration:** Docker networking
- **Health Checks:** Built-in liveness probes
- **Environments:** UAT + Production configs

### Integrations
- **E-Commerce:** Shopify (order sync, webhooks)
- **Messaging:** WhatsApp (WABIS API + Meta Cloud API)
- **Logistics:** India Post (tracking integration)
- **Payments:** COD, Prepaid, Partial modes
- **Reporting:** GST compliance, P&L analytics

---

## 📁 Project Structure

```
/opt/pureleven/
├── README_MAIN.md                          # Main deployment guide
├── README_FULL.md                          # This file
├── JOURNEY_IMPLEMENTATION_GUIDE.md         # Message automation design
├── .env                                    # Environment variables (secrets)
│
├── frontend/                               # Nginx-served vanilla JS
│   ├── *.html                              # 19 page templates
│   ├── ds.css                              # Design system (20260228)
│   ├── styles/
│   │   ├── adaptive.css                    # Responsive breakpoints
│   │   └── mobile.css                      # Mobile-specific styles
│   ├── modules/
│   │   ├── auth.js                         # Shared authentication
│   │   ├── wa-chatbox.js                   # WhatsApp UI component
│   │   └── mobile-nav.js                   # Mobile hamburger menu
│   └── miguel_favicon.png                  # Brand mascot (512x512)
│
├── backend/                                # FastAPI application
│   ├── requirements.txt                    # Python dependencies (39 packages)
│   ├── Dockerfile                          # Container build config
│   ├── app/
│   │   ├── main.py                         # FastAPI app entry point
│   │   ├── core/
│   │   │   ├── auth.py                     # JWT + OAuth logic
│   │   │   ├── database.py                 # SQLAlchemy setup
│   │   │   ├── logger.py                   # Structured logging
│   │   │   ├── security.py                 # Password hashing, tokens
│   │   │   └── tenant_context.py           # Multi-tenant isolation
│   │   │
│   │   ├── models/                         # SQLAlchemy ORM (22 entities)
│   │   │   ├── user.py, order.py, customer.py
│   │   │   ├── shipment.py, invoice.py
│   │   │   └── ... (19 more domain models)
│   │   │
│   │   └── modules/                        # 29 API domain modules
│   │       ├── orders/
│   │       │   ├── models.py               # Order ORM entity
│   │       │   ├── service.py              # Order business logic
│   │       │   └── router.py               # FastAPI endpoints
│   │       │
│   │       ├── message_automation/         # WhatsApp message engine
│   │       │   ├── journey.py              # 7-checkpoint message flow
│   │       │   ├── templates.py            # 8 message templates
│   │       │   ├── service.py              # 3,167 LOC scheduling logic
│   │       │   └── router.py               # API endpoints
│   │       │
│   │       ├── whatsapp/                   # WABIS + Meta Cloud API
│   │       │   ├── wabis_service.py        # WABIS integration
│   │       │   ├── meta_service.py         # Meta Cloud API
│   │       │   └── inbound_handler.py      # Webhook receiver
│   │       │
│   │       ├── shipments/                  # Logistics + tracking
│   │       ├── invoices/                   # PDF generation
│   │       ├── reporting/                  # P&L, GST, analytics
│   │       ├── customers/                  # CRM management
│   │       ├── leads/                      # Sales pipeline
│   │       ├── products/                   # Inventory
│   │       ├── vendors/                    # Supplier management
│   │       ├── purchases/                  # PO management
│   │       ├── platform/                   # Multi-tenant admin
│   │       ├── gst/                        # Tax compliance
│   │       ├── india_post/                 # Courier integration
│   │       └── (23 more modules...)        # See backend/app/modules
│   │
│   └── alembic/                            # Database migrations
│       └── versions/                       # 63 versioned schema files
│
├── config/
│   ├── docker-compose.yml                  # UAT configuration
│   └── docker-compose.prod.yml             # Production configuration
│
├── infra/
│   ├── nginx.conf                          # Development nginx config
│   ├── nginx-prod.conf                     # Production nginx config
│   └── ssl/                                # SSL certificates (production)
│
└── scripts/
    ├── init-hooks.sh                       # Git pre-deployment hooks
    └── deploy.sh                           # Automated deployment script
```

### Code Metrics

| Metric | Value |
|--------|-------|
| **Backend Python** | 47,322 LOC |
| **Frontend HTML/JS/CSS** | 49,070 LOC |
| **Total Code** | ~96K LOC |
| **Database Models** | 22 entities |
| **API Endpoints** | 29 routers |
| **Alembic Migrations** | 63 versions |
| **Dependencies** | 39 packages |
| **Pages** | 19 HTML templates |
| **Largest Service** | message_automation/service.py (3,167 LOC) |

---

## 📦 Module Documentation

### Core Business Domains

#### 1. **Orders Module** (3,007 LOC)
- **Purpose:** Order CRUD, status workflow, payment tracking
- **Models:** Order, OrderItem, OrderPayment
- **Features:**
  - Multi-status workflow: confirmed → processing → packed → shipped → delivered
  - COD/Prepaid/Partial COD payment modes
  - Shopify order sync integration
  - Auto-status transitions on tracking number add
  - Row coloring on orders page (shipped=yellow, delivered=green, cancelled=red)
- **Key Endpoints:**
  - `POST /api/orders` — Create order
  - `GET /api/orders?status=confirmed` — List filtered
  - `PUT /api/orders/{id}/status` — Update status
  - `POST /api/orders/{id}/shipment` — Link shipment

#### 2. **Message Automation Module** (5,200+ LOC)
- **Purpose:** WhatsApp customer journey with 7 checkpoints
- **Models:** MessageAutomationTask, AutomationTemplate
- **Features:**
  - 7 message checkpoints: order_created (0d), tracking_added (0d), tracking_update (3d), delivery_thanks (delivery), review_request (15d), product_promo (60d), website_reminder (90d)
  - Deduplication: one message per checkpoint per order/customer
  - Auto-cancellation: if order cancelled/deleted, all pending messages cancelled
  - 24-hour window optimization: ₹0.60 vs ₹0.75 rates
  - India Post tracking status integration
  - ✅ FIXED: No more recursive tracking messages
- **Key Endpoints:**
  - `POST /api/message-automation/schedule` — Manual schedule
  - `GET /api/message-automation/tasks?customer_id={id}` — Journey status
  - `PUT /api/message-automation/tasks/{id}/cancel` — Cancel pending

#### 3. **WhatsApp Engine Module**
- **Purpose:** WABIS API + Meta Cloud API integration
- **Providers:** WABIS (bot.wabis.in), Meta (graph.facebook.com)
- **Features:**
  - Inbound webhook handler (POST `/api/wa/webhook`)
  - Outbound template send (WABIS + Meta)
  - Conversation window tracking (24h)
  - Message history + state machine
  - File/media attachment support
- **Key Endpoints:**
  - `POST /api/wa/send` — Send message
  - `POST /api/wa/webhook` — Receive inbound
  - `GET /api/wa/conversations` — List chats
  - `GET /api/wa/conversation-by-phone/{phone}` — Get window status

#### 4. **Shipments & Logistics** (3,007 LOC)
- **Purpose:** Order fulfillment, tracking, label generation
- **Models:** Shipment, TrackingUpdate, Tariff
- **Features:**
  - India Post integration (AWB generation)
  - Dynamic tariff calculation (weight-based)
  - Auto-tracking updates from courier
  - PDF label generation (ReportLab)
  - Shipping address parsing (dual parsers: v1 + v2)
  - Bulk label printing
- **Key Endpoints:**
  - `POST /api/shipments` — Create shipment
  - `GET /api/shipments/{id}/tracking` — Real-time tracking
  - `GET /api/shipments/{id}/label-pdf` — Download label

#### 5. **Reporting & Analytics** (2,209 LOC)
- **Purpose:** Financial dashboards, P&L statements, GST compliance
- **Models:** ReportCache, PerformanceMetric
- **Features:**
  - P&L report with date-range filters
  - GST invoice generation
  - Revenue tracking (delivered vs. order-book)
  - Lead funnel analytics
  - Top products chart
  - Employee performance scorecards
  - Risk scoring engine
- **Key Endpoints:**
  - `GET /api/reports/profit-loss?date_from=&date_to=` — P&L statement
  - `GET /api/reports/dashboard` — KPI dashboard
  - `GET /api/reports/gst-register` — GST compliance

#### 6. **Customers Module**
- **Purpose:** CRM contact management, order history
- **Models:** Customer, CustomerNote, ActivityLog
- **Features:**
  - Customer segmentation (tier: Gold/Diamond/etc.)
  - Order history + payment status
  - Notes + tags
  - Bulk actions (WhatsApp, Call, Email)
  - Activity audit trail
  - Row coloring by latest order status
- **Key Endpoints:**
  - `POST /api/customers` — Create customer
  - `GET /api/customers/{id}/orders` — Order history
  - `GET /api/customers/{id}/activity-log` — Audit trail

#### 7. **Leads Module** (Sales Pipeline)
- **Purpose:** Prospect management, 6-stage funnel
- **Models:** Lead, LeadActivity, LeadLabel
- **Features:**
  - 6-stage pipeline: created → new_lead → contacted → remind_later → success_won → lost_lead
  - Tag-based segmentation
  - Auto-reminders (scheduled)
  - Activity tracking
  - Funnel analytics
- **Key Endpoints:**
  - `POST /api/leads` — Create lead
  - `PUT /api/leads/{id}/stage` — Move stage
  - `GET /api/reports/lead-funnel` — Funnel chart

#### 8. **Invoices & Billing**
- **Purpose:** Tax invoice + proforma invoice generation
- **Features:**
  - PDF generation (ReportLab)
  - GST-compliant invoicing
  - Multiple invoice types (Tax/Proforma/Retail)
  - Email send integration
  - Quick PDF download by order
- **Key Endpoints:**
  - `GET /api/invoices/order/{id}/quick-pdf` — Download
  - `POST /api/invoices/order/{id}/send-email` — Email

#### 9. **Products & Inventory**
- **Purpose:** Product catalog, SKU management, stock tracking
- **Models:** Product, Inventory, SKU
- **Features:**
  - Product variants (color, size)
  - Real-time inventory
  - Reorder point alerts
  - Pricing tiers
  - Supplier linking
- **Key Endpoints:**
  - `POST /api/products` — Create product
  - `GET /api/products/{id}/inventory` — Stock status
  - `PUT /api/products/{id}/inventory` — Adjust stock

#### 10. **Platform Administration**
- **Purpose:** Multi-tenant tenant management
- **Features:**
  - Tenant creation/deletion
  - Tenant user management
  - Feature access control (per-tenant)
  - WhatsApp settings per tenant
  - GST configuration
- **Key Endpoints:**
  - `POST /api/platform/tenants` — Create tenant
  - `GET /api/platform/tenants/{id}/settings` — Tenant config
  - `PUT /api/platform/tenants/{id}/whatsapp-settings` — Update WABIS creds

### Utility Modules

| Module | Purpose | LOC |
|--------|---------|-----|
| `address_parser.py` | Parse + geocode addresses | 43K |
| `address_parser_v2.py` | Improved address parsing | 21K |
| `label_pdf.py` | PDF label generation | 18K |
| `gst_engine.py` | GST tax calculation | 12K |
| `risk_engine.py` | Payment risk scoring | 8K |
| `notification_service.py` | Email + SMS fallback | 6K |
| `shopify_worker.py` | Async order sync | 5K |
| `tracking_worker.py` | Background tracking updates | 5K |

---

## 🚀 Setup & Deployment

### Prerequisites

```bash
# System requirements
- Docker 20.10+
- Docker Compose 2.0+
- Python 3.10+ (for local dev)
- PostgreSQL 15 (if running locally)
- Git
```

### Local Development

```bash
# 1. Clone repository
git clone git@github.com:purelevenexim-ai/crm.git
cd /opt/pureleven

# 2. Setup environment
cp .env.example .env
# Edit .env with local database credentials

# 3. Start containers
docker-compose -f config/docker-compose.yml up -d

# 4. Run migrations
docker exec pureleven_backend alembic upgrade head

# 5. Access application
# Frontend: http://localhost:80
# Backend API: http://localhost:8000/docs (Swagger UI)
# pgAdmin: http://localhost:5050 (if included in compose)
```

### Production Deployment

```bash
# 1. SSH to production server
ssh -i ~/.ssh/prod root@172.105.48.142

# 2. Pull latest code
cd /opt/pureleven
git pull origin main

# 3. Deploy using compose
docker-compose -p pureleven -f config/docker-compose.prod.yml \
  --env-file .env up -d --build

# 4. Verify health
docker-compose -p pureleven -f config/docker-compose.prod.yml \
  ps

# 5. Check logs
docker logs pureleven_backend -f
```

### Pre-Deployment Checklist

✅ All tests passing  
✅ No uncommitted changes  
✅ Migrations reviewed  
✅ `.env` secrets secured  
✅ Docker images built  
✅ Health checks pass  
✅ Database backups taken  

---

## 🔌 API Reference

### Authentication

All endpoints require JWT token (except `/login`):

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"pass"}'

# Response:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}

# Use token in subsequent requests:
curl -X GET http://localhost:8000/api/orders \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."
```

### Core Endpoints

#### Orders
```bash
# List all orders (with filtering)
GET /api/orders?status=confirmed&limit=50&offset=0

# Create new order
POST /api/orders
{
  "order_number": "ORD-001",
  "customer_id": "uuid",
  "items": [
    {"product_id": "uuid", "quantity": 2, "price": 500}
  ],
  "shipping_address": {...},
  "payment_mode": "prepaid"
}

# Get single order
GET /api/orders/{order_id}

# Update status
PUT /api/orders/{order_id}/status
{"status": "shipped", "notes": "Dispatched today"}

# Add tracking
POST /api/orders/{order_id}/tracking
{"tracking_number": "1234567890", "courier": "india_post"}
```

#### Customers
```bash
# List customers
GET /api/customers

# Create customer
POST /api/customers
{
  "phone": "9447744583",
  "email": "customer@example.com",
  "name": "Basil Thomas"
}

# Get customer + orders
GET /api/customers/{customer_id}?include=orders,activity_log
```

#### Message Automation
```bash
# Get customer's message journey
GET /api/message-automation/tasks?customer_id={id}

# Manually schedule message
POST /api/message-automation/schedule
{
  "customer_id": "uuid",
  "template_key": "review_request",
  "scheduled_at": "2026-07-05T10:00:00Z"
}

# Cancel pending message
PUT /api/message-automation/tasks/{task_id}/cancel
{"reason": "Customer opted out"}
```

#### WhatsApp
```bash
# Send message via WABIS
POST /api/wa/send
{
  "phone": "9447744583",
  "template_name": "pureleven_product_promo_60day",
  "template_variables": ["Customer Name"]
}

# Get conversation window status
GET /api/wa/conversation-by-phone/9447744583
# Returns: {"window_open": true/false, "expires_at": "..."}
```

---

## 🗄️ Database Schema

### Core Tables (22 entities)

#### **Users & Auth**
```sql
users          -- Platform users, roles, credentials
tenants        -- Multi-tenant accounts
tenant_users   -- User-to-tenant mapping
activity_logs  -- Audit trail
```

#### **E-Commerce**
```sql
orders         -- Order header
order_items    -- Order line items
customers      -- Customer profiles
products       -- Product catalog
inventory      -- Stock tracking
shopify_store  -- Shopify integration (1 per tenant)
shopify_sync_log -- Order sync history
```

#### **Fulfillment**
```sql
shipments      -- Shipment tracking
tracking_updates -- Tracking status history
shipment_labels -- PDF label metadata
tariffs        -- Shipping rate cards
```

#### **Invoicing**
```sql
invoices       -- Invoice header
invoice_lines  -- Line items
gst_register   -- GST compliance register
```

#### **WhatsApp & Messages**
```sql
wa_settings    -- WABIS + Meta credentials (per tenant)
message_automation_tasks -- Scheduled messages
message_templates -- Template definitions
inbound_messages -- Received messages (webhook log)
conversation_windows -- 24h conversation tracking
```

#### **Sales & CRM**
```sql
leads          -- Sales pipeline prospects
lead_activity  -- Lead interaction history
lead_labels    -- Custom tags
customers      -- Customer CRM record
customer_notes -- Notes + history
```

#### **Billing & Reporting**
```sql
invoices       -- Tax invoices
purchase_orders -- PO for vendors
vendors        -- Supplier directory
report_cache   -- Cached analytics (for performance)
```

### Key Design Patterns

✅ **Multi-Tenant Scoping:** All tables have `tenant_id` column (indexed)  
✅ **Audit Trail:** Most tables have `created_at`, `updated_at`, `created_by`  
✅ **Soft Deletes:** `deleted_at` column (not hard deletes)  
✅ **State Machines:** Enums for status fields (order.status, lead.stage)  
✅ **Foreign Keys:** Proper referential integrity  

---

## 🔗 Integration Guides

### Shopify Integration

**Setup:**
1. Go to `/platform-admin.html` → Select Tenant → Shopify Settings
2. Enter:
   - Shop URL: `myshop.myshopify.com`
   - API Key: (from Shopify Admin)
   - API Secret: (from Shopify Admin)
3. Click **Sync Orders**

**Flow:**
- Orders auto-sync from Shopify → PureLevenExim
- Status updates sent back to Shopify (marked as "fulfilled")
- Tracking number added → Shopify notified

### WhatsApp Integration

**WABIS Setup:**
1. Go to `whatsapp.html` → Settings
2. Enter WABIS credentials:
   - API Token: `from bot.wabis.in`
   - Phone Number ID: `from WABIS dashboard`
   - API Base URL: `https://admin.workpex.com`
3. Register 7 message templates on WABIS
4. Approve templates in WABIS dashboard
5. Test send

**Flow:**
- Message automation triggers at checkpoints
- WABIS sends WhatsApp message
- Inbound messages → webhook handler
- Conversation window tracked (24h)

### India Post Integration

**Setup:**
1. Configure in `/api/platform/tenants/{id}/shipping-config`
2. Enter India Post API credentials

**Flow:**
- Create shipment → AWB generated from India Post
- Tracking number auto-fetched
- Customer notified via WhatsApp
- Delivery confirmation updates order status

---

## ⚡ Token Optimization Guide

See [**Token Optimization Architecture**](#token-optimization-architecture-section) below.

---

# Token Optimization Architecture

## 🎯 Problem Statement

Current AI usage (Claude, GPT, etc.) consumes significant tokens per interaction:
- **Full codebase context:** 96K LOC requires loading entire project structure
- **Redundant context:** Same files re-read across multiple interactions
- **Verbose responses:** AI generates comprehensive explanations even for simple tasks
- **No caching:** Each conversation starts from scratch

**Goal:** Reduce token consumption by **95%** through smart caching, summarization, and context optimization.

---

## ✅ 95% Token Reduction Strategy

### 1. **Codebase Indexing System** (-70% tokens)

**Concept:** Pre-index entire codebase into structured metadata, not raw code.

#### What to Index

```
.claude/index/
├── codebase-structure.json          # File tree + metadata
├── module-summary.json              # Each module: purpose, LOC, key files
├── api-endpoints.json               # All endpoints + signatures
├── database-schema.json             # All tables + fields
├── key-files-registry.json          # Critical files + line numbers
└── integration-map.json             # External APIs + flow diagrams
```

#### Example: `codebase-structure.json`

```json
{
  "project": "PureLevenExim CRM",
  "version": "2.4.0",
  "root": "/opt/pureleven",
  "summary": "Multi-tenant SaaS CRM with WhatsApp automation",
  "metrics": {
    "total_loc": 96000,
    "backend_python": 47000,
    "frontend_html_js": 49000,
    "modules": 29,
    "database_models": 22
  },
  "structure": [
    {
      "path": "backend/app/modules/orders",
      "type": "module",
      "purpose": "Order CRUD + status workflow",
      "loc": 3007,
      "files": {
        "service.py": { "lines": 1200, "purpose": "Business logic" },
        "router.py": { "lines": 800, "purpose": "API endpoints" },
        "models.py": { "lines": 300, "purpose": "ORM entities" }
      },
      "dependencies": ["customers", "shipments", "invoices"],
      "key_endpoints": [
        "POST /api/orders",
        "GET /api/orders/{id}",
        "PUT /api/orders/{id}/status"
      ]
    },
    // ... 28 more modules
  ]
}
```

#### Example: `api-endpoints.json`

```json
{
  "orders": [
    {
      "method": "GET",
      "path": "/api/orders",
      "auth_required": true,
      "params": ["status", "limit", "offset"],
      "returns": "Order[]",
      "file": "backend/app/modules/orders/router.py:45",
      "description": "List all orders with optional filtering"
    },
    {
      "method": "POST",
      "path": "/api/orders",
      "auth_required": true,
      "request_body": { /* schema */ },
      "returns": "Order",
      "file": "backend/app/modules/orders/router.py:78"
    }
    // ... 150+ more endpoints
  ]
}
```

#### How to Use in AI Prompts

Instead of:
```
# ❌ BEFORE (Loads entire service.py = 1200 LOC)
Read /opt/pureleven/backend/app/modules/orders/service.py
```

Use:
```
# ✅ AFTER (Loads only metadata = 20 lines)
Check .claude/index/module-summary.json for "orders" module:
- Purpose: Order CRUD + status workflow
- LOC: 3,007
- Key files: service.py (1200 LOC), router.py (800 LOC)
- Dependencies: customers, shipments, invoices

Then: I only need to see service.py:400-450 for order_create logic
```

**Token Savings:** 1200 LOC full file → 50 LOC summary + targeted excerpt = **96% reduction**

---

### 2. **Incremental File Reading** (-15% tokens)

**Concept:** Load only the code you need, not entire files.

#### Strategy

```
# ❌ OLD: Read entire 3KB file
Read("backend/app/modules/orders/router.py")

# ✅ NEW: Read specific sections
Read("backend/app/modules/orders/router.py", offset=400, limit=100)
# Only reads lines 400-500, not the whole file
```

#### Example Workflow

```python
# Step 1: Check index for line numbers
index_data = load_json(".claude/index/key-files-registry.json")
target_file = index_data["files"]["orders_router.py"]
# {
#   "total_lines": 800,
#   "create_function": {"start": 45, "end": 120},
#   "status_update": {"start": 200, "end": 280}
# }

# Step 2: Read only the function you need
read_file("backend/app/modules/orders/router.py", 
          offset=200, limit=80)  # Just status_update function
```

**Token Savings:** 800 lines → 80 lines = **90% reduction** per read

---

### 3. **Response Templates** (-5% tokens)

**Concept:** Use fixed-format response templates instead of prose.

#### Template: "Explain Function"

Instead of 500-word narrative explanation, use structured format:

```markdown
## Function: order_create()

**File:** backend/app/modules/orders/service.py:45

**Purpose:** Create new order in database

**Inputs:**
- order_data: OrderCreateSchema (Pydantic model)
- tenant_id: UUID
- user_id: UUID

**Processing:**
1. Validate order_data (Pydantic automatic)
2. Create Order ORM entity
3. Add OrderItems from list
4. Commit to database
5. Trigger message_automation.schedule_checkpoint() for ORDER_CREATED

**Returns:** Order (ORM entity)

**Errors:**
- ValidationError if order_data invalid
- IntegrityError if customer not found

**Related:** message_automation.schedule_checkpoint(), OrderCreateSchema
```

**Token Savings:** 500-word explanation → 200-word structured = **60% reduction**

---

### 4. **Prompt Engineering** (-3% tokens)

**Concept:** Write precise prompts that prevent AI from generating unnecessary content.

#### ✅ Good Prompt (Concise)

```
Question: How do I add a new field to Order?

Answer format: Single paragraph with 3 steps (no intro/outro).
```

#### ❌ Bad Prompt (Verbose)

```
I need to understand how to add a new field to the Order entity 
in the database. Can you explain the process in detail? I want to 
understand every step from the perspective of someone who is new 
to SQLAlchemy and Alembic. Please provide code examples, 
explanations, and any gotchas to watch out for.
```

**Token Savings:** Clear constraint prevents 3x longer response

---

### 5. **Conversation Context Reuse** (-2% tokens)

**Concept:** Maintain conversation state to avoid re-explaining context.

#### Implementation

```markdown
# CONVERSATION STATE (Stored in .claude/conversations/)

## Session: add-customer-field-to-orders
### Context (shared across messages):
- "Currently working on: Orders module"
- "Goal: Add customer_notes field"
- "Schema: PostgreSQL 15, Alembic versioning"
- "Files modified: models.py, migration version, router.py"

### Message 1: "Add customer_notes field to Order"
- AI uses context above (not re-explained)
- Saves 50 lines of context re-entry

### Message 2: "How do I query this field?"
- Context already loaded (not repeated)
- AI responds directly without preamble
```

**Token Savings:** Per-message context inclusion → single state load = **2-5% reduction**

---

## 📋 Implementation Checklist

### Phase 1: Indexing (Week 1)

- [ ] Create `.claude/index/codebase-structure.json`
  - [ ] File tree with metadata (size, purpose, type)
  - [ ] Module summaries (29 modules)
  - [ ] Key statistics

- [ ] Create `.claude/index/api-endpoints.json`
  - [ ] Scan all router.py files
  - [ ] Extract method, path, auth, request/response types
  - [ ] Add file:line references

- [ ] Create `.claude/index/database-schema.json`
  - [ ] Extract from models.py + migrations
  - [ ] List all tables, fields, relationships
  - [ ] Add constraints, indexes

- [ ] Create `.claude/index/key-files-registry.json`
  - [ ] File paths + line counts
  - [ ] Function/class locations (start:end line numbers)
  - [ ] Dependency graph

### Phase 2: Usage Guidelines (Week 1)

- [ ] Create `.claude/PROMPT_GUIDE.md`
  - [ ] Rules for asking AI questions
  - [ ] How to reference indexed data
  - [ ] Response format expectations
  - [ ] Token budget per task

- [ ] Create `.claude/RESPONSE_TEMPLATES.md`
  - [ ] Fixed formats for common questions
  - [ ] Examples: "Explain function", "How to add field", "Debug error"
  - [ ] Word limits per template

### Phase 3: Conversation State (Week 2)

- [ ] Create `.claude/conversations/` directory structure
- [ ] Save conversation state JSON after each AI session
- [ ] Template for state file (context, files_touched, decisions_made)

### Phase 4: Automation (Week 2)

- [ ] Create indexing script to auto-update indices
- [ ] Add pre-commit hook to validate indices before push
- [ ] Create script to analyze token usage per session

---

## 📊 Expected Results

### Before Optimization
- **Avg. tokens per question:** 5,000 - 8,000
- **Reason:** Full file reading + verbose responses
- **Monthly cost:** $50-100 (Claude Sonnet API)

### After Optimization
- **Avg. tokens per question:** 250 - 500 (95% reduction!)
- **How:** Index + targeted reading + templates
- **Monthly cost:** $2.50 - 5.00 (Claude Sonnet API)
- **Savings:** $45-95/month = **$540-1,140/year**

### Example: "Add field to Order" Task

#### Before (8,200 tokens)
```
[Load entire orders/service.py: 1,200 LOC × 4 tokens/LOC = 4,800 tokens]
[Load entire models.py: 300 LOC × 4 = 1,200 tokens]
[AI explains entire module: 2,200 tokens]
Total: 8,200 tokens
```

#### After (350 tokens)
```
[Load codebase-structure.json index: 50 tokens]
[Load api-endpoints.json subset: 80 tokens]
[Load database-schema.json: orders table only: 60 tokens]
[Load key-files-registry.json: order functions only: 50 tokens]
[AI responds with template format: 100 tokens]
Total: 340 tokens
```

**Reduction:** 8,200 → 340 tokens = **95.9% reduction** ✅

---

## 🚀 Quick Start for Next AI Conversation

### Step 1: Create Indices (Run Once)

```bash
cd /opt/pureleven
python3 << 'PYTHON'
import json
import os
from pathlib import Path

# Create .claude/index directory
Path(".claude/index").mkdir(parents=True, exist_ok=True)

# Create minimal codebase-structure.json
index = {
    "project": "PureLevenExim CRM",
    "version": "2.4.0",
    "metrics": {
        "total_loc": 96000,
        "modules": 29,
        "database_models": 22
    },
    "modules": [
        {
            "name": "orders",
            "path": "backend/app/modules/orders",
            "purpose": "Order CRUD + status workflow",
            "loc": 3007,
            "key_files": ["service.py", "router.py", "models.py"]
        }
        # Add 28 more modules...
    ]
}

with open(".claude/index/codebase-structure.json", "w") as f:
    json.dump(index, f, indent=2)

print("✅ Index created at .claude/index/codebase-structure.json")
PYTHON
```

### Step 2: Next Time You Use AI

Instead of:
```
Read /opt/pureleven/backend/app/modules/orders/service.py
```

Use:
```
Check .claude/index/codebase-structure.json for orders module.
I need to understand order_create() function (find line # in 
.claude/index/key-files-registry.json) and modify it to...
```

### Step 3: Track Token Usage

Create `.claude/token-tracker.json`:

```json
{
  "sessions": [
    {
      "date": "2026-06-20",
      "task": "Add customer_notes to Order",
      "tokens_before_opt": 8200,
      "tokens_after_opt": 350,
      "reduction": "95.7%",
      "time_saved": "45 seconds"
    }
  ],
  "cumulative": {
    "total_sessions": 1,
    "avg_reduction": "95.7%",
    "estimated_yearly_savings": "$900"
  }
}
```

---

## 📚 Summary

| Strategy | Token Reduction | Implementation |
|----------|-----------------|-----------------|
| Codebase Indexing | -70% | Create 5 JSON index files |
| Incremental Reading | -15% | Use offset/limit in Read() |
| Response Templates | -5% | Define formats in PROMPT_GUIDE |
| Prompt Engineering | -3% | Write concise constraints |
| Context Reuse | -2% | Save conversation state |
| **TOTAL** | **-95%** | **1-2 days of setup** |

---

## 🎯 Next Steps

1. ✅ **Review this architecture** — Does it make sense?
2. 📝 **Create the 5 index files** (codebase-structure, api-endpoints, database-schema, key-files-registry, integration-map)
3. 📖 **Write PROMPT_GUIDE.md** — How to ask AI questions efficiently
4. 🤖 **Use the index in next AI conversation** — Reference indices instead of files
5. 📊 **Track token usage** — Measure actual reduction

---

**This README provides everything needed to understand, deploy, and efficiently maintain the PureLevenExim CRM platform while minimizing AI token consumption by 95%.**

---

*Generated: June 20, 2026 | v2.4.0 Production Ready*
