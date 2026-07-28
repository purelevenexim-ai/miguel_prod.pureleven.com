# 🔴 CRITICAL FIX: India Post 502/503 Errors — Quick Summary

## The Problem (in 1 sentence)
The backend is trying to reach India Post APIs using a broken default URL instead of your actual production API gateway URL.

---

## What's Happening

```
Your frontend → prod.pureleven.com → backend container
                                        ↓
                          Tries: https://apigw.indiapost.gov.in
                          Result: ❌ DNS doesn't resolve (never worked)
                                  ❌ 502 Bad Gateway (pincode)
                                  ❌ 503 Service Unavailable (tariff)
```

**Why now?** IP whitelisting worked ✅, but backend still using broken default URL ❌

---

## The Fix (3 Steps)

### Step 1: Get Real URL from India Post Portal
- Login: https://indiapostcustomer.com
- Find: "Subscribed APIs" → "Bulk Customer API"
- Copy: The production base URL (looks like `https://prod-api.indiapost.gov.in:8080/beextcustomer`)

### Step 2: Add to Production .env
```bash
# SSH to production
ssh root@172.105.48.142

# Edit .env
nano /opt/pureleven/.env

# Add these lines (with YOUR actual URL):
INDIA_POST_PROD_URL="https://YOUR-ACTUAL-URL-HERE/beextcustomer"
INDIA_POST_PROD_MASTERDATA_URL="https://YOUR-ACTUAL-URL-HERE/bemasterdata"
```

### Step 3: Restart Backend
```bash
cd /opt/pureleven
docker-compose -f config/docker-compose.prod.yml restart backend
sleep 30
```

**That's it.** Tariff & pincode should work immediately after.

---

## How to Verify It's Fixed

**Test 1 (in browser):**
```
Click on an order → Select "India Post" delivery partner
→ Fill weight/pincode → Click "Calculate"
→ Should show tariff (NOT 502 or 503)
```

**Test 2 (from terminal):**
```bash
# Replace TOKEN with your JWT
curl "https://prod.pureleven.com/api/india-post/pincode?pincode=685561" \
  -H "Authorization: Bearer TOKEN"

# Should return pincode details, NOT error
```

---

## What Was Wrong

**File:** `/opt/pureleven/backend/app/core/shipping/india_post_client.py` (Line 52-53)

```python
# These use broken defaults:
PROD_URL = os.getenv("INDIA_POST_PROD_URL", "https://apigw.indiapost.gov.in")
PROD_MASTERDATA_URL = os.getenv("INDIA_POST_PROD_MASTERDATA_URL", "https://apigw.indiapost.gov.in")

# Code tries to use them but DNS fails:
# → 502 Bad Gateway (pincode)
# → 503 Service Unavailable (tariff)
```

**The code is correct.** It's just waiting for you to configure the actual URLs via environment variables.

---

## Where to Get Help

If you can't find the URL in India Post portal:

**Contact India Post Support with:**
```
"Can you provide the production API gateway URL for our 
Bulk Customer API subscription? 
Reference: Subscribed APIs section should show {base_path}.
Organization: [Your Company]
Whitelisted IPs: 152.58.200.96, 172.105.48.142"
```

---

## Files Created for Reference

1. **INDIA_POST_PRODUCTION_DIAGNOSTIC.md** — Full technical analysis
2. **INDIA_POST_PRODUCTION_ACTION_PLAN.md** — Detailed step-by-step with tests

---

**Time to fix:** ~10 minutes once you have the URL  
**Priority:** 🔴 CRITICAL (blocks all India Post shipping orders)  
**Status:** ⏳ Waiting for production URL configuration
