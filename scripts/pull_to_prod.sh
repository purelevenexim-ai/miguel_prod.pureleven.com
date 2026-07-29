#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# �� PULL TO PRODUCTION — The ONE script to use on the prod server
#
# This script is the permanent, safe way to deploy.
# It always uses: docker compose -p pureleven
# which ensures ALL containers share the SAME network (pureleven_pureleven_network)
# and the backend image is always named pureleven_backend.
#
# Usage (on prod server):
#   bash scripts/pull_to_prod.sh
#
# ═══════════════════════════════════════════════════════════════════════════
set -e

COMPOSE="docker compose -p pureleven -f config/docker-compose.prod.yml"

echo "═══════════════════════════════════════════════════════════════════════════"
echo "📥 PULLING LATEST CODE TO PRODUCTION"
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""

cd /opt/pureleven || { echo "❌ Failed to cd to /opt/pureleven"; exit 1; }

# ── Phase 1: Clean & Pull from GitHub ───────────────────────────────────────
echo "🌐 PHASE 1: PULLING FROM GITHUB"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "  Current: $(git log --oneline -1)"

# Clean Python cache so it never blocks a pull
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -name '*.pyc' -delete 2>/dev/null || true

# Hard-reset to avoid local-change conflicts (never edit files directly on prod)
git fetch origin main
CURRENT=$(git rev-parse HEAD)
ORIGIN=$(git rev-parse origin/main)

if [ "$CURRENT" = "$ORIGIN" ]; then
    echo "  ℹ️  Already up to date: $(git log --oneline -1)"
    UPDATED=false
else
    git reset --hard origin/main
    echo "  ✅ Pulled: $(git log --oneline -1)"
    UPDATED=true
fi
echo ""

# ── Phase 2: Rebuild & Restart Backend ──────────────────────────────────────
echo "🔄 PHASE 2: REBUILDING BACKEND"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Always rebuild backend — ensures fresh code + correct image name + correct network
$COMPOSE up -d --build --force-recreate backend
echo "  ✅ Backend rebuilt and running"
echo ""

# ── Phase 3: Reload Nginx (frontend) ────────────────────────────────────────
echo "🔄 PHASE 3: RELOADING FRONTEND"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Recreate frontend to pick up any nginx config changes (fast, no downtime)
$COMPOSE up -d --force-recreate frontend
echo "  ✅ Frontend reloaded"
echo ""

# ── Phase 4: Wait for Health ─────────────────────────────────────────────────
echo "⏳ PHASE 4: WAITING FOR HEALTH"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sleep 8
echo ""

# ── Phase 5: Verify ─────────────────────────────────────────────────────────
echo "✅ PHASE 5: VERIFYING"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "  Containers:"
docker ps --filter name=pureleven --format "    {{.Names}}\t{{.Status}}\t{{.Image}}"
echo ""

# Check all three are on the SAME network
echo "  Networks:"
for c in pureleven_db pureleven_backend pureleven_frontend; do
    NET=$(docker inspect $c 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin)[0]; nets=list(d['NetworkSettings']['Networks'].keys()); print(', '.join(nets))" 2>/dev/null || echo "not running")
    echo "    $c → $NET"
done
echo ""

# API health check
API=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs 2>/dev/null || echo "000")
if [ "$API" = "200" ]; then
    echo "  ✅ API: HTTP $API (backend healthy)"
else
    echo "  ❌ API: HTTP $API — check: docker logs pureleven_backend --tail 30"
fi

# Nginx DNS check
DNS=$(docker exec pureleven_frontend nslookup pureleven_backend 127.0.0.11 2>&1 | grep "Address:" | tail -1)
if echo "$DNS" | grep -q "172\|10\."; then
    echo "  ✅ Nginx DNS: pureleven_backend resolves to $DNS"
else
    echo "  ❌ Nginx DNS: backend hostname not resolving — containers may be on different networks"
    echo "     Run: docker network connect pureleven_pureleven_network pureleven_frontend"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo "✅ DEPLOYMENT COMPLETE"
echo "  Git: $(git log --oneline -1)"
echo "  API: http://localhost:8000"
echo "  App: https://prod.pureleven.com"
echo "═══════════════════════════════════════════════════════════════════════════"
