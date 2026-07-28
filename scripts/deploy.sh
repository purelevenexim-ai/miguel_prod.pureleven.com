#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# PureLevenExim CRM — Deploy from UAT → GitHub → Production
#
# Run this from UAT server to:
#   1. Push local changes to GitHub
#   2. SSH into prod and run pull_to_prod.sh
#
# Usage: bash scripts/deploy.sh
# ═══════════════════════════════════════════════════════════════════════════════
set -e

PROD_HOST="root@172.105.48.142"
PROD_DIR="/opt/pureleven"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; }

echo "═══════════════════════════════════════════════"
echo "  PureLevenExim CRM — Deploy to Production"
echo "═══════════════════════════════════════════════"

# ── Step 1: Push to GitHub ──────────────────────────────────────────────────
echo ""
info "Pushing to GitHub..."
git push origin main 2>&1 || { error "Git push failed. Retrying in 5s..."; sleep 5; git push origin main; }
info "Pushed: $(git log --oneline -1)"

# ── Step 2: Pull & Deploy on Production ────────────────────────────────────
echo ""
info "Deploying on production server..."
ssh $PROD_HOST "cd $PROD_DIR && bash scripts/pull_to_prod.sh"

echo ""
echo "═══════════════════════════════════════════════"
info "Deployment complete!"
echo "═══════════════════════════════════════════════"
