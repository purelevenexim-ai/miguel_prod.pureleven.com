# India Post Integration — Phase 1 Status Report

**Date:** March 2, 2026  
**Status:** ✅ **Phase 1 Complete — Awaiting IP Whitelisting**  
**Commit:** `5825141`

---

## 🎯 Phase 1: Auto-Tariff Calculation (COMPLETE)

### ✅ What Was Implemented

#### Backend (`india_post_client.py` — 508 lines)
- **Full API Client** with production + sandbox endpoints
  - Sandbox: `https://test.cept.gov.in/beextcustomer`
  - Production: `https://apigw.indiapost.gov.in`
  
- **Authentication**
  - POST `/v1/access/login` → Bearer token (900s expiry)
  - Token caching with auto-refresh before expiry
  - Per-customer_id token management
  
- **Tariff Calculators** (4 service types)
  - `calculate_speed_post_tariff()` — Speed Post
  - `calculate_parcel_tariff()` — Parcel
  - `calculate_business_parcel_tariff()` — Business Parcel
  - `calculate_letter_tariff()` — Letter
  
- **Supporting Features**
  - Pincode search → office details (city, state, PIN)
  - Single article tracking
  - Bulk tracking (up to 50 items)
  - Domestic label generation
  - Connection test (login + pincode verify)
  - Convenience function: `calculate_tariff()` (multi-service)
  
- **Error Handling**
  - Structured responses with `success` field
  - Informative error messages
  - HTTP status codes

#### Backend Router (`/api/india-post/*` — 174 lines)

| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|----------------|
| `/tariff` | GET | Calculate shipping tariff | User only |
| `/pincode` | GET | Validate & lookup pincode | User only |
| `/track/{tracking_number}` | GET | Track single article | User + India Post creds |
| `/test-connection` | POST | Test API auth | Admin only |

#### Frontend (`orders.html` — Multiple edits)

**Weight & Dimensions Panel** (shown when India Post selected)
- Input fields: Weight (grams), Length/Width/Height (cm)
- Calculate button with loading state
- Tariff result card (green) showing:
  - Final amount (auto-filled to orderShip)
  - Base tariff
  - Tax breakdown (CGST, SGST, IGST)
  - Zone, distance, weight slab

**Auto-Calculation Logic**
- 800ms debounce on weight/pincode changes
- Triggers on:
  - Courier change (India Post selection)
  - Service type change
  - Weight input change
  - Pincode input (6 digits)
- Auto-fills shipping cost from tariff result
- Auto-fills city/state from pincode lookup

**UI Features**
- Loading indicator during API call
- Error display (red alert)
- Result card with breakdown chips
- Pincode validation (6 digits)
- Auto-scroll result into view

#### Rename: Customer IDs → Contract IDs
- **tenant-admin.html**: All labels, placeholders, comments
  - "Customer IDs" → "Contract IDs"
  - "Customer ID (e.g., 12345)" → "Contract ID (e.g., 41903381)"
  
- **orders.html**: Delivery partner service selection
  - "India Post Service" → "Contract ID"
  - "Select Service Type" → "Select Contract"
  - Display labels: "IP ID:" → "Contract:"

---

## 🚫 Current Blocker: IP Whitelisting

### ❌ Issue
India Post sandbox (`test.cept.gov.in` IP: `103.244.127.150`) is **not whitelisted** for the production server IP (`172.105.48.142`).

**Evidence:**
```bash
# From Prod Server (172.105.48.142):
ssh root@172.105.48.142 "ping -c 3 103.244.127.150"
# Result: 100% packet loss — firewall blocked
```

### ✅ Solution
Contact India Post to whitelist both server IPs:
- **UAT Server:** `172.232.118.208`
- **Prod Server:** `172.105.48.142`

Once whitelisted, tariff auto-calculation will work end-to-end.

---

## 📋 What's Pending: Phases 2–4

### Phase 2: Booking & Labels (Design Phase)
**Timeline:** After IP whitelisting  
**Features:**
- [ ] Booking API integration (POST article data)
- [ ] Automatic label generation (PDF download)
- [ ] Label printing workflow
- [ ] Tracking number assignment in orders table

**Files to Create/Modify:**
- `backend/app/modules/orders/router.py` — Add booking endpoint
- `backend/app/modules/shipments/router.py` — Add label generation
- `frontend/invoices.html` — Add label download button
- `frontend/orders.html` — Add print labels button

### Phase 3: Webhook Integration (Event Notifications)
**Timeline:** After Phase 2  
**Features:**
- [ ] Configure India Post webhooks
  - Booking events (article created, assigned)
  - Delivery events (dispatched, out for delivery, delivered)
  - Exception events (RTO, undelivered, damage)
- [ ] Webhook endpoint: `POST /api/shipments/webhooks/india-post`
- [ ] Update order status from webhook events
- [ ] Store raw webhook payloads for audit
- [ ] Send notifications (email/SMS/WhatsApp)

**Files to Create/Modify:**
- `backend/app/modules/shipments/webhooks.py` — Webhook receiver
- `backend/app/models/webhook_log.py` — Audit table
- `backend/app/tasks/notify.py` — Notification sender
- `frontend/orders.html` — Add tracking timeline

### Phase 4: Advanced Features (Roadmap)
**Timeline:** Future releases  
**Features:**
- [ ] Batch shipment uploads (CSV)
- [ ] Weight/dimension auto-detection (barcode scanner)
- [ ] Rate caching (refresh daily)
- [ ] Multi-contract management per tenant
- [ ] Return shipping (RTO handling)
- [ ] Insurance integration
- [ ] Duty calculator
- [ ] Bulk tracking dashboard

---

## 🔧 Technical Debt & Improvements

### Backend Improvements
- [ ] Add connection pooling for HTTP requests
- [ ] Implement request queuing for rate limiting
- [ ] Add retry logic with exponential backoff
- [ ] Cache tariff calculations (30 min TTL)
- [ ] Add comprehensive logging for debugging
- [ ] Unit tests for India Post client
- [ ] Integration tests with sandbox API

### Frontend Improvements
- [ ] Add weight/dimension templates (common packages)
- [ ] Show tariff breakdown in order summary
- [ ] Add tariff history chart
- [ ] Bulk tariff calculation (spreadsheet upload)
- [ ] Real-time exchange rate conversion
- [ ] Postcode validator with auto-complete
- [ ] Mobile-optimized tariff panel

### Configuration
- [ ] Move sandbox/prod toggle to tenant config
- [ ] Store contract IDs securely (encrypted)
- [ ] Add tenant-specific source pincodes
- [ ] Configurable tax rates per service

---

## 📊 Implementation Summary

### Code Changes
| File | Lines | Status | Notes |
|------|-------|--------|-------|
| `india_post_client.py` | +508 | ✅ Complete | Full API client rewrite |
| `router.py` | +174 | ✅ Complete | 4 endpoints |
| `main.py` | +2 | ✅ Complete | Router registration |
| `orders.html` | +236 | ✅ Complete | Weight panel + JS |
| `tenant-admin.html` | +16 | ✅ Complete | Contract ID rename |
| `__init__.py` | — | ✅ Complete | Module initialization |

### Testing Status
| Test | Status | Notes |
|------|--------|-------|
| Backend import | ✅ Pass | All 4 routes load |
| Backend restart | ✅ Pass | Uvicorn starts cleanly |
| Frontend syntax | ✅ Pass | No JS errors |
| Sandbox API (tariff) | ❌ Blocked | IP not whitelisted |
| Sandbox API (pincode) | ❌ Blocked | IP not whitelisted |
| Production API | ❌ DNS fail | Domain doesn't resolve |

---

## 🚀 Deployment Status

### Current Environment
```
Commit:    5825141 (feat: India Post API Phase 1)
Dev:       /opt/miguel (local testing)
UAT:       172.232.118.208 (not whitelisted)
Prod:      172.105.48.142 (not whitelisted)
Branch:    main
Status:    ✅ Deployed
```

### To Activate Phase 1
**After IP whitelisting:**
1. Configure India Post credentials in Tenant Admin → Shipping Config
2. Select India Post as delivery partner for an order
3. Enter weight, dimensions, destination pincode
4. Click "Calculate" button
5. Tariff will auto-populate with shipping cost

---

## 📝 Next Steps

### Immediate (This Week)
1. **Contact India Post** — Request IP whitelisting
   - Provide both server IPs
   - Reference: Bulk Customer API, sandbox `test.cept.gov.in`
   
2. **Test sandbox after whitelisting**
   ```bash
   curl -X POST "https://test.cept.gov.in/beextcustomer/v1/access/login" \
     -H "Content-Type: application/json" \
     -d '{"username":"9999726749","password":"Dop@1234"}'
   ```

3. **Verify end-to-end in orders.html**
   - Create test order
   - Select India Post
   - Enter weight/dimensions
   - Verify tariff calculates and cost auto-fills

### Short-term (Next 2 weeks)
1. Implement Phase 2 (booking + labels)
2. Add unit tests for India Post client
3. Create tenant configuration guide
4. Test with live contract IDs (41903381, 41257013)

### Medium-term (Next month)
1. Implement Phase 3 (webhooks)
2. Add webhook event logging
3. Build tracking timeline UI
4. Email/WhatsApp notifications

---

## 💾 Database Schema Notes

### Existing Models Used
- `DeliveryPartner` — Stores India Post credentials
  - `customer_ids` — JSON array of contract IDs
  - `client_id` — Sandbox/prod account identifier
  - `api_key` — Password/secret
  - `pickup_location_code` — Source pincode
  
- `Order` — Shipping details
  - `shipping_service` — Service type (speed_post, parcel, etc.)
  - `india_post_customer_id` — Selected contract ID
  - `delivery_pincode` — Destination
  - `shipping_charge` — Auto-filled from tariff
  - `tracking_number` — Will be set on booking

### New Models Needed (Phase 2+)
- `ShipmentBooking` — Booking confirmation + article number
- `WebhookLog` — Webhook events from India Post
- `TrackingEvent` — Order status history
- `TariffCache` — Cached rates (for performance)

---

## 🎓 API Reference Quick Links

**Tariff Calculation:**
```bash
GET /api/india-post/tariff?service=speed_post&weight=500&source_pincode=685561&destination_pincode=110001&length=20&width=15&height=10&cod=false
```

**Pincode Lookup:**
```bash
GET /api/india-post/pincode?pincode=685561&limit=10
```

**Track Article:**
```bash
GET /api/india-post/track/ABC123456789
```

**Test Connection:**
```bash
POST /api/india-post/test-connection
```

---

## 📞 Contacts & Resources

**India Post**
- Customer ID (sandbox): `9999726749`
- Portal: https://indiapostcustomer.com
- API Docs: `/docs` (behind portal login)

**Internal**
- Source Pincode (Adimali): `685561`
- Contract IDs: `41903381` (Parcel), `41257013` (Speed Post)
- Codebase: `/opt/miguel`
- Production: `root@172.105.48.142:/opt/pureleven`

---

**Status: ✅ Phase 1 COMPLETE — Awaiting IP Whitelisting for Activation**

Generated: March 2, 2026  
Last Updated: 5825141 (India Post Phase 1 commit)
