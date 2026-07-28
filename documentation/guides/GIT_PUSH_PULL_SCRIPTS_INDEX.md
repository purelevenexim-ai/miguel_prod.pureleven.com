# 📚 Git Documentation & Push/Pull Scripts Index

**Created:** February 27, 2026  
**Environment:** PureLeven CRM UAT (/opt/miguel) & Production (172.105.48.142)

---

## 🎯 Quick Navigation

### 🔴 **START HERE** - First Time Users

1. **[GIT_USAGE_GUIDE.md](documentation/guides/GIT_USAGE_GUIDE.md)** ⭐
   - Complete guide to Git workflow
   - Learn push/pull basics
   - Understand file synchronization
   - **Read this first!**

### 🟡 **Daily Work** - Regular Developers

2. **[Push Script](scripts/push.sh)** - Deploy to production
   ```bash
   bash scripts/push.sh "your commit message"
   ```
   - One command deployment
   - Automatically syncs all files
   - Restarts backend

3. **[Pull Script](scripts/pull_to_prod.sh)** - Manual pull on production
   ```bash
   bash scripts/pull_to_prod.sh
   ```
   - Manual update option
   - Run from UAT or Production

4. **[Status Script](scripts/prod_status.sh)** - Check production health
   ```bash
   bash scripts/prod_status.sh
   ```
   - Verify deployment worked
   - Check API health
   - Show git sync status

### 🟢 **Reference** - Advanced Topics

5. **[DEPLOYMENT_WORKFLOW_GUIDE.md](documentation/deployment/DEPLOYMENT_WORKFLOW_GUIDE.md)**
   - Complete workflow reference
   - All commands and options
   - Troubleshooting guide

6. **[HOW_TO_PULL_TO_PROD.md](documentation/deployment/HOW_TO_PULL_TO_PROD.md)**
   - Pull-to-prod options
   - Different ways to deploy
   - SSH commands

---

## 📋 File Organization

All Git-related documentation is organized:

```
documentation/
├── guides/
│   └── GIT_USAGE_GUIDE.md          ← Main Git guide (START HERE)
│
└── deployment/
    ├── DEPLOYMENT_WORKFLOW_GUIDE.md
    └── HOW_TO_PULL_TO_PROD.md

scripts/
├── push.sh                          ← Deploy to production
├── pull_to_prod.sh                  ← Manual pull option
└── prod_status.sh                   ← Check health
```

---

## 🚀 Three Essential Commands

### 1️⃣ Deploy All Changes to Production

```bash
bash scripts/push.sh "your message here"
```

**What It Does:**
- ✅ Stages ALL changes (code, docs, configs, etc.)
- ✅ Commits with your message
- ✅ Pushes to GitHub
- ✅ SSHes to Production
- ✅ Pulls latest from GitHub
- ✅ Restarts backend
- ✅ Verifies deployment

**When to Use:** After making changes in UAT, deploy to production with one command

**Examples:**
```bash
bash scripts/push.sh "feat: add customer report feature"
bash scripts/push.sh "fix: resolve order calculation bug"
bash scripts/push.sh "docs: update deployment guide"
```

### 2️⃣ Pull Latest Code to Production (Manual)

```bash
bash scripts/pull_to_prod.sh
```

**What It Does:**
- ✅ Cleans cache files
- ✅ Pulls latest from GitHub
- ✅ Shows what changed
- ✅ Restarts backend if needed

**When to Use:** If you need to manually sync production without deploying from UAT

### 3️⃣ Check Production Health & Sync Status

```bash
bash scripts/prod_status.sh
```

**What It Shows:**
- ✅ Git commit history
- ✅ Docker container status
- ✅ API health (HTTP 200 = working)
- ✅ Recent logs

**When to Use:** After deployment to verify everything is working

---

## 📊 File Synchronization Guaranteed

### ✅ What WILL Sync to Production

| Category | Examples | Notes |
|----------|----------|-------|
| **Backend Code** | `backend/app/modules/*/` | All Python code |
| **Frontend Code** | `frontend/*.html`, `frontend/styles/` | HTML, CSS, JS |
| **Scripts** | `scripts/*.sh`, `scripts/*.py` | Deployment scripts |
| **Documentation** | `docs/`, `documentation/` | Markdown files |
| **Configuration** | `config/docker-compose.yml` | Docker configs |
| **Database** | `backend/alembic/versions/` | Migrations |
| **New Files** | Any file you create | Automatically synced |
| **Renamed Files** | Files moved with `git mv` | Proper tracking |
| **Deleted Files** | Files removed with `git rm` | Properly tracked |

### ❌ What WON'T Sync (By Design)

| Type | Why |
|------|-----|
| `__pycache__/` | Python cache, auto-generated |
| `*.pyc` files | Compiled Python, auto-generated |
| `.env` files | Secrets, environment-specific |
| `.log` files | Temporary logs, not needed |
| `venv/` | Virtual env, environment-specific |

---

## 🔑 Key Rules for Perfect Sync

### ✅ DO THIS

1. **Use `git mv` for file moves**
   ```bash
   git mv old_path/file new_path/file
   ```

2. **Use `git rm` for deletions**
   ```bash
   git rm obsolete_file.py
   ```

3. **Use `git add -A` to stage everything** (handled by push.sh)
   ```bash
   git add -A
   ```

4. **Use push.sh for one-command deployment**
   ```bash
   bash scripts/push.sh "your message"
   ```

5. **Always write descriptive commit messages**
   ```bash
   git commit -m "feat: add customer report feature"
   git commit -m "fix: resolve order calculation"
   ```

### ❌ DON'T DO THIS

1. **Don't use manual `mv` for file moves** (breaks git tracking)
   ```bash
   # ❌ WRONG
   mv old_path/file new_path/file
   
   # ✅ RIGHT
   git mv old_path/file new_path/file
   ```

2. **Don't manually delete files** (breaks git tracking)
   ```bash
   # ❌ WRONG
   rm obsolete_file.py
   
   # ✅ RIGHT
   git rm obsolete_file.py
   ```

3. **Don't edit files directly on Production** (changes lost on next pull)
   ```bash
   # ❌ WRONG - changes not in git, lost on pull
   ssh prod
   vim backend/app/main.py
   
   # ✅ RIGHT - edit in UAT, push
   vim backend/app/main.py
   bash scripts/push.sh "fix"
   ```

4. **Don't force push** (overwrites others' work)
   ```bash
   # ❌ NEVER
   git push origin main -f
   ```

---

## 🔄 Synchronization Workflow

### How `push.sh` Ensures Perfect Sync

```
┌─────────────────────────────────────────────────┐
│ You make changes in UAT                         │
│ (edit code, add docs, move files, etc.)         │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│ bash scripts/push.sh "your message"             │
│ ├─ git add -A                                  │
│ ├─ git commit -m "..."                         │
│ └─ git push origin/main                        │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│ Changes in GitHub (purelevenexim-ai/crm)       │
│ ✅ Code changes                                │
│ ✅ New files                                   │
│ ✅ File renames (from git mv)                  │
│ ✅ File deletions (from git rm)                │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│ SSH to Production + git pull origin/main        │
│ ├─ Apply all changes from GitHub               │
│ ├─ Clean cache files                           │
│ ├─ docker restart backend                      │
│ └─ Verify HTTP 200                             │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│ ✅ Production Updated & Running!                │
│    All files synced perfectly                   │
└─────────────────────────────────────────────────┘
```

### Real Example: File Organization Sync

**Scenario:** Moved 5 scattered root files to organized folders

**What We Did:**
```bash
# In UAT
git mv README_MAIN.md documentation/guides/README_MAIN.md
git mv HOW_TO_PULL_TO_PROD.md documentation/deployment/HOW_TO_PULL_TO_PROD.md
# (and 3 more files)

git commit -m "chore: organize root files"
git push origin main
```

**What Happened to Production:**
```bash
# Automatic pull (via push.sh)
git pull origin main

# Result:
# ✅ Files deleted from root
# ✅ Files created in new locations
# ✅ All 5 files synced perfectly
# ✅ No files in both old AND new locations
```

**Why This Worked:**
- Used `git mv` (proper git tracking)
- GitHub knows files were "renamed" (not deleted + recreated)
- Production applied the renames correctly

---

## 📖 Learning Path

### For New Users

1. **Day 1:** Read [GIT_USAGE_GUIDE.md](documentation/guides/GIT_USAGE_GUIDE.md)
   - Understand the workflow
   - Learn daily commands
   - Understand file sync

2. **Day 2:** Try it safely
   - Make small change in UAT
   - Run `bash scripts/push.sh "test: my first change"`
   - Watch the deployment happen
   - Check `bash scripts/prod_status.sh`

3. **Day 3+:** Work normally
   - Use `bash scripts/push.sh` for all deployments
   - Use `bash scripts/prod_status.sh` to verify
   - Reference guide when needed

### For Advanced Users

- Read [DEPLOYMENT_WORKFLOW_GUIDE.md](documentation/deployment/DEPLOYMENT_WORKFLOW_GUIDE.md)
- Learn all push/pull options
- Understand troubleshooting
- Study `.gitignore` for what syncs

---

## ❓ Common Questions

### Q: How do I know what will sync?

**A:** Run before pushing:
```bash
git status          # See what changed
git diff            # See exact changes
git diff --cached   # See what will commit
```

### Q: How do I undo a commit?

**A:** Before pushing:
```bash
git commit --amend -m "new message"  # Fix message
git reset --soft HEAD~1               # Undo, keep changes
git reset --hard HEAD~1               # Undo, discard changes
```

### Q: Can I deploy without restarting?

**A:** No, backend needs restart to pick up changes. But it takes ~5 seconds.

### Q: What if production and UAT are out of sync?

**A:** Run pull_to_prod.sh to sync production to latest GitHub:
```bash
bash scripts/pull_to_prod.sh
```

### Q: Why can't I edit files directly on production?

**A:** Because changes aren't in Git, they're lost on the next pull. Always edit in UAT and push.

---

## 🎓 Next Steps

1. **Read the main guide:** [GIT_USAGE_GUIDE.md](documentation/guides/GIT_USAGE_GUIDE.md)
2. **Learn the commands:** Review the script comments
3. **Try safely:** Make a small change and deploy
4. **Reference this:** Come back when you have questions

---

## 📞 Quick Reference

```bash
# Deploy changes to production
bash scripts/push.sh "your message"

# Check production health
bash scripts/prod_status.sh

# Manually pull on production
bash scripts/pull_to_prod.sh

# View git history
git log --oneline -10

# See what changed
git status
git diff

# Stage all changes
git add -A

# Commit changes
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

## 📚 Documentation Files

| File | Purpose | Read When |
|------|---------|-----------|
| [GIT_USAGE_GUIDE.md](documentation/guides/GIT_USAGE_GUIDE.md) | Complete Git workflow guide | First time, refresher |
| [DEPLOYMENT_WORKFLOW_GUIDE.md](documentation/deployment/DEPLOYMENT_WORKFLOW_GUIDE.md) | Full deployment reference | Advanced topics |
| [HOW_TO_PULL_TO_PROD.md](documentation/deployment/HOW_TO_PULL_TO_PROD.md) | Pull-to-prod options | Need to deploy manually |
| [FILE_ORGANIZATION_COMPLETE.md](FILE_ORGANIZATION_COMPLETE.md) | File structure overview | Understand organization |

---

**Status:** ✅ All documentation and scripts ready for production use  
**Last Updated:** February 27, 2026  
**Next Review:** When workflow changes occur
