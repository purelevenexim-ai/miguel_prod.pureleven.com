# Production Setup — Port 80 Configuration

**Updated:** February 25, 2026  
**Status:** ✅ Live on Port 80

---

## **What Changed**

✅ **Frontend moved from port 3000 → port 80**
- Updated `docker-compose.yml`: Changed `3000:80` to `80:80`
- Stopped system Nginx that was listening on port 80
- Restarted Docker services to apply network changes
- All 3 Docker services now running on standard ports

---

## **Access Points (Updated)**

| Component | URL | Port | Status |
|-----------|-----|------|--------|
| **Frontend (Login)** | `http://172.232.118.208/login` | 80 | ✅ Working |
| **Admin Dashboard** | `http://172.232.118.208/tenant-admin` | 80 | ✅ Working |
| **Backend API** | `http://172.232.118.208:8000` | 8000 | ✅ Working |
| **API Docs (Swagger)** | `http://172.232.118.208:8000/docs` | 8000 | ✅ Working |
| **API ReDoc** | `http://172.232.118.208:8000/redoc` | 8000 | ✅ Working |

---

## **Test Credentials**

```
Email:    purelevenexim@gmail.com
Password: wM01gkxGCNhJT!
```

---

## **Quick Commands**

### **Check Service Status**
```bash
docker ps
```

### **View Nginx Logs**
```bash
docker logs miguel_frontend -f
```

### **View Backend Logs**
```bash
docker logs miguel_backend -f
```

### **Stop All Services**
```bash
docker compose down
```

### **Restart All Services**
```bash
docker compose up -d
```

### **Test API Endpoints**
```bash
python3 /opt/miguel/scripts/test_shipping.py
```

---

## **Important Notes**

### **System Nginx**
- The system Nginx service (`nginx` PID 744) was stopped
- If you need it later, restart with: `sudo systemctl start nginx`
- However, this will conflict with Docker Nginx on port 80

### **Network**
- All services communicate via Docker network: `miguel_miguel_network`
- Frontend can reach backend via hostname `backend:8000` (internal)
- External requests go through Nginx routing rules in `infra/nginx.conf`

### **Port 80 (Standard HTTP)**
- No additional port number needed in URLs
- Direct IP access now works: `http://172.232.118.208/login`
- Perfect for production with SSL/TLS termination

---

## **SSL/TLS Setup (Optional)**

For HTTPS, you can add SSL certificates to the Nginx container:

```yaml
# In docker-compose.yml frontend service
volumes:
  - ./frontend:/usr/share/nginx/html:ro
  - ./infra/nginx.conf:/etc/nginx/nginx.conf:ro
  - /etc/letsencrypt:/etc/letsencrypt:ro  # Add this
```

Then update `infra/nginx.conf` to listen on 443 and redirect HTTP to HTTPS.

---

## **Verification Checklist**

- [x] Frontend accessible on port 80
- [x] Login page returning 200 OK
- [x] Backend API responding
- [x] API documentation accessible
- [x] Docker network configured properly
- [x] All 3 services running
- [x] System Nginx stopped (no conflict)

✅ **Production setup complete!**

---

**Next Steps:**
1. Access the dashboard: `http://172.232.118.208/login`
2. Log in with provided credentials
3. Configure Shopify stores, delivery partners, etc.
4. Run integration tests: `python3 scripts/test_shipping.py`

