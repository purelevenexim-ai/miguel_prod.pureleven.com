#!/bin/bash
# Tenant Data Replication Script
# Replicates pureleven tenant from UAT to Production
# Includes: employees, Shopify stores, delivery partners, vendors, notification channels
# Excludes: products, customers, orders, leads

set -e

TENANT_ID="3f7160e0-c6c3-4feb-bfff-b4eaed704110"
TENANT_COMPANY="Pureleven"
TENANT_SLUG="purelevenexim"

echo "=============================================="
echo "Tenant Data Replication: UAT → Production"
echo "=============================================="
echo ""
echo "Step 1: Extracting data from UAT..."
echo ""

# Create temporary SQL script to extract data
cat > /tmp/extract_tenant_data.sql << 'EOF'
-- Extract pureleven tenant data from UAT
SET search_path TO public;

-- Get tenant ID
\echo '=== Tenant Record ==='
SELECT id, company_name, slug, owner_email, contact_person_name, contact_phone, is_active FROM tenants WHERE id = '3f7160e0-c6c3-4feb-bfff-b4eaed704110';

\echo ''
\echo '=== Employees ==='
SELECT id, tenant_id, first_name, last_name, email, role, is_active FROM employees WHERE tenant_id = '3f7160e0-c6c3-4feb-bfff-b4eaed704110' ORDER BY created_at;

\echo ''
\echo '=== Delivery Partners ==='
SELECT id, tenant_id, partner_name, api_key, api_secret, base_url, is_active FROM delivery_partners WHERE tenant_id = '3f7160e0-c6c3-4feb-bfff-b4eaed704110' ORDER BY created_at;

\echo ''
\echo '=== Shopify Stores ==='
SELECT id, tenant_id, store_name, store_url, api_key, api_secret, access_token, is_active FROM shopify_stores WHERE tenant_id = '3f7160e0-c6c3-4feb-bfff-b4eaed704110' ORDER BY created_at;

\echo ''
\echo '=== Vendors ==='
SELECT id, tenant_id, vendor_name, contact_name, email, phone, is_active FROM vendors WHERE tenant_id = '3f7160e0-c6c3-4feb-bfff-b4eaed704110' ORDER BY created_at;

\echo ''
\echo '=== Notification Channels ==='
SELECT id, tenant_id, channel_type, config, is_active FROM notification_channels WHERE tenant_id = '3f7160e0-c6c3-4feb-bfff-b4eaed704110' ORDER BY created_at;

\echo ''
\echo '=== Couriers ==='
SELECT id, tenant_id, courier_name, api_endpoint, is_active FROM couriers WHERE tenant_id = '3f7160e0-c6c3-4feb-bfff-b4eaed704110' ORDER BY created_at;

\echo ''
\echo '=== Meta Integrations ==='
SELECT id, tenant_id, meta_type, config, is_active FROM meta_integrations WHERE tenant_id = '3f7160e0-c6c3-4feb-bfff-b4eaed704110' ORDER BY created_at;

\echo ''
\echo '=== WhatsApp Settings ==='
SELECT id, tenant_id, setting_key, setting_value FROM wa_settings WHERE tenant_id = '3f7160e0-c6c3-4feb-bfff-b4eaed704110' ORDER BY created_at;

EOF

# Run the extraction on UAT
echo "Connecting to UAT database..."
ssh uat "cd /opt/miguel && docker exec miguel_db psql -U miguel_user -d miguel_db -f /dev/stdin" < /tmp/extract_tenant_data.sql

echo ""
echo "=============================================="
echo "Data extraction complete!"
echo "=============================================="
echo ""
echo "NEXT STEPS:"
echo "1. Copy the employee email (should be purelevenexim@gmail.com)"
echo "2. Note the Shopify API credentials"
echo "3. Note the Delivery Partner (Delhivery) credentials"
echo ""
echo "Now run the SQL INSERT statements on Production..."
echo ""
