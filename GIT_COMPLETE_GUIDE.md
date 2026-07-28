# Complete Git Usage and Deployment Guide

## 📚 Documentation Overview

This workspace now includes comprehensive Git usage documentation to ensure perfect synchronization between UAT and Production environments.

### 📖 Available Guides

1. **GIT_USAGE_GUIDE.md** (This File)
   - User-friendly guide for everyday Git operations
   - Common scenarios and workflows
   - Quick reference for developers
   - Troubleshooting tips

2. **GIT_WORKFLOW_DOCUMENTATION.md**
   - Technical architecture overview
   - Detailed workflow diagrams
   - Real-world scenarios with examples
   - Advanced Git operations
   - Verification procedures

3. **FILE_ORGANIZATION_COMPLETE.md**
   - File structure overview
   - How files are organized in the workspace
   - What each folder contains

4. **DEPLOYMENT_WORKFLOW_GUIDE.md**
   - Step-by-step deployment procedures
   - Rollback instructions
   - Production verification checklist

---

## 🚀 Quick Start

### Your First Deployment

1. **Make changes on UAT** (`/opt/miguel`):
   ```bash
   vim backend/app/modules/orders/service.py
   # Edit your code...
   ```

2. **Test locally**:
   ```bash
   curl http://localhost:8000/docs  # Should return 200
   ```

3. **Deploy to Production** (ONE command):
   ```bash
   bash scripts/push.sh "fix: resolve order status calculation"
   ```

4. **Verify Production**:
   ```bash
   bash scripts/prod_status.sh
   ```

**That's it!** Your changes are now live.

---

## 📋 Essential Commands

### Checking What Changed
```bash
git status          # See what files changed
git diff            # See exact changes in files
git log -1          # See your latest commit
```

### Staging & Committing
```bash
git add -A          # Stage ALL changes
git commit -m "your message"  # Commit with message
git push origin main  # Push to GitHub
```

### Deployment
```bash
bash scripts/push.sh "message"      # Deploy everything
bash scripts/prod_status.sh         # Check production
bash scripts/rollback.sh            # Rollback if needed
```

### File Operations (IMPORTANT!)
```bash
# ✅ CORRECT
git mv old_path/file.py new_path/file.py  # Move file with git
git rm file_path.py                        # Delete file with git

# ❌ WRONG
mv old_path/file.py new_path/file.py      # Don't use manual mv
rm file_path.py                            # Don't use manual rm
```

---

## 🔄 Complete Workflow

### Phase 1: Development (UAT)
```
┌─────────────────────────────────────┐
│ /opt/miguel (UAT Server)            │
├─────────────────────────────────────┤
│ 1. Edit code files                  │
│ 2. Create new features/documents    │
│ 3. Move/organize files (git mv)     │
│ 4. Test locally                     │
└─────────────────────────────────────┘
         ↓ (When ready to deploy)
```

### Phase 2: Commit & Push
```
┌─────────────────────────────────────┐
│ Git Local Repo (/opt/miguel/.git)   │
├─────────────────────────────────────┤
│ 1. git add -A                       │
│ 2. git commit -m "message"          │
│ 3. git push origin main             │
└─────────────────────────────────────┘
         ↓ (Upload to GitHub)
```

### Phase 3: GitHub Storage
```
┌─────────────────────────────────────────────────────┐
│ GitHub Repository (origin/main)                     │
├─────────────────────────────────────────────────────┤
│ • Stores all code history                           │
│ • Single source of truth                            │
│ • Accessible to all environments                    │
│ • Shows all commits with timestamps                 │
└─────────────────────────────────────────────────────┘
         ↓ (Pull latest)
```

### Phase 4: Production Deployment
```
┌──────────────────────────────────────┐
│ /opt/pureleven (Production Server)   │
├──────────────────────────────────────┤
│ 1. git pull origin main              │
│ 2. docker restart pureleven_backend  │
│ 3. API starts serving changes        │
│ 4. Users see updates                 │
└──────────────────────────────────────┘
         ↓
   🟢 LIVE FOR USERS ✅
```

---

## ✅ What Gets Synced (Automatically!)

### Code & Configuration
- ✅ All Python files (backend/app/modules/)
- ✅ All HTML/CSS files (frontend/)
- ✅ Docker Compose configs (config/)
- ✅ Nginx configs (infra/)
- ✅ Test files (tests/)

### Documentation
- ✅ All Markdown files (.md)
- ✅ Setup guides
- ✅ Deployment procedures
- ✅ API documentation
- ✅ Troubleshooting guides

### File Changes
- ✅ New files you create
- ✅ New folders you create
- ✅ Files moved with `git mv`
- ✅ Files deleted with `git rm`
- ✅ All modifications to existing files

### NOT Synced (Excluded)
- ❌ `__pycache__` directories
- ❌ `*.pyc` compiled files
- ❌ `.env` files (secrets)
- ❌ `*.log` files
- ❌ `venv/` directories
- ❌ Local system files (.DS_Store)

---

## 📊 Deployment Scripts

All scripts are pre-configured and ready to use. They're located in `/opt/miguel/scripts/`.

### push.sh - Main Deployment
```bash
bash scripts/push.sh "your commit message"
```

**Does:**
1. ✅ Stages all your changes (`git add -A`)
2. ✅ Creates a commit with your message
3. ✅ Pushes to GitHub
4. ✅ Deploys to Production server
5. ✅ Restarts backend container
6. ✅ Verifies API is responding

**Output shows:**
- Phase 1: Your changes
- Phase 2: Staging details
- Phase 3: GitHub push confirmation
- Phase 4: Production deployment
- Phase 5: Health check (HTTP 200 = success)

### prod_status.sh - Check Production
```bash
bash scripts/prod_status.sh
```

**Shows:**
- Latest commits on production
- Docker container status
- API health check
- Recent backend logs
- Overall system health

### rollback.sh - Undo Last Deploy
```bash
bash scripts/rollback.sh
```

**Does:**
- Reverts to previous git commit
- Restarts backend
- Verifies everything is working

### pull_to_prod.sh - Manual Pull
```bash
bash scripts/pull_to_prod.sh
```

**For:**
- Emergency pulls
- Manual synchronization
- Testing pull procedures

---

## 🔍 Verification Steps

### Before Deploying
```bash
# 1. See what you're deploying
git status
git diff

# 2. Test on UAT
curl http://localhost:8000/docs

# 3. Review your commits
git log -2 --oneline
```

### After Deploying
```bash
# 1. Run full deployment
bash scripts/push.sh "your message"

# 2. Check production status
bash scripts/prod_status.sh

# 3. Verify commit on production
ssh root@172.105.48.142 "cd /opt/pureleven && git log --oneline -1"
# Should match your commit hash

# 4. Test production API
curl http://172.105.48.142:8000/docs
# Should return HTTP 200
```

---

## 🎯 Real-World Examples

### Example 1: Fix a Bug

```bash
# 1. Edit the file
vim backend/app/modules/orders/service.py
# Make your fix...

# 2. Test on UAT
curl http://localhost:8000/docs

# 3. Deploy
git add -A
git commit -m "fix: resolve order status calculation in service.py"
bash scripts/push.sh "fix: resolve order status calculation"

# 4. Verify on production
bash scripts/prod_status.sh
curl http://172.105.48.142:8000/docs
```

### Example 2: Add New Endpoint

```bash
# 1. Create new module
mkdir -p backend/app/modules/invoicing
touch backend/app/modules/invoicing/{__init__.py,router.py,service.py}

# 2. Write code
vim backend/app/modules/invoicing/router.py
# Add your endpoints...

# 3. Register in main.py
vim backend/app/main.py
# Add: from app.modules.invoicing.router import router
# Add: app.include_router(router)

# 4. Test on UAT
curl http://localhost:8000/docs

# 5. Deploy
git add backend/app/modules/invoicing/
git add backend/app/main.py
git commit -m "feat: add invoicing module with CRUD endpoints"
bash scripts/push.sh "feat: add invoicing module"

# Production now has your complete new module!
```

### Example 3: Update Documentation

```bash
# 1. Edit markdown file
vim docs/SETUP_GUIDE.md
# Update documentation...

# 2. Deploy
git add docs/SETUP_GUIDE.md
git commit -m "docs: update setup guide with new steps"
bash scripts/push.sh "docs: update setup guide"

# Documentation is updated on production immediately!
```

### Example 4: Reorganize Files

```bash
# 1. Move files CORRECTLY (use git mv!)
git mv README.md documentation/guides/README.md
git mv SETUP.md documentation/guides/SETUP.md

# 2. Verify staging
git status

# 3. Commit
git commit -m "chore: reorganize documentation files"

# 4. Deploy
bash scripts/push.sh "chore: reorganize documentation"

# Production will have files in NEW locations only!
```

---

## ⚠️ Common Mistakes & Solutions

### ❌ Mistake 1: Using manual `mv` instead of `git mv`

```bash
# WRONG
mv old_path/file.py new_path/file.py
git add -A
git push origin main
# Problem: Production will have BOTH old and new locations!
```

**Solution**: Always use `git mv`:
```bash
# CORRECT
git mv old_path/file.py new_path/file.py
git add -A
git push origin main
# Result: Production will have file in NEW location only
```

### ❌ Mistake 2: Editing files directly on Production

```bash
# WRONG
ssh root@172.105.48.142
vim /opt/pureleven/backend/app/main.py
# Changes won't sync back to UAT, lost when next deploy happens!
```

**Solution**: Always edit on UAT, then deploy:
```bash
# CORRECT
vim /opt/miguel/backend/app/main.py
bash scripts/push.sh "fix: update main.py"
# Changes sync to production automatically
```

### ❌ Mistake 3: Pushing without testing

```bash
# WRONG
git add -A
git commit -m "update"
git push origin main
# What if there's a bug? Production is broken!
```

**Solution**: Test on UAT first:
```bash
# CORRECT
# Test on UAT
curl http://localhost:8000/docs
# Then deploy
bash scripts/push.sh "your message"
```

---

## 🆘 Troubleshooting

### Problem: "Changes not appearing on production"

**Step 1**: Check production's git log
```bash
ssh root@172.105.48.142 "cd /opt/pureleven && git log --oneline -1"
```

**Step 2**: Compare with your UAT
```bash
git log --oneline -1
```

**Step 3**: If they don't match, manually pull
```bash
ssh root@172.105.48.142 "cd /opt/pureleven && git pull origin main && docker restart pureleven_backend"
```

### Problem: "API not responding after deploy"

**Step 1**: Check container status
```bash
ssh root@172.105.48.142 "docker ps | grep pureleven"
```

**Step 2**: Check backend logs
```bash
ssh root@172.105.48.142 "docker logs pureleven_backend --tail 50"
```

**Step 3**: Restart backend
```bash
ssh root@172.105.48.142 "docker restart pureleven_backend"
sleep 5
curl http://172.105.48.142:8000/docs
```

### Problem: "SSH key authentication failed"

**Solution**:
```bash
# Test GitHub authentication
ssh -T git@github.com
# Should say: "Hi [username]! You've successfully authenticated..."

# Test production SSH
ssh root@172.105.48.142
# Should connect without password
```

### Problem: "merge conflicts"

**Prevention**: Pull before starting work
```bash
git pull origin main  # Get latest from GitHub
# Then start editing
```

**Solution if it happens**:
```bash
git status  # See conflicting files
# Edit the files and resolve conflicts
git add -A
git commit -m "fix: resolve merge conflicts"
git push origin main
```

---

## 📈 Best Practices

### ✅ DO

1. **Use descriptive commit messages**
   ```bash
   ✅ git commit -m "fix: resolve order calculation bug"
   ✅ git commit -m "feat: add invoicing module"
   ✅ git commit -m "docs: update deployment guide"
   ```

2. **Test on UAT before deploying**
   ```bash
   curl http://localhost:8000/docs
   docker logs miguel_backend | tail 20
   ```

3. **Commit frequently**
   - Small, logical commits
   - Easy to understand and debug
   - Easy to rollback if needed

4. **Use `git mv` for file operations**
   ```bash
   git mv old_path new_path
   git rm file_to_delete
   ```

5. **Keep .env files out of Git**
   - Already in .gitignore
   - Never commit secrets or passwords
   - Set sensitive vars directly on servers

### ❌ DON'T

1. **Don't use vague commit messages**
   ```bash
   ❌ git commit -m "update"
   ❌ git commit -m "fix bug"
   ❌ git commit -m "WIP"
   ```

2. **Don't push untested code**
   - Test on UAT first
   - Verify logs for errors
   - Check API responds

3. **Don't edit files directly on production**
   - Always work on UAT
   - Use git push for deployment
   - Changes get lost on next deploy

4. **Don't use manual `mv` or `rm`**
   - Use `git mv` and `git rm`
   - Git tracks changes correctly
   - Syncs perfectly to production

5. **Don't commit large binary files**
   - Git stores all versions in history
   - Repository gets bloated
   - Slows down clone/fetch operations

---

## 📞 Support & Help

### Available Documentation
- `GIT_USAGE_GUIDE.md` - Quick reference for developers
- `GIT_WORKFLOW_DOCUMENTATION.md` - Technical deep dive
- `FILE_ORGANIZATION_COMPLETE.md` - File structure
- `DEPLOYMENT_WORKFLOW_GUIDE.md` - Deployment procedures

### Quick Command Reference
```bash
# View this file
cat GIT_USAGE_GUIDE.md

# View workflow documentation
cat GIT_WORKFLOW_DOCUMENTATION.md

# Check production status
bash scripts/prod_status.sh

# View recent commits
git log --oneline -10
```

---

## ✨ Summary

### Your Workflow
```
Edit Code (UAT)
    ↓
Test on UAT
    ↓
bash scripts/push.sh "message"
    ↓
✅ Changes are LIVE on Production
```

### Key Rules
- ✅ Use `git mv` for file moves
- ✅ Use `bash scripts/push.sh` for deployment
- ✅ Test on UAT before deploying
- ✅ Check production with `bash scripts/prod_status.sh`

### Your Commands
```bash
# Deploy
bash scripts/push.sh "your message"

# Check status
bash scripts/prod_status.sh

# Rollback
bash scripts/rollback.sh
```

---

**Status**: ✅ Git workflow fully configured and documented
**Last Updated**: February 27, 2026
**Commit**: 3a4df20 (GIT documentation added)

🚀 **You're ready to deploy with confidence!**
