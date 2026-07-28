# Miguel CRM — Adaptive UI Conversion Plan (Compose Model)

**Version:** 1.0  
**Date:** March 2026  
**Based on:** [Android Compose Adaptive Layouts](https://developer.android.com/develop/ui/compose/layouts/adaptive), [Material Design for Mobile](https://developer.android.com/design/ui/mobile), [Window Size Classes](https://developer.android.com/develop/ui/compose/layouts/adaptive/window-size-classes)

---

## 1. Executive Summary

This document outlines the complete plan to convert the Miguel CRM web application from a fixed desktop-first layout with a bolt-on mobile stylesheet into a **true adaptive-layout architecture** modeled on Google's Compose UI principles. The application will use **Window Size Classes** to dynamically detect device form-factor and adapt navigation, layout, and components in real time — just as Jetpack Compose does for Android apps.

### What Changes
- **Detection:** Runtime JavaScript module detects device pixel density, viewport width/height, orientation, and computes Window Size Classes (Compact, Medium, Expanded, Large)
- **Navigation:** Adaptive navigation switches between Bottom Nav (phone), Nav Rail (tablet), and Persistent Drawer (desktop) — exactly matching Compose's `NavigationSuiteScaffold`
- **Layouts:** Canonical layouts (List-Detail, Feed, Supporting Pane) implemented via CSS Container Queries + adaptive CSS custom properties
- **Components:** All UI components inherit adaptive tokens — they resize, reflow, and respace based on the active size class without separate "mobile.css" overrides
- **Theming:** Full Material 3 token system with light/dark mode support and `prefers-color-scheme` respect

### What Doesn't Change
- Backend API — zero changes
- Page URLs / routing — same HTML files
- Business logic JavaScript — untouched
- Git repository structure — same monorepo

---

## 2. Research Summary: Android Compose Adaptive UI

### 2.1 Window Size Classes (from Google Docs)

Google defines **opinionated viewport breakpoints** for adaptive layout:

| Class | Width Range | Typical Devices |
|-------|------------|----------------|
| **Compact** | `< 600px` | 99.96% of phones in portrait |
| **Medium** | `600px – 839px` | 93.73% of tablets in portrait |
| **Expanded** | `840px – 1199px` | 97.22% of tablets in landscape |
| **Large** | `1200px – 1599px` | Large tablet displays |
| **Extra-Large** | `≥ 1600px` | Desktop displays |

Height classes (used for landscape phone detection):

| Class | Height Range | Typical Devices |
|-------|-------------|----------------|
| **Compact** | `< 480px` | 99.78% of phones in landscape |
| **Medium** | `480px – 899px` | Tablets landscape, phones portrait |
| **Expanded** | `≥ 900px` | Tablets in portrait |

**Key principle:** Size classes are determined by *window size*, not device type. The class can change during app lifetime (orientation change, split-screen, window resize).

### 2.2 Canonical Layouts

Google defines three canonical layout patterns:

#### List-Detail (used by: Leads, Orders, Customers, WhatsApp Inbox, Lead-Messages)
- **Compact:** Single pane — list OR detail, with back navigation
- **Medium:** Split — list (40%) + detail (60%) side by side
- **Expanded:** Split — list (33%) + detail (67%) with nav rail visible

#### Feed (used by: Dashboard, Marketing Audience, Products)
- **Compact:** Single column, full-width cards
- **Medium:** 2-column grid
- **Expanded:** 3-4 column grid with varying card sizes

#### Supporting Pane (used by: GST, Profit & Loss, Marketing Filters)
- **Compact:** Supporting content below main OR in bottom sheet
- **Medium:** Main (50%) + Support (50%) side by side
- **Expanded:** Main (70%) + Support (30%)

### 2.3 Adaptive Navigation

Compose's `NavigationSuiteScaffold` automatically switches between:

| Size Class | Navigation Type | Web Implementation |
|-----------|----------------|-------------------|
| **Compact** | Bottom Navigation Bar | Fixed bottom bar with 3-5 icons |
| **Medium** | Navigation Rail | 72px left rail with icons + labels |
| **Expanded** | Persistent Navigation Drawer | 240px sidebar (current desktop layout) |

### 2.4 Material Design Principles Applied

From the Mobile Design docs:
- **Icons:** Material Symbols (variable font or SVG)
- **Themes:** Dynamic color from Material 3, light/dark support
- **Components:** Buttons, Cards, Chips, FABs, Bottom Sheets, Dialogs, Tables
- **Accessibility:** 44px touch targets, 4.5:1 contrast, semantic HTML, ARIA labels, focus management, `prefers-reduced-motion`
- **Patterns:** Predictive back, swipe gestures, pull-to-refresh, edge-to-edge content

---

## 3. Device Detection Mechanisms

### 3.1 CSS-Based Detection (Zero JS Required)

```css
/* Window Size Classes via CSS Media Queries */
@media (max-width: 599px)  { /* Compact  */ }
@media (min-width: 600px) and (max-width: 839px)  { /* Medium   */ }
@media (min-width: 840px) and (max-width: 1199px) { /* Expanded */ }
@media (min-width: 1200px) and (max-width: 1599px) { /* Large    */ }
@media (min-width: 1600px) { /* Extra-Large */ }

/* Height classes */
@media (max-height: 479px) { /* Compact height (landscape phone) */ }

/* Pixel density / DPR */
@media (min-resolution: 2dppx) { /* HiDPI / Retina */ }
@media (min-resolution: 3dppx) { /* Ultra HiDPI    */ }

/* Orientation */
@media (orientation: portrait)  { }
@media (orientation: landscape) { }

/* User preferences */
@media (prefers-color-scheme: dark)    { }
@media (prefers-reduced-motion: reduce) { }

/* Container Queries (component-level) */
@container sidebar (max-width: 200px) { }
```

### 3.2 JavaScript Runtime Detection

```javascript
// Window Size Class computation (matches Android exactly)
function getWidthSizeClass() {
  const w = window.innerWidth;
  if (w < 600)  return 'compact';
  if (w < 840)  return 'medium';
  if (w < 1200) return 'expanded';
  if (w < 1600) return 'large';
  return 'xlarge';
}

// Device pixel ratio
const dpr = window.devicePixelRatio || 1;

// Modern User-Agent Client Hints
navigator.userAgentData?.getHighEntropyValues(['mobile','platform','model'])
  .then(ua => console.log(ua));

// Reactive: listen for changes
const mq = window.matchMedia('(max-width: 599px)');
mq.addEventListener('change', e => {
  document.documentElement.dataset.sizeWidth = getWidthSizeClass();
});
```

### 3.3 Our Implementation: `adaptive-layout.js`

A single module that:
1. Computes width + height size classes on load and resize
2. Sets `data-size-width` and `data-size-height` attributes on `<html>`
3. Adds CSS classes: `.size-compact`, `.size-medium`, `.size-expanded`, `.size-large`
4. Detects pixel density and sets `data-dpr="1|2|3"`
5. Detects orientation and sets `data-orientation="portrait|landscape"`
6. Exposes a global `MiguelAdaptive` API with event callbacks
7. Works with CSS to enable adaptive navigation switching

---

## 4. Architecture: New Design System

### 4.1 File Structure

```
frontend/
├── ds.css                    # Core design tokens + base styles (UPDATED)
├── styles/
│   ├── adaptive.css          # NEW: Adaptive layout rules by size class
│   └── mobile.css            # DEPRECATED: Replaced by adaptive.css
├── modules/
│   ├── adaptive-layout.js    # NEW: Runtime size-class detection
│   ├── mobile-nav.js         # UPDATED: Now uses adaptive-layout.js API
│   └── wa-chatbox.js         # Unchanged
```

### 4.2 CSS Architecture

Instead of a single `@media (max-width: 767px)` block, we use **data-attribute selectors** driven by the JS runtime:

```css
/* Adaptive tokens — override by size class */
:root {
  --nav-width: 240px;      /* Default: Expanded (drawer) */
  --content-padding: 24px;
  --grid-columns: 4;
  --stat-columns: 4;
  --touch-target: 34px;
}

html[data-size-width="compact"] {
  --nav-width: 0px;         /* No persistent nav */
  --content-padding: 12px;
  --grid-columns: 1;
  --stat-columns: 2;
  --touch-target: 44px;
}

html[data-size-width="medium"] {
  --nav-width: 72px;        /* Nav rail */
  --content-padding: 16px;
  --grid-columns: 2;
  --stat-columns: 3;
  --touch-target: 40px;
}
```

Components consume these tokens automatically:

```css
.stats-grid {
  grid-template-columns: repeat(var(--stat-columns), 1fr);
}
.main {
  margin-left: var(--nav-width);
  padding: var(--content-padding);
}
.btn {
  min-height: var(--touch-target);
}
```

### 4.3 Adaptive Navigation Pattern

Mapping Compose's `NavigationSuiteScaffold` to web:

| Component | Compact (Phone) | Medium (Tablet) | Expanded (Desktop) |
|-----------|-----------------|-----------------|-------------------|
| **Primary Nav** | Bottom Nav (fixed, 56px) | Nav Rail (72px, left) | Drawer (240px, left) |
| **Secondary Nav** | Page tabs (h-scroll) | Page tabs | Page tabs |
| **Back Nav** | ← button / swipe | ← button | Breadcrumbs |
| **Hamburger** | Hidden (bottom nav replaces it) | Hidden (rail visible) | Hidden (drawer visible) |
| **FAB** | Bottom-right, 56px | Bottom-right, 56px | Inline button |

---

## 5. Component Inventory & Page Mapping

### 5.1 Global Components

| Component | Current | Adaptive Version |
|-----------|---------|-----------------|
| Sidebar Nav | 240px fixed drawer | Drawer → Rail → Bottom Nav |
| Topbar | 52px sticky | 52px all sizes, content adapts |
| Search | In topbar | Compact: expandable icon → full bar |
| FAB | Mobile-only | Compact+Medium: floating. Expanded: inline |
| Modals | Centered dialog | Compact: bottom sheet. Others: dialog |
| Drawers | Right slide, fixed width | Compact: 100% full-screen |
| Tables | Fixed, h-scroll on mobile | All: h-scroll with sticky first col |
| Forms | Multi-column grids | Compact: 1-col. Medium: 2-col. Expanded: 3-col |
| Toasts | Top-right | Compact: bottom-center |

### 5.2 Page → Canonical Layout Mapping

| Page | Canonical Layout | Compact | Medium | Expanded |
|------|-----------------|---------|--------|----------|
| **Dashboard** | Feed | 1-col stats | 2-col stats | 4-col stats + charts side |
| **Leads** | List-Detail | List only → tap → detail sheet | List (40%) + Detail (60%) | List (33%) + Detail (67%) |
| **Orders** | List-Detail + Form | Table only → tap → order drawer (full) | Table + drawer (split) | Table + drawer (520px) |
| **Customers** | List-Detail | Table → tap → detail overlay (full) | Table + detail (split) | Table + detail (split) |
| **Products** | Feed | 1-col table | 2-col table + modal | Full table + modal |
| **Vendors** | List-Detail | Table → tap → drawer (full) | Table + drawer (split) | Table + drawer |
| **Invoices** | Feed | Card list | 2-col cards | Full table |
| **WhatsApp** | List-Detail | Nav tabs → section full | Sidebar + section | Sidebar + section |
| **Lead-Messages** | List-Detail | Conv list OR chat (toggle) | List (40%) + Chat (60%) | List (340px) + Chat |
| **GST** | Supporting Pane | Sidebar on top → content below | Sidebar (30%) + Content (70%) | Sidebar (280px) + Content |
| **Marketing** | Supporting Pane + Feed | Filters above → content below | Filters (30%) + Content (70%) | Filters (220px) + Content |
| **Profit & Loss** | Supporting Pane | Filters stacked → charts 1-col | Filters + Charts 2-col | Full layout |
| **Platform Admin** | Feed | 1-col | 2-col | Full |

---

## 6. Implementation Plan — Phased Approach

### Phase 0: Foundation (Week 1-2)
**Goal:** Adaptive runtime + design tokens + navigation scaffold

| Task | File(s) | Effort |
|------|---------|--------|
| Create `adaptive-layout.js` | `modules/adaptive-layout.js` | 1 day |
| Create `adaptive.css` with size-class tokens | `styles/adaptive.css` | 2 days |
| Update `mobile-nav.js` → adaptive nav (bottom/rail/drawer) | `modules/mobile-nav.js` | 2 days |
| Update `ds.css` tokens for adaptive consumption | `ds.css` | 1 day |
| Add `<link>` and `<script>` to all 14 HTML files | All `.html` | 0.5 day |
| Add Material Symbols icon font | All `.html` | 0.5 day |
| Test on phone/tablet/desktop (Chrome DevTools) | — | 1 day |

**Deliverables:** All pages get adaptive detection, navigation automatically switches between bottom-nav / rail / drawer based on viewport.

### Phase 1: Core Pages (Week 3-5)
**Goal:** Convert 5 highest-traffic pages to adaptive canonical layouts

| Page | Layout Type | Effort |
|------|------------|--------|
| Leads | List-Detail | 3 days |
| Orders | List-Detail + Form | 3 days |
| Customers | List-Detail | 2 days |
| Dashboard | Feed | 2 days |
| Marketing | Supporting Pane | 2 days |

### Phase 2: Secondary Pages (Week 6-7)
**Goal:** Convert remaining pages

| Page | Layout Type | Effort |
|------|------------|--------|
| WhatsApp | List-Detail | 2 days |
| Lead-Messages | List-Detail | 2 days |
| GST | Supporting Pane | 1.5 days |
| Profit & Loss | Supporting Pane | 1 day |
| Products | Feed | 1 day |
| Vendors | List-Detail | 1.5 days |
| Invoices | Feed | 1 day |

### Phase 3: Polish & Accessibility (Week 8-9)

| Task | Effort |
|------|--------|
| Dark mode theme implementation | 2 days |
| Material Symbols icon replacement | 2 days |
| Accessibility audit (axe-core + manual) | 2 days |
| Performance optimization (lazy loading, code splitting) | 1 day |
| Touch gesture enhancements (swipe-to-go-back, pull-to-refresh) | 2 days |
| Cross-browser testing (Safari, Firefox, Samsung Browser) | 1 day |

### Phase 4: Release (Week 10)

| Task | Effort |
|------|--------|
| Staged rollout with feature flag | 1 day |
| Monitor production for regressions | 2 days |
| Documentation + handoff | 1 day |

---

## 7. Adaptive Navigation — Detailed Design

### 7.1 Bottom Navigation (Compact / Phone)

```
┌─────────────────────────────────────────┐
│ ☰ Topbar Title            🔍  👤       │
├─────────────────────────────────────────┤
│                                         │
│           Page Content                  │
│           (full width)                  │
│                                         │
├─────────────────────────────────────────┤
│  🏠    🎯    📦    📄    ⚙️            │
│ Home  Leads Orders Invoices More        │
└─────────────────────────────────────────┘
```

- 5 primary destinations in bottom nav
- "More" opens a bottom sheet with remaining nav items
- 56px height, Material 3 styling
- Active indicator: pill-shaped highlight

### 7.2 Navigation Rail (Medium / Tablet)

```
┌──┬──────────────────────────────────────┐
│  │ Topbar Title            🔍  👤      │
│🏠├──────────────────────────────────────┤
│  │                                      │
│🎯│         Page Content                 │
│  │         (beside rail)                │
│📦│                                      │
│  │                                      │
│📄│                                      │
│  │                                      │
│⚙️│                                      │
│  │                                      │
└──┴──────────────────────────────────────┘
```

- 72px wide rail with icon + small label
- Vertically centered
- FAB can sit at top of rail

### 7.3 Persistent Drawer (Expanded / Desktop)

```
┌──────────┬──────────────────────────────┐
│ Miguel   │ Topbar                       │
│ CRM      │                              │
│──────────├──────────────────────────────┤
│ Overview │                              │
│ 📊 Dash  │      Page Content            │
│ Business │      (full layout)           │
│ 🎯 Leads │                              │
│ 📦 Orders│                              │
│ 📄 Inv.  │                              │
│ ...      │                              │
│──────────│                              │
│ ⬅ Logout │                              │
└──────────┴──────────────────────────────┘
```

- Current 240px drawer layout preserved
- No changes for desktop users

---

## 8. Canonical Layout Implementation Details

### 8.1 List-Detail (Example: Leads Page)

**Compact (Phone):**
```
State A: List visible
┌─────────────────────┐
│ Topbar              │
├─────────────────────┤
│ [Stat] [Stat] [Stat]│  ← 3-col stat strip
├─────────────────────┤
│ Status filter tabs   │  ← h-scroll
├─────────────────────┤
│ Lead Row 1          │
│ Lead Row 2          │  ← Full-width list
│ Lead Row 3          │
│ ...                 │
├─────────────────────┤
│ Bottom Nav           │
└─────────────────────┘

State B: Detail visible (after tap)
┌─────────────────────┐
│ ← Back   Lead Name  │  ← Topbar changes
├─────────────────────┤
│                     │
│   Lead Detail       │  ← Full-screen sheet
│   (all fields)      │
│                     │
│   [Actions]         │
│                     │
├─────────────────────┤
│ Bottom Nav           │
└─────────────────────┘
```

**Expanded (Desktop):**
```
┌──────────┬──────────────────┬────────────────────┐
│ Sidebar  │   Lead List      │   Lead Detail      │
│ (240px)  │   (33%)          │   (67%)            │
│          │   [Stats]        │   Name, Phone...   │
│          │   [Filters]      │   [Timeline]       │
│          │   Row 1 ●        │   [Actions]        │
│          │   Row 2          │                    │
│          │   Row 3          │                    │
└──────────┴──────────────────┴────────────────────┘
```

### 8.2 Feed Layout (Example: Dashboard)

**Compact:** 1-col stats, stacked cards  
**Medium:** 2-col stats grid, 2-col report grid  
**Expanded:** 4-col stats, 2-col reports with charts

### 8.3 Supporting Pane (Example: GST)

**Compact:** Config panel stacked above data  
**Medium:** Config (40%) | Data (60%)  
**Expanded:** Config sidebar (280px) | Data (flex)

---

## 9. Theming & Tokens

### 9.1 Adaptive Tokens

```css
:root {
  /* Layout tokens — change with size class */
  --adaptive-nav-width: 240px;
  --adaptive-content-padding: 24px;
  --adaptive-grid-columns: 4;
  --adaptive-stat-columns: 4;
  --adaptive-touch-target: 34px;
  --adaptive-modal-style: dialog;      /* dialog | bottom-sheet */
  --adaptive-drawer-width: 520px;
  --adaptive-table-layout: full;       /* full | scroll */
  --adaptive-form-columns: 3;
  --adaptive-nav-type: drawer;         /* bottom-nav | rail | drawer */
}

html[data-size-width="compact"] {
  --adaptive-nav-width: 0px;
  --adaptive-content-padding: 12px;
  --adaptive-grid-columns: 1;
  --adaptive-stat-columns: 2;
  --adaptive-touch-target: 48px;
  --adaptive-modal-style: bottom-sheet;
  --adaptive-drawer-width: 100vw;
  --adaptive-table-layout: scroll;
  --adaptive-form-columns: 1;
  --adaptive-nav-type: bottom-nav;
}

html[data-size-width="medium"] {
  --adaptive-nav-width: 72px;
  --adaptive-content-padding: 16px;
  --adaptive-grid-columns: 2;
  --adaptive-stat-columns: 3;
  --adaptive-touch-target: 44px;
  --adaptive-modal-style: dialog;
  --adaptive-drawer-width: 60vw;
  --adaptive-table-layout: scroll;
  --adaptive-form-columns: 2;
  --adaptive-nav-type: rail;
}
```

### 9.2 Dark Mode

```css
@media (prefers-color-scheme: dark) {
  :root {
    --md-sys-color-background: #1f1f1f;
    --md-sys-color-surface: #2d2d2d;
    --md-sys-color-on-surface: #e8eaed;
    --md-sys-color-primary: #8ab4f8;
    --md-sys-color-primary-container: #1a3a5c;
    /* ... full dark palette */
  }
}
```

---

## 10. Accessibility Compliance

| Requirement | Implementation |
|-------------|---------------|
| Touch targets ≥ 48px (Compact), ≥ 44px (Medium) | `--adaptive-touch-target` token |
| Color contrast ≥ 4.5:1 | Verified via M3 palette generator |
| Keyboard navigation | Semantic HTML + tabindex + focus-visible |
| Screen reader support | ARIA labels, roles, live regions |
| Focus trapping in modals | JS focus-trap utility |
| Reduced motion | `@media (prefers-reduced-motion: reduce) { * { transition: none !important; animation: none !important; } }` |
| High contrast | `@media (forced-colors: active)` support |
| Font scaling | rem-based sizing, no px for text |

---

## 11. Testing Strategy

### 11.1 Device Matrix

| Device Type | Viewport | Test Method |
|-------------|----------|-------------|
| Phone portrait | 360×800 | Chrome DevTools / Real device |
| Phone landscape | 800×360 | Chrome DevTools |
| Small tablet | 600×960 | Chrome DevTools |
| Tablet portrait | 768×1024 | Chrome DevTools / iPad |
| Tablet landscape | 1024×768 | Chrome DevTools / iPad |
| Desktop | 1440×900 | Real browser |
| Wide desktop | 1920×1080 | Real browser |
| Ultra-wide | 2560×1440 | Real browser |

### 11.2 Automated Tests

- **Lighthouse:** Performance ≥ 80, Accessibility ≥ 90
- **axe-core:** Zero critical violations
- **Visual regression:** Screenshots at each breakpoint for each page
- **E2E:** Playwright tests for critical flows at Compact + Expanded

---

## 12. Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Desktop layout breaks | High | Expanded size class maps exactly to current 240px drawer layout. No changes for ≥840px users initially. |
| Performance regression from adaptive JS | Low | Module is <2KB, runs once + on resize (debounced). Zero DOM manipulation except class/attribute changes. |
| Browser compatibility | Medium | CSS data-attribute selectors work in all modern browsers. Fallback: current mobile.css remains as safety net. |
| Complex merge conflicts | Medium | Incremental approach — update one file at a time, test between each. |

---

## 13. Migration Strategy: From mobile.css to adaptive.css

### Current approach (mobile.css v5):
- Single `@media (max-width: 767px)` breakpoint
- One binary state: "mobile" or "desktop"
- ~1500 lines of `!important` overrides

### New approach (adaptive.css):
- Five size classes matching Android's specification
- Data-attribute-driven CSS with zero `!important`
- Tokens change per size class, components consume tokens
- **Backward compatible:** mobile.css continues to work as fallback during transition

### Migration path:
1. Deploy `adaptive-layout.js` → adds data attributes
2. Deploy `adaptive.css` → adds token overrides per size class
3. Incrementally move rules from `mobile.css` → `adaptive.css`
4. Once all rules migrated, deprecate `mobile.css`

---

## 14. Effort Summary

| Phase | Duration | Deliverables |
|-------|----------|-------------|
| Phase 0: Foundation | 2 weeks | Runtime, tokens, adaptive nav |
| Phase 1: Core Pages | 3 weeks | Leads, Orders, Customers, Dashboard, Marketing |
| Phase 2: Secondary Pages | 2 weeks | WA, Messages, GST, P&L, Products, Vendors, Invoices |
| Phase 3: Polish | 2 weeks | Dark mode, icons, accessibility, gestures |
| Phase 4: Release | 1 week | Rollout, monitoring, docs |
| **Total** | **~10 weeks** | Full adaptive UI |

With 1 developer focused full-time. With 2 developers: ~6 weeks.

---

## 15. Next Steps

1. ✅ Project plan approved (this document)
2. ⬜ Create `adaptive-layout.js` runtime module
3. ⬜ Create `adaptive.css` with size-class tokens
4. ⬜ Update `mobile-nav.js` for adaptive navigation
5. ⬜ Update all HTML pages with new includes
6. ⬜ Begin Phase 1: Core page conversions
7. ⬜ Accessibility audit
8. ⬜ Dark mode implementation
9. ⬜ Production rollout

---

*This plan is based on thorough research of Google's Android Compose Adaptive Layout documentation, Material Design 3 guidelines, and a complete audit of the Miguel CRM frontend codebase.*
