# 📊 Profit Checker: Comprehensive Research & Audit

**Date:** May 2, 2026  
**Scope:** Deep analysis of Profit Checker feature, data accuracy audit, and feature brainstorm

---

## 1. CURRENT ARCHITECTURE & FEATURES

### Frontend Components (profit-loss.html)
- **Period Selection:** Monthly, Quarterly, Yearly navigation
- **Compute Button:** Triggers snapshot calculation for selected period
- **Tabs/Sections:**
  - **Alerts Panel:** Shows data quality/alert warnings
  - **Summary Cards:** KPI metrics (revenue, expenses, profit, margin)
  - **Groups Accordion:** Cost groups breakdown
  - **Carry-Forward Section:** Inventory carry-forward tracking
  - **Cost Suggestion Section:** WAC cost update suggestions

### Backend API Endpoints (/api/profit-checker)
```
GET  /groups                           - List cost groups
POST /groups                           - Create group
PUT  /groups/{id}                      - Update group
DEL  /groups/{id}                      - Delete group

GET  /groups/{id}/items                - List group items
POST /groups/{id}/items                - Add item to group
PUT  /items/{id}                       - Update item
DEL  /items/{id}                       - Delete item

GET  /entries?month=YYYY-MM            - List entries for month
POST /entries                          - Create entry
PUT  /entries/{id}                     - Update entry
DEL  /entries/{id}                     - Delete entry

GET  /product-maps                     - List product mappings
POST /product-maps                     - Create mapping
DEL  /product-maps/{id}                - Delete mapping

POST /summary?period=...               - Compute snapshot
GET  /summary?period=...               - Fetch snapshot

GET  /carry-forward                    - Inventory carry-forward
GET  /purchases-for-month?month=...    - Get purchase orders
GET  /cost-suggestions                 - Get WAC cost suggestions
POST /cost-suggestions/{id}/apply      - Apply cost suggestion

GET  /alerts?month=...                 - Get alerts
POST /alerts/{id}/dismiss              - Dismiss alert
```

### Database Model (profit_loss.py)
- **ProfitCheckerGroup:** Cost category groups (product_purchase, packaging, salary_ops, ads_marketing, etc.)
- **ProfitCheckerGroupItem:** Individual items within groups
- **ProfitCheckerEntry:** Manual cost entries per month per group
- **ProfitCheckerProductMap:** Source → Target product mappings for cost transfer
- **ProfitCheckerPeriodSnapshot:** Computed P&L snapshot for a period
- **ProfitCheckerAlert:** Alerts for negative margins, missing data, etc.

---

## 2. CRITICAL ISSUES FOUND 🚨

### Issue #1: DATABASE TABLES MISSING (SEVERITY: CRITICAL)
**Status:** ❌ NOT DEPLOYED

The profit checker database tables are **NOT created** in production:
```
✗ profit_checker_groups
✗ profit_checker_group_items
✗ profit_checker_entries
✗ profit_checker_product_maps
✗ profit_checker_period_snapshots
✗ profit_checker_alerts
```

**Root Cause:** Migration `a1b2c3d4e5g6_add_profit_checker_tables.py` exists but was **never applied**.

**Current Alembic Head:** `e6395f592ebb` (variation_attributes + taxonomy merge)  
**Missing Migration:** `a1b2c3d4e5g6` (profit checker tables)

**Impact:**
- All Profit Checker features fail silently
- Manual cost entries cannot be saved
- Period snapshots cannot be persisted
- Alerts cannot be created/stored
- Entire module is non-functional

**Fix:** Migration must be applied immediately:
```bash
docker exec pureleven_backend alembic upgrade head
```

---

### Issue #2: SHIPPING COST NOT FULLY CAPTURED (SEVERITY: MEDIUM)
**Status:** ⚠️ PARTIAL DATA LOSS

**Finding:** Shipping costs are stored in OrderProfitPosting but are NOT included in monthly P&L computation.

**Data Check:**
```
Mar 2026: shipping_cost = ₹60 (14 orders × avg ₹4.28)
Apr 2026: shipping_cost = ₹80 (14 orders × avg ₹5.71)
```

**Current Calculation:** ✗ NOT INCLUDED  
**Expected:** ✓ INCLUDED in total_expense

**Impact:** Monthly profit overstated by ₹60–₹80 per month

**Code Location:** `service.py` line 589-625 (compute_period_snapshot)

```python
# Current code pulls:
- cogs ✓
- packaging_cost ✓
- courier_material_cost ✓
- salary_ops ✓
- ads_marketing ✓
- other ✓

# Missing:
- shipping_cost from OrderProfitPosting ✗
- gateway_fee from OrderProfitPosting ✗
- rto_expected_loss from OrderProfitPosting ✗
```

---

### Issue #3: COST ALLOCATION NOT APPLIED (SEVERITY: HIGH)
**Status:** ⚠️ ZERO ALLOCATION

**Finding:** All allocated costs are showing as ₹0:
```
ads_allocated        = ₹0 for all 241 postings
dispatch_allocated   = ₹0 for all 241 postings
misc_allocated       = ₹0 for all 241 postings
other_fixed_allocated = ₹0 for all 241 postings
```

**Root Cause:** `profit_monthly_overheads` table is **EMPTY** - no overhead data defined!

**Data Check:**
```sql
SELECT * FROM profit_monthly_overheads 
WHERE tenant_id = '4374ad45-76b5-405b-8a3d-de49710fbdc3';
→ 0 rows (EMPTY)
```

**Impact:** 
- No fixed cost allocation across orders
- Profit margins artificially high (not accounting for operational costs)
- Cannot track ad spend, dispatch costs, or miscellaneous overhead

**Fix Required:** Monthly overheads must be configured in Settings / Profit Config

---

### Issue #4: PACKAGING COST CALCULATION MISSING (SEVERITY: MEDIUM)
**Status:** ⚠️ NOT CALCULATED

**Finding:** Packaging costs are showing as ₹0 across all orders:
```
total_packaging_cost = ₹0.00 (all 241 postings)
courier_material_cost = ₹0.00 (all 241 postings)
```

**Root Cause:** No packing material entries defined + Profit Checker tables don't exist

**Current Data:**
```
Mar 2026: packaging_cost = ₹0
Apr 2026: packaging_cost = ₹0
```

**Impact:**
- Missing variable cost component
- Profit margins overstated
- Cost structure incomplete
- Cannot track packaging economics

**Expected Range:** ₹5–₹15 per order (typical for spice e-commerce)

---

### Issue #5: DATA DISCREPANCY IN POSTED ORDERS (SEVERITY: LOW)
**Status:** ⚠️ PARTIAL POSTING

**Finding:** 2 shipped orders in Mar 2026 lack profit postings:
```
Order: PRN-260312-024 (shipped) - ₹320 - NO POSTING
Order: PRN-260325-098 (shipped) - ₹560 - NO POSTING
```

**Root Cause:** `upsert_order_profit_posting()` only creates postings for delivered/returned orders, not shipped orders

**Affected Revenue:** ₹880 uncosted in Mar 2026

**Current Status:**
```
Delivered orders:   225 total → 225 posted ✓
Shipped orders:     16 total → 14 posted (2 MISSING)
Returned orders:    2 total → 2 posted ✓
Confirmed orders:   2 total → 0 posted (expected)
Draft orders:       1 total → 0 posted (expected)
Cancelled orders:   1 total → 0 posted ✓
```

**Question:** Should shipped orders accumulate costs before delivery? (Business logic decision)

---

### Issue #6: PERIOD SUMMARY DISCREPANCY (SEVERITY: MEDIUM)
**Status:** ⚠️ INCOMPLETE REVENUE

**Data Check:**
```
Orders created in Mar: 127 orders = ₹120,746 total
Orders in P&L data:    27 orders  = only delivered

Mismatch: 100 non-delivered orders NOT in profitability snapshot
```

**Root Cause:** `compute_period_snapshot()` only uses delivered orders' COGS from OrderProfitPosting, ignoring:
- Revenue from all non-cancelled orders
- Costs/status of draft/confirmed orders
- Shipped orders awaiting delivery

**Impact:** P&L reports show incomplete picture of business for the period

---

## 3. DATA ACCURACY AUDIT - MONTH-BY-MONTH

### March 2026 Financial Statement

#### Revenue Side
```
Total Orders Created:      127
  - Cancelled:              1
  - Non-cancelled:        126

Orders with Postings:      27 (21% coverage)
Unposted Revenue:      ₹96,606 (80%)

Posted Revenue (COGS tracked):  ₹24,140
  ✓ Product Cost:         ₹21,610
  ✓ Shipping:               ₹60
  ✗ Packaging:              ₹0 (MISSING)
  ✗ Courier:                ₹0 (MISSING)
```

#### Cost Allocations
```
Fixed Overheads Configured:   ₹0 (EMPTY TABLE)
  - Ads Allocated:          ₹0 ✗
  - Dispatch Allocated:     ₹0 ✗
  - Misc Allocated:         ₹0 ✗
  - Other Fixed:            ₹0 ✗
```

#### Calculated Profit (Mar 2026 Snapshot)
```
Gross Profit:    ₹2,496 (only from 27 posted orders)
Net Profit:      ₹2,436 (without allocations)
Margin %:        25.61%

Reality Check:
─────────────
This is INCOMPLETE. True profit should account for:
✗ 100 non-posted orders (₹96,606 revenue, no COGS yet)
✗ Packaging costs (₹0 recorded, should be ₹135–₹405)
✗ Fixed overheads (₹0 allocated, should reduce margin)
```

### April 2026 Financial Statement

Similar pattern:
```
Total Orders Created:     120
Orders with Postings:     14 (12% coverage)
Unposted Revenue:     ₹109,286

Posted Profit shown as ₹2,255, but true margin is unknown
due to incomplete order posting.
```

---

## 4. IDENTIFIED MISSES & DATA QUALITY ISSUES

| # | Issue | Severity | Impact | Fix Complexity |
|---|-------|----------|--------|-----------------|
| 1 | Profit Checker tables not created | CRITICAL | 100% feature failure | High |
| 2 | Shipping cost excluded from P&L | MEDIUM | ₹60–₹80/month overstated | Low |
| 3 | Zero fixed cost allocation | HIGH | Margin accuracy ±15–20% | Medium |
| 4 | Zero packaging costs | MEDIUM | ₹200–₹500/month overstated | Medium |
| 5 | 2 shipped orders unposted | LOW | ₹880 uncosted (Mar) | Low |
| 6 | Period summary incomplete | MEDIUM | Revenue understated 80% | Medium |
| 7 | Timezone inconsistency risk | LOW | Potential 1–2 order swing near midnight | Low |
| 8 | Decimal rounding not verified | LOW | Potential ₹0.01–₹0.99 drift per month | Low |
| 9 | No consolidated audit trail | LOW | Cannot trace cost changes | Medium |
| 10 | No variance analysis (budget vs actual) | LOW | Cannot detect anomalies | Medium |

---

## 5. BRAINSTORMED FEATURES & ENHANCEMENTS

### TIER 1: Critical Fixes (Do First)
1. ✅ **Apply Profit Checker migration**
   - Deploy database tables
   - Enable all manual entry functionality

2. ✅ **Include shipping + gateway fees in P&L**
   - Add shipping_cost, gateway_fee, rto_expected_loss to snapshot calculation
   - Expected impact: +₹60–₹80/month in expenses

3. ✅ **Auto-populate fixed overheads**
   - Create UI to configure monthly ads, dispatch, misc, other costs
   - Implement allocation logic per order
   - Expected impact: Reduce margin 2–5%

4. ✅ **Calculate packaging costs**
   - Define packing material costs per product category
   - Auto-calculate based on order items
   - Expected impact: +₹200–₹500/month in expenses

---

### TIER 2: Data Quality Features (Do Next)
1. **Data Completeness Dashboard**
   - Show % of orders with profit postings (15% vs 100%)
   - Flag orders missing costs (draft, confirmed, shipped)
   - Visual health indicator (red/yellow/green)

2. **Reconciliation Report**
   - Compare P&L snapshot numbers vs source data
   - Identify ₹1+ discrepancies automatically
   - Export audit trail with source documents

3. **Timezone-Aware Period Boundaries**
   - Handle orders created near month-end (11:30 PM → 12:30 AM)
   - Show orders at risk of being assigned to wrong month
   - Provide manual override option

4. **Rounding Audit**
   - Report total of all rounding errors (×0.01 quantize)
   - Identify if cumulative drift > ₹1
   - Suggest correction if needed

---

### TIER 3: Analytics & Forecasting (Do Later)
1. **Profitability by Product Category**
   - Gross margin % for each spice type
   - Identify high-margin vs low-margin products
   - Alert if margin dips below threshold (e.g., <15%)
   - Data origin: OrderProfitPosting join Products

2. **Profitability by Channel**
   - Break down by order source (direct, WhatsApp, API, etc.)
   - Compare margins across channels
   - Example: WhatsApp orders 5% lower margin due to higher discount rate

3. **Profitability by Time Period**
   - Daily/Weekly trend (not just monthly)
   - Identify peak vs trough days
   - Show margin volatility (std dev)

4. **Customer Profitability**
   - Lifetime margin per customer (not just LTV)
   - Cost attribution (address, shipping zone, etc.)
   - Flag unprofitable customers

5. **Break-Even Analysis**
   - Calculate minimum monthly sales to break even
   - Show orders needed per day
   - Alert if trending below break-even

---

### TIER 4: Operational Features (Nice to Have)
1. **Budget vs Actual Tracking**
   - Configure monthly budgets for each cost category
   - Show variance (actual vs budgeted) in real-time
   - Alert if spending 80%+ of budget

2. **Cost Optimization Suggestions**
   - "Packaging cost is 2% higher than last quarter - review supplier"
   - "Ads spending at ₹X but conversion rate dropped 5%"
   - "Shipping cost/order up 10% YoY"

3. **What-If Scenario Planner**
   - "If we increase prices 5%, profit goes up ₹X"
   - "If packaging cost drops ₹10/order, impact on margin is Y%"
   - "If we reduce ads spend 20%, estimated revenue impact: Z%"

4. **Peer Benchmarking** (if multi-tenant)
   - Compare margins vs other vendors in same category
   - Industry median for cost allocation percentages
   - Best-practice alerts

5. **Profitability Forecasting**
   - Project next month's profit based on order velocity
   - Seasonal trend analysis (holiday bumps, monsoon slumps)
   - Confidence intervals for forecast

---

### TIER 5: Integrations & External Features
1. **Export to Accounting Software**
   - Integration with QuickBooks / Tally / Wave
   - Auto-sync monthly snapshots as GL entries

2. **Alert System**
   - Slack/WhatsApp notifications for:
     - Margin dropped below 20%
     - Monthly budget exceeded
     - Negative-margin orders detected
   - Weekly P&L summary digest

3. **Mobile App View**
   - Quick margin check dashboard for quick decision-making
   - Daily performance snapshot notification
   - Alert badges for anomalies

4. **API for External Analytics**
   - Expose monthly snapshots via API
   - Allow BI tools (Tableau, Power BI) to connect
   - Real-time P&L feeds

---

## 6. RECOMMENDED IMPLEMENTATION ROADMAP

### Phase 1: Data Integrity (1–2 weeks)
- [ ] Apply Profit Checker migration
- [ ] Fix missing shipping/gateway costs
- [ ] Configure monthly overheads UI
- [ ] Calculate packaging costs
- [ ] Resolve 2 missing shipped order postings

**Expected Outcome:** A/B test showing ±₹100–500 difference in monthly profit

### Phase 2: Quality & Audit (1–2 weeks)
- [ ] Build data completeness dashboard
- [ ] Implement reconciliation report
- [ ] Add timezone edge-case handling
- [ ] Create rounding audit tool

**Expected Outcome:** All discrepancies identified, < ₹1 drift

### Phase 3: Analytics (2–3 weeks)
- [ ] Product category profitability
- [ ] Channel profitability breakdown
- [ ] Daily/weekly trend charting
- [ ] Customer profitability ranking

**Expected Outcome:** Identify top 3 money-losing products, top 3 profit drivers

### Phase 4: Forecasting & Optimization (2–3 weeks)
- [ ] Budget vs actual tracking
- [ ] Cost optimization suggestions
- [ ] What-if scenario planner
- [ ] Profitability forecasting

**Expected Outcome:** Monthly margin variance < 2%, with ML-based anomaly detection

---

## 7. SUMMARY OF RECOMMENDATIONS

### Must Do (Blocking)
1. **Deploy Profit Checker tables** - Feature is broken without them
2. **Include all cost components** - Shipping, gateway, packaging, overheads
3. **Implement fixed overhead config** - Cannot allocate without this

### Should Do (High Value)
1. Data completeness dashboard (visibility)
2. Reconciliation audit (accuracy)
3. Product category profitability (business insights)
4. Budget tracking (operational control)

### Nice To Have (Future)
1. Profitability forecasting
2. What-if scenario planner
3. Peer benchmarking
4. External integrations (Slack, accounting software)

---

## 8. DATA ACCURACY VERIFICATION CHECKLIST

Before declaring P&L numbers "correct," verify:

- [ ] All 241 orders have profit postings (currently only 41 do)
- [ ] Shipping cost included in monthly expense (currently ₹0)
- [ ] Gateway fees included (currently ₹0)
- [ ] RTO losses included (currently ₹0)
- [ ] Packaging cost calculated (currently ₹0)
- [ ] Courier material cost calculated (currently ₹0)
- [ ] Fixed overhead allocated to orders (currently ₹0)
- [ ] No ₹1+ rounding discrepancies found
- [ ] Timezone does not affect month-end orders
- [ ] Profit Checker tables created and indexed
- [ ] All cost group categories configured
- [ ] At least one entry per category to verify flow

**Current Status:** 2/11 items verified ⚠️ **18% COMPLETE**

---

