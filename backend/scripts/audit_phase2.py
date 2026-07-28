import sys
import traceback
from sqlalchemy import inspect
from app.database.session import SessionLocal
from app.models.user import User
from app.models.tenant import Tenant
from app.core.security import verify_password, create_access_token
from app.core.config import settings
from jose import jwt

print("\n==============================")
print("   MIGUEL – PHASE 2 AUDIT")
print("==============================\n")

db = SessionLocal()

try:
    # 1️⃣ TABLE VALIDATION
    print("1️⃣ Checking database tables...")

    inspector = inspect(db.bind)
    tables = inspector.get_table_names()

    required_tables = ["tenants", "platform_users", "employees", "alembic_version"]

    for table in required_tables:
        if table in tables:
            print(f"   ✅ Table '{table}' exists")
        else:
            print(f"   ❌ Table '{table}' MISSING")

    # 2️⃣ TENANT VALIDATION
    print("\n2️⃣ Checking tenant existence...")

    tenant = db.query(Tenant).first()
    if tenant:
        print(f"   ✅ Tenant found")
        print(f"      → ID: {tenant.id}")
        print(f"      → Company: {tenant.company_name}")
        print(f"      → Slug: {tenant.slug}")
    else:
        print("   ❌ No tenant found")

    # 3️⃣ SUPERADMIN VALIDATION
    print("\n3️⃣ Checking SuperAdmin user...")

    admin = db.query(User).filter(User.email == "admin@platform.com").first()

    if admin:
        print("   ✅ SuperAdmin exists")
        print(f"      → ID: {admin.id}")
        print(f"      → Role: {admin.role}")
    else:
        print("   ❌ SuperAdmin missing")

    # 4️⃣ PASSWORD VALIDATION
    print("\n4️⃣ Checking password verification...")

    if admin and verify_password("Admin@123", admin.password_hash):
        print("   ✅ Password hashing works")
    else:
        print("   ❌ Password verification FAILED")

    # 5️⃣ JWT GENERATION TEST
    print("\n5️⃣ Checking JWT generation...")

    if admin:
        token = create_access_token(
            data={
                "sub": str(admin.id),
                "role": admin.role,
                "type": "platform",
            }
        )
        print("   ✅ JWT generated successfully")

        # 6️⃣ JWT DECODE TEST
        print("\n6️⃣ Checking JWT decoding...")

        decoded = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
        )

        if decoded.get("sub") == str(admin.id):
            print("   ✅ JWT decode verified")
        else:
            print("   ❌ JWT decode mismatch")

    # 7️⃣ ROLE VALIDATION
    print("\n7️⃣ Checking role integrity...")

    if admin and admin.role == "superadmin":
        print("   ✅ Role is valid")
    else:
        print("   ⚠️ Role not superadmin")

    # 8️⃣ ENVIRONMENT VALIDATION
    print("\n8️⃣ Checking environment configuration...")

    if settings.SECRET_KEY and len(settings.SECRET_KEY) > 10:
        print("   ✅ SECRET_KEY configured properly")
    else:
        print("   ❌ SECRET_KEY missing or too short")

    print("\n==============================")
    print("   PHASE 2 AUDIT COMPLETE")
    print("==============================\n")

except Exception:
    print("\n❌ CRITICAL ERROR DURING AUDIT")
    traceback.print_exc()
    sys.exit(1)

finally:
    db.close()

