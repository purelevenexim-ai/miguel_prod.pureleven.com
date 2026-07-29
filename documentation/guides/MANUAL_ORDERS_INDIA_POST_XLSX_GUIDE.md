# Manual Orders — India Post Tracking Upload Guide

## Overview
Employees can now bulk-upload India Post tracking numbers for **manual orders** using an Excel (.xlsx) file. The system will automatically match customers by name and assign tracking IDs.

---

## How It Works

### 1. **Upload Location**
- Go to **Orders** page → **Manual Orders** tab
- In the toolbar, click **📄 India Post xlsx** button
- Select your xlsx file

### 2. **File Format**
The xlsx file needs **two columns** (column order doesn't matter, matching is flexible):

#### **Column 1: Customer Name**
- Header can be: `Customer Name`, `Customer`, `Name`, `customer_name`, etc.
- Value: Full or partial customer name (e.g., "Rajesh Kumar", "Rajesh", "Kumar")

#### **Column 2: Tracking Number / Article Number**
- Header can be: `Article Number`, `Tracking Number`, `Article No`, `tracking no`, `AWB`, etc.
- Value: India Post article number (e.g., `EE123456789IN`)

### 3. **Matching Algorithm**
- The system searches for orders with matching customer names (case-insensitive, substring match)
- If multiple orders match the same customer, the **most recent order** is selected
- If no match found, the row is skipped with a reason logged

### 4. **Order Updates**
For each successfully matched order:
- ✅ Tracking number assigned
- ✅ Shipping partner set to **India Post**
- ✅ Order status updated to **Shipped** (if not already shipped/delivered)
- ✅ Entry logged in response

---

## Example Excel File

| Customer Name | Article Number |
|---|---|
| Rajesh Kumar | EE123456789IN |
| Priya Sharma | EE987654321IN |
| Amit Patel | EE111222333IN |
| John Doe | EE444555666IN |

---

## Response & Feedback

After upload, you'll see:
- ✅ **Count**: Number of orders updated
- ⚠️ **Skipped**: Rows that couldn't be matched
- 📋 **Details**: Each skipped row shows the customer name and reason

### Reasons for Skipped Rows:
- `Missing tracking number` — Article number field is empty
- `No matching customer found` — No order found with that customer name
- `Invalid format` — Row is empty or malformed

---

## Tips for Best Results

1. **Use Full Names**: More specific names = better matching
   - Good: "Rajesh Kumar Singh"
   - Bad: "R.K." or just "Rajesh"

2. **Check Order Status**: Only matching will update **awaiting_shipment** → **shipped**
   - Already shipped orders: status unchanged

3. **Review Before Upload**: 
   - Use **Manual Orders** search to find customers first
   - Verify names match exactly

4. **Batch Uploads**: You can upload multiple files in succession
   - Each upload is independent
   - No duplicates — if tracking is already set, it's overwritten

---

## Auto-Refresh
After a successful upload, the Manual Orders table automatically refreshes after ~1 second to show the updated tracking information.

---

## Troubleshooting

| Issue | Solution |
|---|---|
| "Cannot find 'Customer Name' column" | Check that the header row has a recognizable customer name column |
| "Cannot find 'Article Number' column" | Ensure tracking/article column exists with proper headers |
| "No matching customer found" | Use **Search** in Manual Orders to find the exact customer name used |
| "xlsx file has no data rows" | Ensure file has at least 2 rows (header + data) |
| "Cannot parse xlsx" | Ensure file is a valid Excel file (.xlsx, not .xls or .csv) |

---

## Related Features

- **Shopify Orders**: Use the separate `📄 India Post xlsx` button on the **🛍️ Shopify** tab (matches by Shopify Order #)
- **Manual Assignment**: Use the order drawer to assign individual tracking numbers
- **Delhivery**: Supports auto-waybill creation (no manual tracking needed)
