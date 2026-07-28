import uuid
from app.database.session import SessionLocal
import app.models  # noqa: F401 – ensure all models registered
from app.models.tenant import Tenant
from app.models.user import User
from app.models.employee import Employee, RoleEnum
from app.models.customer import Customer
from app.models.product import Product
from app.models.order import Order, OrderItem
from app.models.lead import Lead
from app.core.security import hash_password

db = SessionLocal()

try:
    # 1. Create default tenant
    tenant = Tenant(
        id=uuid.uuid4(),
        company_name="Demo Company Ltd",
        slug="demo-tenant",
        contact_person_name="Owner Person",
        contact_phone="9876543210",
        owner_email="owner@demo.com",
    )
    db.add(tenant)
    db.commit()
    print(f"✅ Tenant created: {tenant.company_name}")

    # 2. Create tenant admin employee (with password for login)
    admin_employee = Employee(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        full_name="Tenant Admin",
        email="admin@demo.com",
        phone="9876543210",
        hashed_password=hash_password("Admin@123"),
        role="admin",
    )
    db.add(admin_employee)
    db.commit()
    print(f"✅ Admin employee created: {admin_employee.email}")

    # 3. Create regular sales employee
    sales_employee = Employee(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        full_name="John Sales",
        email="john@demo.com",
        phone="9876543210",
        hashed_password=hash_password("John@123"),
        role="employee",
    )
    db.add(sales_employee)
    db.commit()
    print(f"✅ Sales employee created: {sales_employee.full_name}")

    # 4. Create sample products
    products_data = [
        {"name": "Laptop Pro", "sku": "LAPTOP-001", "price": 50000},
        {"name": "Wireless Mouse", "sku": "MOUSE-001", "price": 500},
        {"name": "Mechanical Keyboard", "sku": "KBD-001", "price": 2000},
    ]
    
    products = []
    for pdata in products_data:
        product = Product(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            name=pdata["name"],
            sku=pdata["sku"],
            price=pdata["price"],
            created_by_id=sales_employee.id,
        )
        db.add(product)
        products.append(product)
    db.commit()
    print(f"✅ {len(products)} products created")

    # 5. Create sample customers
    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Raj Kumar",
        email="raj@customer.com",
        phone="9999888877",
        customer_type="retailer",
    )
    db.add(customer)
    db.commit()
    print(f"✅ Customer created: {customer.name}")

    # 6. Create sample order
    order = Order(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
        customer_id=customer.id,
        created_by_id=sales_employee.id,
        status="new",
        total_amount=50000,
    )
    db.add(order)
    db.commit()
    print(f"✅ Order created: {order.order_number}")

    # 7. Create order item
    order_item = OrderItem(
        id=uuid.uuid4(),
        order_id=order.id,
        product_id=products[0].id,
        quantity=1,
        unit_price=50000,
        total_price=50000,
    )
    db.add(order_item)
    db.commit()
    print(f"✅ Order item added to order")

    # 8. Create sample lead
    lead = Lead(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Priya Singh",
        email="priya@lead.com",
        phone="8888777766",
        status="new_lead",
        source="manual",
        created_by_id=sales_employee.id,
    )
    db.add(lead)
    db.commit()
    print(f"✅ Lead created: {lead.name}")

    print("\n" + "="*60)
    print("✅✅✅ UAT SEED DATA COMPLETE! ✅✅✅")
    print("="*60)
    print("\nDemo Tenant Admin Credentials:")
    print("  Email: admin@demo.com")
    print("  Password: Admin@123")
    print("\nDemo Tenant Sales Employee:")
    print("  Email: john@demo.com")
    print("  Password: John@123")
    print("\nPlatform Superadmin Credentials:")
    print("  Email: admin@platform.com")
    print("  Password: Admin@123")
    print("\nData Created:")
    print(f"  ✓ 1 Tenant: {tenant.company_name}")
    print(f"  ✓ 1 Admin Employee: {admin_employee.full_name}")
    print(f"  ✓ 1 Sales Employee: {sales_employee.full_name}")
    print(f"  ✓ 3 Products (Laptop, Mouse, Keyboard)")
    print(f"  ✓ 1 Customer: {customer.name}")
    print(f"  ✓ 1 Order: {order.order_number}")
    print(f"  ✓ 1 Order Item")
    print(f"  ✓ 1 Lead: {lead.name}")
    print("="*60)

except Exception as e:
    db.rollback()
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
