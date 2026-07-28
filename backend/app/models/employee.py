import enum
import uuid
from sqlalchemy import Column, String, Boolean, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import Base


class RoleEnum(str, enum.Enum):
    admin = "admin"
    sales = "sales"
    marketing = "marketing"
    operations = "operations"
    support = "support"


class Employee(Base):
    __tablename__ = "employees"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False, index=True)
    phone = Column(String, nullable=True)

    hashed_password = Column(String, nullable=False)
    role = Column(Enum(RoleEnum), nullable=False)

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)

    # Relationship
    tenant = relationship("Tenant", back_populates="employees")

    # Composite unique constraint (email unique per tenant)
    __table_args__ = (
        UniqueConstraint("email", "tenant_id", name="uq_employee_email_tenant"),
    )
