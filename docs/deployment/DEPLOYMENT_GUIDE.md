# 🚀 CRM — UAT & Production Deployment Guide

This guide explains how to set up and manage your CRM across **UAT** and **Production** environments using GitHub Actions.

---

## **Architecture Overview**

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Repository                         │
│  ┌──────────┬──────────┬──────────┐                         │
│  │   dev    │   uat    │   main   │                         │
│  └────┬─────┴────┬─────┴────┬─────┘                         │
│       │          │          │                                │
└───────┼──────────┼──────────┼────────────────────────────────┘
        │          │          │
        ▼          ▼          ▼
    (DEV)    (UAT Server)  (PROD Server)
   Linode      Linode         Linode
   
🎯 Workflow:
  dev → uat → main (automatic deployment via GitHub Actions)
```

---

## **Step 1: Configure GitHub Secrets**

Before deploying, you need to add SSH credentials to GitHub so it can automatically deploy to your servers.

### **For UAT Server:**
1. Go to your GitHub repository
2. Click **Settings → Secrets and variables → Actions**
3. Add these secrets:
   - `UAT_SSH_HOST` → Your UAT server IP (e.g., `192.168.1.100`)
   - `UAT_SSH_USER` → SSH username (e.g., `root`)
   - `UAT_SSH_KEY` → Your private SSH key (paste the contents of your `id_rsa` file)

### **For Production Server:**
1. Add these secrets:
   - `PROD_SSH_HOST` → Your Production server IP
   - `PROD_SSH_USER` → SSH username
   - `PROD_SSH_KEY` → Your private SSH key

---

## **Step 2: Set Up UAT Server**

### **On your UAT Linode:**

```bash
# Clone the repository
git clone https://github.com/purelevenexim-ai/crm.git
cd crm
git checkout uat

# Create .env file with your credentials
cp .env.example .env
# Edit .env with your actual values (database passwords, API keys, etc.)
nano .env

# Start Docker containers
docker compose up -d --build

# Run database migrations
docker exec -it crm-uat-backend alembic upgrade head

# Verify everything is running
docker ps
```

---

## **Step 3: Set Up Production Server**

### **On your Production Linode:**

```bash
# Clone the repository
git clone https://github.com/purelevenexim-ai/crm.git
cd crm
git checkout main

# Create .env file with your credentials
cp .env.example .env
# Edit .env with your actual PRODUCTION values
nano .env

# Start Docker containers
docker compose up -d --build

# Run database migrations
docker exec -it crm-prod-backend alembic upgrade head

# Verify everything is running
docker ps
```

---

## **Step 4: Development Workflow**

### **1️⃣ Develop Features**
Work on your UAT + DEV Linode:

```bash
# Switch to dev branch
git checkout dev

# Make your changes
# ... edit files ...

# Create a database migration (if needed)
docker exec -it crm-uat-backend alembic revision --autogenerate -m "Add new feature"

# Commit your changes
git add .
git commit -m "Add new feature"
git push origin dev
```

### **2️⃣ Test in UAT**
Merge dev into uat:

```bash
# On your local or UAT server
git checkout uat
git merge dev
git push origin uat

# GitHub Actions automatically deploys to UAT server!
# ✅ The GitHub Actions workflow:
#    - SSH into your UAT server
#    - Pulls the latest uat branch
#    - Rebuilds Docker containers
#    - Runs database migrations
#    - Restarts the backend
```

Test your changes in the UAT environment:
- Visit your UAT server's IP/domain
- Test all features thoroughly
- Verify database migrations work correctly

### **3️⃣ Deploy to Production**
When you're confident everything works:

```bash
# Merge uat into main
git checkout main
git merge uat
git push origin main

# GitHub Actions automatically deploys to Production! 🎉
# ✅ The workflow:
#    - SSH into your Production server
#    - Pulls the latest main branch
#    - Backs up the database
#    - Rebuilds Docker containers
#    - Runs database migrations
#    - Restarts the backend
```

---

## **Step 5: Managing Secrets & Credentials**

### **⚠️ Important Rules:**

1. **Never commit secrets to GitHub**
   - All sensitive data goes in `.env` file
   - `.env` is in `.gitignore` — never committed

2. **Use `.env.example` for templates**
   - Shows the structure of required variables
   - Safe to commit to GitHub
   - Copy it to `.env` and fill in actual values

3. **Supported secret types:**
   - Database credentials
   - API keys (Shopify, Delhivery, WABIS, etc.)
   - JWT secrets
   - Encryption keys
   - SMTP passwords

4. **Accessing secrets in your code:**
   ```python
   import os
   
   # In your FastAPI app
   DELHIVERY_API_KEY = os.getenv("DELHIVERY_API_KEY")
   SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY")
   ```

---

## **Step 6: Database Migrations**

### **Creating a New Migration:**

```bash
# On UAT server
docker exec -it crm-uat-backend alembic revision --autogenerate -m "Description of changes"

# This creates a new file in backend/alembic/versions/
# Example: uat_changes_add_new_field.py
```

### **Applying Migrations:**

```bash
# Manually on UAT
docker exec -it crm-uat-backend alembic upgrade head

# Automatically on Production (via GitHub Actions)
# When you push to main, GitHub Actions runs:
# docker exec -it crm-prod-backend alembic upgrade head
```

### **Backing Up Before Migrations:**

The GitHub Actions automatically backs up your database before running migrations:

```bash
docker exec -it crm-prod-db pg_dump -U miguel_user miguel_db > backup_prod_20260226_120000.sql
```

You can restore from backup if needed:

```bash
# Restore from backup
docker exec -i crm-prod-db psql -U miguel_user miguel_db < backup_prod_20260226_120000.sql
```

---

## **Step 7: Monitoring & Debugging**

### **Check if containers are running:**

```bash
docker ps
```

### **View logs:**

```bash
# Backend logs
docker logs crm-uat-backend

# Database logs
docker logs crm-uat-db

# Frontend logs
docker logs miguel_frontend
```

### **Check database:**

```bash
# Connect to database
docker exec -it crm-uat-db psql -U miguel_user -d miguel_db

# View tables
\dt

# View specific table
SELECT * FROM customers LIMIT 5;
```

---

## **Step 8: Rollback (If Something Goes Wrong)**

### **Option 1: Restore from database backup**

```bash
# On Production server
docker exec -i crm-prod-db psql -U miguel_user miguel_db < backup_prod_20260226_120000.sql

# Restart backend
docker compose restart crm-prod-backend
```

### **Option 2: Rollback Git commit**

```bash
# On Production server
git revert <commit-hash>
git push origin main

# GitHub Actions automatically deploys the reverted version
```

### **Option 3: Downgrade database**

```bash
# If a migration causes issues
docker exec -it crm-prod-backend alembic downgrade -1

# This runs the downgrade() function in your migration file
```

---

## **Step 9: Delhivery API Integration**

Your Delhivery API credentials should be stored in `.env`:

```bash
# In .env file
DELHIVERY_API_KEY=your_delhivery_api_key
DELHIVERY_API_TOKEN=your_delhivery_api_token
DELHIVERY_ACCOUNT_ID=your_delhivery_account_id
DELHIVERY_BASE_URL=https://api.delhivery.com
```

Access in your code:

```python
import os

DELHIVERY_API_KEY = os.getenv("DELHIVERY_API_KEY")
DELHIVERY_API_TOKEN = os.getenv("DELHIVERY_API_TOKEN")
DELHIVERY_BASE_URL = os.getenv("DELHIVERY_BASE_URL", "https://api.delhivery.com")
```

---

## **Quick Reference**

| Action | Command |
|--------|---------|
| **Pull latest code (UAT)** | `git pull origin uat` |
| **Pull latest code (Prod)** | `git pull origin main` |
| **View running containers** | `docker ps` |
| **Rebuild containers** | `docker compose up -d --build` |
| **Run migrations** | `docker exec -it crm-uat-backend alembic upgrade head` |
| **View logs** | `docker logs crm-uat-backend` |
| **Create migration** | `docker exec -it crm-uat-backend alembic revision --autogenerate -m "msg"` |
| **Backup database** | `docker exec -it crm-uat-db pg_dump -U miguel_user miguel_db > backup.sql` |
| **Restore database** | `docker exec -i crm-uat-db psql -U miguel_user miguel_db < backup.sql` |

---

## **Troubleshooting**

### **GitHub Actions not deploying?**
- Check that SSH secrets are correctly configured
- Verify that your server's SSH key is added to GitHub
- Check the Actions tab to see deployment logs

### **Database migration failed?**
- Check logs: `docker logs crm-uat-backend`
- Restore from backup: `docker exec -i crm-uat-db psql -U miguel_user miguel_db < backup.sql`
- Run downgrade: `docker exec -it crm-uat-backend alembic downgrade -1`

### **Containers not starting?**
- Check `.env` file — all required variables must be set
- Check logs: `docker logs crm-uat-backend`
- Rebuild: `docker compose down && docker compose up -d --build`

### **Secret is exposed in GitHub?**
- GitHub will block the push automatically
- Remove the secret from the file
- Commit and push the fix
- GitHub's secret scanning will automatically approve the push

---

## **Final Notes**

✅ **Never commit `.env` to GitHub** — it contains sensitive credentials

✅ **Always test in UAT first** — before deploying to Production

✅ **Keep backups** — GitHub Actions automatically backs up before migrations

✅ **Use `.env.example`** — as a template for required variables

✅ **Monitor logs** — check deployment logs if something goes wrong

---

**For questions or issues, check the troubleshooting section or review GitHub Actions logs.**

Good luck with your deployment! 🚀
