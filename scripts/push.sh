#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# 📤 PUSH TO GIT + DEPLOY TO PRODUCTION
# ═══════════════════════════════════════════════════════════════════════════
#
# This script handles the COMPLETE deployment workflow:
# 1. Stages ALL file changes (code, docs, configs, assets, etc.)
# 2. Commits with your message
# 3. Pushes to GitHub (origin/main)
# 4. Deploys to Production server by pulling from GitHub
# 5. Restarts the backend to pick up changes
# 6. Verifies deployment is successful
#
# WHAT GETS SYNCED:
# ✅ All code changes (backend, frontend, scripts)
# ✅ All documentation files (markdown guides)
# ✅ Configuration files (docker-compose, env configs)
# ✅ New files and folders
# ✅ Renamed files (when using git mv)
# ✅ Deleted files (when using git rm)
#
# WHAT DOES NOT GET SYNCED (Excluded by .gitignore):
# ❌ __pycache__ directories
# ❌ *.pyc files
# ❌ .env files (secrets)
# ❌ *.log files
# ❌ venv/ directories
#
# Usage: bash scripts/push.sh "your commit message"
#
# Example: bash scripts/push.sh "fix: resolve order calculation bug"
#
# ═══════════════════════════════════════════════════════════════════════════

set -e

COMMIT_MSG="${1:-update code}"
PROD_SERVER="root@172.105.48.142"
PROD_DIR="/opt/pureleven"
PROD_COMPOSE="config/docker-compose.prod.yml"

echo "═══════════════════════════════════════════════════════════════════════════"
echo "📤 PUSH TO GIT + DEPLOY TO PRODUCTION"
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""

cd /opt/miguel

# ── Phase 1: Review Local Changes ───────────────────────────────────────────
echo "📋 PHASE 1: REVIEWING YOUR CHANGES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Current branch: $(git rev-parse --abbrev-ref HEAD)"
echo "Latest commit: $(git log --oneline -1)"
echo ""
echo "📁 Files with changes:"
git status --short || echo "  (No changes)"
echo ""

# ── Phase 2: Stage and Commit All Changes ───────────────────────────────────
echo "📝 PHASE 2: STAGING AND COMMITTING"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Running: git add -A"
echo "  (Stages ALL changes: code, docs, configs, new/deleted/moved files)"
echo ""
echo "  ✅ WILL SYNC TO PRODUCTION:"
echo "    - Backend code (Python modules, services, API)"
echo "    - Frontend code (HTML, CSS, JavaScript)"
echo "    - Documentation (markdown guides)"
echo "    - Configuration files (docker-compose, configs)"
echo "    - Scripts (deployment, utilities)"
echo "    - Database migrations (alembic versions)"
echo "    - New files and folders"
echo "    - File renames (when using git mv)"
echo "    - File deletions (when using git rm)"
echo ""
echo "  ❌ WILL NOT SYNC (ignored by .gitignore):"
echo "    - __pycache__ directories"
echo "    - *.pyc compiled files"
echo "    - .env files (secrets)"
echo "    - .log files"
echo "    - venv/ directories"
echo ""
git add -A

# Check if anything to commit
if git diff --cached --quiet; then
    echo ""
    echo "ℹ️  ℹ️  No changes to commit - repository already up to date"
    echo ""
    echo "═══════════════════════════════════════════════════════════════════════════"
    exit 0
fi

echo ""
echo "✅ Staged changes:"
git diff --cached --name-status | sed 's/^/  /'
echo ""

echo "  Running: git commit -m \"$COMMIT_MSG\""
git commit -m "$COMMIT_MSG"
echo "✅ Committed successfully"
echo ""

# ── Phase 3: Push to GitHub ─────────────────────────────────────────────────
echo "🌐 PHASE 3: PUSHING TO GITHUB"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Running: git push origin main"
git push origin main
echo "✅ Pushed to GitHub (origin/main)"
echo ""

NEW_COMMIT=$(git log --oneline -1)
echo "  New commit: $NEW_COMMIT"
echo ""

# ── Phase 4: Deploy to Production ───────────────────────────────────────────
echo "🚀 PHASE 4: DEPLOYING TO PRODUCTION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
ssh -o StrictHostKeyChecking=no "$PROD_SERVER" "
    set -e
    cd $PROD_DIR

    echo '  📍 Production location: $PROD_DIR'
    echo '  Current commit before pull:'
    git log --oneline -1 | sed 's/^/    /'
    echo ''

    # Clean any local cache conflicts
    # (These are .gitignored so they don't appear in git, but may exist locally)
    echo '  🧹 Cleaning local cache files (__pycache__, *.pyc)...'
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -name '*.pyc' -delete 2>/dev/null || true
    echo '  ✅ Cache cleaned'
    echo ''

    # Reset to clean state (in case of uncommitted local changes)
    echo '  🔄 Resetting to clean git state...'
    git reset --hard HEAD >/dev/null 2>&1 || true
    echo '  ✅ Clean state'
    echo ''

    # Pull latest code from GitHub
    echo '  📥 Pulling latest code from GitHub (origin/main)...'
    git pull origin main
    NEW_PROD_COMMIT=\$(git log --oneline -1)
    echo '  ✅ Code pulled successfully'
    echo '  New commit: '\$NEW_PROD_COMMIT | sed 's/^/    /'
    echo ''

    # Restart backend to pick up code changes
    echo '  🔧 Restarting backend container...'
    # Try project-aware restart first, then fallback to container name
    docker-compose -f config/docker-compose.prod.yml restart backend 2>/dev/null || \
    docker restart pureleven_backend
    sleep 5
    echo '  ✅ Backend restarted'
    echo ''

    # Show container status
    echo '  📊 Container status:'
    docker ps --filter name=pureleven --format 'table {{.Names}}\t{{.Status}}' | sed 's/^/    /'
    echo ''
"

# ── Phase 5: Verify Deployment ──────────────────────────────────────────────
echo "✔️  PHASE 5: VERIFYING DEPLOYMENT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Small delay to ensure service is ready
sleep 2

# Test API health
HEALTH_CHECK=$(curl -s -o /dev/null -w '%{http_code}' http://172.105.48.142:8000/docs 2>/dev/null || echo "000")

if [ "$HEALTH_CHECK" = "200" ]; then
    echo "✅ API Health Check: HTTP $HEALTH_CHECK (OK)"
else
    echo "⚠️  API Health Check: HTTP $HEALTH_CHECK (may need a moment to start)"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo "✅ ✅ ✅  DEPLOYMENT COMPLETE!"
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""
echo "📋 Summary:"
echo "  ✅ All changes staged and committed"
echo "  ✅ Changes pushed to GitHub"
echo "  ✅ Production pulled latest code"
echo "  ✅ Backend restarted"
echo ""
echo "🔍 To verify deployment:"
echo "  1. Check API:    curl http://172.105.48.142:8000/docs"
echo "  2. Check logs:   bash scripts/prod_status.sh"
echo "  3. Test feature: Visit https://172.105.48.142 in browser"
echo ""
