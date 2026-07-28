# 🚀 Production Deployment - Step by Step

## 📍 Location
You're currently on: **UAT Server** (`/opt/miguel`)
You need to deploy on: **Production Server** (`172.105.48.142:/opt/pureleven`)

---

## ⚡ Quick Start (Copy-Paste Ready)

### Step 1: SSH to Production Server
```bash
ssh root@172.105.48.142
```

Expected output: `root@localhost:~#`

### Step 2: Complete the Deployment
```bash
cd /opt/pureleven && bash /tmp/complete_deployment.sh
```

**That's it!** Wait 2-3 minutes for completion.

---

## 🔍 Detailed Steps (If You Need Them)

### Step 1: Connect to Production Server
```bash
ssh root@172.105.48.142
```

You should now be on the production server:
```
root@localhost:~#
```

### Step 2: Navigate to Production Directory
```bash
cd /opt/pureleven
pwd
# Should show: /opt/pureleven
```

### Step 3: Create Database Backup
```bash
BACKUP="/tmp/prod_backup_$(date +%F_%H%M%S).dump"
docker-compose -f config/docker-compose.prod.yml exec -T db pg_dump -U pureleven_user pureleven_db -Fc > "$BACKUP"
echo "Backup: $BACKUP"
ls -lh "$BACKUP"
```

Expected: A .dump file around 2-5 MB

### Step 4: Pull Latest Docker Images
```bash
docker-compose -f config/docker-compose.prod.yml pull
```

Expected: Shows pulling backend, db, nginx images

### Step 5: Start/Restart Containers
```bash
docker-compose -f config/docker-compose.prod.yml up -d --remove-orphans
sleep 10
docker-compose -f config/docker-compose.prod.yml ps
```

Expected: All containers RUNNING

### Step 6: Run Database Migrations
```bash
docker-compose -f config/docker-compose.prod.yml exec -T backend bash -c "cd /app && alembic upgrade head"
```

Expected: Shows "INFO [alembic.runtime.migration] Running upgrade..." messages

### Step 7: Verify Deployment
```bash
# Check service status
docker-compose -f config/docker-compose.prod.yml ps

# Test API
curl -I http://localhost:8000/docs

# Check recent logs
docker-compose -f config/docker-compose.prod.yml logs --tail=20 backend
```

Expected: All running, HTTP 200 response

---

## ✅ Verification Checklist

After deployment, verify everything works:

```bash
# 1. Check git is updated
git log --oneline -1
# Expected: 0d8a977 Add quick deployment reference card

# 2. Check services
docker-compose -f config/docker-compose.prod.yml ps
# Expected: All RUNNING (db, backend, nginx)

# 3. Test API
curl -I http://localhost:8000/docs
# Expected: HTTP/1.1 200 OK

# 4. Check database
docker-compose -f config/docker-compose.prod.yml exec -T db \
  psql -U pureleven_user -d pureleven_db -c "SELECT COUNT(*) as user_count FROM users;"
# Expected: user_count > 0

# 5. Test login
curl -X POST http://localhost:8000/tenant/login \
  -H 'Content-Type: application/json' \
  -d '{
    "slug":"purelevenexim",
    "email":"admin@purelevenexim.com",
    "password":"Admin@123"
  }' | jq .
# Expected: Returns JWT token
```

---

## 🆘 If Something Goes Wrong

### Error: Permission Denied
```bash
# Check if you can SSH
ssh -v root@172.105.48.142

# If SSH fails, check your keys are configured
cat ~/.ssh/id_rsa
# Should show: -----BEGIN RSA PRIVATE KEY-----
```

### Error: /opt/pureleven: No such file
```bash
# You're on the wrong server
pwd  # Check your location
hostname  # Check server name

# If on UAT (/opt/miguel), you need to SSH to production first!
ssh root@172.105.48.142
```

### Error: docker-compose command not found
```bash
# Check docker is installed
docker --version
docker-compose --version

# Restart docker if needed
systemctl restart docker
```

### Error: Database connection failed
```bash
# Check if database container is running
docker ps | grep db

# Check database logs
docker-compose -f config/docker-compose.prod.yml logs db

# If stuck, restart the database
docker-compose -f config/docker-compose.prod.yml down
docker-compose -f config/docker-compose.prod.yml up -d
sleep 10
```

### Containers Won't Start
```bash
# View full logs
docker-compose -f config/docker-compose.prod.yml logs

# Check available disk space
df -h

# Check memory
free -h

# Restart everything
docker-compose -f config/docker-compose.prod.yml down
docker-compose -f config/docker-compose.prod.yml up -d --remove-orphans
```

---

## 🔄 Rollback (If Needed)

```bash
# Stop services
docker-compose -f config/docker-compose.prod.yml down

# Restore database from backup
BACKUP="/tmp/prod_backup_*.dump"  # Use actual timestamp
pg_restore -U pureleven_user -d pureleven_db $BACKUP

# Restart
docker-compose -f config/docker-compose.prod.yml up -d

# Verify
docker-compose -f config/docker-compose.prod.yml ps
```

---

## 📊 Key Information

| Item | Value |
|------|-------|
| **Production Server** | 172.105.48.142 |
| **Production Directory** | /opt/pureleven |
| **Database** | pureleven_db (PostgreSQL 15) |
| **API Port** | 8000 |
| **Admin User** | admin@purelevenexim.com |
| **Admin Password** | Admin@123 |
| **Tenant Slug** | purelevenexim |
| **Latest Commit** | 0d8a977 |
| **Backup Location** | /tmp/prod_backup_*.dump |

---

## 🎯 Summary

1. **SSH to production:** `ssh root@172.105.48.142`
2. **Run deployment:** `cd /opt/pureleven && bash /tmp/complete_deployment.sh`
3. **Verify:** Check services and test API
4. **Done!** Production updated

**Time required:** 2-3 minutes

---

**Status:** ✅ Ready to Deploy
**Created:** Feb 27, 2026
