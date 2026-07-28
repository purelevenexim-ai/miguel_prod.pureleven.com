#!/bin/bash

# 🚀 Production Deployment Script
# Pulls latest code from Git main branch and deploys to production
# Usage: bash deploy_to_prod.sh

set -e  # Exit on error

PROD_HOST="172.105.48.142"
PROD_USER="root"
PROD_PATH="/opt/pureleven"
GIT_BRANCH="main"

echo "═══════════════════════════════════════════════════════════"
echo "🚀 PRODUCTION DEPLOYMENT SCRIPT"
echo "═══════════════════════════════════════════════════════════"
echo "Target: $PROD_HOST"
echo "Path: $PROD_PATH"
echo "Branch: $GIT_BRANCH"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Confirm before proceeding
read -p "⚠️  Proceed with production deployment? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "❌ Deployment cancelled"
    exit 0
fi

echo ""
echo "📋 Step 1: Create database backup on production..."
ssh "$PROD_USER@$PROD_HOST" bash -s << 'SSH_SCRIPT'
    set -e
    cd /opt/pureleven
    
    echo "Creating database dump..."
    BACKUP_FILE="/tmp/prod_backup_$(date +%F_%H%M%S).dump"
    docker-compose -f config/docker-compose.prod.yml exec -T db pg_dump -U pureleven_user pureleven_db -Fc > "$BACKUP_FILE"
    
    echo "✅ Backup created: $BACKUP_FILE"
    echo "Backup size: $(du -h $BACKUP_FILE | cut -f1)"
SSH_SCRIPT

echo ""
echo "📦 Step 2: Pull latest code from Git..."
ssh "$PROD_USER@$PROD_HOST" bash -s << 'SSH_SCRIPT'
    set -e
    cd /opt/pureleven
    
    echo "Fetching from origin..."
    git fetch origin
    
    echo "Checking out main branch..."
    git checkout main
    
    echo "Pulling latest changes..."
    git pull origin main
    
    echo "✅ Git pull complete"
    git log --oneline -1
SSH_SCRIPT

echo ""
echo "🐳 Step 3: Update Docker containers..."
ssh "$PROD_USER@$PROD_HOST" bash -s << 'SSH_SCRIPT'
    set -e
    cd /opt/pureleven
    
    echo "Pulling latest Docker images..."
    docker-compose -f config/docker-compose.prod.yml pull
    
    echo "Starting/updating containers..."
    docker-compose -f config/docker-compose.prod.yml up -d --remove-orphans
    
    echo "✅ Containers updated"
    echo ""
    echo "Service status:"
    docker-compose -f config/docker-compose.prod.yml ps
SSH_SCRIPT

echo ""
echo "🔄 Step 4: Run database migrations..."
ssh "$PROD_USER@$PROD_HOST" bash -s << 'SSH_SCRIPT'
    set -e
    cd /opt/pureleven
    
    echo "Waiting for backend to be ready..."
    sleep 5
    
    echo "Running Alembic migrations..."
    docker-compose -f config/docker-compose.prod.yml exec -T backend bash -c "cd /app && alembic upgrade head"
    
    echo "✅ Migrations complete"
SSH_SCRIPT

echo ""
echo "🧪 Step 5: Health checks..."
ssh "$PROD_USER@$PROD_HOST" bash -s << 'SSH_SCRIPT'
    set -e
    cd /opt/pureleven
    
    echo "Checking service health..."
    docker-compose -f config/docker-compose.prod.yml ps
    
    echo ""
    echo "Backend logs (last 50 lines):"
    docker-compose -f config/docker-compose.prod.yml logs --tail=50 backend | tail -20
    
    echo ""
    echo "✅ Health check complete"
SSH_SCRIPT

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ DEPLOYMENT COMPLETE"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "1. Verify production is working: http://prod.pureleven.com"
echo "2. Check API: http://prod.pureleven.com:8000/docs"
echo "3. Test login with credentials"
echo ""
echo "Rollback (if needed):"
echo "  ssh $PROD_USER@$PROD_HOST"
echo "  cd /opt/pureleven"
echo "  docker-compose -f config/docker-compose.prod.yml down"
echo "  pg_restore -U pureleven_user -d pureleven_db /tmp/prod_backup_YYYY-MM-DD_HHMMSS.dump"
echo "  docker-compose -f config/docker-compose.prod.yml up -d"
echo ""
