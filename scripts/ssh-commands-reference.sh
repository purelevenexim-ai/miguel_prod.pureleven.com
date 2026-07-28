#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# SSH COMMAND REFERENCE
# Quick commands for connecting to UAT and Production servers
# ═══════════════════════════════════════════════════════════════════════════

cat << 'EOF'
╔═══════════════════════════════════════════════════════════════════════════╗
║                     SSH COMMAND REFERENCE                                ║
║                                                                           ║
║  Run these commands on the UAT server (172.232.118.208)                  ║
╚═══════════════════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 🔑 SSH KEYS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  UAT Private Key:
    /root/.ssh/uat

  Production Private Key:
    /root/.ssh/prod

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 🚀 QUICK CONNECT COMMANDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1️⃣  Connect to UAT (this server):
      ssh -i /root/.ssh/uat root@172.232.118.208

  2️⃣  Connect to Production:
      ssh -i /root/.ssh/prod root@172.105.48.142

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 🧪 TEST COMMANDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Test UAT connectivity:
    ssh -i /root/.ssh/uat root@172.232.118.208 'whoami && date'

  Test Prod connectivity:
    ssh -i /root/.ssh/prod root@172.105.48.142 'whoami && date'

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 🐳 DOCKER COMMANDS (Remote)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Check running containers on UAT:
    ssh -i /root/.ssh/uat root@172.232.118.208 'docker ps'

  Check running containers on Prod:
    ssh -i /root/.ssh/prod root@172.105.48.142 'docker ps'

  View UAT backend logs:
    ssh -i /root/.ssh/uat root@172.232.118.208 'docker logs miguel_backend --tail 50'

  View Prod backend logs:
    ssh -i /root/.ssh/prod root@172.105.48.142 'docker logs pureleven_backend --tail 50'

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 📁 PROJECT PATHS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  UAT Project Directory:
    /opt/miguel

  Production Project Directory:
    /opt/pureleven

  Database Backups (UAT):
    /opt/miguel/backup_uat_*.sql

  Database Backups (Prod):
    /opt/pureleven/backup_prod_*.sql

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 🔄 DEPLOYMENT WORKFLOW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  To deploy to UAT:
    git checkout uat
    git merge dev
    git push origin uat
    # GitHub Actions automatically deploys via SSH

  To deploy to Production:
    git checkout main
    git merge uat
    git push origin main
    # GitHub Actions automatically deploys via SSH

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 🔒 GITHUB SECRETS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  6 Secrets needed at:
  https://github.com/purelevenexim-ai/crm/settings/secrets/actions

  ✅ UAT_SSH_HOST = 172.232.118.208
  ✅ UAT_SSH_USER = root
  ✅ UAT_SSH_KEY = [UAT private key]

  ✅ PROD_SSH_HOST = 172.105.48.142
  ✅ PROD_SSH_USER = root
  ✅ PROD_SSH_KEY = [PROD private key]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 📝 IMPORTANT NOTES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  • Private keys (/root/.ssh/uat and /root/.ssh/prod) MUST be added to GitHub
    Secrets, NOT committed to Git

  • Public keys are in /root/.ssh/authorized_keys on both servers

  • SSH keys allow GitHub Actions to deploy automatically on branch push

  • Never share private keys; they are sensitive!

  • Rotate keys every 90 days for security

EOF
