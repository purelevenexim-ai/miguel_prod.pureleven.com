# 🚀 Production Deployment - QUICK FIX GUIDE

## Issue Summary
Production deployment blocked by:
1. **Git merge conflict** - local changes in `/opt/pureleven` preventing pull
2. **Docker-compose path error** - incorrect path reference in script

## ⚡ Quick Fix (One Command)

Run this on the production server (ssh to 172.105.48.142):

```bash
cd /opt/pureleven && \
git clean -fd backend/app/models/__pycache__ && \
git checkout -- docker-compose.yml && \
git pull origin main && \
bash scripts/deploy_to_prod_FIXED.sh
```

This will:
- ✅ Clean Python cache files
- ✅ Discard local docker-compose.yml changes
- ✅ Pull latest code from Git
- ✅ Run complete deployment with backups, migrations, and verification

## 🔍 Step-by-Step (If Issues Occur)

### Step 1: Connect to Production Server
```bash
ssh root@172.105.48.142
cd /opt/pureleven
```

### Step 2: Check Current Status
```bash
git status
git log --oneline -1
```

### Step 3: Clean Local Changes
```bash
# Remove Python cache
git clean -fd backend/app/models/__pycache__

# Discard docker-compose.yml changes
git checkout -- docker-compose.yml

# Verify cleanup
git status  # Should show "working tree clean"
```

### Step 4: Pull Latest Code
```bash
git pull origin main
git log --oneline -1  # Should show commit 17b5983
```

### Step 5: Run Deployment Script
```bash
# Option A: Run the corrected script
bash scripts/deploy_to_prod_FIXED.sh

# Option B: Or run steps manually (see below)
```

## 🛠️ Manual Deployment (If Script Fails)

### Backup Database
```bash
BACKUP="/tmp/prod_backup_$(date +%F_%H%M%S).dump"
docker-compose -f config/docker-compose.prod.yml exec -T db pg_dump \
  -U pureleven_user pureleven_db -Fc > "$BACKUP"
echo "Backup saved: $BACKUP"
```

### Update Containers
```bash
# Pull latest images
docker-compose -f config/docker-compose.prod.yml pull

# Start/update containers
docker-compose -f config/docker-compose.prod.yml up -d --remove-orphans

# Wait for startup
sleep 10
```

### Run Migrations
```bash
docker-compose -f config/docker-compose.prod.yml exec -T backend \
  bash -c "cd /app && alembic upgrade head"
```

### Verify Services
```bash
docker-compose -f config/docker-compose.prod.yml ps
docker-compose -f config/docker-compose.prod.yml logs --tail=30 backend
```

### Test API
```bash
curl -I http://localhost:8000/docs  # Should return 200
```

## 🔧 Troubleshooting

### If git pull still fails
```bash
# Show what's being blocked
git status

# Force reset if needed (BE CAREFUL)
git reset --hard HEAD

# Then pull again
git pull origin main
```

### If docker-compose.prod.yml not found
```bash
# Check what files exist
ls -la config/
ls -la docker-compose*

# If config/docker-compose.prod.yml exists, use absolute path
docker-compose -f /opt/pureleven/config/docker-compose.prod.yml ps
```

### If containers won't start
```bash
# Check logs
docker-compose -f config/docker-compose.prod.yml logs backend

# Restart everything
docker-compose -f config/docker-compose.prod.yml down
docker-compose -f config/docker-compose.prod.yml up -d

# Wait and check again
sleep 10
docker-compose -f config/docker-compose.prod.yml ps
```

### If migrations fail
```bash
# Check migration status
docker-compose -f config/docker-compose.prod.yml exec -T backend \
  bash -c "cd /app && alembic current"

# View pending migrations
docker-compose -f config/docker-compose.prod.yml exec -T backend \
  bash -c "cd /app && alembic history --verbose | tail -5"

# Retry migration
docker-compose -f config/docker-compose.prod.yml exec -T backend \
  bash -c "cd /app && alembic upgrade head"
```

## ✅ Verification Checklist

After deployment completes:

- [ ] `git log --oneline -1` shows commit 17b5983
- [ ] `docker-compose ps` shows all services RUNNING
- [ ] Backend logs show no ERROR or CRITICAL messages
- [ ] `curl -I http://localhost:8000/docs` returns HTTP 200
- [ ] Can login to tenant: POST /tenant/login (admin@purelevenexim.com)
- [ ] Database shows recent changes: `SELECT COUNT(*) FROM users;`

## 🔄 Rollback (If Needed)

```bash
# Stop services
docker-compose -f config/docker-compose.prod.yml down

# Restore from backup
pg_restore -U pureleven_user -d pureleven_db /tmp/prod_backup_*.dump

# Restart
docker-compose -f config/docker-compose.prod.yml up -d

# Verify
docker-compose -f config/docker-compose.prod.yml ps
```

## 📝 Notes

- All backups saved to `/tmp/prod_backup_*.dump`
- Logs available: `docker-compose logs -f backend`
- To push future updates: commit to main, then run this same process
- Git fetch happens automatically, so deploy script stays current

---

**Created:** $(date)
**Target:** Production server at 172.105.48.142:/opt/pureleven
**Status:** Ready to deploy

