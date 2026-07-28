# PurEleven CRM — Data Issues Todo List
_Generated: 2026-05-05 | Status after XLSX migration cleanup session_

---

## ✅ FIXED IN THIS SESSION

| # | Issue | Fix Applied |
|---|-------|-------------|
| 1 | **May 2026 revenue spike (₹7.7L)** — 613 XLSX orders imported with `created_at = import_date` (May 4, 2026) instead of their actual historical dates | Updated `created_at` and `delivered_at` from `SOURCE_CREATED_TS` embedded in order notes |
| 2 | **XLSX orders with wrong prefix** — 613 orders from Customer Details.xlsx had `PUR-` prefix, indistinguishable from native CRM orders | Renamed `PUR-XXXXXX-NNN` → `XLSX-XXXXXX-NNN` for all 613 orders |
| 3 | **Orders page showing 883 instead of 1,491** — stale in-memory TTL cache from before XLSX migration | Backend restarted to clear in-process cache |
| 4 | **All 1,035 customers had `total_orders = 0`** — bulk import bypassed `_update_customer_stats()` | Bulk UPDATE recalculated `total_orders`, `average_order_value`, `first_order_date`, `last_order_date` |
| 5 | **XLSX orders missing `delivered_at`** — import script didn't set `delivered_at` despite setting status=delivered | Set `delivered_at = created_at` for all 613 XLSX orders |
| 6 | **Profit Checker showing 617 delivered in "This Month"** — side effect of May 2026 spike | Fixed via created_at correction above |

---

## 🔴 HIGH PRIORITY — Fix Soon

### H1: Sep 2025 Revenue Outlier — XLSX-250920-008
- **Problem**: One XLSX order has `total_amount = ₹3,06,520` — almost certainly a data entry error in the original Excel file
- **Impact**: Sep 2025 shows ₹4.79L revenue vs ~₹0.9L for all other months. Inflates Total Revenue and Avg Order Value
- **DB**: `SELECT order_number, total_amount FROM orders WHERE order_number = 'XLSX-250920-008'`
- **Action needed**: Manually investigate original Excel Row 104 of "Customer Details Sept.xlsx". Fix or set the correct amount.
- **Note**: Without fixing this, Total Revenue is overstated by ~₹3L and Sep 2025 in dashboard looks anomalous

### H2: 5 Stale "Shipped" Orders Never Delivered
- **Problem**: 5 orders have been in `shipped` status for 30–200+ days
- **Orders**:
  | Order | Date | Amount | Tracking | Age |
  |-------|------|--------|----------|-----|
  | PUR-251016-003 | Oct 16, 2025 | ₹4,500 | None | 7+ months |
  | PUR-251205-002 | Dec 5, 2025 | ₹280 | CL346334431IN | 5+ months |
  | PUR-251212-005 | Dec 12, 2025 | ₹1,330 | CL346339867IN | 5+ months |
  | PUR-251215-008 | Dec 15, 2025 | ₹600 | EL570351055IN | 4+ months |
  | PRN-260321-073 | Mar 21, 2026 | ₹999 | CL377891094IN | 1.5 months |
- **Action needed**: Check tracking status — mark as `delivered` or `returned`

### H3: 320 XLSX Orders Missing Line Items (order_items table)
- **Problem**: 320 of the 613 XLSX orders have no entries in `order_items` table — the import script created order headers but not the product line items
- **Impact**: These orders don't appear in:
  - Profit Checker SKU analysis (no per-product profit/loss)
  - Top Products table on dashboard
  - Product sales reports
- **Prefix breakdown**: All 320 are XLSX- batch orders
- **Action needed**: Either re-import with product matching OR accept that historical XLSX orders won't have per-SKU profitability data

### H4: 53 Zero-Amount Orders (total_amount = ₹0)
- **Problem**: 53 XLSX/PUUR orders have `total_amount = 0`
  - 14 in Oct 2025, 24 in Sep 2025, 12 in Aug 2025, 2 in Jul 2025, 1 in Feb 2026
- **Impact**: Pulls down Avg Order Value; obscures revenue accuracy
- **Sample query**: `SELECT order_number, notes FROM orders WHERE total_amount=0 AND tenant_id='...' AND is_active=true LIMIT 5`
- **Action needed**: Review original Excel data for these rows; either set actual amounts or mark as test/gift orders

---

## 🟡 MEDIUM PRIORITY — Fix When Possible

### M1: All 1,492 Orders Have `tax_amount = 0` — GST Gap
- **Problem**: No order has any tax data. GST & Accounting page shows ₹0 tax for all periods
- **Impact**: GSTR-1 filing data is incomplete — cannot generate accurate GST returns from the CRM
- **Root cause**: Import scripts didn't carry tax data; native CRM orders (PRN-) also have `tax_amount = 0`
- **Action needed**: For new PRN- orders: ensure tax is calculated at order creation. For historical: manually add GST breakdown if required for filing.

### M2: 21 XLSX Orders Missing Delivery Address
- **Problem**: 21 XLSX orders (all XLSX- prefix) have NULL or empty `delivery_address`
- **Impact**: Cannot print labels for these; address field blank in order view
- **Query**: `SELECT order_number, delivery_name FROM orders WHERE delivery_address IS NULL AND tenant_id='...' AND is_active=true`
- **Action needed**: Cross-reference with original Excel to fill in addresses

### M3: PUUR Orders Cannot Be Renamed to XLSX Prefix
- **Problem**: 76 order number collisions would occur if PUUR-XXXXXX is renamed to XLSX-XXXXXX (since XLSX-XXXXXX orders already exist from the PUR→XLSX rename)
- **Current state**: 
  - XLSX-XXXXXX (613 orders) = new Customer Details.xlsx batch ✅ done
  - PUUR-XXXXXX (604 orders) = orders from labels.pureleven.com (also from XLSX source)
- **Action needed**: Decide if PUUR prefix should stay or be renamed to a non-conflicting prefix (e.g., `XLSP-` or `HIST-`)

### M4: Sep 2025 Has 218+ PUUR Orders — Validate Data
- **Problem**: Sept 2025 has unusually many orders from PUUR batch. Need to verify these are not duplicates
- **Action**: Check if the PUUR September orders also exist in the XLSX new batch (deduplication check)

### M5: Dashboard "Sales by State" Shows Majority as "Unknown"
- **Problem**: Most XLSX/PUUR orders don't have a recognized `delivery_state` — they appear as "Unknown" in Sales by State chart
- **Impact**: State-wise reporting is unreliable for historical data
- **Action needed**: Check if delivery_state field is properly populated; run state normalization on imported orders

---

## 🔵 LOW PRIORITY / INFORMATIONAL

### L1: Aug 2024 Orphan Order
- One order from Aug 2024 (XLSX-240815-001). Single record, possibly a test or very early order in the Excel file.
- No action needed unless it's causing report noise.

### L2: Jan 2026 High Single Order (₹10,050)
- One order in Jan 2026 was ₹10,050 — higher than typical. Verify legitimacy vs data error.

### L3: PUUR Orders Do Not Have `delivered_at` Set
- 604 PUUR orders from labels.pureleven.com are `status=delivered` but `delivered_at` may be NULL or approximate
- Impact: Revenue-by-month in dashboard uses `delivered_at` for some calculations
- Action: Consider setting `delivered_at = created_at` for PUUR orders where `delivered_at IS NULL`

---

## 📊 Current Data Summary (Post-Fix)

| Metric | Value |
|--------|-------|
| Total Active Orders | 1,492 |
| XLSX- prefix (new batch) | 613 |
| PUUR- prefix (labels src) | 604 |
| PRN- prefix (native CRM) | 271 |
| PUR- prefix (native, old) | 4 |
| Active Customers | 1,509 |
| May 2026 Revenue (correct) | ₹25,039 (29 orders) |
| Total Revenue (incl. H1 outlier) | ₹15.7L |

---

## 🛠 Useful Queries for Investigation

```sql
-- Find and fix Sep 2025 outlier
SELECT order_number, total_amount, notes 
FROM orders WHERE order_number = 'XLSX-250920-008';

-- View all zero-amount orders
SELECT order_number, created_at::date, notes
FROM orders WHERE total_amount=0 AND tenant_id='4374ad45-76b5-405b-8a3d-de49710fbdc3' AND is_active=true;

-- Fix PUUR delivered_at if needed
UPDATE orders SET delivered_at = created_at, updated_at=NOW()
WHERE LEFT(order_number,4)='PUUR' AND status::text='delivered' AND delivered_at IS NULL
AND tenant_id='4374ad45-76b5-405b-8a3d-de49710fbdc3';

-- Monthly revenue after removing Sep outlier
SELECT TO_CHAR(DATE_TRUNC('month',created_at),'Mon YYYY'), 
  COUNT(*), ROUND(SUM(CASE WHEN total_amount < 50000 THEN total_amount ELSE 0 END)/100000,2) AS revenue_excl_outlier
FROM orders WHERE tenant_id='4374ad45-76b5-405b-8a3d-de49710fbdc3' AND is_active=true
GROUP BY 1, DATE_TRUNC('month',created_at) ORDER BY 2 DESC;
```
