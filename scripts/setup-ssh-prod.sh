#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# SSH SETUP GUIDE FOR PRODUCTION SERVER
# ═══════════════════════════════════════════════════════════════════════════
# Location: /root/.ssh/prod (private key on UAT server for GitHub Actions)
# Location: /root/.ssh/prod.pub (public key to add to Prod server)
# Server: 172.105.48.142 (prod.pureleven.com)
# ═══════════════════════════════════════════════════════════════════════════

echo "╔═══════════════════════════════════════════════════════════════════════╗"
echo "║  PRODUCTION SSH SETUP                                                ║"
echo "║  Server: 172.105.48.142 → prod.pureleven.com                         ║"
echo "╚═══════════════════════════════════════════════════════════════════════╝"
echo ""

# ─── STEP 1: Verify keys exist on UAT server ──────────────────────────────
echo "✅ STEP 1: Verify SSH keys on UAT server (172.232.118.208)"
echo "   Keys stored at:"
echo "   - Private key: /root/.ssh/prod"
echo "   - Public key:  /root/.ssh/prod.pub"
echo ""
ls -lh /root/.ssh/prod*
echo ""

# ─── STEP 2: Instructions for setting up Prod server ─────────────────────
echo "📋 STEP 2: On Production Server (172.105.48.142)"
echo "   Run these commands as root:"
echo ""
echo "   ┌─────────────────────────────────────────────────────────────┐"
echo "   │ ssh root@172.105.48.142                                     │"
echo "   │ mkdir -p /root/.ssh                                         │"
echo "   │ chmod 700 /root/.ssh                                        │"
echo "   │ echo 'SSH_PUBLIC_KEY_HERE' >> /root/.ssh/authorized_keys    │"
echo "   │ chmod 600 /root/.ssh/authorized_keys                        │"
echo "   └─────────────────────────────────────────────────────────────┘"
echo ""

# ─── STEP 3: Show the public key to add ────────────────────────────────────
echo "🔑 STEP 3: Public Key to Add to Production Server"
echo "   Run this command on the Prod server:"
echo ""
echo "   echo '$(cat /root/.ssh/prod.pub)' >> /root/.ssh/authorized_keys"
echo ""

# ─── STEP 4: Test SSH from UAT ──────────────────────────────────────────────
echo "🧪 STEP 4: Test SSH Connection from UAT (run on this server)"
echo "   ┌─────────────────────────────────────────────────────────────┐"
echo "   │ ssh -i /root/.ssh/prod root@172.105.48.142 'whoami'         │"
echo "   │ # Should return: root                                       │"
echo "   └─────────────────────────────────────────────────────────────┘"
echo ""

# ─── STEP 5: Add to GitHub Secrets ────────────────────────────────────────
echo "📝 STEP 5: Add to GitHub Secrets"
echo "   URL: https://github.com/purelevenexim-ai/crm/settings/secrets/actions"
echo ""
echo "   Secret Name: PROD_SSH_HOST"
echo "   Value:       172.105.48.142"
echo ""
echo "   Secret Name: PROD_SSH_USER"
echo "   Value:       root"
echo ""
echo "   Secret Name: PROD_SSH_KEY"
echo "   Value:       [PASTE PRIVATE KEY BELOW]"
echo ""

# ─── Display private key for copy/paste ─────────────────────────────────────
echo "═════════════════════════════════════════════════════════════════════════"
echo "PRIVATE KEY TO ADD TO GITHUB SECRETS (PROD_SSH_KEY)"
echo "═════════════════════════════════════════════════════════════════════════"
cat /root/.ssh/prod
echo ""
echo "═════════════════════════════════════════════════════════════════════════"
echo ""
