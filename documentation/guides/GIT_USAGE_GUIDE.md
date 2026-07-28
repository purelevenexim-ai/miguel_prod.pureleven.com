# 🔧 Complete Git Usage Guide for UAT & Production Deployment

**Last Updated:** February 27, 2026  
**Environment:** PureLeven CRM - UAT (/opt/miguel) & Production (172.105.48.142:/opt/pureleven)

---

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Understanding Git in This Environment](#understanding-git-in-this-environment)
3. [Daily Workflow](#daily-workflow)
4. [File Synchronization Explained](#file-synchronization-explained)
5. [Common Git Commands](#common-git-commands)
6. [Push & Pull Scripts Reference](#push--pull-scripts-reference)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)

---

## 🚀 Quick Start

### Deploy Changes to Production (One Command)

```bash
# From UAT (/opt/miguel)
bash scripts/push.sh "your commit message here"
```

That's it! This command will:
- ✅ Stage ALL your changes (code, docs, configs, files, etc.)
- ✅ Commit to Git with your message
- ✅ Push to GitHub (origin/main)
- ✅ Deploy to Production via SSH
- ✅ Restart backend services
- ✅ Verify deployment success

### Check Production Health

```bash
bash scripts/prod_status.sh
```

This shows:
- Production git commit status
- Running Docker containers
- API health check (HTTP 200 if working)
- Recent logs

### Manually Pull on Production

```bash
# Option 1: Run from UAT
bash scripts/pull_to_prod.sh

# Option 2: SSH to production and run there
ssh root@172.105.48.142
cd /opt/pureleven
bash scripts/pull_to_prod.sh
```

---

## 🌍 Understanding Git in This Environment

### Repository Structure

```
GitHub (purelevenexim-ai/crm)
    ↑
    └─── Origin/Main (Single Source of Truth)
         ↓
    UAT (/opt/miguel) ←→ Production (172.105.48.142)
```

### How Synchronization Works

**With `push.sh`:**
```
UAT Changes → git add -A → git commit → git push origin/main
                                              ↓
                                    GitHub Updates
                                              ↓
                                    SSH to Production
                                              ↓
                                    git pull origin/main
                                              ↓
                                    docker restart backend
                                              ↓
                                    Production Updated ✅
```

**Manual pull on Production:**
```
Production → git pull origin/main → Get latest GitHub code → Update files
```

### What Gets Synchronized

#### ✅ Files THAT SYNC

| Type | Example | Notes |
|------|---------|-------|
| **Backend Code** | `backend/app/modules/*/service.py` | Python files, entire modules |
| **Frontend Code** | `frontend/modules/*.html`, `frontend/styles/*.css` | HTML, CSS, JS |
| **Scripts** | `scripts/*.sh`, `scripts/*.py` | Deployment and utility scripts |
| **Documentation** | `docs/`, `documentation/` | All markdown guides |
| **Configuration** | `config/docker-compose.yml` | Docker Compose configs |
| **Database** | `backend/alembic/versions/` | Migration files |
| **New Files** | Any new file you create | Automatically included |
| **Renamed Files** | Files moved with `git mv` | Proper git tracking |
| **Deleted Files** | Files removed with `git rm` | Properly tracked |

#### ❌ Files THAT DON'T SYNC (Ignored by .gitignore)

| Type | Example | Why |
|------|---------|-----|
| **Python Cache** | `__pycache__/`, `*.pyc` | Auto-generated, waste space |
| **Virtual Environments** | `venv/`, `.venv/` | Large, environment-specific |
| **Environment Variables** | `.env`, `.env.local` | Contains secrets, not shared |
| **Log Files** | `*.log`, `app.log` | Temporary, large |
| **OS Files** | `.DS_Store`, `Thumbs.db` | OS-specific, not needed |
| **IDE Cache** | `.vscode/`, `.idea/` | Editor-specific settings |

---

## 📊 Daily Workflow

### Scenario 1: Making Code Changes

```bash
# 1. Make your changes in UAT
vim backend/app/modules/orders/service.py
vim frontend/orders.html

# 2. Test your changes locally
# (Run your app, test in browser, etc.)

# 3. Deploy to production (one command)
bash scripts/push.sh "feat: add new order status calculation"

# 4. Verify production updated
bash scripts/prod_status.sh
```

### Scenario 2: Adding New Files/Documentation

```bash
# 1. Create new files in UAT
mkdir -p documentation/new-feature
touch documentation/new-feature/README.md
echo "Documentation here" > documentation/new-feature/README.md

# 2. Deploy
bash scripts/push.sh "docs: add new feature documentation"

# 3. Check production has the new files
ssh root@172.105.48.142 "ls -la /opt/pureleven/documentation/new-feature/"
```

### Scenario 3: Renaming/Moving Files

```bash
# ✅ CORRECT: Use git mv (ensures proper sync)
git mv backend/old_location/file.py backend/new_location/file.py
git mv documentation/old_guide.md documentation/guides/old_guide.md

# ❌ WRONG: Don't use manual mv (won't sync properly)
# mv backend/old_location/file.py backend/new_location/file.py

# Then deploy
bash scripts/push.sh "refactor: reorganize backend modules"
```

### Scenario 4: Deleting Files

```bash
# ✅ CORRECT: Use git rm
git rm backend/deprecated_module.py
git rm documentation/outdated_guide.md

# Then deploy
bash scripts/push.sh "refactor: remove deprecated code"
```

---

## 📁 File Synchronization Explained

### Real Example: The File Organization Sync

**What Happened:**
1. In UAT, we organized 5 root-level files into folders
2. Used `git mv` to move them properly
3. Committed and pushed to GitHub
4. Production pulled changes
5. All 5 files appeared in correct folders on Production

**Why It Worked:**
```bash
# In UAT
git mv README_MAIN.md documentation/guides/README_MAIN.md
git mv HOW_TO_PULL_TO_PROD.md documentation/deployment/HOW_TO_PULL_TO_PROD.md
# (etc for all 5 files)

git commit -m "chore: reorganize root files"
git push origin/main
# GitHub now knows: "These files moved to new locations"

# In Production (automatic via push.sh)
git pull origin/main
# Git applies the moves: Old locations deleted, new locations created
# Result: Files appear in correct folders ✅
```

**If We Had Used Manual `mv`:**
```bash
# WRONG (don't do this)
mv README_MAIN.md documentation/guides/README_MAIN.md

# Git sees: "New file appeared in docs/guides, old file disappeared"
# When Production pulls: Confusion about whether to rename or recreate
# Result: Files in BOTH old and new locations, or sync errors ❌
```

**Key Rule:** Always use `git mv` for file moves, never manual `mv`

---

## 🔧 Common Git Commands

### Check Status

```bash
# See what changed
git status

# See detailed changes in each file
git diff

# See what's staged to commit
git diff --cached
```

### Stage Changes

```bash
# Stage all changes (recommended for push.sh)
git add -A

# Stage specific file
git add backend/app/modules/orders/service.py

# Stage all files in a folder
git add documentation/
```

### Commit Changes

```bash
# Commit with message
git commit -m "feat: add new order status"

# Change last commit message (before pushing)
git commit --amend -m "new message"
```

### Push to GitHub

```bash
# Push to main branch
git push origin main

# Push with all tags
git push origin --tags
```

### Pull from GitHub

```bash
# Pull latest changes
git pull origin main

# See what would change before pulling
git fetch origin
git diff main origin/main
```

### View History

```bash
# View recent commits
git log --oneline -10

# View commits with file changes
git log --oneline --stat

# View specific commit
git show abc1234
```

### Undo Changes

```bash
# Undo unstaged changes to a file
git checkout -- filename

# Unstage a file
git reset HEAD filename

# Go back one commit (keep changes)
git reset --soft HEAD~1

# Go back one commit (discard changes)
git reset --hard HEAD~1
```

### Create Feature Branches (Optional)

```bash
# Create new branch for feature
git checkout -b feature/new-orders-ui

# Make changes...

# Merge back to main
git checkout main
git merge feature/new-orders-ui

# Delete branch
git branch -d feature/new-orders-ui
```

---

## 📤📥 Push & Pull Scripts Reference

### push.sh - Deploy Everything to Production

**Location:** `/opt/miguel/scripts/push.sh`

**What It Does:**
1. Reviews all your changes locally
2. Stages all files (`git add -A`)
3. Commits with your message
4. Pushes to GitHub
5. SSHes to Production
6. Pulls latest from GitHub
7. Restarts Docker backend
8. Verifies deployment

**Usage:**
```bash
bash scripts/push.sh "your commit message"
```

**Examples:**
```bash
bash scripts/push.sh "fix: resolve order calculation bug"
bash scripts/push.sh "feat: add customer report feature"
bash scripts/push.sh "docs: update deployment guide"
bash scripts/push.sh "refactor: reorganize backend modules"
```

**Output Shows:**
```
═════════════════════════════════════════════════════════════
📤 PUSH TO GIT + DEPLOY TO PRODUCTION
═════════════════════════════════════════════════════════════

📋 PHASE 1: REVIEWING YOUR CHANGES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[shows files changed, additions, deletions]

📤 PHASE 2: PUSHING TO GITHUB
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Commit abc1234 pushed to GitHub

🚀 PHASE 3: DEPLOYING TO PRODUCTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Production pulled latest code
✅ Backend restarted
✅ Deployment verified

🎉 SUCCESS! Production is now running your changes
```

### pull_to_prod.sh - Manual Pull on Production

**Location:** `/opt/miguel/scripts/pull_to_prod.sh` (UAT) and `/opt/pureleven/scripts/pull-to-prod.sh` (Prod)

**What It Does:**
1. Shows current state on Production
2. Cleans cache files
3. Pulls latest from GitHub
4. Shows what changed
5. Restarts backend if needed

**Usage:**

```bash
# Option 1: Run from UAT (auto-SSHes to Production)
bash scripts/pull_to_prod.sh

# Option 2: SSH to Production manually
ssh root@172.105.48.142

# Then run on Production
cd /opt/pureleven
bash scripts/pull-to-prod.sh
```

### prod_status.sh - Check Production Health

**Location:** `/opt/miguel/scripts/prod_status.sh`

**What It Does:**
1. Shows git commit history
2. Shows running Docker containers
3. Tests API health (HTTP 200)
4. Shows recent backend logs

**Usage:**
```bash
bash scripts/prod_status.sh
```

**Output Example:**
```
═════════════════════════════════════════════════════════════
🔍 PRODUCTION STATUS CHECK
═════════════════════════════════════════════════════════════

📊 Git Status:
Commit: abc1234 feat: add customer reports
Branch: main

🐳 Docker Containers:
pureleven_frontend: Up 10 hours
pureleven_backend: Up 15 minutes
pureleven_db: Up 11 hours

🏥 API Health:
HTTP Status: 200 ✅

📜 Recent Logs:
[last 20 lines of backend logs]
```

---

## 🆘 Troubleshooting

### Problem: "Changes not reflected on Production after push.sh"

**Possible Causes:**

1. **Files moved with `mv` instead of `git mv`**
   ```bash
   # Check git status
   git status
   # If you see both old and new locations, you used manual mv
   
   # Fix: Use git mv
   git mv old_location/file new_location/file
   git commit -m "fix: proper file move using git mv"
   git push
   ```

2. **Files in .gitignore**
   ```bash
   # Check .gitignore
   cat .gitignore
   
   # If your file is listed, either:
   # - Remove from .gitignore if it should be tracked
   # - Accept it won't sync (like .env files)
   ```

3. **Commit not pushed to GitHub**
   ```bash
   # Check local vs GitHub
   git log --oneline -5
   # Compare with: https://github.com/purelevenexim-ai/crm
   
   # If different, push again
   git push origin main
   ```

### Problem: "Git merge conflicts"

```bash
# See conflicting files
git status | grep 'both modified'

# Edit conflicting file
vim backend/app/modules/orders/service.py

# Look for markers:
# <<<<<<< HEAD (your changes)
# your code
# =======
# incoming code
# >>>>>>> branch-name

# Fix conflicts, keep what you need
git add backend/app/modules/orders/service.py

# Complete the merge
git commit -m "fix: resolve merge conflicts"
git push origin main
```

### Problem: "Need to undo a commit"

```bash
# View recent commits
git log --oneline -5

# Undo last commit (keep changes)
git reset --soft HEAD~1

# Fix and re-commit
git add .
git commit -m "corrected message"
git push origin main

# OR: Undo last commit (discard changes)
git reset --hard HEAD~1
# WARNING: This deletes your changes! Only do this if you're sure.
```

### Problem: "Can't SSH to Production"

```bash
# Check SSH key exists
ls ~/.ssh/id_rsa

# Test SSH connection
ssh -v root@172.105.48.142

# If fails, check SSH config in UAT
cat ~/.ssh/config
# Should have entry for 172.105.48.142

# Generate key if needed
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa
```

---

## ✅ Best Practices

### ✅ DO

| ✅ DO | Example |
|------|---------|
| **Use git mv for file moves** | `git mv old_path new_path` |
| **Use git rm for deletions** | `git rm obsolete_file.py` |
| **Commit frequently** | Commit after each feature/fix |
| **Write descriptive messages** | `feat: add customer report feature` |
| **Use one command to deploy** | `bash scripts/push.sh "message"` |
| **Check status before pushing** | `git status` then `git diff` |
| **Verify production after deploy** | `bash scripts/prod_status.sh` |
| **Pull before starting work** | `git pull origin main` |

### ❌ DON'T

| ❌ DON'T | Why |
|---------|-----|
| **Use `mv` for file moves** | Git won't track it properly, sync breaks |
| **Commit secrets (.env files)** | Security risk, secrets exposed |
| **Force push (`git push -f`)** | Overwrites others' work |
| **Ignore merge conflicts** | Will break on push |
| **Commit large binary files** | Slows down entire repo |
| **Edit files on Production directly** | Changes won't be in Git, lost when pulled |
| **Use unclear commit messages** | Future you won't understand it |
| **Deploy without testing** | Bugs go to production |

### Commit Message Format

```
Format: <type>: <description>

Types:
  feat:    New feature
  fix:     Bug fix
  docs:    Documentation changes
  refactor: Code reorganization
  perf:    Performance improvement
  chore:   Maintenance tasks

Examples:
  feat: add customer report feature
  fix: resolve order calculation bug
  docs: update deployment guide
  refactor: reorganize backend modules
  chore: remove deprecated code
```

---

## 🔍 Verification Checklist

After each deployment, verify:

```bash
# 1. Check git log shows your commit
git log --oneline -1

# 2. Check production pulled the change
bash scripts/prod_status.sh

# 3. Check containers running
bash scripts/prod_status.sh | grep "pureleven_"

# 4. Check API responds
bash scripts/prod_status.sh | grep "HTTP Status"

# 5. Visually verify in browser
# Navigate to your production app and test functionality
```

---

## 📚 Related Documentation

- **[FILE_ORGANIZATION_COMPLETE.md](FILE_ORGANIZATION_COMPLETE.md)** - How files are organized
- **[DEPLOYMENT_WORKFLOW_GUIDE.md](../deployment/DEPLOYMENT_WORKFLOW_GUIDE.md)** - Full deployment workflow
- **[HOW_TO_PULL_TO_PROD.md](../deployment/HOW_TO_PULL_TO_PROD.md)** - Pull-to-prod options

---

## 🎯 Quick Reference Card

```bash
# Daily deployment
bash scripts/push.sh "your message"

# Check status
bash scripts/prod_status.sh

# Manual pull on prod
bash scripts/pull_to_prod.sh

# View git history
git log --oneline -10

# See changes
git diff

# Stage all changes
git add -A

# Commit
git commit -m "your message"

# Push to GitHub
git push origin main

# Pull from GitHub
git pull origin main

# Move files correctly
git mv old_path new_path

# Delete files correctly
git rm filename
```

---

**Last Updated:** February 27, 2026  
**Next Review:** When major workflow changes occur
