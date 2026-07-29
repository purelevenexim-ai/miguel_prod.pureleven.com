# Profit & Loss System - Implementation Guide

**Status**: Ready for Development  
**Created**: February 24, 2026  
**Effort**: 16-20 hours  

---

## 📋 Quick Reference

| Component | Status | File | Time |
|-----------|--------|------|------|
| System Design | ✅ Complete | `PROFIT_LOSS_SYSTEM_DESIGN.md` | - |
| Shipping Calculators | ✅ Code Ready | `SHIPPING_CALCULATOR_IMPLEMENTATION.py` | 2 hrs |
| Profit Router | ✅ Code Ready | `PROFIT_LOSS_ROUTER_IMPLEMENTATION.py` | 3 hrs |
| Frontend Dashboard | ✅ Code Ready | `PROFIT_LOSS_FRONTEND.html` | 2 hrs |
| Database Migrations | 📝 Needed | SQL scripts | 1 hr |
| Testing & QA | 📝 Needed | Test suite | 2 hrs |

---

## Phase 1: Database Setup (1 hour)

### Step 1.1: Add Columns to Product Table

```sql
-- Run this migration
-- File: backend/alembic/versions/{timestamp}_add_product_cost_fields.py

ALTER TABLE products ADD COLUMN IF NOT EXISTS (
    actual_cost NUMERIC(12, 2) NOT NULL DEFAULT 0,
    packing_cost NUMERIC(12, 2) NOT NULL DEFAULT 0,
    tax_rate NUMERIC(5, 2) NOT NULL DEFAULT 18,
    weight_grams INTEGER DEFAULT NULL
);

CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_cost ON products(actual_cost);
```

**Action**: Run in database terminal
```bash
cd /opt/miguel/backend
alembic upgrade head
```

### Step 1.2: Add Columns to Order Table

```sql
ALTER TABLE orders ADD COLUMN IF NOT EXISTS (
    shipping_charge NUMERIC(12, 2) DEFAULT 0,
    handling_charge NUMERIC(12, 2) DEFAULT 0,
    order_profit NUMERIC(12, 2),
    profit_margin_percentage NUMERIC(5, 2),
    shipping_service VARCHAR(50),
    tracking_number VARCHAR(100)
);

CREATE INDEX idx_orders_date ON orders(created_at);
CREATE INDEX idx_orders_profit ON orders(order_profit);
```

### Step 1.3: Add Columns to OrderItem Table

```sql
ALTER TABLE order_items ADD COLUMN IF NOT EXISTS (
    unit_price_after_discount NUMERIC(12, 2),
    discount_amount NUMERIC(12, 2) DEFAULT 0,
    product_cost_at_purchase NUMERIC(12, 2),
    packing_cost_at_purchase NUMERIC(12, 2),
    line_profit NUMERIC(12, 2)
);

CREATE INDEX idx_order_items_product ON order_items(product_id);
```

### Step 1.4: Create Shipping Rate Tables

```sql
-- India Post Speed Post Tariff
CREATE TABLE shipping_rates_india_post (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_type VARCHAR(50),
    weight_min_grams INTEGER,
    weight_max_grams INTEGER,
    distance_zone VARCHAR(50),
    base_charge NUMERIC(12, 2),
    additional_charge_per_500g NUMERIC(12, 2),
    gst_rate NUMERIC(5, 2) DEFAULT 5,
    effective_from DATE,
    effective_to DATE,
    INDEX idx_india_post_lookup (service_type, weight_max_grams, distance_zone)
);

-- Delhivery Tariff
CREATE TABLE shipping_rates_delhivery (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_type VARCHAR(50),
    weight_min_kg NUMERIC(5, 2),
    weight_max_kg NUMERIC(5, 2),
    distance_zone VARCHAR(50),
    base_charge NUMERIC(12, 2),
    cod_surcharge_fixed NUMERIC(12, 2),
    cod_surcharge_percentage NUMERIC(5, 2),
    gst_rate NUMERIC(5, 2) DEFAULT 5,
    effective_from DATE,
    effective_to DATE
);

-- Pincode distance mapping
CREATE TABLE pincode_zones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    origin_pincode VARCHAR(10),
    destination_pincode VARCHAR(10),
    distance_km INTEGER,
    india_post_zone VARCHAR(50),
    delhivery_zone VARCHAR(50),
    updated_at TIMESTAMP,
    UNIQUE (origin_pincode, destination_pincode)
);
```

### Step 1.5: Create Views for Profit Aggregation

```sql
-- Daily profit summary
CREATE OR REPLACE VIEW profit_summary_daily AS
SELECT
    DATE(o.created_at) as sale_date,
    o.tenant_id,
    COUNT(DISTINCT o.id) as total_orders,
    COUNT(DISTINCT oi.product_id) as unique_products_sold,
    SUM(oi.quantity) as total_units_sold,
    SUM(oi.unit_price_after_discount * oi.quantity) as total_revenue,
    SUM((COALESCE(oi.product_cost_at_purchase, 0) + COALESCE(oi.packing_cost_at_purchase, 0)) * oi.quantity) as total_cogs,
    SUM(COALESCE(o.shipping_charge, 0)) as total_shipping,
    SUM(COALESCE(o.handling_charge, 0)) as total_handling,
    SUM(oi.unit_price_after_discount * oi.quantity) - 
        (SUM((COALESCE(oi.product_cost_at_purchase, 0) + COALESCE(oi.packing_cost_at_purchase, 0)) * oi.quantity) 
         + SUM(COALESCE(o.shipping_charge, 0)) + SUM(COALESCE(o.handling_charge, 0))) as net_profit
FROM orders o
LEFT JOIN order_items oi ON o.id = oi.order_id
WHERE o.status != 'cancelled'
GROUP BY DATE(o.created_at), o.tenant_id;
```

---

## Phase 2: Backend Implementation (3-4 hours)

### Step 2.1: Copy Shipping Calculator Code

**File**: `app/core/shipping_calculator.py`

1. Copy the entire content from `SHIPPING_CALCULATOR_IMPLEMENTATION.py`
2. Save to `backend/app/core/shipping_calculator.py`
3. Ensure proper imports

**Test it**:
```bash
cd /opt/miguel/backend
python -c "
from app.core.shipping_calculator import IndiaPostShippingCalculator
calc = IndiaPostShippingCalculator()
result = calc.calculate_speed_post(500, 2100)
print(f'Speed Post (500g, 2100km): ₹{result[\"total_charge\"]}')
"
```

Expected output: `Speed Post (500g, 2100km): ₹109.74`

### Step 2.2: Create Shipping Router

**File**: `app/modules/shipping/router.py`

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.shipping_calculator import IndiaPostShippingCalculator, DelhiveryShippingCalculator
from app.database.session import get_db

router = APIRouter(prefix="/api/shipping", tags=["shipping"])

@router.post("/calculate")
async def calculate_shipping(
    origin_pincode: str = Query(...),
    destination_pincode: str = Query(...),
    weight_grams: int = Query(...),
    service_provider: str = Query("india_post"),
    service_type: str = Query("speed_post"),
    length_cm: float = Query(None),
    width_cm: float = Query(None),
    height_cm: float = Query(None),
    cod_value: float = Query(0),
    db: Session = Depends(get_db),
):
    """Calculate shipping cost"""
    
    # Lookup distance between pincodes
    # TODO: Implement pincode distance lookup
    distance_km = 2100  # Placeholder
    
    if service_provider.lower() == "india_post":
        calc = IndiaPostShippingCalculator()
        if service_type == "speed_post":
            result = calc.calculate_speed_post(weight_grams, distance_km, cod_value)
        else:
            result = calc.calculate_parcel(weight_grams, distance_km)
    else:
        calc = DelhiveryShippingCalculator()
        volumetric = calc.calculate_volumetric_weight(length_cm or 0, width_cm or 0, height_cm or 0)
        if service_type == "surface":
            result = calc.calculate_surface(weight_grams / 1000, "D", volumetric, cod_value)
        else:
            result = calc.calculate_express(weight_grams / 1000, "D", volumetric, cod_value)
    
    return {
        "origin_pincode": origin_pincode,
        "destination_pincode": destination_pincode,
        "distance_km": distance_km,
        "result": result,
    }
```

2. Register router in `app/main.py`:

```python
from app.modules.shipping.router import router as shipping_router

app.include_router(shipping_router)
```

### Step 2.3: Copy Profit Router Code

**File**: `app/modules/profit_report/router.py`

1. Copy entire content from `PROFIT_LOSS_ROUTER_IMPLEMENTATION.py`
2. Save to `backend/app/modules/profit_report/router.py`
3. Create `__init__.py` in the folder

### Step 2.4: Register Profit Router

In `app/main.py`:

```python
from app.modules.profit_report.router import router as profit_router

# Add to router registration section
app.include_router(profit_router)
```

### Step 2.5: Test Backend APIs

```bash
# Test profit report endpoint
curl -X GET "http://localhost:8000/api/admin/profit/report?start_date=2026-02-01&end_date=2026-02-28"

# Test shipping calculator
curl -X POST "http://localhost:8000/api/shipping/calculate?origin_pincode=685561&destination_pincode=560001&weight_grams=500&service_provider=india_post&service_type=speed_post"
```

---

## Phase 3: Frontend Implementation (2-3 hours)

### Step 3.1: Create Dashboard HTML

**File**: `frontend/profit-dashboard.html`

1. Copy the entire HTML from `PROFIT_LOSS_FRONTEND.html`
2. Save to `frontend/profit-dashboard.html`
3. Update the link in main navigation

### Step 3.2: Add Navigation Menu Item

In your main `frontend/index.html` or navigation component:

```html
<a href="profit-dashboard.html" class="nav-item">
    📊 Profit & Loss
</a>
```

### Step 3.3: Verify CSS & JavaScript

The dashboard uses:
- **CSS**: Inline styles + `ds.css` Material Design system
- **JS Libraries**: Chart.js for visualizations
- **No dependencies**: Uses vanilla JS, fetch API

No additional packages needed!

### Step 3.4: Test Frontend

1. Start backend: `cd backend && python -m uvicorn app.main:app --reload`
2. Open browser: `http://localhost:8000/frontend/profit-dashboard.html`
3. Test date filters and views

---

## Phase 4: Sample Data & Testing (2 hours)

### Step 4.1: Populate Sample Shipping Rates

```sql
-- Insert India Post rates
INSERT INTO shipping_rates_india_post (service_type, weight_min_grams, weight_max_grams, distance_zone, base_charge, additional_charge_per_500g, gst_rate, effective_from)
VALUES
    ('speed_post', 0, 50, '<=200km', 47, 0, 5, '2025-10-01'),
    ('speed_post', 51, 250, '<=200km', 59, 0, 5, '2025-10-01'),
    ('speed_post', 251, 500, '<=200km', 70, 0, 5, '2025-10-01'),
    ('speed_post', 0, 50, '>2000km', 47, 0, 5, '2025-10-01'),
    ('speed_post', 51, 250, '>2000km', 77, 10, 5, '2025-10-01'),
    ('speed_post', 251, 500, '>2000km', 93, 10, 5, '2025-10-01');

-- Insert Delhivery rates
INSERT INTO shipping_rates_delhivery (service_type, weight_min_kg, weight_max_kg, distance_zone, base_charge, cod_surcharge_fixed, cod_surcharge_percentage, gst_rate, effective_from)
VALUES
    ('surface', 0, 0.5, 'D', 125, 40, 0.02, 5, '2025-10-01'),
    ('surface', 0.5, 1, 'D', 250, 40, 0.02, 5, '2025-10-01'),
    ('express', 0, 0.5, 'D', 200, 40, 0.02, 5, '2025-10-01'),
    ('express', 0.5, 1, 'D', 400, 40, 0.02, 5, '2025-10-01');
```

### Step 4.2: Update Sample Orders

```sql
-- Add cost data to sample orders (if they don't exist)
UPDATE order_items
SET 
    unit_price_after_discount = unit_price * 0.9,
    product_cost_at_purchase = unit_price * 0.4,
    packing_cost_at_purchase = unit_price * 0.05,
    line_profit = (unit_price * 0.9 - unit_price * 0.4 - unit_price * 0.05) * quantity
WHERE product_cost_at_purchase IS NULL;

UPDATE orders
SET 
    shipping_charge = 50,
    handling_charge = 25,
    order_profit = (SELECT COALESCE(SUM(line_profit), 0) FROM order_items WHERE order_id = orders.id) - 50 - 25
WHERE shipping_charge IS NULL;
```

### Step 4.3: Run Tests

Create test file: `tests/test_profit_system.py`

```python
import pytest
from app.core.shipping_calculator import IndiaPostShippingCalculator, DelhiveryShippingCalculator

def test_india_post_speed_post():
    calc = IndiaPostShippingCalculator()
    result = calc.calculate_speed_post(500, 2100)
    assert result['service'] == 'india_post_speed_post'
    assert result['total_charge'] > 0
    assert result['estimated_delivery_days'] > 0

def test_delhivery_surface():
    calc = DelhiveryShippingCalculator()
    result = calc.calculate_surface(0.5, 'D')
    assert result['service'] == 'delhivery_surface'
    assert result['total_charge'] > 0

def test_volumetric_weight():
    calc = DelhiveryShippingCalculator()
    volweight = calc.calculate_volumetric_weight(10, 10, 10)
    assert volweight == 0.02  # (10*10*10)/5000
```

Run tests:
```bash
cd /opt/miguel/backend
pytest tests/test_profit_system.py -v
```

---

## Phase 5: Integration & Deployment (2-3 hours)

### Step 5.1: Verify All Integrations

Checklist:
- [ ] Database migrations applied
- [ ] Shipping calculator working
- [ ] Profit router endpoints responding
- [ ] Frontend dashboard loads
- [ ] Charts render correctly
- [ ] Filters apply correctly
- [ ] Export functionality works

### Step 5.2: Performance Optimization

Add database indexes:

```sql
CREATE INDEX idx_order_items_order_product ON order_items(order_id, product_id);
CREATE INDEX idx_orders_customer_date ON orders(customer_id, created_at);
CREATE INDEX idx_profit_summary_date ON profit_summary_daily(sale_date DESC);
```

### Step 5.3: Caching Strategy

Add Redis caching for frequently accessed data:

```python
# In profit router
from app.core.cache import cache

@router.get("/dashboard-cards")
@cache.cached(timeout=3600)  # 1 hour
async def get_dashboard_summary_cards(...):
    # Implementation
```

### Step 5.4: Documentation

Create user guide: `docs/PROFIT_DASHBOARD_USER_GUIDE.md`

```markdown
# Profit & Loss Dashboard - User Guide

## Accessing the Dashboard
1. Login to admin panel
2. Click "Profit & Loss" in sidebar
3. Dashboard loads with current month data

## Interpreting the Cards
- **Total Sales**: All revenue from completed orders
- **Total Cost**: COGS + Packing + Shipping
- **Net Profit**: Revenue - Costs
- **Profit Margin**: (Profit/Revenue) × 100%

## Finding Unprofitable Orders
1. Sort orders table by Profit (ascending)
2. Red negative values = losses
3. Click to investigate

## Top Products Analysis
- Green = profitable products
- Red = loss-making products
- Consider discontinuing red products
```

---

## Deployment Checklist

- [ ] All database migrations applied
- [ ] Environment variables set (API keys, etc.)
- [ ] Shipping calculator tested with real pincodes
- [ ] Backend APIs tested with Postman
- [ ] Frontend dashboard responsive on mobile
- [ ] Performance tested with 1000+ orders
- [ ] Error handling tested
- [ ] Documentation updated
- [ ] Team trained on new features
- [ ] Monitoring set up for API performance

---

## Troubleshooting

### Issue: Shipping calculation returns 0

**Solution**: Check pincode distance lookup is working

```bash
SELECT * FROM pincode_zones WHERE origin_pincode='685561' AND destination_pincode='560001';
```

If empty, add mapping:

```sql
INSERT INTO pincode_zones (origin_pincode, destination_pincode, distance_km, india_post_zone, delhivery_zone)
VALUES ('685561', '560001', 2100, '>2000km', 'D');
```

### Issue: Frontend charts not rendering

**Solution**: Check Chart.js is loaded

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
```

### Issue: API returns 403 Forbidden

**Solution**: User must be admin role

```sql
UPDATE employees SET role='admin' WHERE id='...';
```

---

## Next Steps After Implementation

1. **Monitor dashboard** for first week of real data
2. **Gather feedback** from business users
3. **Optimize** frequently accessed queries
4. **Add** more granular filters (by salesperson, region, etc.)
5. **Implement** automated alerts for loss-making products
6. **Create** reports export for board meetings

---

**Total Implementation Time**: 16-20 hours  
**Complexity**: Medium  
**Risk**: Low (isolated feature, no existing code changes needed)

Good luck! 🚀
