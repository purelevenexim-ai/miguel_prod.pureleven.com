#!/usr/bin/env python3
"""Direct customer creation and linking for order 1534"""
import sys
import uuid
sys.path.insert(0, "/app")

from sqlalchemy import text
from app.database.session import SessionLocal
from datetime import datetime, timezone

session = SessionLocal()

try:
    # Get tenant and employee info
    result = session.execute(text("""
SELECT so.tenant_id, e.id
FROM shopify_orders so
CROSS JOIN employees e
WHERE so.shopify_order_name = '##1534'
  AND e.tenant_id = so.tenant_id
  AND e.role = 'admin'
LIMIT 1;
"""))
    
    row = result.fetchone()
    if not row:
        print("❌ Order or admin employee not found")
        sys.exit(1)
    
    tenant_id, emp_id = row
    print(f"✅ Found: tenant_id={tenant_id}, admin_id={emp_id}")
    
    # Create customer
    cust_id = str(uuid.uuid4())
    session.execute(text("""
INSERT INTO customers (
    id, tenant_id, unique_customer_code, name, phone, email,
    address, pincode, city, state, country,
    customer_type, payment_mode_preference, source, lead_status,
    assigned_employee_id, created_by_employee_id,
    first_order_date, last_order_date, last_seen_at,
    total_orders, average_order_value,
    notes, is_active,
    created_at, updated_at
) VALUES (
    :cust_id, :tenant_id, 'CUST-00017', 'Basil Jacob', '+919074579850', NULL,
    NULL, NULL, 'Ernakulam', NULL, 'India',
    'retail', 'cod', 'website', 'converted',
    NULL, :emp_id,
    NOW(), NOW(), NOW(),
    1, 500.02,
    'Auto-created from Shopify order ##1534. Tracking: 27860310013646', true,
    NOW(), NOW()
);
"""), {
    "cust_id": cust_id,
    "tenant_id": tenant_id,
    "emp_id": emp_id
})
    
    print(f"✅ Customer created: {cust_id}")
    
    # Link the order
    session.execute(text("""
UPDATE shopify_orders
SET customer_id = :cust_id
WHERE shopify_order_name = '##1534';
"""), {"cust_id": cust_id})
    
    session.commit()
    print(f"✅ Order ##1534 linked to customer CUST-00017")
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
finally:
    session.close()
