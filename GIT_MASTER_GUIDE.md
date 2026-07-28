# 📚 Master Git Documentation & Deployment Guide

**Last Updated:** February 27, 2026  
**Environment:** PureLeven CRM - UAT (/opt/miguel) & Production (172.105.48.142)  
**Status:** ✅ Production Ready

---

## 🚀 START HERE - Complete Quick Start

### For First-Time Users

```bash
# 1. Read the main guide
cat documentation/guides/GIT_USAGE_GUIDE.md

# 2. Deploy a test change
bash scripts/push.sh "test: my first deployment"

# 3. Check it worked
bash scripts/prod_status.sh
```

### For Experienced Developers

```bash
# Deploy changes
bash scripts/push.sh "your commit message"

# Verify deployment
bash scripts/prod_status.sh

# Pull manually if needed
bash scripts/pull_to_prod.sh
```

---

## 📖 Documentation Library

### 🔴 Essential Reading (READ THESE FIRST)

1. **[GIT_USAGE_GUIDE.md](documentation/guides/GIT_USAGE_GUIDE.md)** ⭐⭐⭐
   - **Purpose:** Complete Git workflow guide
   - **Length:** ~35 min read
   - **Contains:**
     - Quick start commands
     - Daily workflow scenarios
     - File sync explanation
     - Common commands reference
     - Troubleshooting guide
     - Best practices
   - **Read when:** Starting work, first time, refresher needed

2. **[FILE_SYNCHRONIZATION_REFERENCE.md](documentation/guides/FILE_SYNCHRONIZATION_REFERENCE.md)** ⭐⭐
   - **Purpose:** Understand exactly how files sync
   - **Length:** ~25 min read
   - **Contains:**
     - Complete sync matrix (what syncs, what doesn't)
     - Real-world examples
     - File type sync reference
     - Verification checklist
   - **Read when:** Need to understand sync details, verify changes

3. **[GIT_PUSH_PULL_SCRIPTS_INDEX.md](documentation/guides/GIT_PUSH_PULL_SCRIPTS_INDEX.md)** ⭐
   - **Purpose:** Navigate push/pull scripts and quick reference
   - **Length:** ~15 min read
   - **Contains:**
     - Script quick reference
     - 3 essential commands
     - Learning path for new users
     - Common questions
   - **Read when:** Need quick reference, learning the scripts

### 🟡 Advanced Reference

4. **[DEPLOYMENT_WORKFLOW_GUIDE.md](documentation/deployment/DEPLOYMENT_WORKFLOW_GUIDE.md)**
   - **Purpose:** Complete deployment reference
   - **Length:** ~20 min read
   - **Contains:**
     - Full workflow with all options
     - Troubleshooting guide
     - Advanced scenarios
   - **Read when:** Advanced topics, unusual situations

5. **[HOW_TO_PULL_TO_PROD.md](documentation/deployment/HOW_TO_PULL_TO_PROD.md)**
   - **Purpose:** Pull-to-prod options
   - **Length:** ~10 min read
   - **Contains:**
     - Different pull methods
     - SSH commands
     - Manual sync options
   - **Read when:** Need to manually pull without push.sh

### 🟢 Reference & Setup

6. **[FILE_ORGANIZATION_COMPLETE.md](FILE_ORGANIZATION_COMPLETE.md)**
   - **Purpose:** Understand folder structure
   - **Length:** ~10 min read
   - **Contains:**
     - File organization overview
     - Folder structure
     - File locations
   - **Read when:** Need to find where files are

---

## 🔧 Three Essential Scripts

All scripts are in `/opt/miguel/scripts/` and automatically sync to production.

### 1️⃣ push.sh - Deploy to Production

**File:** `scripts/push.sh`

**One-Line:** Deploy ALL your changes to production with one command

**Command:**
```bash
bash scripts/push.sh "your commit message"
```

**What It Does:**
```
Your Changes in UAT
        ↓
git add -A (stage all)
        ↓
git commit (commit with message)
        ↓
git push (push to GitHub)
        ↓
SSH to Production (connect)
        ↓
git pull (get changes)
        ↓
docker restart (load new code)
        ↓
✅ PRODUCTION UPDATED!
```

**Examples:**
```bash
bash scripts/push.sh "feat: add customer report feature"
bash scripts/push.sh "fix: resolve order calculation bug"
bash scripts/push.sh "docs: update deployment guide"
bash scripts/push.sh "refactor: reorganize backend modules"
bash scripts/push.sh "perf: optimize database queries"
```

**Syncs Automatically:**
- ✅ Python code (`.py` files)
- ✅ Frontend code (`.html`, `.css`, `.js`)
- ✅ Documentation (`.md` files)
- ✅ Configuration files
- ✅ New files and folders
- ✅ File renames (using `git mv`)
- ✅ File deletions (using `git rm`)

**Does NOT Sync:**
- ❌ `__pycache__` (Python cache)
- ❌ `*.pyc` files
- ❌ `.env` files (secrets)
- ❌ `.log` files
- ❌ `venv/` (virtual environment)

**Output Shows:**
```
═══════════════════════════════════════════════════════════
📤 PUSH TO GIT + DEPLOY TO PRODUCTION
═══════════════════════════════════════════════════════════

📋 PHASE 1: REVIEWING YOUR CHANGES
📁 Files with changes:
   M backend/app/modules/orders/service.py
   A documentation/guides/new-guide.md

📝 PHASE 2: STAGING AND COMMITTING
✅ Staged changes: 2 files

🌐 PHASE 3: PUSHING TO GITHUB
✅ Pushed to GitHub

🚀 PHASE 4: DEPLOYING TO PRODUCTION
✅ Production pulled latest code
✅ Backend restarted
✅ Containers running

✔️  PHASE 5: VERIFYING DEPLOYMENT
✅ API Health Check: HTTP 200

✅ ✅ ✅  DEPLOYMENT COMPLETE!
```

---

### 2️⃣ prod_status.sh - Check Production Health

**File:** `scripts/prod_status.sh`

**One-Line:** Check if production is healthy and synced with UAT

**Command:**
```bash
bash scripts/prod_status.sh
```

**What It Shows:**
```
Git Status
├─ Current commit hash
├─ Commit message
└─ Branch name

Docker Containers
├─ pureleven_backend: Up X minutes
├─ pureleven_db: Up X hours
└─ pureleven_frontend: Up X hours

API Health
├─ HTTP Status: 200 ✅ (working)
└─ Response time

Recent Logs
└─ Last 20 lines of backend logs
```

**Use Cases:**
```bash
# After deployment
bash scripts/prod_status.sh

# During troubleshooting
bash scripts/prod_status.sh

# Morning health check
bash scripts/prod_status.sh

# Verify API is responding
bash scripts/prod_status.sh | grep "HTTP"
```

---

### 3️⃣ pull_to_prod.sh - Manual Pull Option

**File:** `scripts/pull_to_prod.sh` (UAT) or `scripts/pull-to-prod.sh` (Prod)

**One-Line:** Manually pull latest code to production without push.sh

**Commands:**
```bash
# Option 1: Run from UAT (auto-SSHes to production)
bash scripts/pull_to_prod.sh

# Option 2: SSH to production first
ssh root@172.105.48.142
cd /opt/pureleven
bash scripts/pull-to-prod.sh
```

**What It Does:**
```
Check Current State
        ↓
Clean Cache Files (__pycache__, *.pyc)
        ↓
Reset to Clean Git State
        ↓
Fetch from GitHub
        ↓
Check for Updates
        ↓
Pull New Code
        ↓
Show What Changed
        ↓
✅ PRODUCTION UPDATED!
```

**When to Use:**
- Manually sync production without deploying from UAT
- Emergency rollback/restore
- Testing pull process
- Manual verification of changes

---

## 📊 File Synchronization

### What Syncs (Complete List)

| Category | Syncs? | Examples |
|----------|--------|----------|
| **Backend Code** | ✅ | `backend/app/modules/*.py`, `backend/app/core/*.py` |
| **Frontend Code** | ✅ | `frontend/*.html`, `frontend/styles/*.css` |
| **Documentation** | ✅ | `documentation/guides/*.md`, `docs/*.md` |
| **Configuration** | ✅ | `config/docker-compose.yml`, `infra/nginx.conf` |
| **Scripts** | ✅ | `scripts/*.sh`, `scripts/*.py` |
| **Database** | ✅ | `backend/alembic/versions/*.py` |
| **New Files** | ✅ | Any file you create |
| **File Renames** | ✅ | Files moved with `git mv` |
| **File Deletions** | ✅ | Files deleted with `git rm` |

### What Doesn't Sync (By Design)

| Type | Example | Why |
|------|---------|-----|
| **Python Cache** | `__pycache__/` | Auto-generated, wasteful |
| **Compiled Python** | `*.pyc` | Auto-generated |
| **Secrets** | `.env` | Server-specific, confidential |
| **Logs** | `*.log` | Temporary, large |
| **Virtual Env** | `venv/` | Environment-specific, large |

---

## ✅ Best Practices Summary

### ✅ DO

```bash
# 1. Use git mv for file moves
git mv old_location new_location

# 2. Use git rm for deletions
git rm obsolete_file.py

# 3. Use push.sh for deployments
bash scripts/push.sh "your message"

# 4. Check status before pushing
git status
git diff

# 5. Verify after deployment
bash scripts/prod_status.sh
```

### ❌ DON'T

```bash
# 1. Don't use manual mv (breaks git)
mv old_location new_location  # ❌ WRONG

# 2. Don't use manual rm (breaks git)
rm obsolete_file.py           # ❌ WRONG

# 3. Don't edit files on production
ssh prod
vim backend/app/main.py       # ❌ WRONG

# 4. Don't force push
git push -f                   # ❌ WRONG

# 5. Don't commit secrets
echo "password=123" > .env    # ❌ WRONG
```

---

## 🔄 Daily Workflow

### Morning - Start Your Work

```bash
# Update UAT to latest
git pull origin main

# Check what's on production
bash scripts/prod_status.sh
```

### During Work - Make Changes

```bash
# Edit your files
vim backend/app/modules/orders/service.py
vim frontend/customers.html

# Check what changed
git status
git diff

# Move/delete files properly
git mv old_file new_file
git rm obsolete_file
```

### Before Deploying - Stage Changes

```bash
# Review changes one more time
git status
git diff

# Stage all changes (handled by push.sh, but you can check)
git add -A
```

### Deploy - Push to Production

```bash
# One command deployment
bash scripts/push.sh "feat: add new order status"
```

### After Deploy - Verify

```bash
# Check production is healthy
bash scripts/prod_status.sh

# Check API is responding
curl http://172.105.48.142:8000/docs

# Test feature in browser
# Visit https://172.105.48.142
```

---

## 🆘 Common Issues & Solutions

### Issue: "Changes not synced to production"

**Solution:**
```bash
# Check production is at same commit
bash scripts/prod_status.sh

# If different, manually pull
bash scripts/pull_to_prod.sh

# Re-deploy with push.sh
bash scripts/push.sh "fix: resync changes"
```

### Issue: "File moved but broke on production"

**Solution:**
```bash
# Check if you used git mv (correct)
git log -p --follow -- filename

# If you used manual mv, fix it:
git reset --hard HEAD~1
git mv old_location new_location
git add -A
git commit -m "fix: proper file move using git mv"
git push origin main
bash scripts/pull_to_prod.sh
```

### Issue: "Cannot SSH to production"

**Solution:**
```bash
# Check SSH key exists
ls ~/.ssh/id_rsa

# Test connection
ssh -v root@172.105.48.142

# If fails, check config
cat ~/.ssh/config
# Should have 172.105.48.142 entry
```

### Issue: "Merge conflicts when pulling"

**Solution:**
```bash
# See conflicts
git status | grep "both modified"

# Fix conflicts in the file
vim conflicting_file.py
# Look for <<<<<<, =======, >>>>>> markers
# Keep what you need

# Complete merge
git add conflicting_file.py
git commit -m "fix: resolve merge conflicts"
git push origin main
```

---

## 📞 Quick Reference

```bash
# ═══════════════════════════════════════════════════════════
# MOST IMPORTANT COMMANDS
# ═══════════════════════════════════════════════════════════

# Deploy to production
bash scripts/push.sh "your message"

# Check production health
bash scripts/prod_status.sh

# Manually pull on production
bash scripts/pull_to_prod.sh

# ═══════════════════════════════════════════════════════════
# GIT BASICS
# ═══════════════════════════════════════════════════════════

# See what changed
git status
git diff

# Stage changes (automatically in push.sh)
git add -A

# Commit changes (automatically in push.sh)
git commit -m "your message"

# Push to GitHub (automatically in push.sh)
git push origin main

# Pull from GitHub
git pull origin main

# View history
git log --oneline -10

# ═══════════════════════════════════════════════════════════
# FILE OPERATIONS (Important: use git commands!)
# ═══════════════════════════════════════════════════════════

# Move/rename files correctly
git mv old_path new_path

# Delete files correctly
git rm filename

# Undo changes to file
git checkout -- filename

# Undo last commit (keep changes)
git reset --soft HEAD~1

# Undo last commit (discard changes)
git reset --hard HEAD~1

# ═══════════════════════════════════════════════════════════
```

---

## 🎓 Learning Resources

### For Beginners

1. Start: **GIT_USAGE_GUIDE.md** (Quick Start section)
2. Try: Run push.sh with a test change
3. Verify: Run prod_status.sh to confirm
4. Learn: Read FILE_SYNCHRONIZATION_REFERENCE.md
5. Reference: Use GIT_PUSH_PULL_SCRIPTS_INDEX.md as needed

### For Advanced Users

1. Reference: DEPLOYMENT_WORKFLOW_GUIDE.md
2. Deep Dive: FILE_SYNCHRONIZATION_REFERENCE.md (File Type Sync Matrix)
3. Troubleshoot: Use prod_status.sh to diagnose issues
4. Customize: Modify scripts if needed (then push to sync)

---

## ✨ Key Takeaways

1. **One Command Deployment**
   ```bash
   bash scripts/push.sh "your message"
   ```
   Stages, commits, pushes, deploys, restarts, verifies. Done!

2. **Perfect File Synchronization**
   - All code syncs ✅
   - All docs syncs ✅
   - All config syncs ✅
   - Use git commands (git mv, git rm, git add) ✅

3. **Three Essential Scripts**
   - `push.sh` → Deploy to production
   - `prod_status.sh` → Verify health
   - `pull_to_prod.sh` → Manual pull

4. **Always Verify**
   - After deployment: `bash scripts/prod_status.sh`
   - Check API: `curl http://172.105.48.142:8000/docs`
   - Check logs: `bash scripts/prod_status.sh | tail -20`

5. **Use Proper Git Commands**
   - Move files: `git mv` (not `mv`)
   - Delete files: `git rm` (not `rm`)
   - Stage changes: `git add -A` (handled by push.sh)

---

## 📚 Document Map

```
documentation/
├── guides/
│   ├── GIT_USAGE_GUIDE.md ⭐ START HERE
│   ├── GIT_PUSH_PULL_SCRIPTS_INDEX.md ← Navigation & Quick Ref
│   ├── FILE_SYNCHRONIZATION_REFERENCE.md ← Deep Dive
│   └── ... (other guides)
│
└── deployment/
    ├── DEPLOYMENT_WORKFLOW_GUIDE.md ← Full Reference
    ├── HOW_TO_PULL_TO_PROD.md ← Pull Options
    └── ... (other deployment docs)

scripts/
├── push.sh ← Deploy to production
├── prod_status.sh ← Check health
├── pull_to_prod.sh ← Manual pull
└── ... (other scripts)

FILE_ORGANIZATION_COMPLETE.md ← Folder Structure

THIS FILE ← Master Guide (you are here)
```

---

## 🎯 Next Steps

1. **Read** [GIT_USAGE_GUIDE.md](documentation/guides/GIT_USAGE_GUIDE.md) (20-30 min)
2. **Try** deploying a small change: `bash scripts/push.sh "test: my first deploy"`
3. **Verify** it worked: `bash scripts/prod_status.sh`
4. **Reference** this guide whenever you need it

---

## ✅ Verification

Confirm everything is set up:

```bash
# 1. Check scripts exist
ls -la scripts/push.sh scripts/prod_status.sh scripts/pull_to_prod.sh

# 2. Check documentation exists
ls -la documentation/guides/GIT_USAGE_GUIDE.md
ls -la documentation/guides/FILE_SYNCHRONIZATION_REFERENCE.md
ls -la documentation/guides/GIT_PUSH_PULL_SCRIPTS_INDEX.md

# 3. Check production can be reached
ssh -o StrictHostKeyChecking=no root@172.105.48.142 "echo ✅ SSH works"

# 4. Check git is configured
git config --global user.name
git config --global user.email

# 5. Check current branch
git rev-parse --abbrev-ref HEAD  # Should show: main

# 6. Try a test deployment
bash scripts/push.sh "test: verification deployment"

# 7. Check it synced
bash scripts/prod_status.sh
```

---

**Status:** ✅ Complete  
**Last Updated:** February 27, 2026  
**All Systems:** Tested and Production Ready  
**Total Documentation:** 1,000+ lines across 5 comprehensive guides  
**Scripts:** 3 production-ready deployment scripts  
**Synchronization:** Guaranteed file sync across all environments
