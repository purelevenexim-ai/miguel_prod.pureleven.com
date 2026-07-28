# Partial COD Payment System — Frontend Implementation Guide

## Overview
Partial COD (Cash on Delivery) allows customers to pay a partial amount (advance) upfront and the remaining balance on delivery. This document provides complete frontend design and implementation guidance.

---

## 1. UI/UX Design — Payment Section

### Current Payment Options (From Attachment)
- ☑ COD (Cash on Delivery) — fully unpaid until delivery
- ◻ UPI
- ◻ Bank Transfer
- ◻ Cheque
- ◻ Prepaid

### New Addition: **Partial COD**
When a customer (e.g., Rani) wants to pay only ₹200 advance on a ₹2000 order:

```
PAYMENT METHOD
═════════════════════════════════════════════════════════════

🔘 COD                           📱 UPI
   "Pay full amount on delivery"    
                                🏦 Bank Transfer

☑ PARTIAL COD                   💳 Cheque
   "Pay advance now, balance on delivery"
   
   └─ Advanced Amount Input Field
      ├─ Current Input: ___________₹
      └─ Remaining (COD): Calculated automatically

📌 Prepaid
```

---

## 2. Frontend Component Structure

### File: `frontend/modules/orders/payment-section.js`

```javascript
class PartialCODPaymentController {
  
  constructor(formContext) {
    this.form = formContext;
    this.totalAmount = 0;
    this.advanceAmount = 0;
    this.codAmount = 0;
    this.selectedMethod = null;
  }

  // Initialize payment method radio buttons
  initPaymentMethods() {
    const paymentMethods = [
      { id: 'cod', label: 'COD', icon: '🚗', desc: 'Pay full amount on delivery' },
      { id: 'partial_cod', label: 'Partial COD', icon: '📦', desc: 'Pay advance now, balance on delivery' },
      { id: 'upi', label: 'UPI', icon: '📱', desc: '' },
      { id: 'bank_transfer', label: 'Bank Transfer', icon: '🏦', desc: '' },
      { id: 'cheque', label: 'Cheque', icon: '💳', desc: '' },
      { id: 'prepaid', label: 'Prepaid', icon: '✓', desc: '' }
    ];

    paymentMethods.forEach(method => {
      this.createPaymentButton(method);
    });
  }

  createPaymentButton(method) {
    const button = document.createElement('div');
    button.className = 'payment-method-btn';
    button.id = `payment-${method.id}`;
    button.innerHTML = `
      <div class="payment-method-content">
        <input type="radio" name="payment_method" value="${method.id}" />
        <label>
          <span class="payment-icon">${method.icon}</span>
          <span class="payment-label">${method.label}</span>
          ${method.desc ? `<span class="payment-desc">${method.desc}</span>` : ''}
        </label>
      </div>
    `;

    button.addEventListener('click', () => this.selectPaymentMethod(method.id));
    
    return button;
  }

  selectPaymentMethod(methodId) {
    this.selectedMethod = methodId;
    
    // Remove active state from all buttons
    document.querySelectorAll('.payment-method-btn').forEach(btn => {
      btn.classList.remove('active');
    });
    
    // Activate selected button
    document.getElementById(`payment-${methodId}`).classList.add('active');
    
    // Show/hide advance amount input based on selection
    if (methodId === 'partial_cod') {
      this.showAdvanceAmountInput();
    } else {
      this.hideAdvanceAmountInput();
      this.resetAdvanceAmount();
    }
  }

  showAdvanceAmountInput() {
    let container = document.getElementById('partial-cod-container');
    
    if (!container) {
      container = document.createElement('div');
      container.id = 'partial-cod-container';
      container.className = 'partial-cod-input-group';
      container.innerHTML = `
        <div class="input-group">
          <label for="advance_amount">
            💰 Advance Amount to Pay Now
            <span class="info-icon" title="Amount customer pays upfront before delivery">ℹ️</span>
          </label>
          <div class="input-wrapper">
            <span class="currency">₹</span>
            <input 
              type="number" 
              id="advance_amount" 
              name="advance_amount"
              placeholder="Enter advance amount"
              min="0"
              step="1"
              class="form-input"
            />
          </div>
          <div class="helper-text">
            Max amount: <strong id="max-advance">₹0</strong>
          </div>
        </div>

        <div class="payment-breakdown">
          <div class="breakdown-row">
            <span class="label">Total Amount:</span>
            <span class="value" id="total-display">₹0</span>
          </div>
          <div class="breakdown-row highlight">
            <span class="label">Advance (Paid Now):</span>
            <span class="value advance" id="advance-display">₹0</span>
          </div>
          <div class="breakdown-row highlight">
            <span class="label">Remaining (COD):</span>
            <span class="value cod" id="cod-display">₹0</span>
          </div>
          <div class="breakdown-divider"></div>
          <div class="breakdown-row summary">
            <span class="label">You will pay on delivery:</span>
            <span class="value" id="delivery-pay">₹0</span>
          </div>
        </div>
      `;

      // Insert after summary section
      const summarySection = document.querySelector('.SUMMARY');
      summarySection.parentNode.insertBefore(container, summarySection.nextSibling);

      // Attach event listeners
      const advanceInput = document.getElementById('advance_amount');
      advanceInput.addEventListener('input', (e) => this.handleAdvanceInput(e));
      advanceInput.addEventListener('change', (e) => this.validateAdvanceAmount(e));
    }

    container.style.display = 'flex';
    this.updateAdvanceAmountDisplay();
  }

  hideAdvanceAmountInput() {
    const container = document.getElementById('partial-cod-container');
    if (container) {
      container.style.display = 'none';
    }
  }

  handleAdvanceInput(event) {
    this.advanceAmount = parseFloat(event.target.value) || 0;
    this.updatePaymentBreakdown();
  }

  validateAdvanceAmount(event) {
    const input = event.target;
    const value = parseFloat(input.value) || 0;

    // Validation: advance cannot exceed total
    if (value > this.totalAmount) {
      alert(`❌ Advance amount cannot exceed total (₹${this.totalAmount})`);
      input.value = this.totalAmount;
      this.advanceAmount = this.totalAmount;
    }

    // Validation: advance cannot be negative
    if (value < 0) {
      input.value = 0;
      this.advanceAmount = 0;
    }

    // Validation: advance must be at least ₹1 for partial COD
    if (this.selectedMethod === 'partial_cod' && value === 0) {
      alert('⚠️ Please enter an advance amount or choose a different payment method');
      document.getElementById('payment-partial_cod').classList.remove('active');
      this.selectedMethod = null;
    }

    this.updatePaymentBreakdown();
  }

  updatePaymentBreakdown() {
    // Recalculate COD amount
    this.codAmount = Math.max(0, this.totalAmount - this.advanceAmount);

    // Update display
    document.getElementById('advance-display').textContent = `₹${this.advanceAmount.toFixed(2)}`;
    document.getElementById('cod-display').textContent = `₹${this.codAmount.toFixed(2)}`;
    document.getElementById('delivery-pay').textContent = `₹${this.codAmount.toFixed(2)}`;

    // Update form data
    this.form.advance_amount = this.advanceAmount;
  }

  updateAdvanceAmountDisplay() {
    // Calculate total from items summary
    const totalElement = document.querySelector('[class*="total"]');
    if (totalElement) {
      const totalText = totalElement.textContent;
      const total = parseFloat(totalText.replace(/[^0-9.]/g, ''));
      this.totalAmount = total || 0;
    }

    document.getElementById('total-display').textContent = `₹${this.totalAmount.toFixed(2)}`;
    document.getElementById('max-advance').textContent = `₹${this.totalAmount.toFixed(2)}`;
  }

  resetAdvanceAmount() {
    this.advanceAmount = 0;
    this.codAmount = 0;
    const input = document.getElementById('advance_amount');
    if (input) input.value = '';
  }

  // Get form data including partial COD fields
  getFormData() {
    return {
      payment_method: this.selectedMethod,
      advance_amount: this.selectedMethod === 'partial_cod' ? this.advanceAmount : 0,
      // ... other form fields
    };
  }

  // Validate form before submission
  validatePaymentForm() {
    if (!this.selectedMethod) {
      alert('❌ Please select a payment method');
      return false;
    }

    if (this.selectedMethod === 'partial_cod') {
      if (this.advanceAmount <= 0) {
        alert('❌ Please enter a valid advance amount');
        return false;
      }
      if (this.advanceAmount > this.totalAmount) {
        alert('❌ Advance amount cannot exceed total amount');
        return false;
      }
    }

    return true;
  }
}

// Usage in orders.html
document.addEventListener('DOMContentLoaded', () => {
  const paymentController = new PartialCODPaymentController(window.orderForm);
  paymentController.initPaymentMethods();
});
```

---

## 3. CSS Styling

### File: `frontend/styles/partial-cod.css`

```css
/* Payment Methods Container */
.payment-methods-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  margin-top: 16px;
}

/* Individual Payment Button */
.payment-method-btn {
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
  background: white;
}

.payment-method-btn:hover {
  border-color: #2196f3;
  background: #f5f9ff;
}

.payment-method-btn.active {
  border-color: #2196f3;
  background: #e3f2fd;
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.2);
}

.payment-method-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.payment-method-content input[type="radio"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.payment-method-content label {
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin: 0;
}

.payment-icon {
  font-size: 24px;
}

.payment-label {
  font-weight: 600;
  color: #333;
  font-size: 14px;
}

.payment-desc {
  font-size: 12px;
  color: #666;
  font-weight: normal;
}

/* Partial COD Input Container */
.partial-cod-input-group {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin: 24px 0;
  padding: 16px;
  background: #fffbea;
  border: 2px solid #ffc107;
  border-radius: 8px;
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.input-group label {
  font-weight: 600;
  color: #333;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.info-icon {
  cursor: help;
  font-size: 14px;
  color: #2196f3;
}

.input-wrapper {
  display: flex;
  align-items: center;
  border: 2px solid #ddd;
  border-radius: 6px;
  overflow: hidden;
  transition: border-color 0.2s;
}

.input-wrapper:focus-within {
  border-color: #2196f3;
}

.currency {
  padding: 0 12px;
  font-weight: 600;
  color: #666;
  background: #f5f5f5;
}

.form-input {
  flex: 1;
  border: none;
  padding: 12px 16px;
  font-size: 16px;
  outline: none;
}

.helper-text {
  font-size: 12px;
  color: #666;
}

#max-advance {
  color: #2196f3;
  font-weight: 600;
}

/* Payment Breakdown */
.payment-breakdown {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px;
  background: white;
  border-radius: 6px;
}

.breakdown-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  font-size: 14px;
}

.breakdown-row.highlight {
  padding: 12px;
  border-radius: 4px;
  background: #f5f5f5;
}

.breakdown-row.highlight.advance {
  background: #e8f5e9;
  border-left: 4px solid #4caf50;
}

.breakdown-row.highlight.cod {
  background: #fff3e0;
  border-left: 4px solid #ff9800;
}

.breakdown-row.summary {
  margin-top: 8px;
  padding: 12px;
  background: #e3f2fd;
  border-radius: 4px;
  font-weight: 600;
  color: #1565c0;
}

.breakdown-label {
  color: #666;
}

.breakdown-value {
  font-weight: 600;
  color: #333;
}

.breakdown-divider {
  height: 1px;
  background: #e0e0e0;
  margin: 8px 0;
}

/* Responsive */
@media (max-width: 768px) {
  .partial-cod-input-group {
    grid-template-columns: 1fr;
  }

  .payment-methods-container {
    grid-template-columns: 1fr;
  }
}

/* Desktop View - Payment Section from Attachment */
.payment-section-container {
  background: white;
  border-radius: 8px;
  padding: 20px;
  margin-top: 20px;
}

.payment-section-title {
  font-weight: 600;
  color: #333;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 2px solid #f0f0f0;
}
```

---

## 4. HTML Integration (orders.html)

Update the PAYMENT section to include Partial COD:

```html
<section class="PAYMENT">
  <h3>PAYMENT</h3>
  
  <div class="payment-tabs">
    <button class="tab-btn" data-tab="F2">F2 COD</button>
    <button class="tab-btn" data-tab="F3">F3 PREPAID</button>
  </div>

  <div class="payment-methods-container">
    <!-- Payment Method Buttons -->
    <div class="payment-method-btn active">
      <div class="payment-method-content">
        <input type="radio" name="payment_method" value="cod" checked />
        <label>
          <span class="payment-icon">🚗</span>
          <span class="payment-label">COD</span>
        </label>
      </div>
    </div>

    <!-- NEW: Partial COD -->
    <div class="payment-method-btn">
      <div class="payment-method-content">
        <input type="radio" name="payment_method" value="partial_cod" />
        <label>
          <span class="payment-icon">📦</span>
          <span class="payment-label">Partial COD</span>
          <span class="payment-desc">Advance + Balance on delivery</span>
        </label>
      </div>
    </div>

    <div class="payment-method-btn">
      <div class="payment-method-content">
        <input type="radio" name="payment_method" value="upi" />
        <label>
          <span class="payment-icon">📱</span>
          <span class="payment-label">UPI</span>
        </label>
      </div>
    </div>

    <div class="payment-method-btn">
      <div class="payment-method-content">
        <input type="radio" name="payment_method" value="bank_transfer" />
        <label>
          <span class="payment-icon">🏦</span>
          <span class="payment-label">Bank Transfer</span>
        </label>
      </div>
    </div>
  </div>

  <!-- Partial COD Input (Hidden by default) -->
  <div id="partial-cod-container" class="partial-cod-input-group" style="display: none;">
    <!-- Generated dynamically by JavaScript -->
  </div>
</section>
```

---

## 5. API Integration

### POST `/api/orders` - Create Order with Partial COD

**Request Body:**
```json
{
  "customer_name": "Rani",
  "customer_phone": "9876543210",
  "items": [
    {
      "product_name": "PureLeven Combo Pack",
      "sku": "SKU123",
      "quantity": 1,
      "unit": "piece",
      "unit_price": 2000,
      "discount_pct": 0
    }
  ],
  "payment_method": "partial_cod",
  "advance_amount": 200,
  "delivery_address": "123 Main St",
  "delivery_city": "Mumbai",
  "delivery_state": "Maharashtra",
  "delivery_pincode": "400001",
  "gst_invoice": true,
  "order_source": "manual"
}
```

**Response:**
```json
{
  "id": "uuid-here",
  "order_number": "PLX-260225-001",
  "payment_method": "partial_cod",
  "total_amount": 2000.00,
  "advance_amount": 200.00,
  "cod_amount": 1800.00,
  "amount_paid": 200.00,
  "amount_due": 1800.00,
  "payment_status": "partial",
  "status": "confirmed"
}
```

---

## 6. Order Display & Tracking

### Order Summary Page (After Creation)

```html
<div class="order-confirmation">
  <div class="order-header">
    ✅ Order Created Successfully - <strong>PLX-260225-001</strong>
  </div>

  <div class="order-details">
    <div class="detail-row">
      <span class="label">Customer:</span>
      <span class="value">Rani</span>
    </div>
    <div class="detail-row">
      <span class="label">Total Amount:</span>
      <span class="value">₹2,000.00</span>
    </div>
  </div>

  <!-- Partial COD Breakdown -->
  <div class="payment-info partial-cod-info">
    <h4>💰 Payment Breakdown</h4>
    
    <div class="breakdown-table">
      <div class="breakdown-item">
        <div class="item-label">Total Order Amount</div>
        <div class="item-value">₹2,000.00</div>
      </div>
      
      <div class="breakdown-item paid">
        <div class="item-label">✓ Advance (Already Paid)</div>
        <div class="item-value">-₹200.00</div>
      </div>
      
      <div class="breakdown-item pending">
        <div class="item-label">📦 To Pay on Delivery</div>
        <div class="item-value">₹1,800.00</div>
      </div>
    </div>

    <div class="payment-status-badge">
      <strong>Status:</strong> 
      <span class="badge partial">PARTIAL (₹200 received)</span>
    </div>

    <div class="courier-instructions">
      <p>📌 <strong>Courier Instructions:</strong></p>
      <ul>
        <li>Advance amount of ₹200 already paid - recorded in system</li>
        <li>Collect ₹1,800 from customer on delivery</li>
        <li>Total received should be ₹2,000</li>
      </ul>
    </div>
  </div>
</div>
```

---

## 7. Admin Dashboard - Partial COD Analytics

### New Metrics to Display

```javascript
// Dashboard statistics for Partial COD orders
const partialCODStats = {
  totalPartialOrders: 45,
  totalAdvanceReceived: 25000,    // Sum of all advance_amount
  totalPendingOnDelivery: 75000,  // Sum of all cod_amount
  conversionRate: "92%",          // Orders where balance was collected
  averageAdvancePercentage: "25%" // Avg advance as % of total
};

// Display in dashboard
document.getElementById('partial-cod-stat').innerHTML = `
  <div class="stat-card">
    <div class="stat-label">Partial COD Orders</div>
    <div class="stat-value">${partialCODStats.totalPartialOrders}</div>
    <div class="stat-detail">
      💰 Advance: ₹${partialCODStats.totalAdvanceReceived.toLocaleString('en-IN')}
    </div>
    <div class="stat-detail">
      📦 Pending: ₹${partialCODStats.totalPendingOnDelivery.toLocaleString('en-IN')}
    </div>
  </div>
`;
```

---

## 8. Order Management Features

### Editing Advance Amount (Draft Orders Only)

```javascript
function editAdvanceAmount(orderId) {
  const currentAdvance = getOrderField(orderId, 'advance_amount');
  const totalAmount = getOrderField(orderId, 'total_amount');

  const newAdvance = prompt(
    `Edit advance amount (current: ₹${currentAdvance}, max: ₹${totalAmount}):`,
    currentAdvance
  );

  if (newAdvance !== null) {
    if (parseFloat(newAdvance) > totalAmount) {
      alert(`❌ Cannot exceed total amount (₹${totalAmount})`);
      return;
    }

    // API call to update
    fetch(`/api/orders/${orderId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        advance_amount: parseFloat(newAdvance)
      })
    })
    .then(res => res.json())
    .then(data => {
      alert(`✅ Advance amount updated to ₹${newAdvance}`);
      refreshOrderDetails(orderId);
    });
  }
}
```

---

## 9. WhatsApp Integration

When sending order confirmation via WhatsApp for Partial COD:

```
📦 Order Confirmation - PLX-260225-001

Customer: Rani
Items: PureLeven Combo Pack 4×100g

💰 Payment Summary:
Total: ₹2,000
✓ Advance Paid: ₹200
📦 Pay on Delivery: ₹1,800

Expected Delivery: Tomorrow

Thank you! 🙏
```

---

## 10. Implementation Checklist

- [ ] Update `frontend/modules/orders/payment-section.js` with PartialCODPaymentController
- [ ] Add CSS styles to `frontend/styles/partial-cod.css`
- [ ] Update `frontend/orders.html` to include Partial COD payment button
- [ ] Integrate `payment-section.js` into orders form initialization
- [ ] Test advance amount input validation
- [ ] Test payment breakdown calculations
- [ ] Test API integration (create partial COD orders)
- [ ] Verify order confirmation display
- [ ] Test order editing/update of advance amounts
- [ ] Add Partial COD to dashboard analytics
- [ ] Test WhatsApp integration for partial COD messages
- [ ] Test responsive design on mobile
- [ ] Verify courier instructions generation
- [ ] Add admin-side controls for advance collection tracking

---

## 11. Sample Data for Testing

```javascript
const testPartialCODOrder = {
  customer_name: "Rani",
  customer_phone: "9876543210",
  items: [
    {
      product_name: "PureLeven Combo Pack 4-in-1",
      sku: "PURE-001",
      quantity: 1,
      unit: "piece",
      unit_price: 2000,
      discount_pct: 0,
      notes: "Customer prefers morning delivery"
    }
  ],
  payment_method: "partial_cod",
  advance_amount: 200,  // Customer pays only 200, remaining 1800 on delivery
  delivery_address: "123 Main Street",
  delivery_city: "Mumbai",
  delivery_state: "Maharashtra",
  delivery_pincode: "400001",
  gst_invoice: true
};
```

---

## Summary

This Partial COD payment system provides:

✅ **Backend**: New `partial_cod` payment method with advance/cod amount tracking
✅ **Frontend**: Intuitive UI for selecting payment method and entering advance amount
✅ **Validation**: Prevents invalid advance amounts (>total or negative)
✅ **Calculations**: Auto-calculates COD amount = total - advance
✅ **Order Management**: Full tracking of advance vs. pending amounts
✅ **Analytics**: Dashboard visibility into partial payment metrics
✅ **Integration**: Works seamlessly with existing COD, UPI, and prepaid flows

