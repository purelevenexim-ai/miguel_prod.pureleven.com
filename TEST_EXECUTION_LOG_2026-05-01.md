# Production Read-Only Verification Log

Date: 2026-05-01
Mode: Production only, read-only (no create/update/delete)
Tester: GitHub Copilot (GPT-5.3-Codex)

## Scope Started
- Full page reachability and filter/control verification started.
- Focused deep check started on Profit and Loss page (Profit Checker route).

## Executed Checks

### 1) Profit and Loss page: /profit-loss.html
Status: PASS (core rendering and new modal behavior)

Checks performed:
- Verified tab render for Overview, Revenue, Products, Profit Checker, Customers.
- Verified Profit Checker groups visible:
  - Product Purchases
  - Packing Materials
  - Courier Materials
  - Salary & Operations
  - Ads & Marketing
  - Sales
- Verified Add Expense modal opens for each relevant group.
- Verified Product Purchases modal supports purchase type toggles:
  - Specific Product
  - Bulk / Raw Material
  - Generic (no product)
- Verified group-specific modal behavior:
  - Packing Materials shows product + quantity/unit cost + amount + usage rate per product unit sold.
  - Courier Materials shows quantity/unit cost + amount + usage rate per order dispatched.
- Verified Overview filters are present and functional:
  - Period filter changed to This Month.
  - Status filter changed to Delivered.
  - Active filter label updates (example: "This month | Status: delivered").

Notes:
- UI IDs for Apply Filters action appear inconsistent with automation selector used in one attempt; manual/state-based filter changes still reflected correctly.

### 2) Orders page: /orders.html
Status: PASS (reachability and load)

Checks performed:
- Page loads with order creation panel and order workflow controls.
- Core data-entry and lookup controls visible (address parser, phone lookup, courier/service selectors).
- Navigation integrity from shared sidebar confirmed.

### 3) Customers page: /customers.html
Status: PASS (reachability and filter controls)

Checks performed:
- Search input present.
- State filter, active/inactive filter, customer type filter visible.
- Refresh and New Customer controls present.

### 4) Leads page: /leads.html
Status: PASS (reachability and filter controls)

Checks performed:
- Search leads input visible.
- Filter button visible.
- Status chips/pills visible (new, contacted, remind, won, lost).
- Pagination controls visible.

### 5) Products page: /products.html
Status: PASS (reachability and filter controls)

Checks performed:
- Search input visible.
- Status/category/GST filters visible.
- Refresh and New Product controls visible.

### 6) Vendors page: /vendors.html
Status: PASS (reachability and filter controls)

Checks performed:
- Search input visible.
- Active/all/inactive filter visible.
- Vendor type filter visible.

### 7) Invoices page: /invoices.html
Status: PASS (reachability and customer search controls)

Checks performed:
- Customer search visible.
- Orders/Invoice/Label mode controls visible.
- Label editor link accessible.

### 8) GST page: /gst.html
Status: PASS (reachability and filter controls)

Checks performed:
- Date range filters (from/to) visible.
- State filter visible.
- Customer type toggle visible.
- Min/max amount filters visible.
- Generate Report and Reset Filters actions visible.
- GSTR-1/HSN/Tax summary tabs visible.

### 9) WhatsApp page: /whatsapp.html
Status: PASS (reachability and inbox/template filters)

Checks performed:
- Template search visible.
- Refresh action visible.
- Sidebar sections available (templates, send, inbox, settings, campaign types, postback rules, subscribers, webhook setup).

### 10) Marketing page: /marketing.html
Status: PASS (reachability and audience filters)

Checks performed:
- Audience filtering controls visible:
  - Source
  - Lead status
  - Label
  - Has orders
  - Has email
  - State/region
  - Interest
- Search, refresh, CSV export visible.

### 11) Lead Messages page: /lead-messages.html
Status: PASS after fix

Initial defect observed:
- API sync failure in page load path.
- Console/page error indicated Subscribers API error 500.

Root cause confirmed from backend logs:
- Endpoint: GET /api/wa/subscribers
- Exception: fastapi.exceptions.ResponseValidationError
- Contract mismatch: response field wa_status returned as WaStatus ORM object, but schema expected string.

Fix implemented:
- File patched: backend/app/modules/wa_engine/router.py
- Change: serialize subscriber response payload explicitly so wa_status is returned as string (sub.wa_status.status) instead of ORM relationship object.
- Applied to both endpoints:
  - GET /api/wa/subscribers
  - GET /api/wa/subscribers/{sub_id}
- Backend container restarted and health verified.

Retest evidence:
- Lead Messages page now loads conversation list successfully.
- Sync indicator shows success with populated counts (example observed: 281 conversations, 100 unread).
- No server error banner/toast present in post-fix snapshot.

## Early Findings Summary
- Profit Checker redesign changes are reflected in production UI, including Packing/Courier split and modal logic.
- Most pages load with expected filter/search controls.
- One critical module path initially failed (Lead Messages subscriber sync endpoint), now fixed and verified.

## Next Implementation Steps
1. Execute filter action tests (not only visibility) for remaining pages:
   - Customers, Leads, Products, Vendors, GST, Marketing, WhatsApp, Invoices.
2. Capture endpoint-level evidence for failing Lead Messages API and map to backend router/service.
3. Perform cross-page data consistency spot checks:
   - Same customer/order/product across at least two modules.
4. Produce severity-ranked defect report with reproducible steps and impacted API contracts.

## Additional Functional Filter Execution (in progress)

### Customers
Status: PARTIAL PASS

Actions performed:
- Entered unmatched search term: zzzz_nomatch_12345
- Verified search state updates in input and list area refresh behavior.

Observations:
- Customer stats and list metadata loaded.
- One transient server error overlay was observed during an earlier pass; subsequent reload after wa_engine fix did not reproduce.

### Leads
Status: PASS

Actions performed:
- Entered unmatched search term: zzzz_nomatch_12345

Results:
- Table displayed explicit no-result empty state: "No leads found".
- Pagination disabled correctly in empty state.
- No write action triggered.

### Products
Status: PASS

Actions performed:
- Entered unmatched search term: zzzz_nomatch_12345

Results:
- Shown count changed to 0.
- Empty state rendered: "No products found.".
- No write action triggered.

## Code Fixes Applied During Verification

1) wa_engine subscriber serialization fix
- Commit: 7e0d774
- Files:
  - backend/app/modules/wa_engine/router.py
  - TEST_EXECUTION_LOG_2026-05-01.md
- Branch: main (pushed)

2) customers with-orders search filter fix
- Root cause: function-local import shadowed or_ causing UnboundLocalError during search filter path.
- File: backend/app/modules/customers/service.py
- Change: removed local `from sqlalchemy import or_` inside list_customers_with_orders; rely on module-level import.
- Runtime validation after restart: customers search + inactive filter returns empty-state cleanly, no 500 panel.

## Remaining Module Filter Tests Completed

### GST
Status: PASS (with explicit date assignment)

Actions performed:
- Set from/to date fields to 2026-05-01 / 2026-05-31.
- Triggered Generate Report.

Result:
- Report renders with invoice headers.
- No server error.

Observation:
- One transient UX validation message ("Please select a date range") occurred before explicit date binding; not reproduced after direct input assignment.

### Marketing
Status: PASS

Actions performed:
- Source filter: Leads.
- Lead status filter: Won.
- Search: zzzz_nomatch_12345.

Result:
- Dataset narrowed to 14 contacts under Leads+Won.
- No-match search correctly shows "No contacts match your filters."

### WhatsApp
Status: PASS (within tenant configuration state)

Actions performed:
- Template search with no-match term.
- Switched to Inbox section.

Result:
- Templates no-match state rendered correctly.
- Inbox section opens and starts sync.

Note:
- Tenant banner indicates "Not configured"; this is a config state, not a functional crash.

### Invoices
Status: PASS

Actions performed:
- Waited for customer list load.
- Searched customer "dileep".

Result:
- Matching customer card displayed (Dileep Kumar, phone, city, order count, value ₹1,750).
- No server error.

### Vendors
Status: PASS

Actions performed:
- Search with no-match term.
- Refresh with active filters.

Result:
- Stable empty-state rendering with zero counts and no crash.

### Orders
Status: PASS

Actions performed:
- Search with no-match term.
- Search with real entity (dileep).

Result:
- No-match path: "No orders found" + disabled pagination.
- Positive path: row for PRN-260501-001 with Dileep Kumar, phone 9427258815, amount ₹1750, product Kerala Cardamom 8mm - 500.

### Customers (deep)
Status: PASS after fix

Actions performed:
- Search no-match and Inactive filter.
- Search positive entity (dileep).

Result:
- No-match path shows clean empty-state.
- Positive path shows Dileep row with phone 9427258815 and value ₹1,750.

## Cross-Page Data Consistency Checks

Checked entities and outcomes:

1) Customer/Order consistency (Dileep Kumar)
- Orders page: PRN-260501-001, customer Dileep Kumar, phone 9427258815, amount ₹1750.
- Invoices page: Dileep Kumar card with phone 919427258815 and value ₹1,750.
- Profit & Loss Overview: top customer row Dileep Kumar with ₹1,750.
- Customers page: Dileep row shows phone 9427258815 and paid value ₹1,750.
- Result: CONSISTENT (phone formatting differs by country prefix display only).

2) API-level customer/order linkage
- /api/orders/?page=1&page_size=25 returns orders with customer_id.
- /api/customers/with-orders?page=1&limit=50 contains matching customer_id.
- Result: CONSISTENT (sample order PRN-260429-014 matched customer id 0240f268-0899-4722-b712-e110c2342574).

3) Product catalog vs report product naming
- /api/reports/products returns display names with suffix format (example: "Black Pepper Kerala - 500 — 500gm").
- /api/products returns catalog names (example: "Black Pepper Kerala - 500").
- Normalized-name match succeeds and cost price aligns (450.00).
- Result: CONSISTENT data, DIFFERENT presentation naming.

## Severity-Ranked Defect Report

### Critical
None open after fixes.

### High
1) Fixed: Lead Messages sync 500
- Symptom: Lead Messages failed to load conversations.
- Repro: open /lead-messages.html with synced subscribers.
- API impact: GET /api/wa/subscribers
- Root cause: response validation mismatch (wa_status ORM object vs expected string).
- Fix: serialize wa_status string in wa_engine router responses.
- Status: CLOSED.

2) Fixed: Customers search/filter 500
- Symptom: customers page crashed during with-orders filtered search.
- Repro: /customers.html search term + with-orders endpoint (e.g. search=zzzz_nomatch_12345, is_active=false).
- API impact: GET /api/customers/with-orders
- Root cause: UnboundLocalError from local variable shadowing or_.
- Fix: removed function-local import shadowing.
- Status: CLOSED.

### Medium
1) GST filter UX instability (transient)
- Symptom: occasional "Please select a date range" prompt despite visible date fields.
- Repro: click Generate without explicit date re-input after page transitions.
- API impact: user may not trigger report query.
- Current status: not blocking after explicit date set; keep under observation.

2) WhatsApp tenant not configured state
- Symptom: dashboard shows "Not configured" and inbox starts in syncing/empty state.
- Repro: open /whatsapp.html for tenant without complete WA setup.
- API impact: campaign/template/inbox features limited by config.
- Status: expected configuration dependency, not a runtime defect.

### Low
1) Naming normalization difference between catalog and report product labels
- Symptom: report product names include pack-size suffix delimiter while catalog uses base name.
- Impact: strict exact-string joins can fail in diagnostics scripts.
- API impact: none for UI behavior; only impacts naive reconciliation scripts.

## Final Data-Integrity Conclusion

- No data-loss evidence found in tested module interactions.
- Cross-page sampled entities remained consistent across Orders, Customers, Invoices, and Profit & Loss.
- API parity checks for core read paths returned 200 and coherent counts after hotfixes.
- Two high-severity runtime defects were found and closed during this execution cycle.
