"""Fix lead_activities: add old_status/new_status columns, clean up remind_date, add activity enum values

Revision ID: m0n1o2p3q4r5
Revises: l9m0n1o2p3q4
Create Date: 2026-02-22
"""
from alembic import op
import sqlalchemy as sa

revision = "m0n1o2p3q4r5"
down_revision = "l9m0n1o2p3q4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add old_status and new_status to lead_activities (already applied via raw SQL)
    conn = op.get_bind()
    cols = [r[0] for r in conn.execute(sa.text(
        "SELECT column_name FROM information_schema.columns WHERE table_name='lead_activities'"
    )).fetchall()]

    if "old_status" not in cols:
        op.add_column("lead_activities", sa.Column("old_status", sa.String(50), nullable=True))
    if "new_status" not in cols:
        op.add_column("lead_activities", sa.Column("new_status", sa.String(50), nullable=True))

    # 2. Drop old remind_date column from leads if it exists
    lead_cols = [r[0] for r in conn.execute(sa.text(
        "SELECT column_name FROM information_schema.columns WHERE table_name='leads'"
    )).fetchall()]
    if "remind_date" in lead_cols:
        op.drop_column("leads", "remind_date")

    # 3. Enum values for leadactivitytype already added via separate ALTER TYPE commands


def downgrade() -> None:
    op.drop_column("lead_activities", "new_status")
    op.drop_column("lead_activities", "old_status")
    op.add_column("leads", sa.Column("remind_date", sa.Date(), nullable=True))
