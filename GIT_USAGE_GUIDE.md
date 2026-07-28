#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
# GIT USAGE GUIDE FOR UAT ↔ PRODUCTION DEPLOYMENT
# ═══════════════════════════════════════════════════════════════════════════
#
# This guide explains how to use Git to keep UAT and Production perfectly
# in sync. All changes made in UAT will be automatically reflected in
# Production with proper Git commands.
#
# ═══════════════════════════════════════════════════════════════════════════

cat << 'EOF'

╔═══════════════════════════════════════════════════════════════════════════╗
║                    GIT USAGE GUIDE FOR DEVELOPERS                         ║
║            UAT ↔ Git ↔ Production Deployment Workflow                    ║
╚═══════════════════════════════════════════════════════════════════════════╝

═══════════════════════════════════════════════════════════════════════════════
1. UNDERSTANDING THE WORKFLOW
═══════════════════════════════════════════════════════════════════════════════

Your deployment flow:

    UAT (/opt/miguel)
         ↓ [Make changes]
         ↓ [Test locally]
         ↓ [git add, commit, push]
         ↓
    GitHub (origin/main)
         ↓ [Contains latest code]
         ↓
    Production (/opt/pureleven)
         ↓ [git pull from origin/main]
         ↓ [Docker restart]
    LIVE ✅

Key principle: Everything goes through Git. No manual file operations.

═══════════════════════════════════════════════════════════════════════════════
2. INITIAL SETUP (Already Done)
═══════════════════════════════════════════════════════════════════════════════

Your Git is already configured with:

✅ Repository: https://github.com/purelevenexim-ai/crm
✅ Branch: main (single source of truth)
✅ SSH key auth: Passwordless push/pull
✅ .gitignore: Excludes cache files (.pyc, __pycache__, .env, etc.)

Check your current state:

    cd /opt/miguel
    git remote -v
    # Should show: origin  https://github.com/purelevenexim-ai/crm (fetch)

═══════════════════════════════════════════════════════════════════════════════
3. COMMON GIT OPERATIONS
═══════════════════════════════════════════════════════════════════════════════

SCENARIO 1: You made code changes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Changes you can make:
  • Edit existing files (backend/app/modules/*/service.py)
  • Create new files (backend/app/modules/new_feature/*)
  • Delete files (use git rm)
  • Move/rename files (use git mv - IMPORTANT!)

Step 1: Check what changed
    git status
    # Shows modified, new, and deleted files

Step 2: Stage changes (add to commit)
    git add -A                 # Add ALL changes
    # OR
    git add backend/app/modules/orders/service.py  # Add specific file
    # OR
    git add *.md               # Add all .md files

Step 3: Review staged changes before committing
    git diff --cached          # Shows what will be committed

Step 4: Commit with a meaningful message
    git commit -m "fix: resolve order status calculation bug"
    
    Commit message format:
    • fix: ...          (Bug fixes)
    • feat: ...         (New features)
    • docs: ...         (Documentation)
    • refactor: ...     (Code refactoring)
    • chore: ...        (File organization, cleanup)
    • test: ...         (Tests)

Step 5: Push to GitHub
    git push origin main
    # Output: Shows commits sent to GitHub

Step 6: Deploy to production
    bash scripts/push.sh "your message"  # All-in-one
    # OR manually:
    ssh root@172.105.48.142
    cd /opt/pureleven
    git pull origin main
    docker restart pureleven_backend


SCENARIO 2: You moved/renamed a file
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ WRONG: Use manual mv command
    mv old_location/file.py new_location/file.py
    git add -A
    git commit -m "move file"
    # Problem: Production may have BOTH old and new locations!

✅ CORRECT: Use git mv command
    git mv old_location/file.py new_location/file.py
    git add -A
    git commit -m "chore: move file to new location"
    git push origin main
    # Result: Production will have file in NEW location only


SCENARIO 3: You created a new folder with files
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    mkdir -p backend/app/modules/new_feature
    touch backend/app/modules/new_feature/__init__.py
    touch backend/app/modules/new_feature/service.py
    # ... Add your code ...
    git add backend/app/modules/new_feature/
    git commit -m "feat: add new feature module"
    git push origin main
    # Production will automatically have the new folder


SCENARIO 4: You deleted a file
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ WRONG: Use manual rm command
    rm backend/app/modules/old_feature/service.py
    git add -A
    git commit -m "delete file"
    # Production might not reflect the deletion

✅ CORRECT: Use git rm command
    git rm backend/app/modules/old_feature/service.py
    git add -A  # Usually not needed after git rm, but safe to include
    git commit -m "feat: remove deprecated module"
    git push origin main
    # Production will NOT have this file after git pull


═══════════════════════════════════════════════════════════════════════════════
4. VIEWING HISTORY
═══════════════════════════════════════════════════════════════════════════════

See recent commits:
    git log --oneline -10
    # Output: Shows last 10 commits with hashes and messages
    
    a842ab2 docs: add file organization completion summary
    1bb61d3 chore(docs): move all remaining root files to organized folders
    9bed3c2 docs: add comprehensive pull-to-prod guide with all options
    ... and so on

See what changed in a specific commit:
    git show a842ab2
    # Shows the changes made in that commit

See changes between UAT and Production:
    ssh root@172.105.48.142 "git log --oneline -1"
    git log --oneline -1
    # Both should show the same commit hash if in sync

See detailed changes (diff):
    git diff                    # Show changes not yet staged
    git diff --cached           # Show staged changes
    git diff origin/main        # Show local changes vs GitHub

═══════════════════════════════════════════════════════════════════════════════
5. SYNCING WITH GITHUB
═══════════════════════════════════════════════════════════════════════════════

Check if you're behind GitHub:
    git fetch origin
    git status
    # Output: "Your branch is X commits behind" or "Your branch is ahead"

Pull latest from GitHub (if someone else pushed):
    git fetch origin
    git pull origin main
    # Brings in changes from GitHub to your local UAT

Push your changes to GitHub:
    git push origin main
    # Sends your commits to GitHub

═══════════════════════════════════════════════════════════════════════════════
6. BEFORE YOU PUSH - CHECKLIST
═══════════════════════════════════════════════════════════════════════════════

Always verify before pushing to production:

Step 1: See what you're pushing
    git log origin/main..HEAD
    # Shows commits that will be pushed

Step 2: See what files will change
    git diff origin/main
    # Shows all file changes (green = new/added, red = removed)

Step 3: Verify locally (test on UAT)
    # Run API tests, check browser, verify logs
    curl http://localhost:8000/docs  # Should return 200

Step 4: Check status one more time
    git status
    # Should show: "On branch main" and "nothing to commit, working tree clean"

Step 5: Push with confidence
    bash scripts/push.sh "your message"

═══════════════════════════════════════════════════════════════════════════════
7. PUSHING TO PRODUCTION
═══════════════════════════════════════════════════════════════════════════════

AUTOMATED WAY (Recommended):
    From UAT (/opt/miguel):
    
    bash scripts/push.sh "fix: resolve order status bug"
    
    This does:
    ✅ git add -A
    ✅ git commit -m "..."
    ✅ git push origin main
    ✅ SSH to production
    ✅ git pull origin main
    ✅ docker restart backend
    ✅ Verify services are running

MANUAL WAY (If you need control):
    From UAT (/opt/miguel):
    
    # 1. Commit and push
    git add -A
    git commit -m "your message"
    git push origin main
    
    # 2. SSH to production
    ssh root@172.105.48.142
    cd /opt/pureleven
    
    # 3. Pull changes
    git pull origin main
    
    # 4. Restart backend (to pick up code changes)
    docker restart pureleven_backend
    
    # 5. Verify
    docker logs pureleven_backend | tail -20
    curl http://localhost:8000/docs  # Should be 200

═══════════════════════════════════════════════════════════════════════════════
8. PULLING FROM PRODUCTION
═══════════════════════════════════════════════════════════════════════════════

If you want to pull latest code to UAT:
    From UAT (/opt/miguel):
    
    git fetch origin
    git pull origin main
    
    Then restart UAT backend (if needed):
    docker restart miguel_backend

═══════════════════════════════════════════════════════════════════════════════
9. TROUBLESHOOTING
═══════════════════════════════════════════════════════════════════════════════

PROBLEM: "Your branch is ahead of 'origin/main' by X commits"
SOLUTION: You have unpushed commits. Push them:
    git push origin main

PROBLEM: "Your branch is behind 'origin/main'"
SOLUTION: GitHub has newer code. Pull it:
    git pull origin main

PROBLEM: "fatal: Could not read from remote repository"
SOLUTION: SSH key issue. Check:
    ssh -T git@github.com
    # Should say: "Hi [username]! You've successfully authenticated..."

PROBLEM: "Changes not appearing on Production after git pull"
SOLUTION: Check if you used git mv properly:
    # View what was pulled
    ssh root@172.105.48.142 "cd /opt/pureleven && git log --oneline -1"
    # Should match your latest commit hash
    
    # If git log matches but files not there:
    ssh root@172.105.48.142 "cd /opt/pureleven && git status"
    # If it shows "not updated" files, do: git reset --hard HEAD

PROBLEM: "git status shows untracked files cluttering output"
SOLUTION: Check .gitignore is set up. Should exclude:
    __pycache__/
    *.pyc
    .env
    *.log
    node_modules/
    .venv/

═══════════════════════════════════════════════════════════════════════════════
10. IMPORTANT RULES
═══════════════════════════════════════════════════════════════════════════════

✅ DO:
  • Use git mv for moving/renaming files
  • Use git rm for deleting files
  • Commit frequently with clear messages
  • Pull before starting work (git pull origin main)
  • Test changes on UAT before pushing
  • Include meaningful commit messages (not "update", "fix bug", etc.)
  • Keep .env files out of Git (they're in .gitignore)

❌ DON'T:
  • Use manual mv/rm commands for file operations
  • Push without testing on UAT first
  • Commit node_modules, __pycache__, or .env files
  • Force push (git push --force) unless you know what you're doing
  • Commit large binary files (images, videos, etc.)
  • Edit files directly on Production (always push from UAT)

═══════════════════════════════════════════════════════════════════════════════
11. YOUR COMMANDS CHEAT SHEET
═══════════════════════════════════════════════════════════════════════════════

From UAT (/opt/miguel):

Deploy to production:
    bash scripts/push.sh "your message"

Check production status:
    bash scripts/prod_status.sh

Rollback production:
    bash scripts/rollback.sh

Manual git operations:
    git status                          # See what changed
    git add -A                          # Stage all changes
    git commit -m "message"             # Commit with message
    git push origin main                # Push to GitHub
    git log --oneline -5                # See recent commits
    git mv old_path new_path            # Move file properly
    git rm file_path                    # Delete file properly
    git pull origin main                # Pull from GitHub

═══════════════════════════════════════════════════════════════════════════════
12. REAL WORLD EXAMPLE
═══════════════════════════════════════════════════════════════════════════════

Scenario: Fix a bug in orders and deploy to production

Step 1: Edit file on UAT
    vim backend/app/modules/orders/service.py
    # Fix the bug, save

Step 2: Test locally
    curl http://localhost:8000/docs  # Verify API still works

Step 3: Stage and commit
    git add backend/app/modules/orders/service.py
    git commit -m "fix: resolve order status calculation in service.py"

Step 4: Deploy to production (one command!)
    bash scripts/push.sh "fix: resolve order status calculation"

Step 5: Verify production
    bash scripts/prod_status.sh
    # Should show:
    # - Latest git commit
    # - All containers "Up"
    # - API HTTP 200 ✅

DONE! Your fix is now live on production.

═══════════════════════════════════════════════════════════════════════════════
13. ADDING NEW FEATURES
═══════════════════════════════════════════════════════════════════════════════

Example: Create a new API endpoint

Step 1: Create new module
    mkdir -p backend/app/modules/invoicing
    touch backend/app/modules/invoicing/__init__.py
    touch backend/app/modules/invoicing/router.py
    touch backend/app/modules/invoicing/service.py
    touch backend/app/modules/invoicing/schemas.py

Step 2: Add code to files
    vim backend/app/modules/invoicing/router.py
    # Add your endpoint code

Step 3: Import in main.py
    vim backend/app/main.py
    # Add: from app.modules.invoicing.router import router as invoicing_router
    # Add: app.include_router(invoicing_router)

Step 4: Stage entire module
    git add backend/app/modules/invoicing/

Step 5: Commit
    git commit -m "feat: add invoicing module with basic endpoints"

Step 6: Deploy
    bash scripts/push.sh "feat: add invoicing module"

Production will now have the complete new module!

═══════════════════════════════════════════════════════════════════════════════

For more help, see:
  • FILE_ORGANIZATION_COMPLETE.md    - File organization guide
  • DEPLOYMENT_WORKFLOW_GUIDE.md     - Deployment procedures
  • HOW_TO_PULL_TO_PROD.md           - Pull to production guide
  • scripts/push.sh                  - Deploy script
  • scripts/rollback.sh              - Rollback script
  • scripts/prod_status.sh           - Status check script

═══════════════════════════════════════════════════════════════════════════════
END OF GUIDE
═══════════════════════════════════════════════════════════════════════════════

EOF
