# PureLeven CRM - Project Root Index

**Last Updated:** February 26, 2026  
**Environments:** UAT (172.232.118.208) | Production (172.105.48.142)  
**Repository:** https://github.com/purelevenexim-ai/crm

---

## 📁 Project Structure

### Core Application Files
- `backend/` - FastAPI application, migrations, database models
- `frontend/` - React frontend application
- `tests/` - Unit and integration tests
- `.github/` - GitHub Actions CI/CD workflows
- `.git/` - Git repository

### Configuration Files
- `docker-compose.yml` - Container orchestration (UAT)
- `docker-compose.prod.yml` - Production configuration template
- `.env.example` - Environment variables template
- `.gitignore` - Git ignore rules

### Documentation (Quick Links)

#### 🚀 Getting Started
- `QUICK_REFERENCE.md` - Quick start guide
- `docs/setup/PRODUCTION_SETUP_COMPLETE.md` - Full setup guide
- `docs/setup/SSH_SETUP_COMPLETE.md` - SSH configuration
- `docs/setup/GITHUB_SECRETS_SETUP.md` - CI/CD configuration

#### 🔧 Deployment
- `docs/deployment/DEPLOYMENT_GUIDE.md` - How to deploy
- `docs/deployment/PRODUCTION_DEPLOYMENT_TOKENS.md` - Credentials reference
- `.github/workflows/` - Automated deployment pipelines

#### 📚 Features & Implementation
- `docs/features/SHOPIFY*.md` - Shopify integration
- `docs/features/PARTIAL_COD*.md` - Cash on Delivery system
- `docs/features/ORDER*.md` - Order management
- `docs/features/PAYMENT*.md` - Payment processing

#### 🐛 Troubleshooting
- `docs/troubleshooting/` - Debugging guides and fixes
- `REMAINING_TASKS.md` - Outstanding issues

#### 📖 API Reference
- `docs/api/API_QUICK_REFERENCE.md` - API endpoints

---

## 🚀 Quick Commands

### Connect to Servers
```bash
ssh uat          # UAT server (172.232.118.208)
ssh prod         # Production server (172.105.48.142)
```

### Container Management
```bash
docker-compose ps                    # Check running containers
docker-compose logs -f backend       # View backend logs
docker-compose restart backend       # Restart backend
docker-compose up -d                 # Start all services
docker-compose down                  # Stop all services
```

### Database
```bash
docker-compose exec db psql -U miguel_user -d miguel_db  # Connect to DB
```

### Git Operations
```bash
git status                           # Check status
git checkout uat                     # Switch to UAT branch
git checkout main                    # Switch to main branch
git pull origin uat                  # Update from remote
```

---

## 📊 Environment Details

### UAT (172.232.118.208)
- **Branch:** uat
- **Location:** `/opt/miguel`
- **Database:** miguel_db (user: miguel_user)
- **Domain:** uat.pureleven.com
- **Status:** ✅ Active

### Production (172.105.48.142)
- **Branch:** main
- **Location:** `/opt/pureleven`
- **Database:** pureleven_db (user: pureleven_user)
- **Domain:** prod.pureleven.com
- **Status:** ✅ Active

---

## 🔐 Security

- SSH keys in `~/.ssh/uat` and `~/.ssh/prod`
- SSL certificates via Let's Encrypt
- Environment variables in `.env` (not in git)
- GitHub Secrets for CI/CD automation

---

## 📝 Important Files

| File | Purpose |
|------|---------|
| `README.md` | Project overview |
| `QUICK_REFERENCE.md` | Quick start commands |
| `FINAL_CHECKLIST.md` | Deployment checklist |
| `REMAINING_TASKS.md` | Outstanding work items |
| `FINAL_SETUP_COMPLETE.txt` | Setup completion summary |

---

## 🔄 Git Workflow

```
main (Production)
  ↑
  └─ uat (Staging/UAT)
      ↑
      └─ dev (Development)
```

**Push flow:** `dev` → `uat` (test) → `main` (production)

---

## 🆘 Support

For common issues, see:
- `QUICK_REFERENCE.md` - Quick commands
- `docs/troubleshooting/` - Detailed debugging guides
- `REMAINING_TASKS.md` - Known issues and solutions

---

**Generated on:** February 26, 2026
