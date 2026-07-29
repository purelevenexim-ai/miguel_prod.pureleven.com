# ⚡ GSTIN Validation — Quick Start

## Your GSTIN: `32BCJPT7873A1ZG` ✅

**Status:** Validated ✓  
**State:** Daman and Diu  
**Format:** Valid (15 characters)  

---

## What to Do Next

### Step 1: Go to GST & Accounting Page
Dashboard → **🧮 GST & Accounting**

### Step 2: Click "Edit GST Profile"
Button in sidebar: **✏️ Edit GST Profile**

### Step 3: Enter & Verify Your GSTIN
```
GSTIN field: 32BCJPT7873A1ZG
Click: ✓ Verify
```

### Step 4: Auto-fill Happens
```
✅ Valid GSTIN · State: Daman and Diu
State dropdown → automatically set to "Daman and Diu"
```

### Step 5: Complete the Profile
- **Address:** Your registered business address
- **City:** City name
- **Pincode:** 6-digit postal code

### Step 6: Save
Click **💾 Save Profile** button

---

## What Just Happened

| Feature | What It Does |
|---------|-------------|
| GSTIN Validator | Checks if GSTIN is valid format + state code exists |
| Auto-fill | When GSTIN is valid, automatically fills state dropdown |
| Error Messages | Clear feedback if GSTIN is invalid |

---

## Why This Matters

Your **Home State** (now: **Daman and Diu**) controls GST calculation:

- **Orders shipped TO Daman & Diu:**  
  CGST + SGST split (5% each if 10% rate)

- **Orders shipped TO other states:**  
  IGST only (10% on entire value)

---

## FAQ

**Q: Where does it get business name & address?**  
A: GSTIN format validation only. For full details, check https://www.gst.gov.in manually.

**Q: What if validation fails?**  
A: Check GSTIN spelling + state code is valid (01-37). Use https://www.gst.gov.in to verify.

**Q: Can I use a different state?**  
A: Yes, manually override. But it must match your actual registered office for GST compliance.

---

## Test the Feature

**Open Browser Console (F12) and test:**
```javascript
// Validate your GSTIN via API
fetch('/api/gst/validate-gstin/32BCJPT7873A1ZG', {
  headers: { 'Authorization': 'Bearer ' + localStorage.getItem('token') }
})
.then(r => r.json())
.then(d => console.log(d))
```

Expected output:
```json
{
  "valid": true,
  "details": {
    "gstin": "32BCJPT7873A1ZG",
    "state_code": "32",
    "state_name": "Daman and Diu",
    "pan_prefix": "BCJPT",
    "registration_number": "7873A",
    "is_valid": true
  }
}
```

---

## Done! ✅

Your GST module is ready. Generate a report to see it in action.
