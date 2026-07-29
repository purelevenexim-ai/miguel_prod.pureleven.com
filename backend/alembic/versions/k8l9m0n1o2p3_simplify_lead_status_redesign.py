"""
Simplify lead pipeline status to match user-defined workflow:
- CREATED: Always at top (new leads from manual/order page)
- NEW_LEAD: Fresh leads from WhatsApp/marketing tools
- CONTACTED: After contact attempt with mandatory note → 3 outcomes
- REMIND_LATER: Follow-up scheduled for specific date (top priority)
- SUCCESS_WON: Customer purchased, converted to customer record
- LOST_LEAD: Not interested (recovery campaign candidate)

Removes: qualified, proposal_sent, negotiation, on_hold, won (→ success_won), not_interested (→ lost_lead)
Adds: remind_later (new status with date scheduling)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = 'k8l9m0n1o2p3'
down_revision = 'j7k8l9m0n1o2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    
    # Create new enum type
    conn.execute(sa.text("""
        CREATE TYPE leadpipelinestatus_new AS ENUM (
            'created',
            'new_lead',
            'contacted',
            'remind_later',
            'success_won',
            'lost_lead'
        )
    """))
    
    # Alter column using mapping from old to new values
    conn.execute(sa.text("""
        ALTER TABLE leads 
        ALTER COLUMN status TYPE leadpipelinestatus_new 
        USING CASE 
            WHEN status::text IN ('new', 'qualified') THEN 'new_lead'::leadpipelinestatus_new
            WHEN status::text IN ('proposal_sent', 'negotiation', 'contacted') THEN 'contacted'::leadpipelinestatus_new
            WHEN status::text IN ('won', 'success') THEN 'success_won'::leadpipelinestatus_new
            WHEN status::text IN ('lost', 'not_interested') THEN 'lost_lead'::leadpipelinestatus_new
            WHEN status::text = 'on_hold' THEN 'remind_later'::leadpipelinestatus_new
            WHEN status::text = 'new_lead' THEN 'new_lead'::leadpipelinestatus_new
            WHEN status::text = 'created' THEN 'created'::leadpipelinestatus_new
            ELSE 'new_lead'::leadpipelinestatus_new
        END
    """))
    
    # Drop old enum and rename new one
    conn.execute(sa.text("DROP TYPE leadpipelinestatus CASCADE"))
    conn.execute(sa.text("ALTER TYPE leadpipelinestatus_new RENAME TO leadpipelinestatus"))
    
    # Add remind_later_date column
    conn.execute(sa.text("""
        ALTER TABLE leads ADD COLUMN IF NOT EXISTS remind_later_date DATE NULL
    """))


def downgrade() -> None:
    conn = op.get_bind()
    
    # Recreate old enum
    conn.execute(sa.text("""
        CREATE TYPE leadpipelinestatus_old AS ENUM (
            'new',
            'contacted',
            'qualified',
            'proposal_sent',
            'negotiation',
            'won',
            'lost',
            'on_hold',
            'new_lead',
            'created',
            'success',
            'not_interested',
            'follow_up'
        )
    """))
    
    # Reverse mapping
    conn.execute(sa.text("""
        ALTER TABLE leads 
        ALTER COLUMN status TYPE leadpipelinestatus_old 
        USING CASE 
            WHEN status::text = 'new_lead' THEN 'new_lead'::leadpipelinestatus_old
            WHEN status::text = 'contacted' THEN 'contacted'::leadpipelinestatus_old
            WHEN status::text = 'success_won' THEN 'won'::leadpipelinestatus_old
            WHEN status::text = 'lost_lead' THEN 'lost'::leadpipelinestatus_old
            WHEN status::text = 'remind_later' THEN 'on_hold'::leadpipelinestatus_old
            WHEN status::text = 'created' THEN 'created'::leadpipelinestatus_old
            ELSE 'new_lead'::leadpipelinestatus_old
        END
    """))
    
    # Drop new enum and rename old one
    conn.execute(sa.text("DROP TYPE leadpipelinestatus CASCADE"))
    conn.execute(sa.text("ALTER TYPE leadpipelinestatus_old RENAME TO leadpipelinestatus"))
    
    # Drop new column
    conn.execute(sa.text("ALTER TABLE leads DROP COLUMN IF EXISTS remind_later_date"))
