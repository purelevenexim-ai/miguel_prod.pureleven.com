# 🎯 REMAINING TASKS — Complete Action Plan

## Status: GitHub & Automation Setup ✅ COMPLETE
## Status: Server Configuration ⏳ IN PROGRESS

---

## **WHAT'S LEFT TO DO**

### **Phase 1: GitHub Secrets Configuration** (5-10 minutes)
**Status:** ⏳ NOT STARTED

You need to add SSH credentials to GitHub so it can automatically deploy to your servers.

**Tasks:**
- [ ] Get your private SSH key
- [ ] Add 6 GitHub Secrets
- [ ] Verify secrets are saved

**Instructions:**

1. **Get Your Private SSH Key**
   ```bash
   # On your UAT server, display your private SSH key
   cat ~/.ssh/id_rsa
   ```
   Copy the entire output (including `-----BEGIN RSA PRIVATE KEY-----` and `-----END RSA PRIVATE KEY-----`)

2. **Add GitHub Secrets**
   - Go to: `https://github.com/purelevenexim-ai/crm`
   - Click: **Settings → Secrets and variables → Actions**
   - Click: **New repository secret**
   - Add these 6 secrets one by one:

   **UAT Secrets:**
   ```
   Name: UAT_SSH_HOST
   Value: [Your UAT Linode IP address]
   ```

   ```
   Name: UAT_SSH_USER
   Value: root
   ```

   ```
   Name: UAT_SSH_KEY
   Value: [Paste the entire contents of ~/.ssh/id_rsa]
   ```

   **Production Secrets:**
   ```
   Name: PROD_SSH_HOST
   Value: [Your Production Linode IP address]
   ```

   ```
   Name: PROD_SSH_USER
   Value: root
   ```

   ```
   Name: PROD_SSH_KEY
   Value: [Paste the entire contents of your Production server's ~/.ssh/id_rsa]
   ```

3. **Verify Secrets**
   - Go to GitHub repo → Settings → Secrets and variables → Actions
   - You should see all 6 secrets listed
   - Click each one to verify it's saved (you can't see the value, but it should say "Updated X seconds ago")

---

### **Phase 2: Configure UAT Server** (10-15 minutes)
**Status:** ⏳ NOT STARTED

**Tasks:**
- [ ] SSH into UAT server
- [ ] Create `.env` file from template
- [ ] Fill in all required values
- [ ] Start Docker containers
- [ ] Run database migrations
- [ ] Verify everything is working

**Step-by-Step Instructions:**

```bash
# 1. SSH into UAT server
ssh root@[Your_UAT_Server_IP]

# 2. Navigate to project
cd /opt/miguel

# 3. Create .env from template
cp .env.example .env

# 4. Edit the .env file
nano .env
```

**Fill in these values in .env:**

```env
# Database
DATABASE_URL=postgresql://crm_uat_user:YOUR_DB_PASSWORD@db:5432/crm_uat
POSTGRES_PASSWORD=YOUR_DB_PASSWORD

# WhatsApp (if using)
WHATSAPP_PHONE_NUMBER_ID=your_phone_id
WHATSAPP_ACCESS_TOKEN=your_token
WHATSAPP_API_VERSION=v19.0

# Webhook Verification
META_WEBHOOK_VERIFY_TOKEN=your_verify_token

# Encryption
ENCRYPTION_KEY=your_encryption_key

# Delhivery API (YOUR MOST IMPORTANT ONE)
DELHIVERY_API_KEY=your_api_key
DELHIVERY_API_TOKEN=your_api_token
DELHIVERY_ACCOUNT_ID=your_account_id
DELHIVERY_BASE_URL=https://api.delhivery.com

# Shopify (if using)
SHOPIFY_STORE_NAME=your_store_name
SHOPIFY_API_KEY=your_key
SHOPIFY_API_SECRET=your_secret

# JWT
JWT_SECRET_KEY=your_jwt_secret
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Environment
ENV=uat
LOG_LEVEL=INFO
```

**After editing .env (press Ctrl+X, then Y, then Enter):**

```bash
# 5. Start Docker containers
docker compose up -d --build

# 6. Wait for containers to start (30-60 seconds)
sleep 30

# 7. Run database migrations
docker exec -it crm-uat-backend alembic upgrade head

# 8. Verify containers are running
docker ps

# 9. Verify backend is responding
curl http://localhost:8000/docs
```

**Expected output for step 9:**
```
<!DOCTYPE html>
...
<title>FastAPI</title>
...
```

---

### **Phase 3: Configure Production Server** (10-15 minutes)
**Status:** ⏳ NOT STARTED

**Same steps as Phase 2, but on your Production server:**

```bash
# 1. SSH into Production server
ssh root@[Your_PROD_Server_IP]

# 2. Navigate to project
cd /opt/miguel

# 3. Create .env from template
cp .env.example .env

# 4. Edit the .env file (PRODUCTION VALUES ONLY!)
nano .env
```

**Fill in PRODUCTION values** (different from UAT):

```env
DATABASE_URL=postgresql://crm_prod_user:PROD_DB_PASSWORD@db:5432/crm_prod
POSTGRES_PASSWORD=PROD_DB_PASSWORD
DELHIVERY_API_KEY=prod_api_key  # Use PRODUCTION Delhivery credentials
DELHIVERY_API_TOKEN=prod_api_token
DELHIVERY_ACCOUNT_ID=prod_account_id
ENV=prod
# ... rest of configuration with PRODUCTION values
```

**Then:**

```bash
# 5. Start Docker containers
docker compose up -d --build

# 6. Wait for containers to start
sleep 30

# 7. Run database migrations
docker exec -it crm-prod-backend alembic upgrade head

# 8. Verify
docker ps
curl http://localhost:8000/docs
```

---

### **Phase 4: Test GitHub Actions Deployment** (5 minutes)
**Status:** ⏳ NOT STARTED

Once you've completed Phases 1-3, test that automatic deployment works:

```bash
# 1. Make a test commit
cd /opt/miguel
git checkout uat
echo "# Test deployment $(date)" >> TEST_DEPLOYMENT.md
git add TEST_DEPLOYMENT.md
git commit -m "Test GitHub Actions deployment"
git push origin uat
```

**Then:**

```
2. Watch GitHub Actions:
   Go to: https://github.com/purelevenexim-ai/crm/actions
   You should see "Deploy to UAT" workflow running
   Wait for it to complete (should show ✅)

3. Verify UAT server has the new file:
   ssh root@[UAT_IP]
   cd /opt/miguel
   cat TEST_DEPLOYMENT.md
   # Should show your commit message
```

---

### **Phase 5: Test Delhivery API Integration** (10-15 minutes)
**Status:** ⏳ NOT STARTED

Verify that Delhivery API is working correctly:

```bash
# SSH into UAT server
ssh root@[UAT_IP]
cd /opt/miguel

# Test Delhivery connectivity
python3 << 'EOF'
import os
import requests

api_key = os.getenv("DELHIVERY_API_KEY")
api_token = os.getenv("DELHIVERY_API_TOKEN")
base_url = os.getenv("DELHIVERY_BASE_URL", "https://api.delhivery.com")

print(f"API Key: {api_key[:10]}..." if api_key else "❌ API Key not set")
print(f"API Token: {api_token[:10]}..." if api_token else "❌ API Token not set")
print(f"Base URL: {base_url}")

# Try a simple API call
try:
    response = requests.get(
        f"{base_url}/api/cust/me/",
        headers={"Authorization": f"Token {api_token}"}
    )
    print(f"✅ Delhivery API Response: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"❌ Error: {e}")
EOF
```

---

## **QUICK CHECKLIST**

Print this out and check off as you complete:

### GitHub Setup
- [ ] GitHub Secrets added (6 total)
- [ ] All secrets verified in GitHub

### UAT Server
- [ ] `.env` file created and filled
- [ ] Docker containers started
- [ ] Database migrations completed
- [ ] `curl http://localhost:8000/docs` works
- [ ] Delhivery API responds

### Production Server
- [ ] `.env` file created with PROD values
- [ ] Docker containers started
- [ ] Database migrations completed
- [ ] `curl http://localhost:8000/docs` works
- [ ] Separate database from UAT verified

### Automation Testing
- [ ] Test commit pushed to `uat` branch
- [ ] GitHub Actions "Deploy to UAT" completed ✅
- [ ] New file visible on UAT server
- [ ] Production secrets configured correctly

### Final Verification
- [ ] Can deploy to UAT with: `git push origin uat`
- [ ] Can deploy to Production with: `git push origin main`
- [ ] Database backups working
- [ ] Alembic migrations run automatically

---

## **COMMANDS REFERENCE**

### SSH Into Servers
```bash
ssh root@[UAT_IP]      # UAT
ssh root@[PROD_IP]     # Production
```

### View Docker Status
```bash
docker ps                        # Running containers
docker logs crm-uat-backend      # Backend logs
docker logs crm-uat-db           # Database logs
```

### View .env File (to verify it's set)
```bash
cat /opt/miguel/.env
# Should show all your configuration
```

### Check Database Connection
```bash
docker exec -it crm-uat-db psql -U crm_uat_user -d crm_uat -c "SELECT 1;"
# Should return: 1
```

### View Migration Status
```bash
docker exec -it crm-uat-backend alembic current
# Should show latest migration ID
```

### Restart Services
```bash
docker compose restart crm-uat-backend
docker compose restart crm-uat-db
```

### View Real-time Logs
```bash
docker logs -f crm-uat-backend  # Follow backend logs
docker logs -f crm-uat-db       # Follow database logs
```

---

## **TROUBLESHOOTING**

### ".env file not found"
```bash
cp .env.example .env
# Then fill in values with: nano .env
```

### "Docker containers won't start"
```bash
# Check logs
docker logs crm-uat-backend

# Common issues:
# 1. .env file missing → cp .env.example .env
# 2. Database password wrong → check .env DATABASE_URL
# 3. Port already in use → docker ps to see conflicts
```

### "Alembic migration failed"
```bash
# View error
docker logs crm-uat-backend

# Check current migration state
docker exec -it crm-uat-backend alembic current

# If stuck, downgrade one version
docker exec -it crm-uat-backend alembic downgrade -1
```

### "GitHub Actions won't deploy"
```bash
# Check that all 6 secrets are added:
# https://github.com/purelevenexim-ai/crm/settings/secrets/actions

# Verify SSH key format:
head -1 ~/.ssh/id_rsa
# Should show: -----BEGIN RSA PRIVATE KEY-----

# Not: -----BEGIN PUBLIC KEY-----
```

### "Can't connect to Delhivery API"
```bash
# Verify credentials in .env
grep DELHIVERY /opt/miguel/.env

# Test API manually
curl -H "Authorization: Token YOUR_API_TOKEN" \
  https://api.delhivery.com/api/cust/me/
```

---

## **DOCUMENTATION AVAILABLE**

In your GitHub repository, you have:

- **FINAL_CHECKLIST.md** — Complete pre-flight checklist
- **DEPLOYMENT_GUIDE.md** — Full deployment guide
- **QUICK_REFERENCE.md** — Common commands
- **SETUP_COMPLETE.md** — What was set up
- **GITHUB_SETUP_SUMMARY.txt** — Executive summary

---

## **NEXT IMMEDIATE ACTIONS**

**Right Now:**
1. Get your private SSH key: `cat ~/.ssh/id_rsa`
2. Add 6 GitHub Secrets (5 minutes)

**Within 30 minutes:**
3. Configure UAT server `.env`
4. Configure Production server `.env`
5. Start Docker on both servers

**Within 1 hour:**
6. Run Alembic migrations
7. Test deployment
8. Verify Delhivery API

---

## **YOU'RE ALMOST THERE!**

Everything is set up and ready. Now it's just:
- ✅ Adding credentials (GitHub secrets)
- ✅ Configuring servers (fill in .env)
- ✅ Starting services (docker compose up)
- ✅ Testing deployment (git push)

**Once done, you'll have:**
- Fully automated deployments
- Secure credential management
- Production-ready CRM
- Zero downtime updates

Let me know when you're ready to start! 🚀
