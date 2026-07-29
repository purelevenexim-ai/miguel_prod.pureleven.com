"""add shopify to leadsource enum

Revision ID: z3a4b5c6d7e8
Revises: x1y2z3a4b5c6
Create Date: 2026-03-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'z3a4b5c6d7e8'
down_revision = 'x1y2z3a4b5c6'
branch_labels = None
depends_on = None


def upgrade():
    # Add 'shopify' to the leadsource enum in PostgreSQL
    op.execute("ALTER TYPE leadsource ADD VALUE IF NOT EXISTS 'shopify'")


def downgrade():
    # PostgreSQL does not support removing enum values, so this is a no-op
    pass
