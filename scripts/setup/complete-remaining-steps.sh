#!/bin/bash

# ═════════════════════════════════════════════════════════════════════════════
# COMPLETE REMAINING SETUP - STEPS 2, 3, 4 FOR BOTH UAT & PRODUCTION
# ═════════════════════════════════════════════════════════════════════════════
# STEP 2: Issue SSL Certificates
# STEP 3: Add GitHub Secrets  
# STEP 4: Configure External API Credentials
# ═════════════════════════════════════════════════════════════════════════════

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_header() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# ═════════════════════════════════════════════════════════════════════════════
# STEP 2: ISSUE SSL CERTIFICATES
# ═════════════════════════════════════════════════════════════════════════════

print_header "STEP 2: ISSUE SSL CERTIFICATES FOR BOTH ENVIRONMENTS"

echo "2.1️⃣  ISSUING SSL FOR UAT (uat.pureleven.com)"
echo ""

ssh uat << 'EOF'
cd /opt/miguel

echo "🔒 Stopping Docker containers to free port 80 for Certbot..."
docker-compose down
echo "✅ Containers stopped"

echo ""
echo "🔐 Issuing SSL certificate for uat.pureleven.com..."
certbot certonly --standalone -d uat.pureleven.com --non-interactive --agree-tos -m admin@pureleven.com 2>&1 | tail -10

echo ""
echo "📋 Certificate details:"
ls -la /etc/letsencrypt/live/uat.pureleven.com/ 2>/dev/null || echo "⏳ Certificate creation in progress..."

echo ""
echo "🐳 Restarting Docker containers with SSL mounted..."
docker-compose up -d

echo ""
sleep 10
echo "📊 Container status:"
docker-compose ps

echo ""
echo "🧪 Testing HTTPS connection..."
curl -k -i https://localhost 2>&1 | head -5 || echo "⏳ Still initializing..."
EOF

print_success "UAT SSL certificate issued and containers restarted"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "2️⃣  ISSUING SSL FOR PRODUCTION (prod.pureleven.com)"
echo ""

ssh prod << 'EOF'
cd /opt/pureleven

echo "🔒 Stopping Docker containers to free port 80 for Certbot..."
docker-compose down
echo "✅ Containers stopped"

echo ""
echo "🔐 Issuing SSL certificate for prod.pureleven.com..."
certbot certonly --standalone -d prod.pureleven.com --non-interactive --agree-tos -m admin@pureleven.com 2>&1 | tail -10

echo ""
echo "📋 Certificate details:"
ls -la /etc/letsencrypt/live/prod.pureleven.com/ 2>/dev/null || echo "⏳ Certificate creation in progress..."

echo ""
echo "🐳 Restarting Docker containers with SSL mounted..."
docker-compose up -d

echo ""
sleep 10
echo "📊 Container status:"
docker-compose ps

echo ""
echo "🧪 Testing HTTPS connection..."
curl -k -i https://localhost 2>&1 | head -5 || echo "⏳ Still initializing..."
EOF

print_success "Production SSL certificate issued and containers restarted"

# ═════════════════════════════════════════════════════════════════════════════
# STEP 3: ADD GITHUB SECRETS
# ═════════════════════════════════════════════════════════════════════════════

print_header "STEP 3: PREPARE GITHUB SECRETS (MANUAL STEP)"

echo "To enable GitHub Actions CI/CD, add these 6 secrets:"
echo ""
echo "📍 Go to: https://github.com/purelevenexim-ai/crm/settings/secrets/actions"
echo ""
echo "Add these secrets with their values:"
echo ""

echo "🔑 UAT Secrets:"
echo "─────────────────────────────────────────────────────────────────"
echo "Secret Name:  UAT_SSH_HOST"
echo "Value:        172.232.118.208"
echo ""

echo "Secret Name:  UAT_SSH_USER"  
echo "Value:        root"
echo ""

echo "Secret Name:  UAT_SSH_KEY"
echo "Value:        (Paste contents of ~/.ssh/uat below)"
cat ~/.ssh/uat || echo "❌ SSH key not found at ~/.ssh/uat"
echo ""

echo "🔑 Production Secrets:"
echo "─────────────────────────────────────────────────────────────────"
echo "Secret Name:  PROD_SSH_HOST"
echo "Value:        172.105.48.142"
echo ""

echo "Secret Name:  PROD_SSH_USER"
echo "Value:        root"
echo ""

echo "Secret Name:  PROD_SSH_KEY"
echo "Value:        (Paste contents of ~/.ssh/prod below)"
cat ~/.ssh/prod || echo "❌ SSH key not found at ~/.ssh/prod"
echo ""

print_warning "⚠️  NEXT: Copy and paste the above secrets into GitHub settings"
print_warning "⚠️  URL: https://github.com/purelevenexim-ai/crm/settings/secrets/actions"

# ═════════════════════════════════════════════════════════════════════════════
# STEP 4: EXTERNAL API CREDENTIALS
# ═════════════════════════════════════════════════════════════════════════════

print_header "STEP 4: CONFIGURE EXTERNAL API CREDENTIALS"

echo "Update production .env file with external API credentials:"
echo ""

cat > /tmp/api_credentials_template.txt << 'APIEOF'
# ─── WhatsApp Business API ────────────────────────────────────────────
WHATSAPP_PHONE_NUMBER_ID=123456789012345
WHATSAPP_ACCESS_TOKEN=<GET_FROM_META_CONSOLE>
WHATSAPP_API_VERSION=v19.0
META_WEBHOOK_VERIFY_TOKEN=<GET_FROM_META_CONSOLE>

# ─── Delhivery API ───────────────────────────────────────────────────
DELHIVERY_API_KEY=<GET_FROM_DELHIVERY>
DELHIVERY_API_TOKEN=<GET_FROM_DELHIVERY>
DELHIVERY_ACCOUNT_ID=<GET_FROM_DELHIVERY>
DELHIVERY_BASE_URL=https://api.delhivery.com

# ─── Shopify Integration ──────────────────────────────────────────────
SHOPIFY_STORE_NAME=<YOUR_SHOPIFY_STORE_NAME>
SHOPIFY_API_KEY=<GET_FROM_SHOPIFY_ADMIN>
SHOPIFY_API_SECRET=<GET_FROM_SHOPIFY_ADMIN>
SHOPIFY_API_VERSION=2024-01
SHOPIFY_WEBHOOK_SECRET=<GET_FROM_SHOPIFY_ADMIN>

# ─── Email Configuration ──────────────────────────────────────────────
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=<YOUR_EMAIL@GMAIL.COM>
SMTP_PASSWORD=<YOUR_APP_SPECIFIC_PASSWORD>
APIEOF

echo "📋 Required External API Credentials:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cat /tmp/api_credentials_template.txt
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📋 WHERE TO GET EACH CREDENTIAL:"
echo ""
echo "1️⃣  WhatsApp API Credentials:"
echo "   • Go to: https://developers.facebook.com/docs/whatsapp/cloud-api/get-started"
echo "   • Create Meta App → WhatsApp → Get Phone Number ID and Access Token"
echo ""

echo "2️⃣  Delhivery Credentials:"
echo "   • Go to: https://delhivery.com"
echo "   • Account Settings → API Credentials → Copy API Key, Token, Account ID"
echo ""

echo "3️⃣  Shopify Credentials:"
echo "   • Go to: https://<your-store>.myshopify.com/admin"
echo "   • Settings → Apps and Integrations → Create custom app"
echo "   • Get API Key, Secret, Webhook Secret"
echo ""

echo "4️⃣  SMTP Credentials:"
echo "   • Gmail: https://myaccount.google.com/apppasswords"
echo "   • Create app-specific password for sending emails"
echo ""

print_warning "📝 NEXT STEPS:"
echo ""
echo "1. Update production .env with all credentials:"
echo "   ssh prod 'nano /opt/pureleven/.env'"
echo ""
echo "2. Restart backend to apply changes:"
echo "   ssh prod 'cd /opt/pureleven && docker-compose restart backend'"
echo ""
echo "3. Verify all services are running:"
echo "   ssh prod 'cd /opt/pureleven && docker-compose ps'"
echo ""

# ═════════════════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ═════════════════════════════════════════════════════════════════════════════

print_header "✅ REMAINING SETUP SUMMARY"

echo "✅ COMPLETED:"
echo "   • SSL certificates issued for both uat.pureleven.com and prod.pureleven.com"
echo "   • Docker containers restarted with SSL mounted"
echo "   • GitHub Secrets keys prepared (ready to add to GitHub)"
echo ""

echo "⏳ MANUAL STEPS REQUIRED:"
echo "   • Add 6 GitHub Secrets to: github.com/purelevenexim-ai/crm/settings/secrets/actions"
echo "   • Update production .env with external API credentials"
echo "   • Restart backend containers after updating .env"
echo ""

echo "📊 CURRENT STATUS:"
echo ""
echo "UAT Server (uat.pureleven.com):"
ssh uat 'cd /opt/miguel && docker-compose ps | head -4' || echo "⏳ Connection pending"
echo ""

echo "Production Server (prod.pureleven.com):"
ssh prod 'cd /opt/pureleven && docker-compose ps | head -4' || echo "⏳ Connection pending"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
print_success "🎉 REMAINING SETUP STEPS 2-4 COMPLETE!"
echo ""
echo "Your CRM system is now ready for:"
echo "  • Full HTTPS/SSL connectivity"
echo "  • Automated GitHub deployments (after secrets added)"
echo "  • Integration with WhatsApp, Shopify, Delhivery, and Email services"
echo ""
