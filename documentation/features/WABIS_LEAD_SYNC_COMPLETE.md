# WABIS → CRM Lead Sync — Implementation Complete

**Date:** February 23, 2026  
**Phase:** Phase 12.2 (WA Engine v2 Enhancement)  
**Status:** ✅ **COMPLETE**

---

## Overview

WABIS webhook payloads now automatically create and update Lead records in the CRM, with labels merged into the `Lead.wabis_labels` JSONB column. This bridges WhatsApp contacts with the CRM pipeline.

---

## What Changed

### 1. Database Model Update

**File:** `/opt/miguel/backend/app/models/lead.py`

Added new column to `Lead` model:
```python
# ── WABIS Integration ───────────────────────────────────
wabis_labels = Column(JSONB, nullable=True)   # labels from WABIS webhook (merged)
```

**Migration:** `4fa5a68e4260_add_wabis_labels_to_leads.py`  
✅ Applied successfully

### 2. Service Layer Enhancement

**File:** `/opt/miguel/backend/app/modules/wa_engine/service.py`

#### Added: `_sync_wabis_to_lead()` Function

Called during `process_inbound()` right after subscriber upsert.

**Logic:**
1. Check if subscriber has `lead_id` already linked
   - If yes: Update lead labels (merge) and return
2. Search for existing Lead by phone number
   - If found: Link subscriber to lead, merge labels
3. Create new Lead if phone doesn't match any existing lead
   - Generate lead number: `LEAD-00001`, `LEAD-00002`, etc.
   - Set source to `whatsapp`
   - Set status to `new_lead`
   - Set creator_id to first admin in tenant
   - Store labels in `wabis_labels`
4. Link subscriber to new lead: `subscriber.lead_id = new_lead.id`

**Label Merge Behavior:**
```python
# Example 1: New lead, labels from WABIS
Lead.wabis_labels = ["Interested", "Price_checked"]

# Example 2: Second webhook with different labels
existing = ["Interested", "Price_checked"]
new       = ["Interested", "Address_checked"]
merged    = ["Interested", "Price_checked", "Address_checked"]  # union

# Example 3: Duplicate labels are NOT added
incoming = ["Price_checked"]  # already in existing
result   = ["Interested", "Price_checked"]  # unchanged
```

---

## End-to-End Flow

### Inbound WABIS Webhook

**URL:** `POST /api/wa/inbound/{tenant_id}`

**Example Payload:**
```json
{
  "subscriber_id": "919447480687-43011",
  "first_name": "Sajitha V V",
  "chat_id": "919447480687",
  "birthdate": "",
  "user_location_gps": "",
  "label_names": "Interested,Address_checked",
  "postbackid": "c9EyF70CGyzUFv0",
  "whatsapp_bot_username": "+91 88482 65849"
}
```

### Processing Steps

1. **Parse**: WABIS provider parses fields
   - `subscriber_id` → subscriber ID
   - `first_name` → name
   - `chat_id` → phone number
   - `label_names` (comma-separated) → `["Interested", "Address_checked"]`
   - `postbackid` → postback ID

2. **Upsert Subscriber**
   ```
   WaSubscriber(
     subscriber_id: "919447480687-43011",
     phone_number: "919447480687",
     name: "Sajitha V V",
     wabis_labels: ["Interested", "Address_checked"],
     last_postback_id: "c9EyF70CGyzUFv0"
   )
   ```

3. **Sync to Lead** ← NEW STEP
   - Search: Is there a lead with phone `919447480687`?
   - If NO: Create new Lead
     ```
     Lead(
       lead_number: "LEAD-00001",
       phone: "919447480687",
       name: "Sajitha V V",
       source: LeadSource.whatsapp,
       status: LeadPipelineStatus.new_lead,
       wabis_labels: ["Interested", "Address_checked"],
       created_by_id: <tenant_admin_id>
     )
     ```
   - If YES: Update existing lead
     ```
     existing_labels = ["Price_checked"]
     incoming        = ["Interested", "Address_checked"]
     merged          = ["Price_checked", "Interested", "Address_checked"]
     lead.wabis_labels = merged
     ```

4. **Create/Update Conversation**
   - Link to lead via subscriber

5. **Store Message**
   - Save inbound message to conversation

6. **Apply Postback Rule**
   - If matching rule exists, apply action

7. **Update WA Status**
   - Set to `new_message` (never reset on subsequent triggers)

8. **Fire Outbound Webhooks**
   - Background task: POST to configured outbound URLs

---

## Database Impact

### Before

**Leads table:** Only leads created manually or via direct CRM input

### After

**Leads table:** Automatically populated from WABIS webhook
- All WhatsApp contacts become leads
- Phone-deduplicated (no duplicate leads)
- Labels available for filtering/segmentation

**WA Subscribers table:** Now linked to leads
- `wa_subscribers.lead_id` ← populated automatically
- `wa_subscribers.wabis_labels` ← accumulated across triggers

---

## Frontend Changes

### Audience Tab — Two Sub-tabs

#### 👥 All Contacts
- Shows all leads (including WABIS-created ones)
- **Status:** All WABIS contacts show "💬 New Lead" badge
- **Labels column:** Blue chips showing WABIS labels
  - Click to edit labels for this contact
  - Labels persist in database when saved
- **Filter by Label:** Text input in sidebar filters by label name

#### 🏷 Labels
- Shows all unique WABIS labels as cards
- Each card displays: label name + subscriber count
- Click a card to see all subscribers with that label
- **Blast this label** button:
  - Pre-selects all subscribers with this label
  - Opens WhatsApp blast modal
  - Sends to all selected subscribers

### How Leads Page is Updated

Currently, the Leads page doesn't show WABIS-created leads separately. To access them:

1. **Go to Audience tab** → see all contacts (including WABIS)
2. **Filter by Source:** "💬 WABIS" to see WhatsApp-only contacts
3. **Click any contact** → chat drawer opens (if it's WABIS contact)

**Future Enhancement:** Could add "Source" column to Leads page to distinguish WABIS-created vs. manually-entered leads.

---

## API Changes

### New Function in Service

```python
def _sync_wabis_to_lead(
    db: Session,
    tenant_id: uuid.UUID,
    inbound: InboundMessage,
    subscriber: WaSubscriber,
) -> None:
    """Sync WABIS data to CRM Lead record."""
```

### Existing Endpoint Enhanced

`GET /api/wa/subscribers/as-leads/list`

Now returns `wabis_labels` array for each subscriber:
```json
{
  "total": 5,
  "results": [
    {
      "id": "...",
      "name": "Sajitha V V",
      "phone": "919447480687",
      "wabis_labels": ["Interested", "Address_checked"],
      "postback_ids": ["c9EyF70CGyzUFv0", "abc123"],
      "last_postback_id": "c9EyF70CGyzUFv0",
      ...
    }
  ]
}
```

### Label Management Endpoint

`PATCH /api/wa/subscribers/{sub_id}/labels`

Update labels for a subscriber:
```bash
curl -X PATCH http://localhost:8000/api/wa/subscribers/{sub_id}/labels \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "labels": ["Interested", "VIP", "Follow_Up"]
  }'
```

---

## Test Case: Two Webhooks, Same Customer

### Webhook 1: Initial Contact

```json
{
  "subscriber_id": "919447480687-1",
  "chat_id": "919447480687",
  "first_name": "Anu Kuriakose",
  "label_names": "Price_checked",
  "postbackid": "postback_1"
}
```

**Result:**
- Subscriber created
- Lead created: `LEAD-00001`
- `lead.wabis_labels = ["Price_checked"]`

### Webhook 2: Follow-up (Same Customer)

```json
{
  "subscriber_id": "919447480687-1",
  "chat_id": "919447480687",
  "first_name": "Anu Kuriakose",
  "label_names": "Interested,Address_checked",
  "postbackid": "postback_2"
}
```

**Result:**
- Subscriber updated (same ID)
- Lead FOUND (phone matches) or LINKED (if not already)
- `lead.wabis_labels = ["Price_checked", "Interested", "Address_checked"]` (merged)
- `subscriber.postback_ids = ["postback_1", "postback_2"]`

---

## Implementation Details

### Label Deduplication

Labels are deduplicated by Python set logic:
```python
existing = ["Price_checked", "Interested"]
new      = ["Interested", "Address_checked"]
# Only "Address_checked" is added
merged   = ["Price_checked", "Interested", "Address_checked"]
```

### Lead Number Generation

Sequential format: `LEAD-00001`, `LEAD-00002`, etc.

```python
latest_lead = db.query(Lead).filter(...).order_by(Lead.lead_number.desc()).first()
next_num = int(latest_lead.lead_number.split('-')[-1]) + 1
```

### Creator Assignment

New leads created from WABIS are assigned to the first admin:

```python
creator = db.query(Employee).filter(
    Employee.tenant_id == tenant_id,
    Employee.role == RoleEnum.admin,
).first()
```

If no admin exists (shouldn't happen), `created_by_id` is NULL.

### Phone Matching

Exact string match on `phone` column:

```python
existing_lead = db.query(Lead).filter(
    Lead.tenant_id == tenant_id,
    Lead.phone == phone,
).first()
```

No normalization (international dialing, spaces, etc.). Phone from WABIS is used as-is.

---

## Error Handling

All exceptions in `_sync_wabis_to_lead()` are caught at the `process_inbound()` level. Webhook returns 200 OK regardless, so WABIS doesn't retry.

If Lead creation fails:
- Subscriber is still saved
- Conversation still created
- Message still stored
- Only the Lead link is missing

---

## Files Changed

### Backend

1. **Model:** `/opt/miguel/backend/app/models/lead.py`
   - Added `JSONB` import
   - Added `wabis_labels` column

2. **Migration:** `/opt/miguel/backend/alembic/versions/4fa5a68e4260_add_wabis_labels_to_leads.py`
   - Adds column to `leads` table

3. **Service:** `/opt/miguel/backend/app/modules/wa_engine/service.py`
   - Added `_sync_wabis_to_lead()` function
   - Updated `process_inbound()` to call it

### Frontend

No changes needed — Audience tab and Labels column already in place from previous phase.

### Documentation

1. **README:** `/opt/miguel/README.md`
   - Updated Phase 12 section with WABIS → Lead sync details
   - Added example webhook payload and processing steps

2. **This file:** `/opt/miguel/WABIS_LEAD_SYNC_COMPLETE.md`
   - Comprehensive documentation of feature

---

## Testing Steps

### 1. Send Test Webhook

```bash
curl -X POST http://localhost:8000/api/wa/inbound/3f7160e0-c6c3-4feb-bfff-b4eaed704110 \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: your_secret" \
  -d '{
    "subscriber_id": "919447480687-1",
    "first_name": "Test User",
    "chat_id": "919447480687",
    "label_names": "Test_Label",
    "postbackid": "test_pb_1"
  }'
```

### 2. Check WaSubscriber

```sql
SELECT id, name, phone_number, wabis_labels, lead_id
FROM wa_subscribers
WHERE phone_number = '919447480687'
  AND tenant_id = '3f7160e0-c6c3-4feb-bfff-b4eaed704110';
```

### 3. Check Lead

```sql
SELECT id, lead_number, name, phone, source, wabis_labels
FROM leads
WHERE phone = '919447480687'
  AND tenant_id = '3f7160e0-c6c3-4feb-bfff-b4eaed704110';
```

### 4. Frontend

- Open Audience tab
- Check "👥 All Contacts" sub-tab
- Filter by Source = "💬 WABIS"
- Should see the contact with "💬 New Lead" status
- Labels column should show the label

---

## Deployment

1. Run migration: `docker compose exec backend alembic upgrade head`
2. Restart backend: `docker compose restart backend`
3. Test with webhook payload
4. Verify Lead created and labels populated

**Status:** ✅ **READY FOR PRODUCTION**

---

## Future Enhancements

1. **Leads Page Integration**
   - Add "Source" column to Leads page
   - Show "💬 WhatsApp" badge for WABIS-created leads
   - Filter by source

2. **Lead Activity from WABIS**
   - Create `LeadActivity` entries when WABIS webhook received
   - Track label changes as activity

3. **Label Sync Bidirectional**
   - Allow editing Lead labels in Leads page
   - Sync back to WABIS (if supported)

4. **Phone Number Normalization**
   - Normalize international dialing formats
   - Handle spaces, dashes, parentheses
   - Improve lead matching

5. **Lead Deduplication**
   - Detect when two WABIS contacts are same person
   - Merge leads intelligently
   - Consolidate labels

---

## Support

For issues or questions:
- Check backend logs: `docker compose logs backend | grep -i wabis`
- Check database: Query `leads` and `wa_subscribers` tables
- Verify migration was applied: `SELECT * FROM alembic_version`

---

**Deployed by:** Auto-implementation  
**Tested:** Yes, end-to-end flow verified  
**Status:** ✅ **PRODUCTION READY**
