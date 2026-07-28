# Excel Upload Auto-Transition Fix — Testing Guide

**Date:** March 10, 2026  
**Version:** 1.0  
**Status:** Ready for QA Testing

---

## Production Deployment Status

✅ **Code Changes:** Committed to GitHub (commit: acbfae6)  
✅ **Backend Container:** Restarted successfully  
✅ **API Health:** Responding normally (HTTP 200)  
✅ **Database:** Connected and healthy  
✅ **Ready for Testing:** YES

---

## What Was Fixed

### Issue 1: Tracking-Only Excel Upload Not Auto-Transitioning
**Before:** Upload tracking → tracking saved, but status stays "confirmed"  
**After:** Upload tracking → status auto-transitions to "shipped" ✅

### Issue 2: Delivery Status Excel Upload Not Auto-Transitioning  
**Before:** Upload delivery status → status stays "confirmed"  
**After:** Upload delivery status → status auto-transitions to "delivered" ✅

### Issue 3: COD Orders Not Auto-Paid on Delivery
**Before:** Upload delivered status for COD → payment_status stays "pending"  
**After:** Upload delivered status for COD → payment_status auto-updates to "paid" ✅

### Issue 4: No Audit Trail for Excel Uploads
**Before:** Upload excel → no history created, no activity logged  
**After:** Upload excel → OrderStatusHistory created, ActivityLog created ✅

---

## Test Setup

### Prerequisites
- Access to production CRM (http://172.105.48.142)
- Admin or Operations role
- Sample Excel file templates
- Test orders already in system

### Test Orders Needed
Create 5-6 test orders before running tests:

1. **Order A** — Status: Confirmed, Payment: COD, Amount: ₹500
2. **Order B** — Status: Confirmed, Payment: Partial COD, Amount: ₹1000
3. **Order C** — Status: Confirmed, Payment: UPI, Amount: ₹750
4. **Order D** — Status: Confirmed, Payment: COD, Amount: ₹200
5. **Order E** — Status: Confirmed, Payment: Pending (no payment)
6. **Order F** — Status: Confirmed, Payment: Bank Transfer, Amount: ₹1500

---

## Test Cases

### TEST 1: Tracking-Only Excel Upload (Auto-Transition to Shipped)

**Objective:** Verify that uploading tracking numbers without delivery status auto-transitions to "shipped"

**Steps:**

1. Create Excel file with 2 columns:
   ```
   Customer Name           | Tracking Number
   Customer A              | EE123456789IN
   Customer B              | CL377883138IN
   ```

2. Go to Orders → India Post → Upload Tracking File

3. Upload the Excel file

4. Verify response shows:
   ```
   ✅ updated_count: 2
   ✅ action: "tracking updated → shipped"
   ```

5. Go to each order and verify:
   - Status changed from "confirmed" → "shipped" ✅
   - Tracking number saved ✅
   - Courier set to "India Post" ✅

6. **Verify Status History:**
   - Click "View" on order
   - Go to Status History tab
   - Should see entry: "Auto-transitioned to shipped: tracking EE123456789IN assigned" ✅

7. **Verify Activity Log:**
   - Go to Admin → Activity Log
   - Search for order number
   - Should see: "India Post XLSX: tracking updated → shipped (Order #...)" ✅

**Expected Result:** ✅ PASS if all verifications above succeed

---

### TEST 2: Delivery Excel Upload - COD Order (Auto-Transition + Auto-Pay)

**Objective:** Verify that uploading delivery status for COD order auto-transitions AND auto-pays

**Steps:**

1. Create Excel file with 3 columns:
   ```
   Customer Name           | Tracking Number     | Status
   Order A Customer        | RX987654321IN       | delivered
   Order D Customer        | EM111222333IN       | delivered
   ```

2. Go to Orders → India Post → Upload Delivery File

3. Upload the Excel file

4. Verify response shows:
   ```
   ✅ updated_count: 2
   ✅ delivered_and_paid: 2
   ✅ action: "delivered + COD paid ✅"
   ```

5. Go to Order A and verify:
   - Status changed → "delivered" ✅
   - Tracking saved ✅
   - Payment Status changed → "paid" ✅
   - Amount Paid = ₹500 (the order total) ✅
   - Amount Due = ₹0 ✅

6. Go to Order D and verify same as Order A:
   - Status → "delivered" ✅
   - Payment Status → "paid" ✅
   - Amount Due = ₹0 ✅

7. **Verify Status History for Order A:**
   - Should see: "Marked delivered: tracking RX987654321IN assigned + COD auto-paid" ✅

8. **Verify Activity Log:**
   - Search for Order A number
   - Should see: "India Post XLSX: delivered + COD paid ✅ (Order A#...)" ✅

**Expected Result:** ✅ PASS if all verifications above succeed

---

### TEST 3: Delivery Excel Upload - Partial COD Order (Auto-Pay)

**Objective:** Verify auto-pay works for Partial COD payment method

**Steps:**

1. Create Excel file:
   ```
   Customer Name           | Tracking Number     | Status
   Order B Customer        | CL555666777IN       | delivered
   ```

2. Upload delivery file

3. Go to Order B and verify:
   - Status → "delivered" ✅
   - Tracking saved ✅
   - Payment Status → "paid" ✅
   - Amount Due = ₹0 ✅

4. **Verify Status History:**
   - Should show: "Marked delivered: ... + COD auto-paid" ✅

**Expected Result:** ✅ PASS if all above succeed

---

### TEST 4: Delivery Excel Upload - Non-COD Order (No Auto-Pay)

**Objective:** Verify that non-COD orders do NOT get auto-paid

**Steps:**

1. Create Excel file:
   ```
   Customer Name           | Tracking Number     | Status
   Order C (UPI) Cust.     | EM999888777IN       | delivered
   Order F (Bank) Cust.    | RX111333555IN       | delivered
   ```

2. Upload delivery file

3. Go to Order C and verify:
   - Status → "delivered" ✅
   - Tracking saved ✅
   - Payment Status → STILL "pending" (NOT auto-paid) ✅
   - Amount Due → UNCHANGED ✅

4. Go to Order F (Bank Transfer) and verify same:
   - Status → "delivered" ✅
   - Payment Status → STILL "pending" ✅

5. **Verify Status History for Order C:**
   - Should show: "Marked delivered: tracking ... assigned" (NO mention of "COD auto-paid") ✅

**Expected Result:** ✅ PASS if non-COD orders NOT auto-paid

---

### TEST 5: Return Status Upload

**Objective:** Verify that "returned" status is handled correctly

**Steps:**

1. Create Excel file:
   ```
   Customer Name           | Tracking Number     | Status
   Order E Customer        | RX123789555IN       | returned
   ```

2. Upload delivery file

3. Go to Order E and verify:
   - Status → "returned" ✅
   - Tracking saved ✅

4. **Verify Status History:**
   - Should show: "Marked returned: tracking RX123789555IN assigned" ✅

**Expected Result:** ✅ PASS

---

### TEST 6: Unmatched Orders (Negative Test)

**Objective:** Verify error handling for unmatched orders

**Steps:**

1. Create Excel file:
   ```
   Customer Name           | Tracking Number
   Unknown Customer        | TEST123456789IN
   Another Unknown         | TEST987654321IN
   ```

2. Upload tracking file

3. Verify response shows:
   ```
   ✅ skipped_count: 2
   ✅ reason: "No order matched for..."
   ```

4. Verify NO status changes occurred for any actual orders ✅

**Expected Result:** ✅ PASS if unmatched orders properly skipped

---

### TEST 7: Partial Upload (Mix of Matched and Unmatched)

**Objective:** Verify that valid rows process while invalid ones skip

**Steps:**

1. Create Excel file with 5 rows:
   ```
   Row 1: Known Customer A    | EE111111111IN   → Should match ✓
   Row 2: Unknown Customer    | TEST111111IN    → Should skip ✗
   Row 3: Known Customer B    | CL222222222IN   → Should match ✓
   Row 4: Garbage Data        | XYZ999999IN     → Should skip ✗
   Row 5: Known Customer D    | RX333333333IN   → Should match ✓
   ```

2. Upload tracking file

3. Verify response shows:
   ```
   ✅ updated_count: 3 (rows 1, 3, 5)
   ✅ skipped_count: 2 (rows 2, 4)
   ```

4. Verify status changes only occurred for rows 1, 3, 5 ✅
5. Verify rows 2, 4 had NO effect on any orders ✅

**Expected Result:** ✅ PASS if partial upload handles correctly

---

### TEST 8: Multiple Status Changes in Single Upload

**Objective:** Verify that multiple orders with different actions in one upload all work

**Steps:**

1. Create complex Excel file:
   ```
   Customer       | Tracking        | Status
   Cust A (COD)   | EE111111111IN   | delivered
   Cust B         | CL222222222IN   | (empty - track only)
   Cust C (UPI)   | EM333333333IN   | delivered  
   Cust D (PCOD)  | RX444444444IN   | delivered
   ```

2. Upload file

3. Verify response shows:
   ```
   ✅ updated_count: 4
   ✅ delivered_and_paid: 2 (Cust A, Cust D)
   ```

4. Verify each order updated correctly:
   - **Cust A:** delivered + auto-paid ✅
   - **Cust B:** shipped (tracking only) ✅
   - **Cust C:** delivered (no auto-pay) ✅
   - **Cust D:** delivered + auto-paid ✅

5. Verify 4 StatusHistory entries created ✅
6. Verify 4 ActivityLog entries created ✅

**Expected Result:** ✅ PASS if all statuses and payments correct

---

### TEST 9: UI Workflow - Status History Visibility

**Objective:** Verify users can see the auto-transitions in the UI

**Steps:**

1. Open an order that was updated via Excel upload

2. Click "View" to open order detail

3. Go to "Status History" tab

4. Verify entries show:
   - Old Status → New Status transition ✅
   - Meaningful note: "Auto-transitioned to shipped: tracking EE123456789IN assigned" ✅
   - Timestamp of change ✅
   - Employee who made the change (system/admin) ✅

5. Verify history entries are in chronological order ✅

**Expected Result:** ✅ PASS if history visible and meaningful

---

### TEST 10: Activity Log Visibility

**Objective:** Verify admin can see Excel upload activities in activity log

**Steps:**

1. Go to Admin → Activity Log (or where activity logs are displayed)

2. Search by date (today's date)

3. Filter by "Orders" module

4. Verify entries show:
   - Description: "India Post XLSX: tracking updated → shipped (Order #1001)" ✅
   - Module: "orders" ✅
   - Level: "info" ✅
   - Timestamp ✅
   - Reference: Order ID/number ✅

5. Verify one log entry per upload action ✅

**Expected Result:** ✅ PASS if activity logs visible

---

## Regression Testing

### TEST 11: Manual Status Update (UI) Still Works

**Objective:** Verify that clicking "Mark Shipped" in UI still works (not broken by changes)

**Steps:**

1. Create new order, status = "confirmed"

2. Click "🚚 Mark Shipped" button

3. Enter tracking: "MANUAL123456IN"

4. Click "Save"

5. Verify:
   - Status → "shipped" ✅
   - Tracking saved ✅
   - StatusHistory created ✅
   - ActivityLog created ✅

**Expected Result:** ✅ PASS if manual updates unchanged

---

### TEST 12: Shopify Order Upload Still Works

**Objective:** Verify Shopify Excel upload not affected (uses different table)

**Steps:**

1. If available, test Shopify order upload with tracking

2. Verify Shopify orders update as before (note: uses ShopifyOrder table, not Order table)

3. Verify no errors in backend logs

**Expected Result:** ✅ PASS if Shopify upload still works

---

## Error Scenarios

### TEST 13: Invalid Excel Format (Negative Test)

**Objective:** Verify graceful error handling

**Steps:**

1. Try to upload a TXT file instead of XLSX

2. Verify error message: "Cannot parse xlsx: ..."

3. Verify NO changes to any orders ✅

**Expected Result:** ✅ PASS if error handled gracefully

---

### TEST 14: Excel with No Headers

**Objective:** Verify proper error handling

**Steps:**

1. Create Excel file with no header row (just data)

2. Upload file

3. Verify error: "xlsx file has no data rows" or similar

4. Verify NO changes to orders ✅

**Expected Result:** ✅ PASS

---

## Performance Testing

### TEST 15: Bulk Upload Performance

**Objective:** Verify upload performance with larger file

**Steps:**

1. Create Excel with 50 rows (all valid, matched orders)

2. Upload file

3. Measure time taken (should be < 30 seconds for 50 orders)

4. Verify all 50 orders updated correctly ✅

5. Verify 50 StatusHistory entries created ✅

6. Verify 50 ActivityLog entries created ✅

**Expected Result:** ✅ PASS if completes in reasonable time

---

## Test Summary Template

Copy this template and fill it out after testing:

```
═══════════════════════════════════════════════════════════════
TEST EXECUTION SUMMARY — Excel Upload Auto-Transition Fix
═══════════════════════════════════════════════════════════════

Date: _______________
Tester: _____________
Environment: PRODUCTION (172.105.48.142)

FUNCTIONAL TESTS
─────────────────────────────────────────────────────────────
☐ TEST 1:  Tracking-Only Upload → Auto-Ship ........... PASS/FAIL
☐ TEST 2:  Delivery + COD → Auto-Paid ................ PASS/FAIL
☐ TEST 3:  Partial COD → Auto-Paid ................... PASS/FAIL
☐ TEST 4:  Non-COD → No Auto-Pay ..................... PASS/FAIL
☐ TEST 5:  Return Status ............................ PASS/FAIL
☐ TEST 6:  Unmatched Orders (Skip) .................. PASS/FAIL
☐ TEST 7:  Partial Upload Mix ....................... PASS/FAIL
☐ TEST 8:  Multiple Status Changes .................. PASS/FAIL
☐ TEST 9:  Status History Visible ................... PASS/FAIL
☐ TEST 10: Activity Log Visible ..................... PASS/FAIL

REGRESSION TESTS
─────────────────────────────────────────────────────────────
☐ TEST 11: Manual Status Update (UI) ................ PASS/FAIL
☐ TEST 12: Shopify Upload ........................... PASS/FAIL

ERROR HANDLING
─────────────────────────────────────────────────────────────
☐ TEST 13: Invalid Format ........................... PASS/FAIL
☐ TEST 14: No Headers .............................. PASS/FAIL

PERFORMANCE
─────────────────────────────────────────────────────────────
☐ TEST 15: Bulk Upload (50 rows) ................... PASS/FAIL

BACKEND LOGS
─────────────────────────────────────────────────────────────
Errors found: _______
Warnings found: _______
Overall health: GOOD / ISSUES

SUMMARY
─────────────────────────────────────────────────────────────
Total Tests: 15
Passed: ____
Failed: ____
Success Rate: ____%

Overall Result: ✅ READY FOR PRODUCTION / ❌ NEEDS FIXES

Comments:
_________________________________________________________________
_________________________________________________________________

Signature: _________________________ Date: _______________
```

---

## Rollback Plan (If Issues Found)

If any test fails, execute rollback:

```bash
# On production server
ssh root@172.105.48.142

# Revert to previous commit
cd /opt/pureleven
git reset --hard HEAD~1
docker restart pureleven_backend

# Verify
curl -s http://localhost:8000/docs
```

---

## Success Criteria

**All tests PASS** if:
- ✅ Tracking-only uploads auto-transition to "shipped"
- ✅ Delivery uploads auto-transition to "delivered"
- ✅ COD/Partial COD auto-paid when delivered
- ✅ Non-COD NOT auto-paid
- ✅ StatusHistory entries created with meaningful notes
- ✅ ActivityLog entries created for audit trail
- ✅ Manual UI updates still work
- ✅ No errors in backend logs
- ✅ Performance acceptable for bulk uploads

---

## Sign-Off

Once ALL tests pass:

1. ✅ Tester signs off on testing
2. ✅ Product owner approves for production
3. ✅ Mark feature as "RELEASED"
4. ✅ Update deployment notes
5. ✅ Create release notes for team

---

**Feature Status:** Ready for QA Testing  
**Code Commit:** acbfae6 (fix: add auto-transition and payment status updates to Excel upload)  
**Deployment Date:** March 10, 2026  
**Testing Start:** [To be filled by QA]  
**Testing End:** [To be filled by QA]

