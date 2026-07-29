"""add_activity_logs_table

Revision ID: a1b2c3d4e5f6
Revises: 458418b9b413
Create Date: 2026-02-21 00:00:00.000000

Creates activity_logs table with:
- Tenant-scoped log entries
- 6-hour TTL via expires_at column
- Composite indexes for fast queries
- JSONB detail column for structured context
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'a1b2c3d4e5f6'
down_revision = '458418b9b413'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # ── Create enums only if they don't exist ─────────────────
    bind.execute(sa.text("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'loglevel') THEN
                CREATE TYPE loglevel AS ENUM ('INFO', 'WARNING', 'ERROR', 'CRITICAL');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'logmodule') THEN
                CREATE TYPE logmodule AS ENUM (
                    'auth', 'orders', 'customers', 'leads', 'products',
                    'inventory', 'invoices', 'vendors', 'purchases',
                    'labels', 'meta', 'reporting', 'employees', 'platform', 'system'
                );
            END IF;
        END
        $$;
    """))

    # ── Create activity_logs table ────────────────────────────
    op.create_table(
        'activity_logs',

        sa.Column('id',          postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),

        # Tenant scope
        sa.Column('tenant_id',   postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'),
                  nullable=True),

        # Actor
        sa.Column('actor_id',    postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('actor_email', sa.String(255),  nullable=True),
        sa.Column('actor_role',  sa.String(50),   nullable=True),
        sa.Column('actor_ip',    sa.String(45),   nullable=True),

        # Classification
        sa.Column('module',      sa.String(50),  nullable=False),
        sa.Column('action',      sa.String(100),  nullable=False),

        # Outcome
        sa.Column('level',       sa.String(20),
                  nullable=False, server_default='INFO'),
        sa.Column('status_code', sa.Integer(),    nullable=True),
        sa.Column('message',     sa.Text(),       nullable=True),
        sa.Column('detail',      postgresql.JSONB(), nullable=True),

        # Request context
        sa.Column('method',      sa.String(10),   nullable=True),
        sa.Column('path',        sa.String(500),  nullable=True),
        sa.Column('user_agent',  sa.Text(),       nullable=True),

        # Timestamps
        sa.Column('created_at',  sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at',  sa.DateTime(timezone=True), nullable=False),
    )

    # ── Indexes ───────────────────────────────────────────────
    op.create_index('ix_actlog_tenant_id',      'activity_logs', ['tenant_id'])
    op.create_index('ix_actlog_module',         'activity_logs', ['module'])
    op.create_index('ix_actlog_action',         'activity_logs', ['action'])
    op.create_index('ix_actlog_level',          'activity_logs', ['level'])
    op.create_index('ix_actlog_created_at',     'activity_logs', ['created_at'])
    op.create_index('ix_actlog_expires',        'activity_logs', ['expires_at'])
    op.create_index('ix_actlog_tenant_created', 'activity_logs', ['tenant_id', 'created_at'])
    op.create_index('ix_actlog_tenant_level',   'activity_logs', ['tenant_id', 'level'])


def downgrade() -> None:
    op.drop_table('activity_logs')

    op.execute("DROP TYPE IF EXISTS loglevel")
    op.execute("DROP TYPE IF EXISTS logmodule")
