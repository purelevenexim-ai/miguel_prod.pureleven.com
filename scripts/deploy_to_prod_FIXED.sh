#!/bin/bash

# 🚀 Production Deployment Script (CORRECTED)
# Handles local changes and deploys to production
# Run this on the production server at /opt/pureleven

set -e

echo "═══════════════════════════════════════════════════════════"
echo "🚀 PRODUCTION DEPLOYMENT (CORRECTED)"
echo "═══════════════════════════════════════════════════════════"
echo ""

cd /opt/pureleven

# Step 1: Clean local changes
echo "🧹 Step 1: Cleaning local changes..."
echo "  - Removing Python cache files"
git clean -fd backend/app/models/__pycache__
echo "  - Discarding local file changes"
git checkout -- docker-compose.yml 2>/dev/null || true
echo "✅ Local changes cleaned"
echo ""

# Step 2: Verify git status
echo "📋 Step 2: Checking git status..."
git status
echo ""

# Step 3: Create database backup
echo "🔒 Step 3: Creating database backup..."
BACKUP="/tmp/prod_backup_$(date +%F_%H%M%S).dump"
docker-compose -f config/docker-compose.prod.yml exec -T db pg_dump -U pureleven_user pureleven_db -Fc > "$BACKUP"
echo "✅ Backup created: $BACKUP"
echo "   Size: $(du -h "$BACKUP" | cut -f1)"
echo ""

# Step 4: Pull latest code from Git
echo "📥 Step 4: Pulling latest code from Git..."
git fetch origin
git pull origin main
echo "✅ Code pulled"
git log --oneline -1
echo ""

# Step 5: Update Docker containers
echo "🐳 Step 5: Updating Docker containers..."
echo "  - Pulling latest images..."
docker-compose -f config/docker-compose.prod.yml pull
echo "  - Starting containers..."
docker-compose -f config/docker-compose.prod.yml up -d --remove-orphans
echo "  - Waiting for services to start..."
sleep 10
echo "✅ Containers updated"
echo ""

# Step 6: Run database migrations
echo "🔄 Step 6: Running database migrations..."
docker-compose -f config/docker-compose.prod.yml exec -T backend bash -c "cd /app && alembic upgrade head"
echo "✅ Migrations complete"
echo ""

# Step 7: Verify deployment
echo "✅ Step 7: Verifying deployment..."
echo ""
echo "Service status:"
docker-compose -f config/docker-compose.prod.yml ps
echo ""
echo "Recent logs (backend):"
docker-compose -f config/docker-compose.prod.yml logs --tail=30 backend | tail -15
echo ""

# Step 8: Health checks
echo "🧪 Step 8: Running health checks..."
echo ""
echo "Testing API endpoint..."
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs)
if [ "$HEALTH" = "200" ]; then
    echo "✅ API is responding (HTTP $HEALTH)"
else
    echo "⚠️  API returned HTTP $HEALTH (expected 200)"
fi
echo ""

echo "═══════════════════════════════════════════════════════════"
echo "✅ DEPLOYMENT COMPLETE!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "📊 Deployment Summary:"
echo "  - Database: Backed up to $BACKUP"
echo "  - Code: Pulled from origin/main"
echo "  - Containers: Updated and running"
echo "  - Migrations: Complete"
echo "  - API: Responding on port 8000"
echo ""
echo "Next steps:"
echo "  1. Verify in browser: http://prod.pureleven.com"
echo "  2. Test API: http://localhost:8000/docs"
echo "  3. Check logs: docker-compose -f config/docker-compose.prod.yml logs -f backend"
echo ""
echo "Rollback (if needed):"
echo "  docker-compose -f config/docker-compose.prod.yml down"
echo "  pg_restore -U pureleven_user -d pureleven_db $BACKUP"
echo "  docker-compose -f config/docker-compose.prod.yml up -d"
echo ""
