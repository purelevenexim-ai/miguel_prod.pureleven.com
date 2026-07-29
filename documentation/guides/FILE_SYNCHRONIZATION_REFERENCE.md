# 🔄 File Synchronization Deep Dive

**Purpose:** Understand exactly how files sync between UAT and Production  
**Audience:** Developers who need to ensure changes propagate correctly  
**Updated:** February 27, 2026

---

## 📊 Complete Synchronization Reference

### What Happens When You Run: `bash scripts/push.sh "message"`

```
Step 1: Gather Changes
├─ Read all files in /opt/miguel
├─ Compare with last commit
├─ Identify what changed
└─ Show you the files (git status)

Step 2: Stage All Changes
├─ git add -A
├─ This stages:
│  ├─ Modified files
│  ├─ New files
│  ├─ Deleted files
│  ├─ Renamed files (if using git mv)
│  └─ Folder structure changes
└─ Files ignored by .gitignore are SKIPPED

Step 3: Commit to Local Git
├─ git commit -m "your message"
├─ Creates commit with all staged changes
└─ Commit is now in local git history

Step 4: Push to GitHub
├─ git push origin main
├─ Uploads commit to GitHub
├─ Updates origin/main reference
└─ All 9+ million developers can see changes

Step 5: SSH to Production
├─ Connect to 172.105.48.142 (production server)
├─ Change directory to /opt/pureleven
└─ Execute 7 commands remotely

Step 6: Clean Production Cache
├─ Remove __pycache__ directories
├─ Delete *.pyc files
└─ Reset to clean git state (git reset --hard HEAD)

Step 7: Pull from GitHub to Production
├─ git pull origin main
├─ Git applies all commits since last pull
├─ Files are updated/created/deleted/renamed
├─ All changes from GitHub appear on production
└─ Same files as UAT now!

Step 8: Restart Backend
├─ docker restart pureleven_backend (or docker-compose restart)
├─ Backend stops running
├─ Backend starts with NEW code loaded
└─ Takes ~5 seconds

Step 9: Verify Deployment
├─ Check container status
├─ Test API health (curl HTTP 200)
├─ Show success message
└─ YOU'RE DONE!
```

---

## 📁 File Type Sync Matrix

### Category 1: Backend Code

| File Type | Example Path | Syncs? | How It Works |
|-----------|--------------|--------|-------------|
| **Python Modules** | `backend/app/modules/orders/service.py` | ✅ YES | Edit → push.sh → github → prod pulls |
| **API Routes** | `backend/app/modules/*/routes.py` | ✅ YES | Same as above |
| **Models** | `backend/app/models/` | ✅ YES | Same as above |
| **Database Models** | `backend/app/database/models.py` | ✅ YES | Same as above |
| **Core Utilities** | `backend/app/core/` | ✅ YES | Same as above |
| **Migrations** | `backend/alembic/versions/` | ✅ YES | Database schema changes sync |

**Example Sync:**
```bash
# UAT
vim backend/app/modules/orders/service.py
bash scripts/push.sh "fix: resolve order calculation"

# Production (automatic)
git pull origin main  # Gets the modified service.py
docker restart backend  # Backend loads new code
# ✅ Fix is live!
```

### Category 2: Frontend Code

| File Type | Example Path | Syncs? | How It Works |
|-----------|--------------|--------|-------------|
| **HTML** | `frontend/*.html` | ✅ YES | Edit → push.sh → nginx serves new file |
| **CSS** | `frontend/styles/ds.css` | ✅ YES | Edit → push.sh → browser loads new CSS |
| **JavaScript** | `frontend/modules/*.js` | ✅ YES | Edit → push.sh → browser loads new JS |
| **Assets** | `frontend/favicon.ico` | ✅ YES | Edit → push.sh → file synced |

**Example Sync:**
```bash
# UAT
vim frontend/customers.html
bash scripts/push.sh "ui: update customers page"

# Production (automatic)
git pull origin main  # Gets new customers.html
# Nginx serves new file
# ✅ UI update is live!
```

### Category 3: Configuration Files

| File Type | Example Path | Syncs? | How It Works |
|-----------|--------------|--------|-------------|
| **Docker Compose** | `config/docker-compose.prod.yml` | ✅ YES | Edit → push.sh → prod uses new config |
| **Nginx Config** | `infra/nginx-prod.conf` | ✅ YES | Edit → push.sh → nginx reloads |
| **Python Configs** | `backend/app/config/` | ✅ YES | Edit → push.sh → backend reads new config |
| **Environment Configs** | `.env` files | ❌ NO | Security: kept private per server |

**Example Sync:**
```bash
# UAT
vim config/docker-compose.prod.yml
bash scripts/push.sh "ops: update docker compose"

# Production (automatic)
git pull origin main  # Gets new config
# ✅ Config is updated!
```

### Category 4: Documentation

| File Type | Example Path | Syncs? | How It Works |
|-----------|--------------|--------|-------------|
| **Markdown Guides** | `documentation/guides/*.md` | ✅ YES | Edit → push.sh → file synced |
| **Deployment Docs** | `documentation/deployment/*.md` | ✅ YES | Edit → push.sh → file synced |
| **API Docs** | `docs/api/` | ✅ YES | Edit → push.sh → file synced |
| **README Files** | `*.md` | ✅ YES | Edit → push.sh → file synced |

**Example Sync:**
```bash
# UAT
vim documentation/guides/GIT_USAGE_GUIDE.md
bash scripts/push.sh "docs: update git guide"

# Production (automatic)
git pull origin main  # Gets updated guide
# ✅ Docs are updated!
```

### Category 5: Scripts

| File Type | Example Path | Syncs? | How It Works |
|-----------|--------------|--------|-------------|
| **Deployment Scripts** | `scripts/push.sh` | ✅ YES | Edit → push.sh → prod gets new script |
| **Python Scripts** | `scripts/seed_*.py` | ✅ YES | Edit → push.sh → file synced |
| **Utility Scripts** | `scripts/*.sh` | ✅ YES | Edit → push.sh → file synced |

**Example Sync:**
```bash
# UAT
vim scripts/prod_status.sh
bash scripts/push.sh "ops: enhance status check"

# Production (automatic)
git pull origin main  # Gets updated script
# ✅ Script is updated!
```

### Category 6: Database Files

| File Type | Example Path | Syncs? | How It Works |
|-----------|--------------|--------|-------------|
| **Migrations** | `backend/alembic/versions/*.py` | ✅ YES | Edit → push.sh → alembic schema syncs |
| **Alembic Env** | `backend/alembic/env.py` | ✅ YES | Edit → push.sh → migration config syncs |
| **Initial Data** | `backend/alembic/versions/` | ✅ YES | New schemas sync to production DB |

**Example Sync:**
```bash
# UAT
alembic revision --autogenerate -m "add new column"
bash scripts/push.sh "db: add customer_type column"

# Production (automatic)
git pull origin main  # Gets new migration
alembic upgrade head  # (manual, but migration file synced)
# ✅ Schema is updated!
```

### Category 7: New Files & Folders

| Operation | Example | Syncs? | How It Works |
|-----------|---------|--------|-------------|
| **Create New File** | `touch documentation/new-guide.md` | ✅ YES | File added → git add -A → push.sh → prod gets file |
| **Create New Folder** | `mkdir -p docs/new-section/` | ✅ YES | git add will include new folder |
| **Add to Subfolder** | `touch docs/new/file.md` | ✅ YES | git add -A stages entire folder |

**Example Sync:**
```bash
# UAT
mkdir -p documentation/new-feature
echo "Feature guide" > documentation/new-feature/README.md
bash scripts/push.sh "docs: add new feature documentation"

# Production (automatic)
git pull origin main  # Gets new folder + file
# ✅ Folder and file exist on production!
```

### Category 8: File Renames & Moves

| Operation | Example | Syncs? | How It Works |
|-----------|---------|--------|-------------|
| **Rename with `git mv`** | `git mv old.md new.md` | ✅ YES | Git tracks it as rename, prod applies rename |
| **Move with `git mv`** | `git mv old/file new/file` | ✅ YES | Git knows it moved, prod applies move |
| **Rename with `mv`** | `mv old.md new.md` | ❌ NO | Git sees delete + create, sync breaks |

**Example Sync - CORRECT:**
```bash
# UAT - CORRECT WAY
git mv documentation/old-guide.md documentation/guides/old-guide.md
bash scripts/push.sh "docs: reorganize guides"

# Git status shows:
# R  documentation/old-guide.md -> documentation/guides/old-guide.md

# Production pulls:
git pull origin main
# ✅ File moved to correct location!
```

**Example Sync - WRONG:**
```bash
# UAT - WRONG WAY (don't do this!)
mv documentation/old-guide.md documentation/guides/old-guide.md
bash scripts/push.sh "docs: reorganize"

# Git status shows:
# D  documentation/old-guide.md (deleted)
# A  documentation/guides/old-guide.md (new file)

# Production pulls:
git pull origin main
# ❌ Old file removed, new file created
# ❌ But git tracking is confused about the move
# ❌ Sync is fragile and error-prone
```

**KEY RULE:** Always use `git mv`, never manual `mv`

### Category 9: File Deletions

| Operation | Example | Syncs? | How It Works |
|-----------|---------|--------|-------------|
| **Delete with `git rm`** | `git rm deprecated.py` | ✅ YES | Git tracks deletion, prod removes file |
| **Delete with `rm`** | `rm deprecated.py` | ❌ NO | Git doesn't track it as deletion |

**Example Sync - CORRECT:**
```bash
# UAT - CORRECT WAY
git rm backend/deprecated_module.py
bash scripts/push.sh "refactor: remove deprecated code"

# Git status shows:
# D  backend/deprecated_module.py

# Production pulls:
git pull origin main
# ✅ File is deleted on production!
```

**Example Sync - WRONG:**
```bash
# UAT - WRONG WAY (don't do this!)
rm backend/deprecated_module.py
bash scripts/push.sh "refactor: remove code"

# Git status shows:
# D  backend/deprecated_module.py (unstaged)

# If you don't stage it:
git add -A  # This stages all changes
# But git might be confused

# Production pulls:
git pull origin main
# Might not delete the file properly
```

**KEY RULE:** Always use `git rm`, never manual `rm`

### Category 10: Files That DON'T Sync

| File Type | Example Path | Syncs? | Why |
|-----------|--------------|--------|-----|
| **Python Cache** | `__pycache__/` | ❌ NO | Auto-generated, wasteful |
| **Compiled Python** | `*.pyc` | ❌ NO | Auto-generated, wasteful |
| **Environment Files** | `.env` | ❌ NO | Contains secrets, server-specific |
| **Log Files** | `app.log` | ❌ NO | Temporary, large, not needed |
| **Virtual Environments** | `venv/` | ❌ NO | Large, environment-specific |
| **IDE Settings** | `.vscode/`, `.idea/` | ❌ NO | Editor-specific, not needed |
| **OS Files** | `.DS_Store` | ❌ NO | OS-specific, not needed |

**Why They're Ignored:**
```bash
# View what's ignored
cat .gitignore

# Example .gitignore entries
__pycache__/          # Python cache
*.pyc                 # Compiled Python
.env                  # Secrets
*.log                 # Logs
venv/                 # Virtual env
.vscode/              # VS Code settings
.DS_Store             # macOS cruft
```

---

## 🔍 Real-World Synchronization Examples

### Example 1: Code Change Propagation

```
═══════════════════════════════════════════════════════════════════════════════

UAT DEVELOPMENT:
  1. Edit backend code
     vim backend/app/modules/orders/service.py
     
  2. Test locally
     python -m pytest tests/test_orders.py
     # ✅ All tests pass
     
  3. Deploy
     bash scripts/push.sh "fix: resolve order calculation"
     
     Output:
     📋 PHASE 1: REVIEWING YOUR CHANGES
     📁 Files with changes:
       M backend/app/modules/orders/service.py
     
     📝 PHASE 2: STAGING AND COMMITTING
     ✅ Staged changes:
       M backend/app/modules/orders/service.py
     
     ✅ Committed successfully (abc1234)
     
     🌐 PHASE 3: PUSHING TO GITHUB
     ✅ Pushed to GitHub (origin/main)
     
     🚀 PHASE 4: DEPLOYING TO PRODUCTION
     ✅ Code pulled successfully
     ✅ Backend restarted
     
     ✔️  PHASE 5: VERIFYING DEPLOYMENT
     ✅ API Health Check: HTTP 200

═══════════════════════════════════════════════════════════════════════════════

GITHUB:
  GitHub commit abc1234 now contains:
  ├─ Modified service.py with fix
  └─ Message: "fix: resolve order calculation"

═══════════════════════════════════════════════════════════════════════════════

PRODUCTION:
  1. Pulls changes
     git pull origin main
     
  2. Git applies changes
     Updated backend/app/modules/orders/service.py
     
  3. Backend restarts with new code loaded
     docker restart pureleven_backend
     
  4. Fix is live!
     ✅ Order calculations now correct on production

═══════════════════════════════════════════════════════════════════════════════
```

### Example 2: File Reorganization Sync

```
═══════════════════════════════════════════════════════════════════════════════

UAT ORGANIZATION:
  1. Reorganize scattered root files
     git mv README_MAIN.md documentation/guides/README_MAIN.md
     git mv HOW_TO_PULL_TO_PROD.md documentation/deployment/HOW_TO_PULL_TO_PROD.md
     
  2. Git tracks moves properly
     git status shows:
     R  README_MAIN.md -> documentation/guides/README_MAIN.md
     R  HOW_TO_PULL_TO_PROD.md -> documentation/deployment/HOW_TO_PULL_TO_PROD.md
     
  3. Deploy
     bash scripts/push.sh "chore: organize root files"

═══════════════════════════════════════════════════════════════════════════════

GITHUB:
  GitHub commit shows:
  ├─ File moved: README_MAIN.md → documentation/guides/
  ├─ File moved: HOW_TO_PULL_TO_PROD.md → documentation/deployment/
  └─ Git knows these are "renames", not delete+create

═══════════════════════════════════════════════════════════════════════════════

PRODUCTION:
  1. Pulls changes
     git pull origin main
     
  2. Git applies file moves
     - README_MAIN.md deleted from root
     - README_MAIN.md created in documentation/guides/
     - HOW_TO_PULL_TO_PROD.md deleted from root
     - HOW_TO_PULL_TO_PROD.md created in documentation/deployment/
     
  3. Result
     ✅ Files in correct locations on production
     ✅ No duplicate files
     ✅ No files in old + new locations
     ✅ Perfect synchronization

═══════════════════════════════════════════════════════════════════════════════
```

### Example 3: New File Sync

```
═══════════════════════════════════════════════════════════════════════════════

UAT CREATION:
  1. Create new feature
     mkdir -p documentation/new-feature
     echo "Feature docs" > documentation/new-feature/README.md
     
  2. Stage and deploy
     bash scripts/push.sh "docs: add new feature documentation"
     
     Output shows:
     A documentation/new-feature/README.md
     
     git stages the new file:
     git add -A

═══════════════════════════════════════════════════════════════════════════════

GITHUB:
  GitHub commit now includes:
  ├─ New folder: documentation/new-feature/
  └─ New file: documentation/new-feature/README.md

═══════════════════════════════════════════════════════════════════════════════

PRODUCTION:
  1. Pulls changes
     git pull origin main
     
  2. Git creates new files
     - Folder documentation/new-feature/ created
     - File documentation/new-feature/README.md created
     
  3. Result
     ✅ New folder exists on production
     ✅ New file exists on production
     ✅ Content is identical to UAT

═══════════════════════════════════════════════════════════════════════════════
```

---

## ✅ Sync Verification Checklist

After each deployment, verify synchronization:

```bash
# 1. Check UAT commit
cd /opt/miguel
git log --oneline -1
# Example output: abc1234 fix: resolve order calculation

# 2. Check it's on GitHub
# Visit: https://github.com/purelevenexim-ai/crm
# Look for commit abc1234

# 3. Check Production has it
bash scripts/prod_status.sh
# Should show same commit hash in output

# 4. Verify files are present
ssh root@172.105.48.142 "cd /opt/pureleven && ls -la documentation/guides/GIT_USAGE_GUIDE.md"
# Should show the file exists

# 5. Verify API is working
curl http://172.105.48.142:8000/docs
# Should return HTTP 200

# 6. Check containers are running
bash scripts/prod_status.sh | grep "Up "
# Should show all containers "Up X hours/minutes"
```

---

## 🎯 Summary: What You Need to Know

1. **Everything syncs via Git**
   - Changes you make → git add → git commit → git push → GitHub
   - Production pulls from GitHub → gets your changes

2. **Use correct git commands**
   - `git mv` for file moves (not `mv`)
   - `git rm` for deletions (not `rm`)
   - `git add -A` to stage everything (handled by push.sh)

3. **Use push.sh for one-command deployment**
   - `bash scripts/push.sh "your message"`
   - Handles all 9 steps automatically

4. **Verify with prod_status.sh**
   - `bash scripts/prod_status.sh`
   - Shows if production is synced and healthy

5. **UAT and Production should always be at same commit**
   - If they're different, something's wrong
   - Use pull_to_prod.sh to manually sync if needed

---

**Status:** ✅ Complete synchronization documentation  
**Last Updated:** February 27, 2026
