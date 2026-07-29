# Phase 1 Deployment Checklist

## Pre-Deployment (Development Environment)

### ✅ Code Validation
- [x] Python syntax check - All files pass
  - `lead.py` ✓
  - `schemas.py` ✓
  - `service.py` ✓
  - `router.py` ✓

- [x] Type hints validation
  - All functions have proper type annotations
  - All Pydantic models defined
  - Return types specified

- [x] Import validation
  - No circular imports
  - All dependencies available
  - Schema imports in router complete

### ✅ Code Quality
- [x] Enum values consistent
- [x] Error handling implemented
- [x] Tenant isolation checks in place
- [x] Pagination implemented
- [x] Sorting and filtering working

---

## Pre-Migration Checklist

### Database Backup
```bash
# Create backup before migration
cd /opt/miguel/backend

# PostgreSQL backup
pg_dump -U <user> <database> > backup_pre_phase1_$(date +%Y%m%d_%H%M%S).sql

# OR Docker backup
docker exec <postgres_container> pg_dump -U <user> <database> > backup_pre_phase1.sql
```

- [ ] Database backed up
- [ ] Backup location noted: _______________
- [ ] Backup verified (test restore)

### Tenant Notification
- [ ] Users notified of 10-minute maintenance window
- [ ] Leads module will be briefly unavailable
- [ ] Estimated completion time communicated

### Environment Verification
```bash
# Verify database connection
cd /opt/miguel/backend
python -c "from app.database.session import SessionLocal; db = SessionLocal(); print('✓ Database connected')"

# Verify Alembic configuration
alembic current  # Should show current revision

# Verify Python environment
python --version  # 3.10+
pip list | grep sqlalchemy  # Should be installed
```

- [ ] Database connection OK
- [ ] Alembic configured
- [ ] Python 3.10+
- [ ] SQLAlchemy installed

---

## Migration Execution

### Step 1: Apply Migrations
```bash
cd /opt/miguel/backend

# Check pending migrations
alembic upgrade --sql head

# Apply migrations
alembic upgrade head

# Verify current revision
alembic current
```

**Expected Output**:
```
INFO [alembic.migration] Context impl PostgresqlImpl.
INFO [alembic.migration] Will assume transactional DDL.
INFO [alembic.ddl.impl] Implementing Postgresql for dialect postgresql+psycopg2 5.4
INFO [alembic.migration] Running upgrade <prev_revision> -> <new_revision>, ...
```

**Verify After Migration**:
```sql
-- Check new columns exist
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'leads' 
ORDER BY ordinal_position;

-- Expected new columns: remind_date, order_id, contacted_count, is_archived, note_last

-- Check new table exists
SELECT * FROM information_schema.tables 
WHERE table_name = 'lead_messages';

-- Check new indexes
SELECT indexname FROM pg_indexes WHERE tablename = 'leads' 
AND indexname LIKE 'ix_leads_%';

-- Expected 4 new indexes:
-- ix_leads_remind_date
-- ix_leads_is_archived
-- ix_leads_order_id
-- ix_leads_status_remind
```

- [ ] Migration 1 applied successfully
- [ ] Migration 2 applied successfully
- [ ] New columns visible in leads table
- [ ] Lead_messages table created
- [ ] All 8 indexes created

### Step 2: Restart Backend Services
```bash
# Option A: Docker (if running in container)
docker-compose restart backend

# Option B: Manual restart
pkill -f "uvicorn.*app.main"
cd /opt/miguel/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# Option C: With systemd
systemctl restart miguel-backend
```

**Verify Backend Started**:
```bash
curl http://localhost:8000/api/health

# Expected response:
# {"status": "ok"}

# Or check logs
tail -f /opt/miguel/backend/logs/app.log
```

- [ ] Backend restarted
- [ ] Health check passing
- [ ] No error logs

### Step 3: Clear Application Cache (if applicable)
```bash
# If using Redis cache
redis-cli FLUSHDB

# If using browser localStorage (frontend)
# Users may need to clear cache or hard refresh

# If using Nginx cache
# (Already set to no-cache in nginx config)
```

- [ ] Cache cleared
- [ ] Browser cache notice sent to users

---

## Post-Migration Verification

### 1. Database State Check
```sql
-- Count leads table rows (should be unchanged)
SELECT COUNT(*) as lead_count FROM leads;

-- Count new lead_messages table rows (should be 0)
SELECT COUNT(*) as message_count FROM lead_messages;

-- Verify no NULL constraint violations
SELECT COUNT(*) FROM leads WHERE contacted_count IS NULL;  -- Should be 0
SELECT COUNT(*) FROM leads WHERE is_archived IS NULL;     -- Should be 0

-- Verify default values
SELECT 
  COUNT(*) as total_leads,
  COUNT(*) FILTER (WHERE is_archived = false) as active_leads
FROM leads;
```

- [ ] Leads count unchanged
- [ ] Lead_messages table empty (as expected)
- [ ] No constraint violations
- [ ] Default values applied correctly

### 2. API Endpoint Health Check

**Create Test Lead**:
```bash
curl -X POST http://localhost:8000/api/leads \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Phase1 Test Lead",
    "phone": "9999999999",
    "email": "test@phase1.com",
    "status": "new_lead"
  }'

# Expected response (201):
# {
#   "id": "UUID",
#   "lead_number": "LEAD-00001",
#   "status": "new_lead",
#   "contacted_count": 0,
#   "is_archived": false,
#   "remind_date": null,
#   "order_id": null
# }
```

- [ ] Create lead endpoint working
- [ ] New fields present in response
- [ ] Default values correct

**Test Mark Contacted Endpoint**:
```bash
curl -X POST http://localhost:8000/api/leads/{lead_id}/contacted \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "note": "Test contacted flow",
    "action": "save_close"
  }'

# Expected response (200):
# {
#   "message": "Lead marked as contacted",
#   "lead": {
#     "status": "contacted",
#     "contacted_count": 1,
#     "note_last": "Test contacted flow"
#   }
# }
```

- [ ] Mark contacted endpoint working
- [ ] contacted_count incremented
- [ ] note_last saved
- [ ] Status changed

**Test Reminder Endpoint**:
```bash
# Set a reminder for today
curl -X POST http://localhost:8000/api/leads/{lead_id} \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "remind_date": "2024-12-21"
  }'

# Get today's reminders
curl -X GET http://localhost:8000/api/leads/reminders/today \
  -H "Authorization: Bearer <TOKEN>"

# Expected response (200):
# {
#   "count": 1,
#   "leads": [
#     {
#       "id": "UUID",
#       "remind_date": "2024-12-21",
#       ...
#     }
#   ]
# }
```

- [ ] Reminder set successfully
- [ ] Get reminders endpoint working
- [ ] Correct leads returned

**Test Lost Leads Endpoint**:
```bash
curl -X GET http://localhost:8000/api/leads/lost_leads/list \
  -H "Authorization: Bearer <TOKEN>"

# Expected response (200):
# {
#   "total": 0,
#   "page": 1,
#   "page_size": 20,
#   "results": []
# }
```

- [ ] Lost leads endpoint working
- [ ] Pagination working
- [ ] Empty result when no lost leads

**Test WhatsApp Message Endpoint**:
```bash
curl -X POST http://localhost:8000/api/leads/{lead_id}/messages \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "message_body": "Test WhatsApp message",
    "direction": "inbound"
  }'

# Expected response (201):
# {
#   "message": "Message stored successfully",
#   "message_id": "UUID",
#   "created_at": "2024-12-21T..."
# }

# Get messages
curl -X GET http://localhost:8000/api/leads/{lead_id}/messages \
  -H "Authorization: Bearer <TOKEN>"

# Expected response (200):
# {
#   "count": 1,
#   "messages": [
#     {
#       "id": "UUID",
#       "message_body": "Test WhatsApp message",
#       "direction": "inbound",
#       "created_at": "..."
#     }
#   ]
# }
```

- [ ] Store message endpoint working
- [ ] Get messages endpoint working
- [ ] Message retrieved in correct order

### 3. UI Verification

**Frontend Leads Page**:
- [ ] Leads page loads without errors
- [ ] New status values display: `created`, `new_lead`, `contacted`, `success`, `not_interested`
- [ ] Status dropdown shows new values
- [ ] No console errors in browser

**Existing Features Still Working**:
- [ ] Can view leads list
- [ ] Can view lead detail
- [ ] Can edit lead fields
- [ ] Pagination works
- [ ] Filters work (status, priority, source)
- [ ] Search works

---

## Performance Testing

### 1. Response Times
```bash
# Measure API response time
time curl -X GET http://localhost:8000/api/leads/reminders/today

# Expected: < 500ms for 100+ reminders
```

- [ ] Response times acceptable (< 500ms)
- [ ] No database timeout errors
- [ ] No N+1 query issues observed

### 2. Database Load
```bash
# Monitor database connections
SELECT count(*) FROM pg_stat_activity;

# Expected: Normal connection pool usage

# Check slow query log
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
```

- [ ] Connection pool stable
- [ ] No slow queries introduced
- [ ] Indexes being used

### 3. Disk Space
```bash
# Check database size
SELECT 
  pg_size_pretty(pg_database_size(current_database())) as db_size,
  pg_size_pretty(pg_total_relation_size('leads')) as leads_size,
  pg_size_pretty(pg_total_relation_size('lead_messages')) as messages_size;
```

- [ ] Database size reasonable
- [ ] Indexes created successfully

---

## Rollback Plan (If Issues Occur)

### If Migration Fails
```bash
# Option 1: Roll back last migration
cd /opt/miguel/backend
alembic downgrade -1

# Option 2: Roll back to specific revision
alembic downgrade <previous_revision>

# Verify rollback
alembic current
```

### If API Issues Occur
```bash
# Restart with previous code version
git checkout <previous_commit_hash>
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### If Data Corruption Detected
```bash
# Restore from backup
psql -U <user> <database> < backup_pre_phase1.sql

# Verify restored data
SELECT COUNT(*) FROM leads;
```

### Rollback Validation
```bash
# Verify leads table reverted
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'leads' AND column_name IN (
  'remind_date', 'order_id', 'contacted_count', 'is_archived', 'note_last'
);

# Should return: no rows

# Verify lead_messages table removed
SELECT * FROM information_schema.tables 
WHERE table_name = 'lead_messages';

# Should return: no rows
```

- [ ] Rollback procedure documented
- [ ] Backup location secured
- [ ] Team trained on rollback steps

---

## Post-Deployment Monitoring (24 hours)

### Hour 1: Immediate Checks
- [ ] All endpoints responding
- [ ] Error logs clean
- [ ] Users can access leads
- [ ] No data loss reported

### Hour 4: Extended Testing
- [ ] Users creating leads normally
- [ ] Contacted popup workflow tested
- [ ] WhatsApp message storage working
- [ ] Reminder queries fast

### Hour 24: Full Monitoring
- [ ] No unexpected errors
- [ ] Database performance stable
- [ ] All features working as expected
- [ ] User feedback collected

---

## Deployment Communication

### Pre-Deployment Email
```
Subject: Leads Module Update - Maintenance Required

Dear Team,

We'll be updating the Leads module on [DATE] at [TIME] for approximately 10 minutes.

During this time:
- Leads module will be unavailable
- You can continue using other modules
- No data loss will occur

New features coming:
- Mandatory "Contacted" notes
- Reminder scheduling
- Lost leads recovery system
- WhatsApp message history

Thank you for your patience.
```

### Post-Deployment Email
```
Subject: ✅ Leads Module Update Complete

Hi Team,

The Leads module has been successfully updated!

New features available:
1. Contacted Popup Workflow - Mandatory notes when contacting leads
2. Reminder Scheduling - Set follow-up dates and get daily reminders
3. Lost Leads Recovery - Track and attempt to recover lost leads
4. WhatsApp Integration - Store and view message history

Questions? Contact: [SUPPORT EMAIL]
```

- [ ] Pre-deployment notification sent
- [ ] Post-deployment notification ready
- [ ] Support team briefed
- [ ] Documentation updated

---

## Final Sign-Off

### Technical Lead Review
- [ ] Code reviewed and approved
- [ ] Migrations tested in dev/staging
- [ ] Rollback plan documented
- [ ] Performance acceptable

### Product Owner Review
- [ ] Features match requirements
- [ ] UI/UX acceptable
- [ ] No breaking changes
- [ ] Ready for production

### DevOps Sign-Off
- [ ] Infrastructure ready
- [ ] Backup/recovery tested
- [ ] Monitoring configured
- [ ] Deployment runbook ready

**Deployment Approved**: _______________
**Approved By**: _______________
**Date**: _______________

---

## Deployment Day Timeline

| Time | Action | Owner | Status |
|------|--------|-------|--------|
| T-30 | Final code review | Dev Lead | ⏳ |
| T-15 | Database backup | DevOps | ⏳ |
| T-10 | Notify users (maintenance window) | Product | ⏳ |
| T-5 | Stop backend services | DevOps | ⏳ |
| T-0 | Run migrations | DevOps | ⏳ |
| T+3 | Restart backend | DevOps | ⏳ |
| T+5 | Run health checks | QA | ⏳ |
| T+10 | Enable user access | DevOps | ⏳ |
| T+20 | Monitor for issues | DevOps | ⏳ |
| T+60 | Final verification | QA | ⏳ |
| T+90 | Notify users (all clear) | Product | ⏳ |

---

**Deployment Checklist Complete** ✅
