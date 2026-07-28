# 🚀 PHASE 1: BACKEND DEVELOPMENT — START HERE

**Status:** Day 1 of 28  
**Goal:** Create database models and verify they work  
**Time:** 2-3 hours  
**Difficulty:** Easy (copy-paste + test)  

---

## ✅ Today's Tasks

### Task 1: Create Models File (30 minutes)

**File to create:** `/opt/miguel/backend/app/models/shipping_config.py`

**What to do:**
1. Open the file location in your editor
2. Copy all code from SHIPPING_CONFIGURATION_IMPLEMENTATION.md section "Step 1.1: Create Database Models"
3. Paste into the new file
4. Save the file

**Code to copy (from SHIPPING_CONFIGURATION_IMPLEMENTATION.md, lines 1-150):**
- ShopifyStore model
- DeliveryPartner model  
- NotificationChannel model
- ShippingBusinessRules model

**How to verify:**
```bash
# Check file exists
ls -la /opt/miguel/backend/app/models/shipping_config.py

# Should show the file (about 330 lines)
wc -l /opt/miguel/backend/app/models/shipping_config.py
```

---

### Task 2: Generate Encryption Key (5 minutes)

**What to do:**
1. Open terminal
2. Run this command:
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

3. Copy the output (should be ~44 characters starting with "g")
4. Add to your `.env` file:
```bash
echo "ENCRYPTION_KEY=<paste-your-key-here>" >> /opt/miguel/backend/.env
```

**How to verify:**
```bash
# Check it's in .env
grep ENCRYPTION_KEY /opt/miguel/backend/.env
# Should show: ENCRYPTION_KEY=your-key-here
```

---

### Task 3: Install Dependencies (5 minutes)

**What to do:**
```bash
cd /opt/miguel/backend
pip install cryptography httpx
```

**How to verify:**
```bash
python3 -c "import cryptography; import httpx; print('✓ Dependencies installed')"
# Should print: ✓ Dependencies installed
```

---

### Task 4: Test Models File (30 minutes)

**What to do:**
1. Start Python REPL:
```bash
cd /opt/miguel/backend
python3
```

2. Run these commands one by one:

```python
# Import the models
from app.models.shipping_config import (
    ShopifyStore, DeliveryPartner, 
    NotificationChannel, ShippingBusinessRules
)

print("✓ Models imported successfully")

# Check ShopifyStore fields
print(ShopifyStore.__tablename__)  # Should print: shopify_stores
print(dir(ShopifyStore))  # Should list all fields

# Check other models
print(DeliveryPartner.__tablename__)  # Should print: delivery_partners
print(NotificationChannel.__tablename__)  # Should print: notification_channels
print(ShippingBusinessRules.__tablename__)  # Should print: shipping_business_rules

# Exit Python
exit()
```

**Expected output:**
```
✓ Models imported successfully
shopify_stores
[... list of fields and methods ...]
delivery_partners
notification_channels
shipping_business_rules
```

**If you get errors:**
- Check that SHIPPING_CONFIGURATION_IMPLEMENTATION.md code was copied correctly
- Make sure all imports are present
- Verify SQLAlchemy version is compatible

---

### Task 5: Create Schemas File (30 minutes)

**File to create:** `/opt/miguel/backend/app/modules/shipping_config/schemas.py`

**First, create the directory:**
```bash
mkdir -p /opt/miguel/backend/app/modules/shipping_config
touch /opt/miguel/backend/app/modules/shipping_config/__init__.py
```

**Then copy code from SHIPPING_CONFIGURATION_IMPLEMENTATION.md:**
- Step 1.2: Create Pydantic Schemas
- All schema classes (Create, Update, Response)

**Expected file size:** ~280 lines

**How to verify:**
```bash
wc -l /opt/miguel/backend/app/modules/shipping_config/schemas.py
# Should show: ~280 lines
```

---

### Task 6: Test Schemas (30 minutes)

**What to do:**
```bash
cd /opt/miguel/backend
python3
```

```python
# Test importing schemas
from app.modules.shipping_config import schemas

print("✓ Schemas imported successfully")

# Test ShopifyStoreCreate schema
test_data = {
    "store_name": "Test Store",
    "store_url": "test.myshopify.com",
    "api_access_token": "shpat_test123",
    "api_client_id": "client_123",
    "api_client_secret": "secret_123",
    "is_primary": True
}

store = schemas.ShopifyStoreCreate(**test_data)
print(f"✓ ShopifyStoreCreate works: {store.store_name}")

# Test DeliveryPartnerCreate
partner_data = {
    "partner_type": "delhivery",
    "display_name": "Delhivery Express",
    "api_key": "api_key_test",
    "client_name": "test_client",
    "pickup_location_code": "123456",
}

partner = schemas.DeliveryPartnerCreate(**partner_data)
print(f"✓ DeliveryPartnerCreate works: {partner.display_name}")

exit()
```

**Expected output:**
```
✓ Schemas imported successfully
✓ ShopifyStoreCreate works: Test Store
✓ DeliveryPartnerCreate works: Delhivery Express
```

---

## 📋 Checklist - Day 1

- [ ] Created `/opt/miguel/backend/app/models/shipping_config.py` (330 lines)
- [ ] Generated encryption key and added to `.env`
- [ ] Installed `cryptography` and `httpx` dependencies
- [ ] Tested models in Python REPL (all 4 models imported)
- [ ] Created `/opt/miguel/backend/app/modules/shipping_config/` directory
- [ ] Created `/opt/miguel/backend/app/modules/shipping_config/schemas.py` (280 lines)
- [ ] Tested schemas in Python REPL (schemas work)

---

## ✅ Success Criteria

By end of Day 1:
- ✅ Models file created and working
- ✅ Schemas file created and working
- ✅ Encryption key set in `.env`
- ✅ Dependencies installed
- ✅ No import errors

**If all pass → You're ready for Day 2!**

---

## 🐛 Troubleshooting

### Error: `ModuleNotFoundError: No module named 'app.models.shipping_config'`

**Solution:**
```bash
# Make sure __init__.py exists in models directory
touch /opt/miguel/backend/app/models/__init__.py

# Verify the file exists
ls -la /opt/miguel/backend/app/models/__init__.py
```

### Error: `Encryption key must be 44 characters`

**Solution:**
Generate a new key:
```bash
python3 -c "from cryptography.fernet import Fernet; key = Fernet.generate_key().decode(); print(f'Length: {len(key)}'); print(f'Key: {key}')"

# Verify length is 44
```

### Error: `No module named 'cryptography'`

**Solution:**
```bash
pip install cryptography
pip install httpx
```

---

## 📚 Reference Files

| Need Help With | Read This |
|---|---|
| What the models do | SHIPPING_CONFIGURATION_DASHBOARD_DESIGN.md |
| Full code | SHIPPING_CONFIGURATION_IMPLEMENTATION.md |
| Security | SHIPPING_CONFIG_SERVICE_ENCRYPTION.md |
| Full schedule | SHIPPING_DASHBOARD_QUICK_START.md |

---

## ⏭️ Tomorrow (Day 2)

Tomorrow you'll:
1. Create the service layer (encryption & business logic)
2. Test credential encryption/decryption
3. Test Shopify connection function

**Time:** 3-4 hours

---

## 🎯 Ready to Start?

1. Open your editor
2. Go to `/opt/miguel/backend/app/models/`
3. Create new file: `shipping_config.py`
4. Copy code from SHIPPING_CONFIGURATION_IMPLEMENTATION.md
5. Save and test

**Let's go! 🚀**

