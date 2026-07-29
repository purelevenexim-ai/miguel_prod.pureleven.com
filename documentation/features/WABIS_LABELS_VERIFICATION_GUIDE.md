# WABIS Labels in Leads — Verification & Troubleshooting Guide

## ✅ What's Already Implemented

### Frontend (leads.html)
- ✅ **Display labels** in table row and drawer Info tab
- ✅ **Edit labels** via modal dialog (click "✎ Edit" or "+ add")
- ✅ **Add new labels** via input field  
- ✅ **Remove labels** with ✕ button on each label
- ✅ **Save labels** to backend via PATCH API
- ✅ **Styling**: Green chips matching Audience page design

### Backend API
- ✅ **Parse webhook** — extracts `label_names` field from WABIS payload
- ✅ **Merge labels** — adds new labels to existing ones (no duplicates)
- ✅ **Store labels** — saves to `Lead.wabis_labels` (JSONB column)
- ✅ **Return labels** — sends back in GET `/api/leads/{id}` response
- ✅ **Edit labels** — PATCH `/api/leads/{lead_id}/wabis-labels` endpoint
- ✅ **Update timestamp** — sets `updated_at` when labels change

### Database
- ✅ **Column exists** — `wabis_labels` JSONB column in `leads` table
- ✅ **Migration applied** — `4fa5a68e4260_add_wabis_labels_to_leads.py`

---

## 🔍 Verification Checklist

### Step 1: Check Webhook is Sending Labels
The WABIS webhook payload should include a `label_names` field:
```json
{
  "subscriber_id": "919447480687-43011",
  "first_name": "Customer Name",
  "chat_id": "919447480687",
  "label_names": "Interested,Follow_Up,Price_Checked",
  "postbackid": "xyz123"
}
```

**Location to check:** WABIS Dashboard → Webhook Logs  
or inspect backend logs: `docker logs miguel-backend | grep label`

---

### Step 2: Verify Backend is Receiving Labels
Check if labels are being parsed:
```bash
# SSH into backend
docker exec -it miguel-backend sh

# Query database
python3 -c "
import sys
sys.path.insert(0, '/app')
from app.database import SessionLocal
from app.models.lead import Lead

db = SessionLocal()
# Find a recent lead from WhatsApp
lead = db.query(Lead).filter(Lead.source == 'whatsapp').order_by(Lead.created_at.desc()).first()
if lead:
    print(f'Lead: {lead.name}')
    print(f'Phone: {lead.phone}')
    print(f'WABIS Labels: {lead.wabis_labels}')
else:
    print('No WhatsApp leads found')
db.close()
"
```

**Expected output:**
```
Lead: Sajitha V V
Phone: 919447480687
WABIS Labels: ['Interested', 'Follow_Up', 'Price_Checked']
```

---

### Step 3: Check Frontend is Displaying Labels

1. **Open Leads page** → `/leads.html`
2. **Find a WhatsApp lead** (source = 📱)
3. **Look in the table** → "Labels" column (rightmost)
4. **Expected:**
   - If labels exist: Show green chips with label names + "✎ Edit" link
   - If no labels: Show "+ add" link (only for WhatsApp leads)

5. **Click on lead name** to open drawer
6. **Click Info tab** → scroll down
7. **Look for "🏷 WABIS Labels" section**
8. **Expected:** Green chips showing all labels from webhook

---

### Step 4: Test Editing Labels

1. **Click "✎ Edit"** (on labels display or "+ add" link)
2. **Modal dialog opens** with title "🏷 Edit Labels"
3. **Current labels shown** as editable chips with ✕ buttons
4. **Add a test label:**
   - Type in input field: "test_label"
   - Press Enter OR click "＋ Add" button
5. **Remove a label:**
   - Click ✕ on any existing label chip
6. **Save changes:**
   - Click "💾 Save" button
   - Modal closes
   - Banner shows "🏷 Labels saved."
   - Labels update in table and drawer

---

## 🛠️ Troubleshooting

### Issue 1: Labels Not Showing in Leads Page

**Symptom:** "wabis_labels is empty or null for a WhatsApp lead"

**Checklist:**
- [ ] Webhook is sending `label_names` field?
- [ ] Backend received the webhook? (Check docker logs)
- [ ] Lead was created/updated AFTER webhook implementation?
- [ ] Did a fresh webhook arrive? (Labels are merged, not replaced)

**Solution:**
```bash
# Option A: Manually trigger a test webhook
curl -X POST http://localhost:8000/api/wa/test-inbound \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "subscriber_id": "919447480687-43011",
    "first_name": "Test Customer",
    "chat_id": "919447480687",
    "label_names": "Interested,Priority",
    "postbackid": "test123"
  }'

# Option B: Update existing lead with labels manually
curl -X PATCH http://localhost:8000/api/leads/LEAD_UUID/wabis-labels \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"labels": ["Label1", "Label2"]}'
```

---

### Issue 2: Labels Show But Are Wrong/Outdated

**Symptom:** "Labels don't match what I sent in the webhook"

**Checklist:**
- [ ] Did you send a NEW webhook after changing labels in WABIS?
- [ ] Are labels being MERGED (appended) instead of replaced?
- [ ] Is the webhook hitting the correct tenant?

**Solution:**
If you need to REPLACE all labels (not merge):
1. Click "✎ Edit"
2. Remove ALL existing labels (click ✕ on each)
3. Add the correct labels
4. Save

This will replace the entire label set instead of merging.

---

### Issue 3: Edit Modal Not Opening

**Symptom:** "Clicking label or '+ add' doesn't open the edit modal"

**Checklist:**
- [ ] Is the label clickable? (Hover should show cursor pointer)
- [ ] Is JavaScript enabled in browser?
- [ ] Any console errors? (F12 → Console tab)

**Solution:**
```bash
# Check if editLeadLabels function exists
# In browser console:
typeof editLeadLabels  # Should return "function"

# Check if lblModal exists
document.getElementById('lblModal')  # Should not be null
```

---

### Issue 4: Save Button Not Working

**Symptom:** "Click Save but nothing happens / modal doesn't close"

**Checklist:**
- [ ] At least one label exists? (Can't save empty label list)
- [ ] Network error? (Check Network tab in DevTools)
- [ ] Backend API endpoint exists? (`PATCH /api/leads/{lead_id}/wabis-labels`)

**Solution:**
```bash
# Test API manually
curl -X PATCH http://localhost:8000/api/leads/UUID/wabis-labels \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"labels": ["Test1", "Test2"]}'

# Check response:
# Should return 200 with:
# {"message": "Labels updated", "lead_id": "...", "wabis_labels": [...]}
```

---

## 📝 Common Webhook Payload Examples

### WABIS Payload
```json
{
  "subscriber_id": "919447480687-43011",
  "first_name": "Sajitha V V",
  "chat_id": "919447480687",
  "birthdate": "",
  "user_location_gps": "",
  "label_names": "Interested,Price_Checked,Address_verified",
  "postbackid": "c9EyF70CGyzUFv0",
  "whatsapp_bot_username": "+91 88482 65849"
}
```

### Label Merging Example
```
First webhook:  label_names = "Interested,Follow_Up"
  → Lead.wabis_labels = ["Interested", "Follow_Up"]

Second webhook: label_names = "Interested,Price_Checked"
  → Lead.wabis_labels = ["Interested", "Follow_Up", "Price_Checked"]
     (Interested not duplicated, Price_Checked appended)

Third webhook: label_names = "Interested"
  → Lead.wabis_labels = ["Interested", "Follow_Up", "Price_Checked"]
     (No change, already present)
```

---

## 🔗 Related Files

### Frontend
- `frontend/leads.html` — Label display (lines 150-175) + Edit modal (1703-1727) + JS functions (1486-1562)

### Backend
- `backend/app/modules/leads/router.py` — PATCH endpoint (line 108)
- `backend/app/modules/leads/service.py` — Label update function (line 218)
- `backend/app/modules/wa_engine/service.py` — Label merge during sync (line 1020)
- `backend/app/models/lead.py` — Model definition (line 119)

---

## 🚀 Next Steps

If labels are displaying correctly but you need to:

### **Add bulk labels to multiple leads:**
Use the edit modal for each lead (currently one-by-one)

### **Filter leads by label:**
Implement label filter in the Leads page filter section

### **Sync labels from WABIS Audience:**
Labels are already synced automatically via webhook

### **Archive old labels:**
Edit modal and manually remove them (or clear via API)

---

## 💡 Quick Reference

| Action | UI Location | API Endpoint | Result |
|--------|------------|-------------|--------|
| View labels | Leads table → Labels column | GET `/api/leads/` | Displays green chips |
| View labels (drawer) | Drawer → Info tab | GET `/api/leads/{id}` | Shows WABIS Labels section |
| Add label | Click "✎ Edit" or "+ add" | (opens modal) | Edit modal with input field |
| Remove label | Click ✕ on chip | (in modal) | Label removed from _lblCurrent |
| Save labels | Click 💾 Save | PATCH `/api/leads/{id}/wabis-labels` | Labels persisted to DB |
| Receive from webhook | (auto) | POST `/api/wa/inbound/` | Labels merged into Lead |

---

## 📞 Support

If labels still aren't working:

1. **Check backend logs** for parsing errors:
   ```bash
   docker logs miguel-backend | tail -50 | grep -i label
   ```

2. **Verify webhook is hitting the right URL:**
   - Should be: `POST /api/wa/inbound/{tenant_id}`
   - Check WABIS webhook configuration

3. **Inspect database directly:**
   ```bash
   docker exec miguel-postgres psql -U postgres -d miguel \
     -c "SELECT id, name, wabis_labels FROM leads WHERE source='whatsapp' LIMIT 5;"
   ```

4. **Check browser console** (F12 → Console) for JavaScript errors

5. **Clear browser cache** (Ctrl+Shift+Delete) and reload

---

**Last Updated:** 2026-02-23  
**Status:** ✅ Feature Complete — All components implemented and tested

