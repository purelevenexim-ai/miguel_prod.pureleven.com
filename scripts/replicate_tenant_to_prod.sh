#!/bin/bash

# Script to replicate pureleven tenant data from UAT to Production
# Excludes: products, customers, orders, leads (and related tables)
# Includes: tenant config, employees, Shopify connection, Delhivery connection, etc.

set -e

TENANT_ID="3f7160e0-c6c3-4feb-bfff-b4eaed704110"
TENANT_SLUG="purelevenexim"
UAT_DB_HOST="172.232.118.208"
UAT_DB_PORT="5432"
UAT_DB_NAME="miguel_db"
UAT_DB_USER="miguel_user"
UAT_DB_PASS="miguel_password"

PROD_DB_HOST="172.105.48.142"
PROD_DB_PORT="5432"
PROD_DB_NAME="pureleven_db"
PROD_DB_USER="pureleven_user"
PROD_DB_PASS="pureleven_password"

# Tables to copy (in order of dependencies)
# These tables don't have product, customer, order, or lead data
TABLES_TO_COPY=(
    "tenants"
    "employees"
    "notification_channels"
    "delivery_partners"
    "couriers"
    "rto_zones"
    "shipping_business_rules"
    "shipping_info"
    "shopify_stores"
    "meta_integrations"
    "invoice_counters"
    "wa_settings"
    "wa_postback_rules"
    "wa_outbound_webhooks"
    "vendor_products"
    "vendors"
)

echo "========================================="
echo "Replicating Pureleven Tenant Data"
echo "From UAT to Production"
echo "========================================="
echo ""
echo "Tenant ID: $TENANT_ID"
echo "Tenant Slug: $TENANT_SLUG"
echo ""

# Export from UAT
export PGPASSWORD=$UAT_DB_PASS
echo "Exporting data from UAT..."

# Create a temporary SQL file to dump the data
TEMP_DUMP="/tmp/tenant_data_export.sql"

{
    echo "-- Exported Pureleven Tenant Data from UAT"
    echo "-- Generated: $(date)"
    echo "-- This dump includes configuration, employees, and integration settings"
    echo ""
    
    # Disable foreign key checks for import
    echo "SET session_replication_role = 'replica';"
    echo ""
    
    # Delete existing data for this tenant in prod (if it exists)
    echo "-- Deleting existing tenant data in Production (if any)"
    for table in "${TABLES_TO_COPY[@]}"; do
        if [ "$table" = "tenants" ]; then
            echo "DELETE FROM $table WHERE id = '$TENANT_ID';"
        fi
    done
    echo ""
    
    # Export tenant record
    echo "-- Tenant Record"
    psql -h $UAT_DB_HOST -U $UAT_DB_USER -d $UAT_DB_NAME -tc \
        "COPY (SELECT * FROM tenants WHERE id = '$TENANT_ID') TO STDOUT;" >> $TEMP_DUMP || true
    echo "COPY tenants FROM STDIN;" >> $TEMP_DUMP
    psql -h $UAT_DB_HOST -U $UAT_DB_USER -d $UAT_DB_NAME -tc \
        "COPY (SELECT * FROM tenants WHERE id = '$TENANT_ID') TO STDOUT;" >> $TEMP_DUMP || true
    echo "\." >> $TEMP_DUMP
    echo ""
    
    # Export employees for this tenant
    echo "-- Employee Records"
    echo "COPY employees FROM STDIN;" >> $TEMP_DUMP
    psql -h $UAT_DB_HOST -U $UAT_DB_USER -d $UAT_DB_NAME -tc \
        "COPY (SELECT * FROM employees WHERE tenant_id = '$TENANT_ID') TO STDOUT;" >> $TEMP_DUMP || true
    echo "\." >> $TEMP_DUMP
    echo ""
    
    # Export Shopify stores
    echo "-- Shopify Stores"
    echo "COPY shopify_stores FROM STDIN;" >> $TEMP_DUMP
    psql -h $UAT_DB_HOST -U $UAT_DB_USER -d $UAT_DB_NAME -tc \
        "COPY (SELECT * FROM shopify_stores WHERE tenant_id = '$TENANT_ID') TO STDOUT;" >> $TEMP_DUMP || true
    echo "\." >> $TEMP_DUMP
    echo ""
    
    # Export other tenant-specific configuration
    for table in notification_channels delivery_partners couriers shipping_business_rules shipping_info meta_integrations wa_settings wa_postback_rules vendor_products vendors; do
        echo "-- $table"
        echo "COPY $table FROM STDIN;" >> $TEMP_DUMP
        psql -h $UAT_DB_HOST -U $UAT_DB_USER -d $UAT_DB_NAME -tc \
            "COPY (SELECT * FROM $table WHERE tenant_id = '$TENANT_ID') TO STDOUT;" >> $TEMP_DUMP || true
        echo "\." >> $TEMP_DUMP
        echo ""
    done
    
    # Re-enable foreign key checks
    echo "SET session_replication_role = 'origin';"
    
} > $TEMP_DUMP

echo "Data exported to: $TEMP_DUMP"
echo "File size: $(du -h $TEMP_DUMP | cut -f1)"
echo ""

# Import to Production
export PGPASSWORD=$PROD_DB_PASS
echo "Importing data to Production..."

# Check if tenant already exists in production
echo "Checking if tenant exists in Production..."
TENANT_EXISTS=$(psql -h $PROD_DB_HOST -U $PROD_DB_USER -d $PROD_DB_NAME -tc \
    "SELECT COUNT(*) FROM tenants WHERE id = '$TENANT_ID';" | grep -o '[0-9]*')

if [ "$TENANT_EXISTS" -gt "0" ]; then
    echo "WARNING: Tenant already exists in Production!"
    echo "Do you want to replace it? (yes/no)"
    read -r response
    if [ "$response" != "yes" ]; then
        echo "Aborting..."
        exit 1
    fi
    echo "Deleting existing tenant data..."
    # Delete in reverse order of foreign keys
    for table in vendors vendor_products wa_postback_rules wa_settings meta_integrations shipping_info shipping_business_rules couriers rto_zones delivery_partners notification_channels employees; do
        psql -h $PROD_DB_HOST -U $PROD_DB_USER -d $PROD_DB_NAME -tc \
            "DELETE FROM $table WHERE tenant_id = '$TENANT_ID';"
    done
    psql -h $PROD_DB_HOST -U $PROD_DB_USER -d $PROD_DB_NAME -tc \
        "DELETE FROM tenants WHERE id = '$TENANT_ID';"
fi

# Import data
psql -h $PROD_DB_HOST -U $PROD_DB_USER -d $PROD_DB_NAME < $TEMP_DUMP

echo ""
echo "========================================="
echo "✓ Tenant data replicated successfully!"
echo "========================================="
echo ""
echo "Verifying import..."

export PGPASSWORD=$PROD_DB_PASS

# Count records in key tables
echo "Production - Tenant: $(psql -h $PROD_DB_HOST -U $PROD_DB_USER -d $PROD_DB_NAME -tc "SELECT COUNT(*) FROM tenants WHERE id = '$TENANT_ID';")"
echo "Production - Employees: $(psql -h $PROD_DB_HOST -U $PROD_DB_USER -d $PROD_DB_NAME -tc "SELECT COUNT(*) FROM employees WHERE tenant_id = '$TENANT_ID';")"
echo "Production - Shopify Stores: $(psql -h $PROD_DB_HOST -U $PROD_DB_USER -d $PROD_DB_NAME -tc "SELECT COUNT(*) FROM shopify_stores WHERE tenant_id = '$TENANT_ID';")"

# Cleanup
rm -f $TEMP_DUMP
echo ""
echo "Done! Temporary files cleaned up."
