"""Add isolated customer retargeting workflow

Revision ID: rtg001_customer_retarget
Revises: z1a2b3c4d5e6
Create Date: 2026-07-28 16:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "rtg001_customer_retarget"
down_revision = "z1a2b3c4d5e6"
branch_labels = None
depends_on = None


retarget_outcome = postgresql.ENUM(
    "no_answer",
    "callback",
    "interested",
    "purchased_again",
    "not_interested",
    "purchased_elsewhere",
    "invalid_number",
    "risk",
    name="customer_retarget_outcome",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    retarget_outcome.create(bind, checkfirst=True)

    op.create_table(
        "customer_retarget_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "current_outcome",
            retarget_outcome,
            nullable=False,
        ),
        sa.Column("last_call_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_callback_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latest_notes", sa.Text(), nullable=True),
        sa.Column("last_employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["last_employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "customer_id",
            name="uq_customer_retarget_state_tenant_customer",
        ),
    )
    op.create_index(
        "ix_customer_retarget_states_tenant",
        "customer_retarget_states",
        ["tenant_id"],
    )
    op.create_index(
        "ix_customer_retarget_states_tenant_outcome",
        "customer_retarget_states",
        ["tenant_id", "current_outcome"],
    )
    op.create_index(
        "ix_customer_retarget_states_tenant_callback",
        "customer_retarget_states",
        ["tenant_id", "next_callback_at"],
    )

    op.create_table(
        "customer_retarget_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("outcome", retarget_outcome, nullable=False),
        sa.Column("phone_called", sa.String(length=20), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("next_callback_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_customer_retarget_calls_tenant_customer_created",
        "customer_retarget_calls",
        ["tenant_id", "customer_id", "created_at"],
    )
    op.create_index(
        "ix_customer_retarget_calls_tenant_employee",
        "customer_retarget_calls",
        ["tenant_id", "employee_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_customer_retarget_calls_tenant_employee",
        table_name="customer_retarget_calls",
    )
    op.drop_index(
        "ix_customer_retarget_calls_tenant_customer_created",
        table_name="customer_retarget_calls",
    )
    op.drop_table("customer_retarget_calls")
    op.drop_index(
        "ix_customer_retarget_states_tenant_callback",
        table_name="customer_retarget_states",
    )
    op.drop_index(
        "ix_customer_retarget_states_tenant_outcome",
        table_name="customer_retarget_states",
    )
    op.drop_index(
        "ix_customer_retarget_states_tenant",
        table_name="customer_retarget_states",
    )
    op.drop_table("customer_retarget_states")
    retarget_outcome.drop(op.get_bind(), checkfirst=True)
