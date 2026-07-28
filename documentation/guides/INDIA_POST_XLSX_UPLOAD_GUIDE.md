# India Post xlsx Upload - Quick Start Guide

**Last Updated:** Feb 25, 2026  
**Status:** ✅ Fully Functional  

---

## 📖 Overview

Bulk assign tracking numbers and delivery status to orders using India Post xlsx reports.

**Supported Formats:**
- ✅ Simple 2-column: `Customer Name | Article Number`
- ✅ Simple 3-column: `Customer Name | Article Number | Delivery Status`
- ✅ India Post bulk report (34 columns, hyphenated headers)
- ✅ India Post custom formats (auto-detection by content)

---

## 🚀 How to Use

### Step 1: Prepare Your xlsx File

#### Option A: Simple Format (Recommended for Quick Updates)
Create a simple Excel file with 2-3 columns:

| Customer Name | Article No. | Delivery Status |
|---------------|-------------|-----------------|
| Vijaya Raman | EE123456789IN | Delivered |
| Mrs. Premalatha | EE987654321IN | Delivered |
| Basil Thomas | RX111222333IN | Undelivered |

**Column Names (auto-detected):**
- Name: `Customer Name`, `Customer`, `Receiver`, `Addressee`, etc.
- Tracking: `Article No.`, `Article Number`, `Tracking Number`, `AWB`, etc.
- Status: `Delivery Status`, `Status`, `Event`, etc.

#### Option B: India Post Bulk Report Format
Download directly from India Post portal. Supports all 34-column formats with hyphenated headers.

### Step 2: Upload via Frontend

1. **Navigate:** Orders page → scroll to top toolbar
2. **Click** one of three buttons:
   - 🔍 **Preview xlsx** — Verify matches before committing
   - 📄 **Tracking xlsx** — Upload tracking numbers only (auto-advances status to "shipped")
   - ✅ **Delivery xlsx** — Upload with delivery status (auto-sets "delivered" + marks COD paid if applicable)

3. **Select your xlsx file** → Upload

### Step 3: Review Results

#### Success Response
```json
{
  "success": true,
  "updated_count": 2,
  "skipped_count": 0,
  "delivered_and_paid": 1,
  "updated": [
    {
      "order_number": "PRM-260225-038",
      "customer": "Vijaya Raman,",
      "tracking": "EE123456789IN",
      "action": "delivered"
    }
  ]
}
```

#### Preview Modal
Click 🔍 **Preview xlsx** to see matched/unmatched rows **before** making changes:
- Green rows: ✅ Matched to an order
- Red rows: ❌ Could not match (reason shown)

---

## 📋 What Happens to Your Orders

### When You Upload (Tracking Only)
```
Order Status Changes:
  confirmed → shipped  (if no previous tracking)
  shipped, out_for_delivery, delivered, returned → unchanged (already advanced)

Tracking Assigned:
  tracking_number = "EE123456789IN"
  courier_name = "India Post"
```

### When You Upload (With Delivery Status)
If `Delivery Status` column = "Delivered":
```
Order Status Changes:
  ANY → delivered
  delivered_at = now()
  
Payment Status (COD orders only):
  IF payment_method = "cod" OR "partial_cod":
    payment_status = "paid"
    amount_paid = total_amount
    amount_due = 0
```

If `Delivery Status` = "Returned" or "Undelivered" or "RTO":
```
Order Status Changes:
  ANY → returned
```

---

## 🔍 Matching Logic

The xlsx upload matches rows to orders using this priority:

1. **Exact Tracking Number Match** (highest priority)
   - If `article-number = EE123456789IN` and an order already has this tracking → **instant match**
   
2. **Fuzzy Customer Name Match** (fallback)
   - Strips titles (Mr., Mrs., Dr., Sri, Smt., etc.)
   - Strips punctuation (commas, periods, hyphens)
   - Normalizes whitespace
   - Example: `"Mrs. Premalatha,"` (from xlsx) matches `"Premalatha"` (from order delivery_name)
   - Word-subset matching: if xlsx has `"Vijaya Raman"` and order has `"Vijaya Raman, Chennai"` → **match**

3. **No Match** → Skipped row (reason logged)

---

## ⚙️ Supported Column Headers

### Customer Name Columns
```
customer name        receiver name       customer        addressee
sender name          recipient           consignee       party name
to name              beneficiary         customer-name   receiver-name
sender-name
```

### Article/Tracking Columns
```
article no.          article no          article number      article-number
article-no           tracking no.        tracking no         tracking number
tracking-number      tracking_number     awb                 awb number
barcode              consignment no      consignment no.     consignment number
booking no           booking no.         booking number      speed post no
parcel no            parcel number       reg no              registered no
```

### Delivery Status Columns
```
delivery status      status              delivered          shipment status
current status       delivery            event              current event
latest status        remarks             delivery remarks   status description
scan event           scan status         event-description  event-code
event-description    event-code          event description  event code
```

---

## 🛠️ Troubleshooting

### Issue: File returns 400 Bad Request
**Cause:** Column headers not recognized  
**Solution:**
1. Click 🔍 **Preview xlsx** first to see detected headers
2. Frontend shows: `Headers: ['col1', 'col2', ...]`
3. Rename columns to match one of the supported headers above
4. Re-upload

### Issue: Rows show as "Unmatched"
**Cause:** Customer name in xlsx doesn't match any order  
**Solution:**
1. Verify customer name spelling matches order's `delivery_name` exactly
2. Use Preview to see which names were matched vs unmatched
3. Edit xlsx with correct names

### Issue: Order status not updating to "Delivered"
**Cause:** Delivery Status column value not recognized  
**Solution:** Use exact keywords:
- ✅ "Delivered" / "Delivery" / "DLV" / "Success" / "DEL"
- ❌ "DELIV" / "Deliverd" (misspelled)

### Issue: Nothing changes after upload
**Cause:** No orders matched (all skipped)  
**Solution:**
1. Run Preview first to diagnose
2. Check: tracking numbers exist in xlsx? customer names match?
3. Use simpler 2-column format: just Name + Article Number

---

## 📊 Real-World Examples

### Example 1: Simple Tracking Update
**File:** `tracking_feb25.xlsx`
```
Customer Name        | Article Number
Vijaya Raman,        | EE100000001IN
Mrs. Premalatha,     | EE100000002IN
```

**Result:**
```
✅ PRM-260225-038 → tracking updated → shipped
✅ PRM-260225-037 → tracking updated → shipped
Skipped: 0
```

### Example 2: Delivery Confirmation
**File:** `delivery_feb25.xlsx`
```
Receiver Name     | Article No. | Event Description
Vijaya Raman      | EE100000001IN | Delivered
Mrs. Premalatha   | EE100000002IN | Returned
```

**Result:**
```
✅ PRM-260225-038 → delivered + COD paid ✅
✅ PRM-260225-037 → returned
Skipped: 0
```

### Example 3: India Post Bulk Report
**File:** Download from India Post portal (34 columns)  
**Column Detection:** Automatic
```
✅ Detected: article-number @ col 13, receiver-name @ col 24, event-description @ col 27
✅ PRM-260225-038 → Matched by receiver name, updated
✅ PRM-260225-037 → Matched by receiver name, updated
Skipped: 0
```

---

## 🔐 Data Integrity

### What's Safe
- ✅ Multiple uploads of same file (idempotent — won't duplicate)
- ✅ Partial matches (only matched rows updated)
- ✅ Updating delivered orders (allowed for final confirmations)
- ✅ Previous tracking numbers preserved if not in new xlsx

### What's Protected
- ❌ Cannot change customer details via xlsx (name field is read-only for matching)
- ❌ Cannot delete orders
- ❌ Cannot unassign tracking (set to NULL)

---

## 📞 Support

For issues:
1. Check `docker logs miguel_backend --tail=50 | grep xlsx-upload`
2. Headers and any errors will be logged
3. Use Preview modal to debug before uploading

---

## 🔄 API Endpoints (For Developers)

### Upload & Process
```bash
POST /api/shipments/manual-orders/india-post-xlsx
Content-Type: multipart/form-data
Authorization: Bearer $TOKEN

Form Data:
  file: (binary xlsx file)

Response:
  {
    "success": true,
    "updated_count": 2,
    "skipped_count": 0,
    "delivered_and_paid": 1,
    "updated": [...],
    "skipped": [...]
  }
```

### Preview Only
```bash
POST /api/shipments/manual-orders/india-post-xlsx-preview
Content-Type: multipart/form-data
Authorization: Bearer $TOKEN

Response:
  {
    "total_rows": 3,
    "matched_count": 2,
    "unmatched_count": 1,
    "headers_found": {
      "name_col": "receiver-name",
      "track_col": "article-number",
      "status_col": "event-description"
    },
    "matched": [...],
    "unmatched": [...]
  }
```

---

