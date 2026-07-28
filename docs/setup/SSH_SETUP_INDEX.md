# SSH Production Setup - Complete Index

> **Status:** ✅ SSH SETUP COMPLETE & READY  
> **Date:** February 26, 2026

---

## 🎯 Quick Start

**You are here:** SSH keys are generated and ready.

**Next step:** Add 6 GitHub Secrets to enable automated deployments.

📄 **File to use:** `GITHUB_SECRETS_COPY_PASTE.md` (copy-paste all secrets)

🔗 **GitHub link:** https://github.com/purelevenexim-ai/crm/settings/secrets/actions

---

## 📋 SSH Key Files

| File | Location | Purpose | Status |
|------|----------|---------|--------|
| UAT Private Key | `/root/.ssh/uat` | For GitHub to deploy to UAT | ✅ Ready |
| UAT Public Key | `/root/.ssh/uat.pub` | For UAT authorized_keys | ✅ Added |
| Prod Private Key | `/root/.ssh/prod` | For GitHub to deploy to Prod | ✅ Ready |
| Prod Public Key | `/root/.ssh/prod.pub` | For Prod authorized_keys | ✅ Ready |
| All Public Keys | `/root/.ssh/authorized_keys` | UAT server SSH access | ✅ Added |

---

## 📚 Documentation Files

### 1. **For Adding GitHub Secrets (START HERE)**

📄 **File:** `GITHUB_SECRETS_COPY_PASTE.md`

**Contains:**
- 6 secrets ready to copy-paste
- Step-by-step instructions
- Names and values for all secrets

**Use this file:** Open on your computer, copy values, paste into GitHub Secrets

---

### 2. **Detailed Setup Guide**

📄 **File:** `GITHUB_SECRETS_SETUP.md`

**Contains:**
- Explanation of what each secret does
- How the CI/CD pipeline works
- Testing instructions
- Troubleshooting guide

**Use this file:** When you need to understand what's happening

---

### 3. **Complete Reference**

📄 **File:** `SSH_SETUP_COMPLETE.md`

**Contains:**
- Full setup summary
- SSH key details
- Workflow triggers
- Security notes
- Current setup status

**Use this file:** As your complete reference guide

---

### 4. **Quick Command Reference**

📄 **File:** `scripts/ssh-commands-reference.sh`

**Contains:**
- Quick SSH connection commands
- Docker commands for remote servers
- Database backup paths
- Quick reference tables

**Use this file:** `bash scripts/ssh-commands-reference.sh`

---

### 5. **Production Server Bootstrap**

📄 **File:** `scripts/setup-ssh-prod.sh`

**Contains:**
- Step-by-step guide for production server setup
- System installation commands
- SSH key placement instructions

**Use this file:** When setting up a fresh production server

---

## 🔑 SSH Keys Quick Reference

### UAT Server (172.232.118.208)

```bash
# SSH fingerprint
SHA256:2t7o6sHPpcVg6hGbM8imBCCCyjYjc7tyENTNyjtjlyU (ed25519)

# Connect from UAT server
ssh -i /root/.ssh/uat root@172.232.118.208

# Private key for GitHub Secret
cat /root/.ssh/uat
```

### Production Server (172.105.48.142)

```bash
# SSH fingerprint
SHA256:jK3X0348HRDU7EQ+CeV4GMhuO5dJyQf9GlkgbdXJD/I (ed25519)

# Connect from UAT server
ssh -i /root/.ssh/prod root@172.105.48.142

# Private key for GitHub Secret
cat /root/.ssh/prod
```

---

## 🚀 Deployment Workflow

### After GitHub Secrets are Added

```
┌─────────────────────────────────────────────────────────┐
│  1. You push code to GitHub                             │
│     git push origin uat                                 │
│                                                         │
│  2. GitHub Actions triggered automatically              │
│     Uses: UAT_SSH_HOST, UAT_SSH_USER, UAT_SSH_KEY      │
│                                                         │
│  3. SSH to UAT server & deploy                          │
│     cd /opt/miguel                                      │
│     docker compose up -d --build                        │
│     docker exec miguel_backend alembic upgrade head    │
│                                                         │
│  4. View logs in GitHub Actions tab                     │
│     https://github.com/purelevenexim-ai/crm/actions   │
└─────────────────────────────────────────────────────────┘

Same process for:
  - Push to 'main' → deploys to Production (172.105.48.142)
```

---

## ✅ Setup Checklist

- [x] SSH key pairs generated (uat & prod)
- [x] SSH keys tested and working
- [x] Public keys added to authorized_keys
- [x] All documentation created
- [x] Code pushed to GitHub
- [x] Workflows updated with correct paths
- [ ] **TODO: Add 6 GitHub Secrets** ← You are here
- [ ] Test deployments (after secrets added)
- [ ] (Optional) Set up DNS records
- [ ] (Optional) Install SSL certificates

---

## 🎓 How It All Works

### GitHub Actions Pipeline

1. **Developer pushes code**
   ```bash
   git push origin uat
   ```

2. **GitHub Actions triggered** (via `.github/workflows/deploy-uat.yml`)

3. **Reads 6 GitHub Secrets**
   - `UAT_SSH_HOST` = 172.232.118.208
   - `UAT_SSH_USER` = root
   - `UAT_SSH_KEY` = [private key from /root/.ssh/uat]
   - (+ 3 similar for Production)

4. **SSHes into server using the private key**
   ```bash
   ssh -i <UAT_SSH_KEY> root@<UAT_SSH_HOST>
   ```

5. **Runs deployment commands**
   ```bash
   cd /opt/miguel
   git pull origin uat
   docker compose up -d --build
   docker exec miguel_backend alembic upgrade head
   ```

6. **Logs available in GitHub Actions tab**

---

## 🔒 Security Notes

- Private keys in `/root/.ssh/uat` and `/root/.ssh/prod` are SENSITIVE
- Never commit private keys to Git
- Private keys only go in GitHub Secrets (encrypted at rest)
- Public keys in `authorized_keys` are safe
- Rotate keys every 90 days
- GitHub Actions logs are readable by repo members

---

## 📞 Troubleshooting

### "Permission denied (publickey)" in GitHub Actions

**Cause:** GitHub Secrets not added, or public key not in authorized_keys

**Fix:**
1. Verify all 6 GitHub Secrets are added
2. Check public keys in `/root/.ssh/authorized_keys`
3. Test SSH manually: `ssh -i /root/.ssh/uat root@172.232.118.208`

### Deployment succeeds but containers don't start

**Cause:** `.env` file missing or invalid

**Fix:**
1. Check `.env` exists: `cat /opt/miguel/.env`
2. Verify all required variables are set
3. Check logs: `docker logs miguel_backend`

### SSH connection timeout

**Cause:** Server down or firewall blocking port 22

**Fix:**
1. Test server reachability: `ping 172.232.118.208`
2. Test port 22: `nc -zv 172.232.118.208 22`
3. Check server status

---

## 📊 Setup Status

| Task | Status |
|------|--------|
| Generate SSH keys | ✅ Complete |
| Test SSH connections | ✅ Complete |
| Add public keys to authorized_keys | ✅ Complete |
| Create documentation | ✅ Complete |
| Push to GitHub | ✅ Complete |
| Update GitHub Actions workflows | ✅ Complete |
| **Add GitHub Secrets** | ⏳ TODO |
| Setup Production server | ⏳ TODO |
| Setup DNS records | ⏳ TODO |
| Setup SSL certificates | ⏳ TODO |

---

## 🎯 Next Steps

### Step 1: Add GitHub Secrets (5 minutes)
- Open: https://github.com/purelevenexim-ai/crm/settings/secrets/actions
- File: `GITHUB_SECRETS_COPY_PASTE.md`
- Add all 6 secrets

### Step 2: Test Deployment (2 minutes)
- Push a small change to 'uat' branch
- Watch GitHub Actions execute
- View logs and verify deployment

### Step 3: (Optional) Setup Production Server
- SSH into 172.105.48.142
- Add production public key to authorized_keys
- Create .env file
- Start containers

### Step 4: (Optional) Setup Domains & SSL
- Add DNS A records
- Run Certbot for SSL certificates
- Configure Nginx

---

## 📞 Questions?

All answers are in these files:
- `GITHUB_SECRETS_COPY_PASTE.md` — For adding secrets
- `SSH_SETUP_COMPLETE.md` — For complete reference
- `GITHUB_SECRETS_SETUP.md` — For detailed explanations

---

**Created:** February 26, 2026  
**SSH Keys:** ED25519 2048-bit  
**Status:** ✅ Ready for deployment
