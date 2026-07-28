# 📋 PENDING WORK & NEXT STEPS

**Date**: February 24, 2026  
**Current Phase**: 12 (WA Engine v2) — Complete  
**Next Phase**: 13 (SaaS Billing) — Not Started  
**Status**: All core features production-ready, enhancements needed

---

## 🔴 WHAT NEEDS TO BE DONE

### Priority 1: CRITICAL (Next 7 Days) ⚠️

#### 1. **Install Automated Testing Framework**
- **Current State**: Manual testing only, pytest not installed
- **What to Do**:
  1. Install pytest and dependencies
     ```bash
     cd /opt/miguel/backend
     pip install pytest pytest-asyncio httpx python-multipart
     ```
  2. Create `/opt/miguel/backend/tests/conftest.py` with test database setup
  3. Create test files for core modules:
     - `tests/test_auth.py` (login, token refresh)
     - `tests/test_leads.py` (CRUD, status changes)
     - `tests/test_orders.py` (create, payment flow)
     - `tests/test_gst.py` (report generation)
  4. Run full test suite: `pytest -v`
- **Effort**: 20 hours
- **Impact**: HIGH (confidence in deployments)
- **Files to Create**:
  - `/opt/miguel/backend/tests/conftest.py` (test config)
  - `/opt/miguel/backend/tests/test_*.py` (6-8 test files)

#### 2. **Add Two-Factor Authentication (2FA)**
- **Current State**: Only email + password
- **What to Do**:
  1. Add OTP fields to Employee model:
     ```python
     otp_secret: Optional[str]
     otp_enabled: bool = False
     backup_codes: Optional[str]  # JSON array
     ```
  2. Create new migration for OTP schema
  3. Add TOTP (Time-based OTP) generation:
     ```python
     pip install pyotp
     ```
  4. Create endpoints:
     - `POST /api/auth/setup-2fa` (generate secret)
     - `POST /api/auth/verify-2fa` (verify code)
     - `POST /api/auth/enable-2fa` (enable OTP)
  5. Update login flow:
     - After password match, prompt for OTP
     - Validate OTP before issuing JWT
  6. Frontend:
     - Add OTP input form after password
     - Show QR code for secret setup
- **Effort**: 15 hours
- **Impact**: HIGH (security)
- **Files to Modify**:
  - `/opt/miguel/backend/app/models/employee.py` (add OTP fields)
  - `/opt/miguel/backend/app/modules/employee_auth/router.py` (2 new endpoints)
  - `/opt/miguel/backend/app/modules/employee_auth/service.py` (OTP logic)
  - `/opt/miguel/frontend/tenant-login.html` (OTP input)
  - `/opt/miguel/backend/alembic/versions/` (new migration)

#### 3. **Implement Rate Limiting**
- **Current State**: No rate limiting, API can be abused
- **What to Do**:
  1. Install `slowapi`:
     ```bash
     pip install slowapi
     ```
  2. Configure in `main.py`:
     ```python
     from slowapi import Limiter
     limiter = Limiter(key_func=get_remote_address)
     app.state.limiter = limiter
     ```
  3. Add rate limits:
     - Login: 5 attempts per minute
     - API general: 100 requests per minute
     - API heavy (export): 10 requests per minute
  4. Test with curl:
     ```bash
     for i in {1..10}; do curl -i http://localhost:8000/api/orders/; done
     ```
- **Effort**: 8 hours
- **Impact**: HIGH (security)
- **Files to Modify**:
  - `/opt/miguel/backend/app/main.py` (configure limiter)
  - `/opt/miguel/backend/app/modules/*/router.py` (add @limiter decorators)

#### 4. **Email Verification for Customers**
- **Current State**: Customer emails not verified
- **What to Do**:
  1. Add fields to Customer model:
     ```python
     email_verified: bool = False
     email_verification_token: Optional[str]
     email_verified_at: Optional[datetime]
     ```
  2. Create endpoint `POST /api/customers/{id}/send-verification-email`
  3. Send email with verification link:
     ```python
     pip install python-dotenv aiosmtplib
     # Link: {base_url}/api/customers/verify-email?token={token}
     ```
  4. Create endpoint `POST /api/customers/verify-email?token=...`
  5. Frontend: Show "Email not verified" badge, allow resend
- **Effort**: 12 hours
- **Impact**: MEDIUM (data quality)
- **Files to Create/Modify**:
  - `/opt/miguel/backend/app/models/customer.py` (3 new fields)
  - `/opt/miguel/backend/app/core/email.py` (new, email sending)
  - `/opt/miguel/backend/app/modules/customers/router.py` (2 new endpoints)
  - `/opt/miguel/backend/alembic/versions/` (new migration)
  - `/opt/miguel/frontend/customers.html` (verification badge)

---

### Priority 2: IMPORTANT (Next 30 Days) 📋

#### 5. **Add Caching Layer (Redis)**
- **Current State**: Every query hits database
- **What to Do**:
  1. Add Redis to docker-compose:
     ```yaml
     redis:
       image: redis:7-alpine
       ports:
         - "6379:6379"
     ```
  2. Install `redis` client:
     ```bash
     pip install redis aioredis
     ```
  3. Cache hot data:
     - Lead list for tenant: TTL 5 min
     - Customer list for tenant: TTL 5 min
     - Product catalog: TTL 1 hour
     - Settings/config: TTL 1 day
  4. Invalidate on write:
     - Create lead → clear `leads:tenant_id:*`
     - Update order → clear `orders:tenant_id:*`
  5. Measure improvement:
     ```bash
     # Before: API response time 200ms
     # After: API response time 20ms (expected)
     ```
- **Effort**: 25 hours
- **Impact**: HIGH (performance)
- **Files to Create/Modify**:
  - `/opt/miguel/backend/app/core/cache.py` (new, cache utilities)
  - `/opt/miguel/docker-compose.yml` (add redis service)
  - `/opt/miguel/backend/app/modules/leads/service.py` (add caching)
  - `/opt/miguel/backend/app/modules/orders/service.py` (add caching)
  - `/opt/miguel/backend/app/modules/customers/service.py` (add caching)

#### 6. **Implement Database Backups**
- **Current State**: No automated backups
- **What to Do**:
  1. Create backup script:
     ```bash
     #!/bin/bash
     # /opt/miguel/scripts/backup.sh
     TIMESTAMP=$(date +%Y%m%d_%H%M%S)
     docker-compose exec -T db pg_dump -U miguel_user miguel_db > backups/miguel_$TIMESTAMP.sql
     gzip backups/miguel_$TIMESTAMP.sql
     ```
  2. Schedule with cron:
     ```bash
     # Every day at 2 AM
     0 2 * * * /opt/miguel/scripts/backup.sh
     ```
  3. Add S3 upload (optional):
     ```python
     pip install boto3
     # Upload to S3 bucket
     ```
  4. Create restore script:
     ```bash
     docker-compose exec -T db psql -U miguel_user miguel_db < backup.sql
     ```
- **Effort**: 10 hours
- **Impact**: CRITICAL (disaster recovery)
- **Files to Create**:
  - `/opt/miguel/scripts/backup.sh` (backup script)
  - `/opt/miguel/scripts/restore.sh` (restore script)
  - `/opt/miguel/.crontab` (cron schedule)

#### 7. **Add Logging to S3**
- **Current State**: Logs only in docker logs (lost on container restart)
- **What to Do**:
  1. Install logging utilities:
     ```bash
     pip install python-json-logger boto3
     ```
  2. Create `/opt/miguel/backend/app/core/logging_config.py`:
     ```python
     # Log to stdout (JSON format)
     # Periodically upload to S3
     ```
  3. Setup CloudWatch or S3:
     ```python
     # Store logs in S3: s3://miguel-logs/2026-02-24/app.log
     ```
  4. Create log query interface (optional)
- **Effort**: 12 hours
- **Impact**: MEDIUM (ops)
- **Files to Create/Modify**:
  - `/opt/miguel/backend/app/core/logging_config.py` (new)
  - `/opt/miguel/backend/app/main.py` (integrate logging)

#### 8. **Implement Deployment Automation (CI/CD)**
- **Current State**: Manual deployment (docker-compose restart)
- **What to Do**:
  1. Create `.github/workflows/deploy.yml`:
     ```yaml
     on:
       push:
         branches: [main]
     
     jobs:
       test:
         runs-on: ubuntu-latest
         steps:
           - uses: actions/checkout@v3
           - name: Run tests
             run: pytest -v
       deploy:
         needs: test
         runs-on: ubuntu-latest
         steps:
           - name: SSH to Linode and restart
             run: |
               ssh root@172.232.118.208 'cd /opt/miguel && git pull && docker-compose restart'
     ```
  2. Setup SSH keys in GitHub secrets
  3. Configure auto-deployment on main branch push
- **Effort**: 8 hours
- **Impact**: HIGH (deployment safety)
- **Files to Create**:
  - `/.github/workflows/deploy.yml` (GitHub Actions)
  - `/.github/workflows/tests.yml` (test CI)

#### 9. **Performance Testing & Benchmarking**
- **Current State**: No performance baseline
- **What to Do**:
  1. Create load test script using `locust`:
     ```bash
     pip install locust
     ```
  2. Create `/opt/miguel/tests/load_test.py`:
     ```python
     from locust import HttpUser, task
     class CRMUser(HttpUser):
         @task
         def get_leads(self):
             self.client.get("/api/leads/")
     ```
  3. Run load test:
     ```bash
     locust -f tests/load_test.py --headless -u 100 -r 10 -t 5m
     ```
  4. Document results:
     - Requests/sec: X
     - Response time (p99): X ms
     - Error rate: X%
  5. Establish baselines for monitoring
- **Effort**: 15 hours
- **Impact**: MEDIUM (optimization)
- **Files to Create**:
  - `/opt/miguel/tests/load_test.py` (load test)
  - `/opt/miguel/PERFORMANCE_BASELINE.md` (results)

#### 10. **Mobile Responsiveness Audit**
- **Current State**: Desktop-focused, may not work on mobile
- **What to Do**:
  1. Test on iPhone 12 (Chrome DevTools)
  2. Check each page:
     - leads.html
     - orders.html
     - customers.html
     - gst.html
  3. Add mobile-specific CSS:
     ```css
     @media (max-width: 768px) {
       .sidebar { display: none; }
       .main { width: 100%; }
     }
     ```
  4. Test touch interactions:
     - Drawer/modal closing
     - Form inputs
     - Button clicks
  5. Document known issues
- **Effort**: 10 hours
- **Impact**: MEDIUM (UX)
- **Files to Modify**:
  - `/opt/miguel/frontend/ds.css` (add media queries)
  - `/opt/miguel/frontend/*.html` (adjust layouts)

---

### Priority 3: NICE-TO-HAVE (Q2 2026) 🎯

#### 11. **Phase 13: SaaS Billing Layer**
- **Scope**: Subscription management, invoices, payment processing
- **Features**:
  - Pricing plans (free, starter, pro, enterprise)
  - Usage tracking (API calls, contacts, storage)
  - Invoice generation
  - Payment processor (Razorpay/Stripe)
  - Upgrade/downgrade flows
  - Dunning (failed payment recovery)
- **Effort**: 80-120 hours
- **Impact**: CRITICAL (revenue generation)
- **Files to Create**:
  - `/opt/miguel/backend/app/modules/billing/` (6+ files)
  - `/opt/miguel/frontend/billing.html` (billing dashboard)
  - `/opt/miguel/backend/alembic/versions/` (billing schema)

#### 12. **Advanced Analytics Dashboard**
- **Features**:
  - Cohort analysis (customer groups by acquisition date)
  - Funnel visualization (leads → customers)
  - Time-series graphs (revenue trend)
  - Custom reports
  - Export to PDF/Excel
- **Effort**: 40 hours
- **Impact**: MEDIUM (insights)
- **Frontend**: Chart library (Chart.js or Plotly)

#### 13. **Third-Party Integrations**
- **Shopify Sync**: Sync products, orders, customers
- **WooCommerce Sync**: Sync e-commerce data
- **Google Sheets**: Export/import customers and orders
- **Zapier**: Webhook integration for external triggers
- **Effort**: 30-50 hours each
- **Impact**: MEDIUM (ecosystem)

#### 14. **Mobile App (iOS/Android)**
- **Framework**: React Native
- **Features**: Leads, customers, orders, reporting
- **Effort**: 120+ hours
- **Impact**: MEDIUM (mobile-first users)

---

## 🎬 QUICK START: WHAT TO DO TODAY

### For the Next 7 Days (Before Friday):
1. **Install pytest** and run one test
2. **Setup 2FA** (at least basic TOTP)
3. **Add rate limiting** (5 min, 3 requests per endpoint)
4. **Document current architecture** (if not done)

### Estimated Time: 40 hours (1 developer, 1 week)

**Command Checklist**:
```bash
# 1. Install testing
pip install pytest pytest-asyncio httpx

# 2. Create test file
touch /opt/miguel/backend/tests/test_leads.py

# 3. Install 2FA library
pip install pyotp qrcode

# 4. Install rate limiting
pip install slowapi

# 5. Test endpoints still work
curl http://localhost:8000/api/orders/ -H "Authorization: Bearer test"
```

---

## 📊 COMPLETION MATRIX

| Task | Status | Effort | Impact | Owner |
|------|--------|--------|--------|-------|
| Automated testing | 🔴 PENDING | 20h | HIGH | — |
| 2FA authentication | 🔴 PENDING | 15h | HIGH | — |
| Rate limiting | 🔴 PENDING | 8h | HIGH | — |
| Email verification | 🔴 PENDING | 12h | MEDIUM | — |
| Redis caching | 🔴 PENDING | 25h | HIGH | — |
| Database backups | 🔴 PENDING | 10h | CRITICAL | — |
| Log archival (S3) | 🔴 PENDING | 12h | MEDIUM | — |
| CI/CD deployment | 🔴 PENDING | 8h | HIGH | — |
| Performance testing | 🔴 PENDING | 15h | MEDIUM | — |
| Mobile audit | 🔴 PENDING | 10h | MEDIUM | — |
| **Phase 13: Billing** | 🔵 NOT STARTED | 100h | CRITICAL | — |
| **Advanced Analytics** | 🔵 NOT STARTED | 40h | MEDIUM | — |

**Total Pending Work**: ~240+ hours (≈ 6 weeks at 40h/week)

---

## ✅ WHAT'S ALREADY DONE

### ✅ Complete (Phase 1-12)
- [x] Infrastructure (Docker, PostgreSQL)
- [x] Authentication (JWT, multi-tenant)
- [x] CRM Core (leads, customers, orders, products)
- [x] WhatsApp Integration (WABIS + Meta)
- [x] Marketing Module (campaigns, audience)
- [x] GST & Accounting (GSTR-1, HSN, exports)
- [x] Label & PDF generation
- [x] M3 Design System
- [x] Database migrations (17 total)

### ⚠️ Partially Complete
- [x] Documentation (95% complete)
- [x] Error handling (good, some improvements needed)
- [x] Performance (good for current load)

### 🔴 Not Done
- [ ] Automated testing
- [ ] 2FA
- [ ] Rate limiting
- [ ] Caching
- [ ] Backups (automated)
- [ ] CI/CD
- [ ] Monitoring

---

## 🎯 RECOMMENDED NEXT STEPS

### Week 1 (Feb 25 - Mar 3)
```
Monday:   Install pytest, write 5 basic tests
Tuesday:  Setup 2FA (TOTP + QR code)
Wednesday: Add rate limiting (5 endpoints)
Thursday:  Email verification flow
Friday:    Testing & documentation
```

### Week 2 (Mar 4 - 10)
```
Monday:   Redis setup & caching
Tuesday:  Database backup automation
Wednesday: Log archival to S3
Thursday:  CI/CD pipeline setup
Friday:    Performance testing & benchmarks
```

### Week 3 (Mar 11 - 17)
```
Full week: Mobile responsiveness audit + fixes
```

### Week 4+ (Mar 18+)
```
Start Phase 13 (SaaS Billing Layer)
```

---

## 📞 QUESTIONS TO ANSWER

Before starting next phase:
1. **Billing Model**: Freemium, subscription, or usage-based?
2. **Scalability**: How many tenants/users expected in 1 year?
3. **Integrations**: Which third-party systems matter most?
4. **Mobile**: iOS only, Android only, or both?
5. **Support**: In-app chat, email, or phone support?

---

## 🏁 FINAL CHECKLIST

- [x] All core features implemented
- [x] Database schema designed & applied
- [x] Frontend pages created
- [x] API endpoints working
- [x] Documentation written
- [ ] Automated tests created
- [ ] Security hardened (2FA, rate limiting)
- [ ] Performance optimized (caching)
- [ ] Backups automated
- [ ] Monitoring setup
- [ ] Mobile responsive
- [ ] Production deployment ready

**Current Readiness**: 60% (core features only)  
**Full Production Readiness**: 85% (after Priority 1 + 2)  
**Ready for Scale**: 95% (after Phase 13)

---

*Last Updated: February 24, 2026*  
*Next Review: March 3, 2026 (after Priority 1 tasks)*  
*Prepared by: Copilot (Code Review Agent)*
