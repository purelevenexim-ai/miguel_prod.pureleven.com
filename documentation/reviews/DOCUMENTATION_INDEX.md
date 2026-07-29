# Miguel CRM — Documentation Index

**Generated:** February 25, 2026  
**Status:** Production Ready

---

## **Quick Navigation**

### **For New Users (Start Here)**
1. **README.md** — Quick start, features, how to access
2. **CODEBASE_STRUCTURE.md** — Detailed architecture, API reference

### **For Orders Management**
1. **ORDERS_TABLE_FIX_SESSION_2026_02_25.md** — Latest fixes (status/pay-status, xlsx upload)
2. **INDIA_POST_XLSX_UPLOAD_GUIDE.md** — How to use xlsx tracking upload
3. **MANUAL_ORDERS_INDIA_POST_XLSX_GUIDE.md** — Technical implementation

### **For Developers**
1. **CODEBASE_STRUCTURE.md** — Full API endpoints, database schema
2. **backend/README.md** — Backend setup, development
3. **infra/nginx.conf** — Frontend routing rules

### **For Admins/Operations**
1. **README.md** — Common tasks (create employee, add store, etc.)
2. **CLEANUP_REPORT.md** — What changed, current status
3. **scripts/test_shipping.py** — Run to verify system health

### **Historical Documentation**
- **docs/archived/** — 62 feature documentation files (refer if needed)

---

## **Documentation Files**

| File | Purpose | Audience | Read Time |
|------|---------|----------|-----------|
| **README.md** | Quick start & overview | Everyone | 5 min |
| **ORDERS_TABLE_FIX_SESSION_2026_02_25.md** | Latest session fixes & testing | Developers | 10 min |
| **INDIA_POST_XLSX_UPLOAD_GUIDE.md** | How-to guide for xlsx uploads | Operations | 8 min |
| **CODEBASE_STRUCTURE.md** | Architecture & API reference | Developers | 15 min |
| **MANUAL_ORDERS_INDIA_POST_XLSX_GUIDE.md** | Technical xlsx implementation | Backend devs | 12 min |
| **CLEANUP_REPORT.md** | What was fixed & organized | Admins | 10 min |
| **infra/nginx.conf** | Routing & proxy configuration | DevOps | 5 min |
| **backend/README.md** | Backend setup & development | Backend devs | 10 min |
| **scripts/test_shipping.py** | Integration test script | QA/Devs | N/A (code) |
| **docs/archived/*** | Historical features (62 files) | Reference | Variable |

---

## **System Architecture at a Glance**

```
┌─────────────────────────────────────┐
│         Nginx (Frontend)            │ ← Port 3000
│     Serves HTML/CSS/JS + Routes    │
│   • Proxies /api/* to backend      │
│   • Routing rules (auth, modules)  │
└──────────┬──────────────────────────┘
           │
           │ HTTP
           │
┌──────────▼──────────────────────────┐
│      FastAPI Backend                │ ← Port 8000
│  • JWT authentication               │
│  • 16 shipping config endpoints    │
│  • Encryption (Fernet)             │
│  • Activity logging                │
│  • Multi-tenant isolation          │
└──────────┬──────────────────────────┘
           │
           │ SQL
           │
┌──────────▼──────────────────────────┐
│   PostgreSQL 15 Database            │ ← Port 5432
│  • Tenants & employees             │
│  • Shipping config (4 tables)      │
│  • CRM data (leads, customers)     │
│  • Activity logs                   │
│  • Encrypted credentials           │
└─────────────────────────────────────┘
```

---

## **Features Overview**

### **1. Shipping Configuration** 📦
Store Shopify credentials, delivery partner configs, notification channels, and business rules.
- **Endpoint:** `/api/config/*`
- **Docs:** CODEBASE_STRUCTURE.md § 4

### **2. Multi-Tenant Support** 👥
Isolated data per organization, employee role-based access control.
- **Auth:** JWT Bearer token
- **Roles:** admin, sales, marketing, operations, support
- **Docs:** CODEBASE_STRUCTURE.md § 2, § 3.1

### **3. CRM Modules** 💼
Leads, customers, orders, vendors, products.
- **Status:** Implemented (see docs/archived for feature docs)
- **Docs:** CODEBASE_STRUCTURE.md § 3.1

### **4. WhatsApp Integration** 💬
Meta Business API, auto-reply, webhooks.
- **Module:** `backend/app/modules/wa_engine/`
- **Docs:** docs/archived/ (WA related docs)

### **5. Financial Tracking** 💰
Profit & Loss dashboard, GST compliance.
- **Module:** `backend/app/modules/reporting/`
- **Docs:** docs/archived/P_L_* and GSTIN_*

---

## **Access Points**

| What | URL | Port | Use Case |
|------|-----|------|----------|
| Frontend (web app) | http://localhost:3000 | 3000 | Browse admin dashboard |
| Login page | http://localhost:3000/login | 3000 | Employee login |
| Admin dashboard | http://localhost:3000/tenant-admin | 3000 | Manage shipping config |
| Backend API | http://localhost:8000 | 8000 | Direct API calls (curl, Postman) |
| Swagger docs | http://localhost:8000/docs | 8000 | Interactive API documentation |
| ReDoc | http://localhost:8000/redoc | 8000 | API reference (read-only) |
| PostgreSQL | localhost:5432 | 5432 | Database access (docker exec) |

---

## **Test Credentials**

```
Tenant Admin:
  Email:    purelevenexim@gmail.com
  Password: wM01gkxGCNhJT!
  Slug:     purelevenexim
  Role:     admin

Test command:
  python3 /opt/miguel/scripts/test_shipping.py
```

---

## **Common Questions**

### **Q: Where is the database?**
A: PostgreSQL 15 running in Docker container `miguel_db`. Access via:
```bash
docker compose exec db psql -U miguel_user -d miguel_db
```

### **Q: How do I add a new employee?**
A: POST to `/tenant/employees` with admin role. See README.md § Common Tasks.

### **Q: How do I configure Shopify?**
A: Admin Dashboard → Shipping Stores → Add Store. Requires Shopify Admin API access token.
For details, see CODEBASE_STRUCTURE.md § 7 (Troubleshooting).

### **Q: How do I deploy to production?**
A: See README.md § Deployment Checklist and CODEBASE_STRUCTURE.md § 9.

### **Q: Where are the old feature docs?**
A: Archived in `docs/archived/` (62 files from earlier phases).

### **Q: How do I run tests?**
A: `python3 /opt/miguel/scripts/test_shipping.py` (tests all 16 endpoints).

---

## **What Changed (Feb 25, 2026)**

✅ **Fixed:** Password hash corruption, ENCRYPTION_KEY config, reportlab, missing Nginx service  
✅ **Organized:** Frontend folder structure, archived 62 old docs, removed 8 backup files  
✅ **Added:** Comprehensive documentation (CODEBASE_STRUCTURE.md, nginx.conf)  
✅ **Verified:** All 16 API endpoints working, authentication operational  

See **CLEANUP_REPORT.md** for detailed breakdown.

---

## **Getting Help**

| Issue | Resource |
|-------|----------|
| API not responding | Check `docker logs miguel_backend` |
| Frontend returning 404 | Check `docker logs miguel_frontend` |
| Database connection error | Check `docker logs miguel_db` |
| Login not working | Reset password (see CODEBASE_STRUCTURE.md § 10) |
| Shopify test fails | Ensure Admin API token (not session token) |
| General questions | Read CODEBASE_STRUCTURE.md |

---

## **File Locations**

```
/opt/miguel/
├── README.md                          ← Start here (user guide)
├── CODEBASE_STRUCTURE.md             ← Tech reference
├── CLEANUP_REPORT.md                 ← What was done
├── DOCUMENTATION_INDEX.md            ← This file
├── backend/
│   ├── app/
│   │   ├── main.py                   ← FastAPI initialization
│   │   ├── core/                     ← Auth, config, logging
│   │   ├── models/                   ← Database ORM models
│   │   └── modules/                  ← Feature modules
│   ├── alembic/                      ← Database migrations
│   ├── requirements.txt               ← Python dependencies
│   └── Dockerfile
├── frontend/
│   ├── pages/index.html              ← Landing page
│   ├── auth/                         ← Login pages
│   ├── modules/                      ← Admin dashboards
│   ├── styles/ds.css                 ← CSS
│   └── *.html                        ← Feature pages
├── infra/
│   └── nginx.conf                    ← Frontend routing
├── scripts/
│   └── test_shipping.py              ← Integration test
├── docker-compose.yml                ← Service definitions
├── docs/
│   └── archived/                     ← 62 historical docs
└── deploy/                           ← Deployment configs
```

---

## **Roadmap & Next Steps**

### **Immediate (Next Sprint)**
- [ ] Integrate Shopify Admin API OAuth (optional, currently manual)
- [ ] Add more delivery partner integrations (DTDC, India Post)
- [ ] Implement SMS via Twilio
- [ ] Complete P&L dashboard

### **Near-term (Next 2-3 Months)**
- [ ] Add customer import/export (CSV)
- [ ] Implement lead scoring
- [ ] Add email notifications
- [ ] Frontend unit tests
- [ ] Backend integration tests

### **Long-term (Q2-Q3 2026)**
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Kubernetes deployment
- [ ] Advanced analytics & reporting
- [ ] Mobile app (React Native)
- [ ] SaaS billing layer

---

## **Support & Contribution**

**Issues:** Check `docker logs` and CODEBASE_STRUCTURE.md § 10 (Troubleshooting)  
**Contributions:** Follow backend & frontend structure conventions  
**Questions:** Review the relevant documentation file above  

---

**Last Updated:** February 25, 2026  
**System Status:** ✅ Production Ready  
**All Tests:** ✅ Passing

---

Happy shipping! 🚀
