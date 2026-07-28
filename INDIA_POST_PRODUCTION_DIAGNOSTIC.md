# India Post Production Issues — Diagnostic Report

**Date:** May 22, 2026  
**Status:** ⚠️ Critical Issues Identified After IP Whitelisting

---

## 📊 Current Production Errors

### API Response Codes

| Endpoint | Error | Issue |
|----------|-------|-------|
| `/api/india-post/pincode?pincode=685561` | **502 Bad Gateway** | Backend cannot reach pincode API |
| `/api/india-post/tariff?...speed_post...` | **503 Service Unavailable** | Tariff service unreachable (multiple attempts) |

### Root Cause Analysis

The errors indicate **networking issues** between the backend and India Post APIs despite IP whitelisting:

1. ✅ IPs whitelisted: `152.58.200.96`, `172.105.48.142`
2. ❌ Backend URLs still failing: `https://apigw.indiapost.gov.in`
3. ⚠️ **Code Comment Warning:** `"The previous default https://apigw.indiapost.gov.in does not resolve in public DNS"`

---

## 🔍 Problem Identification

### Issue #1: Incorrect/Incomplete Production URLs

**Location:** [backend/app/core/shipping/india_post_client.py](backend/app/core/shipping/india_post_client.py#L49-L53)

```python
# Current defaults (DON'T WORK):
PROD_URL            = os.getenv("INDIA_POST_PROD_URL", "https://apigw.indiapost.gov.in")
PROD_MASTERDATA_URL = os.getenv("INDIA_POST_PROD_MASTERDATA_URL", "https://apigw.indiapost.gov.in")
```

**Problem:**
- Default URL `https://apigw.indiapost.gov.in` doesn't resolve in public DNS
- Environment variables not set in production `.env` file
- Backend trying to reach unreachable hostname

### Issue #2: Missing Production API Configuration

**Current Production Status:**
- Production `.env` file exists but **doesn't contain**:
  - `INDIA_POST_PROD_URL`
  - `INDIA_POST_PROD_MASTERDATA_URL`

**Why This Matters:**
- When the default URL fails, the backend falls back to sandbox (which also won't connect with production IPs)
- No explicit error message about what URL is being used

---

## 🛠️ Solution Steps

### Step 1: Obtain Correct Production URLs from India Post

**Action Required:** Contact your India Post account manager / developer portal

**Information Needed:**
- [ ] **Production API Gateway Base URL** for:
  - Tariff calculation endpoints (speed_post, parcel, etc.)
  - Pincode/masterdata endpoints
  
- [ ] **Masterdata API Base URL** for:
  - Office lookup (`/v1/offices/limited-details`)
  - Pincode validation

**Example Response Format:**
```
Production URLs (from India Post):
- Bulk Customer API: https://prod-api.indiapost.gov.in:8080/beextcustomer
- Masterdata API: https://prod-api.indiapost.gov.in:8080/bemasterdata
```

### Step 2: Update Production Environment

Once you have the correct URLs, update the production `.env` file:

```bash
# Add to /opt/pureleven/.env
INDIA_POST_PROD_URL="https://prod-api.indiapost.gov.in:8080/beextcustomer"
INDIA_POST_PROD_MASTERDATA_URL="https://prod-api.indiapost.gov.in:8080/bemasterdata"
```

### Step 3: Restart Backend Container

```bash
cd /opt/pureleven
docker-compose -f config/docker-compose.prod.yml restart backend

# Verify logs:
docker-compose -f config/docker-compose.prod.yml logs -f backend | grep "India Post"
```

### Step 4: Test Connection

Use the built-in test endpoint:

```bash
curl -X POST "https://prod.pureleven.com/api/india-post/test-connection" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "username": "YOUR_INDIA_POST_USERNAME",
    "password": "YOUR_INDIA_POST_PASSWORD",
    "customer_id": "YOUR_CONTRACT_ID"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "message": "India Post production API connection successful",
  "api_version": "v1",
  "endpoints": ["tariff", "pincode", "tracking"]
}
```

---

## 🔧 Fallback Troubleshooting

### If URLs Still Don't Work

**Check 1: Verify IP Whitelisting**
```bash
# From backend container:
docker exec pureleven_backend bash -c "curl -I https://ACTUAL_PROD_URL"

# This will show if:
- DNS resolves (name resolution)
- IP is reachable (connection timeout)
- Firewall blocks port (connection refused)
```

**Check 2: Check Backend Container's Outbound IP**
```bash
docker exec pureleven_backend bash -c "curl https://ifconfig.me"

# Should return: 172.105.48.142 (or 152.58.200.96)
# If returns private IP: routing/NAT issue
```

**Check 3: Test from Host Machine**
```bash
# Verify India Post actually receives connections from your IPs
curl -I https://ACTUAL_PROD_URL/v1/tariff

# If times out: whitelisting may be incomplete
# If 403/401: whitelisting works but auth missing
```

---

## 📋 Checklist for Production Fix

- [ ] Obtain correct production API URLs from India Post
- [ ] Update `INDIA_POST_PROD_URL` environment variable
- [ ] Update `INDIA_POST_PROD_MASTERDATA_URL` environment variable
- [ ] Restart backend container
- [ ] Run test-connection endpoint
- [ ] Test pincode lookup: `GET /api/india-post/pincode?pincode=685561`
- [ ] Test tariff calculation: `GET /api/india-post/tariff?service=speed_post&weight=50&source_pincode=685561&destination_pincode=685561&cod_amount=160`
- [ ] Verify frontend tariff auto-calculation works

---

## 📞 Next Action

**Contact India Post support with:**
- Production server IP: `172.105.48.142` (now whitelisted ✅)
- Alternate IP: `152.58.200.96`
- Request: Production API Gateway URLs for their Bulk Customer API
- Reference: Bulk Customer Portal → "Subscribed APIs" section should show {base_path}

---

**Last Updated:** May 22, 2026  
**Issue Status:** Waiting for India Post URL configuration
