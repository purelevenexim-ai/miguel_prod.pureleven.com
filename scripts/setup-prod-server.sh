#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# PRODUCTION SERVER BOOTSTRAP SCRIPT
# Run this ONCE on the fresh Linode (172.105.48.142) as root
# Usage: bash setup-prod-server.sh
# ═══════════════════════════════════════════════════════════════════════════

set -e  # Exit on any error

echo "╔══════════════════════════════════════════════════════╗"
echo "║   PureLeven CRM — Production Server Setup            ║"
echo "║   Server: 172.105.48.142 → prod.pureleven.com        ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ─── 1. System Update ─────────────────────────────────────────────────────
echo "📦 [1/8] Updating system packages..."
apt update -y && apt upgrade -y

# ─── 2. Install Docker ────────────────────────────────────────────────────
echo "🐳 [2/8] Installing Docker..."
if ! command -v docker &> /dev/null; then
    apt install -y ca-certificates curl gnupg lsb-release
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt update -y
    apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl enable docker
    systemctl start docker
    echo "✅ Docker installed: $(docker --version)"
else
    echo "✅ Docker already installed: $(docker --version)"
fi

# Install docker-compose standalone (v2 compatible)
if ! command -v docker-compose &> /dev/null; then
    apt install -y docker-compose
fi

# ─── 3. Install Git ───────────────────────────────────────────────────────
echo "📁 [3/8] Installing Git..."
apt install -y git
echo "✅ Git installed: $(git --version)"

# ─── 4. Install Nginx (for SSL cert issuance — host-level, not Docker) ───
echo "🌐 [4/8] Installing Nginx (for Certbot SSL)..."
apt install -y nginx
systemctl stop nginx  # Stop it — Docker nginx will handle port 80/443
systemctl disable nginx
echo "✅ Nginx installed (disabled — Docker handles ports)"

# ─── 5. Install Certbot ───────────────────────────────────────────────────
echo "🔒 [5/8] Installing Certbot..."
apt install -y certbot
echo "✅ Certbot installed: $(certbot --version)"

# ─── 6. Clone Repository ─────────────────────────────────────────────────
echo "📥 [6/8] Cloning repository to /opt/pureleven..."
if [ -d "/opt/pureleven" ]; then
    echo "⚠️  /opt/pureleven already exists — pulling latest instead"
    cd /opt/pureleven
    git fetch origin
    git checkout main
    git pull origin main
else
    git clone https://github.com/purelevenexim-ai/crm.git /opt/pureleven
    cd /opt/pureleven
    git checkout main
    echo "✅ Repository cloned to /opt/pureleven on branch: main"
fi

# ─── 7. Create .env File ─────────────────────────────────────────────────
echo "⚙️  [7/8] Creating .env file..."
cd /opt/pureleven
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "══════════════════════════════════════════════════════════"
    echo "  ⚠️  ACTION REQUIRED: Fill in your .env file"
    echo "  Run: nano /opt/pureleven/.env"
    echo ""
    echo "  Key values to set:"
    echo "    DB_PASSWORD=<strong_password>"
    echo "    DATABASE_URL=postgresql://pureleven_user:<DB_PASSWORD>@db:5432/pureleven_db"
    echo "    ENCRYPTION_KEY=<generate: python3 -c \"import secrets; print(secrets.token_urlsafe(32))\">"
    echo "    JWT_SECRET_KEY=<generate: python3 -c \"import secrets; print(secrets.token_urlsafe(32))\">"
    echo "    META_WEBHOOK_VERIFY_TOKEN=<your_token>"
    echo "    (All Shopify, Delhivery, WhatsApp keys from UAT .env)"
    echo "══════════════════════════════════════════════════════════"
    echo ""
else
    echo "✅ .env file already exists"
fi

# ─── 8. Summary ───────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   ✅ Bootstrap Complete!                             ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "📋 NEXT STEPS:"
echo ""
echo "  1. Fill in environment variables:"
echo "     nano /opt/pureleven/.env"
echo ""
echo "  2. Issue SSL certificate (after DNS A record is set for prod.pureleven.com):"
echo "     certbot certonly --standalone -d prod.pureleven.com"
echo ""
echo "  3. Start the application:"
echo "     cd /opt/pureleven"
echo "     docker compose -f docker-compose.prod.yml up -d --build"
echo ""
echo "  4. Run database migrations:"
echo "     docker exec pureleven_backend alembic upgrade head"
echo ""
echo "  5. Verify everything is running:"
echo "     docker ps"
echo "     curl http://localhost:80"
echo ""
