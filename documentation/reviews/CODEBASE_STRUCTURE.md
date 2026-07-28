# Miguel CRM — Codebase Structure & Architecture

**Last Updated:** Feb 25, 2026  
**Version:** 1.0

---

## **1. Project Overview**

Miguel is a **multi-tenant CRM platform** built with FastAPI (Python backend) + Nginx + PostgreSQL + HTML/JavaScript frontend. It integrates with Shopify, Delhivery, WhatsApp Business API, and other logistics/communication providers.

**Core Features:**
- Multi-tenant support (each company/organization is isolated)
- Admin role management (create/delete employees, configure settings)
- Shipping integration (Shopify stores, delivery partners, notification channels)
- WhatsApp automation & CRM (leads, customers, orders)
- GST/Tax compliance tracking
- Profit & Loss dashboard
- Activity logging & audit trails

---

## **2. Directory Structure**

```
/opt/miguel/
├── backend/                          # FastAPI server
│   ├── app/
│   │   ├── core/                     # Core utilities & config
│   │   │   ├── config.py             # Pydantic settings, env vars
│   │   │   ├── security.py           # Password hashing, JWT
│   │   │   ├── logger.py             # Activity logging service
│   │   │   ├── auth/                 # Multi-tenant auth
│   │   │   │   ├── tenant.py
│   │   │   │   └── platform.py
│   │   │   ├── deps.py               # FastAPI dependencies
│   │   │   └── log_middleware.py     # Request/response logging middleware
│   │   ├── database/
│   │   │   └── session.py            # SQLAlchemy engine & session factory
│   │   ├── models/                   # SQLAlchemy ORM models
│   │   │   ├── tenant.py             # Tenant, Employee
│   │   │   ├── shipping_config.py    # ShopifyStore, DeliveryPartner, NotificationChannel
│   │   │   ├── leads.py
│   │   │   ├── customers.py
│   │   │   ├── orders.py
│   │   │   └── activity_log.py       # Audit log entries
│   │   ├── modules/                  # Feature modules (router + service + schema)
│   │   │   ├── shipping_config/
│   │   │   │   ├── router.py         # 16 endpoints (CRUD + test-connection)
│   │   │   │   ├── service.py        # Encryption, connection testing
│   │   │   │   └── schemas.py        # Pydantic request/response models
│   │   │   ├── wa_engine/            # WhatsApp automation
│   │   │   ├── leads/                # Lead management
│   │   │   ├── customers/
│   │   │   ├── orders/
│   │   │   ├── reporting/            # P&L dashboard
│   │   │   ├── meta/                 # Meta/WhatsApp integration
│   │   │   └── employee_auth/        # Tenant login/employee management
│   │   ├── main.py                   # FastAPI app initialization
│   │   └── __init__.py
│   ├── alembic/                      # Database migrations
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── c0e793280887_...py    # Shipping config tables
│   ├── requirements.txt               # Python dependencies
│   ├── Dockerfile                     # Docker image definition
│   ├── .env                           # Environment variables (local)
│   └── README.md
│
├── frontend/                          # Static HTML/CSS/JS
│   ├── pages/
│   │   └── index.html                # Landing page
│   ├── auth/
│   │   ├── tenant-login.html
│   │   └── platform-login.html
│   ├── modules/
│   │   ├── tenant-admin.html         # Main admin dashboard (4 tabs)
│   │   ├── platform-admin.html       # Platform admin (not used currently)
│   │   └── wa-setup-guide.html
│   ├── styles/
│   │   └── ds.css                    # Design system CSS
│   ├── leads.html
│   ├── orders.html
│   ├── customers.html
│   ├── gst.html
│   ├── marketing.html
│   ├── vendors.html
│   ├── products.html
│   ├── profit-loss.html
│   └── ds.css.backup
│
├── infra/
│   ├── nginx.conf                    # Nginx routing & proxy config
│   └── README.md
│
├── scripts/
│   ├── test_shipping.py              # Integration test for shipping API
│   └── reset_db.sh                   # Database reset utility
│
├── deploy/
│   └── [deployment configs]
│
├── docker-compose.yml                # Services: db, backend, frontend
├── .env.example                      # Template for .env
├── README.md                          # Project README
└── docs/
    ├── archived/                      # Old documentation (62 files)
    └── API_REFERENCE.md              # [To be created]
```

---

## **3. Key Components**

### **3.1 Backend Architecture**

**Framework:** FastAPI 0.100+ with SQLAlchemy 2.x ORM

**Database:** PostgreSQL 15 with Alembic migrations

**Authentication:**
- JWT-based (HS256)
- Two auth types: Tenant (employee login) + Platform (superadmin)
- Role-based access control (RBAC): admin, sales, marketing, operations, support

**Modules:**
- **shipping_config**: Shopify stores, delivery partners (Delhivery, Blue Dart, etc.), notification channels (WhatsApp, SMS, Email)
- **wa_engine**: WhatsApp Business API integration (message sending, webhook handling)
- **leads/customers/orders**: Core CRM data models
- **reporting**: Profit & Loss calculations
- **employee_auth**: Tenant login, employee management

**Encryption:**
- Uses Fernet (symmetric encryption via `cryptography` library)
- Credentials stored encrypted in DB (API keys, access tokens, secrets)
- ENCRYPTION_KEY in docker-compose.yml environment

**Logging:**
- Every API request/response logged to `activity_logs` table
- RequestLoggingMiddleware auto-captures method, path, status, duration, IP, user-agent
- Log level: INFO (success), WARNING (4xx), ERROR (5xx)

### **3.2 Frontend Architecture**

**Technology:** Vanilla HTML/JavaScript/CSS (no frameworks)

**Structure:**
- Static files served by Nginx from `/usr/share/nginx/html`
- Single HTML files per page (SPA-like via JS routing)
- Form submissions via fetch API to backend

**Main Pages:**
- **tenant-admin.html**: 4-tab admin interface
  - **Shipping Stores**: Create/edit/delete/test Shopify stores
  - **Delivery Partners**: Configure Delhivery, Blue Dart, etc.
  - **Notification Channels**: WhatsApp, SMS, Email
  - **Business Rules**: Set order thresholds, RTO alerts, auto-shipment rules
- **leads.html**: Lead management CRM
- **orders.html**: Order tracking
- **profit-loss.html**: Financial dashboard
- **gst.html**: GST/tax tracking
- **marketing.html**: Marketing campaigns
- **vendors.html**: Supplier management

### **3.3 Database Schema** (4 main shipping tables)

```sql
shopify_stores (
  id UUID PRIMARY KEY,
  tenant_id UUID FOREIGN KEY,
  store_name VARCHAR,
  store_url VARCHAR UNIQUE,
  api_access_token TEXT ENCRYPTED,
  api_client_id VARCHAR,
  api_client_secret TEXT ENCRYPTED,
  is_primary BOOLEAN,
  is_active BOOLEAN,
  is_connected BOOLEAN,
  last_sync TIMESTAMP,
  last_connection_test TIMESTAMP,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)

delivery_partners (
  id UUID PRIMARY KEY,
  tenant_id UUID FOREIGN KEY,
  partner_type VARCHAR (delhivery|bluedart|dtdc|india_post|amazon),
  display_name VARCHAR,
  api_key TEXT ENCRYPTED,
  api_secret TEXT ENCRYPTED,
  client_name VARCHAR,
  client_id VARCHAR,
  api_base_url VARCHAR,
  pickup_location_code VARCHAR,
  warehouse_name VARCHAR,
  supported_shipment_types ARRAY,
  is_primary BOOLEAN,
  is_active BOOLEAN,
  is_connected BOOLEAN,
  last_connection_test TIMESTAMP,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)

notification_channels (
  id UUID PRIMARY KEY,
  tenant_id UUID FOREIGN KEY,
  channel_type VARCHAR (whatsapp|sms|email),
  provider VARCHAR (meta|twilio|sendgrid),
  api_key TEXT ENCRYPTED,
  api_secret TEXT ENCRYPTED,
  access_token TEXT ENCRYPTED,
  phone_number VARCHAR,
  business_account_id VARCHAR,
  phone_number_id VARCHAR,
  sender_email VARCHAR,
  is_primary BOOLEAN,
  is_active BOOLEAN,
  is_connected BOOLEAN,
  last_connection_test TIMESTAMP,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)

shipping_business_rules (
  id UUID PRIMARY KEY,
  tenant_id UUID FOREIGN KEY UNIQUE,
  max_order_value DECIMAL,
  max_cod_amount DECIMAL,
  high_rto_threshold DECIMAL,
  medium_rto_threshold DECIMAL,
  require_cod_confirmation BOOLEAN,
  cod_confirmation_timeout_minutes INTEGER,
  auto_create_on_order_created BOOLEAN,
  auto_create_on_payment_confirmed BOOLEAN,
  require_manual_approval BOOLEAN,
  send_delivery_confirmation BOOLEAN,
  send_rto_alerts BOOLEAN,
  send_ndr_alerts BOOLEAN,
  notify_via_whatsapp BOOLEAN,
  notify_via_sms BOOLEAN,
  notify_via_email BOOLEAN,
  admin_alert_on_rto BOOLEAN,
  admin_alert_on_ndr BOOLEAN,
  admin_alert_on_high_value_order BOOLEAN,
  admin_emails ARRAY,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)
```

---

## **4. API Endpoints**

### **Shipping Config Endpoints** (`/api/config/*`)

| Method | Endpoint                                              | Description |
|--------|-------------------------------------------------------|-------------|
| GET    | `/api/config/shopify-stores`                          | List stores |
| POST   | `/api/config/shopify-stores`                          | Create store |
| PUT    | `/api/config/shopify-stores/{id}`                     | Update store |
| DELETE | `/api/config/shopify-stores/{id}`                     | Delete store |
| POST   | `/api/config/shopify-stores/{id}/test-connection`     | Test Shopify API token |
| GET    | `/api/config/delivery-partners`                       | List partners |
| POST   | `/api/config/delivery-partners`                       | Create partner |
| PUT    | `/api/config/delivery-partners/{id}`                  | Update partner |
| DELETE | `/api/config/delivery-partners/{id}`                  | Delete partner |
| POST   | `/api/config/delivery-partners/{id}/test-connection`  | Test partner API |
| GET    | `/api/config/notification-channels`                   | List channels |
| POST   | `/api/config/notification-channels`                   | Create channel |
| PUT    | `/api/config/notification-channels/{id}`              | Update channel |
| DELETE | `/api/config/notification-channels/{id}`              | Delete channel |
| POST   | `/api/config/notification-channels/{id}/test-connection` | Test channel |
| GET    | `/api/config/business-rules`                          | Get rules |
| PUT    | `/api/config/business-rules`                          | Update rules |

### **Auth Endpoints**

| Method | Endpoint                                              | Description |
|--------|-------------------------------------------------------|-------------|
| POST   | `/tenant/login`                                       | Tenant employee login |
| GET    | `/tenant/me`                                          | Current employee profile |
| POST   | `/tenant/employees`                                   | Create employee (admin only) |
| GET    | `/tenant/employees`                                   | List employees (admin only) |
| PUT    | `/tenant/employees/{id}`                              | Update employee (admin only) |
| DELETE | `/tenant/employees/{id}`                              | Delete employee (admin only) |

---

## **5. Configuration & Secrets**

### **Environment Variables** (docker-compose.yml)

```yaml
# ── WhatsApp Business API ──
WHATSAPP_PHONE_NUMBER_ID: ""         # Phone number ID from Meta
WHATSAPP_ACCESS_TOKEN: ""            # Permanent token for system user
WHATSAPP_API_VERSION: "v19.0"        # Meta API version
WHATSAPP_AUTO_REPLY_MSG: "..."       # Default auto-reply message
META_WEBHOOK_VERIFY_TOKEN: "..."     # Webhook verification token

# ── Encryption ─────────────
ENCRYPTION_KEY: "11_I0ko3xNdGEu6f7y3DZig-nMQVd3BIBvhKOsL86tg="
```

### **Backend .env** (local only, not in docker-compose)

```env
SECRET_KEY=<long-random-key>
DATABASE_URL=postgresql+psycopg2://miguel_user:miguel_password@db:5432/miguel_db
ENCRYPTION_KEY=11_I0ko3xNdGEu6f7y3DZig-nMQVd3BIBvhKOsL86tg=
```

---

## **6. Development Workflow**

### **Setup**

```bash
# Build and start all services
docker compose build
docker compose up -d

# Run migrations
docker compose exec backend alembic upgrade head

# Test API
python3 scripts/test_shipping.py
```

### **Accessing the System**

| Component | URL | Credentials |
|-----------|-----|-------------|
| Frontend | `http://localhost/` | N/A |
| Tenant Login | `http://localhost/login` | `purelevenexim@gmail.com / wM01gkxGCNhJT!` |
| Tenant Admin | `http://localhost/tenant-admin` | After login |
| Backend API | `http://localhost:8000` | Bearer JWT token |
| Backend Docs | `http://localhost:8000/docs` | Swagger UI |

### **Database Management**

```bash
# Connect to DB
docker compose exec db psql -U miguel_user -d miguel_db

# Run migrations
docker compose exec backend alembic upgrade head
docker compose exec backend alembic downgrade -1  # Rollback one

# Backup/restore
docker compose exec db pg_dump -U miguel_user -d miguel_db > backup.sql
docker compose exec db psql -U miguel_user -d miguel_db < backup.sql
```

---

## **7. Known Bugs & Fixes Applied**

| Issue | Status | Fix | Date |
|-------|--------|-----|------|
| ENCRYPTION_KEY not reaching container | ✅ Fixed | Added to docker-compose.yml environment | Feb 24 |
| reportlab missing in Docker image | ✅ Fixed | Rebuilt image with full requirements.txt | Feb 24 |
| Password hash corruption on login | ✅ Fixed | Reset password hash using app.core.security.hash_password | Feb 25 |
| 70+ docs at root level | ✅ Fixed | Archived to docs/archived/ | Feb 25 |
| Frontend backups & debug files | ✅ Fixed | Removed .bak*, *debug* files | Feb 25 |
| No Nginx in docker-compose | ✅ Fixed | Added frontend Nginx service + config | Feb 25 |

---

## **8. Testing & Verification**

### **Quick Health Check**

```bash
# Backend running?
curl http://localhost:8000/docs

# Database connected?
docker compose exec backend python3 -c "from app.database.session import engine; print(engine.url)"

# Tenant login works?
curl -X POST http://localhost:8000/tenant/login \
  -H "Content-Type: application/json" \
  -d '{"email":"purelevenexim@gmail.com","password":"wM01gkxGCNhJT!","slug":"purelevenexim"}'

# Shipping config API working?
python3 scripts/test_shipping.py
```

### **Running Tests**

```bash
# Full shipping config test (GET + POST + PUT + DELETE)
python3 scripts/test_shipping.py

# Backend tests (if any)
docker compose exec backend pytest
```

---

## **9. Deployment Checklist**

- [ ] All secrets in docker-compose.yml (ENCRYPTION_KEY, WHATSAPP tokens, etc.)
- [ ] DATABASE_URL points to production DB
- [ ] Backend image built: `docker compose build backend`
- [ ] Frontend served by Nginx on port 80
- [ ] SSL/TLS configured (if not using ngrok for testing)
- [ ] Database migrations applied: `alembic upgrade head`
- [ ] Test tenant credentials created
- [ ] Shopify App configured with App URL: `https://pureleven.com`
- [ ] Delhivery/Blue Dart API keys configured
- [ ] WhatsApp Business API webhook registered

---

## **10. Troubleshooting**

### **"Invalid access token" on Shopify connection test**
- Ensure you're using the **Admin API access token** (from Custom App → API credentials)
- Not the client secret or session token
- Token must start with `shpat_` or similar

### **500 Internal Server Error on login**
- Check backend logs: `docker logs miguel_backend`
- Likely: password hash corrupted (run password reset script)
- Or: missing ENCRYPTION_KEY in docker-compose.yml environment

### **"Could not validate credentials" (401) on API calls**
- JWT token expired or invalid
- Re-login to get fresh token
- Check SECRET_KEY matches between backend/.env and settings

### **Nginx returning 404 for admin pages**
- Verify frontend files are in `/usr/share/nginx/html`
- Check nginx.conf routing rules
- Restart Nginx: `docker compose restart frontend`

---

## **11. Next Steps & Roadmap**

- [ ] Implement Shopify OAuth flow (optional, currently using manual API credentials)
- [ ] Add more delivery partner integrations (DTDC, India Post)
- [ ] Build email notification service
- [ ] Implement SMS via Twilio
- [ ] Complete P&L dashboard calculations
- [ ] Add customer import/export (CSV)
- [ ] Implement lead scoring & automation
- [ ] Add frontend unit tests
- [ ] Add backend integration tests
- [ ] Set up CI/CD pipeline (GitHub Actions)

---

**Questions?** Check the `/docs/archived/` folder for detailed feature documentation or the backend README at `/backend/README.md`.
