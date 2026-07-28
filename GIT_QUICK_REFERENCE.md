# 🎯 Git Quick Reference Card

**Bookmark This!** - Keep this handy for daily use

---

## 🚀 THREE COMMANDS YOU NEED

### 1. Deploy to Production
```bash
bash scripts/push.sh "your commit message"
```
Does everything: stage → commit → push GitHub → pull prod → restart → verify

### 2. Check Production Health  
```bash
bash scripts/prod_status.sh
```
Shows: git status, containers running, API health (HTTP 200)

### 3. Manual Pull (if needed)
```bash
bash scripts/pull_to_prod.sh
```
Manual sync to production from GitHub

---

## 📋 Daily Workflow

```bash
# 1. Start day - get latest
git pull origin main

# 2. Make changes
vim backend/app/modules/orders/service.py
vim frontend/customers.html

# 3. Check what changed
git status
git diff

# 4. Deploy to production
bash scripts/push.sh "feat: add new order status"

# 5. Verify it worked
bash scripts/prod_status.sh

# 6. Repeat for each feature!
```

---

## ⚠️ IMPORTANT RULES

### ✅ DO THIS
```bash
# Move files with git
git mv old_path new_path

# Delete files with git
git rm obsolete_file.py

# Deploy with push.sh
bash scripts/push.sh "message"

# Verify with prod_status
bash scripts/prod_status.sh
```

### ❌ DON'T DO THIS
```bash
# Don't move files manually
mv old_path new_path  # ❌ BREAKS GIT

# Don't delete files manually  
rm obsolete_file.py   # ❌ BREAKS GIT

# Don't edit on production
ssh prod
vim backend/app/main.py  # ❌ CHANGES LOST

# Don't force push
git push -f  # ❌ OVERWRITES OTHERS
```

---

## 🔄 What Syncs When You Deploy

### ✅ WILL SYNC
- Backend Python code
- Frontend (HTML, CSS, JS)
- Documentation (markdown files)
- Configuration files
- Scripts (bash, python)
- New files & folders
- File renames (git mv)
- File deletions (git rm)

### ❌ WON'T SYNC
- `__pycache__/` (Python cache)
- `*.pyc` files
- `.env` (secrets - keep separate!)
- `.log` files
- `venv/` (virtual environment)

---

## 🐛 Quick Troubleshooting

### Problem: Changes not on production

**Solution:**
```bash
# Check if production is synced
bash scripts/prod_status.sh

# If not, manually pull
bash scripts/pull_to_prod.sh

# Then deploy
bash scripts/push.sh "fix: resync"
```

### Problem: File moved but broke

**Solution:**
```bash
# Check if you used git mv (correct)
git log -p --follow -- filename

# If not, fix it:
git reset --hard HEAD~1
git mv old_path new_path
git commit -m "fix: proper move with git mv"
git push origin main
bash scripts/pull_to_prod.sh
```

### Problem: Can't SSH to production

**Solution:**
```bash
# Check SSH works
ssh root@172.105.48.142 "echo ok"

# Test push.sh directly
bash scripts/push.sh "test: verify ssh"
```

---

## 📊 Git Commands Cheat Sheet

```bash
# SEE WHAT CHANGED
git status              # What files changed
git diff                # Exact changes
git log --oneline -10   # Recent commits

# STAGE & COMMIT (push.sh does this)
git add -A              # Stage all changes
git commit -m "message" # Create commit
git push origin main    # Push to GitHub

# PULL FROM GITHUB
git pull origin main    # Get latest code

# MOVE & DELETE FILES
git mv old_path new_path    # Rename/move (correct!)
git rm filename             # Delete (correct!)

# UNDO CHANGES
git checkout -- file    # Undo edits
git reset HEAD file     # Unstage file
git reset --soft HEAD~1 # Undo commit, keep changes
git reset --hard HEAD~1 # Undo commit, discard changes
```

---

## 🎯 Deployment Checklist

Before pushing:
- [ ] Changes are tested in UAT
- [ ] File moves use `git mv` (not `mv`)
- [ ] File deletions use `git rm` (not `rm`)
- [ ] Commit message is descriptive

After pushing:
- [ ] Run `bash scripts/prod_status.sh`
- [ ] Check HTTP Status is 200
- [ ] Verify feature in browser
- [ ] Check logs for errors

---

## 📞 Need Help?

| Topic | File |
|-------|------|
| Complete guide | GIT_MASTER_GUIDE.md |
| Detailed workflow | GIT_USAGE_GUIDE.md |
| File sync details | FILE_SYNCHRONIZATION_REFERENCE.md |
| Script navigation | GIT_PUSH_PULL_SCRIPTS_INDEX.md |
| This session | GIT_DOCUMENTATION_COMPLETION_SUMMARY.md |

All files are in: `/opt/miguel/`

---

## 🚀 First Deployment (5 Minutes)

```bash
# 1. Make a test change (1 min)
echo "# Test" >> README.md

# 2. Deploy (2 min)
bash scripts/push.sh "test: first deployment"

# 3. Verify (2 min)
bash scripts/prod_status.sh | grep HTTP

# Expected output:
# HTTP Status: 200 ✅
```

Done! Your changes are live!

---

## 💾 Git Commit Message Format

```
<type>: <description>

Types: feat, fix, docs, refactor, perf, chore

Examples:
feat: add customer report feature
fix: resolve order calculation bug
docs: update deployment guide
refactor: reorganize backend modules
```

---

## 🎓 Key Concepts

**Repository Flow:**
```
Your Changes in UAT
      ↓
git add -A (stage all)
      ↓
git commit (create commit)
      ↓
git push (send to GitHub)
      ↓
GitHub has your changes
      ↓
git pull on Production (gets your changes)
      ↓
✅ Production Updated!
```

**File Sync Guarantee:**
- All code: ✅
- All docs: ✅
- All config: ✅
- Cache/secrets: ❌ (intentional)

---

## 📱 Copy These Commands

```bash
# Deploy
bash scripts/push.sh "your message"

# Verify  
bash scripts/prod_status.sh

# Check git
git status
git log --oneline -5

# Safe file ops
git mv old new
git rm file

# Manual pull
bash scripts/pull_to_prod.sh
```

---

**Last Updated:** February 27, 2026  
**Status:** ✅ Production Ready  
**Sync Status:** Perfect (UAT = Prod = GitHub)

Print this card or bookmark it!
