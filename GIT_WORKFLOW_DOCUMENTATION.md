# Git Workflow Documentation

## Overview

This document explains how Git is used to keep UAT and Production in perfect sync. All changes flow through GitHub (origin/main) as the single source of truth.

---

## Workflow Architecture

```
Your Changes on UAT                    GitHub (origin/main)           Production Server
(Development)                          (Repository)                   (Live)
    ↓                                      ↓                              ↓
┌─────────────────────┐             ┌─────────────────────┐        ┌──────────────────┐
│ /opt/miguel/        │  git add    │ origin/main branch  │        │ /opt/pureleven/  │
│ • Modify files      │  git commit │                     │ git    │ • Contains live  │
│ • Create new code   │  git push   │ • Latest commits    │ pull   │   application    │
│ • Test locally      │      ↓      │ • Contains all code │   ↓    │ • Runs Docker    │
│ • Organize docs     │    Code     │ • Stores history    │  Code  │ • Serves users   │
│                     │    flows    │                     │ flows  │                  │
└─────────────────────┘      →      └─────────────────────┘   →    └──────────────────┘
      UAT ENVIRONMENT                                                  PROD ENVIRONMENT
     (Local Testing)                                                    (Live Users)
```

---

## What Gets Synced

### ✅ Included (Tracked by Git)

- **Code**: All Python, JavaScript, HTML, CSS files
- **Documentation**: Markdown files (.md)
- **Configuration**: docker-compose.yml, config files, nginx configs
- **Scripts**: Bash scripts, deployment automation
- **New Files & Folders**: Any new content you create
- **File Moves**: Properly renamed/moved files (using `git mv`)
- **File Deletions**: Properly deleted files (using `git rm`)

### ❌ Excluded (In .gitignore)

- `__pycache__/` directories
- `*.pyc` compiled Python files
- `.env` files (secrets/passwords)
- `*.log` files
- `venv/` and `node_modules/` directories
- `.DS_Store` and system files

---

## Your Typical Workflow

### Step 1: Make Changes on UAT

Edit files directly on `/opt/miguel` (your development server):

```bash
# Edit a file
vim backend/app/modules/orders/service.py

# Create a new feature
mkdir -p backend/app/modules/invoicing
touch backend/app/modules/invoicing/{__init__.py,router.py,service.py}
```

### Step 2: Test Locally

Verify your changes work on UAT before deploying:

```bash
# Check API responds
curl http://localhost:8000/docs

# Check logs
docker logs miguel_backend --tail 50

# Test feature manually
# Visit http://localhost in browser
```

### Step 3: Stage Changes

Prepare all changes for commit:

```bash
cd /opt/miguel

# Stage ALL changes
git add -A

# Or stage specific files
git add backend/app/modules/orders/service.py
git add backend/app/modules/invoicing/

# Or stage all .md files
git add *.md
```

### Step 4: Commit with Message

Save your work with a descriptive message:

```bash
# Good commit messages (clear, concise)
git commit -m "fix: resolve order status calculation bug"
git commit -m "feat: add invoicing module with API endpoints"
git commit -m "docs: add deployment guide for new team members"
git commit -m "refactor: simplify order service logic"
git commit -m "chore: reorganize configuration files"

# Bad commit messages (vague, unclear)
git commit -m "update"           # ❌ Too vague
git commit -m "fix bug"          # ❌ Which bug?
git commit -m "WIP"              # ❌ Not descriptive
```

### Step 5: Push to GitHub

Send your changes to GitHub (the master repository):

```bash
git push origin main
```

### Step 6: Deploy to Production

Deploy automatically with one command:

```bash
bash scripts/push.sh "fix: resolve order status calculation"
```

Or deploy manually:

```bash
# Your changes are now on GitHub
# Log into production server
ssh root@172.105.48.142
cd /opt/pureleven

# Pull latest code
git pull origin main

# Restart backend to pick up changes
docker restart pureleven_backend
```

---

## Key Git Commands Reference

### Checking Status

```bash
# See what changed
git status

# See changes not yet staged
git diff

# See changes that are staged
git diff --cached

# See local vs GitHub
git log origin/main..HEAD
```

### Staging Files

```bash
# Stage everything (recommended)
git add -A

# Stage specific file
git add path/to/file.py

# Stage specific folder
git add backend/app/modules/

# Stage all markdown files
git add *.md
```

### Committing

```bash
# Commit with message
git commit -m "your message"

# Commit all modified files (skip git add)
git commit -am "your message"
```

### Pushing & Pulling

```bash
# Push to GitHub
git push origin main

# Pull from GitHub
git pull origin main

# Check for updates without pulling
git fetch origin
```

### Viewing History

```bash
# See last 10 commits
git log --oneline -10

# See commits not yet on GitHub
git log origin/main..HEAD

# See what changed in a commit
git show a842ab2

# See differences between versions
git diff origin/main
```

### File Operations (IMPORTANT!)

```bash
# ✅ CORRECT: Move file with git
git mv old_path/file.py new_path/file.py

# ✅ CORRECT: Delete file with git
git rm file_path.py

# ❌ WRONG: Don't do manual operations
mv old_path/file.py new_path/file.py  # Direct move (causes sync issues!)
rm file_path.py                        # Direct delete (causes sync issues!)
```

---

## Deployment Scripts

### push.sh - Complete Deployment

One command that handles everything:

```bash
bash scripts/push.sh "your commit message"
```

What it does:
1. ✅ Stages all changes (`git add -A`)
2. ✅ Commits with your message
3. ✅ Pushes to GitHub (`git push origin main`)
4. ✅ SSHes to production
5. ✅ Pulls latest code (`git pull origin main`)
6. ✅ Restarts backend container
7. ✅ Verifies API is responding

### pull_to_prod.sh - Manual Pull

If you need to pull to production manually:

```bash
# Option 1: Run from UAT
bash scripts/pull_to_prod.sh

# Option 2: Run directly on production
ssh root@172.105.48.142
cd /opt/pureleven
bash scripts/pull_to_prod.sh
```

### prod_status.sh - Check Production

Verify production is synced and healthy:

```bash
bash scripts/prod_status.sh
```

Shows:
- Latest commits in production
- Docker container status
- API health check
- Recent backend logs

### rollback.sh - Undo Last Deploy

If something goes wrong, rollback:

```bash
bash scripts/rollback.sh
```

What it does:
1. Reverts production to previous commit (`git reset --hard HEAD~1`)
2. Restarts backend
3. Verifies services

---

## Real-World Scenarios

### Scenario 1: Fix a Bug

```bash
# 1. Edit the file on UAT
vim backend/app/modules/orders/service.py
# Fix the bug...

# 2. Test locally
curl http://localhost:8000/docs  # Should work

# 3. Stage and push
git add backend/app/modules/orders/service.py
git commit -m "fix: resolve order calculation bug in service.py"
git push origin main

# 4. Deploy to production
bash scripts/push.sh "fix: resolve order calculation bug"

# Done! Fix is live on production
```

### Scenario 2: Add New Feature

```bash
# 1. Create new module
mkdir -p backend/app/modules/invoicing
touch backend/app/modules/invoicing/{__init__.py,router.py,service.py,schemas.py}

# 2. Add code to files
vim backend/app/modules/invoicing/router.py
# Write your endpoints...

# 3. Import in main.py
vim backend/app/main.py
# Add: from app.modules.invoicing.router import router
# Add: app.include_router(router, prefix="/invoicing")

# 4. Test on UAT
# Visit http://localhost:8000/docs
# Test your new endpoints...

# 5. Commit and push
git add backend/app/modules/invoicing/
git add backend/app/main.py
git commit -m "feat: add invoicing module with CRUD endpoints"
git push origin main

# 6. Deploy
bash scripts/push.sh "feat: add invoicing module"

# Production now has your complete new module!
```

### Scenario 3: Reorganize Documentation

```bash
# 1. Move documentation files (use git mv, not manual mv!)
git mv README.md documentation/guides/README.md
git mv SETUP.md documentation/guides/SETUP.md
git mv DEPLOYMENT.md documentation/deployment/DEPLOYMENT.md

# 2. Check what's staged
git status

# 3. Commit
git commit -m "chore: reorganize documentation into folders"
git push origin main

# 4. Deploy
bash scripts/push.sh "chore: reorganize documentation"

# Production will have files in NEW locations only (old locations deleted)
# This is why git mv is essential!
```

### Scenario 4: Sync Production to Latest

If production is behind GitHub:

```bash
ssh root@172.105.48.142
cd /opt/pureleven
bash /opt/pureleven/scripts/pull_to_prod.sh

# Or manually
cd /opt/pureleven
git pull origin main
docker restart pureleven_backend
```

---

## Verification Checklist

### Before Pushing

✅ Check what changed:
```bash
git status
git diff
```

✅ Test on UAT:
```bash
curl http://localhost:8000/docs  # HTTP 200?
docker logs miguel_backend | tail -20  # Any errors?
```

✅ Review commits:
```bash
git log origin/main..HEAD
```

### After Pushing

✅ Verify production got the changes:
```bash
bash scripts/prod_status.sh
```

✅ Check production API:
```bash
curl http://172.105.48.142:8000/docs  # HTTP 200?
```

✅ Verify commit on production:
```bash
ssh root@172.105.48.142 "cd /opt/pureleven && git log --oneline -1"
# Should match your latest commit hash
```

---

## Troubleshooting

### Problem: "Your branch is ahead of 'origin/main'"

**Meaning**: You have uncommitted changes
**Solution**: Push them:
```bash
git push origin main
```

### Problem: "Your branch is behind 'origin/main'"

**Meaning**: GitHub has newer code (someone else pushed)
**Solution**: Pull it:
```bash
git pull origin main
```

### Problem: "Changes not appearing on production"

**Diagnosis**: 
```bash
# Check if you used git mv properly
git log --oneline -1
# Should show your commit

# Check if production pulled
ssh root@172.105.48.142 "cd /opt/pureleven && git log --oneline -1"
# Should match your commit hash

# If commit hashes match but files not there, reset
ssh root@172.105.48.142 "cd /opt/pureleven && git status"
# If shows untracked or modified, do:
ssh root@172.105.48.142 "cd /opt/pureleven && git reset --hard HEAD"
```

### Problem: "SSH connection failed to production"

**Solution**:
```bash
# Check SSH key is set up
ssh -T git@github.com
# Should show: "Hi [username]! You've successfully authenticated..."

# Check you can reach production
ping 172.105.48.142

# Test SSH to production
ssh root@172.105.48.142
```

### Problem: "API not responding after deploy"

**Solution**:
```bash
# Check backend is running
docker ps | grep pureleven_backend

# Check backend logs
docker logs pureleven_backend --tail 50

# Restart backend
docker restart pureleven_backend

# Wait a moment and test
sleep 5
curl http://localhost:8000/docs
```

---

## Important Rules

### ✅ DO

- Use `git mv` for moving/renaming files
- Use `git rm` for deleting files
- Commit frequently with clear messages
- Test on UAT before deploying
- Use `bash scripts/push.sh` for deployments
- Keep .env files out of Git (already in .gitignore)
- Review changes before committing (`git diff`)

### ❌ DON'T

- Use manual `mv` or `rm` commands (creates sync issues)
- Edit files directly on Production (always push from UAT)
- Push without testing on UAT first
- Commit secrets, passwords, or .env files
- Use `git push --force` unless you know exactly what you're doing
- Commit large binary files (videos, images, etc.)

---

## Summary

### The Flow

```
UAT (/opt/miguel)
  ↓ [Make changes, test]
  ↓ [git add, git commit]
  ↓ [git push origin main]
  ↓
GitHub (origin/main)
  ↓ [Central repository]
  ↓
Production (/opt/pureleven)
  ↓ [git pull origin main]
  ↓ [docker restart]
  ↓
LIVE USERS ✅
```

### Your Commands

```bash
# From UAT, deploy everything:
bash scripts/push.sh "your message"

# Check production:
bash scripts/prod_status.sh

# Rollback if needed:
bash scripts/rollback.sh
```

---

## Need Help?

See also:
- `GIT_USAGE_GUIDE.md` - Detailed user guide
- `FILE_ORGANIZATION_COMPLETE.md` - File organization structure
- `DEPLOYMENT_WORKFLOW_GUIDE.md` - Complete deployment procedures
- `scripts/push.sh` - See deployment script
- `scripts/prod_status.sh` - See status check script

---

**Remember**: Git is your safety net. Use it correctly, and you'll never lose code or have sync issues between UAT and Production! ✅
