# Phase 1 Implementation - Test Guide

## Prerequisites

1. **Backend Running**:
   ```bash
   cd /opt/miguel/backend
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Migrations Applied**:
   ```bash
   cd /opt/miguel/backend
   alembic upgrade head
   ```

3. **Test Tenant Ready**:
   - Email: `purelevenexim@gmail.com`
   - Password: `prfRwEoBep&Nw8`
   - Slug: `purelevenexim`

---

## Test Scenarios

### Test 1: Create Lead with New Fields

**Setup**: You should have a lead ID from the system. If not, create one first.

**Endpoint**: `POST /api/leads`

**Request**:
```json
{
  "name": "Test Lead Phase1",
  "phone": "9876543210",
  "email": "test@phase1.com",
  "company_name": "Test Corp",
  "city": "Mumbai",
  "source": "manual",
  "priority": "high",
  "status": "new_lead",
  "order_id": null,
  "remind_date": null,
  "is_archived": false
}
```

**Expected Response** (201):
```json
{
  "id": "UUID",
  "lead_number": "LEAD-00001",
  "name": "Test Lead Phase1",
  "status": "new_lead",
  "remind_date": null,
  "order_id": null,
  "contacted_count": 0,
  "is_archived": false,
  "note_last": null,
  "created_at": "2024-12-21T..."
}
```

---

### Test 2: Mark Lead as Contacted (Popup Workflow)

**Endpoint**: `POST /api/leads/{lead_id}/contacted`

**Scenario A - Save & Close**:
```json
{
  "note": "Customer interested in wholesale pricing for rice",
  "action": "save_close"
}
```

**Expected Response** (200):
```json
{
  "message": "Lead marked as contacted",
  "lead": {
    "status": "contacted",
    "contacted_count": 1,
    "note_last": "Customer interested in wholesale pricing for rice",
    "last_contacted_at": "2024-12-21T..."
  }
}
```

**Verification**:
- ✅ `status` changed to `contacted`
- ✅ `contacted_count` incremented to 1
- ✅ `note_last` saved
- ✅ Activity logged with type `contacted_popup`

---

**Scenario B - Remind Later**:
```json
{
  "note": "Waiting for budget approval from their end",
  "action": "remind_later",
  "remind_date": "2025-01-10"
}
```

**Expected Response** (200):
```json
{
  "message": "Lead marked as contacted",
  "lead": {
    "status": "contacted",
    "remind_date": "2025-01-10",
    "note_last": "Waiting for budget approval from their end"
  }
}
```

**Verification**:
- ✅ `remind_date` set to 2025-01-10
- ✅ `status` set to `contacted`
- ✅ Activity logged

---

**Scenario C - Not Interested (Lost Lead)**:
```json
{
  "note": "They found a cheaper supplier in Indonesia",
  "action": "not_interested"
}
```

**Expected Response** (200):
```json
{
  "message": "Lead marked as contacted",
  "lead": {
    "status": "not_interested",
    "note_last": "They found a cheaper supplier in Indonesia"
  }
}
```

**Verification**:
- ✅ `status` changed to `not_interested`
- ✅ Two activities logged: `contacted_popup` + `recovery_campaign`
- ✅ Available for recovery campaigns

---

### Test 3: Get Today's Reminders

**Endpoint**: `GET /api/leads/reminders/today`

**Setup**: Set `remind_date` to today for multiple leads (use Test 2 Scenario B).

**Request**:
```
GET /api/leads/reminders/today
```

**Expected Response** (200):
```json
{
  "count": 2,
  "leads": [
    {
      "id": "UUID1",
      "lead_number": "LEAD-00001",
      "name": "Test Lead Phase1",
      "phone": "9876543210",
      "status": "contacted",
      "remind_date": "2024-12-21",
      "last_contacted_at": "2024-12-21T..."
    },
    {
      "id": "UUID2",
      "lead_number": "LEAD-00002",
      "name": "Another Lead",
      "phone": "9988776655",
      "status": "contacted",
      "remind_date": "2024-12-21"
    }
  ]
}
```

**Verification**:
- ✅ Only leads with today's remind_date returned
- ✅ Sorted by remind_date, then created_at
- ✅ Includes all necessary fields for UI display

---

### Test 4: Get Lost Leads (Recovery Campaigns)

**Endpoint**: `GET /api/leads/lost_leads/list?page=1&page_size=20`

**Setup**: Mark multiple leads as `not_interested` using Test 2 Scenario C.

**Request**:
```
GET /api/leads/lost_leads/list?page=1&page_size=20
```

**Expected Response** (200):
```json
{
  "total": 2,
  "page": 1,
  "page_size": 20,
  "results": [
    {
      "id": "UUID",
      "lead_number": "LEAD-00003",
      "name": "Uninterested Lead",
      "phone": "9111222333",
      "status": "not_interested",
      "last_contacted_at": "2024-12-21T...",
      "notes": "Found cheaper supplier",
      "days_since_contact": 0
    }
  ]
}
```

**Verification**:
- ✅ Only `not_interested` leads returned
- ✅ Sorted by last_contacted_at DESC
- ✅ Pagination works (test page=2, page_size=5)
- ✅ Total count matches

---

### Test 5: Store & Retrieve WhatsApp Messages

**Endpoint**: `POST /api/leads/{lead_id}/messages`

**Request** (Incoming Message):
```json
{
  "message_body": "Hi, can you send us samples of your premium rice?",
  "direction": "inbound",
  "whatsapp_message_id": "wamid.HBEUGkNOBBBBBBBB"
}
```

**Expected Response** (201):
```json
{
  "message": "Message stored successfully",
  "message_id": "UUID",
  "created_at": "2024-12-21T..."
}
```

**Verification**:
- ✅ Message stored in `lead_messages` table
- ✅ Activity logged with type `message_received`
- ✅ Timestamp recorded

---

**Retrieve Messages**:

**Endpoint**: `GET /api/leads/{lead_id}/messages?limit=50`

**Request**:
```
GET /api/leads/{lead_id}/messages?limit=50
```

**Expected Response** (200):
```json
{
  "count": 2,
  "messages": [
    {
      "id": "UUID1",
      "lead_id": "LEAD_UUID",
      "message_body": "Hi, can you send us samples?",
      "direction": "inbound",
      "created_at": "2024-12-21T10:30:00Z"
    },
    {
      "id": "UUID2",
      "lead_id": "LEAD_UUID",
      "message_body": "Sure, we can send samples by courier",
      "direction": "outbound",
      "created_at": "2024-12-21T10:35:00Z"
    }
  ]
}
```

**Verification**:
- ✅ Messages ordered by created_at (oldest first)
- ✅ Both inbound and outbound messages shown
- ✅ Limit parameter respected
- ✅ Message body preserved

---

### Test 6: Success/Won Conversion

**Endpoint**: `POST /api/leads/{lead_id}/success_won`

**Setup**: Have a lead in `contacted` status ready.

**Request**:
```json
{
  "order_items": [
    {
      "product_id": "PRODUCT_UUID",
      "quantity": 100,
      "unit": "kg",
      "total": 25000
    },
    {
      "product_id": "PRODUCT_UUID2",
      "quantity": 50,
      "unit": "bags",
      "total": 15000
    }
  ],
  "payment_method": "bank_transfer",
  "discount": 2000,
  "notes": "Wholesale order - premium rice",
  "delivery_date": "2025-01-05"
}
```

**Expected Response** (201):
```json
{
  "message": "Lead successfully converted to customer and order created",
  "lead_id": "UUID",
  "customer_id": "UUID",
  "order_id": "UUID",
  "order_number": "ORD-20241221120000"
}
```

**Verification**:
- ✅ Lead status changed to `success`
- ✅ Customer record created
- ✅ Order record created with items
- ✅ `lead.order_id` linked
- ✅ `lead.converted_customer_id` set
- ✅ Activity logged with status change details

---

### Test 7: Enum Status Values

**Test Endpoint**: `GET /api/leads`

**Verify New Statuses Appear**:
In the leads list, check that status values include:
- ✅ `created` - Top priority
- ✅ `new_lead` - Fresh leads
- ✅ `contacted` - Reached out
- ✅ `success` - Converted
- ✅ `not_interested` - Lost/recovery

**Verify Legacy Statuses Still Work**:
- ✅ `new` (maps to new_lead)
- ✅ `won` (maps to success)
- ✅ `lost` (maps to not_interested)
- ✅ Others for backward compatibility

---

## Performance Tests

### Test 8: Reminder Query Performance

**Test**: Fetch reminders for a large tenant (100+ leads with reminders)

```bash
# Time the query
time curl -X GET "http://localhost:8000/api/leads/reminders/today"
```

**Expected**:
- ✅ Response time < 500ms
- ✅ Uses `ix_leads_remind_date` index
- ✅ Returns all matching leads quickly

---

### Test 9: Lost Leads Pagination

**Test**: Fetch lost leads with pagination

```bash
# Page 1
curl -X GET "http://localhost:8000/api/leads/lost_leads/list?page=1&page_size=20"

# Page 2
curl -X GET "http://localhost:8000/api/leads/lost_leads/list?page=2&page_size=20"

# Large page size
curl -X GET "http://localhost:8000/api/leads/lost_leads/list?page=1&page_size=100"
```

**Expected**:
- ✅ Correct offset/limit applied
- ✅ Total count accurate
- ✅ Results sorted by last_contacted_at DESC
- ✅ Response time < 300ms

---

### Test 10: WhatsApp Message History

**Test**: Fetch 200+ messages for a lead

```bash
# Fetch with different limits
curl -X GET "http://localhost:8000/api/leads/{id}/messages?limit=50"
curl -X GET "http://localhost:8000/api/leads/{id}/messages?limit=200"
```

**Expected**:
- ✅ Messages ordered correctly (oldest first)
- ✅ Limit parameter respected
- ✅ Uses `ix_lead_messages_created_at` index
- ✅ Response time < 200ms for 200 messages

---

## Integration Tests

### Test 11: Complete Workflow

**Step 1**: Create a new lead
```bash
POST /api/leads → LEAD_ID
```

**Step 2**: Mark as contacted (save & close)
```bash
POST /api/leads/{LEAD_ID}/contacted
```

**Step 3**: Send WhatsApp message
```bash
POST /api/leads/{LEAD_ID}/messages
```

**Step 4**: Retrieve conversation history
```bash
GET /api/leads/{LEAD_ID}/messages
```

**Step 5**: Create successful order
```bash
POST /api/leads/{LEAD_ID}/success_won
```

**Step 6**: Verify lead status is "success"
```bash
GET /api/leads/{LEAD_ID}
→ status = "success"
→ converted_customer_id is set
→ order_id is set
```

---

### Test 12: Lost Lead Recovery

**Step 1**: Create lead
```bash
POST /api/leads → LEAD_ID
```

**Step 2**: Contact and mark as not interested
```bash
POST /api/leads/{LEAD_ID}/contacted
→ action: "not_interested"
```

**Step 3**: Verify in lost leads list
```bash
GET /api/leads/lost_leads/list
→ Should see LEAD_ID with status "not_interested"
```

**Step 4**: Check activity shows recovery_campaign
```bash
GET /api/leads/{LEAD_ID}
→ activities should show:
   - "contacted_popup" activity
   - "recovery_campaign" activity
```

---

## Error Handling Tests

### Test 13: Validation Errors

**Missing Required Fields**:
```bash
POST /api/leads/contacted
{
  "note": "",  # Empty note
  "action": "save_close"
}
→ Expected: 422 (Validation Error)
```

**Missing Remind Date**:
```bash
POST /api/leads/contacted
{
  "note": "Customer busy",
  "action": "remind_later"
  # Missing remind_date
}
→ Expected: 400 (Bad Request)
```

---

### Test 14: 404 Errors

**Non-existent Lead**:
```bash
POST /api/leads/{FAKE_UUID}/contacted
{
  "note": "test",
  "action": "save_close"
}
→ Expected: 404 (Not Found)
```

---

## Summary of Test Coverage

| Test | Endpoint | Status |
|------|----------|--------|
| 1 | POST /api/leads | Create with new fields |
| 2 | POST /api/leads/{id}/contacted | All 3 action types |
| 3 | GET /api/leads/reminders/today | Reminder queries |
| 4 | GET /api/leads/lost_leads/list | Lost leads pagination |
| 5 | POST/GET /api/leads/{id}/messages | Message storage & retrieval |
| 6 | POST /api/leads/{id}/success_won | Lead → Customer → Order |
| 7 | GET /api/leads | Enum status values |
| 8 | GET /api/leads/reminders/today | Performance (100+ leads) |
| 9 | GET /api/leads/lost_leads/list | Pagination performance |
| 10 | GET /api/leads/{id}/messages | Large message history |
| 11 | All endpoints | Complete workflow |
| 12 | All endpoints | Lost lead recovery |
| 13 | All endpoints | Validation errors |
| 14 | All endpoints | 404 errors |

---

## Test Checklist

- [ ] All migrations applied successfully
- [ ] Test 1: Create lead with new fields
- [ ] Test 2A: Mark contacted (save & close)
- [ ] Test 2B: Mark contacted (remind later)
- [ ] Test 2C: Mark contacted (not interested)
- [ ] Test 3: Get today's reminders
- [ ] Test 4: Get lost leads
- [ ] Test 5: Store messages
- [ ] Test 5: Retrieve messages
- [ ] Test 6: Success/Won conversion
- [ ] Test 7: Verify new enum statuses
- [ ] Test 8: Reminder query performance
- [ ] Test 9: Lost leads pagination
- [ ] Test 10: Message history performance
- [ ] Test 11: Complete workflow
- [ ] Test 12: Lost lead recovery
- [ ] Test 13: Validation errors
- [ ] Test 14: 404 errors

---

## Next Phase (Phase 2)

Once all Phase 1 tests pass:
1. Integrate Meta Business WhatsApp API
2. Set up webhook for incoming messages
3. Implement auto-reply system
4. Create message forwarding

---

**Ready to test!** 🚀
