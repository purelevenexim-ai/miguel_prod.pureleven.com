# 📚 Documentation Index — March 2, 2026

**Last Updated:** March 2, 2026  
**Project:** PureLevenExim CRM  
**Status:** ✅ Production Ready

---

## Quick Navigation

### 📖 Main Documentation

| File | Purpose | Length | Audience |
|------|---------|--------|----------|
| **README_MAIN.md** | Project overview, architecture, modules, completed features, deployment | 222 lines | Everyone |
| **MOBILE_CSS_v1.0_STATUS.md** | Comprehensive mobile CSS framework documentation (16 sections, 362 lines, all 15 pages) | 313 lines | Frontend developers, UI/UX teams |
| **PROJECT_STATUS_MARCH_2_2026.md** | High-level project status, completed work, deployment info, future roadmap | 304 lines | Project managers, stakeholders |
| **INDIA_POST_PHASE1_STATUS.md** | NEW: India Post API integration — Phase 1 complete, Phases 2–4 roadmap, IP whitelisting blocker | 385 lines | Shipping team, Backend devs |
| **📋 This File** | Documentation index and quick reference | — | Everyone |

---

## 🎯 What to Read

### I need to...

**Understand the project architecture**
→ Read: `README_MAIN.md` → Section: "🏗️ Architecture"

**Deploy to production**
→ Read: `README_MAIN.md` → Section: "🚀 Deploy to Production"  
→ OR: `PROJECT_STATUS_MARCH_2_2026.md` → Section: "How to Deploy"

**Understand mobile CSS framework**
→ Read: `MOBILE_CSS_v1.0_STATUS.md` (complete guide)  
→ Quick: Section "File Details" for breakpoints and coverage

**Check deployment status**
→ Read: `PROJECT_STATUS_MARCH_2_2026.md` → Section: "Deployment Information"

**See what's completed**
→ Read: `PROJECT_STATUS_MARCH_2_2026.md` → Section: "Completed Features"  
→ OR: `README_MAIN.md` → Section: "✅ Completed Features"

**Plan next steps**
→ Read: `PROJECT_STATUS_MARCH_2_2026.md` → Section: "Known Limitations & Future Work"

**Check India Post integration status**
→ Read: `INDIA_POST_PHASE1_STATUS.md` (complete — awaiting IP whitelisting)  
→ Quick: Section "Current Blocker" for what's pending

**Check browser compatibility**
→ Read: `MOBILE_CSS_v1.0_STATUS.md` → Section: "Browser Support"  
→ OR: `PROJECT_STATUS_MARCH_2_2026.md` → Section: "Testing Status"

---

## 📱 Mobile CSS v1.0 Framework Overview

**Created:** March 2, 2026  
**File:** `frontend/styles/mobile.css`  
**Size:** 361 lines  
**Sections:** 16 comprehensive CSS modules  
**Coverage:** All 15 pages  
**Status:** ✅ Deployed to production

### The 16 Sections

1. **Global Touch & Scroll** — Momentum scrolling, overflow containment
2. **Topbar** — 48px height, compact layout
3. **Toolbar / Filter Bar** — Horizontal search, 36px inputs
4. **Content Area** — Responsive padding
5. **Stat Strips & Cards** — 2-col (mobile) / 3-col (tablet) grids
6. **Tables** — Horizontal scroll, proper typography
7. **Panels & Cards** — Rounded corners, compact spacing
8. **Form Grids** — Single-column layout, 40px inputs
9. **Modals & Drawers** — Bottom-sheet pattern (88vh height)
10. **Split-Pane Layouts** — Stack vertically on mobile
11. **Horizontal Tabs** — Overflow-x scroll
12. **Pagination** — 32px buttons, proper spacing
13. **FAB** — 52px circular button, z-index: 400
14. **Empty States** — Large icons, centered layout
15. **Badges & Tags** — Compact 9px styling
16. **Print** — Hide mobile chrome

### Applied to 15 Pages

**Application Pages (13):**
- Tenant Admin, Platform Admin, Customers, Orders, Leads
- Invoices, GST, Products, Vendors, Marketing
- WhatsApp, Lead Messages, Profit & Loss

**Login Pages (2):**
- Platform Login, Tenant Login

---

## 🚀 Current Status

### Commit Hash
```
c355878 (HEAD -> main)
fix: populate mobile.css v1.0 — 16 sections, 361 lines of shared mobile styles
```

### Backup Tag
```
backup-clean-20260301 @ c355878
Use for safe rollback if needed
```

### Production Deployment
```
Server: root@172.105.48.142:/opt/pureleven
Status: ✅ LIVE
Last Deploy: March 2, 2026
```

### CSS Cache Version
```
?v=20260301
(Bumped in all 15 HTML pages)
```

---

## 📊 Statistics

| Metric | Value |
|--------|-------|
| CSS Sections | 16 |
| Pages Covered | 15 |
| Lines of Code (mobile.css) | 361 |
| Breakpoints | 3 |
| Media Queries | 12+ |
| Gzip File Size | ~3.2 KB |
| Browser Support | iOS 12+, Chrome 70+, Firefox 68+, Samsung 10+ |

---

## 🔧 Quick Commands

### Deploy Changes
```bash
ssh root@172.105.48.142 "cd /opt/pureleven && git pull origin main"
```

### Update CSS Cache
```bash
cd /opt/miguel/frontend
sed -i 's|mobile.css?v=20260301|mobile.css?v=20260302|g' *.html
git add -A && git commit -m "chore: bump mobile.css cache version"
git push origin main
```

### Rollback to Clean State
```bash
cd /opt/miguel
git reset --hard backup-clean-20260301
git push -f origin main
ssh root@172.105.48.142 "cd /opt/pureleven && git reset --hard origin/main"
```

### Check Production Status
```bash
ssh root@172.105.48.142 "cd /opt/pureleven && git log --oneline -5"
```

---

## 🎓 Framework Architecture

### CSS Cascade (Load Order)
```
1. ds.css         (Design System Tokens — colors, fonts, spacing)
2. adaptive.css   (Layout Framework — flex, grid, responsive)
3. mobile.css     (Mobile Overrides — compact, touch-optimized)
```

### Breakpoints
```
≤599px   = Compact (phones)
600-839px = Medium (tablets, landscape)
≥840px   = Expanded (desktop)
```

### Implementation
```
All mobile rules wrapped in: @media (max-width: 839px) { ... }
No desktop rules in mobile.css (clean separation)
Cache versioned: ?v=20260301
```

---

## ✅ Checklist for Developers

- [ ] Reviewed `MOBILE_CSS_v1.0_STATUS.md` for comprehensive framework guide
- [ ] Understood 16 CSS sections and their purposes
- [ ] Know how to update cache version (e.g., `?v=20260302`)
- [ ] Know how to deploy changes to production
- [ ] Know how to rollback using `backup-clean-20260301` tag
- [ ] Tested on mobile (≤599px), tablet (600–839px), and desktop (≥840px)
- [ ] Verified all 15 pages load mobile.css correctly

---

## 📞 Support & Contact

**Development:** `/opt/miguel`  
**Production:** `root@172.105.48.142:/opt/pureleven`  
**Repository:** https://github.com/purelevenexim-ai/crm  
**Branch:** `main`  

**Emergency Rollback:** `git reset --hard backup-clean-20260301`

---

## 📈 Next Phases

**Phase 2 (Planned):**
- Dark mode support
- Enhanced accessibility (WCAG 2.1 AA)
- Page transition animations
- Improved keyboard navigation

**Phase 3 (Planned):**
- Swipe gestures
- Offline support
- Service worker PWA features

**Phase 4 (Planned):**
- PWA app installation
- Custom app icons
- Splash screens

---

## 📝 Notes

- **Mobile CSS is version 1.0** — Clean state, no breaking changes
- **All 15 pages tested** on iOS, Android, Chrome, Firefox
- **Cache versioning critical** — Always bump `?v=YYYYMMDD` when updating CSS
- **Backup tag available** — `backup-clean-20260301` for quick rollback
- **Production live** — Deployed and operational as of March 2, 2026

---

**Generated:** March 2, 2026  
**Status:** ✅ **PRODUCTION READY**
