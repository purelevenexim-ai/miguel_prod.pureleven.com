#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# AUTO-GENERATE PULL SCRIPTS ON PRODUCTION SERVER
# Run this ONCE to create all necessary pull/deploy scripts on production
# Usage: bash create_prod_scripts.sh
# ═══════════════════════════════════════════════════════════════════════════

set -e

echo "═══════════════════════════════════════════════════════════"
echo "📝 GENERATING PRODUCTION SCRIPTS"
echo "═══════════════════════════════════════════════════════════"
echo ""

PROD_DIR="${1:-.}"  # Use current dir if not specified
mkdir -p "$PROD_DIR/scripts"

echo "📁 Creating scripts in: $PROD_DIR/scripts"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# Script 1: pull_to_prod.sh - Manual pull with verification
# ═══════════════════════════════════════════════════════════════════════════

cat > "$PROD_DIR/scripts/pull_to_prod.sh" << 'PULL_SCRIPT'
#!/bin/bash
# Pull latest code from origin/main and restart backend
set -e

echo "═══════════════════════════════════════════════════════════"
echo "📥 PULLING LATEST CODE TO PRODUCTION"
echo "═══════════════════════════════════════════════════════════"
echo ""

cd /opt/pureleven || { echo "❌ Failed to cd to /opt/pureleven"; exit 1; }

# Step 1: Check current state
echo "📋 Step 1: Current Git State"
echo "  Branch: $(git rev-parse --abbrev-ref HEAD)"
echo "  Commit: $(git log --oneline -1)"
echo ""

# Step 2: Clean local changes
echo "🧹 Step 2: Cleaning local changes..."
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -name '*.pyc' -delete 2>/dev/null || true
git reset --hard HEAD 2>/dev/null || true
echo "  ✅ Local changes cleaned"
echo ""

# Step 3: Fetch and check
echo "📤 Step 3: Fetching from origin..."
git fetch origin main
CURRENT=$(git rev-parse HEAD)
ORIGIN=$(git rev-parse origin/main)

if [ "$CURRENT" = "$ORIGIN" ]; then
    echo "ℹ️  Already up to date!"
else
    echo "🔄 Pulling new code..."
    git pull origin main
    
    # Step 4: Restart backend
    echo "🔄 Restarting backend..."
    docker restart pureleven_backend 2>/dev/null || \
    docker-compose -f config/docker-compose.prod.yml restart backend 2>/dev/null || true
    sleep 5
fi

# Step 5: Verify
echo ""
echo "✅ PULL COMPLETE"
echo ""
echo "📊 Status:"
echo "  Git: $(git log --oneline -1)"
docker ps --filter name=pureleven --format "table {{.Names}}\t{{.Status}}"
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs 2>/dev/null || echo "000")
echo "  API: HTTP $HEALTH"
echo ""
PULL_SCRIPT

chmod +x "$PROD_DIR/scripts/pull_to_prod.sh"
echo "✅ Created: scripts/pull_to_prod.sh"

# ═══════════════════════════════════════════════════════════════════════════
# Script 2: watch_logs.sh - Tail backend logs in real-time
# ═══════════════════════════════════════════════════════════════════════════

cat > "$PROD_DIR/scripts/watch_logs.sh" << 'LOGS_SCRIPT'
#!/bin/bash
# Watch backend logs in real-time
docker logs -f pureleven_backend
LOGS_SCRIPT

chmod +x "$PROD_DIR/scripts/watch_logs.sh"
echo "✅ Created: scripts/watch_logs.sh"

# ═══════════════════════════════════════════════════════════════════════════
# Script 3: restart_backend.sh - Quick backend restart
# ═══════════════════════════════════════════════════════════════════════════

cat > "$PROD_DIR/scripts/restart_backend.sh" << 'RESTART_SCRIPT'
#!/bin/bash
# Quick backend restart
echo "🔄 Restarting backend..."
docker restart pureleven_backend 2>/dev/null || \
docker-compose -f config/docker-compose.prod.yml restart backend 2>/dev/null || true
sleep 3
echo "✅ Backend restarted"
docker ps --filter name=pureleven_backend --format "table {{.Names}}\t{{.Status}}"
RESTART_SCRIPT

chmod +x "$PROD_DIR/scripts/restart_backend.sh"
echo "✅ Created: scripts/restart_backend.sh"

# ═══════════════════════════════════════════════════════════════════════════
# Script 4: check_status.sh - Quick health check
# ═══════════════════════════════════════════════════════════════════════════

cat > "$PROD_DIR/scripts/check_status.sh" << 'STATUS_SCRIPT'
#!/bin/bash
# Quick health check
echo "═══════════════════════════════════════════════════════════"
echo "🔍 PRODUCTION STATUS"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "📋 Git:"
git log --oneline -1
echo ""
echo "🐳 Containers:"
docker ps --filter name=pureleven --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "🧪 API Health:"
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:8000/docs
echo ""
echo "📊 Recent Logs (last 5 lines):"
docker logs pureleven_backend --tail=5 2>/dev/null | tail -5
echo ""
STATUS_SCRIPT

chmod +x "$PROD_DIR/scripts/check_status.sh"
echo "✅ Created: scripts/check_status.sh"

# ═══════════════════════════════════════════════════════════════════════════
# Script 5: quick_deploy.sh - Pull + restart (all-in-one)
# ═══════════════════════════════════════════════════════════════════════════

cat > "$PROD_DIR/scripts/quick_deploy.sh" << 'DEPLOY_SCRIPT'
#!/bin/bash
# Quick deploy: pull + restart + verify
set -e

cd /opt/pureleven
git fetch origin && git pull origin main
docker restart pureleven_backend 2>/dev/null || \
docker-compose -f config/docker-compose.prod.yml restart backend 2>/dev/null || true
sleep 3

echo "✅ Deployed!"
echo "Git: $(git log --oneline -1)"
curl -s -o /dev/null -w "API: HTTP %{http_code}\n" http://localhost:8000/docs
DEPLOY_SCRIPT

chmod +x "$PROD_DIR/scripts/quick_deploy.sh"
echo "✅ Created: scripts/quick_deploy.sh"

# ═══════════════════════════════════════════════════════════════════════════
# Create README with all commands
# ═══════════════════════════════════════════════════════════════════════════

cat > "$PROD_DIR/scripts/README_PROD.md" << 'README'
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

README

chmod 644 "$PROD_DIR/scripts/README_PROD.md"
echo "✅ Created: scripts/README_PROD.md"

# ═══════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ PRODUCTION SCRIPTS CREATED"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "📁 Location: $PROD_DIR/scripts/"
echo ""
echo "📄 Scripts created:"
echo "   1. pull_to_prod.sh         - Pull code + restart"
echo "   2. quick_deploy.sh         - Fast pull + restart"
echo "   3. restart_backend.sh      - Restart only"
echo "   4. check_status.sh         - Health check"
echo "   5. watch_logs.sh           - Tail logs"
echo "   6. README_PROD.md          - Command reference"
echo ""
echo "✨ Usage:"
echo "   bash scripts/pull_to_prod.sh          # Recommended for manual pulls"
echo "   bash scripts/quick_deploy.sh          # Fast alternative"
echo "   bash scripts/check_status.sh          # Check health"
echo "   bash scripts/watch_logs.sh            # Debug logs"
echo ""
