"""Add order tracking metadata

Revision ID: u1v2w3x4y5z6
Revises: tus001_tariff_upload_staging
Create Date: 2026-05-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "u1v2w3x4y5z6"
down_revision = "tus001_tariff_upload_staging"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("orders", sa.Column("tracking_status_text", sa.String(length=120), nullable=True))
    op.add_column("orders", sa.Column("tracking_last_location", sa.String(length=255), nullable=True))
    op.add_column("orders", sa.Column("tracking_last_event_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("tracking_synced_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("tracking_events_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("orders", sa.Column("tracking_raw_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("orders", sa.Column("return_status", sa.String(length=120), nullable=True))
    op.add_column("orders", sa.Column("actual_shipping_cost", sa.Numeric(12, 2), nullable=True))
    op.create_index("ix_orders_tracking_synced_at", "orders", ["tracking_synced_at"])


def downgrade():
    op.drop_index("ix_orders_tracking_synced_at", table_name="orders")
    op.drop_column("orders", "actual_shipping_cost")
    op.drop_column("orders", "return_status")
    op.drop_column("orders", "tracking_raw_response")
    op.drop_column("orders", "tracking_events_json")
    op.drop_column("orders", "tracking_synced_at")
    op.drop_column("orders", "tracking_last_event_at")
    op.drop_column("orders", "tracking_last_location")
    op.drop_column("orders", "tracking_status_text")
