# India Post Implementation — Pending Tasks & Checklist

**Status:** Phase 1 ✅ Complete — Phases 2–4 🔴 Blocked on IP Whitelisting

---

## 🚫 Current Blocker

### IP Whitelisting Required
India Post sandbox server (`103.244.127.150`) not responding to our production server (`172.105.48.142`).

**Action:** Contact India Post support to whitelist:
- UAT Server: `172.232.118.208`
- Production Server: `172.105.48.142`

---

## ✅ Phase 1: Auto-Tariff Calculation (COMPLETE)

- [x] Backend API client (508 lines) with:
  - [x] Auth (login + token refresh)
  - [x] Tariff calculators (4 service types)
  - [x] Pincode lookup
  - [x] Tracking
  - [x] Label generation stub
  - [x] Connection test
- [x] Backend router (4 endpoints)
- [x] Frontend weight/dimensions panel
- [x] Auto-calculation with debounce
- [x] Auto-fill shipping cost
- [x] Pincode auto-lookup (city/state)
- [x] Rename "Customer IDs" → "Contract IDs"
- [x] Deploy to production
- [x] Test backend endpoints (import/restart OK)

### ❌ Missing (blocked by IP whitelisting)
- [ ] End-to-end test with sandbox API
- [ ] Live test with production credentials
- [ ] User acceptance testing

---

## 🔔 Phase 2: Booking & Labels (DESIGN PHASE)

**Timeline:** After IP whitelisting  
**Effort:** 8–12 hours

### Backend Tasks
- [ ] Create `/api/orders/{order_id}/book-india-post` endpoint
  - [ ] Collect weight, dimensions, service type
  - [ ] Call India Post booking API
  - [ ] Store article number + booking reference
  - [ ] Update order with tracking number
  - [ ] Handle errors gracefully
  
- [ ] Create `/api/shipments/{order_id}/generate-label` endpoint
  - [ ] Fetch booked article from order
  - [ ] Call India Post label API (PDF)
  - [ ] Return downloadable PDF
  - [ ] Store label in storage
  
- [ ] Database changes:
  - [ ] Add `ShipmentBooking` table
    - order_id, article_number, booking_date, status
  - [ ] Add columns to `Order`:
    - article_number, booking_date, label_url

### Frontend Tasks
- [ ] `orders.html`:
  - [ ] Add "Book Shipment" button (appears after tariff calc)
  - [ ] Loading state during booking
  - [ ] Success notification with article number
  - [ ] Error handling

- [ ] `invoices.html`:
  - [ ] Add "Print Label" button (if labeled)
  - [ ] Open label PDF in new window
  - [ ] Batch label printing (bulk select orders)

### Testing
- [ ] Unit test booking flow
- [ ] Test label generation
- [ ] Test error scenarios (duplicate booking, invalid weight)
- [ ] Sandbox testing with test customer ID

---

## 🎯 Phase 3: Webhook Integration (FEATURE PHASE)

**Timeline:** After Phase 2  
**Effort:** 16–20 hours  
**Complexity:** High (async, event processing)

### India Post Webhooks to Configure
1. **Article Created** → Order status: "booked"
2. **Article Assigned** → Store article number
3. **In Transit** → Order status: "shipped"
4. **Out for Delivery** → Order status: "in-delivery"
5. **Delivered** → Order status: "delivered"
6. **RTO Initiated** → Order status: "return"
7. **Returned** → Order status: "returned"
8. **Damaged/Lost** → Order status: "exception"

### Backend Tasks
- [ ] Create `POST /api/shipments/webhooks/india-post` endpoint
  - [ ] Verify webhook signature (HMAC-SHA256)
  - [ ] Parse payload (article_number, status, timestamp)
  - [ ] Update order status based on event
  - [ ] Log webhook in audit table
  - [ ] Handle duplicate events

- [ ] Create `WebhookLog` model
  - [ ] event_type, payload, processed_at, status
  - [ ] Index by order_id, article_number
  - [ ] Retention: 1 year

- [ ] Create notification system
  - [ ] `POST /api/notifications/send`
  - [ ] Email on status change
  - [ ] WhatsApp message (via WABIS)
  - [ ] SMS fallback

- [ ] Create order tracking timeline
  - [ ] `TrackingEvent` model
  - [ ] Display event history in orders.html

### Frontend Tasks
- [ ] `orders.html`:
  - [ ] Add "Tracking" tab showing timeline
  - [ ] Display each event: status, timestamp, description
  - [ ] Real-time updates (WebSocket or polling)
  - [ ] Expand/collapse details

### Database
- [ ] `WebhookLog` — Audit + error recovery
- [ ] `TrackingEvent` — Timeline display
- [ ] `Notification` — Sent notifications log

### Testing
- [ ] Simulate India Post webhook payloads
- [ ] Test status flow (created → delivered)
- [ ] Test error handling (malformed payload, duplicate)
- [ ] Test notification delivery
- [ ] Test concurrent webhook events

---

## 🚀 Phase 4: Advanced Features (ROADMAP)

**Timeline:** Future releases  
**Effort:** Varies per feature

### Batch Operations
- [ ] Bulk upload orders (CSV) with auto-tariff
- [ ] Batch booking (multiple orders at once)
- [ ] Bulk label printing
- [ ] Shipment scheduling (book on specific date)

### Smart Features
- [ ] Weight/dimension templates (common packages)
  - [ ] Save custom templates
  - [ ] Quick-select on order creation
  
- [ ] Tariff caching (30-min TTL)
  - [ ] Reduce API calls
  - [ ] Show rate confidence ("updated 5 mins ago")
  
- [ ] Rate cards dashboard
  - [ ] Historical rates visualization
  - [ ] Cost comparison (Speed Post vs Parcel)
  - [ ] Export rate cards as CSV

### Multi-Contract Support
- [ ] Allow multiple India Post accounts per tenant
- [ ] Route orders by service type → contract
- [ ] Contract utilization dashboard
- [ ] Cost allocation by contract

### Returns & RTO
- [ ] RTO (Return-to-Origin) handling
  - [ ] Automatic return booking
  - [ ] Refund calculation
  - [ ] Return label generation
  - [ ] Return tracking
  
- [ ] Reverse logistics
  - [ ] Return warehouse management
  - [ ] Stock reconciliation

### Advanced Integrations
- [ ] Duty calculator for international shipments
- [ ] Insurance claim filing
- [ ] VAT/GST reports by shipment
- [ ] Customs declaration forms
- [ ] Multi-carrier rate comparison

---

## 📋 Blocked Items (Waiting for IP Whitelisting)

| Item | Status | Blocker | Unblocks |
|------|--------|---------|----------|
| Sandbox testing | ❌ Blocked | IP not whitelisted | Phase 1 validation, Phase 2 dev |
| Production testing | ❌ Blocked | IP not whitelisted | Prod deployment confidence |
| User acceptance | ❌ Blocked | Sandbox offline | Release approval |
| Phase 2 start | ❌ Blocked | Phase 1 needs validation | Booking + labels |
| Go-live | ❌ Blocked | UAT needs to pass | Production launch |

---

## 🔄 Dependency Chain

```
IP Whitelisting (India Post)
        ↓
Phase 1 Validation (sandbox testing)
        ↓
Phase 2: Booking & Labels
        ↓
Phase 3: Webhooks (requires booking API)
        ↓
Phase 4: Advanced Features
```

---

## 📞 What to Do Now

### Today
1. **Create ticket with India Post** requesting IP whitelisting
   - Contact: support@indiapost.gov.in
   - Reference: Bulk Customer API, sandbox `test.cept.gov.in`
   - Server IPs: 172.232.118.208 (UAT), 172.105.48.142 (Prod)
   - Timeline: 1–3 business days (typical)

2. **Verify Phase 1 frontend** manually
   - No sandbox testing possible yet
   - But UI should render without errors

### After IP Whitelisting (Next Steps)
1. Test tariff calculation with sandbox credentials
2. Validate end-to-end workflow
3. Create test orders with auto-filled costs
4. Proceed to Phase 2 (booking)

---

## 📊 Progress Snapshot

| Phase | Status | Code Lines | Tests | Notes |
|-------|--------|-----------|-------|-------|
| 1 | ✅ Complete | 918 | ⚠️ Blocked | Code ready, awaiting IP whitelist |
| 2 | 🔴 Design | — | — | Ready to start after Phase 1 validate |
| 3 | 🔴 Design | — | — | Requires Phase 2 complete |
| 4 | 🔴 Roadmap | — | — | Future releases |

---

## 🎓 Implementation Notes

### For Backend Developers
- India Post API responses vary by service type
- Always check `success` field in response
- Token refresh happens automatically
- Tariff includes all taxes (CGST/SGST/IGST)
- Weight must be in grams, dimensions in cm

### For Frontend Developers
- Debounce tariff calls (800ms) to reduce API load
- Show loading indicator during calculation
- Display error messages prominently
- Auto-fill shipping cost only on successful response
- Validate pincode format (6 digits) before API call

### For DevOps
- Monitor India Post API latency (typical: 200–500ms)
- Set API timeout to 30 seconds
- Whitelist both server IPs on India Post side
- Log all webhook events for audit
- Backup webhook payloads before processing

---

**Last Updated:** March 2, 2026  
**Next Review:** After IP whitelisting confirmation  
**Assigned To:** Shipping team, Backend team
