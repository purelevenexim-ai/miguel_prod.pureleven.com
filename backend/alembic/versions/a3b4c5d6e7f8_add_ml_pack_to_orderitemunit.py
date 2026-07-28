"""add ml and pack to orderitemunit enum

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-02-21

Adds 'ml' and 'pack' to the orderitemunit PostgreSQL enum
to match ProductUnit enum values.
"""

from alembic import op


revision      = 'a3b4c5d6e7f8'
down_revision = 'f2a3b4c5d6e7'
branch_labels = None
depends_on    = None


def upgrade():
    # Add missing enum values to orderitemunit
    op.execute("ALTER TYPE orderitemunit ADD VALUE IF NOT EXISTS 'ml'")
    op.execute("ALTER TYPE orderitemunit ADD VALUE IF NOT EXISTS 'pack'")


def downgrade():
    # PostgreSQL doesn't support removing enum values easily
    pass
