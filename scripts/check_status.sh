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
