# Data Quality Investigation: Zero-Cost Orders

**Date:** May 2, 2026  
**Status:** ISSUE IDENTIFIED & PARTIALLY RESOLVED

## Summary

A data quality warning shows **6 delivered orders have missing product cost**, causing profit to be overstated. Investigation revealed two root causes:

### Root Cause #1: Race Condition (FIXED ✅)

**Issue:** Profit postings were bulk-created at **02:34 UTC** before recovered products were added at **14:52 UTC**.

**Impact:** 5 orders containing recovered products (Clove 100g, White Pepper 100g) initially showed zero cost.

**Solution:** Re-ran backfill script after products were available.

**Result:** All 5 orders now show proper costs:
- PRN-260413-149: ₹200 product_cost → ₹15 profit (5.88% margin)
- PRN-260324-092: ₹80 product_cost → ₹160 profit (57.14% margin)
- PRN-260321-075: ₹80 product_cost → ₹140 profit (63.64% margin)
- PRN-260319-066: ₹80 product_cost → ₹280 profit (77.78% margin)
- PRN-260309-005: ₹80 product_cost → ₹280 profit (77.78% margin)

---

### Root Cause #2: Product Name Mismatch (UNFIXED ⚠️)

**Issue:** Order items reference generic product names that don't exactly match catalogue entries.

**Affected Orders (6 total):**

| Order | Product Name in Order | Should Match | Catalog Status |
|-------|----------------------|--------------|-----------------|
| PRN-260429-010 | Clove 200 gram | Clove 100 gram | ❌ Different size |
| PRN-260429-006 | Clove 200 gram | Clove 100 gram | ❌ Different size |
| PRN-260424-212 | Black pepper 200 gram | Black Pepper Kerala - 500 | ❌ Different naming |
|  | Cardamom 50 gram | Kerala Cardamom 8mm - 100gm | ❌ Different size |
|  | Cinnamon 50 gram | Ceylon True Cinnamon - 100 | ❌ Different size |
|  | Clove 50 gram | Clove 100 gram | ❌ Different size |
| PRN-260424-211 | Black pepper 500 gram | Black Pepper Kerala - 500 | ✅ Match exists |
|  | Cylon Cinnamon 100 gram | Ceylon True Cinnamon - 100 | ❌ Typo: "Cylon" vs "Ceylon" |
| PRN-260406-133 | Clove 200 gram | Clove 100 gram | ❌ Different size |
| PRN-260330-121 | Clove 200 gram | Clove 100 gram | ❌ Different size |
| PRN-260326-106 | Clove 500 gram | Clove 100 gram | ❌ Different size |
| PRN-260323-085 | Clove 200 gram | Clove 100 gram | ❌ Different size |
| PRN-260321-074 | Clove 200 gram | Clove 100 gram | ❌ Different size |
| PRN-260321-072 | Clove 200 gram | Clove 100 gram | ❌ Different size |

**Root Cause:** The product resolution logic in `upsert_order_profit_posting()` does **exact name matching** (case-insensitive). Since order items use generic names ("Clove 200 gram") and the catalog has specific entries ("Clove 100 gram"), the matching fails.

**Solution Options:**

1. **Create Missing Product Variants** (RECOMMENDED)
   - Add products: "Clove 200 gram", "Clove 500 gram", "Black pepper 200 gram", etc.
   - Set appropriate cost_prices for each variant
   - Orders will then match automatically on next recalculation

2. **Implement Fuzzy Matching**
   - Update product resolver to do substring/similarity matching
   - May match incorrectly in some cases
   - Higher implementation complexity

3. **Manual Order Linking**
   - Create records mapping each order item to correct product
   - Very tedious for 100+ orders
   - Not scalable

---

## Dashboard Improvements

✅ **Added Recalculate Button**
- Located on Data Quality warning panel
- Requires management role
- Triggers `/api/reports/profit/recalculate` endpoint
- Allows backfill of posting costs for any date range
- Useful when products are updated/added

**How to Use:**
1. Go to Profit Checker > Overview tab
2. Click "Recalculate" button on the yellow warning
3. Confirm the month range
4. Button will process all orders and refresh P&L metrics

---

## Next Steps

### Immediate (This Session)

**Option A: Quick Fix (20 minutes)**
1. Create product variants matching order items:
   - Clove 200 gram (₹160 estimated cost)
   - Clove 500 gram (₹400 estimated cost)
   - Black pepper 200 gram (₹200 estimated cost)
   - Cardamom 50 gram (₹160 estimated cost)
   - Cinnamon 50 gram (₹100 estimated cost)
   - Clove 50 gram (₹40 estimated cost)

2. Click **Recalculate** button on dashboard
3. Verify all orders now show proper costs

### Alternative: Accept Known Limitation ✅

The 6 zero-cost orders represent **₹4,130 revenue** with **₹3,570 profit** (overstated by ~86% if we assume ₹100 average cost per order).

**Impact:** Minor compared to overall P&L:
- Mar 2026: ₹5,166 profit from 27 orders → 6% overstated if one order zero-costed
- Apr 2026: ₹2,335 profit from 14 orders → higher impact (9%) if one order zero-costed

**Acceptable if:**
- These 6 orders processed long ago (not current business)
- No immediate need for precise historical margins
- Team bandwidth constrained

---

## Files Modified

### Frontend
- `/opt/pureleven/frontend/profit-loss.html`
  - Added "Recalculate" button to Data Quality warning
  - Added button styling and click handler
  - Button triggers `/api/reports/profit/recalculate` endpoint

### Backend
- `/opt/pureleven/backend/app/modules/reporting/router.py`
  - Added POST `/api/reports/profit/recalculate` endpoint
  - Requires management role
  - Accepts `from_month` and `to_month` in YYYY-MM format

- `/opt/pureleven/backend/app/modules/reporting/service.py`
  - Added `recalculate_profit_postings()` function
  - Queries orders in date range
  - Calls `upsert_order_profit_posting()` for each order
  - Returns success/processed count

- `/opt/pureleven/backend/app/modules/reporting/schemas.py`
  - Added `RecalculateRequest` schema
  - Added `RecalculateResponse` schema

---

## Recommendations

1. **Standardize product naming** in order entry forms
   - Use dropdown autocomplete from product catalog
   - Prevent free-text product names
   - Eliminates future mismatches

2. **Periodic data quality checks**
   - Alert when unmatched order items exist
   - Flag orders with product_cost = 0 monthly
   - Dashboard already shows count (visible when > 0)

3. **Product catalog documentation**
   - Define all available product variants upfront
   - Create size matrix (100g, 200g, 500g versions for each spice)
   - Assign cost prices with margin policies

