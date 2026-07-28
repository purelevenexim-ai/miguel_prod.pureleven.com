# LEADS REDESIGN — DETAILED IMPLEMENTATION ROADMAP

## 📋 PHASE 1: CORE BACKEND (Days 1-2)

### 1.1 Database Schema Updates

#### Migration 1: Update Lead Model Fields
**File**: `/opt/miguel/backend/alembic/versions/<timestamp>_update_leads_schema.py`

**Changes**:
```python
# Add columns
ALTER TABLE leads:
  + remind_date DATE NULL                    # When to remind staff
  + order_id UUID REFERENCES orders(id)      # Link to unconfirmed order
  + contacted_count INT DEFAULT 0            # Track engagement
  + is_archived BOOLEAN DEFAULT FALSE         # For not_interested leads
  + note_last TEXT NULL                      # Last contacted popup note

# Update indexes
  + INDEX(remind_date, status)               # For reminder queries
  + INDEX(is_archived, updated_at)           # For lost leads
  + INDEX(last_contacted_at)                 # For 48hr highlight
  + INDEX(order_id)                          # For order lookups
```

#### Migration 2: Create LeadMessage Table
**File**: `/opt/miguel/backend/alembic/versions/<timestamp>_create_lead_messages.py`

```python
CREATE TABLE lead_messages:
  id UUID PRIMARY KEY
  tenant_id UUID REFERENCES tenants(id)
  lead_id UUID REFERENCES leads(id)
  direction VARCHAR(20)  # 'inbound', 'outbound'
  message_body TEXT
  whatsapp_message_id VARCHAR(100) NULL  # External ID from WhatsApp API
  created_at DATETIME DEFAULT now()
  INDEXES: lead_id, (lead_id, direction), created_at
```

#### Migration 3: Update Enums
**File**: `/opt/miguel/backend/alembic/versions/<timestamp>_update_lead_enums.py`

```python
# Update LeadPipelineStatus
ALTER TYPE leadpipelinestatus ADD VALUES ('created', 'new_lead', 'success');
# Mark old values as deprecated: 'new', 'qualified', 'proposal_sent', 'negotiation', 'on_hold'
# Keep 'contacted', 'won', 'lost' (map: won→success, lost→not_interested)

# Add new LeadActivityType values
ALTER TYPE leadactivitytype ADD VALUES ('contacted_popup', 'recovery_campaign', 'message_received');
```

### 1.2 Model Updates

**File**: `/opt/miguel/backend/app/models/lead.py`

```python
# Update LeadPipelineStatus enum
class LeadPipelineStatus(str, enum.Enum):
    created        = "created"
    new_lead       = "new_lead"
    contacted      = "contacted"
    success        = "success"
    not_interested = "not_interested"

# Add fields to Lead model
class Lead(Base):
    # ... existing fields ...
    
    # NEW FIELDS
    remind_date           = Column(Date, nullable=True)
    order_id              = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True)
    contacted_count       = Column(Integer, default=0, nullable=False)
    is_archived           = Column(Boolean, default=False, nullable=False)
    note_last             = Column(Text, nullable=True)
    
    # NEW RELATIONSHIP
    order                 = relationship("Order", foreign_keys=[order_id])

# NEW LeadMessage model
class LeadMessage(Base):
    __tablename__ = "lead_messages"
    
    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id   = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    lead_id     = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False)
    direction   = Column(String(20), nullable=False)  # 'inbound', 'outbound'
    message_body = Column(Text, nullable=False)
    whatsapp_message_id = Column(String(100), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    
    lead        = relationship("Lead", back_populates="messages")
    
    __table_args__ = (
        Index("ix_lead_messages_lead_id", "lead_id"),
        Index("ix_lead_messages_direction", "lead_id", "direction"),
        Index("ix_lead_messages_created_at", "created_at"),
    )
```

### 1.3 Schema Updates

**File**: `/opt/miguel/backend/app/modules/leads/schemas.py`

```python
# NEW: Contacted popup request
class ContactedPopupRequest(BaseModel):
    note: str  # Required: what customer said
    action: Literal["lost_lead", "remind_later", "success_won"]
    remind_date: Optional[date] = None  # Required if action = "remind_later"

# NEW: Success WON request
class SuccessWONRequest(BaseModel):
    order_data: dict  # Order items, payment, discount, etc. (from mini editor)
    # Backend will create order + customer + finalize conversion

# NEW: Lead message
class LeadMessageCreate(BaseModel):
    message_body: str
    direction: Literal["inbound", "outbound"]
    whatsapp_message_id: Optional[str] = None

class LeadMessageResponse(BaseModel):
    id: UUID
    lead_id: UUID
    message_body: str
    direction: str
    created_at: datetime
    
    model_config = {"from_attributes": True}

# UPDATE: LeadCreate/Update
class LeadCreate(BaseModel):
    # ... existing fields ...
    order_id: Optional[UUID] = None  # NEW

class LeadUpdate(BaseModel):
    # ... existing fields ...
    order_id: Optional[UUID] = None
    remind_date: Optional[date] = None
    is_archived: Optional[bool] = None
```

### 1.4 Service Layer

**File**: `/opt/miguel/backend/app/modules/leads/service.py`

```python
# NEW FUNCTIONS

def mark_contacted(
    db: Session,
    lead_id: str,
    current_user: Employee,
    request: ContactedPopupRequest,
) -> Lead:
    """
    Execute Contacted workflow:
    - If action='lost_lead' → status=not_interested, is_archived=True
    - If action='remind_later' → remind_date=<date>, status=contacted
    - If action='success_won' → return lead (caller opens mini editor)
    """
    lead = get_lead(db, lead_id, current_user)
    
    # Log activity
    activity = LeadActivity(
        tenant_id=current_user.tenant_id,
        lead_id=lead.id,
        employee_id=current_user.id,
        activity_type=LeadActivityType.contacted_popup,
        note=request.note,
        old_status=lead.status,
    )
    
    if request.action == "lost_lead":
        lead.status = LeadPipelineStatus.not_interested
        lead.is_archived = True
        activity.new_status = LeadPipelineStatus.not_interested
    
    elif request.action == "remind_later":
        lead.remind_date = request.remind_date
        lead.status = LeadPipelineStatus.contacted  # stays contacted
        activity.new_status = LeadPipelineStatus.contacted
    
    elif request.action == "success_won":
        # Mark for WON flow (mini editor will finalize)
        lead.status = LeadPipelineStatus.contacted  # stays, mini editor decides
        activity.new_status = None  # Don't log yet, wait for order finalization
    
    lead.note_last = request.note
    lead.last_contacted_at = datetime.now(timezone.utc)
    lead.contacted_count += 1
    
    db.add(activity)
    db.commit()
    db.refresh(lead)
    return lead


def finalize_success_won(
    db: Session,
    lead_id: str,
    order_items: list,  # [{product_id, quantity, unit_price}, ...]
    payment_method: PaymentMethod,
    discount: Decimal = Decimal(0),
    current_user: Employee = None,
) -> dict:
    """
    Finalize WON lead:
    1. Create/update Order with status=confirmed
    2. Auto-create Customer
    3. Link order → customer → lead
    4. Move lead to success
    5. Return success response
    """
    lead = get_lead(db, lead_id, current_user)
    
    # Create Customer from Lead
    customer_code = _generate_unique_customer_code(db, lead.tenant_id)
    customer = Customer(
        tenant_id=lead.tenant_id,
        unique_customer_code=customer_code,
        name=lead.name,
        phone=lead.phone,
        email=lead.email,
        city=lead.city,
        state=lead.state,
        lead_status=LeadStatus.converted,
        source=SourceType(lead.source.value) if lead.source else SourceType.manual,
        created_by_employee_id=current_user.id,
    )
    db.add(customer)
    db.flush()
    
    # Create Order (confirmed)
    order = Order(
        tenant_id=lead.tenant_id,
        order_number=_generate_order_number(db, lead.tenant_id),
        customer_id=customer.id,
        status=OrderStatus.confirmed,
        payment_method=payment_method,
        delivery_city=lead.city,
        delivery_state=lead.state,
    )
    
    # Add order items + calculate totals
    subtotal = Decimal(0)
    for item_data in order_items:
        item_total = item_data['quantity'] * item_data['unit_price']
        subtotal += item_total
        order_item = OrderItem(
            order_id=order.id,
            product_id=item_data['product_id'],
            quantity=item_data['quantity'],
            unit_price=item_data['unit_price'],
            total_price=item_total,
        )
        db.add(order_item)
    
    order.subtotal = subtotal
    order.discount_amount = discount
    order.total_amount = subtotal - discount
    db.add(order)
    db.flush()
    
    # Update Lead
    lead.converted_customer_id = customer.id
    lead.converted_at = datetime.now(timezone.utc)
    lead.converted_by_id = current_user.id
    lead.status = LeadPipelineStatus.success
    lead.order_id = order.id
    
    # Log activity
    activity = LeadActivity(
        tenant_id=lead.tenant_id,
        lead_id=lead.id,
        employee_id=current_user.id,
        activity_type=LeadActivityType.status_change,
        note=f"Lead converted to customer. Order: {order.order_number}",
        old_status=LeadPipelineStatus.contacted,
        new_status=LeadPipelineStatus.success,
    )
    db.add(activity)
    
    db.commit()
    db.refresh(lead)
    
    return {
        "success": True,
        "customer_id": str(customer.id),
        "order_id": str(order.id),
        "order_number": order.order_number,
        "lead_id": str(lead.id),
    }


def get_reminded_leads(db: Session, current_user: Employee, target_date: date = None) -> list:
    """
    Fetch leads where remind_date <= target_date (default: today)
    Shows 1 day before + on reminder date
    """
    if not target_date:
        target_date = date.today()
    
    query = db.query(Lead).filter(
        Lead.tenant_id == current_user.tenant_id,
        Lead.remind_date <= target_date,
        Lead.remind_date.isnot(None),
    ).order_by(Lead.remind_date.asc())
    
    return query.all()


def get_lost_leads(db: Session, current_user: Employee, page: int = 1, page_size: int = 20) -> dict:
    """
    Fetch archived (not_interested) leads
    Paginated for performance
    """
    query = db.query(Lead).filter(
        Lead.tenant_id == current_user.tenant_id,
        Lead.is_archived == True,
    ).order_by(Lead.updated_at.desc())
    
    total = query.count()
    leads = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "results": [LeadResponse.model_validate(l) for l in leads],
    }


def store_whatsapp_message(
    db: Session,
    lead_id: str,
    message_create: LeadMessageCreate,
    current_user: Employee,
) -> LeadMessage:
    """Store WhatsApp message in history"""
    lead = get_lead(db, lead_id, current_user)
    
    msg = LeadMessage(
        tenant_id=current_user.tenant_id,
        lead_id=lead.id,
        message_body=message_create.message_body,
        direction=message_create.direction,
        whatsapp_message_id=message_create.whatsapp_message_id,
    )
    
    # Log activity if inbound
    if message_create.direction == "inbound":
        lead.last_contacted_at = datetime.now(timezone.utc)
        activity = LeadActivity(
            tenant_id=current_user.tenant_id,
            lead_id=lead.id,
            employee_id=current_user.id,
            activity_type=LeadActivityType.message_received,
            note=message_create.message_body[:200],  # First 200 chars
        )
        db.add(activity)
    
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def get_whatsapp_messages(
    db: Session,
    lead_id: str,
    current_user: Employee,
    limit: int = 50,
) -> list:
    """Fetch WhatsApp message history (latest first)"""
    lead = get_lead(db, lead_id, current_user)
    
    messages = db.query(LeadMessage).filter(
        LeadMessage.lead_id == lead.id
    ).order_by(LeadMessage.created_at.desc()).limit(limit).all()
    
    return list(reversed(messages))  # Reverse to show oldest first
```

### 1.5 Router Updates

**File**: `/opt/miguel/backend/app/modules/leads/router.py`

```python
# NEW ENDPOINTS

@router.post("/{lead_id}/contacted")
def mark_lead_contacted(
    lead_id: UUID,
    request: ContactedPopupRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.sales, RoleEnum.admin)),
):
    """Mark lead as contacted + execute popup action"""
    return service.mark_contacted(db, str(lead_id), current_user, request)


@router.post("/{lead_id}/success_won")
def finalize_success_won_order(
    lead_id: UUID,
    request: SuccessWONRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.sales, RoleEnum.admin)),
):
    """Finalize WON lead → create order + customer"""
    return service.finalize_success_won(
        db,
        str(lead_id),
        request.order_data['items'],
        PaymentMethod(request.order_data['payment_method']),
        Decimal(request.order_data.get('discount', 0)),
        current_user,
    )


@router.get("/reminded_today")
def get_today_reminders(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Get leads with reminder due today"""
    leads = service.get_reminded_leads(db, current_user)
    return {
        "total": len(leads),
        "results": [LeadResponse.model_validate(l) for l in leads],
    }


@router.get("/lost_leads")
def list_lost_leads(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Get archived (not interested) leads"""
    return service.get_lost_leads(db, current_user, page, page_size)


@router.get("/{lead_id}/messages")
def get_lead_chat_history(
    lead_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Fetch WhatsApp chat history for lead"""
    messages = service.get_whatsapp_messages(db, str(lead_id), current_user)
    return {
        "lead_id": str(lead_id),
        "messages": [
            LeadMessageResponse.model_validate(m) for m in messages
        ],
    }


@router.post("/{lead_id}/messages")
def send_whatsapp_message(
    lead_id: UUID,
    request: LeadMessageCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.sales, RoleEnum.admin)),
):
    """Send WhatsApp message + store in history"""
    msg = service.store_whatsapp_message(db, str(lead_id), request, current_user)
    
    # TODO: Send via WhatsApp API (Phase 2)
    # if request.direction == "outbound":
    #     whatsapp_service.send_message(lead.phone, request.message_body)
    
    return LeadMessageResponse.model_validate(msg)
```

### 1.6 Order → Lead Link Logic

**File**: `/opt/miguel/backend/app/modules/orders/service.py` (Update existing)

```python
# In create_order() or update_order_status() when transitioning to draft:

def _create_or_reuse_lead_for_draft_order(db, order, current_user):
    """
    When order created but not confirmed (draft):
    - Check if lead exists by phone
    - If yes: link order_id to lead, mark status=created
    - If no: create new lead with status=created
    """
    phone = order.customer_phone or None  # Assuming customer_phone field exists
    if not phone:
        return None
    
    existing_lead = db.query(Lead).filter(
        Lead.tenant_id == current_user.tenant_id,
        Lead.phone == phone,
        Lead.is_archived == False,
    ).first()
    
    if existing_lead:
        # Reuse: update order_id if not already set
        if not existing_lead.order_id:
            existing_lead.order_id = order.id
        existing_lead.status = LeadPipelineStatus.created
        db.add(existing_lead)
    else:
        # Create new lead
        lead = Lead(
            tenant_id=current_user.tenant_id,
            lead_number=_next_lead_number(db, current_user.tenant_id),
            name=order.customer_name,
            phone=phone,
            city=order.delivery_city,
            state=order.delivery_state,
            source=LeadSource.manual,
            status=LeadPipelineStatus.created,
            order_id=order.id,
            created_by_id=current_user.id,
            notes=f"Auto-created from draft order {order.order_number}",
        )
        db.add(lead)
    
    db.flush()
```

---

## 📱 PHASE 2: WHATSAPP INTEGRATION (Days 2-3)

### 2.1 WhatsApp Module Setup

**File**: `/opt/miguel/backend/app/modules/whatsapp/__init__.py`

```python
# Create WhatsApp module
```

**File**: `/opt/miguel/backend/app/modules/whatsapp/config.py`

```python
import os

WHATSAPP_PROVIDER = os.getenv("WHATSAPP_PROVIDER", "twilio")  # or "meta"

if WHATSAPP_PROVIDER == "twilio":
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")  # e.g., +1234567890
    
elif WHATSAPP_PROVIDER == "meta":
    META_PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID")
    META_BUSINESS_ACCOUNT_ID = os.getenv("META_BUSINESS_ACCOUNT_ID")
    META_API_TOKEN = os.getenv("META_API_TOKEN")
```

**File**: `/opt/miguel/backend/app/modules/whatsapp/service.py`

```python
import requests
from fastapi import HTTPException
from app.modules.whatsapp.config import WHATSAPP_PROVIDER, TWILIO_*

class WhatsAppService:
    @staticmethod
    def send_message(to_phone: str, message_body: str) -> dict:
        """Send WhatsApp message via configured provider"""
        if WHATSAPP_PROVIDER == "twilio":
            return WhatsAppService._send_twilio(to_phone, message_body)
        elif WHATSAPP_PROVIDER == "meta":
            return WhatsAppService._send_meta(to_phone, message_body)
    
    @staticmethod
    def _send_twilio(to_phone: str, message_body: str) -> dict:
        """Send via Twilio WhatsApp"""
        from twilio.rest import Client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            from_=f"whatsapp:{TWILIO_WHATSAPP_NUMBER}",
            body=message_body,
            to=f"whatsapp:{to_phone}",
        )
        return {"message_id": message.sid, "status": "sent"}
    
    @staticmethod
    def _send_meta(to_phone: str, message_body: str) -> dict:
        """Send via Meta Business WhatsApp API"""
        url = f"https://graph.instagram.com/v18.0/{META_PHONE_NUMBER_ID}/messages"
        headers = {"Authorization": f"Bearer {META_API_TOKEN}"}
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "text",
            "text": {"body": message_body},
        }
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail=f"WhatsApp send failed: {response.text}")
        return {"message_id": response.json()["messages"][0]["id"], "status": "sent"}
    
    @staticmethod
    def send_auto_reply(to_phone: str, customer_name: str) -> dict:
        """Send auto-reply to new WhatsApp lead"""
        message = f"Hi {customer_name}, thanks for reaching out! Our team will contact you shortly. 🙏"
        return WhatsAppService.send_message(to_phone, message)

whatsapp_service = WhatsAppService()
```

**File**: `/opt/miguel/backend/app/modules/whatsapp/router.py`

```python
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.modules.leads import service as leads_service
from app.modules.whatsapp.service import whatsapp_service
import hmac
import hashlib

router = APIRouter(prefix="/webhooks", tags=["WhatsApp Webhooks"])

@router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Webhook receiver for WhatsApp messages
    
    Twilio: Verify webhook signature
    Meta: Verify webhook token
    """
    from app.modules.whatsapp.config import WHATSAPP_PROVIDER, TWILIO_AUTH_TOKEN
    
    body = await request.body()
    
    # Verify signature
    if WHATSAPP_PROVIDER == "twilio":
        signature = request.headers.get("X-Twilio-Signature", "")
        url = str(request.url)
        expected_sig = hmac.new(
            TWILIO_AUTH_TOKEN.encode(),
            (url + body.decode()).encode(),
            hashlib.sha1
        ).digest()
        if signature.encode() != expected_sig:
            raise HTTPException(status_code=403, detail="Invalid signature")
    
    # Parse incoming message
    data = await request.json()
    
    # TODO: Extract phone, message body, message ID
    # TODO: Create Lead if new phone number
    # TODO: Store message in lead_messages
    # TODO: Log activity
    
    return {"status": "ok"}
```

---

## 🎨 PHASE 3: FRONTEND REDESIGN (Days 3-4)

### 3.1 Update Leads Table

**File**: `/opt/miguel/frontend/leads.html` (Major rewrite section)

```javascript
// UPDATE: Sort order + priority display
function renderLeads(items) {
  const tb = document.getElementById('leadsBody');
  
  // Sort by priority
  const sortedItems = items.sort((a, b) => {
    const priorityMap = {
      'remind_later': 0,  // Top (today reminders)
      'created': 1,       // High
      'new_lead': 2,      // Medium
      'contacted': 3,     // Normal
      'success': 4,       // Low (almost done)
      'not_interested': 5, // Archived
    };
    
    const aPri = priorityMap[a.status] || 999;
    const bPri = priorityMap[b.status] || 999;
    
    if (aPri !== bPri) return aPri - bPri;
    
    // Secondary: by created_at (newest first)
    return new Date(b.created_at) - new Date(a.created_at);
  });
  
  if (!sortedItems.length) {
    tb.innerHTML = `<tr><td colspan="7"><div class="empty">No leads found</div></td></tr>`;
    return;
  }
  
  tb.innerHTML = sortedItems.map(l => {
    const fireEmoji = (l.status === 'remind_later' || isInactive48h(l)) ? '🔥 ' : '';
    const statusColor = getStatusColor(l.status);
    
    return `<tr>
      <td>${fireEmoji}<strong>${l.lead_number}</strong></td>
      <td><strong>${l.name}</strong><br>${l.phone}</td>
      <td>${l.product_interest || '—'}</td>
      <td>
        <select class="status-dropdown" data-status="${l.status}" onchange="openContactedPopup('${l.id}', '${l.name}', this.value)">
          <option value="created" ${l.status==='created'?'selected':''}>Created</option>
          <option value="new_lead" ${l.status==='new_lead'?'selected':''}>New Lead</option>
          <option value="contacted" ${l.status==='contacted'?'selected':''}>Contacted</option>
          <option value="success" ${l.status==='success'?'selected':''}>Success ✓</option>
          <option value="not_interested" ${l.status==='not_interested'?'selected':''}>Not Interested</option>
        </select>
      </td>
      <td>${l.next_followup_date || '—'}</td>
      <td>
        <div style="display:flex;gap:4px;">
          <button class="qa-btn" onclick="callLead('${l.phone}')">📞</button>
          <button class="qa-btn" onclick="openWhatsAppChat('${l.id}', '${l.name}')">💬</button>
          <button class="qa-btn" onclick="openDrawer('${l.id}')">→</button>
        </div>
      </td>
    </tr>`;
  }).join('');
}

function isInactive48h(lead) {
  if (lead.status !== 'contacted') return false;
  if (!lead.last_contacted_at) return true;
  const hrs = (Date.now() - new Date(lead.last_contacted_at)) / (1000*60*60);
  return hrs >= 48;
}

function getStatusColor(status) {
  const colors = {
    'created': '#c5221f',      // Red
    'new_lead': '#f97316',     // Orange
    'contacted': '#1a73e8',    // Blue
    'success': '#137333',      // Green
    'not_interested': '#80868b', // Grey
  };
  return colors[status] || '#80868b';
}
```

### 3.2 Contacted Popup Modal

**File**: `/opt/miguel/frontend/leads.html` (Add modal HTML)

```html
<!-- ═══ CONTACTED POPUP MODAL ══════════════════════════ -->
<div class="modal-backdrop" id="contactedModal">
  <div class="modal-box" style="max-width:420px;">
    <div class="modal-head">
      <h3>Mark as Contacted</h3>
      <button class="btn btn-ghost btn-sm" onclick="closeContactedModal()">✕</button>
    </div>
    <form id="contactedForm" onsubmit="submitContactedForm(event)">
      <input type="hidden" id="contactedLeadId">
      
      <div class="form-group">
        <label class="form-label">What did customer say? *</label>
        <textarea class="form-input" id="contactedNote" rows="3" required placeholder="Customer response or conversation summary..."></textarea>
      </div>
      
      <div class="form-group">
        <label class="form-label">Next Action *</label>
        <div style="display:flex;flex-direction:column;gap:8px;">
          <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
            <input type="radio" name="action" value="remind_later" onchange="toggleRemindDate()"> 
            <span>Remind Later</span>
          </label>
          <div id="remindDateRow" style="display:none;margin-left:24px;">
            <input type="date" id="remindDate" class="form-input">
          </div>
          
          <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
            <input type="radio" name="action" value="lost_lead"> 
            <span>Lost Lead (Not Interested)</span>
          </label>
          
          <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
            <input type="radio" name="action" value="success_won"> 
            <span>Success WON (Open Order Editor)</span>
          </label>
        </div>
      </div>
      
      <div style="display:flex;justify-content:flex-end;gap:10px;margin-top:20px;">
        <button type="button" class="btn btn-ghost" onclick="closeContactedModal()">Cancel</button>
        <button type="submit" class="btn btn-primary">Submit</button>
      </div>
    </form>
  </div>
</div>
```

**JavaScript handler**:

```javascript
function openContactedPopup(leadId, leadName, newStatus) {
  if (newStatus !== 'contacted') {
    // Direct status change (other statuses don't need popup)
    updateLeadStatus(leadId, newStatus);
    return;
  }
  
  document.getElementById('contactedLeadId').value = leadId;
  document.getElementById('contactedModal').classList.add('open');
}

function closeContactedModal() {
  document.getElementById('contactedModal').classList.remove('open');
}

function toggleRemindDate() {
  const isRemindLater = document.querySelector('input[name="action"]:checked').value === 'remind_later';
  document.getElementById('remindDateRow').style.display = isRemindLater ? 'block' : 'none';
}

async function submitContactedForm(e) {
  e.preventDefault();
  
  const leadId = document.getElementById('contactedLeadId').value;
  const note = document.getElementById('contactedNote').value.trim();
  const action = document.querySelector('input[name="action"]:checked').value;
  
  if (!note || !action) {
    alert('Please fill all fields');
    return;
  }
  
  const payload = {
    note: note,
    action: action,
    remind_date: action === 'remind_later' ? document.getElementById('remindDate').value : null,
  };
  
  try {
    const r = await fetch(`/api/leads/${leadId}/contacted`, {
      method: 'POST',
      headers: {'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json'},
      body: JSON.stringify(payload),
    });
    
    if (!r.ok) {
      const err = await r.json();
      alert(err.detail || 'Failed to update');
      return;
    }
    
    const updatedLead = await r.json();
    
    if (action === 'success_won') {
      // Open mini order editor
      openSuccessWONEditor(updatedLead.id);
    } else {
      // Refresh lists
      closeContactedModal();
      loadLeads();
      loadStats();
    }
  } catch (ex) {
    alert('Network error');
  }
}
```

### 3.3 Success WON Mini Order Editor

```html
<!-- Similar to mini order form from orders.html -->
<!-- Reuse order editor logic, just pre-fill from lead + order data -->
```

### 3.4 WhatsApp Chat Sidebar

```html
<!-- ═══ WHATSAPP CHAT SIDEBAR ═════════════════════════ -->
<div class="whatsapp-drawer" id="whatsappDrawer">
  <div class="whatsapp-header">
    <span id="whatsappLeadName">—</span>
    <button onclick="closeWhatsAppChat()" class="btn btn-ghost btn-sm">✕</button>
  </div>
  <div class="whatsapp-messages" id="whatsappMessages">
    <!-- Messages loaded here -->
  </div>
  <div class="whatsapp-input">
    <input type="text" id="messageInput" placeholder="Type message...">
    <button onclick="sendWhatsAppMessage()">→</button>
  </div>
</div>
```

---

## ✅ TESTING CHECKLIST

### Unit Tests
- [ ] `mark_contacted()` with all 3 actions
- [ ] `finalize_success_won()` → creates order + customer
- [ ] `get_reminded_leads()` returns correct dates
- [ ] `store_whatsapp_message()` logs correctly

### Integration Tests
- [ ] End-to-end: Created → Contacted → Remind Later → Success WON
- [ ] Order → Lead auto-creation + reuse by phone
- [ ] Lead → Customer conversion
- [ ] WhatsApp message send + receive

### Frontend Tests
- [ ] Table sorts correctly (priority order)
- [ ] Contacted popup validation (required fields)
- [ ] Mini order editor pre-fills correctly
- [ ] WhatsApp chat loads history
- [ ] Responsive on mobile

### Performance Tests
- [ ] List 1000 leads < 200ms
- [ ] Get lead detail < 100ms
- [ ] Chat history load < 300ms

---

## 🚀 GO/NO-GO DECISION

**Ready to start Phase 1?**

Before proceeding, confirm:
- [ ] Twilio or Meta for WhatsApp? (Recommend: Twilio for Phase 1)
- [ ] Auto-reply message text approved?
- [ ] Database backup taken?
- [ ] Development branch created?

Once confirmed, I will create the migrations and implement Phase 1 backend.

