# 🚀 Production Deployment - Complete Reference

**Status:** ✅ **READY TO DEPLOY**  
**Date:** February 27, 2026  
**Last Commit:** e92b314

---

## Your UAT → Git → Production Workflow

```
┌─────────────────┐     ┌──────────────┐     ┌──────────────────┐
│  UAT (Local)    │────▶│   Git Main   │────▶│  Production      │
│  /opt/miguel    │     │  origin/main │     │  /opt/pureleven  │
│ Test Changes    │     │  Push Code   │     │ Pull & Deploy    │
└─────────────────┘     └──────────────┘     └──────────────────┘
  1. Develop           2. Commit & Push      3. SSH, Pull, Deploy
  2. Test              3. Verify Push        4. Run Migrations
  3. Commit                                  5. Verify Health
```

---

## Quick Reference

### Production Server Details
| Item | Value |
|------|-------|
| **IP Address** | 172.105.48.142 |
| **SSH User** | root |
| **Repo Path** | /opt/pureleven |
| **Git Branch** | main |
| **Database** | PostgreSQL (pureleven_db) |

### Key Credentials
- DB User: `pureleven_user`
- Docker Compose: `config/docker-compose.prod.yml`
- Backend Port: 8000
- Frontend Ports: 80, 443

---

## Step 1: On Local Machine (UAT)

### Commit & Push to Git
```bash
cd /opt/miguel

# Check status
git status

# Stage changes (if any)
git add -A

# Commit
git commit -m "Your feature/fix description"

# Push to Git
git push origin main

# Verify
git log --oneline -1
```

✅ **Current Status:** All commits already pushed to origin/main

---

## Step 2: On Production Server

### Connect via SSH
```bash
ssh root@172.105.48.142
cd /opt/pureleven
```

### Deploy (Complete One-Line Script)

**Copy and paste this entire block:**

```bash
#!/bin/bash
set -e
cd /opt/pureleven

# 🔒 Create backup
echo "🔒 Backing up database..."
BACKUP="/tmp/prod_backup_$(date +%F_%H%M%S).dump"
docker-compose -f config/docker-compose.prod.yml exec -T db pg_dump -U pureleven_user pureleven_db -Fc > $BACKUP
echo "✅ Backup created: $BACKUP"

# 📥 Pull latest code
echo ""
echo "📥 Pulling latest code from Git..."
git fetch origin
git pull origin main
echo "✅ Code pulled"
git log --oneline -1

# 🐳 Update containers
echo ""
echo "🐳 Updating Docker containers..."
docker-compose -f config/docker-compose.prod.yml pull
docker-compose -f config/docker-compose.prod.yml up -d --remove-orphans
echo "⏳ Waiting for services to start..."
sleep 8

# 🔄 Run migrations
echo ""
echo "🔄 Running database migrations..."
docker-compose -f config/docker-compose.prod.yml exec -T backend bash -c "cd /app && alembic upgrade head"
echo "✅ Migrations complete"

# ✅ Verify health
echo ""
echo "✅ Checking service health..."
docker-compose -f config/docker-compose.prod.yml ps
echo ""
echo "Latest logs:"
docker-compose -f config/docker-compose.prod.yml logs --tail=20 backend

echo ""
echo "═════════════════════════════════════════════════════════"
echo "✅ DEPLOYMENT COMPLETE!"
echo "═════════════════════════════════════════════════════════"
echo ""
echo "Verify production:"
echo "  curl -I http://172.105.48.142:8000/docs"
echo "  http://prod.pureleven.com"
echo ""
```

---

## Step 3: Verify Deployment

### Check Services
```bash
docker-compose -f config/docker-compose.prod.yml ps
# Should show: backend (Up), db (Up), frontend (Up)
```

### Test API
```bash
curl -I http://172.105.48.142:8000/docs
# Should return: HTTP/1.1 200 OK
```

### Test Login
```bash
curl -X POST http://172.105.48.142:8000/tenant/login \
  -H 'Content-Type: application/json' \
  -d '{
    "slug": "purelevenexim",
    "email": "admin@purelevenexim.com",
    "password": "Admin@123"
  }'
# Should return: access_token, token_type: bearer
```

### Check Logs
```bash
docker-compose -f config/docker-compose.prod.yml logs --tail=100 backend
# Look for: "Application startup complete" and no ERROR messages
```

---

## Emergency Rollback

If deployment fails:

```bash
# On production server
cd /opt/pureleven

# Stop services
docker-compose -f config/docker-compose.prod.yml down

# Restore database
# List available backups
ls -lh /tmp/prod_backup_*.dump

# Restore from backup
pg_restore -U pureleven_user -d pureleven_db /tmp/prod_backup_YYYY-MM-DD_HHMMSS.dump

# Restart
docker-compose -f config/docker-compose.prod.yml up -d

# Verify
docker-compose -f config/docker-compose.prod.yml ps
```

---

## Common Issues & Fixes

### Backend Won't Start
```bash
# Check logs for errors
docker-compose -f config/docker-compose.prod.yml logs backend

# Common cause: Model import error or migration failure
# Solution: Check Git logs and restore from backup if needed
```

### Database Connection Error
```bash
# Wait longer (DB may still be initializing)
sleep 30
docker-compose -f config/docker-compose.prod.yml exec -T db pg_isready
```

### Port 8000 Already in Use
```bash
# Kill existing container
docker-compose -f config/docker-compose.prod.yml down
docker-compose -f config/docker-compose.prod.yml up -d
```

### Nginx 404 on Frontend
```bash
# Verify frontend volume is mounted
docker-compose -f config/docker-compose.prod.yml exec frontend ls -la /usr/share/nginx/html
```

---

## Files You Need to Know

| File | Purpose | Location |
|------|---------|----------|
| `docker-compose.prod.yml` | Production services | `/opt/pureleven/config/` |
| `.env` | Production secrets | `/opt/pureleven/` |
| `alembic.ini` | DB migration config | `/opt/pureleven/backend/` |
| `app/main.py` | FastAPI entry point | `/opt/pureleven/backend/app/` |

---

## Deployment Checklist

Before pushing to production:

- [ ] All tests pass locally (UAT)
- [ ] Code committed and pushed to origin/main
- [ ] Reviewed changes: `git diff origin/main`
- [ ] Database backup created on production
- [ ] No uncommitted changes: `git status`
- [ ] Production `.env` file has correct secrets

After deploying:

- [ ] Services running: `docker-compose ps`
- [ ] API responding: `curl /docs` returns 200
- [ ] Database migrations successful: check logs
- [ ] Can login: test with credentials
- [ ] No errors in logs: `docker-compose logs backend`
- [ ] Frontend accessible: visit domain in browser

---

## Support & Documentation

- **Main Deployment Guide:** `/opt/miguel/PRODUCTION_DEPLOYMENT_MANUAL.md`
- **Deploy Script:** `/opt/miguel/scripts/deploy_to_prod.sh`
- **Production Setup:** `/opt/miguel/docs/setup/PRODUCTION_SETUP_INDEX.md`
- **Session Summary:** `/opt/miguel/SESSION_COMPLETION_SUMMARY.md`

---

## Quick Commands Reference

```bash
# On production server

# View all services
docker-compose -f config/docker-compose.prod.yml ps

# View logs (live)
docker-compose -f config/docker-compose.prod.yml logs -f backend

# Restart services
docker-compose -f config/docker-compose.prod.yml restart

# Stop services
docker-compose -f config/docker-compose.prod.yml down

# Execute command in container
docker-compose -f config/docker-compose.prod.yml exec backend bash

# View database
docker-compose -f config/docker-compose.prod.yml exec db psql -U pureleven_user -d pureleven_db

# Check disk space
df -h

# Check Docker status
docker ps
docker images
```

---

## Last Deployment Info

**Commit:** e92b314  
**Message:** docs: add production deployment manual with UAT → Git → Prod workflow  
**Date:** February 27, 2026  
**Status:** ✅ Ready to deploy

```bash
# Last deployed version
cd /opt/pureleven && git log --oneline -1
```

---

**Remember:** Always backup before deploying! ✅

Questions? Check logs: `docker-compose -f config/docker-compose.prod.yml logs backend`
