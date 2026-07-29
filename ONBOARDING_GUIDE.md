# 🎯 ONBOARDING GUIDE - Miguel CRM Production System

**For:** New team members, stakeholders, developers  
**Time:** 15-20 minutes to understand the complete system  
**Updated:** February 26, 2026

---

## ⏱️ 5-Minute Executive Summary

**What is Miguel?**
A modern SaaS CRM platform for Indian e-commerce businesses with order tracking, WhatsApp automation, and multi-tenant support.

**Where is it running?**
- **Production Server:** 172.232.118.208
- **Frontend:** Port 80 (http://172.232.118.208/login)
- **API:** Port 8000 (http://172.232.118.208:8000/docs)

**How do I access it?**
```
Email:    purelevenexim@gmail.com
Password: wM01gkxGCNhJT!
```

**What can it do?**
- ✅ Manage orders (create, edit, track)
- ✅ Integrate with Shopify
- ✅ Track shipments (Delhivery, Blue Dart, India Post)
- ✅ Send WhatsApp notifications
- ✅ Generate invoices & reports
- ✅ Manage leads, customers, vendors
- ✅ Track payments & financial metrics

**Is it production-ready?**
✅ YES - All systems operational, fully tested, documented.

---

## 🎓 10-Minute Technical Overview

### Architecture (3-Layer)
```
┌─────────────────────────────────┐
│  Frontend (Nginx)               │  ← Your browser (port 80)
│  HTML5 + CSS3 + JavaScript      │
└──────────┬──────────────────────┘
           │
┌──────────▼──────────────────────┐
│  Backend (FastAPI)              │  ← API server (port 8000)
│  20+ routers, background workers│
└──────────┬──────────────────────┘
           │
┌──────────▼──────────────────────┐
│  Database (PostgreSQL)          │  ← Persistent storage
│  30+ tables, encrypted creds    │
└─────────────────────────────────┘
```

### Key Technologies
- **Backend:** Python + FastAPI + SQLAlchemy
- **Frontend:** Vanilla JavaScript (no frameworks)
- **Database:** PostgreSQL 15
- **Server:** Nginx (reverse proxy)
- **Deployment:** Docker Compose (3 containers)

### Core Modules (What exists now)
```
Orders & Logistics
├─ Order Management (create, edit, track)
├─ Shopify Sync (auto-import orders)
├─ Tracking (15-min auto-sync from couriers)
├─ Risk Assessment (4-factor scoring)
└─ Notifications (WhatsApp, SMS, email)

Financial
├─ P&L Dashboard
├─ Invoice Generation
├─ GST/Tax Tracking
├─ Vendor Management
└─ Inventory Tracking

CRM
├─ Leads Pipeline
├─ Customer Database
├─ Marketing Campaigns
├─ Activity Audit Log
└─ WhatsApp Automation (WABIS support)
```

---

## 🚀 15-Minute Feature Tour

### Order Management (Latest - Feb 26)
**Try this:**
1. Login at http://172.232.118.208/login
2. Click "Orders" in left menu
3. Find a draft order (no tracking number)
4. Click the pencil icon → "✏️ Edit"
5. Change payment amount → Click "💾 Save Changes"

**What you can edit:**
- Order number
- Payment method & amount
- Delivery address
- Shipping partner
- Recipient info

**What's locked:**
- Orders with tracking (read-only)
- Delivered orders (read-only)

### Admin Dashboard
**Try this:**
1. Login → Click "Admin Dashboard"
2. **Tab 1: Shipping Stores** - Configure Shopify stores
3. **Tab 2: Delivery Partners** - Add Delhivery, Blue Dart, etc.
4. **Tab 3: Notification Channels** - Setup WhatsApp, SMS, Email
5. **Tab 4: Business Rules** - Configure auto-shipment, thresholds

---

## 📊 20-Minute Architecture Deep-Dive

### Database Design
**30+ tables organized by feature:**
- **orders** - Main order data (created manually or via Shopify)
- **shipping_info** - Tracking numbers, courier details
- **tracking_events** - Real-time status updates
- **customers** - Customer master data with delivery scores
- **rto_zones** - Risk zones by pincode
- **activity_logs** - Complete audit trail
- **shipping_config** - Encrypted API credentials (Shopify, couriers, WhatsApp)

### API Endpoints (20+ routers)
```
GET/POST    /api/orders              Order CRUD
PATCH       /api/orders/{id}         Order edit (NEW)
GET/POST    /api/customers           Customer management
GET/POST    /api/leads               Lead pipeline
GET/POST    /api/config/shopify-stores  Shopify configuration
GET/POST    /api/config/delivery-partners  Courier setup
POST        /api/wa/send-message     WhatsApp sending
GET         /api/reports/profit-loss P&L dashboard
... and 12+ more
```

### Background Workers (Always Running)
```
Tracking Sync         Every 15 minutes     Syncs courier tracking
Shopify Sync          Every 30 minutes     Imports new Shopify orders
Customer Sync         Every 30 minutes     Updates customer scores
Log Cleanup           Daily at 2 AM UTC    Deletes old audit logs
```

### Authentication Flow
```
1. User enters email + password
2. Backend validates against users table
3. JWT token generated (24-hour expiry)
4. Token sent to frontend, stored in localStorage
5. All API calls include token in Authorization header
6. Backend validates token before processing request
7. Request filtered by tenant_id (multi-tenant isolation)
```

### Encryption Strategy
```
Credentials Stored:    Shopify API tokens, courier secrets, WhatsApp tokens
Encryption Method:     Fernet (symmetric)
Encryption Key:        ENCRYPTION_KEY environment variable
Storage Location:      shipping_config table (encrypted columns)
Decryption:            Automatic by service layer when needed
```

---

## 🔍 Key Files You Should Know

### For Understanding the System
| File | Purpose | Read Time |
|------|---------|-----------|
| README.md | Quick start, overview | 5 min |
| CODEBASE_STRUCTURE.md | Architecture, all endpoints | 15 min |
| PRODUCTION_SYSTEM_OVERVIEW.md | Complete system guide | 20 min |
| PROJECT_HISTORY_AND_EVOLUTION.md | Development history | 10 min |

### For Operations
| File | Purpose | Read Time |
|------|---------|-----------|
| OPERATIONS_QUICK_REFERENCE.md | Daily tasks, troubleshooting | 10 min |
| PRODUCTION_STATUS_REPORT.md | Current system health | 5 min |
| PRODUCTION_SETUP.md | Deployment & port config | 5 min |

### For Features
| File | Purpose | Read Time |
|------|---------|-----------|
| DRAFT_ORDER_EDIT_FEATURE.md | Order editing (Feb 26) | 10 min |
| AUTO_PAY_STATUS_UPDATE_FIX.md | Delivery → auto-paid | 5 min |
| ORDERS_TABLE_FIX_SESSION_2026_02_25.md | Bug fixes (Feb 25) | 10 min |
| INDIA_POST_XLSX_UPLOAD_GUIDE.md | Tracking upload guide | 8 min |

---

## 💡 Common Questions (FAQs)

### Q: How do I add a new Shopify store?
**A:** Login → Admin Dashboard → Tab 1: Shipping Stores → Add New Store. Provide store URL and API credentials. System auto-syncs orders every 30 minutes.

### Q: How do I enable WhatsApp notifications?
**A:** Admin Dashboard → Tab 3: Notification Channels → Add WhatsApp. Provide WhatsApp Business API credentials. Orders automatically trigger notifications (confirmed, shipped, delivered, etc.).

### Q: Can I edit an order after it's been shipped?
**A:** No. Once tracking is assigned, the order becomes read-only. Only draft orders (no tracking) can be edited. This prevents accidental modifications.

### Q: How often is tracking updated?
**A:** Every 15 minutes automatically. The system calls courier APIs and updates status in real-time. Check /api/shipments endpoints for manual sync.

### Q: What happens when an order is delivered?
**A:** Payment status automatically changes to "Paid" (regardless of payment method). This is because delivery implies payment was collected.

### Q: Can I upload multiple tracking numbers at once?
**A:** Yes! Use the India Post xlsx upload feature. Download template, fill in order numbers and tracking numbers, upload. System auto-detects columns.

### Q: How is my data secure?
**A:** Multi-layer security:
1. Tenant isolation (data separated by tenant_id)
2. JWT authentication (tokens expire in 24 hours)
3. Encryption (API credentials encrypted at rest)
4. Audit logging (all actions tracked)
5. Password hashing (bcrypt)

### Q: Can I customize the system?
**A:** Yes. The architecture supports:
- Custom business rules (auto-shipment thresholds, RTO alerts)
- Additional delivery partners
- Custom WhatsApp message templates
- Custom reports and dashboards
- API integrations for external systems

---

## 🎯 What's New This Week

### Feb 26 - Draft Order Editing ✅
- Orders without tracking are now fully editable
- Edit payment amounts → auto-infer payment status
- Edit delivery address, courier, customer info
- Feature locked once tracking assigned or delivered

### Feb 25 - Multiple Fixes ✅
- Auto-mark paid when order delivered
- Fixed order creation bug (500 error)
- Enabled status/payment dropdown editing
- Enhanced India Post xlsx upload

---

## 🚀 Getting Started Steps

### Step 1: Access the System (2 minutes)
```
1. Open browser
2. Go to http://172.232.118.208/login
3. Email: purelevenexim@gmail.com
4. Password: wM01gkxGCNhJT!
5. You're in!
```

### Step 2: Explore the Dashboard (5 minutes)
```
1. Click "Admin Dashboard" (if not already there)
2. You see 4 tabs:
   - Shipping Stores (Shopify configuration)
   - Delivery Partners (Courier setup)
   - Notification Channels (WhatsApp, SMS, Email)
   - Business Rules (Auto-shipment, thresholds)
3. Explore each tab to understand configuration
```

### Step 3: Create a Test Order (3 minutes)
```
1. Click "Orders" in left menu
2. Click "New Order"
3. Fill in basic details (customer, address, amount)
4. Click "Create"
5. Order now appears in table
```

### Step 4: Try Editing the Order (3 minutes)
```
1. Find your test order in the table
2. Click the order to open drawer
3. Look for "✏️ Editable" chip (appears if no tracking)
4. Click payment amount field
5. Change the amount
6. Click "💾 Save Changes"
7. Order updated successfully!
```

### Step 5: Check the API (2 minutes)
```
1. Go to http://172.232.118.208:8000/docs
2. You see all available endpoints
3. Try "GET /api/orders" to see your test order
4. Try "PATCH /api/orders/{id}" with test data
```

---

## 📚 Learning Path

### For Sales/Operations Teams
1. **Day 1:** This onboarding guide (15 min)
2. **Day 2:** README.md (5 min)
3. **Day 3:** OPERATIONS_QUICK_REFERENCE.md (10 min)
4. **Ongoing:** INDIA_POST_XLSX_UPLOAD_GUIDE.md (when needed)

### For Developers
1. **Day 1:** This guide (20 min)
2. **Day 2:** CODEBASE_STRUCTURE.md (20 min)
3. **Day 3:** Review backend/app structure (30 min)
4. **Day 4:** Review frontend HTML files (20 min)
5. **Ongoing:** Review specific modules as needed

### For DevOps/SysAdmin
1. **Day 1:** This guide (15 min)
2. **Day 2:** PRODUCTION_SETUP.md (10 min)
3. **Day 3:** OPERATIONS_QUICK_REFERENCE.md (15 min)
4. **Day 4:** docker-compose.yml deep-dive (15 min)
5. **Ongoing:** Monitor and maintain

---

## ✅ Verification Checklist (For First Login)

- [ ] Can access login page (http://172.232.118.208/login)
- [ ] Can login with provided credentials
- [ ] Can see dashboard with 4 tabs
- [ ] Can navigate to Orders page
- [ ] Can view existing orders in table
- [ ] Can open order drawer and see details
- [ ] Can access API docs (http://172.232.118.208:8000/docs)
- [ ] All tabs in admin dashboard load without errors

If all checked: ✅ You're ready to use the system!

---

## 🆘 Need Help?

### Common Issues
1. **Can't login?** → Check email/password, try again
2. **Orders page blank?** → Refresh browser, check network tab
3. **API returning 500?** → Check backend logs: `docker logs pureleven_backend`
4. **Can't edit order?** → Order must have no tracking number and not be delivered
5. **WhatsApp not sending?** → Verify credentials in Admin Dashboard

### Documentation References
- **Quick reference:** OPERATIONS_QUICK_REFERENCE.md
- **System overview:** PRODUCTION_SYSTEM_OVERVIEW.md
- **Features:** CODEBASE_STRUCTURE.md
- **History:** PROJECT_HISTORY_AND_EVOLUTION.md

### Escalation
If issue persists:
1. Check logs: `docker logs pureleven_backend`
2. Verify containers: `docker ps`
3. Contact: Development team with screenshots + error messages

---

## 🎓 Next Steps After Onboarding

### For Everyone
1. ✅ Complete this guide (you are here)
2. ✅ Explore the system with test account
3. ✅ Read README.md for feature overview
4. ✅ Check OPERATIONS_QUICK_REFERENCE.md for daily tasks

### For Developers
1. ✅ Review CODEBASE_STRUCTURE.md
2. ✅ Explore backend/app directory structure
3. ✅ Read through models/ and modules/ directories
4. ✅ Set up local development environment (optional)

### For Operations
1. ✅ Learn to manage orders and customers
2. ✅ Set up Shopify stores (Admin Dashboard)
3. ✅ Configure delivery partners
4. ✅ Test WhatsApp notifications

---

## 📞 Quick Reference

| Need | Find In | Read Time |
|------|---------|-----------|
| System overview | PRODUCTION_SYSTEM_OVERVIEW.md | 20 min |
| Quick start | README.md | 5 min |
| Operations | OPERATIONS_QUICK_REFERENCE.md | 10 min |
| Architecture | CODEBASE_STRUCTURE.md | 15 min |
| Features | PROJECT_HISTORY_AND_EVOLUTION.md | 10 min |
| Status | PRODUCTION_STATUS_REPORT.md | 5 min |

---

## 🎊 Welcome to Miguel CRM!

You now understand:
- ✅ What the system does
- ✅ How to access it
- ✅ Where the documentation is
- ✅ How the architecture works
- ✅ What features exist
- ✅ How to get help

**Ready to get started?**

→ Go to http://172.232.118.208/login  
→ Login with provided credentials  
→ Explore the dashboard  
→ Create a test order  
→ Try the edit feature  

**Enjoy!** 🚀

---

**Generated:** February 26, 2026  
**Status:** ✅ Complete & Ready to Share  
**Audience:** New team members, stakeholders, developers
