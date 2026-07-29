# 🏗️ Compose Model Migration Plan

## Current State Audit

### Problem Statement
The app loads elements in desktop layout, then JS fires and switches to mobile — causing a **FOUC (Flash of Unstyled Content)**. This happens because:
1. `adaptive-layout.js` waits for `DOMContentLoaded` to set `data-size-width`
2. ALL mobile CSS depends on `html[data-size-width="compact"]` selectors
3. Until JS runs → desktop layout renders → then suddenly rewrites to mobile

### Files Inventory (What Exists)

| File | Lines | Status |
|------|-------|--------|
| `ds.css` | 1,129 | ✅ KEEP — M3 design tokens + base components |
| `adaptive.css` | 1,565 | ❌ REWRITE — 80% is patched mobile overrides |
| `mobile.css` | 1,537 | ❌ DELETE — dead file, no pages reference it |
| `mobile.css.bak` | — | ❌ DELETE — backup of dead file |
| `partial-cod.css` | 582 | ❌ DELETE — not referenced by any page |
| `adaptive-layout.js` | 224 | ✅ KEEP+FIX — size class detection |
| `mobile-nav.v4.js` | 283 | ✅ REWRITE — cleaner compose navigation |
| `mobile-nav.js` | — | ❌ DELETE — old version, not used |
| 15 HTML pages | ~3,547 inline `<style>` lines | ❌ EXTRACT to CSS |
| 15 HTML pages | 1,840 `style=""` attributes | ❌ CONVERT to classes |

### Architecture Problems
1. **FOUC** — JS-dependent layout switching
2. **3 layers of CSS** competing: ds.css → inline `<style>` → adaptive.css
3. **1,840 inline styles** — unmaintainable, inconsistent
4. **~3,547 lines** of page-specific CSS inside `<style>` blocks
5. **Dead files** adding confusion (mobile.css, partial-cod.css, mobile-nav.js)
6. **No CSS-first responsiveness** — everything depends on JS attribute

---

## Migration Plan — Compose Model for Web

### Principles (from Android Compose, adapted for Web)

| Compose Concept | Web Implementation |
|---|---|
| **WindowSizeClasses** | CSS `@media` queries (no JS dependency) |
| **Material Theme** | CSS custom properties in `:root` (ds.css) |
| **Composable functions** | Reusable CSS component classes |
| **Scaffold** | `.scaffold` layout with topbar/content/bottomnav slots |
| **NavigationBar** | `.nav-bar` (bottom), `.nav-rail` (side), `.nav-drawer` (expanded) |
| **Modifier** | Utility classes (.p-4, .gap-2, .flex, etc.) |
| **State hoisting** | Data attributes + minimal JS |
| **LazyColumn/LazyGrid** | CSS Grid + Flexbox |
| **AnimateVisibility** | CSS transitions + animations |
| **Typography** | M3 type scale classes |

---

## Phase 1: Fix FOUC + Delete Dead Files
**Estimated scope: ~30 min**

### 1A. Fix FOUC — CSS-first responsive (no JS dependency)
**Root cause:** `data-size-width` is set by JS after page loads.
**Fix:** Use standard `@media` queries as the PRIMARY layout mechanism. JS `data-size-width` becomes an enhancement, not a requirement.

- Rewrite `adaptive.css` to use `@media (max-width: 599px)` instead of `html[data-size-width="compact"]`
- `adaptive-layout.js` still sets attributes for JS consumers but CSS no longer depends on it
- Page renders correctly BEFORE JS loads — no flash

### 1B. Delete dead files
- `styles/mobile.css` — not referenced
- `styles/mobile.css.bak` — backup
- `styles/partial-cod.css` — not referenced
- `modules/mobile-nav.js` — old version

---

## Phase 2: Compose Scaffold + Component System
**Estimated scope: ~2 hours**

### 2A. Create Compose Scaffold Layout System
Every page gets a standard scaffold structure:

```html
<body class="scaffold">
  <nav class="nav-drawer">...</nav>          <!-- expanded only -->
  <nav class="nav-rail">...</nav>            <!-- medium only -->
  <div class="scaffold-content">
    <header class="top-bar">...</header>     <!-- always -->
    <main class="content-area">...</main>    <!-- scrollable -->
  </div>
  <nav class="nav-bar">...</nav>             <!-- compact only -->
</body>
```

### 2B. Compose Component Classes (replace inline styles)
Create utility + component classes in `ds.css`:

```css
/* Layout */
.flex { display: flex; }
.flex-col { flex-direction: column; }
.items-center { align-items: center; }
.justify-between { justify-content: space-between; }
.gap-1 { gap: 4px; }
.gap-2 { gap: 8px; }
.gap-3 { gap: 12px; }
.gap-4 { gap: 16px; }
.p-2 { padding: 8px; }
.p-4 { padding: 16px; }
.p-x-4 { padding-left: 16px; padding-right: 16px; }
.w-full { width: 100%; }

/* M3 Components */
.card { ... }
.card-elevated { ... }
.card-outlined { ... }
.chip { ... }
.chip-filled { ... }
.dialog { ... }
.drawer { ... }
.list-item { ... }
.stat-card { ... }
.data-table { ... }
```

### 2C. Compose Navigation System
Replace `mobile-nav.v4.js` with a cleaner implementation:

```
Compact (<600px)  → Bottom NavigationBar (3-5 items + FAB)
Medium (600-839px) → NavigationRail (left strip, 72px)
Expanded (840px+)  → NavigationDrawer (permanent sidebar)
```

All controlled by CSS `@media`, JS only handles interactivity (toggle sidebar, etc.)

---

## Phase 3: Page-by-Page Conversion
**Estimated scope: ~3-4 hours**

Convert each page (priority order):
1. `tenant-admin.html` (Dashboard) — template page
2. `leads.html` — most complex mobile usage
3. `orders.html` — drawer + overlay issues
4. `customers.html` — table layout
5. `invoices.html` — table layout
6. `products.html` — grid layout
7. `vendors.html` — table layout
8. `gst.html` — table layout
9. `marketing.html` — largest page (4,104 lines)
10. `whatsapp.html` — chat interface
11. `profit-loss.html` — charts
12. `lead-messages.html` — messaging
13. `platform-admin.html` — admin panel
14. `tenant-login.html` — auth page
15. `platform-login.html` — auth page

Per page:
- Extract inline `<style>` to component classes
- Replace `style=""` attributes with utility classes
- Apply scaffold structure
- Remove page-specific media queries (use global)
- Test mobile + desktop

---

## Phase 4: Polish + Performance
**Estimated scope: ~1 hour**

- Animation system (Material motion)
- Touch targets (min 48px)
- Accessibility (ARIA, focus management)
- Performance audit (CSS size, paint times)
- Dark mode ready (token-based)

---

## Execution Order

We start NOW with **Phase 1 + Phase 2** (the foundation):

1. ✅ Delete dead files
2. ✅ Fix FOUC — rewrite adaptive.css to use @media queries
3. ✅ Create scaffold layout system
4. ✅ Create compose component + utility classes
5. ✅ Rewrite navigation system (CSS-first)
6. ✅ Convert template page (tenant-admin.html)
7. → Test, deploy, iterate on remaining pages
