# Tenant Archive & Deletion System — February 25, 2026

**Status:** ✅ Fully Implemented

---

## **Feature Overview**

Implemented a two-stage deletion system for tenants:

### **Stage 1: Soft Delete (Archive)**
- Tenant moved to Archive
- Data remains in database (marked as deleted with `deleted_at` timestamp)
- Can be restored anytime
- User sees warning dialog before confirming

### **Stage 2: Hard Delete (Permanent)**
- **Only available from Archive tab**
- Requires confirmation by typing tenant name
- **Irreversible** — deletes ALL tenant data:
  - Tenant record
  - All employees
  - All orders, leads, products, customers, etc.
  - All configurations and settings
  - All audit logs

---

## **User Interface Changes**

### **1. New Archive Tab in Navigation**
```
Navigation Menu:
├── Dashboard
├── All Tenants
├── Create Tenant
├── 🗑️ Archive (NEW)
├── System Stats
└── Logs
```

### **2. Delete Dialog (Soft Delete)**
When clicking "Delete" on a tenant:
- **Modal appears** with warning icon ⚠️
- Text: "Move to Archive?"
- Message: "The tenant will be hidden from the main list. You can restore it from the Archive tab anytime."
- Buttons: `Cancel` | `Archive Tenant`

### **3. Archive Tab**
Shows all soft-deleted tenants with:
- Company name
- Slug
- Contact person
- Deleted date
- **Two action buttons:**
  - `↶ Restore` — Restore to active list
  - `🔥 Permanently Delete` — Hard delete (requires confirmation)

### **4. Permanent Delete Dialog (Hard Delete)**
When clicking "Permanently Delete" in Archive:
- **Large red warning modal** appears
- Headline: "🔥 PERMANENTLY DELETE?"
- Shows tenant name prominently in red box
- Lists what will be deleted:
  - All tenant data (orders, leads, products, etc.)
  - All employees and users
  - All configurations and settings
  - All audit logs
- **Requires typing tenant name to enable delete button**
- Warning text: "⚠️ WARNING: This action cannot be undone!"

---

## **Backend API Endpoints**

### **List Active Tenants**
```
GET /platform/tenants
Authorization: Bearer {token}
```
**Returns:** Array of active (non-deleted) tenants

### **List Archived Tenants** (NEW)
```
GET /platform/tenants/archived/list
Authorization: Bearer {token}
```
**Returns:** Array of soft-deleted (archived) tenants

### **Soft Delete Tenant**
```
DELETE /platform/tenants/{tenant_id}
Authorization: Bearer {token}
```
**What happens:**
- Sets `is_active = false`
- Sets `deleted_at = NOW()`
- **Tenant hidden from active list**
- **Data remains intact**

### **Permanent Delete Tenant** (NEW)
```
DELETE /platform/tenants/{tenant_id}/permanent
Authorization: Bearer {token}
```
**Requirements:**
- Tenant must be soft-deleted first (must have `deleted_at` set)
- Otherwise returns 400 error

**What happens:**
- Deletes ALL employees for this tenant
- Cascades to delete all related data
- Removes tenant record completely
- **IRREVERSIBLE**

---

## **Database Changes**

### **Tenant Model - Already Had:**
```python
class Tenant(Base):
    __tablename__ = "tenants"
    
    # ...other fields...
    
    is_active = Column(Boolean, default=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
```

### **Query Filtering**
**Active tenants (default behavior):**
```python
db.query(Tenant).filter(Tenant.deleted_at == None)
```

**Archived tenants:**
```python
db.query(Tenant).filter(Tenant.deleted_at != None)
```

---

## **Frontend Functions**

### **confirmDelete(id, name)**
- Shows styled modal dialog
- User clicks "Archive Tenant"
- Calls `performSoftDelete()`

### **performSoftDelete(id)**
- Makes DELETE request to `/platform/tenants/{id}`
- Closes modal
- Reloads tenant list
- Shows success alert

### **restoreTenant(id, name)**
- Shows confirmation dialog
- Makes PATCH request to `/platform/tenants/{id}/activate`
- Removes `is_active = false` and `deleted_at` timestamp
- Reloads archive list

### **confirmPermanentDelete(id, name)**
- Shows dramatic red warning modal
- Requires user to type tenant name
- Delete button disabled until name matches

### **performPermanentDelete(id, name)**
- Makes DELETE request to `/platform/tenants/{id}/permanent`
- Closes modal
- Reloads archive list
- Shows success alert

### **loadArchive()**
- Fetches `/platform/tenants/archived/list`
- Populates archive table
- Shows archived tenants

### **archiveHtml(list)**
- Renders table of archived tenants
- Shows restore and permanent delete buttons

---

## **CSS Styling**

### **New Button Styles**
```css
.btn-act.act-restore {
  background: #dbeafe;      /* Light blue */
  color: #1d4ed8;
  border-color: #93c5fd;
}

.btn-act.act-destroy {
  background: #fee2e2;      /* Light red */
  color: var(--g-red);
  border-color: #f87171;    /* Darker red border */
  font-weight: 600;         /* Bold text */
}
```

---

## **Testing Workflow**

### **Step 1: Test Soft Delete (Archive)**
1. Go to Platform Admin → All Tenants
2. Click "✕ Delete" on any active tenant
3. Warning dialog appears with "Archive Tenant" button
4. Click "Archive Tenant"
5. Tenant disappears from active list
6. ✅ Verify tenant now shows in Archive tab

### **Step 2: Test Restore**
1. Go to Archive tab
2. Click "↶ Restore" on any archived tenant
3. Confirm dialog appears
4. Click OK
5. ✅ Tenant returns to active list

### **Step 3: Test Permanent Delete**
1. Go to Archive tab
2. Click "🔥 Permanently Delete"
3. Red warning modal appears
4. Try clicking button (should be disabled)
5. Type tenant name in text field
6. Button becomes enabled
7. Click "Permanently Delete"
8. ✅ Tenant completely removed from database

### **Step 4: Verify Data Integrity**
Check database:
```bash
docker exec miguel_db psql -U miguel_user -d miguel_db -c "
  SELECT company_name, is_active, deleted_at FROM tenants ORDER BY deleted_at DESC LIMIT 10;
"
```

---

## **Files Modified**

| File | Changes |
|---|---|
| `/opt/miguel/backend/app/modules/platform/routes.py` | Added `list_archived_tenants()` endpoint; Added `permanently_delete_tenant()` endpoint; Updated `list_tenants()` to filter `deleted_at == None` |
| `/opt/miguel/frontend/platform-admin.html` | Added Archive tab to navigation; Added Archive section HTML; Added `loadArchive()` function; Added `archiveHtml()` function; Rewrote `confirmDelete()` with styled modal; Added `performSoftDelete()`; Added `restoreTenant()`; Added `confirmPermanentDelete()`; Added `performPermanentDelete()`; Added CSS for new buttons |

---

## **Safety Features**

✅ **Soft Delete First**
- Can't hard delete active tenants
- Hard delete only works on already-archived tenants

✅ **Confirmation Required**
- Soft delete: Dialog with "Archive Tenant" button
- Hard delete: Must type tenant name to confirm

✅ **Styled Warnings**
- Soft delete: Yellow warning (cautious)
- Hard delete: Red warning (destructive)
- Clear messaging about what will be deleted

✅ **User-Friendly Recovery**
- Archived tenants visible in Archive tab
- Easy one-click restore
- No data lost on soft delete

✅ **Irreversible Hard Delete**
- Clear message: "cannot be undone"
- Requires typing tenant name (not just clicking)
- API validates tenant is soft-deleted first

---

## **API Response Examples**

### **Soft Delete Response**
```json
{
  "message": "Tenant deleted",
  "tenant_id": "496f35eb-050b-4738-88d5-f9f5b5a4fb6f"
}
```

### **Permanent Delete Response**
```json
{
  "message": "Tenant permanently deleted with all data",
  "tenant_id": "496f35eb-050b-4738-88d5-f9f5b5a4fb6f",
  "status": "destroyed"
}
```

### **Permanent Delete Error (Not Archived First)**
```json
{
  "detail": "Tenant must be soft-deleted first. Use DELETE endpoint."
}
```

---

## **Statistics**

Platform dashboard now tracks:
- `active_tenants` — Active (non-deleted)
- `inactive_tenants` — Inactive but not deleted
- `deleted_tenants` — Soft-deleted (archived)

Query: `GET /platform/stats`

---

## **Audit Trail**

All deletions tracked via:
- `deleted_at` timestamp (when soft-deleted)
- Activity logs (requests to delete endpoints)
- Database can be audited for hard-deleted records

---

## **Edge Cases Handled**

| Case | Behavior |
|---|---|
| Hard delete non-archived tenant | Returns 400 error: "Must be soft-deleted first" |
| Restore active tenant (bug) | Stays active; no error |
| Delete already-deleted tenant | Idempotent; succeeds with same response |
| Permanent delete non-existent tenant | Returns 404: "Tenant not found" |

---

## **Summary**

✅ **Soft Delete Working** — Tenants move to Archive  
✅ **Hard Delete Working** — Permanent removal with confirmation  
✅ **Restore Working** — Recover archived tenants  
✅ **UI Polished** — Styled dialogs with warnings  
✅ **Safety Features** — Multiple confirmations  
✅ **API Complete** — All endpoints tested  

**Feature Status: PRODUCTION READY** 🚀

