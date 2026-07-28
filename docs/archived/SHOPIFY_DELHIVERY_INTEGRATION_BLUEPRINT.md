# Shopify + Delhivery Integration Blueprint
## Logistics Intelligence Engine for Miguel CRM

**Date:** Feb 24, 2026  
**Status:** Architecture Design Phase  
**Scope:** Full automation with Risk Intelligence

---

## 📋 Confirmed Requirements Summary

### Business Configuration
- ✅ Single Shopify store
- ✅ Single warehouse
- ✅ Full end-to-end automation
- ✅ Auto-create shipment on order creation
- ✅ Product weight stored in Shopify
- ✅ Auto-select Surface/Express by pincode

### Financial Controls
- ✅ COD allowed with SMS confirmation before shipping
- ✅ COD reconciliation & remittance tracking in CRM
- ✅ Block shipments if:
  - Order value > threshold
  - Suspicious pincode (high RTO zone)
  - Customer blacklisted

### Tracking & Notifications
- ✅ 15-min tracking sync interval
- ✅ WhatsApp notifications for:
  - COD confirmation request
  - Delivery confirmation
  - RTO alerts to admin
- ✅ Update Shopify fulfillment on delivery
- ✅ RTO → Alert admin only (no auto-reattempt)

### Intelligence Features
- ✅ Detect high RTO pincodes
- ✅ Maintain customer blacklist
- ✅ Delivery scoring per customer
- ✅ NDR auto-handling (send WhatsApp retry)
- ✅ NO auto-reattempt shipments

---

## 🏗️ System Architecture

### Data Flow Diagram

```
┌─────────────────┐
│  Shopify Store  │
└────────┬────────┘
         │ (Webhook: order/created)
         ↓
┌─────────────────────────────┐
│  CRM Webhook Receiver       │
│  /webhooks/shopify/order    │
└────────┬────────────────────┘
         │
         ↓
┌─────────────────────────────┐
│  Risk Engine                │
│  - Value check              │
│  - Pincode RTO score        │
│  - Blacklist check          │
└────────┬────────────────────┘
         │
    Pass/Fail/Manual Review
         │
         ├─→ MANUAL REVIEW (holds order)
         │
         ↓ (if pass)
┌─────────────────────────────┐
│  COD Confirmation Service   │
│  (if COD order)             │
│  WhatsApp: "Confirm YES"    │
└────────┬────────────────────┘
         │
    Confirmed/Timeout
         │
         ├─→ HOLD (await confirmation)
         │
         ↓ (if confirmed)
┌─────────────────────────────┐
│  Shipment Creation Service  │
│  - Validate address         │
│  - Call Delhivery API       │
│  - Get AWB                  │
│  - Save shipment record     │
└────────┬────────────────────┘
         │
         ↓
┌─────────────────────────────┐
│  Push to Shopify            │
│  Update fulfillment with    │
│  tracking number            │
└────────┬────────────────────┘
         │
         ↓
┌─────────────────────────────┐
│  Queue for Tracking Sync    │
│  Background Worker          │
│  (every 15 minutes)         │
└────────┬────────────────────┘
         │
         ↓
┌─────────────────────────────┐
│  Event Engine               │
│  - Delivered → notify       │
│  - RTO → alert admin        │
│  - NDR → WhatsApp retry     │
└────────┬────────────────────┘
         │
         ↓
┌─────────────────────────────┐
│  Notification Service       │
│  - WhatsApp                 │
│  - SMS                      │
│  - Admin Dashboard          │
└─────────────────────────────┘
```

---

## 🗄️ Database Schema (SQLAlchemy Models)

### 1. Shipments Table
```python
class Shipment(Base):
    __tablename__ = "shipments"
    
    # Core IDs
    id = Column(UUID, primary_key=True)
    tenant_id = Column(UUID, ForeignKey("tenants.id"))
    order_id = Column(String, unique=True)  # Shopify order ID
    
    # Courier & AWB
    courier_partner = Column(String, default="Delhivery")  # For future multi-courier
    awb_number = Column(String, unique=True, nullable=True)
    tracking_url = Column(String, nullable=True)
    
    # Address & Logistics
    consignee_name = Column(String)
    consignee_phone = Column(String)
    consignee_address = Column(String)
    consignee_city = Column(String)
    consignee_state = Column(String)
    consignee_pincode = Column(String)
    
    # Shipment Details
    weight_kg = Column(Float)
    package_count = Column(Integer, default=1)
    shipment_type = Column(String)  # Surface / Express
    product_description = Column(String)
    
    # Financial
    order_value = Column(Decimal(10, 2))
    payment_mode = Column(String)  # Prepaid / COD
    cod_amount = Column(Decimal(10, 2), nullable=True)
    
    # Status Tracking
    shipment_status = Column(String, default="created")  # created, confirmed, in_transit, delivered, rto, ndr
    delivery_status = Column(String, nullable=True)
    last_tracking_update = Column(DateTime, nullable=True)
    delivery_date = Column(DateTime, nullable=True)
    
    # Risk Assessment
    risk_level = Column(String, nullable=True)  # low, medium, high
    manual_review_reason = Column(String, nullable=True)
    requires_manual_review = Column(Boolean, default=False)
    
    # RTO Handling
    rto_reason = Column(String, nullable=True)
    rto_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # API Responses (for debugging)
    delhivery_request_payload = Column(JSON, nullable=True)
    delhivery_response_payload = Column(JSON, nullable=True)
    shopify_fulfillment_id = Column(String, nullable=True)
```

### 2. Tracking Events Table
```python
class TrackingEvent(Base):
    __tablename__ = "tracking_events"
    
    id = Column(UUID, primary_key=True)
    shipment_id = Column(UUID, ForeignKey("shipments.id"))
    
    event_time = Column(DateTime)
    location = Column(String)
    status = Column(String)  # In Transit, Out for Delivery, Delivered, RTO, NDR
    remarks = Column(String, nullable=True)
    
    raw_response = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### 3. RTO Zones Table
```python
class RTOZone(Base):
    __tablename__ = "rto_zones"
    
    id = Column(UUID, primary_key=True)
    tenant_id = Column(UUID, ForeignKey("tenants.id"))
    
    pincode = Column(String, unique=True)
    city = Column(String)
    state = Column(String)
    
    total_shipments_30d = Column(Integer, default=0)
    rto_count_30d = Column(Integer, default=0)
    rto_percentage = Column(Float, default=0.0)
    
    risk_level = Column(String)  # low, medium, high (auto-calculated)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    created_at = Column(DateTime, default=datetime.utcnow)
```

### 4. Blacklisted Customers Table
```python
class BlacklistedCustomer(Base):
    __tablename__ = "blacklisted_customers"
    
    id = Column(UUID, primary_key=True)
    tenant_id = Column(UUID, ForeignKey("tenants.id"))
    
    phone_number = Column(String)
    email = Column(String, nullable=True)
    shopify_customer_id = Column(String, nullable=True)
    
    reason = Column(String)  # fraud, high_rto, high_ndr, repeated_cod_loss
    blocked_until = Column(DateTime, nullable=True)  # None = permanent
    
    rto_count = Column(Integer, default=0)
    ndr_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
```

### 5. Customer Delivery Score Table
```python
class CustomerDeliveryScore(Base):
    __tablename__ = "customer_delivery_scores"
    
    id = Column(UUID, primary_key=True)
    tenant_id = Column(UUID, ForeignKey("tenants.id"))
    shopify_customer_id = Column(String, unique=True)
    
    phone_number = Column(String)
    
    # Statistics
    total_orders = Column(Integer, default=0)
    successful_deliveries = Column(Integer, default=0)
    rto_count = Column(Integer, default=0)
    ndr_count = Column(Integer, default=0)
    cod_failed_count = Column(Integer, default=0)
    
    # Scores
    delivery_success_rate = Column(Float, default=100.0)
    risk_score = Column(Float, default=0.0)  # 0-100, higher = riskier
    
    last_order_date = Column(DateTime, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    created_at = Column(DateTime, default=datetime.utcnow)
```

### 6. COD Transactions Table
```python
class CODTransaction(Base):
    __tablename__ = "cod_transactions"
    
    id = Column(UUID, primary_key=True)
    tenant_id = Column(UUID, ForeignKey("tenants.id"))
    
    shipment_id = Column(UUID, ForeignKey("shipments.id"))
    order_id = Column(String)
    awb_number = Column(String)
    
    cod_amount = Column(Decimal(10, 2))
    remitted_amount = Column(Decimal(10, 2), nullable=True)
    
    status = Column(String)  # pending, remitted, failed
    remittance_date = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 7. Notification Log Table
```python
class NotificationLog(Base):
    __tablename__ = "notification_logs"
    
    id = Column(UUID, primary_key=True)
    tenant_id = Column(UUID, ForeignKey("tenants.id"))
    
    shipment_id = Column(UUID, ForeignKey("shipments.id"), nullable=True)
    
    notification_type = Column(String)  # cod_confirmation, delivery, rto, ndr
    channel = Column(String)  # whatsapp, sms, email
    recipient = Column(String)
    
    message = Column(String)
    status = Column(String)  # sent, failed, read
    
    response_payload = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

## 🔌 API Routes (FastAPI)

### 1. Shopify Webhook Receiver
```python
# POST /api/webhooks/shopify/order-created
# Receives: Shopify order webhook
# Triggers: Order intake → Risk check → Shipment creation

@router.post("/webhooks/shopify/order-created")
async def shopify_order_webhook(
    payload: ShopifyOrderWebhook,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Shopify sends webhook when order is created/paid.
    
    Flow:
    1. Validate webhook signature
    2. Parse order data
    3. Run risk engine
    4. If COD: send confirmation
    5. If pass: create shipment
    """
    # Implementation in next section
```

### 2. Risk Engine Endpoint
```python
# POST /api/shipments/validate-risk
# Input: order data
# Output: risk assessment + decision

@router.post("/api/shipments/validate-risk")
async def validate_shipment_risk(
    order: OrderData,
    db: Session = Depends(get_db),
    current_tenant = Depends(get_current_tenant),
):
    """
    Check if order is safe to ship:
    - Order value threshold
    - Pincode RTO score
    - Customer blacklist
    - Repeat fraud patterns
    
    Returns:
    {
        "status": "pass" | "fail" | "manual_review",
        "risk_level": "low" | "medium" | "high",
        "reason": "..."
    }
    """
```

### 3. COD Confirmation Service
```python
# POST /api/shipments/confirm-cod
# Trigger: WhatsApp confirmation from customer

@router.post("/api/shipments/confirm-cod")
async def confirm_cod_shipment(
    phone: str,
    order_id: str,
    confirmed: bool,
    db: Session = Depends(get_db),
):
    """
    Customer confirms COD via WhatsApp reply
    If confirmed → proceed to shipment creation
    If not confirmed → hold order
    """
```

### 4. Create Shipment Endpoint
```python
# POST /api/shipments/create
# Calls Delhivery API to create shipment

@router.post("/api/shipments/create")
async def create_shipment(
    order_id: str,
    db: Session = Depends(get_db),
    current_tenant = Depends(get_current_tenant),
):
    """
    Main shipment creation flow:
    
    1. Fetch order from Shopify
    2. Extract weight from products
    3. Validate address & phone
    4. Call Delhivery API
    5. Save AWB
    6. Push to Shopify fulfillment
    7. Queue for tracking sync
    
    Returns: shipment record with AWB
    """
```

### 5. Tracking Sync Endpoint
```python
# POST /api/shipments/sync-tracking
# Background worker: fetch tracking updates

@router.post("/api/shipments/sync-tracking")
async def sync_all_tracking(
    db: Session = Depends(get_db),
    current_tenant = Depends(get_current_tenant),
):
    """
    Background job (runs every 15 min):
    
    1. Get all shipments with status != delivered/rto
    2. For each AWB, call Delhivery tracking API
    3. Store tracking events
    4. Update shipment status
    5. If delivered: notify customer + update Shopify
    6. If RTO: alert admin + increase risk score
    7. If NDR: send WhatsApp with new address request
    """
```

### 6. Admin Shipment Dashboard
```python
# GET /api/shipments/dashboard
# Dashboard stats for admin

@router.get("/api/shipments/dashboard")
async def get_shipment_dashboard(
    date_range: str = "today",
    db: Session = Depends(get_db),
    current_tenant = Depends(get_current_tenant),
):
    """
    Returns:
    {
        "total_shipped": 45,
        "delivered_today": 12,
        "in_transit": 28,
        "rto_today": 3,
        "ndr_pending": 2,
        "pending_cod_confirmation": 5,
        "manual_review_queue": 2
    }
    """
```

---

## 🎯 Key Service Classes

### 1. DelhiveryService (Delhivery API Integration)

```python
class DelhiveryService:
    """
    Encapsulates all Delhivery API calls.
    Handles authentication, request formatting, error handling.
    """
    
    def __init__(self, api_key: str, client_name: str, pickup_location: str):
        self.api_key = api_key
        self.client_name = client_name
        self.pickup_location = pickup_location
        self.base_url = "https://track.delhivery.com/api"
    
    async def create_shipment(
        self,
        order_id: str,
        consignee_name: str,
        phone: str,
        address: str,
        city: str,
        state: str,
        pincode: str,
        weight_kg: float,
        order_value: float,
        payment_mode: str,
        cod_amount: float = 0,
        shipment_type: str = "Surface",
    ) -> dict:
        """
        Create shipment in Delhivery
        Returns: {"awb": "...", "status": "confirmed"}
        """
    
    async def track_shipment(self, awb: str) -> dict:
        """
        Get tracking status for shipment
        Returns: tracking events, current status, delivery date
        """
    
    async def check_serviceability(self, pincode: str) -> bool:
        """
        Check if pincode is serviceable
        Returns: True/False
        """
```

### 2. RiskEngine (Intelligent Risk Assessment)

```python
class RiskEngine:
    """
    Evaluates shipment risk before creation.
    Prevents fraud, COD losses, and wasted logistics.
    """
    
    async def assess_order_risk(
        self,
        order_id: str,
        customer_phone: str,
        order_value: float,
        pincode: str,
        payment_mode: str,
        is_first_order: bool,
        db: Session,
    ) -> dict:
        """
        Returns:
        {
            "status": "pass" | "fail" | "manual_review",
            "risk_level": "low" | "medium" | "high",
            "reason": "...",
            "actions": [...]
        }
        """
    
    async def check_value_threshold(self, order_value: float, threshold: float) -> bool:
        """Check if order exceeds value limit"""
    
    async def check_pincode_rto_risk(self, pincode: str, db: Session) -> float:
        """Get RTO score for pincode (0-100)"""
    
    async def check_customer_blacklist(self, phone: str, db: Session) -> bool:
        """Check if customer is blacklisted"""
    
    async def get_customer_risk_score(self, phone: str, db: Session) -> float:
        """Calculate customer risk score based on delivery history"""
```

### 3. ShopifyService (Shopify API Integration)

```python
class ShopifyService:
    """
    Integrates with Shopify REST API.
    Fetches orders, updates fulfillments, syncs tracking.
    """
    
    def __init__(self, store_url: str, access_token: str):
        self.store_url = store_url
        self.access_token = access_token
        self.headers = {
            "X-Shopify-Access-Token": access_token
        }
    
    async def get_order(self, order_id: str) -> dict:
        """Fetch order details from Shopify"""
    
    async def get_product_weight(self, product_id: str) -> float:
        """Get weight from product metafield"""
    
    async def create_fulfillment(
        self,
        order_id: str,
        tracking_number: str,
        tracking_company: str = "Delhivery",
    ) -> dict:
        """
        Update Shopify order with tracking number.
        Shopify will notify customer automatically.
        """
    
    async def notify_customer(
        self,
        order_id: str,
        notification_type: str,  # delivered, shipped, etc.
    ):
        """Send order update notification via Shopify"""
```

### 4. NotificationService (Multi-Channel)

```python
class NotificationService:
    """
    Sends notifications via WhatsApp, SMS, Email.
    Tracks delivery status for analytics.
    """
    
    async def send_cod_confirmation(
        self,
        phone: str,
        order_id: str,
        order_value: float,
    ) -> bool:
        """
        WhatsApp: "Order {order_id} - ₹{value} COD. Reply YES to confirm"
        """
    
    async def send_delivery_notification(
        self,
        phone: str,
        order_id: str,
        delivery_date: str,
    ):
        """
        WhatsApp: "Your order has been delivered. Thank you!"
        """
    
    async def send_rto_alert(
        self,
        admin_phone: str,
        order_id: str,
        awb: str,
        reason: str,
    ):
        """Admin alert: RTO occurred"""
    
    async def send_ndr_recovery(
        self,
        phone: str,
        order_id: str,
    ):
        """
        WhatsApp: "Delivery failed. Please reply with updated address"
        """
```

---

## 🔄 Background Worker (Celery / APScheduler)

### Tracking Sync Task (Every 15 minutes)

```python
@app.scheduled_task(interval=900)  # 15 minutes
async def sync_tracking_updates():
    """
    Every 15 minutes:
    1. Get all active shipments
    2. Call Delhivery tracking API
    3. Process delivery/RTO/NDR events
    4. Update customer scores
    5. Send notifications
    """
```

---

## 📞 Unanswered Technical Questions

Before implementation, please provide:

### API & Credentials
1. **Delhivery API Keys**
   - Base URL (production/staging)
   - API Key format
   - Client Name (exact spelling)
   - Pickup Location Code

2. **Shopify Integration**
   - Store URL
   - Admin API access token
   - Using REST API? (or GraphQL)
   - Webhook secret for signature validation

3. **WhatsApp Setup**
   - Using Meta Cloud API?
   - Or 3rd party provider?
   - Account credentials/keys
   - Phone number to send from

### Operational Parameters
1. **Value Thresholds**
   - Max order value before blocking? (e.g., ₹50,000)
   - Max COD amount before requiring confirmation? (e.g., ₹10,000)

2. **RTO Risk Configuration**
   - What RTO % = "High Risk"? (e.g., >15%)
   - What RTO % = "Medium Risk"? (e.g., >8%)

3. **Shipment Routing**
   - Metro/Tier-1 cities for Express (which pincodes?)
   - Or use Delhivery serviceability API to decide?

### Load & Scaling
1. **Expected Daily Volume**
   - <100 orders/day?
   - 100-1000 orders/day?
   - 1000+ orders/day?

2. **Processing**
   - Background queue system? (Celery/Redis)
   - Or synchronous processing?

---

## 📊 Implementation Phases

### Phase 1: Core Integration (Week 1-2)
- [ ] Database schema migration
- [ ] Shopify webhook receiver
- [ ] Delhivery API service class
- [ ] Basic shipment creation

### Phase 2: Risk Engine (Week 2-3)
- [ ] Risk assessment logic
- [ ] RTO zone tracking
- [ ] Customer scoring
- [ ] Blacklist management

### Phase 3: Tracking & Notifications (Week 3-4)
- [ ] 15-min tracking sync worker
- [ ] WhatsApp integration
- [ ] Event handlers (delivery/RTO/NDR)
- [ ] Notification logging

### Phase 4: Admin Dashboard (Week 4-5)
- [ ] Shipment management UI
- [ ] Risk alerts
- [ ] Analytics & reporting
- [ ] Manual override controls

---

## 🔐 Security Checklist

- [ ] Webhook signature validation (Shopify)
- [ ] API key encryption in database
- [ ] Rate limiting on Delhivery API calls
- [ ] Audit logs for all shipment changes
- [ ] Customer PII encryption
- [ ] Secure WhatsApp credential storage

---

## 🚀 Next Steps

1. **Provide missing credentials and parameters** (see unanswered questions)
2. **I will generate complete FastAPI implementation** (all routes + services)
3. **Database migrations** (Alembic scripts)
4. **Testing suite** (unit + integration tests)
5. **Deployment guide** (Docker + production setup)

This will be an enterprise-grade logistics engine. Ready to build? 🔥

