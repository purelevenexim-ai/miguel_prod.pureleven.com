# Miguel CRM — Auth & Session Management

> **Last Updated:** 2026-02-28  
> **Status:** Production-ready  
> **Applies to:** All frontend pages

---

## Overview

Miguel CRM uses a token-based authentication system. User tokens are stored in `localStorage` and validated on every page load. This document describes the canonical patterns used across all pages.

---

## Storage Keys

| Key | Value | Description |
|-----|-------|-------------|
| `token` | JWT string | Auth token from backend login |
| `type` | `tenant` or `platform` | User type |
| `role` | `admin`, `operations`, `sales`, `staff` | Tenant user role |
| `slug` | e.g. `pureleven` | Tenant identifier |
| `email` | user@example.com | User email (optional) |
| `user_id` | integer string | User ID |

---

## Shared Auth Module: `modules/auth.js`

All pages load `/modules/auth.js` which provides:

```javascript
// Exposed as window.MiguelAuth
MiguelAuth.guard('tenant')    // Redirect to tenant-login if not authenticated
MiguelAuth.guard('platform')  // Redirect to platform-login if not platform type
MiguelAuth.guard('any')       // Redirect to login if not authenticated at all

MiguelAuth.logout()           // Clears all storage + redirect to login
MiguelAuth.headers()          // Returns { Authorization: 'Bearer ...', Content-Type: ... }
MiguelAuth.api(method, path, body)  // fetch() with 401 auto-logout
MiguelAuth.isLoggedIn()       // boolean
MiguelAuth.user()             // { token, type, role, slug, email }
MiguelAuth.get(key)           // localStorage.getItem(key) with sessionStorage fallback
```

### Loading auth.js

Every page includes this **before** its own `<script>` block:
```html
<script src="/modules/auth.js"></script>
```

---

## Per-Page Auth Patterns

### Tenant Pages (all except platform-admin)

```javascript
const TOKEN = localStorage.getItem('token');
const TYPE  = localStorage.getItem('type');
if (!TOKEN || TYPE !== 'tenant') window.location.replace('/tenant-login.html');
const H = { 'Authorization': `Bearer ${TOKEN}`, 'Content-Type': 'application/json' };
const ROLE = localStorage.getItem('role') || 'admin';
const SLUG = localStorage.getItem('slug') || '';
```

### Platform Admin Page

```javascript
const TOKEN = localStorage.getItem('token');
const TYPE  = localStorage.getItem('type');
if (!TOKEN || TYPE !== 'platform') window.location.replace('/platform-login.html');
```

---

## Logout Function

All tenant pages use:
```javascript
function logout() {
  ['token','type','role','slug','user_id','email','tenant_token'].forEach(k => {
    localStorage.removeItem(k); sessionStorage.removeItem(k);
  });
  window.location.replace('/tenant-login.html');
}
```

Platform admin uses `window.location.replace('/platform-login.html')`.

**Note:** `replace()` is used instead of `href=` to prevent back-button returning to protected pages.

---

## API Calls — 401 Handling

### Pages with `api()` function (tenant-admin.html)

```javascript
function api(method, path, body) {
  const opts = { method, headers: H };
  if (body) opts.body = JSON.stringify(body);
  return fetch(path, opts).then(r => {
    if (r.status === 401) { logout(); throw new Error('Session expired'); }
    return r;
  });
}
```

### Pages with `handleAuthError()` (orders.html, invoices.html)

```javascript
function handleAuthError(status) {
  if (status === 401) { logout(); }
}
// Used as: if (!r.ok) { handleAuthError(r.status); return; }
```

### Pages with async `api()` (whatsapp.html)

```javascript
async function api(method, path, body) {
  const r = await fetch(HOST + path, opts);
  if (r.status === 401) { logout(); throw new Error('Session expired'); }
  return r.json();
}
```

### Pages with async `apiFetch()` (lead-messages.html)

```javascript
async function apiFetch(method, path, body) {
  const r = await fetch(path, opts);
  if (r.status === 401) { logout(); throw new Error('Session expired'); }
  return r.json();
}
```

---

## Cache Prevention

### HTML Page Headers

Every page has these meta tags in `<head>`:
```html
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
```

### Nginx Configuration

HTML files are served with no-cache headers:
```nginx
location ~* \.html$ {
    add_header Cache-Control "no-cache, no-store, must-revalidate";
    add_header Pragma "no-cache";
    add_header Expires "0";
    try_files $uri =404;
}
```

Static assets (CSS/JS/images) are served with long-cache + versioned URLs:
```nginx
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
    expires 365d;
    add_header Cache-Control "public, max-age=31536000, immutable";
    try_files $uri =404;
}
```

---

## CSS Versioning

All pages use a consistent CSS version to ensure browsers pick up updates:

```html
<link rel="stylesheet" href="/ds.css?v=20260228">
<link rel="stylesheet" href="/styles/mobile.css?v=20260228">
```

**Current version:** `20260228`  
**Update procedure:** When `ds.css` or `mobile.css` changes, update the version across all pages with the date of change.

---

## Token Retrieval Standard

**Use:**
```javascript
localStorage.getItem('token')
```

**Do not use:**
- `sessionStorage` fallbacks (session storage is volatile; tokens are always in localStorage)
- `tenant_token` key (legacy — was removed)
- Multiple fallback chains

---

## Pages Inventory

| Page | Type | Guard | Has logout() | auth.js | 401 handled |
|------|------|-------|--------------|---------|-------------|
| `tenant-admin.html` | tenant | ✅ | ✅ | ✅ | ✅ api() |
| `orders.html` | tenant | ✅ | ✅ | ✅ | ✅ handleAuthError |
| `customers.html` | tenant | ✅ | ✅ | ✅ | ✅ |
| `leads.html` | tenant | ✅ | ✅ | ✅ | ✅ |
| `products.html` | tenant | ✅ | ✅ | ✅ | ✅ |
| `vendors.html` | tenant | ✅ | ✅ | ✅ | ✅ |
| `invoices.html` | tenant | ✅ | ✅ | ✅ | ✅ handleAuthError |
| `whatsapp.html` | tenant | ✅ | ✅ | ✅ | ✅ api() |
| `lead-messages.html` | tenant | ✅ | ✅ | ✅ | ✅ apiFetch() |
| `gst.html` | tenant | ✅ | ✅ | ✅ | ✅ |
| `marketing.html` | tenant | ✅ | ✅ | ✅ | ✅ |
| `profit-loss.html` | tenant | ✅ | ✅ | ✅ | ✅ |
| `platform-admin.html` | platform | ✅ | ✅ | ✅ | — |

---

## Login Pages

Login pages (`tenant-login.html`, `platform-login.html`) do **not** have auth guards or token storage. They set localStorage values on successful login.

### Customer Portal

`customer-portal.html` uses a separate token system (order tracking link tokens, not admin tokens).

---

## Security Notes

1. **No XSS risk from token storage:** Tokens are JWT strings without user-controllable data rendered into the DOM.
2. **All API calls** include `Authorization: Bearer <token>` header.
3. **Session expiry:** 401 responses auto-logout and clear all storage.
4. **Back-button protection:** All redirects use `window.location.replace()` (not `href`) to prevent back-navigation to protected pages after logout.
