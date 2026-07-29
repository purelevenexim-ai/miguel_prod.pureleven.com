# Partial COD Frontend Integration — Quick Start Guide

## 📋 Quick Reference for Frontend Developers

### What is Partial COD?
Partial COD allows customers to pay part of the order upfront and the rest on delivery.

**Example:**
- Order Total: ₹2,000
- Customer pays now: ₹200 (advance)
- Customer pays on delivery: ₹1,800 (COD)

---

## 🚀 Implementation Steps

### Step 1: Copy Files to Project

```bash
# Copy JavaScript controller
cp frontend/modules/orders/partial-cod-controller.js \
   /path/to/your/project/frontend/modules/orders/

# Copy CSS styles
cp frontend/styles/partial-cod.css \
   /path/to/your/project/frontend/styles/
```

### Step 2: Update orders.html

Add to the `<head>`:
```html
<link rel="stylesheet" href="styles/partial-cod.css">
```

Add to the `<body>` where payment methods are defined:
```html
<section class="PAYMENT" data-init-partial-cod>
  <h3>PAYMENT</h3>
  
  <!-- Container will be populated by JavaScript -->
  <div class="payment-methods-container"></div>
  
  <!-- Partial COD input (shown when selected) -->
  <div id="partial-cod-container"></div>
</section>
```

Add before closing `</body>`:
```html
<script src="modules/orders/partial-cod-controller.js"></script>

<script>
  document.addEventListener('DOMContentLoaded', () => {
    if (document.querySelector('[data-init-partial-cod]')) {
      const paymentController = new PartialCODPaymentController(window.orderForm || {});
      paymentController.initPaymentMethods();
      paymentController.watchTotalAmountChanges();
    }
  });
</script>
```

---

## 📦 File Structure

```
frontend/
├── modules/
│   └── orders/
│       └── partial-cod-controller.js (8 KB)
├── styles/
│   └── partial-cod.css (12 KB)
└── orders.html (updated)
```

---

## 🎨 UI Components

### Payment Method Buttons
Automatically created by `PartialCODPaymentController`:
- 🚗 COD
- 📦 **Partial COD** (NEW)
- 📱 UPI
- 🏦 Bank Transfer
- 💳 Cheque
- ✓ Prepaid

### Advance Amount Input Panel
Shows when "Partial COD" is selected:
- Input field for advance amount
- Real-time breakdown calculation
- Validation (cannot exceed total)
- Visual summary

---

## 💻 API Integration

### Order Creation with Partial COD

**JavaScript Example:**
```javascript
const orderData = {
  customer_name: "Rani",
  customer_phone: "9876543210",
  payment_method: "partial_cod",
  advance_amount: 200,  // ← NEW FIELD
  items: [
    {
      product_name: "PureLeven Combo Pack",
      quantity: 1,
      unit_price: 2000,
      discount_pct: 0
    }
  ],
  delivery_city: "Mumbai",
  delivery_state: "Maharashtra"
};

fetch('/api/orders', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(orderData)
})
.then(res => res.json())
.then(order => {
  console.log('Order created:', {
    orderNumber: order.order_number,
    total: order.total_amount,
    advance: order.advance_amount,
    cod: order.cod_amount,
    status: order.payment_status
  });
});
```

### Response Structure
```javascript
{
  id: "uuid-...",
  order_number: "PLX-260225-001",
  payment_method: "partial_cod",
  payment_status: "partial",
  total_amount: 2000.00,
  advance_amount: 200.00,      // ← NEW
  cod_amount: 1800.00,          // ← NEW
  amount_paid: 200.00,
  amount_due: 1800.00
}
```

---

## 🔧 Usage Examples

### Initialize Controller
```javascript
const controller = new PartialCODPaymentController(formContext);
controller.initPaymentMethods();
controller.watchTotalAmountChanges();
```

### Get Payment Data
```javascript
const paymentData = controller.getFormData();
// Returns: { payment_method: "partial_cod", advance_amount: 200 }
```

### Validate Before Submit
```javascript
if (controller.validatePaymentForm()) {
  submitOrder();
}
```

### Listen to Payment Method Changes
```javascript
document.addEventListener('payment-method-changed', (event) => {
  console.log('Selected method:', event.detail.method);
  console.log('Advance:', event.detail.advance_amount);
});
```

---

## 🎯 Payment Breakdown Calculation

**Formula:**
```
cod_amount = total_amount - advance_amount
```

**Example:**
```
Total Amount:        ₹2,000.00
Advance (Now):      -₹  200.00
────────────────────────────────
Pay on Delivery:     ₹1,800.00
```

**Display:**
- Green highlight: Advance (✓ Paid)
- Orange highlight: COD (📦 Pending)
- Blue summary: Total due on delivery

---

## ✅ Validation Rules

| Rule | Condition | Error |
|------|-----------|-------|
| Required | advance_amount > 0 | "Please enter an advance amount" |
| Maximum | advance_amount ≤ total_amount | "Cannot exceed total" |
| Type | Must be numeric | Auto-filtered |
| Sign | Must be positive | Auto-corrected to 0 |

---

## 🎨 Customization

### Change Payment Method Icons

Edit `partial-cod-controller.js`:
```javascript
this.paymentMethods = [
  { 
    id: 'partial_cod', 
    label: 'Partial COD', 
    icon: '📦',  // ← Change emoji here
    desc: 'Pay advance now, balance on delivery' 
  },
  // ...
];
```

### Customize Colors

Edit `partial-cod.css`:
```css
/* Change primary color from blue to your brand color */
.payment-method-btn:hover {
  border-color: #YOUR_COLOR;  /* Change this */
}

.payment-method-btn.active {
  border-color: #YOUR_COLOR;  /* Change this */
}
```

### Adjust Currency Symbol

Edit `partial-cod-controller.js`:
```javascript
// Search for this line (around line 200)
<span class="currency">₹</span>  // ← Change ₹ to your currency
```

---

## 📱 Mobile Responsive

The design automatically adapts:
- **Desktop (1024px+):** 2-column layout (input + breakdown side-by-side)
- **Tablet (768px):** 1-column stacked layout
- **Mobile (480px):** Full-width, optimized touch targets

No extra code needed!

---

## 🐛 Troubleshooting

### Issue: "Partial COD button not showing"
**Solution:** Check console for JavaScript errors
```javascript
console.log('Controller:', window.paymentController);
console.log('Methods:', document.querySelectorAll('.payment-method-btn'));
```

### Issue: "Advance input always shows/hides"
**Solution:** Check CSS display property isn't overridden
```css
/* Make sure this isn't being overridden */
#partial-cod-container { display: none; }  /* Default hidden */
```

### Issue: "Breakdown not calculating correctly"
**Solution:** Verify total amount is detected
```javascript
const controller = window.paymentController;
console.log('Detected total:', controller.totalAmount);
console.log('Advance:', controller.advanceAmount);
console.log('COD:', controller.codAmount);
```

### Issue: "Form submission fails"
**Solution:** Check advance_amount field exists in form
```javascript
const field = document.querySelector('input[name="advance_amount"]');
console.log('Field exists:', !!field);
console.log('Value:', field?.value);
```

---

## 📊 Analytics Integration

Track Partial COD usage:
```javascript
// Send to analytics
window.analytics?.track('order_created', {
  payment_method: 'partial_cod',
  advance_amount: 200,
  cod_amount: 1800,
  total_amount: 2000,
  advance_percentage: (200 / 2000) * 100  // 10%
});
```

---

## 🔐 Security Checklist

✅ **Server validates advance_amount** (don't trust frontend)  
✅ **No hardcoded payment amounts** in JavaScript  
✅ **HTTPS only** for payment data transmission  
✅ **No storing sensitive data** in localStorage  
✅ **CSRF token** included with form submission  
✅ **Rate limiting** on /api/orders endpoint  

---

## 📚 Related Documentation

- **Full Implementation Guide:** `PARTIAL_COD_IMPLEMENTATION_GUIDE.md`
- **System Summary:** `PARTIAL_COD_SYSTEM_SUMMARY.md`
- **Backend API Docs:** Check `/api/orders` endpoint docs
- **Database Schema:** Refer to migration `v9w0x1y2z3a5`

---

## ✨ Support

For issues or feature requests:
1. Check troubleshooting section above
2. Review browser console for errors
3. Check network tab for API failures
4. Refer to full implementation guide
5. Contact backend team for API issues

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial release |

---

**Status:** ✅ Production Ready  
**Last Updated:** February 25, 2026  
**Tested:** All browsers (Chrome, Firefox, Safari, Edge)
