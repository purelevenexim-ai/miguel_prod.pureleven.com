# Multi-Tenant Shipping Integration Dashboard
## Configuration Management for Shopify + Delivery Partners

**Date:** Feb 24, 2026  
**Status:** Architecture Phase  
**Scope:** Tenant-Admin Configuration UI + Backend Services

---

## 📋 Overview

Instead of hardcoding API credentials, we'll build a **comprehensive configuration dashboard** where:

- ✅ **Each tenant manages their own integrations**
- ✅ **Separate sections for Shopify stores**
- ✅ **Separate sections for delivery partners**
- ✅ **Support for multiple integrations of each type**
- ✅ **Only tenant admins can access this section**
- ✅ **Secure credential storage with encryption**
- ✅ **Test connection buttons for verification**

---

## 🏗️ System Architecture

### Dashboard Navigation

```
Tenant Admin Dashboard
    ├─ Shipping Configuration (NEW)
    │   ├─ Shopify Stores
    │   │   ├─ List connected stores
    │   │   ├─ Add new store
    │   │   ├─ Edit store config
    │   │   └─ Test connection
    │   │
    │   ├─ Delivery Partners
    │   │   ├─ Delhivery (if enabled)
    │   │   ├─ Indian Post (if enabled)
    │   │   ├─ DTDC (if enabled)
    │   │   ├─ BlueDart (if enabled)
    │   │   ├─ Amazon (if enabled)
    │   │   ├─ Other providers
    │   │   └─ Add new partner
    │   │
    │   ├─ Notifications Setup
    │   │   ├─ WhatsApp Business API
    │   │   ├─ SMS Gateway (optional)
    │   │   └─ Email Configuration
    │   │
    │   └─ Business Rules
    │       ├─ Order value thresholds
    │       ├─ RTO risk zones
    │       ├─ Blacklist management
    │       └─ Notification preferences
    │
    └─ (Other existing sections)
```

---

## 🗄️ Database Schema

### 1. Shopify Stores (Multi-Store Support)
```python
class ShopifyStore(Base):
    __tablename__ = "shopify_stores"
    
    id = Column(UUID, primary_key=True)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=False)
    
    # Store Identity
    store_name = Column(String, nullable=False)  # e.g., "Pure Leven Main"
    store_url = Column(String, unique=True, nullable=False)  # purelevenexim.myshopify.com
    is_primary = Column(Boolean, default=False)  # Primary store for this tenant
    
    # Credentials (encrypted)
    api_access_token = Column(String, nullable=False)  # Encrypted
    api_client_id = Column(String, nullable=False)  # Encrypted
    api_client_secret = Column(String, nullable=False)  # Encrypted
    
    # API Configuration
    api_version = Column(String, default="2024-01")  # Shopify API version
    webhook_secret = Column(String, nullable=True)  # Encrypted - for signature validation
    webhook_topics = Column(JSON, nullable=True)  # ["orders/created", "orders/paid", ...]
    
    # Status
    is_active = Column(Boolean, default=True)
    is_connected = Column(Boolean, default=False)  # After successful test
    last_connection_test = Column(DateTime, nullable=True)
    last_sync = Column(DateTime, nullable=True)
    
    # Metadata
    custom_fields = Column(JSON, nullable=True)  # Store additional settings
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 2. Delivery Partners (Multi-Provider Support)
```python
class DeliveryPartner(Base):
    __tablename__ = "delivery_partners"
    
    id = Column(UUID, primary_key=True)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=False)
    
    # Partner Identity
    partner_name = Column(String, nullable=False)  # e.g., "Delhivery", "BlueDart"
    partner_type = Column(String, nullable=False)  # "delhivery", "india_post", "dtdc", "bluedart", "amazon"
    display_name = Column(String, nullable=False)  # e.g., "Delhivery Express"
    
    # API Credentials (encrypted)
    api_key = Column(String, nullable=False)
    api_secret = Column(String, nullable=True)  # Some providers need both
    client_name = Column(String, nullable=True)
    client_id = Column(String, nullable=True)
    
    # API Configuration
    api_base_url = Column(String, nullable=False)
    api_version = Column(String, nullable=True)
    
    # Provider-Specific Settings
    pickup_location_code = Column(String, nullable=True)
    warehouse_name = Column(String, nullable=True)
    warehouse_address = Column(String, nullable=True)
    warehouse_phone = Column(String, nullable=True)
    
    # Shipment Type Support
    supported_shipment_types = Column(JSON)  # ["surface", "express", "international"]
    default_shipment_type = Column(String, default="surface")
    
    # Service Areas
    coverage_areas = Column(JSON, nullable=True)  # Pincodes, cities, states covered
    
    # Status
    is_active = Column(Boolean, default=True)
    is_primary = Column(Boolean, default=False)  # Primary partner for auto-selection
    is_connected = Column(Boolean, default=False)  # After successful test
    last_connection_test = Column(DateTime, nullable=True)
    
    # Rate Configuration
    base_charge = Column(Decimal(10, 2), nullable=True)
    weight_rate_per_kg = Column(Decimal(10, 2), nullable=True)
    
    # Metadata
    custom_fields = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 3. Notification Channels
```python
class NotificationChannel(Base):
    __tablename__ = "notification_channels"
    
    id = Column(UUID, primary_key=True)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=False)
    
    # Channel Type
    channel_type = Column(String, nullable=False)  # "whatsapp", "sms", "email"
    provider = Column(String, nullable=False)  # "meta", "twilio", "sendgrid"
    
    # Credentials (encrypted)
    api_key = Column(String, nullable=False)
    api_secret = Column(String, nullable=True)
    access_token = Column(String, nullable=True)
    
    # Channel-Specific Settings
    phone_number = Column(String, nullable=True)  # For WhatsApp/SMS
    business_account_id = Column(String, nullable=True)
    phone_number_id = Column(String, nullable=True)  # WhatsApp
    sender_email = Column(String, nullable=True)  # Email
    
    # Configuration
    is_active = Column(Boolean, default=True)
    is_primary = Column(Boolean, default=False)
    is_connected = Column(Boolean, default=False)
    last_connection_test = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 4. Business Rules Configuration
```python
class ShippingBusinessRules(Base):
    __tablename__ = "shipping_business_rules"
    
    id = Column(UUID, primary_key=True)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=False, unique=True)
    
    # Order Value Controls
    max_order_value = Column(Decimal(10, 2), default=50000)  # ₹50,000
    max_cod_amount = Column(Decimal(10, 2), default=10000)  # ₹10,000
    
    # RTO Controls
    high_rto_threshold = Column(Float, default=15.0)  # 15%
    medium_rto_threshold = Column(Float, default=8.0)  # 8%
    
    # Customer Scoring
    auto_blacklist_rto_count = Column(Integer, default=5)
    auto_blacklist_ndr_count = Column(Integer, default=5)
    auto_blacklist_fraud_score = Column(Float, default=80.0)  # 0-100
    blacklist_duration_days = Column(Integer, nullable=True)  # None = permanent
    
    # COD Management
    require_cod_confirmation = Column(Boolean, default=True)
    cod_confirmation_timeout_minutes = Column(Integer, default=30)
    auto_create_reattempt_on_ndr = Column(Boolean, default=False)
    max_ndr_reattempts = Column(Integer, default=2)
    
    # Shipment Creation
    auto_create_on_order_created = Column(Boolean, default=True)
    auto_create_on_payment_confirmed = Column(Boolean, default=False)
    require_manual_approval = Column(Boolean, default=False)
    
    # Tracking
    tracking_sync_interval_minutes = Column(Integer, default=15)
    
    # Notifications
    send_delivery_confirmation = Column(Boolean, default=True)
    send_rto_alerts = Column(Boolean, default=True)
    send_ndr_alerts = Column(Boolean, default=True)
    notify_via_whatsapp = Column(Boolean, default=True)
    notify_via_sms = Column(Boolean, default=False)
    notify_via_email = Column(Boolean, default=False)
    
    # Admin Alerts
    admin_alert_on_rto = Column(Boolean, default=True)
    admin_alert_on_ndr = Column(Boolean, default=True)
    admin_alert_on_high_value_order = Column(Boolean, default=True)
    admin_emails = Column(JSON)  # ["admin@example.com", ...]
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

---

## 🔌 Backend API Routes

### Configuration Management Endpoints

```python
# ========== SHOPIFY STORES ==========

# GET list of stores for this tenant
@router.get("/api/config/shopify-stores")
async def list_shopify_stores(
    current_tenant = Depends(get_current_tenant),
    current_user = Depends(verify_tenant_admin),
):
    """List all Shopify stores configured for this tenant"""
    # Returns: [{"id": "...", "store_name": "...", "is_connected": true}, ...]

# POST create new Shopify store
@router.post("/api/config/shopify-stores")
async def create_shopify_store(
    store: ShopifyStoreCreate,
    current_tenant = Depends(get_current_tenant),
    current_user = Depends(verify_tenant_admin),
):
    """
    Create new Shopify store configuration
    
    Request:
    {
        "store_name": "Main Store",
        "store_url": "purelevenexim.myshopify.com",
        "api_access_token": "shpat_...",
        "api_client_id": "0704646c...",
        "api_client_secret": "shpss_...",
        "is_primary": true
    }
    """

# GET specific store config
@router.get("/api/config/shopify-stores/{store_id}")
async def get_shopify_store(
    store_id: str,
    current_tenant = Depends(get_current_tenant),
    current_user = Depends(verify_tenant_admin),
):
    """Get detailed config for specific store"""

# PUT update store config
@router.put("/api/config/shopify-stores/{store_id}")
async def update_shopify_store(
    store_id: str,
    store: ShopifyStoreUpdate,
    current_tenant = Depends(get_current_tenant),
    current_user = Depends(verify_tenant_admin),
):
    """Update store configuration"""

# POST test connection
@router.post("/api/config/shopify-stores/{store_id}/test-connection")
async def test_shopify_connection(
    store_id: str,
    current_tenant = Depends(get_current_tenant),
    current_user = Depends(verify_tenant_admin),
):
    """
    Test Shopify API connection
    Returns: {"status": "connected", "message": "Successfully authenticated"}
    """

# DELETE store
@router.delete("/api/config/shopify-stores/{store_id}")
async def delete_shopify_store(
    store_id: str,
    current_tenant = Depends(get_current_tenant),
    current_user = Depends(verify_tenant_admin),
):
    """Delete Shopify store configuration"""


# ========== DELIVERY PARTNERS ==========

# GET list of supported delivery partners
@router.get("/api/config/delivery-partners/available")
async def list_available_partners():
    """
    Get list of supported delivery partner types
    Returns:
    [
        {"id": "delhivery", "name": "Delhivery", "logo": "...", "docs": "..."},
        {"id": "bluedart", "name": "Blue Dart", "logo": "...", "docs": "..."},
        ...
    ]
    """

# GET configured delivery partners for tenant
@router.get("/api/config/delivery-partners")
async def list_delivery_partners(
    current_tenant = Depends(get_current_tenant),
    current_user = Depends(verify_tenant_admin),
):
    """List all delivery partners configured for this tenant"""

# POST add new delivery partner
@router.post("/api/config/delivery-partners")
async def create_delivery_partner(
    partner: DeliveryPartnerCreate,
    current_tenant = Depends(get_current_tenant),
    current_user = Depends(verify_tenant_admin),
):
    """
    Add new delivery partner configuration
    
    Request:
    {
        "partner_type": "delhivery",
        "display_name": "Delhivery Express",
        "api_key": "37ce9815...",
        "client_name": "purelevenexim",
        "pickup_location_code": "685561",
        "is_primary": true
    }
    """

# GET specific partner config
@router.get("/api/config/delivery-partners/{partner_id}")
async def get_delivery_partner(
    partner_id: str,
    current_tenant = Depends(get_current_tenant),
    current_user = Depends(verify_tenant_admin),
):
    """Get detailed config for specific partner"""

# PUT update partner config
@router.put("/api/config/delivery-partners/{partner_id}")
async def update_delivery_partner(
    partner_id: str,
    partner: DeliveryPartnerUpdate,
    current_tenant = Depends(get_current_tenant),
    current_user = Depends(verify_tenant_admin),
):
    """Update partner configuration"""

# POST test connection
@router.post("/api/config/delivery-partners/{partner_id}/test-connection")
async def test_delivery_partner_connection(
    partner_id: str,
    current_tenant = Depends(get_current_tenant),
    current_user = Depends(verify_tenant_admin),
):
    """
    Test delivery partner API connection
    Returns: {"status": "connected", "message": "Successfully authenticated"}
    """

# DELETE partner
@router.delete("/api/config/delivery-partners/{partner_id}")
async def delete_delivery_partner(
    partner_id: str,
    current_tenant = Depends(get_current_tenant),
    current_user = Depends(verify_tenant_admin),
):
    """Delete delivery partner configuration"""


# ========== NOTIFICATION CHANNELS ==========

@router.get("/api/config/notification-channels")
async def list_notification_channels(
    current_tenant = Depends(get_current_tenant),
    current_user = Depends(verify_tenant_admin),
):
    """List configured notification channels"""

@router.post("/api/config/notification-channels")
async def create_notification_channel(
    channel: NotificationChannelCreate,
    current_tenant = Depends(get_current_tenant),
    current_user = Depends(verify_tenant_admin),
):
    """Add WhatsApp, SMS, or Email configuration"""

@router.post("/api/config/notification-channels/{channel_id}/test")
async def test_notification_channel(
    channel_id: str,
    current_tenant = Depends(get_current_tenant),
    current_user = Depends(verify_tenant_admin),
):
    """Send test notification to verify connection"""


# ========== BUSINESS RULES ==========

@router.get("/api/config/business-rules")
async def get_business_rules(
    current_tenant = Depends(get_current_tenant),
    current_user = Depends(verify_tenant_admin),
):
    """Get all business rules for this tenant"""

@router.put("/api/config/business-rules")
async def update_business_rules(
    rules: ShippingBusinessRulesUpdate,
    current_tenant = Depends(get_current_tenant),
    current_user = Depends(verify_tenant_admin),
):
    """
    Update business rules
    
    Request:
    {
        "max_order_value": 50000,
        "max_cod_amount": 10000,
        "high_rto_threshold": 15.0,
        "require_cod_confirmation": true,
        "auto_create_on_order_created": true,
        ...
    }
    """
```

---

## 🎨 Frontend Dashboard UI (React/Vue)

### Shipping Configuration Page Structure

```
┌─────────────────────────────────────────────────────────────────┐
│ Shipping Integration Setup                          [← Back]     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ Tab Navigation:                                                  │
│ [Shopify Stores] [Delivery Partners] [Notifications] [Rules]    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TAB 1: SHOPIFY STORES                                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ [+ Add New Store]                                               │
│                                                                   │
│ Stores List:                                                     │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ Pure Leven Main                                          │   │
│ │ pureleven.myshopify.com                                 │   │
│ │ Status: ● Connected | Last sync: 2 hours ago           │   │
│ │ [Test] [Edit] [Webhooks] [Delete]                      │   │
│ └──────────────────────────────────────────────────────────┘   │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ Pure Leven B2B                                           │   │
│ │ rwxtic-gz.myshopify.com                                 │   │
│ │ Status: ● Connected | Last sync: 5 minutes ago         │   │
│ │ [Test] [Edit] [Webhooks] [Delete]                      │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TAB 2: DELIVERY PARTNERS                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ [+ Add New Partner]  Dropdown: [All Partners ▼]                 │
│                                                                   │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ 🔵 Delhivery (Primary)                                  │   │
│ │ Surface & Express  |  Status: ● Connected              │   │
│ │ Client: purelevenexim  |  Location: 685561             │   │
│ │ [Test] [Edit] [Coverage] [Delete]                      │   │
│ └──────────────────────────────────────────────────────────┘   │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ 🔵 Blue Dart                                            │   │
│ │ Express  |  Status: ⚪ Not Connected                    │   │
│ │ Client: BD001  |  Location: Mumbai                      │   │
│ │ [Test] [Edit] [Coverage] [Delete]                      │   │
│ └──────────────────────────────────────────────────────────┘   │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ 🔵 DTDC                                                 │   │
│ │ Surface  |  Status: ⚪ Not Connected                    │   │
│ │ [Configure] or [Delete if not needed]                  │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TAB 3: NOTIFICATIONS                                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ [+ Add Channel]                                                  │
│                                                                   │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ 💬 WhatsApp (Meta Cloud API)                            │   │
│ │ Status: ● Connected                                     │   │
│ │ Phone: +91-XXXXX-XXXXX                                  │   │
│ │ [Test Message] [Edit] [Logs] [Delete]                  │   │
│ └──────────────────────────────────────────────────────────┘   │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ 📧 Email (SendGrid)                                     │   │
│ │ Status: ⚪ Not Connected                                │   │
│ │ [Configure] or [Delete]                                │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TAB 4: BUSINESS RULES                                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ ORDER VALUE CONTROLS                                             │
│ ├─ Max Order Value: [50000] ₹                                  │
│ │  (Orders exceeding this will be marked for manual review)     │
│ │                                                                │
│ └─ Max COD Amount: [10000] ₹                                    │
│    (COD orders above this require customer confirmation)         │
│                                                                   │
│ RTO & RISK MANAGEMENT                                            │
│ ├─ High RTO Zone: [15] %                                        │
│ ├─ Medium RTO Zone: [8] %                                       │
│ ├─ Auto-blacklist on: [5] RTO incidents                         │
│ └─ Auto-blacklist on: [5] NDR incidents                         │
│                                                                   │
│ COD & NOTIFICATIONS                                              │
│ ├─ [✓] Require COD confirmation via WhatsApp                    │
│ ├─ [✓] Send delivery confirmation                               │
│ ├─ [✓] Send RTO alerts to admin                                 │
│ └─ [✓] Send NDR retry requests                                  │
│                                                                   │
│ SHIPMENT CREATION                                                │
│ ├─ [✓] Auto-create on order created                             │
│ ├─ [ ] Auto-create on payment confirmed                         │
│ └─ [ ] Require manual approval                                  │
│                                                                   │
│ [Save Rules]                                                     │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔐 Security Implementation

### Credential Encryption
```python
from cryptography.fernet import Fernet

class CredentialManager:
    """Secure encryption/decryption of API credentials"""
    
    def __init__(self, encryption_key: str):
        self.cipher = Fernet(encryption_key.encode())
    
    def encrypt_credential(self, value: str) -> str:
        """Encrypt sensitive credential before storing"""
        return self.cipher.encrypt(value.encode()).decode()
    
    def decrypt_credential(self, encrypted_value: str) -> str:
        """Decrypt credential when needed for API calls"""
        return self.cipher.decrypt(encrypted_value.encode()).decode()
```

### Access Control
```python
async def verify_tenant_admin(
    current_user: Employee = Depends(get_current_user),
    current_tenant = Depends(get_current_tenant),
) -> Employee:
    """
    Verify that current user is admin of their tenant
    Only tenant admins can access configuration
    """
    if current_user.role not in ["tenant_admin", "super_admin"]:
        raise HTTPException(
            status_code=403,
            detail="Only tenant admins can configure shipping integrations"
        )
    
    if current_user.tenant_id != current_tenant.id:
        raise HTTPException(
            status_code=403,
            detail="Cannot access configuration for other tenants"
        )
    
    return current_user
```

---

## 📊 Configuration Flow

### Add New Shopify Store

```
Tenant Admin
    ↓
Clicks: "Shipping Config" → "Shopify Stores" → "+ Add New"
    ↓
Form appears:
  • Store Name: [________________]
  • Store URL: [________________]
  • API Token: [________________]
  • Client ID: [________________]
  • Client Secret: [________________]
  • [Test Connection] [Save]
    ↓
Backend validates & encrypts credentials
    ↓
Saves to shopify_stores table
    ↓
Returns to list with "● Connected" status
```

### Add New Delivery Partner

```
Tenant Admin
    ↓
Clicks: "Shipping Config" → "Delivery Partners" → "+ Add New"
    ↓
Dropdown: [Select Partner Type ▼]
  • Delhivery
  • Blue Dart
  • DTDC
  • India Post
  • Amazon Logistics
    ↓
Form appears (fields vary by partner type):
  Delhivery:
    • Display Name: [________________]
    • API Key: [________________]
    • Client Name: [________________]
    • Pickup Location: [________________]
    • [Test Connection] [Save]
    ↓
Backend validates & encrypts
    ↓
Saves to delivery_partners table
    ↓
Returns to list with "● Connected" status
```

---

## 🔄 Runtime Integration

Once configured, the system uses the right credentials at runtime:

```python
async def get_active_shopify_store(
    tenant_id: str,
    db: Session
) -> ShopifyStore:
    """Get primary or first connected Shopify store"""
    store = db.query(ShopifyStore).filter(
        ShopifyStore.tenant_id == tenant_id,
        ShopifyStore.is_active == True,
        ShopifyStore.is_connected == True,
    ).order_by(
        ShopifyStore.is_primary.desc()
    ).first()
    
    if not store:
        raise Exception("No Shopify store configured for this tenant")
    
    return store


async def get_primary_delivery_partner(
    tenant_id: str,
    db: Session
) -> DeliveryPartner:
    """Get primary delivery partner for auto-selection"""
    partner = db.query(DeliveryPartner).filter(
        DeliveryPartner.tenant_id == tenant_id,
        DeliveryPartner.is_active == True,
        DeliveryPartner.is_connected == True,
        DeliveryPartner.is_primary == True,
    ).first()
    
    return partner


# Usage in shipment creation:
async def create_shipment_for_order(order_id: str, tenant_id: str, db: Session):
    # Get configured services for this tenant
    shopify_store = await get_active_shopify_store(tenant_id, db)
    delivery_partner = await get_primary_delivery_partner(tenant_id, db)
    
    # Use their credentials
    shopify_service = ShopifyService(
        store_url=shopify_store.store_url,
        access_token=decrypt_credential(shopify_store.api_access_token)
    )
    
    delhivery_service = DelhiveryService(
        api_key=decrypt_credential(delivery_partner.api_key),
        client_name=delivery_partner.client_name,
        pickup_location=delivery_partner.pickup_location_code
    )
    
    # ... rest of shipment logic
```

---

## 📋 Implementation Phases

### Phase 1: Backend Models & API (Week 1)
- [ ] Create SQLAlchemy models (4 tables)
- [ ] Create credential encryption service
- [ ] Create FastAPI routes (6 endpoints per section)
- [ ] Implement access control (tenant_admin only)
- [ ] Add database migrations

### Phase 2: Frontend Dashboard (Week 2)
- [ ] Create tabs navigation component
- [ ] Build Shopify stores form/list
- [ ] Build Delivery partners form/list
- [ ] Build Notifications configuration
- [ ] Build Business rules configuration
- [ ] Add test connection buttons

### Phase 3: Integration & Testing (Week 3)
- [ ] Connect dashboard to backend APIs
- [ ] Test credential encryption/decryption
- [ ] Test multi-tenant isolation
- [ ] End-to-end testing
- [ ] Security audit

### Phase 4: Documentation & Deployment (Week 4)
- [ ] Create admin user guide
- [ ] Create API documentation
- [ ] Deploy to production
- [ ] Train tenant admins

---

## ✅ Benefits of This Approach

1. **Multi-Tenant Ready** ✅
   - Each tenant manages own integrations
   - Complete isolation of credentials
   - No hardcoding required

2. **Scalable** ✅
   - Easy to add new delivery partners
   - Easy to add new notification channels
   - Multiple stores/partners per tenant

3. **Secure** ✅
   - Encrypted credentials
   - Access control (admin only)
   - Audit logs for changes

4. **User-Friendly** ✅
   - Visual dashboard
   - Test connection buttons
   - Clear status indicators

5. **Flexible** ✅
   - Set business rules per tenant
   - Choose which partners to use
   - Enable/disable integrations without code change

---

## 🚀 Next Steps

1. **Approve this design** (confirm structure is good)
2. **I generate complete FastAPI implementation** (models + routes)
3. **I create React/Vue dashboard components** (forms + UI)
4. **You test in staging** (with your real credentials)
5. **Deploy to production** (fully multi-tenant setup)

Ready to build this? 🔥

