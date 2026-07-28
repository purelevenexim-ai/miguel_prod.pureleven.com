import uuid
from app.database.session import SessionLocal
import app.models  # noqa: F401
from app.models.customer import Customer
from app.models.product import Product
from app.models.order import Order, OrderItem
from app.models.lead import Lead

db = SessionLocal()

try:
    # Get existing tenant and employee
    from app.models.tenant import Tenant
    from app.models.employee import Employee
    
    tenant = db.query(Tenant).filter(Tenant.slug == "demo-tenant").first()
    if not tenant:
        print("❌ demo-tenant not found")
        exit(1)
    
    employee = db.query(Employee).filter(Employee.email == "sam@sages.com").first()
    if not employee:
        print("❌ Employee not found")
        exit(1)
    
    print(f"✅ Using tenant: {tenant.company_name}")
    print(f"✅ Using employee: {employee.full_name}")

    # 1. Create sample products
    products_data = [
        {"name": "Laptop Pro 15", "sku": "LAPTOP-001", "unit_price": 89999, "code": "PROD-00001"},
        {"name": "Wireless Mouse", "sku": "MOUSE-001", "unit_price": 499, "code": "PROD-00002"},
        {"name": "Mechanical Keyboard RGB", "sku": "KBD-001", "unit_price": 3499, "code": "PROD-00003"},
        {"name": "USB-C Hub", "sku": "HUB-001", "unit_price": 1299, "code": "PROD-00004"},
        {"name": "27\" Monitor 4K", "sku": "MON-001", "unit_price": 24999, "code": "PROD-00005"},
    ]
    
    products = []
    for pdata in products_data:
        product = Product(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            product_code=pdata["code"],
            name=pdata["name"],
            sku=pdata["sku"],
            unit_price=pdata["unit_price"],
            created_by_id=employee.id,
        )
        db.add(product)
        products.append(product)
    db.commit()
    print(f"✅ {len(products)} products created")

    # 2. Create sample customers
    customers_data = [
        {"name": "Raj Kumar", "email": "raj@customer.com", "phone": "9999888877", "type": "retailer", "code": "CUST-00001"},
        {"name": "Priya Sharma", "email": "priya@customer.com", "phone": "8888777766", "type": "wholesaler", "code": "CUST-00002"},
        {"name": "Arjun Singh", "email": "arjun@customer.com", "phone": "7777666655", "type": "retailer", "code": "CUST-00003"},
    ]
    
    customers = []
    for cdata in customers_data:
        customer = Customer(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            name=cdata["name"],
            email=cdata["email"],
            phone=cdata["phone"],
            customer_type=cdata["type"],
            unique_customer_code=cdata["code"],
            created_by_employee_id=employee.id,
        )
        db.add(customer)
        customers.append(customer)
    db.commit()
    print(f"✅ {len(customers)} customers created")

    # 3. Create sample orders with items
    for i, customer in enumerate(customers[:2]):  # Create orders for first 2 customers
        order = Order(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            order_number=f"ORD-2026-{i+1:04d}",
            customer_id=customer.id,
            created_by_id=employee.id,
            status="confirmed",
            payment_status="pending",
            total_amount=0,
        )
        db.add(order)
        db.flush()

        # Add 2-3 items per order
        for j, product in enumerate(products[:2 if i == 0 else 3]):
            qty = (j + 1)
            item_total = float(product.unit_price) * qty
            order.total_amount += item_total
            
            order_item = OrderItem(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                order_id=order.id,
                product_name=product.name,
                sku=product.sku,
                quantity=qty,
                unit_price=product.unit_price,
                line_total=item_total,
            )
            db.add(order_item)
        
        db.commit()
        print(f"✅ Order created: {order.order_number} (Total: ₹{order.total_amount})")

    # 4. Create sample leads
    leads_data = [
        {"name": "Rahul Desai", "email": "rahul@lead.com", "phone": "9191919191", "source": "manual", "number": "LEAD-2026-001"},
        {"name": "Sneha Patel", "email": "sneha@lead.com", "phone": "8282828282", "source": "manual", "number": "LEAD-2026-002"},
        {"name": "Vikram Menon", "email": "vikram@lead.com", "phone": "7373737373", "source": "manual", "number": "LEAD-2026-003"},
    ]
    
    leads = []
    for ldata in leads_data:
        lead = Lead(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            lead_number=ldata["number"],
            name=ldata["name"],
            email=ldata["email"],
            phone=ldata["phone"],
            status="new_lead",
            source=ldata["source"],
            created_by_id=employee.id,
        )
        db.add(lead)
        leads.append(lead)
    db.commit()
    print(f"✅ {len(leads)} leads created")

    print("\n" + "="*70)
    print("✅✅✅ UAT BUSINESS DATA SEEDED SUCCESSFULLY! ✅✅✅")
    print("="*70)
    print("\n📊 Data Summary:")
    print(f"  ✓ 5 Products (Laptop, Mouse, Keyboard, Hub, Monitor)")
    print(f"  ✓ 3 Customers (Raj, Priya, Arjun)")
    print(f"  ✓ 2 Orders with items (Total orders: ₹{products[0].unit_price + products[1].unit_price*2} + ₹{products[0].unit_price*2 + products[1].unit_price*3})")
    print(f"  ✓ 3 Leads (Rahul, Sneha, Vikram)")
    print("\n🔐 Login Credentials:")
    print(f"  Tenant Admin: sam@sages.com / Password: (check your DB setup)")
    print(f"  Superadmin: admin@platform.com / Admin@123")
    print("\n🌐 Access points:")
    print(f"  Dashboard: https://uat.pureleven.com/")
    print(f"  API Docs: http://localhost:8000/docs")
    print("="*70)

except Exception as e:
    db.rollback()
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
