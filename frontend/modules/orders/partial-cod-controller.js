/**
 * Partial COD Payment Controller
 * Manages the Partial COD (Cash on Delivery) payment flow
 * Allows customers to pay an advance amount upfront and balance on delivery
 */

class PartialCODPaymentController {
  
  constructor(formContext = {}) {
    this.form = formContext;
    this.totalAmount = 0;
    this.advanceAmount = 0;
    this.codAmount = 0;
    this.selectedMethod = 'cod'; // Default to COD
    this.paymentMethods = [
      { 
        id: 'cod', 
        label: 'COD', 
        icon: '🚗', 
        desc: 'Pay full amount on delivery' 
      },
      { 
        id: 'partial_cod', 
        label: 'Partial COD', 
        icon: '📦', 
        desc: 'Pay advance now, balance on delivery' 
      },
      { 
        id: 'upi', 
        label: 'UPI', 
        icon: '📱', 
        desc: 'Instant online payment' 
      },
      { 
        id: 'bank_transfer', 
        label: 'Bank Transfer', 
        icon: '🏦', 
        desc: 'Direct bank transfer' 
      },
      { 
        id: 'cheque', 
        label: 'Cheque', 
        icon: '💳', 
        desc: 'Cheque payment' 
      },
      { 
        id: 'prepaid', 
        label: 'Prepaid', 
        icon: '✓', 
        desc: 'Full prepayment' 
      }
    ];
  }

  /**
   * Initialize payment method radio buttons
   */
  initPaymentMethods() {
    const container = document.querySelector('.payment-methods-container') 
      || this.createPaymentMethodsContainer();

    this.paymentMethods.forEach(method => {
      const button = this.createPaymentButton(method);
      container.appendChild(button);
    });
  }

  /**
   * Create the payment methods container if it doesn't exist
   */
  createPaymentMethodsContainer() {
    const container = document.createElement('div');
    container.className = 'payment-methods-container';
    
    // Insert after PAYMENT section header
    const paymentSection = document.querySelector('.PAYMENT') 
      || document.querySelector('[class*="payment"]');
    if (paymentSection) {
      paymentSection.appendChild(container);
    }
    
    return container;
  }

  /**
   * Create an individual payment method button
   */
  createPaymentButton(method) {
    const button = document.createElement('div');
    button.className = 'payment-method-btn' + (method.id === this.selectedMethod ? ' active' : '');
    button.id = `payment-${method.id}`;
    button.setAttribute('data-method', method.id);

    button.innerHTML = `
      <div class="payment-method-content">
        <input 
          type="radio" 
          name="payment_method" 
          value="${method.id}"
          ${method.id === this.selectedMethod ? 'checked' : ''}
        />
        <label>
          <span class="payment-icon">${method.icon}</span>
          <span class="payment-label">${method.label}</span>
          ${method.desc ? `<span class="payment-desc">${method.desc}</span>` : ''}
        </label>
      </div>
    `;

    button.addEventListener('click', (e) => {
      e.preventDefault();
      this.selectPaymentMethod(method.id);
    });

    return button;
  }

  /**
   * Handle payment method selection
   */
  selectPaymentMethod(methodId) {
    this.selectedMethod = methodId;
    
    // Update radio button
    const radio = document.querySelector(`input[value="${methodId}"]`);
    if (radio) {
      radio.checked = true;
    }
    
    // Remove active state from all buttons
    document.querySelectorAll('.payment-method-btn').forEach(btn => {
      btn.classList.remove('active');
    });
    
    // Activate selected button
    const activeBtn = document.getElementById(`payment-${methodId}`);
    if (activeBtn) {
      activeBtn.classList.add('active');
    }
    
    // Show/hide advance amount input based on selection
    if (methodId === 'partial_cod') {
      this.showAdvanceAmountInput();
    } else {
      this.hideAdvanceAmountInput();
      this.resetAdvanceAmount();
    }

    // Update form data
    this.updateFormData();
  }

  /**
   * Show the advance amount input field for Partial COD
   */
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
              autocomplete="off"
            />
          </div>
          <div class="helper-text">
            Max: <strong id="max-advance">₹0</strong> 
            | Min: <strong>₹1</strong>
          </div>
        </div>

        <div class="payment-breakdown">
          <div class="breakdown-row">
            <span class="label">Total Amount:</span>
            <span class="value" id="total-display">₹0.00</span>
          </div>
          <div class="breakdown-row highlight advance">
            <span class="label">✓ Advance (Paid Now):</span>
            <span class="value advance" id="advance-display">₹0.00</span>
          </div>
          <div class="breakdown-row highlight cod">
            <span class="label">📦 Remaining (COD):</span>
            <span class="value cod" id="cod-display">₹0.00</span>
          </div>
          <div class="breakdown-divider"></div>
          <div class="breakdown-row summary">
            <span class="label">Pay on delivery:</span>
            <span class="value" id="delivery-pay">₹0.00</span>
          </div>
        </div>
      `;

      // Insert after SUMMARY section
      const summarySection = document.querySelector('.SUMMARY') 
        || document.querySelector('[class*="summary"]');
      
      if (summarySection) {
        summarySection.parentNode.insertBefore(container, summarySection.nextSibling);
      } else {
        // Fallback: insert after payment methods container
        const paymentContainer = document.querySelector('.payment-methods-container');
        if (paymentContainer) {
          paymentContainer.parentNode.insertBefore(container, paymentContainer.nextSibling);
        }
      }

      // Attach event listeners
      const advanceInput = document.getElementById('advance_amount');
      advanceInput.addEventListener('input', (e) => this.handleAdvanceInput(e));
      advanceInput.addEventListener('blur', (e) => this.validateAdvanceAmount(e));
    }

    container.style.display = 'grid';
    this.updateAdvanceAmountDisplay();
  }

  /**
   * Hide the advance amount input field
   */
  hideAdvanceAmountInput() {
    const container = document.getElementById('partial-cod-container');
    if (container) {
      container.style.display = 'none';
    }
  }

  /**
   * Handle real-time input in advance amount field
   */
  handleAdvanceInput(event) {
    const value = event.target.value;
    this.advanceAmount = parseFloat(value) || 0;
    this.updatePaymentBreakdown();
  }

  /**
   * Validate advance amount on blur
   */
  validateAdvanceAmount(event) {
    const input = event.target;
    let value = parseFloat(input.value) || 0;

    // Validation: advance cannot exceed total
    if (value > this.totalAmount) {
      console.warn(`Advance (₹${value}) exceeds total (₹${this.totalAmount})`);
      input.value = this.totalAmount.toFixed(2);
      this.advanceAmount = this.totalAmount;
      this.showNotification('warning', `❌ Advance amount capped at total (₹${this.totalAmount.toFixed(2)})`);
    }

    // Validation: advance cannot be negative
    if (value < 0) {
      input.value = 0;
      this.advanceAmount = 0;
    }

    // Validation: advance must be at least ₹1 for partial COD to make sense
    if (this.selectedMethod === 'partial_cod' && value === 0) {
      this.showNotification('error', '⚠️ Please enter an advance amount or choose a different payment method');
      this.deselectPartialCOD();
      return false;
    }

    this.updatePaymentBreakdown();
    return true;
  }

  /**
   * Deselect Partial COD if validation fails
   */
  deselectPartialCOD() {
    const codBtn = document.getElementById('payment-cod');
    if (codBtn) {
      this.selectPaymentMethod('cod');
    }
  }

  /**
   * Update the payment breakdown display
   */
  updatePaymentBreakdown() {
    // Recalculate COD amount
    this.codAmount = Math.max(0, this.totalAmount - this.advanceAmount);

    // Update display elements
    const advanceDisplay = document.getElementById('advance-display');
    const codDisplay = document.getElementById('cod-display');
    const deliveryPay = document.getElementById('delivery-pay');

    if (advanceDisplay) {
      advanceDisplay.textContent = `₹${this.advanceAmount.toFixed(2)}`;
    }
    if (codDisplay) {
      codDisplay.textContent = `₹${this.codAmount.toFixed(2)}`;
    }
    if (deliveryPay) {
      deliveryPay.textContent = `₹${this.codAmount.toFixed(2)}`;
    }

    // Update form data
    this.updateFormData();
  }

  /**
   * Update the display with current total amount
   */
  updateAdvanceAmountDisplay() {
    // Try to get total from various possible locations
    let total = this.extractTotalAmount();
    this.totalAmount = total || 0;

    // Update display
    const totalDisplay = document.getElementById('total-display');
    const maxAdvance = document.getElementById('max-advance');

    if (totalDisplay) {
      totalDisplay.textContent = `₹${this.totalAmount.toFixed(2)}`;
    }
    if (maxAdvance) {
      maxAdvance.textContent = `₹${this.totalAmount.toFixed(2)}`;
    }
  }

  /**
   * Extract total amount from various possible locations in the DOM
   */
  extractTotalAmount() {
    // Try multiple selectors
    const selectors = [
      '.total-amount',
      '[class*="total-amount"]',
      '[id*="total"]',
      '.summary [class*="total"]',
      '.SUMMARY strong:last-child'
    ];

    for (const selector of selectors) {
      const elements = document.querySelectorAll(selector);
      for (const el of elements) {
        const text = el.textContent.trim();
        const match = text.match(/₹?[\s]*([\d,.]+)/);
        if (match) {
          const amount = parseFloat(match[1].replace(/[,]/g, ''));
          if (!isNaN(amount) && amount > 0) {
            return amount;
          }
        }
      }
    }

    // Fallback: check form context
    if (this.form && this.form.total_amount) {
      return parseFloat(this.form.total_amount);
    }

    return 0;
  }

  /**
   * Reset advance amount
   */
  resetAdvanceAmount() {
    this.advanceAmount = 0;
    this.codAmount = 0;
    const input = document.getElementById('advance_amount');
    if (input) {
      input.value = '';
    }
    this.updatePaymentBreakdown();
  }

  /**
   * Update form data with current payment info
   */
  updateFormData() {
    // Update form object
    this.form.payment_method = this.selectedMethod;
    this.form.advance_amount = this.selectedMethod === 'partial_cod' ? this.advanceAmount : 0;

    // Update hidden form fields if they exist
    const methodField = document.querySelector('input[name="payment_method"]');
    if (methodField) {
      methodField.value = this.selectedMethod;
    }

    const advanceField = document.querySelector('input[name="advance_amount"]');
    if (advanceField) {
      advanceField.value = this.form.advance_amount;
    } else {
      // Create hidden field if it doesn't exist
      this.createAdvanceField();
    }
  }

  /**
   * Create hidden advance_amount field if it doesn't exist
   */
  createAdvanceField() {
    let field = document.querySelector('input[name="advance_amount"]');
    if (!field) {
      field = document.createElement('input');
      field.type = 'hidden';
      field.name = 'advance_amount';
      field.value = this.form.advance_amount || 0;
      document.querySelector('form').appendChild(field);
    }
  }

  /**
   * Get form data including partial COD fields
   */
  getFormData() {
    return {
      payment_method: this.selectedMethod,
      advance_amount: this.selectedMethod === 'partial_cod' ? this.advanceAmount : 0,
    };
  }

  /**
   * Validate payment form before submission
   */
  validatePaymentForm() {
    if (!this.selectedMethod) {
      this.showNotification('error', '❌ Please select a payment method');
      return false;
    }

    if (this.selectedMethod === 'partial_cod') {
      if (this.advanceAmount <= 0) {
        this.showNotification('error', '❌ Please enter a valid advance amount');
        return false;
      }
      if (this.advanceAmount > this.totalAmount) {
        this.showNotification('error', '❌ Advance amount cannot exceed total amount');
        return false;
      }
    }

    return true;
  }

  /**
   * Show notification message
   */
  showNotification(type, message) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      padding: 12px 20px;
      background: ${type === 'error' ? '#f44336' : type === 'success' ? '#4caf50' : '#ff9800'};
      color: white;
      border-radius: 4px;
      z-index: 10000;
      animation: slideInRight 0.3s ease;
    `;

    document.body.appendChild(notification);

    // Auto-remove after 4 seconds
    setTimeout(() => {
      notification.remove();
    }, 4000);
  }

  /**
   * Initialize with dynamic total amount updates
   */
  watchTotalAmountChanges() {
    // Set up a MutationObserver to watch for total amount changes
    const targetElement = document.querySelector('.SUMMARY') 
      || document.querySelector('[class*="summary"]');

    if (targetElement) {
      const observer = new MutationObserver(() => {
        this.updateAdvanceAmountDisplay();
      });

      observer.observe(targetElement, {
        characterData: true,
        subtree: true,
        childList: true
      });
    }
  }
}

// Export for use in HTML
if (typeof module !== 'undefined' && module.exports) {
  module.exports = PartialCODPaymentController;
}

// Auto-initialize if data attributes are present
document.addEventListener('DOMContentLoaded', () => {
  if (document.querySelector('[data-init-partial-cod]')) {
    const controller = new PartialCODPaymentController(window.orderForm || {});
    controller.initPaymentMethods();
    controller.watchTotalAmountChanges();
    window.paymentController = controller; // Expose to global scope
  }
});
