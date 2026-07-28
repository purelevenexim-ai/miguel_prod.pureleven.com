"""add vendor payment and rating fields

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-02-21

Adds:
  vendors.payment_terms_days  — credit period in days (e.g. 30 = Net-30)
  vendors.credit_limit        — max credit allowed (decimal)
  vendors.vendor_rating       — 1–5 star rating (smallint)
"""

from alembic import op
import sqlalchemy as sa


revision      = 'f2a3b4c5d6e7'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on    = None


def upgrade():
    op.add_column('vendors', sa.Column('payment_terms_days', sa.Integer(),    nullable=True))
    op.add_column('vendors', sa.Column('credit_limit',       sa.Numeric(14, 2), nullable=True))
    op.add_column('vendors', sa.Column('vendor_rating',      sa.SmallInteger(), nullable=True))


def downgrade():
    op.drop_column('vendors', 'vendor_rating')
    op.drop_column('vendors', 'credit_limit')
    op.drop_column('vendors', 'payment_terms_days')
