# GitHub Secrets Setup for CI/CD Deployments

## Overview
This document contains all the secrets needed to enable GitHub Actions automated deployments to both UAT and Production servers.

**Location:** `https://github.com/purelevenexim-ai/crm/settings/secrets/actions`

---

## Secrets to Add (6 Total)

### 1. UAT Server Secrets

#### `UAT_SSH_HOST`
```
172.232.118.208
```

#### `UAT_SSH_USER`
```
root
```

#### `UAT_SSH_KEY`
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACC09WQjzQZowWojxrMB5zXwyAZuIaVMJIyBPM3nD7TijgAAAJgCvtV0Ar7V
dAAAAAtzc2gtZWQyNTUxOQAAACC09WQjzQZowWojxrMB5zXwyAZuIaVMJIyBPM3nD7Tijg
AAAEA92QuS2rXUbM8OhtQmt5nU2FxAAPot+zISg5WGEYVpv7T1ZCPNBmjBaiPGswHnNfDI
Bm4hpUwkjIE8zecPtOKOAAAAE3VhdC0xNzIuMjMyLjExOC4yMDgBAg==
-----END OPENSSH PRIVATE KEY-----
```

---

### 2. Production Server Secrets

#### `PROD_SSH_HOST`
```
172.105.48.142
```

#### `PROD_SSH_USER`
```
root
```

#### `PROD_SSH_KEY`
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACBfHZUhtaOTHJp5sxn3uNKEQrbiHuTlr1+ci/m2Ul3FPQAAAJhje8YwY3vG
MAAAAAtzc2gtZWQyNTUxOQAAACBfHZUhtaOTHJp5sxn3uNKEQrbiHuTlr1+ci/m2Ul3FPQ
AAAECa3jPFghVeBahfjiBmJi4OfWotFD0Udr/2JLbRJGxyS18dlSG1o5McmnmzGfe40oRC
tuIe5OWvX5yL+bZSXcU9AAAAE3Byb2QtMTcyLjEwNS40OC4xNDIBAg==
-----END OPENSSH PRIVATE KEY-----
```

---

## How to Add Secrets

1. Go to: `https://github.com/purelevenexim-ai/crm/settings/secrets/actions`
2. Click **"New repository secret"**
3. Enter the **Name** (e.g., `UAT_SSH_HOST`)
4. Paste the **Value**
5. Click **"Add secret"**
6. Repeat for all 6 secrets

---

## How They Work

### Deployment to UAT
- **Trigger:** Push to `uat` branch
- **Workflow:** `.github/workflows/deploy-uat.yml`
- **Uses:** `UAT_SSH_HOST`, `UAT_SSH_USER`, `UAT_SSH_KEY`
- **Destination:** `172.232.118.208:/opt/miguel`
- **Command:** `docker compose up -d --build && docker exec miguel_backend alembic upgrade head`

### Deployment to Production
- **Trigger:** Push to `main` branch
- **Workflow:** `.github/workflows/deploy-prod.yml`
- **Uses:** `PROD_SSH_HOST`, `PROD_SSH_USER`, `PROD_SSH_KEY`
- **Destination:** `172.105.48.142:/opt/pureleven`
- **Command:** `docker compose -f docker-compose.prod.yml up -d --build && docker exec pureleven_backend alembic upgrade head`

---

## SSH Key Details

| Key Name | Server | User | Host | Private Key File |
|----------|--------|------|------|------------------|
| `UAT_SSH_KEY` | UAT | root | 172.232.118.208 | `/root/.ssh/uat` |
| `PROD_SSH_KEY` | Production | root | 172.105.48.142 | `/root/.ssh/prod` |

---

## Testing SSH Access

From UAT server, test connection to Production:
```bash
ssh -i /root/.ssh/prod root@172.105.48.142 'whoami'
# Should output: root
```

From UAT server, test connection to itself:
```bash
ssh -i /root/.ssh/uat root@172.232.118.208 'whoami'
# Should output: root
```

---

## Troubleshooting

### GitHub Actions shows "Permission denied (publickey)"
- [ ] Verify secrets are added (no typos)
- [ ] Verify public keys are in `/root/.ssh/authorized_keys` on both servers
- [ ] Check workflow file uses correct secret names

### Deployment succeeds but containers don't start
- [ ] Check `/opt/miguel/.env` or `/opt/pureleven/.env` exists
- [ ] Check `docker ps` to see if containers are running
- [ ] Check logs: `docker logs <container_name>`

### Alembic migrations fail
- [ ] Ensure database is running: `docker ps | grep db`
- [ ] Check migrations haven't been manually run already
- [ ] Verify `.env` has correct `DATABASE_URL`

---

## SSH Key Rotation

To rotate SSH keys:
1. Generate new key pairs
2. Add new public keys to `authorized_keys` on servers
3. Update GitHub Secrets with new private keys
4. Test before removing old keys
5. Remove old public keys from `authorized_keys`

---

## Security Notes

- 🔒 Never commit private keys to Git
- 🔒 Private keys should only be in GitHub Secrets (encrypted)
- 🔒 Public keys can be in `authorized_keys`
- 🔒 Rotate keys periodically (recommended: every 90 days)
- 🔒 Audit GitHub Actions logs regularly

---

Last updated: 2026-02-26
