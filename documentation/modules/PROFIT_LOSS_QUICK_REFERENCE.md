# Profit & Loss System - Quick Reference Card

**Print this page or save as reference while implementing**

---

## 📚 Where to Find What

| Need | File | Location |
|------|------|----------|
| **Overview** | PROFIT_LOSS_EXECUTIVE_SUMMARY.md | `/documentation/reviews/` |
| **Full Design** | PROFIT_LOSS_SYSTEM_DESIGN.md | `/documentation/modules/` |
| **Implementation Steps** | PROFIT_LOSS_IMPLEMENTATION_GUIDE.md | `/documentation/modules/` |
| **Shipping Code** | SHIPPING_CALCULATOR_IMPLEMENTATION.py | `/documentation/modules/` |
| **Backend Code** | PROFIT_LOSS_ROUTER_IMPLEMENTATION.py | `/documentation/modules/` |
| **Frontend Code** | PROFIT_LOSS_FRONTEND.html | `/documentation/modules/` |

---

## 🗂️ Database Schema at a Glance

### Products Table (Add 4 columns)
```sql
actual_cost NUMERIC(12,2)          -- COGS
packing_cost NUMERIC(12,2)         -- per unit
tax_rate NUMERIC(5,2)              -- GST %
weight_grams INTEGER               -- for volumetric
```

### Orders Table (Add 6 columns)
```sql
shipping_charge NUMERIC(12,2)      -- from carrier
handling_charge NUMERIC(12,2)      -- packing/fulfillment
order_profit NUMERIC(12,2)         -- calculated
profit_margin_percentage NUMERIC   -- (profit/revenue)%
shipping_service VARCHAR(50)       -- 'India Post', 'Delhivery'
tracking_number VARCHAR(100)       -- for tracking
```

### OrderItems Table (Add 4 columns)
```sql
unit_price_after_discount NUMERIC  -- selling price
product_cost_at_purchase NUMERIC   -- COGS snapshot
packing_cost_at_purchase NUMERIC   -- packing snapshot
line_profit NUMERIC(12,2)          -- (qty × cost)
```

### New Tables (4)
- `shipping_rates_india_post` — Speed Post & Parcel rates
- `shipping_rates_delhivery` — Surface & Express rates
- `pincode_zones` — Distance mapping
- Views: `profit_summary_daily`, `product_profitability`, `customer_profitability`

---

## 🚀 Implementation Checklist

### Pre-Implementation (Prep)
- [ ] Read PROFIT_LOSS_EXECUTIVE_SUMMARY.md (10 min)
- [ ] Review PROFIT_LOSS_SYSTEM_DESIGN.md (30 min)
- [ ] Backup database

### Phase 1: Database (1 hour)
- [ ] Run product table migration
- [ ] Run orders table migration
- [ ] Run order_items table migration
- [ ] Create shipping rate tables
- [ ] Create profit views
- [ ] Add indexes
- [ ] Verify with SELECT queries

### Phase 2: Backend (3-4 hours)
- [ ] Copy shipping_calculator.py → app/core/
- [ ] Test shipping calculator (python -c "...")
- [ ] Create profit_report router
- [ ] Register routers in app/main.py
- [ ] Test APIs with curl
- [ ] Add error handling

### Phase 3: Frontend (2-3 hours)
- [ ] Copy profit-dashboard.html → frontend/
- [ ] Add menu item to navigation
- [ ] Test dashboard loads
- [ ] Test filters work
- [ ] Verify charts render
- [ ] Test on mobile

### Phase 4: Testing (2 hours)
- [ ] Insert sample data
- [ ] Run test suite
- [ ] Verify calculations manually
- [ ] Load test with multiple users
- [ ] Check browser console for errors

### Phase 5: Deploy (1-2 hours)
- [ ] Code review
- [ ] Backup production DB
- [ ] Run migrations
- [ ] Deploy code
- [ ] Test in production
- [ ] Monitor logs
- [ ] Announce to users

---

## 🔢 Profit Formula Quick Reference

### Simple Version
```
Profit = Revenue - Costs

Where:
- Revenue = Price after discount × Quantity
- Costs = (COGS + Packing) × Quantity + Shipping + Handling
```

### Full Version (Per Order)
```
OrderProfit = Σ(unit_price × qty) - (Σ((cost + packing) × qty) + shipping + handling)

OrderMargin% = (OrderProfit / OrderRevenue) × 100
```

### Examples

**Order 1: Profitable**
```
2 × Black Pepper @ ₹350 = ₹700 revenue
2 × (₹180 cost + ₹20 packing) = ₹400 item cost
Shipping = ₹50, Handling = ₹25
─────────
Profit = ₹700 - ₹400 - ₹50 - ₹25 = ₹225 ✓
```

**Order 2: Loss-Making**
```
3 × Cloves (bulk) @ ₹400 = ₹1200 revenue
3 × (₹300 cost + ₹50 packing) = ₹1050 item cost
Shipping = ₹150, Handling = ₹50
─────────
Profit = ₹1200 - ₹1050 - ₹150 - ₹50 = -₹50 ✗
```

---

## 📡 API Endpoints Reference

### Get Profit Report
```bash
GET /api/admin/profit/report?start_date=2026-02-01&end_date=2026-02-28
```
Returns: Summary + daily breakdown

### Get Orders Profit
```bash
GET /api/admin/profit/orders?start_date=2026-02-01&end_date=2026-02-28&limit=50
```
Returns: List of orders with profit breakdown

### Get Products Profit
```bash
GET /api/admin/profit/products?start_date=2026-02-01&end_date=2026-02-28
```
Returns: Product profitability ranking

### Get Customer Profit
```bash
GET /api/admin/profit/customers?start_date=2026-02-01&end_date=2026-02-28
```
Returns: Customer lifetime value

### Get Dashboard Cards
```bash
GET /api/admin/profit/dashboard-cards?period=month
```
Returns: Summary cards (revenue, cost, profit, margin)

---

## 🚚 Shipping Calculator Usage

### India Post Speed Post
```python
from app.core.shipping_calculator import IndiaPostShippingCalculator

calc = IndiaPostShippingCalculator()
result = calc.calculate_speed_post(
    weight_grams=500,
    distance_km=2100,
    cod_value=0,
    otp_delivery=False
)
print(f"Cost: ₹{result['total_charge']}")
print(f"Delivery: {result['estimated_delivery_days']} days")
```

**Output**:
```
Cost: ₹109.74
Delivery: 7 days
```

### Delhivery Surface
```python
from app.core.shipping_calculator import DelhiveryShippingCalculator

calc = DelhiveryShippingCalculator()
volumetric = calc.calculate_volumetric_weight(10, 10, 10)  # 0.02 kg
result = calc.calculate_surface(
    actual_weight_kg=0.5,
    distance_zone='D',
    volumetric_weight_kg=volumetric,
    cod_value=2000
)
print(f"Cost: ₹{result['total_charge']}")
```

**Output**:
```
Cost: ₹173.25
```

---

## 💾 Sample SQL Queries

### Insert Product Cost Data
```sql
UPDATE products SET actual_cost = 100, packing_cost = 10, tax_rate = 18
WHERE id = '...';
```

### Query Top Profitable Products
```sql
SELECT product_id, SUM(quantity) as units, 
       SUM(unit_price_after_discount * quantity) as revenue,
       SUM(line_profit) as profit
FROM order_items
WHERE order_id IN (SELECT id FROM orders WHERE status='completed')
GROUP BY product_id
ORDER BY profit DESC
LIMIT 10;
```

### Find Loss-Making Orders
```sql
SELECT o.id, o.order_number, o.created_at, 
       SUM(oi.line_profit) - o.shipping_charge - o.handling_charge as net_profit
FROM orders o
LEFT JOIN order_items oi ON o.id = oi.order_id
WHERE o.status = 'completed'
GROUP BY o.id
HAVING SUM(oi.line_profit) - o.shipping_charge - o.handling_charge < 0;
```

### Insert Shipping Rates
```sql
INSERT INTO shipping_rates_india_post 
(service_type, weight_min_grams, weight_max_grams, distance_zone, base_charge, gst_rate, effective_from)
VALUES ('speed_post', 0, 50, '<=200km', 47, 5, '2025-10-01');
```

---

## 🐛 Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| Shipping charge shows 0 | Distance not found | Add pincode mapping to `pincode_zones` |
| API returns 403 | Not admin | Update user role to 'admin' |
| Charts not rendering | Chart.js not loaded | Check CDN link in HTML |
| Profit = 0 | Cost columns NULL | Update order_items with cost data |
| Frontend not loading | Path wrong | Check href matches file location |
| Database migration fails | Table exists | Check if column already exists |

---

## 📞 Key Contacts & Resources

### India Post Shipping
- Website: indiapost.gov.in
- Rate Card: Updated quarterly
- Documentation: Full tariff details with examples

### Delhivery Shipping
- Website: delhivery.com
- Rate Card: Dynamic pricing by zone
- Documentation: Weight & distance based

### Chart.js Documentation
- CDN: https://cdn.jsdelivr.net/npm/chart.js
- Docs: https://www.chartjs.org/docs/latest/

---

## ⏱️ Time Estimates

| Task | Time | Effort |
|------|------|--------|
| Read documentation | 45 min | Easy |
| Database setup | 1 hour | Easy |
| Backend implementation | 3-4 hours | Medium |
| Frontend implementation | 2-3 hours | Easy |
| Testing & debugging | 2 hours | Medium |
| Deployment | 1-2 hours | Medium |
| **Total** | **10-13 hours** | **Manageable** |

---

## ✅ Success Criteria

After implementation, you should have:

- [ ] Dashboard loads without errors
- [ ] Summary cards show correct values
- [ ] Charts display profit trends
- [ ] Orders table is sortable
- [ ] Date filters work
- [ ] Unprofitable orders highlighted in red
- [ ] API response time < 500ms
- [ ] Mobile view responsive
- [ ] No JavaScript errors in console
- [ ] Can export data (future feature)

---

## 🎓 Learning Resources

**In Documentation**:
- PROFIT_LOSS_SYSTEM_DESIGN.md — Deep dive
- PROFIT_LOSS_IMPLEMENTATION_GUIDE.md — Step-by-step
- PROFIT_LOSS_EXECUTIVE_SUMMARY.md — Business overview

**External Resources**:
- India Post tariff handbook
- Delhivery documentation
- Chart.js tutorials
- FastAPI tutorial
- SQLAlchemy documentation

---

**Print Date**: February 24, 2026  
**Last Updated**: February 24, 2026  
**Version**: 1.0  
**Status**: Ready for Implementation ✅
