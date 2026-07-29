#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# PROD STATUS CHECK
# Quick check of production server health
# Run from UAT: bash scripts/prod_status.sh
# ═══════════════════════════════════════════════════════════════

PROD_SERVER="root@172.105.48.142"
PROD_DIR="/opt/pureleven"

echo "═══════════════════════════════════════════════════════════"
echo "🔍 PRODUCTION STATUS"
echo "═══════════════════════════════════════════════════════════"
echo ""

ssh -o StrictHostKeyChecking=no "$PROD_SERVER" "
    cd $PROD_DIR

    echo '📋 Git Version:'
    git log --oneline -1
    echo ''

    echo '🐳 Docker Containers:'
    docker ps --filter name=pureleven --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
    echo ''

    echo '🧪 API Health:'
    curl -s -o /dev/null -w 'HTTP Status: %{http_code}\n' http://localhost:8000/docs
    echo ''

    echo '📊 Recent Backend Logs (last 10 lines):'
    docker logs pureleven_backend --tail=10 2>&1 | grep -v '^$'
"
echo ""
