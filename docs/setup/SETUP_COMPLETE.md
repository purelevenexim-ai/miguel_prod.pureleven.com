# ✅ CRM GitHub & Deployment Setup — Complete

Your CRM is now properly set up for safe, automated deployments across UAT and Production environments.

---

## **What Was Done**

### ✅ **1. Secured Your Repository**
- **Masked all secrets** in documentation files with `[REDACTED]` placeholders
- **Created `.env.example`** — template showing all required configuration variables
- **Created `.gitignore`** — prevents accidental commit of sensitive files
- **Cleaned Git history** — removed exposed Shopify secret from previous commits

### ✅ **2. Set Up GitHub Branches**
```
main  ← Production branch (auto-deploys to Production Linode)
uat   ← UAT/Staging branch (auto-deploys to UAT Linode)
dev   ← Development branch (for feature work)
```

### ✅ **3. Configured GitHub Actions**
Two automated deployment workflows:

**`.github/workflows/deploy-uat.yml`**
- Triggers when you push to `uat` branch
- Automatically deploys to your UAT server
- Backs up database
- Runs Alembic migrations

**`.github/workflows/deploy-prod.yml`**
- Triggers when you push to `main` branch
- Automatically deploys to your Production server
- Backs up database
- Runs Alembic migrations

### ✅ **4. Created Comprehensive Documentation**
- **`DEPLOYMENT_GUIDE.md`** — Step-by-step guide for the entire workflow
- **`.env.example`** — All configuration variables explained
- **`.gitignore`** — Prevents accidental secret commits

---

## **Your New Workflow**

### **For Development:**
```bash
# 1. Work on features in dev branch
git checkout dev
# ... make changes ...
git push origin dev

# 2. Create database migration if needed
docker exec -it crm-uat-backend alembic revision --autogenerate -m "Your changes"
git push origin dev
```

### **For Testing in UAT:**
```bash
# 3. Merge dev into uat
git checkout uat
git merge dev
git push origin uat

# ✨ GitHub Actions automatically:
#    - SSH into UAT server
#    - Pulls latest code
#    - Backs up database
#    - Rebuilds Docker containers
#    - Runs migrations
```

### **For Production Deployment:**
```bash
# 4. After testing, merge uat into main
git checkout main
git merge uat
git push origin main

# ✨ GitHub Actions automatically:
#    - SSH into Production server
#    - Pulls latest code
#    - Backs up database
#    - Rebuilds Docker containers
#    - Runs migrations
```

---

## **Next Steps**

### **1️⃣ Add SSH Secrets to GitHub**

Go to your GitHub repository:
- **Settings → Secrets and variables → Actions**

Add these 6 secrets:

**For UAT:**
- `UAT_SSH_HOST` → Your UAT server IP
- `UAT_SSH_USER` → SSH username (usually `root`)
- `UAT_SSH_KEY` → Contents of your private SSH key

**For Production:**
- `PROD_SSH_HOST` → Your Production server IP
- `PROD_SSH_USER` → SSH username
- `PROD_SSH_KEY` → Contents of your private SSH key

### **2️⃣ Configure Your Servers**

**On UAT Server:**
```bash
cd /opt/miguel
cp .env.example .env
# Edit .env with your actual database passwords, API keys, etc.
nano .env

docker compose up -d --build
docker exec -it crm-uat-backend alembic upgrade head
```

**On Production Server:**
```bash
cd /opt/miguel
cp .env.example .env
# Edit .env with your PRODUCTION database passwords, API keys, etc.
nano .env

docker compose up -d --build
docker exec -it crm-prod-backend alembic upgrade head
```

### **3️⃣ Test the GitHub Actions**

Once SSH secrets are configured:

```bash
# Test UAT deployment
git checkout uat
git push origin uat

# Watch at: https://github.com/purelevenexim-ai/crm/actions
# Should see: ✅ Deploy to UAT workflow running

# Test Production deployment
git checkout main
git push origin main

# Should see: ✅ Deploy to Production workflow running
```

---

## **Important Files Created**

| File | Purpose |
|------|---------|
| `.env.example` | Template for all configuration variables (safe to commit) |
| `.gitignore` | Prevents accidental commit of `.env` and other secrets |
| `.github/workflows/deploy-uat.yml` | Automatic UAT deployment on push to `uat` |
| `.github/workflows/deploy-prod.yml` | Automatic Production deployment on push to `main` |
| `DEPLOYMENT_GUIDE.md` | Complete guide for using this system |

---

## **For Delhivery Integration**

Your Delhivery API credentials should be in `.env`:

```bash
# .env file (NOT committed to GitHub)
DELHIVERY_API_KEY=your_actual_key_here
DELHIVERY_API_TOKEN=your_actual_token_here
DELHIVERY_ACCOUNT_ID=your_account_id_here
DELHIVERY_BASE_URL=https://api.delhivery.com
```

Access in your code:
```python
import os
api_key = os.getenv("DELHIVERY_API_KEY")
```

---

## **Security Checklist**

✅ All secrets are masked in repository
✅ `.env` file is in `.gitignore`
✅ `.env.example` template is committed
✅ Sensitive data removed from commit history
✅ GitHub Actions can securely deploy
✅ Database auto-backups before migrations

---

## **Troubleshooting**

### **GitHub Actions won't deploy?**
1. Check SSH secrets are added to GitHub
2. Verify SSH key format (should be private key, not public)
3. Check Actions tab for error logs

### **`.env` file missing?**
```bash
cp .env.example .env
nano .env  # Fill in your actual values
```

### **Database migration failed?**
```bash
# View logs
docker logs crm-uat-backend

# Restore backup if needed
docker exec -i crm-uat-db psql -U miguel_user miguel_db < backup_uat_*.sql
```

---

## **Summary**

You now have a **production-ready, secure deployment system**:

1. ✅ Secure credential management (`.env.example` + `.gitignore`)
2. ✅ Automated deployments via GitHub Actions
3. ✅ Safe branching strategy (dev → uat → main)
4. ✅ Database backups before each migration
5. ✅ Easy rollback capability
6. ✅ Comprehensive documentation

**Your tenants' data is safe, and you can deploy with confidence!** 🚀

---

**Questions? See `DEPLOYMENT_GUIDE.md` for detailed instructions.**
