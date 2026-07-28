#!/bin/bash
# Quick backend restart
echo "🔄 Restarting backend..."
docker restart pureleven_backend 2>/dev/null || \
docker-compose -f config/docker-compose.prod.yml restart backend 2>/dev/null || true
sleep 3
echo "✅ Backend restarted"
docker ps --filter name=pureleven_backend --format "table {{.Names}}\t{{.Status}}"
