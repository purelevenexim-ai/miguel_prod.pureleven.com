# 🚀 Shipping Dashboard — Quick Start Guide

**Status:** Ready to Build  
**Complexity:** Medium (5 components per phase)  
**Time to Production:** 4-6 weeks  

---

## ⚡ 5-Minute Setup (Before You Code)

### Step 1: Generate Encryption Key

```bash
cd /opt/miguel/backend

# Generate key (run in Python)
python3 << 'EOF'
from cryptography.fernet import Fernet
key = Fernet.generate_key().decode()
print(f"ENCRYPTION_KEY={key}")
EOF

# Copy output and add to .env
echo "ENCRYPTION_KEY=<paste-output-here>" >> .env
```

### Step 2: Verify Current Structure

```bash
# Check if app/models exists
ls -la app/models/

# Should show: __init__.py, employee.py, orders.py, etc.

# Check if app/modules exists
ls -la app/modules/

# Should show: orders/, leads/, etc.
```

### Step 3: Install Dependencies (if needed)

```bash
# Add to requirements.txt if not present
echo "cryptography>=41.0.0" >> requirements.txt
echo "httpx>=0.25.0" >> requirements.txt

# Install
pip install -r requirements.txt
```

---

## 📁 What You'll Create (Phase by Phase)

```
backend/app/
├── models/
│   ├── shipping_config.py (NEW)  ← 4 database models
│
├── modules/
│   ├── shipping_config/  (NEW)
│   │   ├── __init__.py
│   │   ├── router.py     ← 20+ API endpoints
│   │   ├── schemas.py    ← Pydantic models
│   │   ├── service.py    ← Business logic + encryption
│
alembic/versions/
├── 003_add_shipping_config_tables.py (NEW)  ← Migration

frontend/components/ (NEW)
├── ShippingConfig/
│   ├── ShippingConfigDashboard.jsx
│   ├── ShippingConfig.css
│   ├── tabs/
│   │   ├── ShopifyStoresTab.jsx
│   │   ├── DeliveryPartnersTab.jsx
│   │   ├── NotificationsTab.jsx
│   │   ├── BusinessRulesTab.jsx
│   ├── forms/
│   │   ├── ShopifyStoreForm.jsx
│   │   ├── DeliveryPartnerForm.jsx
│   │   ├── NotificationChannelForm.jsx
│   │   ├── BusinessRulesForm.jsx
│   ├── lists/
│   │   ├── ShopifyStoreList.jsx
│   │   ├── DeliveryPartnerList.jsx
│   │   ├── NotificationChannelList.jsx
```

---

## 🔨 Build Sequence (What to Code First)

### Week 1: Backend Foundation

**Day 1-2: Database Layer**
1. Create `/opt/miguel/backend/app/models/shipping_config.py`
   - 4 models (ShopifyStore, DeliveryPartner, NotificationChannel, ShippingBusinessRules)
   - Copy from SHIPPING_CONFIGURATION_IMPLEMENTATION.md

2. Create `/opt/miguel/backend/app/modules/shipping_config/schemas.py`
   - Pydantic models for validation
   - Copy from SHIPPING_CONFIGURATION_IMPLEMENTATION.md

**Day 3-4: Business Logic**
3. Create `/opt/miguel/backend/app/modules/shipping_config/service.py`
   - Credential encryption/decryption
   - Connection testing functions
   - Partner configurations
   - Copy from SHIPPING_CONFIG_SERVICE_ENCRYPTION.md

4. Create `/opt/miguel/backend/app/modules/shipping_config/router.py`
   - FastAPI endpoints
   - Authentication/authorization
   - CRUD operations
   - Copy from SHIPPING_CONFIGURATION_IMPLEMENTATION.md

**Day 5: Database Migration**
5. Create `/opt/miguel/backend/alembic/versions/003_add_shipping_config_tables.py`
   - Migration script for 4 new tables
   - Copy from SHIPPING_CONFIGURATION_IMPLEMENTATION.md

6. Run migration:
```bash
cd /opt/miguel/backend
alembic upgrade head
```

### Week 2: Frontend UI

**Day 1-2: Main Dashboard**
7. Create `/opt/miguel/frontend/components/ShippingConfig/ShippingConfigDashboard.jsx`
   - Tab navigation
   - 4 sections (Shopify, Delivery, Notifications, Rules)

**Day 3: Shopify Integration UI**
8. Create `/opt/miguel/frontend/components/ShippingConfig/tabs/ShopifyStoresTab.jsx`
9. Create `/opt/miguel/frontend/components/ShippingConfig/forms/ShopifyStoreForm.jsx`
10. Create `/opt/miguel/frontend/components/ShippingConfig/lists/ShopifyStoreList.jsx`

**Day 4: Delivery Partners UI**
11. Create `/opt/miguel/frontend/components/ShippingConfig/tabs/DeliveryPartnersTab.jsx`
12. Create `/opt/miguel/frontend/components/ShippingConfig/forms/DeliveryPartnerForm.jsx`
13. Create `/opt/miguel/frontend/components/ShippingConfig/lists/DeliveryPartnerList.jsx`

**Day 5: Notifications & Rules UI**
14. Create `/opt/miguel/frontend/components/ShippingConfig/tabs/NotificationsTab.jsx`
15. Create `/opt/miguel/frontend/components/ShippingConfig/tabs/BusinessRulesTab.jsx`

### Week 3: Integration & Testing

- Connect frontend to backend APIs
- Test credential encryption
- Test multi-tenant isolation
- End-to-end testing

### Week 4: Documentation & Deployment

- Admin user guides
- API documentation
- Production deployment

---

## 🧪 Testing as You Build

### Test 1: Database Models (After Step 1)

```python
# Python REPL in backend directory
from app.models.shipping_config import ShopifyStore
from app.core.database import engine, Base

# Create tables
Base.metadata.create_all(bind=engine)
print("✅ Tables created")
```

### Test 2: Encryption Service (After Step 3)

```python
from app.modules.shipping_config.service import encrypt_credential, decrypt_credential

plaintext = "shpat_abc123xyz"
encrypted = encrypt_credential(plaintext)
decrypted = decrypt_credential(encrypted)

assert decrypted == plaintext
print("✅ Encryption working")
```

### Test 3: Shopify Connection (After Step 4)

```bash
# Start backend
cd /opt/miguel/backend
uvicorn app.main:app --reload

# Test endpoint (in another terminal)
curl -X POST http://localhost:8000/api/config/shopify-stores \
  -H "Content-Type: application/json" \
  -d '{
    "store_name": "Test Store",
    "store_url": "test.myshopify.com",
    "api_access_token": "shpat_test",
    "api_client_id": "test_id",
    "api_client_secret": "test_secret"
  }'
```

### Test 4: Frontend Components (After Step 7)

```bash
# In frontend directory
npm install @reach/tabs

# Start dev server
npm run dev

# Navigate to /config/shipping
```

---

## 📋 Before You Start Coding

### Checklist 1: Environment Setup

- [ ] `.env` file has `ENCRYPTION_KEY`
- [ ] `requirements.txt` includes `cryptography` and `httpx`
- [ ] Python 3.10+ installed
- [ ] PostgreSQL running
- [ ] Backend virtual environment activated

### Checklist 2: User Credentials Ready

You provided:
- ✅ Delhivery API Key: `37ce9815dcdb4a259163ef6ac8bc56beb3e6b252`
- ✅ Delhivery Client Name: `purelevenexim`
- ✅ Delhivery Pickup Location: `685561`
- ✅ Shopify Store URL: `purelevenexim.myshopify.com`
- ✅ Shopify Client ID: `0704646c7742dd2d8842e23a51d2a60e`
- ❓ Shopify API Token: `_not_shown_`
- ❓ WhatsApp Meta API Credentials: _needed_
- ❓ Business Rule Thresholds: _needed_

### Checklist 3: Decisions to Make

- [ ] Which delivery partners to support initially?
  - [ ] Delhivery (✅ ready)
  - [ ] Blue Dart
  - [ ] DTDC
  - [ ] India Post
  - [ ] Amazon Logistics

- [ ] Which notification channels?
  - [ ] WhatsApp Meta Cloud API (recommended)
  - [ ] SMS (Twilio)
  - [ ] Email (SendGrid)

- [ ] Business rule thresholds:
  - [ ] Max order value (default: ₹50,000)
  - [ ] Max COD amount (default: ₹10,000)
  - [ ] RTO threshold (default: 15%)
  - [ ] Auto-blacklist RTO count (default: 5)

---

## 🔗 Integration Points

### Where to Add Dashboard Link

**In `/opt/miguel/frontend/platform-admin.html`:**

```html
<nav class="admin-nav">
  <!-- Existing items -->
  <a href="index.html">📊 Dashboard</a>
  <a href="orders.html">📦 Orders</a>
  
  <!-- ADD THIS -->
  <a href="shipping-config.html">🚚 Shipping Config</a>
</nav>
```

**Create `/opt/miguel/frontend/shipping-config.html`:**

```html
<!DOCTYPE html>
<html>
<head>
  <title>Shipping Configuration</title>
  <link rel="stylesheet" href="ds.css">
</head>
<body>
  <div id="app"></div>
  <script src="/js/react.js"></script>
  <script src="/js/react-dom.js"></script>
  <script type="module">
    import ShippingConfigDashboard from './components/ShippingConfig/ShippingConfigDashboard.jsx';
    import { createRoot } from 'react-dom';
    
    const root = createRoot(document.getElementById('app'));
    root.render(<ShippingConfigDashboard />);
  </script>
</body>
</html>
```

---

## 🚀 Deploy to Production

### Step 1: Apply Migrations

```bash
cd /opt/miguel/backend
alembic upgrade head
```

### Step 2: Restart Backend

```bash
# If using Docker
docker-compose down
docker-compose up -d

# Or if running locally
pkill -f "uvicorn app.main"
uvicorn app.main:app --reload
```

### Step 3: Verify APIs

```bash
# List Shopify stores
curl http://localhost:8000/api/config/shopify-stores \
  -H "Authorization: Bearer <token>"

# Should return: []  (empty array, no stores yet)
```

---

## 📞 Support Resources

| File | Purpose |
|------|---------|
| SHIPPING_CONFIGURATION_IMPLEMENTATION.md | Step-by-step implementation |
| SHIPPING_CONFIG_SERVICE_ENCRYPTION.md | Encryption/security details |
| SHIPPING_CONFIGURATION_DASHBOARD_DESIGN.md | Complete design specs |
| SHOPIFY_DELHIVERY_INTEGRATION_BLUEPRINT.md | System architecture |

---

## ⚠️ Common Issues & Solutions

### Issue 1: `ImportError: No module named 'app.models.shipping_config'`

**Solution:** Make sure file exists and `__init__.py` is in the models directory

```bash
touch /opt/miguel/backend/app/models/__init__.py
```

### Issue 2: `Encryption key must be 44 characters`

**Solution:** Generate a new key:

```python
from cryptography.fernet import Fernet
key = Fernet.generate_key().decode()
print(len(key))  # Should be 44
```

### Issue 3: `ENCRYPTION_KEY not found in environment`

**Solution:** Set environment variable:

```bash
export ENCRYPTION_KEY="<your-key>"
# Or in .env file
echo "ENCRYPTION_KEY=<your-key>" >> /opt/miguel/backend/.env
```

### Issue 4: `401 Unauthorized` when testing Shopify connection

**Solution:** Verify API token is correct and hasn't expired

```bash
# In Shopify admin:
# Settings → Apps and integrations → App and integration settings → Develop apps
# Create new app or use existing
# Copy access token again
```

---

## 🎯 Success Criteria

After Phase 1 (Backend):
- ✅ 4 database tables created
- ✅ 20+ API endpoints working
- ✅ Credentials encrypted in database
- ✅ Connection testing works
- ✅ Multi-tenant isolation verified

After Phase 2 (Frontend):
- ✅ 4-tab dashboard renders
- ✅ Forms submit to backend
- ✅ Connection buttons test APIs
- ✅ Lists show configured items
- ✅ CRUD operations work

After Phase 3 (Integration):
- ✅ End-to-end workflow tested
- ✅ Security audit passed
- ✅ Multi-tenant isolation verified
- ✅ Encryption/decryption verified

After Phase 4 (Production):
- ✅ Documentation complete
- ✅ Admin trained
- ✅ Live in production
- ✅ Monitoring in place

---

## 📊 Progress Tracker

```
[████████░░░░░░░░░░] Phase 1: Backend (Week 1)
[░░░░░░░░░░░░░░░░░░] Phase 2: Frontend (Week 2)
[░░░░░░░░░░░░░░░░░░] Phase 3: Integration (Week 3)
[░░░░░░░░░░░░░░░░░░] Phase 4: Deploy (Week 4)
```

---

## 🎓 Learning Path (If New to Stack)

1. **FastAPI Basics**
   - Pydantic models (schemas)
   - Route decorators (@router.get, @router.post)
   - Dependency injection (Depends)
   - Read: https://fastapi.tiangolo.com/tutorial/

2. **SQLAlchemy ORM**
   - Column types, relationships
   - Session management
   - Filtering and queries
   - Read: https://docs.sqlalchemy.org/

3. **React Hooks**
   - useState for forms
   - useEffect for API calls
   - Custom hooks for async
   - Read: https://react.dev/reference/react

4. **REST API Design**
   - CRUD operations (POST/GET/PUT/DELETE)
   - Status codes (200, 201, 400, 401, 404)
   - Request/response structure

---

## 💡 Pro Tips

**Tip 1:** Test each component individually before connecting
- Test models in Python REPL
- Test routes with curl
- Test React components in isolation

**Tip 2:** Use meaningful error messages
- Users need to know what failed (invalid API key? network error?)
- Include troubleshooting hints

**Tip 3:** Add logging
```python
import logging
logger = logging.getLogger(__name__)
logger.info(f"Tested connection for store {store.id}: {result}")
```

**Tip 4:** Validate early
```python
# In schemas, use pydantic validators
from pydantic import validator

class ShopifyStoreCreate(BaseModel):
    store_url: str
    
    @validator('store_url')
    def validate_store_url(cls, v):
        if not v.endswith('.myshopify.com'):
            raise ValueError('Must be .myshopify.com domain')
        return v
```

---

## 🚀 Ready to Start?

### Next Action:
1. ✅ Copy code from SHIPPING_CONFIGURATION_IMPLEMENTATION.md
2. ✅ Create database models file
3. ✅ Create schemas file
4. ✅ Create service file
5. ✅ Create router file
6. ✅ Run migration
7. ✅ Test endpoints with curl
8. ✅ Build frontend components

**Total time:** 4-6 weeks to production  
**Complexity:** Medium (lots of CRUD, standard patterns)  
**Benefit:** Multi-tenant, secure, scalable shipping config  

Let's build! 🔥

