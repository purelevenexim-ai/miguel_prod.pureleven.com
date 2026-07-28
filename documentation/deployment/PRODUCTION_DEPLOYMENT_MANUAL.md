# Production Deployment Guide
## UAT → Git → Production Workflow

**Date:** February 27, 2026  
**Production Server:** 172.105.48.142  
**Repo Path:** /opt/pureleven  
**Branch:** main

---

## Quick Summary

Your workflow:
1. **UAT (Local)** → Test changes
2. **Git** → Push to origin/main
3. **Production** → Pull from git and deploy

---

## Step-by-Step Commands

### On your local machine (UAT):

```bash
# 1. Make sure all code is committed
cd /opt/miguel
git status
git add .
git commit -m "Your commit message"

# 2. Push to Git
git push origin main

# Verify push succeeded
git log --oneline -1
```

### On Production Server (SSH in):

```bash
# 1. Connect to production
ssh root@172.105.48.142
cd /opt/pureleven

# 2. Create backup FIRST (critical!)
BACKUP="/tmp/prod_backup_$(date +%F_%H%M%S).dump"
docker-compose -f config/docker-compose.prod.yml exec -T db pg_dump -U pureleven_user pureleven_db -Fc > $BACKUP
echo "✅ Backup: $BACKUP"

# 3. Pull latest code from Git
git fetch origin
git checkout main
git pull origin main
echo "✅ Code pulled"

# 4. Update Docker containers
docker-compose -f config/docker-compose.prod.yml pull
docker-compose -f config/docker-compose.prod.yml up -d --remove-orphans
echo "✅ Containers updated"

# 5. Wait for backend to start
sleep 5

# 6. Run database migrations
docker-compose -f config/docker-compose.prod.yml exec -T backend bash -c "cd /app && alembic upgrade head"
echo "✅ Migrations complete"

# 7. Check service status
docker-compose -f config/docker-compose.prod.yml ps

# 8. View recent logs
docker-compose -f config/docker-compose.prod.yml logs --tail=50 backend
```

---

## Full Deployment in One Block (Copy & Paste)

Run this entire block on the production server:

```bash
#!/bin/bash
set -e
cd /opt/pureleven

# Backup
echo "🔒 Creating backup..."
BACKUP="/tmp/prod_backup_$(date +%F_%H%M%S).dump"
docker-compose -f config/docker-compose.prod.yml exec -T db pg_dump -U pureleven_user pureleven_db -Fc > $BACKUP
echo "✅ Backup: $BACKUP"

# Pull code
echo "📥 Pulling from Git..."
git fetch origin
git checkout main
git pull origin main

# Update containers
echo "🐳 Updating containers..."
docker-compose -f config/docker-compose.prod.yml pull
docker-compose -f config/docker-compose.prod.yml up -d --remove-orphans
sleep 5

# Migrate DB
echo "🔄 Running migrations..."
docker-compose -f config/docker-compose.prod.yml exec -T backend bash -c "cd /app && alembic upgrade head"

# Verify
echo "✅ Checking services..."
docker-compose -f config/docker-compose.prod.yml ps

echo ""
echo "═════════════════════════════════════════════"
echo "✅ DEPLOYMENT COMPLETE"
echo "═════════════════════════════════════════════"
```

---

## Verify Deployment

After running the commands above:

```bash
# Check services are running
docker-compose -f config/docker-compose.prod.yml ps

# Check API is responding
curl -I http://172.105.48.142:8000/docs

# Check recent logs for errors
docker-compose -f config/docker-compose.prod.yml logs --tail=100 backend

# Test API login
curl -X POST http://172.105.48.142:8000/tenant/login \
  -H 'Content-Type: application/json' \
  -d '{"slug":"purelevenexim","email":"admin@purelevenexim.com","password":"Admin@123"}'
```

Expected: You should see HTTP 200 and a JWT token.

---

## Rollback (If Something Goes Wrong)

```bash
# On production server
cd /opt/pureleven

# Stop containers
docker-compose -f config/docker-compose.prod.yml down

# Restore database from backup
pg_restore -U pureleven_user -d pureleven_db /tmp/prod_backup_YYYY-MM-DD_HHMMSS.dump

# Restart services
docker-compose -f config/docker-compose.prod.yml up -d

# Verify
docker-compose -f config/docker-compose.prod.yml ps
```

---

## Directory Structure Reference

```
/opt/pureleven/
├── config/
│   ├── docker-compose.prod.yml
│   └── .env
├── backend/
├── frontend/
├── infra/
└── .git/
```

---

## Credentials Reference

| Item | Value |
|------|-------|
| **Host** | 172.105.48.142 |
| **User** | root |
| **Path** | /opt/pureleven |
| **Branch** | main |
| **DB User** | pureleven_user |
| **DB Name** | pureleven_db |

---

## Troubleshooting

**Backend won't start after pull?**
```bash
docker-compose -f config/docker-compose.prod.yml logs backend
# Check for model import errors or migration issues
```

**Database migration failed?**
```bash
# Restore from backup and retry
pg_restore -U pureleven_user -d pureleven_db /tmp/prod_backup_YYYY-MM-DD.dump
```

**Port 8000 already in use?**
```bash
docker-compose -f config/docker-compose.prod.yml down
# then up -d again
```

**Frontend not showing new code?**
```bash
# Clear Docker image cache
docker-compose -f config/docker-compose.prod.yml pull
```

---

## Questions?

If anything fails, check:
1. Git status: `git log --oneline -5`
2. Docker status: `docker-compose -f config/docker-compose.prod.yml ps`
3. Logs: `docker-compose -f config/docker-compose.prod.yml logs backend`
4. Database: `docker-compose -f config/docker-compose.prod.yml exec db psql -U pureleven_user -d pureleven_db -c "SELECT COUNT(*) FROM employees;"`

---

**Last Updated:** February 27, 2026
