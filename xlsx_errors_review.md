# XLSX Migration — Errors Review

These rows were **not imported** during the XLSX migration on 2026-05-04.  
Action required: find phone numbers for these customers and add manually to Miguel CRM.

---

## Missing Phone — 9 rows

| # | Name | Order ID | Address hint | Sheet | Action needed |
|---|------|----------|--------------|-------|---------------|
| 1 | ഹരികൃഷ്ണൻ | — | — | Customer Details August | Find phone, add manually |
| 2 | Leela Roberts | — | — | Customer Details | Find phone, add manually |
| 3 | Bindu | — | — | Customer Details | Find phone, add manually |
| 4 | Sunny Varghese | — | — | Customer Details | Find phone, add manually |
| 5 | Rachel joseph | — | — | Customer Details August11 | Find phone, add manually |
| 6 | Thomas Abraham | 25090110 | — | Customer Details August20 | Find phone, add manually |
| 7 | KS Radha mani | Done | — | Customer Details Sept | Invalid order ID "Done"; find phone |
| 8 | Shajimm | — | — | Customer Details Sept | Find phone, add manually |
| 9 | shajiphkairali | — | — | Customer Details October | Find phone, add manually |

---

## Partially Resolved Products — 1 order

| Customer | Order number | Issue | Action needed |
|----------|-------------|-------|---------------|
| Beena Shanavas Khan | (auto-assigned at import) | Items contain a stray `"` character (data entry error in XLSX) — 2 of 3 items (Cardamom + Clove) did import correctly; `"` was skipped | Verify order in Miguel and manually check items |

---

## Notes

- 237 rows had no items recorded in the XLSX (items column was blank). These orders were still imported with ₹0 items or no line items. Verify in Miguel if needed.
- `" Customer Details"` sheet (old format) had no product items tracked — 128 orders imported as customer records with amounts only.
- Order ID `"Done"` (KS Radha mani) is not a valid order ID and the customer has no phone — cannot be imported.
