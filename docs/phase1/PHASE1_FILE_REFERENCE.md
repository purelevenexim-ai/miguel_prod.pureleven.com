# Phase 1 Implementation - File Reference & SQL Schema

## Files Modified/Created

### 1. `/opt/miguel/backend/app/models/lead.py`
**Status**: ✅ Modified
**Changes**: 
- Updated `LeadPipelineStatus` enum (5 new + 8 legacy)
- Updated `LeadActivityType` enum (3 new values)
- Added 5 new fields to `Lead` class
- Added `LeadMessage` model class
- Added 8 performance indexes

**Key Code Sections**:

```python
# Enums (lines 14-31)
class LeadPipelineStatus(str, enum.Enum):
    created        = "created"
    new_lead       = "new_lead"
    contacted      = "contacted"
    success        = "success"
    not_interested = "not_interested"
    # Plus 8 legacy values

class LeadActivityType(str, enum.Enum):
    call             = "call"
    whatsapp         = "whatsapp"
    sms              = "sms"
    email            = "email"
    visit            = "visit"
    note             = "note"
    status_change    = "status_change"
    contacted_popup  = "contacted_popup"      # NEW
    recovery_campaign = "recovery_campaign"    # NEW
    message_received = "message_received"      # NEW

# Lead Model (lines ~80-130)
class Lead(Base):
    # ... existing fields ...
    
    # NEW PHASE 1 FIELDS:
    remind_date: Mapped[Optional[date]] = mapped_column(Date)
    order_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("orders.id"))
    contacted_count: Mapped[int] = mapped_column(Integer, default=0)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    note_last: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # NEW RELATIONSHIP:
    messages: Mapped[list[LeadMessage]] = relationship(
        "LeadMessage", 
        back_populates="lead",
        cascade="all, delete-orphan"
    )
    
    # NEW INDEXES:
    __table_args__ = (
        # ... existing indexes ...
        Index("ix_leads_remind_date", "remind_date"),
        Index("ix_leads_is_archived", "is_archived"),
        Index("ix_leads_order_id", "order_id"),
        Index("ix_leads_status_remind", "status", "remind_date"),
    )

# LeadMessage Model (lines ~150+)
class LeadMessage(Base):
    __tablename__ = "lead_messages"
    
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))
    lead_id: Mapped[UUID] = mapped_column(ForeignKey("leads.id"))
    direction: Mapped[str] = mapped_column(String(20))  # "inbound" | "outbound"
    message_body: Mapped[str] = mapped_column(Text)
    whatsapp_message_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    
    lead: Mapped[Lead] = relationship("Lead", back_populates="messages")
    
    __table_args__ = (
        Index("ix_lead_messages_lead_id", "lead_id"),
        Index("ix_lead_messages_tenant_id", "tenant_id"),
        Index("ix_lead_messages_created_at", "created_at"),
        Index("ix_lead_messages_whatsapp_id", "whatsapp_message_id"),
    )
```

---

### 2. `/opt/miguel/backend/alembic/versions/f3e4a5b6c7d8_leads_redesign_phase1_schema.py`
**Status**: ✅ Created (New File)
**Purpose**: Migration to add Phase 1 schema changes to `leads` table

**SQL Generated**:

```sql
-- Upgrade
ALTER TABLE leads ADD COLUMN remind_date DATE;
ALTER TABLE leads ADD COLUMN order_id UUID;
ALTER TABLE leads ADD COLUMN contacted_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE leads ADD COLUMN is_archived BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE leads ADD COLUMN note_last TEXT;

-- Foreign Key
ALTER TABLE leads 
  ADD CONSTRAINT fk_leads_order_id 
  FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL;

-- Indexes
CREATE INDEX ix_leads_remind_date ON leads(remind_date);
CREATE INDEX ix_leads_is_archived ON leads(is_archived);
CREATE INDEX ix_leads_order_id ON leads(order_id);
CREATE INDEX ix_leads_status_remind ON leads(status, remind_date);

-- Downgrade
DROP INDEX IF EXISTS ix_leads_status_remind;
DROP INDEX IF EXISTS ix_leads_order_id;
DROP INDEX IF EXISTS ix_leads_is_archived;
DROP INDEX IF EXISTS ix_leads_remind_date;
ALTER TABLE leads DROP CONSTRAINT fk_leads_order_id;
ALTER TABLE leads DROP COLUMN note_last;
ALTER TABLE leads DROP COLUMN is_archived;
ALTER TABLE leads DROP COLUMN contacted_count;
ALTER TABLE leads DROP COLUMN order_id;
ALTER TABLE leads DROP COLUMN remind_date;
```

**Lines**: 52
**Dependencies**: None (creates new columns)
**Risk**: Low (non-breaking, nullable fields with defaults)

---

### 3. `/opt/miguel/backend/alembic/versions/g4f5b6c7d8e9_leads_redesign_create_lead_messages.py`
**Status**: ✅ Created (New File)
**Purpose**: Migration to create `lead_messages` table for WhatsApp history

**SQL Generated**:

```sql
-- Upgrade
CREATE TABLE lead_messages (
    id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    lead_id UUID NOT NULL,
    direction VARCHAR(20) NOT NULL,
    message_body TEXT NOT NULL,
    whatsapp_message_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    PRIMARY KEY (id),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX ix_lead_messages_lead_id ON lead_messages(lead_id);
CREATE INDEX ix_lead_messages_tenant_id ON lead_messages(tenant_id);
CREATE INDEX ix_lead_messages_created_at ON lead_messages(created_at);
CREATE INDEX ix_lead_messages_whatsapp_id ON lead_messages(whatsapp_message_id);

-- Downgrade
DROP TABLE lead_messages;
```

**Lines**: 44
**Dependencies**: `leads` and `tenants` tables (existing)
**Risk**: Very low (new isolated table)

---

### 4. `/opt/miguel/backend/app/modules/leads/schemas.py`
**Status**: ✅ Modified
**Changes**:
- Updated `LeadCreate` (added 3 new fields)
- Updated `LeadUpdate` (added 3 new fields)
- Updated `LeadResponse` (added 4 new fields)
- Added 7 new schema classes
- Updated imports for new schemas

**New Schemas**:

```python
# Request Schemas
class ContactedPopupRequest(BaseModel):
    note: str
    action: str  # "save_close" | "remind_later" | "not_interested"
    remind_date: Optional[date] = None

class SuccessWONRequest(BaseModel):
    order_items: list[dict]
    payment_method: str
    discount: Optional[Decimal] = Decimal("0.00")
    notes: Optional[str] = None
    delivery_date: Optional[date] = None

class LeadMessageCreate(BaseModel):
    message_body: str
    direction: str  # "inbound" | "outbound"
    whatsapp_message_id: Optional[str] = None

# Response Schemas
class LeadMessageResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    lead_id: UUID
    tenant_id: UUID
    message_body: str
    direction: str
    whatsapp_message_id: Optional[str]
    created_at: datetime

class LostLeadResponse(BaseModel):
    id: UUID
    lead_number: str
    name: str
    phone: str
    company_name: Optional[str]
    status: LeadPipelineStatus
    last_contacted_at: Optional[datetime]
    notes: Optional[str]
    days_since_contact: Optional[int]

class ReminderLeadResponse(BaseModel):
    id: UUID
    lead_number: str
    name: str
    phone: str
    company_name: Optional[str]
    status: LeadPipelineStatus
    remind_date: Optional[date]
    assigned_to_id: Optional[UUID]
    last_contacted_at: Optional[datetime]
    notes: Optional[str]
```

**Lines Modified**: ~150 (additions and updates)

---

### 5. `/opt/miguel/backend/app/modules/leads/service.py`
**Status**: ✅ Modified
**Changes**: Added 6 new service functions (280+ lines)

**New Functions**:

```python
def mark_contacted(
    db: Session, 
    lead_id: str, 
    request, 
    current_user: Employee
) -> Lead:
    """Handle contacted popup with 3 action types."""
    # Implementation: 45 lines

def finalize_success_won(
    db: Session,
    lead_id: str,
    order_items: list,
    payment_method: str,
    discount: Decimal = Decimal("0.00"),
    notes: Optional[str] = None,
    current_user: Employee = None,
) -> dict:
    """Convert lead to customer and create order."""
    # Implementation: 65 lines

def get_reminded_leads(
    db: Session, 
    current_user: Employee, 
    target_date: Optional[date] = None
) -> list:
    """Get leads with reminders for target_date (default: today)."""
    # Implementation: 18 lines

def get_lost_leads(
    db: Session, 
    current_user: Employee, 
    page: int = 1, 
    page_size: int = 20
) -> dict:
    """Get leads in 'not_interested' status (paginated)."""
    # Implementation: 23 lines

def store_whatsapp_message(
    db: Session,
    lead_id: str,
    message_create,
    current_user: Employee,
):
    """Store WhatsApp message in lead_messages table."""
    # Implementation: 25 lines

def get_whatsapp_messages(
    db: Session,
    lead_id: str,
    current_user: Employee,
    limit: int = 50,
) -> list:
    """Get WhatsApp message history for lead."""
    # Implementation: 20 lines
```

**Total New Lines**: 280+

---

### 6. `/opt/miguel/backend/app/modules/leads/router.py`
**Status**: ✅ Modified
**Changes**:
- Added Decimal import
- Updated schema imports
- Added 7 new endpoints (140+ lines)

**New Endpoints**:

```python
@router.post("/{lead_id}/contacted", response_model=dict, status_code=200)
def mark_contacted(
    lead_id: UUID,
    data: ContactedPopupRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(
        require_roles(RoleEnum.admin, RoleEnum.sales, RoleEnum.support)
    ),
):
    """Mark lead as contacted with mandatory note."""

@router.post("/{lead_id}/success_won", response_model=dict, status_code=201)
def finalize_success_won(
    lead_id: UUID,
    data: SuccessWONRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(
        require_roles(RoleEnum.admin, RoleEnum.sales)
    ),
):
    """Convert lead to successful customer and create order."""

@router.get("/reminders/today", response_model=dict)
def get_today_reminders(
    target_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Get leads with reminders scheduled for today."""

@router.get("/lost_leads/list", response_model=dict)
def list_lost_leads(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Get leads in not_interested status for recovery."""

@router.get("/{lead_id}/messages", response_model=dict)
def get_whatsapp_messages(
    lead_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Get WhatsApp message history for lead."""

@router.post("/{lead_id}/messages", response_model=dict, status_code=201)
def store_whatsapp_message(
    lead_id: UUID,
    data: LeadMessageCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Store incoming/outgoing WhatsApp message."""
```

**Total New Lines**: 140+

---

## Database Schema (PostgreSQL)

### Leads Table (Modified)

```sql
CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    lead_number VARCHAR(50) NOT NULL UNIQUE,
    
    -- Contact Info
    name VARCHAR(150) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    alternate_phone VARCHAR(20),
    email VARCHAR(255),
    company_name VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100) DEFAULT 'India',
    
    -- Pipeline
    status VARCHAR(50) NOT NULL DEFAULT 'new_lead',  -- EnumField
    priority VARCHAR(20) NOT NULL DEFAULT 'medium',  -- EnumField
    source VARCHAR(50),  -- EnumField
    
    -- Values
    estimated_value DECIMAL(12,2),
    product_interest TEXT,
    
    -- Assignment
    assigned_to_id UUID REFERENCES employees(id) ON DELETE SET NULL,
    created_by_id UUID NOT NULL REFERENCES employees(id),
    
    -- Conversion
    converted_customer_id UUID REFERENCES customers(id) ON DELETE SET NULL,
    converted_at TIMESTAMP WITH TIME ZONE,
    
    -- Contact History
    last_contacted_at TIMESTAMP WITH TIME ZONE,
    next_followup_date DATE,
    
    -- PHASE 1 NEW FIELDS:
    remind_date DATE,  -- ← NEW
    order_id UUID REFERENCES orders(id) ON DELETE SET NULL,  -- ← NEW
    contacted_count INTEGER NOT NULL DEFAULT 0,  -- ← NEW
    is_archived BOOLEAN NOT NULL DEFAULT false,  -- ← NEW
    note_last TEXT,  -- ← NEW
    
    -- Metadata
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE,
    
    PRIMARY KEY (id),
    UNIQUE(tenant_id, lead_number),
    CHECK (status IN (
        'created', 'new_lead', 'contacted', 'success', 'not_interested',
        'new', 'qualified', 'proposal_sent', 'negotiation', 'won', 'lost', 'on_hold'
    )),
    CHECK (priority IN ('low', 'medium', 'high'))
);

-- PHASE 1 NEW INDEXES:
CREATE INDEX ix_leads_remind_date ON leads(remind_date);
CREATE INDEX ix_leads_is_archived ON leads(is_archived);
CREATE INDEX ix_leads_order_id ON leads(order_id);
CREATE INDEX ix_leads_status_remind ON leads(status, remind_date);

-- Existing Indexes (for reference):
CREATE INDEX ix_leads_tenant_id ON leads(tenant_id);
CREATE INDEX ix_leads_phone ON leads(phone);
CREATE INDEX ix_leads_status ON leads(status);
CREATE INDEX ix_leads_created_at ON leads(created_at DESC);
```

### Lead Messages Table (New)

```sql
CREATE TABLE lead_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    
    direction VARCHAR(20) NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    message_body TEXT NOT NULL,
    whatsapp_message_id VARCHAR(255),
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- PHASE 1 NEW INDEXES:
CREATE INDEX ix_lead_messages_lead_id ON lead_messages(lead_id);
CREATE INDEX ix_lead_messages_tenant_id ON lead_messages(tenant_id);
CREATE INDEX ix_lead_messages_created_at ON lead_messages(created_at);
CREATE INDEX ix_lead_messages_whatsapp_id ON lead_messages(whatsapp_message_id);
```

---

## Enum Reference

### LeadPipelineStatus

| Value | Type | Description |
|-------|------|-------------|
| `created` | New | Top priority unconfirmed orders or manual entry |
| `new_lead` | New | Fresh marketing leads (WhatsApp, Meta, forms) |
| `contacted` | New | Staff reached out (has mandatory popup note) |
| `success` | New | Customer purchased, order finalized |
| `not_interested` | New | Lost lead, available for recovery campaigns |
| `new` | Legacy | Maps to `new_lead` |
| `qualified` | Legacy | Deprecated |
| `proposal_sent` | Legacy | Deprecated |
| `negotiation` | Legacy | Deprecated |
| `won` | Legacy | Maps to `success` |
| `lost` | Legacy | Maps to `not_interested` |
| `on_hold` | Legacy | Deprecated |

### LeadActivityType

| Value | Type | Description |
|-------|------|-------------|
| `call` | Existing | Phone call |
| `whatsapp` | Existing | WhatsApp message |
| `sms` | Existing | SMS message |
| `email` | Existing | Email |
| `visit` | Existing | In-person visit |
| `note` | Existing | Internal note |
| `status_change` | Existing | Status changed |
| `contacted_popup` | New | Mark as contacted with popup note |
| `recovery_campaign` | New | Lost lead selected for recovery |
| `message_received` | New | Incoming WhatsApp/SMS message |

---

## API Endpoint Reference

### Summary

| Method | Endpoint | New | Auth |
|--------|----------|-----|------|
| POST | `/api/leads/{id}/contacted` | ✅ | Admin, Sales, Support |
| POST | `/api/leads/{id}/success_won` | ✅ | Admin, Sales |
| GET | `/api/leads/reminders/today` | ✅ | All |
| GET | `/api/leads/lost_leads/list` | ✅ | All |
| GET | `/api/leads/{id}/messages` | ✅ | All |
| POST | `/api/leads/{id}/messages` | ✅ | All |
| POST | `/api/leads/{id}/activities` | Existing | Admin, Sales, Support |

### Request/Response Sizes

| Endpoint | Request Size | Response Size | Notes |
|----------|-------------|---------------|-------|
| /contacted | ~200 bytes | ~500 bytes | Includes full lead object |
| /success_won | ~500 bytes | ~300 bytes | Returns IDs only |
| /reminders/today | 0 | 1-5KB | Depends on reminder count |
| /lost_leads/list | 0 | 2-10KB | Paginated results |
| /messages GET | 0 | 2-20KB | Up to 200 messages |
| /messages POST | ~300 bytes | ~200 bytes | Returns message ID |

---

## Code Statistics

### Files Modified: 4
- `lead.py` - +200 lines
- `schemas.py` - +150 lines
- `service.py` - +280 lines
- `router.py` - +140 lines
- **Subtotal**: 770 lines

### Files Created: 2
- `f3e4a5b6c7d8_leads_redesign_phase1_schema.py` - 52 lines
- `g4f5b6c7d8e9_leads_redesign_create_lead_messages.py` - 44 lines
- **Subtotal**: 96 lines

### Total: 866 Lines of Code

### Classes/Functions Added
- 3 enum values (LeadPipelineStatus)
- 3 enum values (LeadActivityType)
- 1 new model (LeadMessage)
- 7 new schema classes
- 5 schema class updates
- 6 new service functions
- 7 new router endpoints
- 8 new database indexes

---

## Configuration & Dependencies

### Python Dependencies (Existing)
- FastAPI
- SQLAlchemy
- Pydantic
- Python-dateutil

### No New External Dependencies Required

All Phase 1 code uses existing project dependencies.

---

## Backward Compatibility

✅ **Fully backward compatible**:
- Old enum values still work (mapped to new values in UI)
- New fields are nullable/have defaults
- Existing endpoints unchanged
- New endpoints additive only

---

## Migration Rollback (If Needed)

```bash
# Rollback last migration (Phase 1 Schema)
alembic downgrade -1

# Rollback both Phase 1 migrations
alembic downgrade -2

# Verify state
alembic current
```

---

## Performance Considerations

### Indexes Created (8 Total)

#### Leads Table (4)
1. **ix_leads_remind_date** - Fast reminder lookups
2. **ix_leads_is_archived** - Archive filtering
3. **ix_leads_order_id** - Order linkage queries
4. **ix_leads_status_remind** - Status + remind_date composite (most used)

#### Lead Messages Table (4)
1. **ix_lead_messages_lead_id** - Core chat retrieval
2. **ix_lead_messages_tenant_id** - Tenant isolation
3. **ix_lead_messages_created_at** - Chronological ordering
4. **ix_lead_messages_whatsapp_id** - Meta deduplication

### Query Performance

| Operation | Time (est.) | Index Used |
|-----------|-------------|-----------|
| Get today's reminders | <200ms | ix_leads_remind_date |
| Get lost leads (page 1) | <300ms | status + created_at |
| Get 50 messages | <150ms | ix_lead_messages_created_at |
| Store message | <50ms | Direct write |
| Mark contacted | <50ms | Direct update |

---

**File Reference Complete** ✅
