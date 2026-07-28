# Miguel CRM — Favicon & Branding

> **Last Updated:** 2026-02-28  
> **Status:** Production-deployed

---

## Current Favicon

**File:** `frontend/miguel_favicon.png`  
**Format:** PNG, 512×512 pixels, 8-bit RGBA  
**Size:** ~108KB  
**Source:** Downloaded from Google Drive — real squirrel photo (brand mascot)

---

## Favicon Files

| File | Status | Notes |
|------|--------|-------|
| `frontend/miguel_favicon.png` | ✅ Active | Primary favicon — 512×512 squirrel photo |
| `frontend/favicon.ico` | ✅ Active | Replaced with PNG content (108KB) |
| `frontend/favicon.png` | ✅ Active | Alias — same as miguel_favicon.png |
| `frontend/favicon.svg` | 🗑️ Removed | Old SVG placeholder — no longer used |

---

## HTML Reference (All Pages)

Every page uses exactly these three tags:
```html
<link rel="icon" type="image/png" href="/miguel_favicon.png?v=2">
<link rel="shortcut icon" type="image/png" href="/miguel_favicon.png?v=2">
<link rel="apple-touch-icon" href="/miguel_favicon.png?v=2">
```

The `?v=2` query string forces browsers to reload after the favicon was replaced.

---

## Brand Icon in Sidebar/Login Pages

The squirrel icon also appears as the brand logo in:
- All sidebar navigation headers
- Login pages (`tenant-login.html`, `platform-login.html`)
- Platform admin sidebar

```html
<img src="/miguel_favicon.png" alt="Miguel" style="width:28px;height:28px;border-radius:50%;object-fit:cover;">
```

---

## Updating the Favicon

To replace the favicon again:
1. Upload new PNG to `/opt/miguel/frontend/miguel_favicon.png` (recommended: 512×512)
2. Bump the cache-buster version: change `?v=2` → `?v=3` across all HTML files
3. Run: `grep -rn "miguel_favicon.png?v=" frontend/*.html` to find all occurrences
4. Deploy frontend container

---

## Pages Updated

All 18 HTML files were updated on 2026-02-28:
- tenant-admin.html, orders.html, customers.html, leads.html, products.html
- vendors.html, invoices.html, whatsapp.html, lead-messages.html, gst.html
- marketing.html, profit-loss.html, platform-admin.html, platform-login.html
- tenant-login.html, customer-portal.html, wa-setup-guide.html, index.html
