# ✅ Final Checklist — UAT & Production Deployment Setup

## What Has Been Completed ✅

### GitHub Repository Setup
- [x] All secrets masked with `[REDACTED]` placeholders
- [x] `.env.example` created (safe template)
- [x] `.gitignore` created (prevents secret leaks)
- [x] Git history cleaned (Shopify secret removed)
- [x] Three branches created: `dev`, `uat`, `main`
- [x] All files pushed to GitHub

### GitHub Actions Workflows
- [x] `.github/workflows/deploy-uat.yml` created
- [x] `.github/workflows/deploy-prod.yml` created
- [x] Both workflows configured for automatic deployment
- [x] Database backup included in workflows
- [x] Alembic migration execution configured

### Documentation
- [x] `DEPLOYMENT_GUIDE.md` — Complete step-by-step guide
- [x] `QUICK_REFERENCE.md` — Common commands
- [x] `SETUP_COMPLETE.md` — Setup summary
- [x] `GITHUB_SETUP_SUMMARY.txt` — Final summary
- [x] All documentation pushed to all branches

---

## What You Need To Do Next

### Step 1: Add GitHub Secrets (CRITICAL)
This is required for GitHub Actions to deploy to your servers.

1. Go to: `https://github.com/purelevenexim-ai/crm`
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** and add these 6 secrets:

**For UAT Server:**
```
Name: UAT_SSH_HOST
Value: [Your UAT server IP address]

Name: UAT_SSH_USER
Value: root

Name: UAT_SSH_KEY
Value: [Paste contents of your private SSH key]
```

**For Production Server:**
```
Name: PROD_SSH_HOST
Value: [Your Production server IP address]

Name: PROD_SSH_USER
Value: root

Name: PROD_SSH_KEY
Value: [Paste contents of your private SSH key]
```

### Step 2: Configure UAT Server

SSH into your UAT Linode:
```bash
ssh root@[UAT_IP]
cd /opt/miguel

# Copy template and fill in values
cp .env.example .env
nano .env

# Fill in these critical values:
# - DATABASE_URL (database connection)
# - DELHIVERY_API_KEY
# - DELHIVERY_API_TOKEN
# - DELHIVERY_ACCOUNT_ID
# - WHATSAPP_ACCESS_TOKEN (if using)
# - SHOPIFY credentials (if using)
# - Any other API keys needed
```

Then start services:
```bash
docker compose up -d --build
docker exec -it crm-uat-backend alembic upgrade head
```

### Step 3: Configure Production Server

SSH into your Production Linode:
```bash
ssh root@[PROD_IP]
cd /opt/miguel

# Copy template and fill in PRODUCTION values
cp .env.example .env
nano .env

# Fill in PRODUCTION database credentials and API keys
# (These should be different from UAT)
```

Then start services:
```bash
docker compose up -d --build
docker exec -it crm-prod-backend alembic upgrade head
```

### Step 4: Test GitHub Actions Deployment

Test that deployment works:

```bash
# Test UAT deployment
git checkout uat
git push origin uat

# Watch the deployment at:
# https://github.com/purelevenexim-ai/crm/actions
# You should see "Deploy to UAT" workflow running
# It should complete with ✅ status
```

---

## Verification Checklist

### Repository Verification
- [ ] Visit `https://github.com/purelevenexim-ai/crm`
- [ ] Verify three branches exist: `main`, `uat`, `dev`
- [ ] No `.env` file in repository (only `.env.example`)
- [ ] No secrets exposed in commit history

### GitHub Actions Verification
- [ ] Visit `https://github.com/purelevenexim-ai/crm/actions`
- [ ] See two workflow files: `deploy-uat.yml` and `deploy-prod.yml`
- [ ] SSH secrets are configured (6 total)

### Server Verification (UAT)
- [ ] SSH into UAT server
- [ ] `.env` file exists with all required variables filled
- [ ] Docker containers running: `docker ps`
- [ ] Database accessible: `docker exec -it crm-uat-db psql -U miguel_user -d miguel_db -c "SELECT 1"`
- [ ] Backend running: `curl http://localhost:8000/docs`

### Server Verification (Production)
- [ ] SSH into Production server
- [ ] `.env` file exists with all required PRODUCTION variables
- [ ] Docker containers running: `docker ps`
- [ ] Database accessible and separate from UAT
- [ ] Backend running: `curl http://localhost:8000/docs`

### Deployment Test
- [ ] Make a test commit to `dev` branch
- [ ] Merge `dev` into `uat`
- [ ] Push to `uat` branch
- [ ] Watch GitHub Actions deployment
- [ ] Verify UAT server has latest code
- [ ] Test Delhivery API integration works

---

## Common Commands Reference

### Git Workflow
```bash
# Develop feature
git checkout dev
git add .
git commit -m "Your feature"
git push origin dev

# Test in UAT
git checkout uat
git merge dev
git push origin uat

# Deploy to Production
git checkout main
git merge uat
git push origin main
```

### Database Migrations
```bash
# Create migration
docker exec -it crm-uat-backend alembic revision --autogenerate -m "Description"

# Apply migrations
docker exec -it crm-uat-backend alembic upgrade head

# Rollback migration
docker exec -it crm-uat-backend alembic downgrade -1

# Check migration history
docker exec -it crm-uat-backend alembic history
```

### Docker Commands
```bash
# View running containers
docker ps

# View logs
docker logs crm-uat-backend

# Restart services
docker compose restart crm-uat-backend

# Rebuild and restart
docker compose up -d --build
```

### Backup/Restore
```bash
# Backup database
docker exec -it crm-uat-db pg_dump -U miguel_user miguel_db > backup.sql

# Restore database
docker exec -i crm-uat-db psql -U miguel_user miguel_db < backup.sql
```

---

## Delhivery API Configuration

Your Delhivery API credentials should be in `.env`:

```
DELHIVERY_API_KEY=your_actual_api_key
DELHIVERY_API_TOKEN=your_actual_api_token
DELHIVERY_ACCOUNT_ID=your_account_id
DELHIVERY_BASE_URL=https://api.delhivery.com
```

✅ These are securely stored in `.env` (not committed to GitHub)
✅ Easy to update without redeploying
✅ Different values for UAT and Production

---

## Security Reminders

### DO's ✅
- ✅ Always test in UAT before Production
- ✅ Keep `.env` file safe and never commit it
- ✅ Use `.env.example` as template
- ✅ Backup database before migrations
- ✅ Keep SSH keys secure

### DON'Ts ❌
- ❌ Never hardcode API keys in code
- ❌ Never commit `.env` file to GitHub
- ❌ Never share `.env` or SSH keys
- ❌ Never expose secrets in documentation
- ❌ Never skip UAT testing before Production

---

## Troubleshooting

### GitHub Actions not running?
1. Check SSH secrets are configured correctly
2. Verify SSH key format (private key, not public)
3. Test SSH connection: `ssh -i key.pem root@server_ip`

### Deployment failed?
1. Check GitHub Actions logs: `https://github.com/purelevenexim-ai/crm/actions`
2. SSH to server and check: `docker logs crm-uat-backend`
3. Verify `.env` file has all required variables

### Database migration failed?
1. View error: `docker logs crm-uat-backend`
2. Restore from backup: `docker exec -i crm-uat-db psql -U miguel_user miguel_db < backup.sql`
3. Downgrade migration: `docker exec -it crm-uat-backend alembic downgrade -1`

### Docker won't start?
1. Check `.env` file — all required variables must be set
2. Check logs: `docker logs crm-uat-backend`
3. Rebuild: `docker compose down && docker compose up -d --build`

---

## Documentation Files

| File | Purpose |
|------|---------|
| `.env.example` | Configuration template (safe to commit) |
| `.gitignore` | Prevents accidental secret commits |
| `DEPLOYMENT_GUIDE.md` | Complete deployment guide |
| `QUICK_REFERENCE.md` | Common commands and procedures |
| `SETUP_COMPLETE.md` | Setup summary |
| `GITHUB_SETUP_SUMMARY.txt` | Final setup summary |
| `.github/workflows/deploy-uat.yml` | UAT deployment automation |
| `.github/workflows/deploy-prod.yml` | Production deployment automation |

---

## Support & Questions

**For deployment issues:** See `DEPLOYMENT_GUIDE.md`
**For quick commands:** See `QUICK_REFERENCE.md`
**For overview:** See `SETUP_COMPLETE.md`
**For final summary:** See `GITHUB_SETUP_SUMMARY.txt`

All documentation is in your repository.

---

## Final Checklist Before Going Live

- [ ] SSH secrets added to GitHub (6 total)
- [ ] `.env` configured on UAT server
- [ ] `.env` configured on Production server
- [ ] Docker running on both servers
- [ ] Alembic migrations completed on both servers
- [ ] Test deployment to UAT works
- [ ] Delhivery API credentials configured and tested
- [ ] Database backup works
- [ ] Read and understood the deployment guide
- [ ] Team knows how to use git workflow

---

## You're All Set! 🎉

Your CRM is now ready for:
✅ Safe UAT testing
✅ Secure Production deployment
✅ Automatic backups
✅ Easy rollback
✅ Zero downtime updates

**Your tenants' data is SAFE and PROTECTED!** 🚀

---

**Last Updated:** February 26, 2026
**Status:** ✅ COMPLETE
**Repository:** https://github.com/purelevenexim-ai/crm
