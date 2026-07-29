#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# COMPLETE DEPLOYMENT & WORKFLOW GUIDE
# ═══════════════════════════════════════════════════════════════════════════
# 
# This document covers:
# 1. Your complete git workflow (UAT → Git → Production)
# 2. Exact commands for daily development
# 3. Troubleshooting & rollback procedures
# 4. Production access & monitoring
# ═══════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1: ENVIRONMENT OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════

# UAT Server (Development):
#   Location:   /opt/miguel (on UAT machine)
#   Type:       FastAPI + PostgreSQL + Nginx
#   Access:     Local (you are here)
#   Database:   miguel_db / miguel_user
#   API Port:   8000
#   Git Branch: main (synced with origin)

# Production Server (Live):
#   Location:   /opt/pureleven (on 172.105.48.142)
#   Type:       FastAPI + PostgreSQL + Nginx (same as UAT)
#   Access:     SSH (passwordless key auth)
#   Database:   pureleven_db / pureleven_user
#   API Port:   8000
#   Git Branch: main (always synced with UAT via origin)

# GitHub Repository:
#   Repo:       purelevenexim-ai/crm
#   URL:        https://github.com/purelevenexim-ai/crm
#   Branch:     main (single source of truth)
#   Push Key:   SSH (from UAT machine)

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2: YOUR DAILY WORKFLOW
# ═══════════════════════════════════════════════════════════════════════════

# STEP 1: Make code changes on UAT (/opt/miguel)
# 
# Example: Fix a bug in backend/app/modules/orders/service.py
#   - Edit the file
#   - Test locally on UAT (API should respond)
#   - Verify in browser or with curl

# STEP 2: Push to production with ONE command
# 
#   FROM UAT MACHINE (/opt/miguel):
cd /opt/miguel
bash scripts/push.sh "fix: resolve order status calculation bug"

# What this does:
#   ✅ Stages all changes (git add -A)
#   ✅ Commits with your message
#   ✅ Pushes to origin/main
#   ✅ SSHes to production
#   ✅ Pulls latest code
#   ✅ Restarts backend container
#   ✅ Verifies services are running

# STEP 3: Verify production is updated
# 
#   FROM UAT MACHINE:
bash scripts/prod_status.sh

# This shows:
#   📋 Latest git commit on production
#   🐳 Docker container status (all should be "Up")
#   🧪 API health check (should return HTTP 200)
#   📊 Recent backend logs (check for errors)

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3: ROLLBACK (If something breaks)
# ═══════════════════════════════════════════════════════════════════════════

# If your latest push breaks production, rollback with:
#
#   FROM UAT MACHINE (/opt/miguel):
bash scripts/rollback.sh

# What this does:
#   ⏪ Rolls production back to previous git commit
#   🔄 Restarts backend container
#   ✅ Verifies services are running

# Then check status:
bash scripts/prod_status.sh

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4: MANUAL SSH ACCESS (if you need to)
# ═══════════════════════════════════════════════════════════════════════════

# SSH to production (no password needed):
ssh root@172.105.48.142

# Once connected, useful commands:
cd /opt/pureleven

# Check git status
git status
git log --oneline -5

# View containers
docker ps

# Restart backend manually
docker restart pureleven_backend

# View logs in real-time
docker logs -f pureleven_backend

# Database access (if needed)
docker exec -it pureleven_db psql -U pureleven_user -d pureleven_db

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5: GIT WORKFLOW DETAILS
# ═══════════════════════════════════════════════════════════════════════════

# Current git setup:
#   - UAT and Production both track origin/main
#   - No database schema migrations in this workflow (code-only changes)
#   - Cache files (.pyc, __pycache__) are .gitignore'd (no conflicts)
#   - SSH keys configured for passwordless production access

# To manually push (without using push.sh):
cd /opt/miguel
git add -A
git commit -m "your message"
git push origin main
# Then manually SSH to prod and do: git pull origin main && docker restart pureleven_backend

# To manually check production status:
ssh root@172.105.48.142 "cd /opt/pureleven && git log --oneline -1 && docker ps"

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 6: TROUBLESHOOTING
# ═══════════════════════════════════════════════════════════════════════════

# Problem: push.sh says "No changes to commit"
# Solution: This means there are no staged changes. It's not an error—just verify
#           with `git status` that your changes were saved.

# Problem: Backend doesn't restart after push
# Solution: Check if there's a syntax error:
#           docker logs pureleven_backend | tail -50
#           If error, fix on UAT and push again.

# Problem: API returns 500 error on production
# Solution: Check backend logs for stack traces:
#           ssh root@172.105.48.142
#           docker logs pureleven_backend | tail -100

# Problem: Database connection error
# Solution: Database usually doesn't need restart, but if you do:
#           docker restart pureleven_db
#           Then restart backend:
#           docker restart pureleven_backend

# Problem: Want to see git diff between UAT and production
# Solution: From UAT, check what's ahead:
#           git log --oneline -10 origin/main..HEAD
#           If empty, they're in sync.

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 7: IMPORTANT NOTES
# ═══════════════════════════════════════════════════════════════════════════

# ⚠️  Database: Only code changes are deployed. Database schema changes (migrations)
#     are not included in this workflow. If you add new fields to models:
#     1. Create alembic migration: alembic revision --autogenerate -m "your msg"
#     2. Commit the migration file to git
#     3. Push with push.sh (migrations auto-run on container restart)

# ⚠️  Cache files: Never commit __pycache__ or .pyc files. They're in .gitignore.
#     If they're accidentally committed, they'll be removed in the next git cleanup.

# ⚠️  Secrets: .env files are NOT committed. Production has its own .env file
#     that contains passwords and API keys. Keep it safe!

# ⚠️  Rollback limit: You can only rollback to commits that exist in git history.
#     rollback.sh goes back one commit. For earlier rollbacks, use git directly:
#     ssh root@172.105.48.142
#     cd /opt/pureleven
#     git reset --hard <commit-hash>
#     docker restart pureleven_backend

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 8: QUICK REFERENCE CHEAT SHEET
# ═══════════════════════════════════════════════════════════════════════════

# From UAT machine (/opt/miguel):

# Deploy code to production:
bash scripts/push.sh "your commit message"

# Check production status:
bash scripts/prod_status.sh

# Rollback production:
bash scripts/rollback.sh

# SSH to production:
ssh root@172.105.48.142

# View git log (UAT):
git log --oneline -10

# View git log (Production):
ssh root@172.105.48.142 "git log --oneline -10"

# Verify UAT and Prod are in sync:
bash scripts/prod_status.sh  # Check git version
git log --oneline -1        # Should match

# ═══════════════════════════════════════════════════════════════════════════
# END OF GUIDE
# ═══════════════════════════════════════════════════════════════════════════
