"""
Add Phase 5 lead-order integration columns:
- leads.order_id (FK to orders)
- leads.customer_id (FK to customers, for returning customers)
- orders.lead_id (FK to leads)

This enables:
1. Lead → Order workflow (employee can "Move to Order" button)
2. Order → Lead auto-creation (unconfirmed orders create leads)
3. Customer detection (returning customers auto-linked)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic
revision = 'l9m0n1o2p3q4'
down_revision = 'k8l9m0n1o2p3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add customer_id column to leads (for returning customers)
    conn = op.get_bind()
    
    # Check if customer_id already exists
    result = conn.execute(sa.text("""
        SELECT EXISTS(
            SELECT 1 FROM information_schema.columns 
            WHERE table_name='leads' AND column_name='customer_id'
        )
    """))
    customer_id_exists = result.scalar()
    
    if not customer_id_exists:
        op.add_column('leads', sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key('fk_leads_customer_id', 'leads', 'customers', ['customer_id'], ['id'])
        op.create_index('ix_leads_customer_id', 'leads', ['customer_id'])


def downgrade() -> None:
    op.drop_index('ix_leads_customer_id', table_name='leads')
    op.drop_constraint('fk_leads_customer_id', 'leads', type_='foreignkey')
    op.drop_column('leads', 'customer_id')
