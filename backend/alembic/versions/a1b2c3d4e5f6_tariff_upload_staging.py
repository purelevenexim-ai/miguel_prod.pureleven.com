"""add tariff_upload_staging table

Revision ID: a1b2c3d4e5f6
Revises: z4a5b6c7d8e9
Create Date: 2026-05-03 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from typing import Sequence, Union

revision = 'tus001_tariff_upload_staging'
down_revision: Union[str, Sequence[str], None] = 'z4a5b6c7d8e9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'tariff_upload_staging',
        sa.Column('id',               postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id',        postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('upload_batch_id',  postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('uploaded_by',      postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('xlsx_row_num',     sa.Integer, nullable=True),

        # Raw data from the XLSX row
        sa.Column('xlsx_tracking',       sa.String(60),  nullable=True),
        sa.Column('xlsx_order_ref',      sa.String(80),  nullable=True),
        sa.Column('xlsx_customer_name',  sa.String(200), nullable=True),
        sa.Column('xlsx_amount',         sa.Numeric(10, 2), nullable=True),
        sa.Column('xlsx_weight',         sa.Numeric(10, 3), nullable=True),
        sa.Column('xlsx_status_text',    sa.String(200), nullable=True),

        # Match result
        sa.Column('order_id',       postgresql.UUID(as_uuid=True), sa.ForeignKey('orders.id', ondelete='SET NULL'), nullable=True),
        sa.Column('order_number',   sa.String(80), nullable=True),
        sa.Column('match_method',   sa.String(40), nullable=True),
        # tracking_exact | order_number_exact | name_amount_close | pincode_match | sku_fallback | unmatched

        # Confidence: high | medium | low | none
        sa.Column('confidence', sa.String(10), nullable=False, server_default='none'),

        # Validation gates
        sa.Column('tracking_valid',    sa.Boolean, nullable=False, server_default='false'),
        sa.Column('amount_valid',      sa.Boolean, nullable=False, server_default='false'),
        sa.Column('amount_suspicious', sa.Boolean, nullable=False, server_default='false'),

        # Diff: what is on the order now vs what we propose
        sa.Column('current_tracking',  sa.String(60),     nullable=True),
        sa.Column('proposed_tracking', sa.String(60),     nullable=True),
        sa.Column('current_shipping',  sa.Numeric(10, 2), nullable=True),
        sa.Column('proposed_shipping', sa.Numeric(10, 2), nullable=True),

        # Review state: pending | approved | rejected | applied
        sa.Column('review_status',    sa.String(20), nullable=False, server_default='pending'),
        sa.Column('reviewed_by',      postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reviewed_at',      sa.DateTime(timezone=True), nullable=True),
        sa.Column('applied_at',       sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text, nullable=True),
        sa.Column('apply_error',      sa.Text, nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_tus_tenant_batch',   'tariff_upload_staging', ['tenant_id', 'upload_batch_id'])
    op.create_index('ix_tus_order_id',       'tariff_upload_staging', ['order_id'])
    op.create_index('ix_tus_review_status',  'tariff_upload_staging', ['tenant_id', 'review_status'])
    op.create_index('ix_tus_batch_created',  'tariff_upload_staging', ['tenant_id', 'upload_batch_id', 'created_at'])


def downgrade():
    op.drop_table('tariff_upload_staging')
