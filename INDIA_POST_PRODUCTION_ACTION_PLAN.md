# Production Action Plan — India Post API 502/503 Resolution

**Issue:** After IP whitelisting (152.58.200.96, 172.105.48.142), the India Post APIs are returning:
- **502 Bad Gateway** - Pincode endpoint unreachable
- **503 Service Unavailable** - Tariff endpoints unreachable

**Root Cause:** Production API URLs are not configured correctly in the backend environment.

---

## 🎯 IMMEDIATE ACTION REQUIRED

### Step 1: Get Your Production API URLs from India Post

**Login to:** https://indiapostcustomer.com

**Navigate to:**
- Account Dashboard → API Management (or "My APIs" / "Subscribed APIs")
- Look for your **Bulk Customer API** subscription
- Find the section that shows `{base_path}` or API Gateway URL

**You will see something like:**
```
Bulk Customer API:
  Environment: Production
  Base Path: https://your-prod-api.indiapost.gov.in:8080/beextcustomer
  OR
  Base Path: https://prod-api-gw.indiapost.gov.in/beextcustomer
```

**Copy these values:**
- [ ] Production Bulk Customer API URL (for tariff, tracking, booking)
- [ ] Production Masterdata API URL (for pincode lookup)

**⚠️ If you don't see this section:**
- Contact your India Post account manager
- Reference: "Bulk Customer Portal API Subscription Details"
- Mention: Production IPs 152.58.200.96 and 172.105.48.142 are now whitelisted

---

### Step 2: Update Production Environment

Once you have the URLs, SSH into the production server:

```bash
ssh root@172.105.48.142
cd /opt/pureleven
nano .env
```

**Add/update these lines:**
```bash
# India Post Production API URLs (from your India Post portal)
INDIA_POST_PROD_URL="https://your-prod-api.indiapost.gov.in:8080/beextcustomer"
INDIA_POST_PROD_MASTERDATA_URL="https://your-prod-api.indiapost.gov.in:8080/bemasterdata"
```

**Save (Ctrl+O, Enter, Ctrl+X)**

---

### Step 3: Restart Backend Service

```bash
cd /opt/pureleven

# Restart backend container
docker-compose -f config/docker-compose.prod.yml restart backend

# Wait for it to be healthy (30-45 seconds)
sleep 45

# Check logs for any errors
docker-compose -f config/docker-compose.prod.yml logs backend | tail -50
```

**Expected in logs:**
```
backend   | INFO:     Application startup complete
```

**NOT expected (if you see these, configuration still wrong):**
```
ConnectTimeout
ConnectError
Name or service not known
```

---

### Step 4: Verify Connection

**Test 1: Test Connection Endpoint**

From your browser or terminal:
```bash
curl -X POST "https://prod.pureleven.com/api/india-post/test-connection" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Expected Response:**
```json
{
  "success": true,
  "message": "India Post API connected successfully",
  "environment": "production"
}
```

**Test 2: Pincode Lookup**
```bash
curl "https://prod.pureleven.com/api/india-post/pincode?pincode=685561" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Expected:** 
```json
{
  "success": true,
  "data": [
    {
      "pincode": "685561",
      "office_name": "Adimali",
      "state": "Kerala",
      ...
    }
  ]
}
```

**Test 3: Tariff Calculation**
```bash
curl "https://prod.pureleven.com/api/india-post/tariff?service=speed_post&weight=50&source_pincode=685561&destination_pincode=400001&cod_amount=160" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Expected:**
```json
{
  "success": true,
  "tariff": 145.00,
  "base_charge": 120.00,
  "tax": 25.00
}
```

---

## 🔍 If Tests Still Fail

### Diagnostic Check 1: Verify Backend Can Reach the URL

```bash
# SSH into production server
ssh root@172.105.48.142

# From backend container
docker exec pureleven_backend bash -c \
  "curl -I https://YOUR_PROD_URL/v1/speed-post/tariffs?weight=50"
```

**Possible outcomes:**

| Response | Meaning | Next Step |
|----------|---------|-----------|
| `HTTP/2 200` or `HTTP/2 400` | ✅ Connected | Configuration correct, test with credentials |
| `Connection timed out` | ❌ Network unreachable | Verify IP whitelisting with India Post |
| `Name or service not known` | ❌ DNS resolution failed | Check URL spelling (often includes port like `:8080`) |
| `Connection refused` | ❌ Service not running | Contact India Post support |

### Diagnostic Check 2: Verify Backend Outbound IP

```bash
docker exec pureleven_backend bash -c "curl -s https://ifconfig.me"
```

**Must return one of:**
- `172.105.48.142` (production IP)
- `152.58.200.96` (alternate whitelisted IP)

**If returns private IP (e.g., 10.x.x.x):**
- Backend can't reach external APIs
- Verify Docker networking and gateway configuration
- Check NAT/routing on production server

### Diagnostic Check 3: Test from Production Server Directly

```bash
ssh root@172.105.48.142

# Try to reach India Post API directly
curl -I https://YOUR_PROD_URL/v1/speed-post/tariffs
```

**If this works but backend fails:**
- Docker networking issue
- Check: `docker network ls` and `docker network inspect pureleven_pureleven_network`

---

## 📋 Information to Have Ready

When contacting India Post support if needed:

```
Ticket Title: Production API URLs for Bulk Customer Integration

Details:
- Organization: [Your Company Name]
- Customer Portal Account: [Your Portal Email]
- Contract ID (Parcel): [From portal or invoice]
- Contract ID (Speed Post): [From portal or invoice]
- Whitelisted Production IPs: 152.58.200.96, 172.105.48.142
- Request: Production API Gateway URLs for:
  * Bulk Customer API (tariff, tracking, booking)
  * Masterdata API (pincode lookup)
- Current error: 502/503 when calling APIs with default URL
- Reference: "Subscribed APIs" section of portal shows {base_path}
```

---

## ✅ Success Criteria

Once fixed, you should be able to:

1. ✅ Add India Post as shipping partner in Tenant Admin
2. ✅ Enter credentials and pass credential test
3. ✅ On an order: Select India Post delivery partner
4. ✅ Enter weight/dimensions and pincode
5. ✅ Click "Calculate" → **Tariff appears automatically** (no 502/503)
6. ✅ Pincode auto-fills city/state from lookup
7. ✅ Frontend shows shipping cost in order total

---

## 🚀 Timeline

- **Immediate (now):** Collect production URLs from India Post portal
- **5 minutes:** Update .env and restart backend
- **2 minutes:** Run tests from the steps above
- **Total time to fix:** ~10-15 minutes once you have the URLs

---

**Last Updated:** May 22, 2026  
**Status:** 🔴 Awaiting India Post Production URL Configuration  
**Contact:** India Post Bulk Customer Support
