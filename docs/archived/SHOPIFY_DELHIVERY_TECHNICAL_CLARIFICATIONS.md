# Shopify + Delhivery Integration — Technical Clarifications Needed

**Purpose:** Before implementing, please provide these specific details  
**Date:** Feb 24, 2026

---

## 🔐 SECTION 1: API CREDENTIALS & SETUP

### Delhivery Configuration
```
[ ] API Base URL: https://track.delhivery.com/api  (Production)

[ ] API Key/Username: 37ce9815dcdb4a259163ef6ac8bc56beb3e6b252

[ ] Client Name (exact): purelevenexim

[ ] Pickup Location Name (exact):685561
    (Must match exactly as in Delhivery panel)

[ ] Shipment Types Available: Both
    [ ] Surface only
    [ ] Express only
    [ ] Both (need decision logic)

[ ] Do you have access to Delhivery Serviceability API? Not sure, check it
    [ ] Yes (we can auto-check pincode coverage)
    [ ] No (we'll assume all pincodes serviceable)
```

### Shopify Configuration
```
[ ] Shopify Store URL: purelevenexim.myshopify.com
Domains
Status
Actions
Online Store
pureleven.com
Primary
Connected
rwxtic-gz.myshopify.com
Connected
www.pureleven.com
Connected
Customer Account
orders.pureleven.com
Primary
Connected


    (e.g., mystore.myshopify.com)

[ ] Shopify Admin API Access Token: 

Client ID  : [REDACTED_CLIENT_ID_SHOPIFY]
Secret     : [REDACTED_SECRET_TOKEN_SHOPIFY]

[ ] API Type: both
    [ ] REST API
    [ ] GraphQL
    [ ] Both

[ ] Webhook Secret (for signature validation): ________________________

[ ] Are you using Shopify REST or GraphQL for orders?
    [ ] REST
    [ ] GraphQL
```

### WhatsApp Setup
```
[ ] WhatsApp Platform:
    [ ] Meta Cloud API (with phone number ID)
    [ ] Twilio
    [ ] Other: ________________________

[ ] WhatsApp Business Account Phone Number: ________________________

[ ] API Credentials:
    - Access Token: ________________________
    - Phone Number ID: ________________________
    - Business Account ID: ________________________
    (Or Twilio Account SID, Auth Token, etc.)

[ ] Webhook Verification Token (if using webhooks): ________________________
```

---

## 💰 SECTION 2: BUSINESS RULES & THRESHOLDS

### Order Value Controls
```
[ ] Maximum Order Value Before Blocking:
    ₹ ______________ (suggested: 50,000)
    
    Action: Block if order > this amount

[ ] Maximum COD Amount Before Requiring SMS Confirmation:
    ₹ ______________ (suggested: 10,000)
```

### Shipment Type Auto-Selection
```
[ ] Express Shipping Criteria:
    [ ] Use Delhivery serviceability API (auto-decide)
    [ ] Manual: List of pincodes/cities for Express
    
    If manual, provide:
    Express Pincodes: ________________________
    
[ ] Default: All others → Surface

[ ] Price difference tracking needed?
    [ ] Yes (store cost per shipment)
    [ ] No
```

### RTO Risk Thresholds
```
[ ] High RTO Zone Definition:
    RTO percentage > __________ % (suggested: 15%)

[ ] Medium RTO Zone Definition:
    RTO percentage > __________ % (suggested: 8%)

[ ] Do you have historical RTO data from Delhivery?
    [ ] Yes (share file for initial load)
    [ ] No (we'll build from current data)
```

### Blacklist & Customer Scoring
```
[ ] Auto-Blacklist Triggers:
    [ ] > __________ RTO orders
    [ ] > __________ NDR orders  
    [ ] > __________ COD failures
    [ ] High fraud risk score (> __________)

[ ] Blacklist Duration:
    [ ] Permanent
    [ ] Temporary (how many days? __________)
    [ ] Manual review only (no auto-blacklist)
```

---

## 📊 SECTION 3: OPERATIONAL DECISIONS

### COD & Payment Processing
```
[ ] COD Confirmation Flow:
    [ ] Automatic via WhatsApp (recommended)
    [ ] Manual admin approval
    [ ] No confirmation (skip and create shipment)

[ ] Confirmation Timeout:
    __________ minutes (suggested: 30 min)
    
    Action if no response: [ ] Cancel / [ ] Auto-create / [ ] Manual review

[ ] COD Reconciliation:
    [ ] Daily
    [ ] Weekly
    [ ] Monthly
    
    Who should receive reconciliation reports? ________________________

[ ] Remittance Tracking:
    [ ] Track in CRM only
    [ ] Create separate Finance module
    [ ] Integrate with accounting (QuickBooks/GST portal?)
```

### Notification Preferences
```
[ ] WhatsApp Notifications:
    
    COD Confirmation Request:
    [ ] Enabled with custom message
    Message: "Order {order_id} - ₹{amount} COD. Reply YES to confirm"
    
    Delivery Confirmation:
    [ ] Enabled with custom message
    Message: "Your order {order_id} has been delivered!"
    
    RTO Alert (to admin):
    [ ] Enabled
    Admin phone: ________________________
    
    NDR Alert (to customer):
    [ ] Enabled - auto-request new address via WhatsApp
    [ ] Manual admin review only

[ ] SMS Notifications:
    [ ] Enabled (provide Twilio/other credentials)
    [ ] Disabled (WhatsApp only)

[ ] Email Notifications:
    [ ] Send delivery confirmation to: ________________________
    [ ] Send RTO alerts to admin: ________________________
```

### Order Status & Workflow
```
[ ] Automatic Shipment Creation:
    [ ] On order/created webhook (ASAP)
    [ ] On payment confirmation
    [ ] On manual approval only
    
[ ] For unpaid orders:
    [ ] Create shipment anyway (Prepaid assumed)
    [ ] Wait for payment confirmation
    [ ] Manual review required

[ ] NDR Handling:
    [ ] Auto-send WhatsApp to customer asking for updated address
    [ ] Alert admin only (manual handling)
    [ ] Auto-create reattempt shipment
    
    How many NDR attempts? __________ (suggested: 1-2)

[ ] RTO (Return to Origin):
    [ ] Alert admin
    [ ] Auto-create new shipment? [ ] Yes / [ ] No
    [ ] Hold order? [ ] Yes / [ ] No
    [ ] Automatic refund? [ ] Yes / [ ] No
```

---

## 🏗️ SECTION 4: TECHNICAL INFRASTRUCTURE

### Processing Architecture
```
[ ] Shipment Creation:
    [ ] Synchronous (in webhook handler, immediate)
    [ ] Asynchronous (queue → background worker)
    
    If async, which system?
    [ ] Celery + Redis
    [ ] APScheduler
    [ ] AWS SQS
    [ ] Other: ________________________

[ ] Tracking Sync:
    Frequency: [ ] 15 min (your choice)
    
    Background job system:
    [ ] APScheduler (built into FastAPI)
    [ ] Celery
    [ ] Cron job (separate process)
    [ ] Other: ________________________

[ ] Expected Daily Order Volume:
    [ ] < 100 orders/day
    [ ] 100-1,000 orders/day
    [ ] 1,000-10,000 orders/day
    [ ] > 10,000 orders/day
    
    This affects architecture decisions.
```

### Database & Monitoring
```
[ ] Where should we store Delhivery responses?
    [ ] Store full JSON responses (for audit)
    [ ] Store only essential fields (to save space)

[ ] Do you want:
    [ ] Audit logs for all shipment changes (recommended)
    [ ] Alert mechanism for failed shipments
    [ ] Monitoring dashboard (Grafana/DataDog)

[ ] Data Retention:
    How many months of tracking history to keep? __________ months
```

---

## 🔄 SECTION 5: PRODUCTION READINESS

### Infrastructure
```
[ ] Is your Linode server publicly accessible?
    [ ] Yes (for Shopify webhooks to reach it)
    [ ] No (need webhook proxy/ngrok)

[ ] Do you use:
    [ ] HTTPS with valid SSL certificate?
    [ ] Docker for deployment?
    [ ] Load balancer (if expecting high volume)?

[ ] Database Backup Strategy:
    [ ] Daily automated backups
    [ ] Weekly backups
    [ ] Manual only
```

### Disaster Recovery
```
[ ] What if Delhivery API is down?
    [ ] Queue orders, retry when back up
    [ ] Manual override allowed
    [ ] Fail fast and alert admin

[ ] What if Shopify API is down?
    [ ] Queue updates, sync when back up
    [ ] Manual fallback
    [ ] Stop processing

[ ] Maximum acceptable downtime: __________ minutes/hours
```

### Testing & Rollout
```
[ ] Do you want:
    [ ] Sandbox/staging environment first?
    [ ] Production immediately?
    [ ] Gradual rollout (% of orders)?

[ ] Testing scope:
    [ ] Unit tests (code logic)
    [ ] Integration tests (API calls)
    [ ] End-to-end tests (full flow with real orders)

[ ] Gradual rollout percentage (if not 100%):
    Start with __________% of orders
    Ramp up to 100% over __________ days
```

---

## 📋 SECTION 6: ADVANCED FEATURES (Nice to Have)

```
[ ] Analytics Dashboard:
    [ ] Delivery success rate by state
    [ ] RTO % by pincode
    [ ] Average delivery days by courier
    [ ] Cost per shipment
    [ ] COD collection efficiency

[ ] Multi-Courier Support (Future):
    [ ] BlueDart
    [ ] DTDC
    [ ] India Post
    [ ] International couriers
    
    Who should decide which courier?
    [ ] System based on cost
    [ ] System based on delivery time
    [ ] Manual selection per order

[ ] Integration with Accounting:
    [ ] GST portal sync
    [ ] E-invoice generation
    [ ] Tax compliance reporting

[ ] Customer Portal:
    [ ] Customers can track from CRM directly?
    [ ] Customers can update delivery address before NDR?
    [ ] Self-service refund requests?
```

---

## ✅ CHECKLIST: What to Provide

Please fill out and provide:

**Credentials Checklist:**
- [ ] Delhivery API details
- [ ] Shopify store URL + token
- [ ] WhatsApp API credentials
- [ ] Admin contact numbers (for alerts)

**Configuration Checklist:**
- [ ] Order value thresholds
- [ ] RTO risk thresholds
- [ ] Notification preferences
- [ ] Processing architecture choice

**Infrastructure Checklist:**
- [ ] Server setup confirmation
- [ ] Volume expectations
- [ ] Backup strategy
- [ ] Testing approach

**Timeline:**
- [ ] When do you need this live?
- [ ] Any blackout dates?
- [ ] Priority: Speed vs. Perfect?

---

## 🚀 NEXT STEPS

Once you provide answers:

1. **I will generate:**
   - Complete FastAPI implementation
   - Database migration scripts
   - Service classes for all integrations
   - Unit & integration tests
   - Deployment guide

2. **You will get:**
   - Production-ready code
   - Architecture documentation
   - Operational runbooks
   - Monitoring setup

3. **Timeline:**
   - Phase 1 (Core): 1-2 weeks
   - Phase 2 (Risk Engine): 1-2 weeks
   - Phase 3 (Tracking): 1 week
   - Phase 4 (Dashboard): 1 week

---

**Format for Providing Answers:**

You can:
1. Fill this document directly (recommend)
2. Answer in conversation (I'll compile)
3. Provide CSV/JSON with config values

All information kept confidential. Ready to build? 🔥

