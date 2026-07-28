import enum
import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class RetargetOutcome(str, enum.Enum):
    no_answer = "no_answer"
    callback = "callback"
    interested = "interested"
    purchased_again = "purchased_again"
    not_interested = "not_interested"
    purchased_elsewhere = "purchased_elsewhere"
    invalid_number = "invalid_number"
    risk = "risk"


retarget_outcome_enum = Enum(
    RetargetOutcome,
    name="customer_retarget_outcome",
)


class CustomerRetargetState(Base):
    __tablename__ = "customer_retarget_states"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    current_outcome = Column(retarget_outcome_enum, nullable=False)
    last_call_at = Column(DateTime(timezone=True), nullable=False)
    next_callback_at = Column(DateTime(timezone=True), nullable=True)
    latest_notes = Column(Text, nullable=True)
    last_employee_id = Column(
        UUID(as_uuid=True),
        ForeignKey("employees.id"),
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    customer = relationship("Customer")
    last_employee = relationship("Employee")

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "customer_id",
            name="uq_customer_retarget_state_tenant_customer",
        ),
        Index("ix_customer_retarget_states_tenant", "tenant_id"),
        Index(
            "ix_customer_retarget_states_tenant_outcome",
            "tenant_id",
            "current_outcome",
        ),
        Index(
            "ix_customer_retarget_states_tenant_callback",
            "tenant_id",
            "next_callback_at",
        ),
    )


class CustomerRetargetCall(Base):
    __tablename__ = "customer_retarget_calls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    employee_id = Column(
        UUID(as_uuid=True),
        ForeignKey("employees.id"),
        nullable=False,
    )
    outcome = Column(retarget_outcome_enum, nullable=False)
    phone_called = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)
    next_callback_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    customer = relationship("Customer")
    employee = relationship("Employee")

    __table_args__ = (
        Index(
            "ix_customer_retarget_calls_tenant_customer_created",
            "tenant_id",
            "customer_id",
            "created_at",
        ),
        Index(
            "ix_customer_retarget_calls_tenant_employee",
            "tenant_id",
            "employee_id",
        ),
    )
