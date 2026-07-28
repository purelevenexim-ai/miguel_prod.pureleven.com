import uuid
from app.database.session import SessionLocal
import app.models  # noqa: F401 – ensure all models are registered with SQLAlchemy mapper
from app.models.user import User
from app.core.security import hash_password

db = SessionLocal()

try:
    existing_admin = db.query(User).filter(User.email == "admin@platform.com").first()

    if not existing_admin:
        admin = User(
            id=uuid.uuid4(),
            email="admin@platform.com",
            password_hash=hash_password("Admin@123"),
            role="superadmin",
        )
        db.add(admin)
        db.commit()
        print("✅ SuperAdmin created: admin@platform.com")
    else:
        print("ℹ️  SuperAdmin already exists.")

finally:
    db.close()

