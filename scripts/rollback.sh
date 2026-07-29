#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# ROLLBACK PRODUCTION
# Rolls back production to the previous git commit
# Run this on UAT (/opt/miguel) if something breaks
# Usage: bash scripts/rollback.sh
# ═══════════════════════════════════════════════════════════════

set -e

PROD_SERVER="root@172.105.48.142"
PROD_DIR="/opt/pureleven"

echo "═══════════════════════════════════════════════════════════"
echo "⏪ ROLLING BACK PRODUCTION"
echo "═══════════════════════════════════════════════════════════"
echo ""

ssh -o StrictHostKeyChecking=no "$PROD_SERVER" "
    set -e
    cd $PROD_DIR

    echo '📋 Current state:'
    git log --oneline -3
    echo ''

    CURRENT=\$(git rev-parse HEAD)
    PREVIOUS=\$(git rev-parse HEAD~1)

    echo \"Rolling back from \$CURRENT to \$PREVIOUS\"
    echo ''

    # Roll back code
    git reset --hard HEAD~1
    echo '✅ Code rolled back'
    git log --oneline -1

    # Restart backend
    docker-compose -f config/docker-compose.prod.yml restart backend 2>/dev/null || \
    docker restart pureleven_backend
    sleep 5
    docker ps --filter name=pureleven --format 'table {{.Names}}\t{{.Status}}'
    echo ''
    echo '✅ Rollback complete!'
    echo \"Rolled back to: \$(git log --oneline -1)\"
"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ ROLLBACK COMPLETE"
echo "═══════════════════════════════════════════════════════════"
echo ""
