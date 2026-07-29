#!/usr/bin/env python3
"""
Replicate pureleven tenant from UAT to Production
Excludes: products, customers, orders, leads, and related transaction data
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import sys
from datetime import datetime

# Connection parameters
UAT_CONFIG = {
    'host': '172.232.118.208',
    'port': 5432,
    'database': 'miguel_db',
    'user': 'miguel_user',
    'password': 'miguel_password'
}

PROD_CONFIG = {
    'host': '172.105.48.142',
    'port': 5432,
    'database': 'pureleven_db',
    'user': 'pureleven_user',
    'password': 'pureleven_password'
}

TENANT_ID = '3f7160e0-c6c3-4feb-bfff-b4eaed704110'

# Tables to copy (in dependency order)
TABLES_TO_COPY = [
    'tenants',
    'employees',
    'notification_channels',
    'delivery_partners',
    'couriers',
    'rto_zones',
    'shipping_business_rules',
    'shipping_info',
    'shopify_stores',
    'meta_integrations',
    'invoice_counters',
    'wa_settings',
    'wa_postback_rules',
    'wa_outbound_webhooks',
    'vendor_products',
    'vendors',
]

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")

def get_column_names(conn, table):
    """Get column names for a table"""
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = %s AND table_schema = 'public'
            ORDER BY ordinal_position
        """, (table,))
        return [row[0] for row in cur.fetchall()]

def copy_table_data(uat_conn, prod_conn, table):
    """Copy data from UAT to Production"""
    with uat_conn.cursor(cursor_factory=RealDictCursor) as uat_cur:
        with prod_conn.cursor() as prod_cur:
            # Get column names
            columns = get_column_names(uat_conn, table)
            
            # Check if table has tenant_id column
            has_tenant_id = 'tenant_id' in columns
            
            if table == 'tenants':
                # Copy specific tenant record
                uat_cur.execute(f"""
                    SELECT {','.join(columns)} FROM {table} 
                    WHERE id = %s
                """, (TENANT_ID,))
            elif has_tenant_id:
                # Copy all records for this tenant
                uat_cur.execute(f"""
                    SELECT {','.join(columns)} FROM {table} 
                    WHERE tenant_id = %s
                """, (TENANT_ID,))
            else:
                # No tenant filtering needed
                uat_cur.execute(f"SELECT {','.join(columns)} FROM {table}")
            
            rows = uat_cur.fetchall()
            
            if not rows:
                log(f"  ✓ {table}: No data to copy")
                return 0
            
            # Delete existing data in production if tenant_id exists
            if has_tenant_id or table == 'tenants':
                try:
                    if table == 'tenants':
                        prod_cur.execute(f"DELETE FROM {table} WHERE id = %s", (TENANT_ID,))
                    else:
                        prod_cur.execute(f"DELETE FROM {table} WHERE tenant_id = %s", (TENANT_ID,))
                    prod_conn.commit()
                except Exception as e:
                    log(f"  WARNING: Could not delete existing data: {e}")
                    prod_conn.rollback()
            
            # Insert new data
            for row in rows:
                col_names = ', '.join(columns)
                placeholders = ', '.join(['%s'] * len(columns))
                values = [row[col] for col in columns]
                
                try:
                    prod_cur.execute(f"""
                        INSERT INTO {table} ({col_names}) 
                        VALUES ({placeholders})
                    """, values)
                except psycopg2.IntegrityError as e:
                    log(f"  WARNING: Duplicate key in {table}: {e}")
                    prod_conn.rollback()
                except Exception as e:
                    log(f"  ERROR in {table}: {e}")
                    log(f"    Columns: {col_names}")
                    log(f"    Values: {values}")
                    prod_conn.rollback()
                    raise
            
            prod_conn.commit()
            log(f"  ✓ {table}: {len(rows)} record(s) copied")
            return len(rows)

def main():
    log("=== Tenant Replication: UAT → Production ===")
    log(f"Tenant ID: {TENANT_ID}")
    log("")
    
    try:
        # Connect to UAT
        log("Connecting to UAT database...")
        uat_conn = psycopg2.connect(**UAT_CONFIG)
        log("✓ Connected to UAT")
        
        # Connect to Production
        log("Connecting to Production database...")
        prod_conn = psycopg2.connect(**PROD_CONFIG)
        log("✓ Connected to Production")
        
        log("")
        log("Replicating tables...")
        log("")
        
        total_records = 0
        for table in TABLES_TO_COPY:
            try:
                count = copy_table_data(uat_conn, prod_conn, table)
                total_records += count
            except Exception as e:
                log(f"  ✗ ERROR copying {table}: {e}")
                uat_conn.close()
                prod_conn.close()
                sys.exit(1)
        
        log("")
        log(f"=== Replication Complete ===")
        log(f"Total records copied: {total_records}")
        
        # Verification
        log("")
        log("Verifying imported data...")
        with prod_conn.cursor() as cur:
            cur.execute("SELECT company_name FROM tenants WHERE id = %s", (TENANT_ID,))
            result = cur.fetchone()
            if result:
                log(f"✓ Tenant: {result[0]}")
            
            cur.execute("SELECT COUNT(*) FROM employees WHERE tenant_id = %s", (TENANT_ID,))
            log(f"✓ Employees: {cur.fetchone()[0]}")
            
            cur.execute("SELECT COUNT(*) FROM shopify_stores WHERE tenant_id = %s", (TENANT_ID,))
            log(f"✓ Shopify Stores: {cur.fetchone()[0]}")
            
            cur.execute("SELECT COUNT(*) FROM delivery_partners WHERE tenant_id = %s", (TENANT_ID,))
            log(f"✓ Delivery Partners: {cur.fetchone()[0]}")
            
            cur.execute("SELECT COUNT(*) FROM vendors WHERE tenant_id = %s", (TENANT_ID,))
            log(f"✓ Vendors: {cur.fetchone()[0]}")
        
        uat_conn.close()
        prod_conn.close()
        
        log("")
        log("✓ All done!")
        
    except Exception as e:
        log(f"FATAL ERROR: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
