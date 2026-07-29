# 🎯 Quick Start — UAT & Production Deployment

## **Your Current Setup**

```
LOCAL DEVELOPMENT
    │
    ├─→ git push origin dev
    │
    ▼
┌──────────────────────────────────┐
│  GitHub Repository (3 branches)  │
│  ├─ dev   (features)             │
│  ├─ uat   (staging)              │
│  └─ main  (production)           │
└──────────────────────────────────┘
    │              │              │
    │              │              │
    ▼              ▼              ▼
  LOCAL      UAT Server      PROD Server
  (DEV)      (Linode)        (Linode)
            crm-uat-*       crm-prod-*
            crm_uat DB      crm_prod DB
```

---

## **The Workflow (5 Easy Steps)**

### **1️⃣ Develop**
```bash
git checkout dev
# Make changes
git add .
git commit -m "Your message"
git push origin dev
```

### **2️⃣ Test in UAT**
```bash
git checkout uat
git merge dev
git push origin uat
# ✨ GitHub Actions automatically deploys!
```

### **3️⃣ Verify in UAT**
- Visit your UAT server
- Test all features
- Check database: `docker exec -it crm-uat-db psql ...`

### **4️⃣ Deploy to Production**
```bash
git checkout main
git merge uat
git push origin main
# ✨ GitHub Actions automatically deploys!
```

### **5️⃣ Monitor Production**
```bash
# Via SSH on Production server
docker logs crm-prod-backend
docker ps
```

---

## **One-Click Commands**

### **Create Migration**
```bash
docker exec -it crm-uat-backend alembic revision --autogenerate -m "Description"
git add .
git push origin dev
```

### **Backup Database**
```bash
docker exec -it crm-uat-db pg_dump -U miguel_user miguel_db > backup.sql
```

### **View Logs**
```bash
docker logs crm-uat-backend
docker logs crm-uat-db
```

### **Restart Services**
```bash
docker compose restart crm-uat-backend
docker compose restart crm-uat-db
```

---

## **Secrets Management**

### **❌ DON'T DO THIS:**
```bash
# Don't commit .env
git add .env  # ✗ Wrong!

# Don't expose API keys
SHOPIFY_KEY = "shpss_abc123..."  # ✗ Wrong!
```

### **✅ DO THIS:**
```bash
# Use .env.example as template
cp .env.example .env
nano .env  # Fill in your actual values

# Git ignores .env automatically (in .gitignore)
git add .
git commit -m "..."  # .env is NOT included
```

---

## **GitHub Actions Status**

Visit: https://github.com/purelevenexim-ai/crm/actions

You'll see deployments like:
- ✅ Deploy to UAT — Triggered by push to `uat`
- ✅ Deploy to Production — Triggered by push to `main`

---

## **Emergency Procedures**

### **Rollback Production**
```bash
# SSH into Production server
git revert <commit-hash>
git push origin main

# GitHub Actions automatically redeploys the reverted version
```

### **Restore from Backup**
```bash
# SSH into Production server
docker exec -i crm-prod-db psql -U miguel_user miguel_db < backup_prod_*.sql

# Restart backend
docker compose restart crm-prod-backend
```

---

## **Checklist Before Production**

- [ ] Tested thoroughly in UAT
- [ ] Database migrations run successfully
- [ ] All API keys are in `.env` (not hardcoded)
- [ ] No `[REDACTED]` placeholders left in real values
- [ ] Backup created before pushing to main
- [ ] GitHub Actions workflow completed successfully

---

## **File Locations**

| What | Where |
|------|-------|
| Environment template | `.env.example` |
| Secrets (NEVER commit) | `.env` |
| Deployment automation | `.github/workflows/deploy-*.yml` |
| Full guide | `DEPLOYMENT_GUIDE.md` |
| Setup summary | `SETUP_COMPLETE.md` |

---

## **Getting Help**

### **If deployment fails:**
1. Check GitHub Actions logs: https://github.com/purelevenexim-ai/crm/actions
2. SSH into server and check: `docker logs crm-uat-backend`
3. Verify `.env` file has all required variables

### **If database migration fails:**
1. View error: `docker logs crm-uat-backend`
2. Restore backup: `docker exec -i crm-uat-db psql < backup.sql`
3. Downgrade migration: `docker exec -it crm-uat-backend alembic downgrade -1`

---

## **Key Environment Variables (in `.env`)**

```
# Database
DATABASE_URL=postgresql://user:password@db:5432/database_name

# Delhivery API
DELHIVERY_API_KEY=your_key
DELHIVERY_API_TOKEN=your_token
DELHIVERY_ACCOUNT_ID=your_id

# Shopify
SHOPIFY_API_KEY=your_key
SHOPIFY_API_SECRET=your_secret

# WhatsApp
WHATSAPP_ACCESS_TOKEN=your_token
WHATSAPP_PHONE_NUMBER_ID=your_id

# Encryption
ENCRYPTION_KEY=your_key
JWT_SECRET_KEY=your_key
```

---

## **💡 Tips**

1. **Always test in UAT first** before pushing to main
2. **Use `.env.example`** as reference for required variables
3. **Keep backups** — they're created automatically
4. **Check logs** — they tell you what went wrong
5. **Never hardcode secrets** — always use environment variables

---

## **🎉 You're All Set!**

Your CRM deployment system is:
- ✅ Secure (no exposed secrets)
- ✅ Automated (GitHub Actions)
- ✅ Reliable (database backups)
- ✅ Scalable (easy to add more servers)

**Ready to deploy with confidence!** 🚀
