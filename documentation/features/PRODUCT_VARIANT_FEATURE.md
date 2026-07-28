# 📦 Product Variant Feature

**Created:** February 27, 2026  
**Status:** ✅ Live  
**Version:** 1.0

---

## 🎯 Overview

The **Product Variant Feature** allows you to create variants of existing products without manually re-entering all the parent product information. When you create a variant, the system automatically populates all parent product data, and you only need to customize the fields that differ.

---

## 🚀 How It Works

### Creating a Variant

1. **Go to Products page** → Find the parent product in the list
2. **Click "+ Variant" button** in the product's actions (the teal button)
3. **Auto-populated fields** appear in the form:
   - ✅ Category
   - ✅ Description
   - ✅ Unit (kg, gram, piece, etc.)
   - ✅ Unit Value
   - ✅ HSN Code
   - ✅ GST Rate
   - ✅ Tax Inclusive setting
   - ✅ Cost Price

4. **You must fill in these fields:**
   - 🔴 **Product Name** - The variant name (e.g., "Turmeric - 250g")
   - 🔴 **Selling Price** - The variant's price (different from parent)
   - 💡 **SKU** - Optional, but recommended for inventory tracking
   - 💡 **Pack Label** - How to print on the label (e.g., "250g")
   - 💡 **Variation Label** - Short name (e.g., "250g / 500g / 1kg")
   - 💡 **MRP** - Maximum Retail Price
   - 💡 **Cost Price** - Edit if different from parent

5. **Click "Save Product"** to create the variant

---

## 📊 Example Workflow

### Parent Product
```
Name:         Turmeric Powder
Category:     Spices
SKU:          TUR-MASTER
Description:  Pure turmeric powder from Kerala
Unit:         gram
Unit Value:   1000
Pack Label:   1kg
Unit Label:   1kg
HSN Code:     0910
GST Rate:     5%
Cost Price:   ₹180
```

### Creating Variant 1 (250g)
✅ Auto-populated from parent:
- Category: Spices
- Description: Pure turmeric powder from Kerala
- Unit: gram
- HSN Code: 0910
- GST Rate: 5%
- Cost Price: ₹180

🔴 You enter:
- Product Name: **Turmeric Powder - 250g**
- Selling Price: **₹95** (different from parent's ₹380)
- SKU: **TUR-250G** (optional)
- Pack Label: **250g**
- Variation Label: **250g**

### Creating Variant 2 (500g)
✅ Auto-populated from parent:
- Category: Spices
- Description: Pure turmeric powder from Kerala
- Unit: gram
- HSN Code: 0910
- GST Rate: 5%
- Cost Price: ₹180

🔴 You enter:
- Product Name: **Turmeric Powder - 500g**
- Selling Price: **₹185** (different from parent's ₹380)
- SKU: **TUR-500G** (optional)
- Pack Label: **500g**
- Variation Label: **500g**

---

## 🔑 Key Features

### 1. **Time-Saving**
- Avoid re-typing category, description, GST, HSN code
- Inherits parent's tax and regulatory information
- Reduces data entry errors

### 2. **Data Consistency**
- All variants share parent's:
  - Category
  - Description
  - Tax settings (HSN, GST)
  - Unit type
- Different prices only where needed

### 3. **Flexible Editing**
- Auto-populated fields can be edited if needed
- Cost price can be adjusted per variant
- All fields are optional except product name and price

### 4. **Clear Variant Identification**
- Variants appear indented in product list
- Show "Variant: [label]" under product name
- Easy to see parent-child relationships

---

## 📋 Fields Explained

### Auto-Populated (from Parent)
| Field | Why | Can Edit |
|-------|-----|----------|
| **Category** | Variants are same category | ✅ Yes |
| **Description** | Variants describe same product | ✅ Yes |
| **Unit** | All variants in same unit | ✅ Yes |
| **Unit Value** | Base unit is same | ✅ Yes |
| **HSN Code** | Tax code for same product | ✅ Yes |
| **GST Rate** | Tax rate for product | ✅ Yes |
| **Tax Inclusive** | Tax treatment is same | ✅ Yes |
| **Cost Price** | Usually same cost | ✅ Yes (adjust if different) |

### You Must Enter
| Field | Why | Required |
|-------|-----|----------|
| **Product Name** | Each variant has unique name | ✅ Yes |
| **Selling Price** | Different for each pack size | ✅ Yes |

### Optional (Variant-Specific)
| Field | Example | Recommended |
|-------|---------|-------------|
| **SKU** | TUR-250G, TUR-500G | ✅ Yes |
| **Pack Label** | 250g, 500g, 1kg | ✅ Yes |
| **Variation Label** | 100g / 250g / 500g | 💡 Sometimes |
| **MRP** | Different for different sizes | 💡 If applicable |

---

## 🎨 UI Indicators

### In Product List
- **Indented rows** = Variants (grey background)
- **Parent products** = Normal rows (white background)
- **"Variant: [label]"** text under product name

### In Form
- Modal title: `New Variant of "Parent Name"`
- Pre-filled fields appear with parent's data
- Price fields are empty (you must enter)

---

## 🔄 Typical Use Cases

### Use Case 1: Same Product, Different Pack Sizes
```
Parent:   Turmeric Powder (Master/Default)
Variant 1: Turmeric - 250g (₹95)
Variant 2: Turmeric - 500g (₹185)
Variant 3: Turmeric - 1kg (₹380)
```

### Use Case 2: Different Grades/Qualities
```
Parent:     Coffee Beans (Standard Grade)
Variant 1:  Coffee Beans - Premium Grade (₹450)
Variant 2:  Coffee Beans - Export Grade (₹650)
```

### Use Case 3: Bulk vs Retail
```
Parent:   Rice - Retail (1kg)
Variant 1: Rice - Bulk (25kg bag)
Variant 2: Rice - Wholesale (50kg bag)
```

---

## ⚠️ Important Notes

### What Gets Copied
✅ Category, Description, Unit, HSN Code, GST Rate, Cost Price

### What You Must Change
🔴 Product Name (must be unique)
🔴 Selling Price (usually different)

### What's Optional
💡 SKU, Pack Label, MRP, Variation Label

### Tip: Naming Convention
```
Parent: "Turmeric Powder"
Variant 1: "Turmeric Powder - 250g"
Variant 2: "Turmeric Powder - 500g"

or

Parent: "Turmeric" 
Variant 1: "Turmeric 250g"
Variant 2: "Turmeric 500g"
```

---

## 📱 Step-by-Step Guide

### Creating Your First Variant

**Step 1:** Open Products page
```
Click on "Products" in the sidebar
```

**Step 2:** Find parent product
```
Scroll or search for "Turmeric Powder"
Click the "250g" pack size (or whichever you want as parent)
```

**Step 3:** Click "+ Variant" button
```
In the Actions column, click the teal "+ Variant" button
Modal opens with auto-populated data
```

**Step 4:** Review auto-populated fields
```
✅ Category: Spices (auto-filled, looks correct)
✅ HSN Code: 0910 (auto-filled, looks correct)
✅ Cost Price: ₹180 (auto-filled, adjust if needed)
```

**Step 5:** Enter variant-specific data
```
🔴 Name: "Turmeric Powder - 500g" (unique name required)
🔴 Price: ₹185 (different price)
💡 SKU: TUR-500G (recommended)
💡 Pack Label: 500g (recommended)
```

**Step 6:** Click "Save Product"
```
Success! Variant is created
Product list refreshes
You see new variant indented under parent
```

---

## 🐛 Troubleshooting

### Problem: "+ Variant" button not visible
**Solution:** Check your role permissions. You need "admin" or "operations" role.

### Problem: Form shows empty fields instead of parent data
**Solution:** Reload the page and try again. The parent product needs to be fully loaded in the list.

### Problem: Variant appears in list but not indented
**Solution:** Refresh the page. The frontend caches product data, reload to see new hierarchy.

### Problem: Created variant but can't edit it
**Solution:** 
- Reload the products page
- Variants use same edit functionality as regular products
- You can edit any field at any time

---

## 💡 Best Practices

### DO ✅
- ✅ Use consistent naming: "Product - Size" format
- ✅ Always fill in SKU for variants (helps inventory tracking)
- ✅ Set different prices for different pack sizes
- ✅ Keep category consistent across variants
- ✅ Review auto-populated GST/tax before saving

### DON'T ❌
- ❌ Create variants with identical names
- ❌ Forget to enter selling price
- ❌ Create unnecessary variants (only for real product variations)
- ❌ Use variant system for completely different products
- ❌ Skip SKU if you track inventory

---

## 🔗 Related Features

- **[Product Management](https://github.com/purelevenexim-ai/crm/docs/features/)**
- **[Inventory Management](https://github.com/purelevenexim-ai/crm/docs/features/)**
- **[Stock Tracking](https://github.com/purelevenexim-ai/crm/docs/features/)**

---

## 📊 Product Variant Structure

```
Product Model (database/product.py)
├── variation_of (UUID) → Parent product ID
├── variation_name (String) → "100g / 250g / 500g"
└── All other fields → Inherited or customized

Example:
Turmeric Powder (id: abc123)
  ├─ Turmeric - 250g (variation_of: abc123)
  ├─ Turmeric - 500g (variation_of: abc123)
  └─ Turmeric - 1kg (variation_of: abc123)
```

---

## ✨ Update History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Feb 27, 2026 | Initial release - Auto-populate parent data |

---

**Status:** ✅ Live and Production Ready  
**Last Updated:** February 27, 2026  
**Commit:** 719878b
