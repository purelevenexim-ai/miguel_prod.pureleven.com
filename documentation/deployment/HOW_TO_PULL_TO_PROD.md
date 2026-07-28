# 📥 HOW TO PULL TO PRODUCTION - Complete Guide

## Quick Answer: Pull Latest Code to Production

You have **3 ways** to pull code to production:

---

## **Option 1: From UAT Machine (Recommended for Automation)**

From `/opt/miguel`, the `push.sh` script automatically pulls on production:

```bash
bash scripts/push.sh "your commit message"
```

This **automatically**:
- Commits changes on UAT
- Pushes to GitHub
- SSHes to production
- Pulls latest code
- Restarts backend
- Verifies all services

**This is your default workflow** - one command does everything.

---

## **Option 2: Manual Pull on Production Server**

SSH to production and pull manually:

```bash
ssh root@172.105.48.142

cd /opt/pureleven
bash scripts/pull_to_prod.sh
```

What this does:
- Fetches latest from origin/main
- Cleans local cache files
- Pulls code if updates available
- Restarts backend container
- Verifies API is responding

---

## **Option 3: From UAT, Trigger Pull on Production**

From UAT machine, manually SSH to production and pull:

```bash
ssh root@172.105.48.142 "cd /opt/pureleven && bash scripts/pull_to_prod.sh"
```

This is equivalent to Option 2 but runs from UAT in one command.

---

## All Available Production Scripts

Once on production server (`/opt/pureleven`):

### **1. Pull Code + Restart Backend**
```bash
bash scripts/pull_to_prod.sh
```
Most comprehensive - pulls code, restarts, verifies.

### **2. Fast Deploy (One-liner)**
```bash
bash scripts/quick_deploy.sh
```
Fast version: pull + restart, minimal output.

### **3. Restart Backend Only**
```bash
bash scripts/restart_backend.sh
```
Restart without pulling code (useful if code already pulled).

### **4. Check Production Health**
```bash
bash scripts/check_status.sh
```
Shows git commit, container status, API health, recent logs.

### **5. Watch Live Logs**
```bash
bash scripts/watch_logs.sh
```
Tail backend logs in real-time (Ctrl+C to exit).

### **6. View Command Reference**
```bash
cat scripts/README_PROD.md
```
Complete reference of all commands.

---

## Step-by-Step: Pull Code to Production

### **Scenario 1: You made changes on UAT, want to deploy**

```bash
# On UAT machine (/opt/miguel)
bash scripts/push.sh "fix: bug description"

# This automatically pulls on production
# Done! ✅
```

### **Scenario 2: You're on production server, want to pull latest**

```bash
# On production server (/opt/pureleven)
bash scripts/pull_to_prod.sh

# Or quick version:
bash scripts/quick_deploy.sh
```

### **Scenario 3: Code was pulled but backend crashed, restart it**

```bash
# On production server
bash scripts/restart_backend.sh

# Or check what happened:
bash scripts/watch_logs.sh
```

### **Scenario 4: Check if production has latest code**

```bash
# On production server
bash scripts/check_status.sh

# Or from UAT:
bash scripts/prod_status.sh
```

---

## Raw Git Commands (If You Need Direct Control)

On production server:

```bash
# Check current commit
git log --oneline -1

# Check if updates available
git fetch origin
git log --oneline -10  # See what's available on origin/main

# Pull manually
git pull origin main

# Restart backend after pull
docker restart pureleven_backend
```

---

## Automated Cron Job (Optional)

If you want production to **auto-pull** every hour:

```bash
# On production server, add to crontab:
crontab -e

# Add this line:
0 * * * * cd /opt/pureleven && bash scripts/quick_deploy.sh >> /var/log/prod_deploy.log 2>&1
```

This runs `quick_deploy.sh` every hour at :00 minutes.

---

## Troubleshooting

### Backend won't start after pull
```bash
# Check logs
docker logs pureleven_backend | tail -100

# If syntax error in code, fix on UAT and push again
bash scripts/push.sh "fix: correct syntax error"
```

### API returns 500 error
```bash
# Watch real-time logs
bash scripts/watch_logs.sh

# Look for error messages, fix on UAT, push again
```

### Need to see what changed in latest pull
```bash
# On production
git log --oneline -5

# See diff between commits
git diff <old-commit> <new-commit>

# Or see recent changes
git log -p -1  # Shows last commit's changes
```

### Want to rollback to previous code
```bash
# Option A: Using rollback script from UAT
bash scripts/rollback.sh

# Option B: Manual on production
git log --oneline -10  # Find the commit
git reset --hard <commit-hash>
docker restart pureleven_backend
```

---

## Summary

| Task | Command | Location |
|------|---------|----------|
| **Deploy code from UAT** | `bash scripts/push.sh "msg"` | UAT machine |
| **Pull code manually** | `bash scripts/pull_to_prod.sh` | Production |
| **Quick pull** | `bash scripts/quick_deploy.sh` | Production |
| **Check health** | `bash scripts/check_status.sh` | Production |
| **Watch logs** | `bash scripts/watch_logs.sh` | Production |
| **Check prod from UAT** | `bash scripts/prod_status.sh` | UAT machine |
| **Rollback** | `bash scripts/rollback.sh` | UAT machine |

---

## Your Daily Workflow

1. **Make changes on UAT** - test locally
2. **Push to production** - `bash scripts/push.sh "message"`
3. **Verify** - `bash scripts/prod_status.sh`
4. **If needed, rollback** - `bash scripts/rollback.sh`

That's it! 🚀
