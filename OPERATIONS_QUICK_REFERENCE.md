# ⚡ Quick Reference - Production Operations

**Last Updated:** February 26, 2026  
**Environment:** Production (172.232.118.208)

---

## 🔍 System Status Check

### Check if all containers are running
```bash
docker ps
# Expected: 3 containers (db, backend, frontend) all "Up"
```

### Check backend health
```bash
curl http://localhost:8000/docs
# Expected: Swagger UI loads with all endpoints listed
```

### Check database connection
```bash
docker compose exec db psql -U pureleven_user -d pureleven_db -c "SELECT COUNT(*) FROM orders;"
# Expected: Number of orders in database
```

### View backend logs (last 50 lines)
```bash
docker logs pureleven_backend | tail -50
```

### View all errors in backend
```bash
docker logs pureleven_backend 2>&1 | grep -i error | tail -20
```

---

## 🚀 Common Operations

### Restart all services
```bash
cd /opt/pureleven
docker compose down
docker compose up -d
# Wait 10-15 seconds for startup
```

### Restart only backend (faster)
```bash
cd /opt/pureleven
docker compose restart backend
# Wait 2-3 seconds
```

### Apply database migrations
```bash
cd /opt/pureleven
docker compose exec backend alembic upgrade head
```

### Check current environment variables
```bash
cat /opt/pureleven/.env | grep -E "^[A-Z]"
```

### Update environment variable
```bash
# Edit the file
nano /opt/pureleven/.env

# Then restart backend
docker compose restart backend
```

---

## 🔐 Access & Credentials

### Test Login
- **URL:** http://172.232.118.208/login
- **Email:** purelevenexim@gmail.com
- **Password:** wM01gkxGCNhJT!

### Admin Dashboard
- **URL:** http://172.232.118.208/tenant-admin
- **After login, click "Admin Dashboard" tab**

### API Documentation
- **URL:** http://172.232.118.208:8000/docs
- **Alternative:** http://172.232.118.208:8000/redoc

### Database Access
```bash
docker compose exec db psql -U pureleven_user -d pureleven_db
# Then use standard psql commands
```

---

## 📊 Database Queries (PostgreSQL)

### Count orders by status
```sql
SELECT status, COUNT(*) FROM orders GROUP BY status;
```

### Count orders by payment status
```sql
SELECT payment_status, COUNT(*) FROM orders GROUP BY payment_status;
```

### Find orders without tracking
```sql
SELECT id, order_number, status FROM shipping_info 
WHERE tracking_number IS NULL LIMIT 10;
```

### Find high-risk customers
```sql
SELECT id, phone, risk_score FROM customers 
WHERE risk_score >= 70 ORDER BY risk_score DESC LIMIT 10;
```

### Check recent activity logs
```sql
SELECT created_at, method, path, status_code FROM activity_logs 
ORDER BY created_at DESC LIMIT 20;
```

### Find orders by tenant
```sql
SELECT id, order_number FROM orders 
WHERE tenant_id = 'UUID' LIMIT 10;
```

---

## 🔧 Troubleshooting Checklist

### Backend not starting?
- [ ] Check logs: `docker logs pureleven_backend`
- [ ] Verify .env file exists: `ls -la /opt/pureleven/.env`
- [ ] Check ENCRYPTION_KEY is set: `grep ENCRYPTION_KEY /opt/pureleven/.env`
- [ ] Verify database is running: `docker ps | grep db`
- [ ] Try full restart: `docker compose down && docker compose up -d`

### Orders page showing errors?
- [ ] Clear browser cache (Ctrl+Shift+Delete)
- [ ] Check API response: `curl http://localhost:8000/api/orders`
- [ ] Verify authentication token in localStorage
- [ ] Check backend logs for API errors

### WhatsApp notifications not sending?
- [ ] Verify WhatsApp token in shipping_config table
- [ ] Check logs: `docker logs pureleven_backend | grep -i whatsapp`
- [ ] Verify phone numbers are valid format (+91XXXXXXXXXX)
- [ ] Check notification_logs table for send attempts

### Tracking sync not updating?
- [ ] Check logs: `docker logs pureleven_backend | grep -i tracking`
- [ ] Verify delivery partner credentials are correct
- [ ] Check tracking_events table for recent updates
- [ ] Verify partner API is responding

### Port 80 not accessible?
- [ ] Check if system Nginx is running: `systemctl status nginx`
- [ ] Stop system Nginx: `sudo systemctl stop nginx`
- [ ] Verify Docker Nginx is listening: `docker logs pureleven_frontend | grep -i listen`
- [ ] Check firewall: `sudo ufw status`

---

## 📝 Regular Maintenance

### Weekly
- [ ] Review backend logs for errors
- [ ] Check database disk space: `df -h`
- [ ] Verify no stuck background workers

### Monthly
- [ ] Archive old activity logs (auto-cleanup runs daily)
- [ ] Review customer delivery scores
- [ ] Audit blacklisted customers
- [ ] Check Shopify sync success rate

### Quarterly
- [ ] Database backup: `docker compose exec db pg_dump ...`
- [ ] Update dependencies: Check requirements.txt
- [ ] Security audit: Review encrypted credentials

---

## 💾 Backup & Recovery

### Backup database
```bash
docker compose exec db pg_dump -U pureleven_user pureleven_db > /tmp/backup_$(date +%Y%m%d).sql
```

### Restore from backup
```bash
docker compose exec -T db psql -U pureleven_user pureleven_db < /tmp/backup.sql
```

### List existing backups
```bash
ls -lh /opt/pureleven/backups/
```

---

## 🧪 Testing Endpoints

### Test login
```bash
curl -X POST http://localhost:8000/api/employee-auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"purelevenexim@gmail.com","password":"wM01gkxGCNhJT!"}'
```

### Get all orders (requires token)
```bash
TOKEN="<jwt_token_from_login>"
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/orders
```

### Test shipping config endpoint
```bash
TOKEN="<jwt_token>"
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/config/shopify-stores
```

### Health check
```bash
curl http://localhost:8000/docs
# Should return 200 with Swagger UI HTML
```

---

## 📞 Important Files & Locations

| File | Location | Purpose |
|------|----------|---------|
| Environment vars | `/opt/pureleven/.env` | ENCRYPTION_KEY, DB_PASSWORD, API tokens |
| Docker config | `/opt/pureleven/docker-compose.yml` | Service definitions |
| Nginx config | `/opt/pureleven/infra/nginx.conf` | Reverse proxy rules |
| Backend main | `/opt/pureleven/backend/app/main.py` | FastAPI app entry |
| Database models | `/opt/pureleven/backend/app/models/` | SQLAlchemy ORM |
| API routers | `/opt/pureleven/backend/app/modules/*/router.py` | Endpoint definitions |
| Frontend | `/opt/pureleven/frontend/*.html` | Static pages |
| Migrations | `/opt/pureleven/backend/alembic/versions/` | Database migrations |
| Logs (temporary) | `docker logs <container>` | Real-time logs |

---

## 🎯 Feature Summary (as of Feb 26, 2026)

- ✅ Multi-tenant CRM with RBAC
- ✅ Order management with draft editing (NEW)
- ✅ Shopify store integration
- ✅ Delhivery/Blue Dart/India Post/DTDC logistics
- ✅ Tracking sync (every 15 minutes)
- ✅ WhatsApp Business API integration
- ✅ Risk assessment engine (4-factor scoring)
- ✅ Financial reporting (P&L, GST)
- ✅ Lead & customer management
- ✅ Vendor & inventory management
- ✅ Activity audit logging
- ✅ Excel tracking upload

---

## 🚨 Emergency Procedures

### Service won't start?
```bash
# 1. Check what's wrong
docker compose logs

# 2. Full restart
docker compose down -v     # Remove volumes too
docker compose up -d

# 3. Reapply migrations
docker compose exec backend alembic upgrade head
```

### Data corruption?
```bash
# 1. Restore from backup
docker compose exec -T db psql -U pureleven_user pureleven_db < /opt/pureleven/backups/latest_backup.sql

# 2. Restart services
docker compose restart
```

### Port conflict?
```bash
# Check what's using port 80
sudo lsof -i :80

# Kill the conflicting process or stop system nginx
sudo systemctl stop nginx
```

---

**Last Verified:** Feb 26, 2026, 02:30 UTC  
**Status:** ✅ All systems operational
