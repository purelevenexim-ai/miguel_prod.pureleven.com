#!/bin/bash
set -e

cd /opt/pureleven

echo "🧹 Cleaning local changes..."
git clean -fd backend/app/models/__pycache__
git checkout -- docker-compose.yml 2>/dev/null || true

echo "📥 Pulling latest code..."
git fetch origin
git pull origin main

echo "🔒 Creating backup..."
BACKUP="/tmp/prod_backup_$(date +%F_%H%M%S).dump"
docker-compose -f config/docker-compose.prod.yml exec -T db pg_dump -U pureleven_user pureleven_db -Fc > "$BACKUP"
echo "✅ Backup: $BACKUP"

echo "🐳 Updating containers..."
docker-compose -f config/docker-compose.prod.yml pull
docker-compose -f config/docker-compose.prod.yml up -d --remove-orphans
sleep 10

echo "🔄 Running migrations..."
docker-compose -f config/docker-compose.prod.yml exec -T backend bash -c "cd /app && alembic upgrade head"
echo "✅ Migrations complete"

echo ""
echo "✅ DEPLOYMENT COMPLETE!"
echo ""
docker-compose -f config/docker-compose.prod.yml ps
