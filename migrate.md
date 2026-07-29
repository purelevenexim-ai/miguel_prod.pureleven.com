# XLSX Migration Report — Pureleven CRM

**Migration date:** 2026-05-04  
**Batch tag:** `xlsx_migration_full`  
**Source files:** 3 XLSX workbooks from Google Drive

---

## Source Files

| File | Sheets extracted |
|------|-----------------|
| Customer Details.xlsx | Customer Details August, Customer Details, Customer Details August11, Customer Details August20 |
| Customer Details Sept.xlsx | Customer Details Sept |
| Customer Details October.xlsx | Customer Details October |

---

## Extraction Summary

| Sheet | Rows extracted |
|-------|---------------|
| Customer Details Sept | 224 |
| Customer Details (old format) | 128 |
| Customer Details August11 | 102 |
| Customer Details August | 87 |
| Customer Details October | 86 |
| Customer Details August20 | 81 |
| **Total** | **708** |

*Skipped sheets (metadata/leads only): Order, Color Coding, Customer Call, Leads, Sheet8, Sheet9, Customer call1*

---

## Normalization Summary

| Stage | Count |
|-------|-------|
| Rows extracted | 708 |
| Normalized (ready for import) | 699 |
| Rejected (missing phone) | 9 |

**Reject reason breakdown:**

| Reason | Count |
|--------|-------|
| missing_phone | 9 |

---

## Product Mapping

- **Alias map entries:** 267 (Malayalam → English, size variants, skip tokens)
- **Mapping rows processed:** 581
- **Rows with all products resolved:** 698
- **Rows with 1 unresolved product:** 1 *(Beena Shanavas Khan — stray `"` character in items cell)*

Key product aliases added:
- Elakka 100/200/250/500 → Kerala Cardamom 8mm variants
- Grambu 50/100/200/250/500 → Clove variants  
- Kurumulaku 100/250/500/1kg → Black Pepper Kerala variants
- BP, Peppar → Black Pepper Kerala variants
- Patta, കറുവപ്പട്ട → Ceylon True Cinnamon variants
- 80+ skip tokens (payment notes, call notes) → `__SKIP__`

---

## Import Results

| Metric | Count |
|--------|-------|
| XLSX orders imported | **613** |
| Orders skipped (already in DB) | 86 |
| New customers created | 488 |
| Existing customers updated | 125 |

**All 613 imported orders finalized as: `status=delivered`, `payment_status=paid`**

---

## Database State After Migration

| Order status | Count |
|--------------|-------|
| delivered | 1,453 |
| confirmed | 12 |
| shipped | 23 |
| cancelled | 1 |
| returned | 2 |
| **Total active orders** | **1,491** |
| **Total active customers** | **1,509** |

---

## Order Distribution by Sheet

| Source sheet | Normalized | Source month |
|---|---|---|
| Customer Details Sept | 222 | September 2025 |
| Customer Details Aug/Old | 125 | August 2025 (est.) |
| Customer Details August11 | 101 | August 2025 |
| Customer Details August | 86 | August 2025 |
| Customer Details October | 85 | October 2025 |
| Customer Details August20 | 80 | August 2025 |

---

## Rejected Rows (review file: `xlsx_errors_review.md`)

9 rows could not be imported due to missing phone number:

| Name | Order ID | Sheet | Reason |
|------|----------|-------|--------|
| ഹരികൃഷ്ണൻ | — | Customer Details August | No phone in XLSX |
| Leela Roberts | — | Customer Details | No phone in XLSX |
| Bindu | — | Customer Details | No phone in XLSX |
| Sunny Varghese | — | Customer Details | No phone in XLSX |
| Rachel joseph | — | Customer Details August11 | No phone in XLSX |
| Thomas Abraham | 25090110 | Customer Details August20 | No phone in XLSX |
| KS Radha mani | Done | Customer Details Sept | No phone in XLSX |
| Shajimm | — | Customer Details Sept | No phone in XLSX |
| shajiphkairali | — | Customer Details October | No phone in XLSX |

---

## Technical Notes

- Order IDs: XLSX numeric format (e.g. `25081101`) parsed as `YYMMDDNN` → date `2025-08-11`
- `IN_XXXXXXXX` format (India Post) also parsed correctly
- Sheets without dates used sheet-name date inference (e.g. "August" → `2025-08-01`)
- Rows without ORDER ID used SHA1 `_id` hash as dedup key
- Pincodes sanitized to 6-digit numeric (stripped "Pin : XXX." prefixes)
- Phone numbers sanitized (multi-number cells take first valid number)
- Tracking numbers capped at 98 chars (multi-line item descriptions discarded)
- Payment: `Paid=Yes` → `prepaid`, `Paid=No` → `cod`

---

*Generated automatically by the migration pipeline. See `scripts/migration/` for scripts.*
