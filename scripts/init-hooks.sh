#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# Initialize Git Hooks for Development
# Usage: bash scripts/init-hooks.sh
#
# This script installs pre-push hooks that verify production safety before push.
# ═══════════════════════════════════════════════════════════════════════════════

set -e

REPO_ROOT=$(git rev-parse --show-toplevel)
HOOKS_DIR="$REPO_ROOT/.git/hooks"

echo "Initializing git hooks..."

# Check if pre-push hook exists in repo
if [ ! -f "$REPO_ROOT/.git/hooks/pre-push" ]; then
    echo "Error: .git/hooks/pre-push not found in repository."
    exit 1
fi

# Make the hook executable
chmod +x "$REPO_ROOT/.git/hooks/pre-push"
echo "✓ Git hooks installed at: $HOOKS_DIR"
echo ""
echo "The following checks will run before you push to main:"
echo "  1. No uncommitted changes"
echo "  2. All commits signed"
echo "  3. No sensitive files (.env, secrets, etc.)"
echo "  4. Docker files present (docker-compose.prod.yml, nginx-prod.conf)"
echo "  5. Nginx config syntax valid"
echo "  6. Python syntax check"
echo "  7. Frontend HTML/CSS/JS balanced brackets"
echo "  8. Commit message format (conventional commits)"
echo "  9. Database migrations tracked"
echo " 10. Documentation (README/CHANGELOG) updated"
echo ""
echo "To bypass (USE WITH CAUTION): git push --no-verify"
