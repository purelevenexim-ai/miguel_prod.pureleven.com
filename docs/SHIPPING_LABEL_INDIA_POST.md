# Shipping Label — India Post Customer ID

## Overview

When generating shipping labels for orders with **India Post** as the delivery partner, the **India Post Customer ID** (also called "Service Type" or "Service ID") is now displayed on the label above the "Cash on Delivery" section.

## Changes

### 1. **Backend — Label Service** (`backend/app/modules/labels/service.py`)

- **Modified `_order_to_label_data()`**: 
  - Now accepts an optional `delivery_partner` parameter
  - If the delivery partner's `partner_type == "india_post"` and the order has an `india_post_customer_id`, it extracts and returns that ID
  - Returns the ID in the label data dict as `"india_post_customer_id"`

- **Modified `generate_labels()`**:
  - When processing orders, loads the associated `DeliveryPartner` (if `shipping_partner_id` is set)
  - Passes the delivery partner to `_order_to_label_data()` so it can determine whether to include the India Post customer ID

### 2. **PDF Label Generator** (`backend/app/core/label_pdf.py`)

- **Modified `draw_label()`**:
  - Added new section: **India Post Customer ID display**
  - Positioned above the "Cash on Delivery" section (as requested)
  - Label format: `India Post Service ID: <customer_id>`
  - Font: Helvetica Bold for label, Helvetica regular for ID value
  - Only displays if `india_post_customer_id` key is non-empty in data dict

## Label Display Example

```
┌─────────────────────────────────┐
│       Pure Leven Exim           │
│  Authentic, Organic & Pure...   │
│ ─────────────────────────────── │
│ India Post Service ID: 12345678 │  ← NEW LINE (above COD)
│ ─────────────────────────────── │
│     Cash on Delivery            │
│  Collect Amount - Rs. 440.00    │
│                              [COD]│
│ ─────────────────────────────── │
│ basil                           │
│ Adimali, Kerala                 │
│ PIN: 685561                     │
│ 09447744583                     │
│ ...                             │
└─────────────────────────────────┘
```

## Flow

1. **Order Creation**: User selects:
   - Delivery Partner: "India Post"
   - Service Type (India Post Customer ID): "12345678"
   
2. **Label Generation**: When `/api/labels/generate` is called:
   - Order is loaded with its `shipping_partner_id`
   - Delivery partner is fetched from DB
   - Label data includes the `india_post_customer_id` from the order
   
3. **PDF Rendering**:
   - PDF generator reads the `india_post_customer_id` field
   - Displays it above the COD section if present

## Deployment

- **Commit**: `3f3ffa3`
- **Status**: ✅ Deployed to production
- **Backend**: Restarted successfully

## Testing

To test:

1. Go to **Orders** → **New Order**
2. Select:
   - Delivery Partner: "India Post"
   - Service Type: Any India Post service ID
3. Create the order
4. Go to **Labels** → **Generate**
5. Print/view the label
6. Verify the India Post Service ID appears above the COD section

## Database Fields Used

- `orders.shipping_partner_id` — FK to `delivery_partners`
- `orders.india_post_customer_id` — The selected customer ID
- `delivery_partners.partner_type` — Used to determine if "india_post"

---

**Last Updated**: 2026-02-27  
**Related Feature**: Delivery Partner Selection  
**Status**: Production Ready
