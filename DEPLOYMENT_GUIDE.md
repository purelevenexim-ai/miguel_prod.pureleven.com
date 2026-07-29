# PureLevenExim CRM — Deployment & Production Operations Guide

**Document Version:** 1.0  
**Last Updated:** March 3, 2026  
**Status:** ✅ Production Deployment SOP

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Deployment Procedures](#deployment-procedures)
3. [Container Management Rules](#container-management-rules)
4. [Incident Response](#incident-response)
5. [Monitoring & Health Checks](#monitoring--health-checks)
6. [Rollback Procedures](#rollback-procedures)

---

## Pre-Deployment Checklist

### Automated (Git Hooks)

Every push to `main` branch automatically runs 10 pre-deployment checks:

1. **No uncommitted changes** → `git status --porcelain`
2. **Commit signatures verified** → `git verify-commit`
3. **No sensitive files** → Regex scan for `.env`, `secrets`, `password`, `api_key`
4. **Docker files present** → Check `docker-compose.prod.yml`, `nginx-prod.conf`, `Dockerfile`
5. **Nginx syntax valid** → `docker run --rm nginx:alpine nginx -t`
6. **Python syntax valid** → `python3 -m py_compile` for all `.py` files
7. **Frontend validity** → Balanced brackets in all `.html` files
8. **Commit message format** → Conventional commits (`feat:`, `fix:`, `docs:`, etc.)
9. **Database migrations tracked** → Check `backend/alembic/versions/`
10. **Documentation updated** → Warn if README/CHANGELOG not updated with code changes

**If ANY check fails, push is BLOCKED.**

### Manual (Before You Code)

- [ ] You have the latest `main` branch: `git pull origin main`
- [ ] You're on a feature branch: `git checkout -b feature/your-feature`
- [ ] No conflicting changes exist: `git log --oneline origin/main..HEAD`
- [ ] All tests pass locally: `pytest backend/tests/` (if using pytest)
- [ ] Nginx config changes tested locally (if applicable)

---

## Deployment Procedures

### Scenario 1: Frontend-Only Change (HTML/CSS/JS)

```bash
# 1. Make changes in frontend/*.html
git add frontend/*.html
git commit -m "fix: description of frontend fix"

# 2. Push (hooks run automatically)
git push origin main

# 3. Pull on production
ssh root@172.105.48.142 "cd /opt/pureleven && git pull origin main"

# 4. Restart frontend container ONLY (no DB/backend restart needed)
ssh root@172.105.48.142 "cd /opt/pureleven && docker-compose -f config/docker-compose.prod.yml --env-file .env up -d --no-deps frontend"

# 5. Verify (HTTP 301, HTTPS 200)
curl -sk -o /dev/null -w 'HTTP:%{http_code}' http://localhost/ && echo ''
curl -sk -o /dev/null -w 'HTTPS:%{http_code}' https://prod.pureleven.com/ && echo ''
```

### Scenario 2: Backend Change (Python/API)

```bash
# 1. Make changes in backend/app/
git add backend/app/
git commit -m "feat: new API endpoint"

# 2. If database schema changed, also:
git add backend/alembic/versions/
git commit -m "feat: migration for schema change"

# 3. Push (hooks verify Python syntax)
git push origin main

# 4. Pull on production
ssh root@172.105.48.142 "cd /opt/pureleven && git pull origin main"

# 5. Run migrations (if any)
ssh root@172.105.48.142 "docker exec pureleven_backend alembic upgrade head"

# 6. Rebuild and restart backend
ssh root@172.105.48.142 "cd /opt/pureleven && docker-compose -f config/docker-compose.prod.yml --env-file .env up -d --build backend"

# 7. Verify API is responding
curl -sk -o /dev/null -w '%{http_code}' http://localhost:8000/docs && echo ''
```

### Scenario 3: Infrastructure Change (Docker/Nginx)

```bash
# 1. Make changes in config/, infra/
git add config/ infra/
git commit -m "fix: nginx DNS resolver for dynamic upstream"

# 2. Push (hooks validate nginx config)
git push origin main

# 3. Pull on production
ssh root@172.105.48.142 "cd /opt/pureleven && git pull origin main"

# 4. Recreate all containers (preserves network)
ssh root@172.105.48.142 "cd /opt/pureleven && docker-compose -f config/docker-compose.prod.yml --env-file .env up -d --build --force-recreate"

# 5. Full verification
ssh root@172.105.48.142 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'
ssh root@172.105.48.142 "docker logs pureleven_frontend --tail 5"
```

### Scenario 4: Multiple Changes (Use Deploy Script)

```bash
# All of the above, automated:
bash scripts/deploy.sh

# What it does:
# 1. Commits local changes
# 2. Pushes to origin/main
# 3. Pulls on production
# 4. Recreates frontend container
# 5. Verifies all endpoints responding
# 6. Prints health status
```

---

## Container Management Rules

### ✅ CORRECT: Always use docker-compose

```bash
# Single container update (frontend only)
docker-compose -f config/docker-compose.prod.yml --env-file .env up -d --no-deps frontend

# Rebuild backend
docker-compose -f config/docker-compose.prod.yml --env-file .env up -d --build backend

# Full recreate (nuclear option, last resort)
docker-compose -f config/docker-compose.prod.yml --env-file .env up -d --build --force-recreate
```

### ❌ WRONG: Never use direct docker commands

```bash
docker restart pureleven_frontend    # ❌ Will crash with DNS errors!
docker stop pureleven_backend        # ❌ May break networking!
docker rm pureleven_frontend         # ❌ Loss of network membership!
docker run -d ...                    # ❌ Creates wrong network!
```

### Why the Rule Exists

The nginx config uses:
```nginx
resolver 127.0.0.11 valid=10s;  # Docker's embedded DNS
set $backend http://backend:8000;
proxy_pass $backend;              # Resolves at REQUEST time
```

This requires the container to be on the Docker network **with proper DNS setup**. Using `docker-compose` automatically handles this. Using `docker restart` can:

1. Break DNS resolution inside the container
2. Cause nginx to fail with `host not found in upstream "backend"`
3. Enter a crash loop requiring manual intervention

---

## Incident Response

### Incident: Site is Down (HTTP 500+ or Connection Refused)

```bash
# 1. Check container status
ssh root@172.105.48.142 "docker ps -a --format 'table {{.Names}}\t{{.Status}}'"

# 2. If frontend is restarting, check logs
ssh root@172.105.48.142 "docker logs pureleven_frontend --tail 20"

# 3. If nginx crash error (host not found), it means wrong restart command used
#    Fix with proper docker-compose restart
ssh root@172.105.48.142 "cd /opt/pureleven && docker-compose -f config/docker-compose.prod.yml --env-file .env up -d frontend"

# 4. Check backend is responsive
ssh root@172.105.48.142 "curl http://localhost:8000/docs"

# 5. If backend is down, restart it
ssh root@172.105.48.142 "cd /opt/pureleven && docker-compose -f config/docker-compose.prod.yml --env-file .env up -d backend"

# 6. If database is down, check disk/memory
ssh root@172.105.48.142 "docker logs pureleven_db --tail 10"
```

### Incident: Slow/Hanging Requests

```bash
# 1. Check backend CPU/memory
ssh root@172.105.48.142 "docker stats pureleven_backend --no-stream"

# 2. Check database locks
ssh root@172.105.48.142 "docker exec pureleven_db psql -U pureleven_user -d pureleven_db -c 'SELECT pid, usename, state FROM pg_stat_activity WHERE state != '\''idle'\'';'"

# 3. Check if backend is stuck
ssh root@172.105.48.142 "curl -v http://localhost:8000/docs"

# 4. Soft restart backend (graceful)
ssh root@172.105.48.142 "docker-compose -f config/docker-compose.prod.yml --env-file .env restart backend"

# 5. Hard restart if soft doesn't work
ssh root@172.105.48.142 "cd /opt/pureleven && docker-compose -f config/docker-compose.prod.yml --env-file .env up -d backend"
```

### Incident: DNS Resolution Error (host not found in upstream)

**This means someone used `docker restart` instead of `docker-compose`.**

```bash
# 1. Remove the broken container
ssh root@172.105.48.142 "docker rm -f pureleven_frontend"

# 2. Recreate with docker-compose
ssh root@172.105.48.142 "cd /opt/pureleven && docker-compose -f config/docker-compose.prod.yml --env-file .env up -d frontend"

# 3. Verify
ssh root@172.105.48.142 "docker logs pureleven_frontend --tail 3"

# 4. Test
curl https://prod.pureleven.com/
```

---

## Monitoring & Health Checks

### Docker Compose Healthchecks (Automated)

All containers have healthchecks:

```yaml
db:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U pureleven_user -d pureleven_db"]
    interval: 5s
    timeout: 3s
    retries: 5

backend:
  healthcheck:
    test: ["CMD-SHELL", "curl -sf http://localhost:8000/docs > /dev/null || exit 1"]
    interval: 10s
    timeout: 5s
    retries: 5
    start_period: 15s
```

Check health status:
```bash
ssh root@172.105.48.142 "docker ps --format 'table {{.Names}}\t{{.Status}}'"
# Look for "(healthy)" in Status
```

### Manual Endpoint Checks

```bash
# Frontend (HTTP → HTTPS redirect)
curl -sk -o /dev/null -w 'Status: %{http_code}\n' http://localhost/
# Expected: 301

# Frontend (HTTPS)
curl -sk -o /dev/null -w 'Status: %{http_code}\n' https://prod.pureleven.com/
# Expected: 200

# Backend API
curl -sk http://localhost:8000/docs
# Expected: 200

# Database
ssh root@172.105.48.142 "docker exec pureleven_db pg_isready -U pureleven_user -d pureleven_db"
# Expected: accepting connections
```

### Log Monitoring

```bash
# Frontend (nginx)
ssh root@172.105.48.142 "docker logs -f pureleven_frontend"

# Backend (FastAPI)
ssh root@172.105.48.142 "docker logs -f pureleven_backend"

# Database
ssh root@172.105.48.142 "docker logs -f pureleven_db"
```

---

## Rollback Procedures

### Rollback Last Commit (Hotfix for Critical Bug)

```bash
# 1. Identify the broken commit
git log --oneline main | head -5

# 2. Revert the commit (creates a new commit)
git revert <commit-sha>

# 3. Push the revert commit
git push origin main
# (Pre-push hooks run, if they pass, production will auto-pull)

# 4. Or if urgent, manually force production
ssh root@172.105.48.142 "cd /opt/pureleven && git pull origin main && docker-compose -f config/docker-compose.prod.yml --env-file .env up -d --build"
```

### Rollback to Specific Commit (Emergency Only)

```bash
# 1. On production server (CAREFUL! This rewrites history)
ssh root@172.105.48.142 "cd /opt/pureleven && git reset --hard <commit-sha>"

# 2. Restart services
ssh root@172.105.48.142 "cd /opt/pureleven && docker-compose -f config/docker-compose.prod.yml --env-file .env up -d --build --force-recreate"

# 3. On local machine, sync with production state
git fetch origin
git reset --hard origin/main
```

### Rollback Database (Alembic Migrations)

```bash
# 1. List available migrations
ssh root@172.105.48.142 "docker exec pureleven_backend alembic history"

# 2. Downgrade to previous version
ssh root@172.105.48.142 "docker exec pureleven_backend alembic downgrade -1"

# 3. Or rollback to specific migration
ssh root@172.105.48.142 "docker exec pureleven_backend alembic downgrade <revision>"
```

---

## Safe Deployment Checklist

Before deploying:

- [ ] All pre-push checks passed
- [ ] Code reviewed and tested locally
- [ ] If backend change: all API tests pass
- [ ] If database change: migration tested locally
- [ ] If infrastructure change: nginx config validated
- [ ] You have SSH access to production
- [ ] You know the DB_PASSWORD (in .env file on prod)
- [ ] You have a rollback plan (know the previous good commit)

During deployment:

- [ ] Monitor logs: `docker logs -f <container>`
- [ ] Check health: `docker ps --format 'table {{.Names}}\t{{.Status}}'`
- [ ] Verify endpoints: `curl https://prod.pureleven.com/` and `curl http://localhost:8000/docs`

After deployment:

- [ ] Site loads without errors
- [ ] API endpoints respond (check `/tenant/login`, `/api/customers`)
- [ ] Database queries work (test login with real credentials)
- [ ] WhatsApp integration still works (if changed)
- [ ] No 500 errors in backend logs

---

## Quick Reference

| Command | Purpose | Safety |
|---|---|---|
| `bash scripts/deploy.sh` | Full automated deployment | ✅ Safest |
| `git push origin main` | Push with pre-checks | ✅ Safe |
| `docker-compose ... up -d frontend` | Restart frontend | ✅ Safe |
| `docker-compose ... up -d --build backend` | Rebuild backend | ✅ Safe |
| `docker restart pureleven_frontend` | Direct restart | ❌ **CRASHES** |
| `docker rm -f pureleven_*` | Force remove containers | ❌ **Data loss risk** |
| `git reset --hard <sha>` | Hard reset on prod | ❌ **Emergency only** |

---

## References

- **Nginx Dynamic Upstream:** https://nginx.org/en/docs/http/ngx_http_core_module.html#resolver
- **Docker Compose Health Checks:** https://docs.docker.com/compose/compose-file/#healthcheck
- **Alembic Migrations:** https://alembic.sqlalchemy.org/
- **FastAPI Deployment:** https://fastapi.tiangolo.com/deployment/

---

**Last Incident:** Mar 3, 2026 — Frontend crashed after `docker restart`. Fixed with nginx dynamic DNS resolver + docker-compose enforcement.

**Maintained By:** Miguel CRM Team  
**On-Call Runbook:** See `.git/hooks/pre-push` for automated safety checks.
