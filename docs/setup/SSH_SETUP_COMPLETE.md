# SSH Production Setup - Complete Summary

## ✅ What's Done

### SSH Keys Generated
- ✅ **UAT SSH Key Pair** created at `/root/.ssh/uat`
- ✅ **Production SSH Key Pair** created at `/root/.ssh/prod`
- ✅ Public keys added to `/root/.ssh/authorized_keys`
- ✅ SSH connection tested and working

### Documentation Created
- ✅ `GITHUB_SECRETS_COPY_PASTE.md` — Copy-paste ready secrets
- ✅ `GITHUB_SECRETS_SETUP.md` — Detailed setup guide
- ✅ `scripts/setup-ssh-prod.sh` — Step-by-step prod setup
- ✅ `scripts/ssh-commands-reference.sh` — Quick reference

### GitHub Configuration Ready
- ✅ All code pushed to `uat` branch
- ✅ Workflows updated with correct paths and container names
- ✅ Ready for 6 GitHub Secrets to be added

---

## 🎯 Your Next Step: Add GitHub Secrets

### Quick Links
1. **Add Secrets Here:** https://github.com/purelevenexim-ai/crm/settings/secrets/actions
2. **Copy Values From:** `/opt/miguel/GITHUB_SECRETS_COPY_PASTE.md`

### 6 Secrets to Add

| # | Secret Name | Value |
|---|-------------|-------|
| 1 | `UAT_SSH_HOST` | `172.232.118.208` |
| 2 | `UAT_SSH_USER` | `root` |
| 3 | `UAT_SSH_KEY` | [UAT private key from file] |
| 4 | `PROD_SSH_HOST` | `172.105.48.142` |
| 5 | `PROD_SSH_USER` | `root` |
| 6 | `PROD_SSH_KEY` | [Prod private key from file] |

### How to Add (per secret)
1. Go to GitHub Secrets page (link above)
2. Click **"New repository secret"**
3. Copy secret name → paste in "Name" field
4. Copy secret value → paste in "Value" field
5. Click **"Add secret"**
6. Repeat for all 6 secrets

---

## 🔑 SSH Key Locations on UAT Server

```bash
# View the keys (for reference only, not to copy manually)
cat /root/.ssh/uat        # UAT private key (for GitHub)
cat /root/.ssh/uat.pub    # UAT public key (already in authorized_keys)
cat /root/.ssh/prod       # Prod private key (for GitHub)
cat /root/.ssh/prod.pub   # Prod public key (ready to add to Prod server)
```

---

## 🧪 Test SSH Connections

After setting up the Production server with the public key, test from UAT:

```bash
# Test UAT-to-UAT SSH
ssh -i /root/.ssh/uat root@172.232.118.208 'whoami'
# Expected output: root

# Test UAT-to-Prod SSH
ssh -i /root/.ssh/prod root@172.105.48.142 'whoami'
# Expected output: root
```

---

## 📋 Workflow Triggers (Automatic after GitHub Secrets)

### UAT Deployment Trigger
```bash
git checkout uat
git merge dev
git push origin uat
# → Automatically deploys to 172.232.118.208:/opt/miguel
# → Workflow: .github/workflows/deploy-uat.yml
# → View logs: GitHub Actions tab
```

### Production Deployment Trigger
```bash
git checkout main
git merge uat
git push origin main
# → Automatically deploys to 172.105.48.142:/opt/pureleven
# → Workflow: .github/workflows/deploy-prod.yml
# → View logs: GitHub Actions tab
```

---

## 📁 Project Structure

### UAT Server (172.232.118.208)
```
/opt/miguel/
├── docker-compose.yml (uses miguel_* container names)
├── .env (NOT IN GIT - you must create manually)
├── frontend/
├── backend/
├── alembic/
└── ... (rest of project)
```

### Production Server (172.105.48.142)
```
/opt/pureleven/
├── docker-compose.prod.yml (uses pureleven_* container names)
├── .env (NOT IN GIT - you must create manually)
├── frontend/
├── backend/
├── alembic/
└── ... (rest of project)
```

---

## 🚨 Important Pre-Production Tasks

### Before Adding GitHub Secrets (Optional but Recommended)

1. **SSH into Production Server & Add Public Key** (if server already exists)
   ```bash
   ssh root@172.105.48.142
   mkdir -p ~/.ssh
   chmod 700 ~/.ssh
   # Paste this into authorized_keys:
   # ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIF8dlSG1o5McmnmzGfe40oRCtuIe5OWvX5yL+bZSXcU9 prod-172.105.48.142
   ```

2. **Create `.env` on Production Server**
   ```bash
   scp /opt/miguel/.env root@172.105.48.142:/opt/pureleven/.env
   # OR manually create and fill in the values
   ```

3. **Set up DNS** (when ready for domains)
   ```
   A record: uat.pureleven.com  → 172.232.118.208
   A record: prod.pureleven.com → 172.105.48.142
   ```

---

## 🔐 Security Notes

- 🔒 **Never commit** private keys to Git
- 🔒 Private keys only go in GitHub Secrets (encrypted)
- 🔒 Public keys are safe in `authorized_keys`
- 🔒 Rotate keys every 90 days
- 🔒 GitHub Actions logs are readable by repo members

---

## 📞 Troubleshooting

### If GitHub Actions SSH Deployment Fails

**Error: "Permission denied (publickey)"**
- [ ] Check all 6 GitHub Secrets are added correctly
- [ ] Verify public key is in `/root/.ssh/authorized_keys` on target server
- [ ] Check server's SSH daemon is running: `systemctl status ssh`

**Error: "Connection refused"**
- [ ] Verify server IP is correct
- [ ] Verify server is running and has SSH open (port 22)
- [ ] Test manually: `ssh -i /root/.ssh/uat root@172.232.118.208 'pwd'`

**Containers not starting after deployment**
- [ ] Check `.env` exists on target server with correct values
- [ ] Check Docker is running: `docker ps`
- [ ] View logs: `docker logs <container_name>`

---

## 📊 Current Setup Status

| Component | Status | Details |
|-----------|--------|---------|
| GitHub Repo | ✅ Ready | 3 branches: dev, uat, main |
| SSH Keys (UAT) | ✅ Ready | `/root/.ssh/uat` & `.pub` |
| SSH Keys (Prod) | ✅ Ready | `/root/.ssh/prod` & `.pub` |
| GitHub Actions Workflows | ✅ Ready | Both updated with correct paths |
| GitHub Secrets | ⏳ TODO | 6 secrets need to be added by you |
| Production Server | ⏳ TODO | Needs: public key + .env setup |
| DNS | ⏳ TODO | Need A records for domains |
| SSL Certificates | ⏳ TODO | Certbot setup after DNS ready |

---

## 🎓 What Happens After GitHub Secrets

1. GitHub Secrets are encrypted and stored safely
2. When you push to `uat` branch → GitHub Actions:
   - Reads the 6 secrets
   - SSHes into 172.232.118.208 as root
   - Pulls latest code from `uat` branch
   - Runs `docker compose up -d --build`
   - Runs migrations
   - Logs output to GitHub Actions tab

3. Same process for `main` branch → deploys to Production

---

## ✨ Summary

**You now have:**
- ✅ Two SSH key pairs (UAT & Production)
- ✅ All documentation for GitHub Secrets setup
- ✅ Automated deployment workflows ready to trigger
- ✅ Quick reference commands

**Next immediate action:**
- 👉 Add the 6 GitHub Secrets (link above)
- 👉 (Optional) SSH into prod server and add public key
- 👉 Test by pushing a branch to GitHub

**Then you can:**
- Push to `uat` → see auto-deployment to UAT server
- Push to `main` → see auto-deployment to Production server

---

Last updated: 2026-02-26  
Ready for automated CI/CD deployments! 🚀
