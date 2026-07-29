# Production Server Scripts

All scripts are located in `/opt/pureleven/scripts/`

## Quick Commands

### Pull Latest Code
```bash
bash scripts/pull_to_prod.sh
```
- Fetches latest code from origin/main
- Cleans local cache files
- Restarts backend if updates found
- Verifies services are running

### Quick Deploy (Pull + Restart)
```bash
bash scripts/quick_deploy.sh
```
- Pulls code and restarts backend in one command
- Minimal output, fast execution

### Restart Backend Only
```bash
bash scripts/restart_backend.sh
```
- Restarts the backend container
- No code pull, no verification

### Check Status
```bash
bash scripts/check_status.sh
```
- Show git commit
- Show container status
- Show API health (HTTP status code)
- Show recent logs

### Watch Logs
```bash
bash scripts/watch_logs.sh
```
- Tail backend logs in real-time
- Press Ctrl+C to exit

## Manual Commands (if you need raw git/docker)

```bash
# Check git status
git status
git log --oneline -5

# Pull code manually
git fetch origin
git pull origin main

# View containers
docker ps

# Restart backend
docker restart pureleven_backend

# View logs
docker logs -f pureleven_backend

# Database access
docker exec -it pureleven_db psql -U pureleven_user -d pureleven_db
```

## Troubleshooting

### Backend won't start
```bash
docker logs pureleven_backend | tail -50
bash scripts/restart_backend.sh
```

### API returns 500
Check logs:
```bash
bash scripts/watch_logs.sh
```

### Need to rollback
```bash
git log --oneline -10  # Find the commit
git reset --hard <commit-hash>
bash scripts/restart_backend.sh
```

