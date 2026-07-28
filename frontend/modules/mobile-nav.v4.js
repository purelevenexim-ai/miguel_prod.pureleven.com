/**
 * Adaptive Navigation Handler  v5.0
 * ══════════════════════════════════════════════════════════════════════
 * One canonical tenant navigation across every authenticated application page.
 *
 * v4.2 CHANGES:
 *   - Nav items match tenant-admin sidebar (Employees, Reports, Inventory,
 *     Shipping Config, etc.)
 *   - Footer shows user info (name, email, role badge) from /tenant/me
 *   - Brand slug from localStorage
 *   - Role-based visibility (Employees, Shipping hidden for non-admin)
 *
 * SIZE CLASSES:
 *   compact  → Bottom Navigation Bar (Material 3)
 *   medium   → Navigation Rail (72px left strip)
 *   expanded → Persistent Navigation Drawer (240px sidebar — existing)
 *
 * DEPENDS ON: adaptive-layout.js (must be loaded first)
 * ══════════════════════════════════════════════════════════════════════
 */
(function () {
  'use strict';

  /* ── Canonical tenant navigation schema ───────────── */
  var NAV_ITEMS = [
    { label: 'Overview',          type: 'heading' },
    { label: 'Dashboard',         href: '/tenant-admin.html',  icon: '📊', key: 'dashboard' },
    { label: 'Management',        type: 'heading', adminOnly: true },
    { label: 'Employees',         href: '/tenant-admin.html?section=employees', icon: '👥', key: 'employees', section: 'employees', adminOnly: true, elementId: 'nav-employees' },
    { label: 'Analytics',         type: 'heading' },
    { label: 'Reports',           href: '/tenant-admin.html?section=reports', icon: '📈', key: 'reports', section: 'reports' },
    { label: 'Profit & Loss',     href: '/profit-loss.html',   icon: '📉', key: 'pl' },
    { label: 'Business',          type: 'heading' },
    { label: 'Leads',             href: '/leads.html',         icon: '🎯', key: 'leads' },
    { label: 'Customers',         href: '/customers.html',     icon: '🧑‍💼', key: 'customers' },
    { label: 'Orders',            href: '/orders.html',        icon: '📦', key: 'orders' },
    { label: 'Invoices & Labels', href: '/invoices.html',      icon: '📄', key: 'invoices' },
    { label: 'Products',          href: '/products.html',      icon: '🛒', key: 'products' },
    { label: 'Vendors',           href: '/vendors.html',       icon: '🏭', key: 'vendors' },
    { label: 'Inventory',         href: '/products.html?view=inventory', icon: '🗃️', key: 'inventory', view: 'inventory' },
    { label: 'GST & Accounting',  href: '/gst.html',           icon: '🧮', key: 'gst' },
    { label: 'Outreach',          type: 'heading' },
    { label: 'Marketing',         href: '/marketing.html',     icon: '📣', key: 'marketing' },
    { label: 'Customer Retarget', href: '/customer-retarget.html', icon: '📞', key: 'customer-retarget' },
    { label: 'WhatsApp',          href: '/whatsapp.html',      icon: '💬', key: 'whatsapp' },
    { label: 'Administration',    type: 'heading', adminOnly: true },
    { label: 'Shipping Config',   href: '/tenant-admin.html?section=shipping-config', icon: '🚚', key: 'shipping', section: 'shipping-config', adminOnly: true, elementId: 'nav-shipping' },
    { label: 'Company Settings',  href: '/label-editor.html',  icon: '🎨', key: 'label-editor', adminOnly: true },
  ];

  /* Primary nav items for bottom nav (max 5: 4 main + More) */
  var BOTTOM_NAV_ITEMS = [
    { label: 'Home',     href: '/tenant-admin.html', icon: '📊', key: 'dashboard' },
    { label: 'Leads',    href: '/leads.html',        icon: '🎯', key: 'leads' },
    { label: 'Orders',   href: '/orders.html',       icon: '📦', key: 'orders' },
    { label: 'Invoices', href: '/invoices.html',     icon: '📄', key: 'invoices' },
  ];

  /* Nav items for the rail (max ~8 for vertical space) */
  var RAIL_NAV_ITEMS = [
    { label: 'Home',      href: '/tenant-admin.html', icon: '📊', key: 'dashboard' },
    { label: 'Leads',     href: '/leads.html',        icon: '🎯', key: 'leads' },
    { label: 'Customers', href: '/customers.html',    icon: '🧑‍💼', key: 'customers' },
    { label: 'Orders',    href: '/orders.html',       icon: '📦', key: 'orders' },
    { label: 'Invoices',  href: '/invoices.html',     icon: '📄', key: 'invoices' },
    { label: 'Products',  href: '/products.html',     icon: '🛒', key: 'products' },
    { label: 'Marketing', href: '/marketing.html',    icon: '📣', key: 'marketing' },
    { label: 'Retarget',  href: '/customer-retarget.html', icon: '📞', key: 'customer-retarget' },
    { label: 'WhatsApp',  href: '/whatsapp.html',     icon: '💬', key: 'whatsapp' },
  ];

  var currentPath = window.location.pathname;
  var currentParams = new URLSearchParams(window.location.search);
  var userRole = (localStorage.getItem('role') || '').toLowerCase();
  var tenantSlug = localStorage.getItem('slug') || '';

  function itemIsActive(item) {
    var target = new URL(item.href, window.location.origin);
    if (target.pathname !== currentPath) return false;
    if (item.section) return currentParams.get('section') === item.section;
    if (item.view) return currentParams.get('view') === item.view;
    if (target.pathname === '/tenant-admin.html') return !currentParams.get('section');
    if (target.pathname === '/products.html') return !currentParams.get('view');
    return true;
  }

  function activateTenantSection(item, anchor, event) {
    if (!item.section || currentPath !== '/tenant-admin.html' || typeof window.go !== 'function') return;
    event.preventDefault();
    window.history.replaceState({}, '', item.href);
    currentParams = new URLSearchParams(window.location.search);
    window.go(item.section, anchor);
  }

  /* ── Selectors ─────────────────────────────────────── */
  function getSidebar() {
    return document.querySelector('aside.sidebar') ||
           document.querySelector('.sidebar') ||
           document.querySelector('aside.mobile-injected-sidebar');
  }

  /* ── Build or normalize the canonical sidebar ─────── */
  function ensureSidebar() {
    var aside = getSidebar();
    var isInjected = !aside;
    document.body.classList.add('canonical-nav-ready');
    if (!aside) {
      document.body.classList.add('nav-injected');
      aside = document.createElement('aside');
      document.body.insertBefore(aside, document.body.firstChild);
    }
    aside.className = 'sidebar mobile-injected-sidebar canonical-sidebar';
    aside.setAttribute('aria-label', 'Application navigation');
    aside.setAttribute('data-canonical-nav', 'true');
    aside.innerHTML = '';

    /* Brand header — shows tenant slug */
    var brand = document.createElement('div');
    brand.className = 'brand';
    brand.innerHTML =
      '<div class="brand-icon" style="background:none;padding:0;overflow:hidden;">' +
        '<img src="/miguel_favicon.png" alt="Miguel" style="width:30px;height:30px;display:block;">' +
      '</div>' +
      '<div>' +
        '<div class="brand-name">Miguel CRM</div>' +
        '<div class="brand-slug" id="sidebarSlug">' +
          (tenantSlug ? tenantSlug.toUpperCase() : 'Menu') +
        '</div>' +
      '</div>';
    aside.appendChild(brand);

    /* Nav links — matches tenant-admin.html sidebar */
    var nav = document.createElement('nav');
    nav.id = 'sideNav';

    for (var i = 0; i < NAV_ITEMS.length; i++) {
      var item = NAV_ITEMS[i];

      /* Skip admin-only items for non-admin users */
      if (item.adminOnly && userRole !== 'admin') continue;

      if (item.type === 'heading') {
        var lbl = document.createElement('div');
        lbl.className = 'nav-label';
        if (item.label === 'Management') lbl.id = 'nav-mgmt-label';
        lbl.textContent = item.label;
        nav.appendChild(lbl);
      } else {
        var a = document.createElement('a');
        a.href = item.href;
        a.innerHTML = '<span class="canonical-nav-icon">' + item.icon + '</span><span>' + item.label + '</span>';
        a.dataset.navKey = item.key;
        if (item.elementId) a.id = item.elementId;
        if (itemIsActive(item)) {
          a.className = 'active';
          a.setAttribute('aria-current', 'page');
        }
        a.addEventListener('click', activateTenantSection.bind(null, item, a));
        nav.appendChild(a);
      }
    }
    aside.appendChild(nav);

    /* Footer with user info + sign-out — matches tenant-admin sidebar */
    var footer = document.createElement('div');
    footer.className = 'sidebar-footer';

    var userInfo = document.createElement('div');
    userInfo.className = 'user-info';
    var nameEl = document.createElement('strong');
    nameEl.id = 'nav-empName';
    nameEl.textContent = tenantSlug || '—';
    var emailEl = document.createElement('span');
    emailEl.id = 'nav-empEmail';
    emailEl.textContent = '';
    var roleEl = document.createElement('span');
    roleEl.className = 'role-badge';
    roleEl.id = 'nav-empRole';
    roleEl.textContent = userRole ? userRole.toUpperCase() : '';

    userInfo.appendChild(nameEl);
    userInfo.appendChild(emailEl);
    if (userRole) userInfo.appendChild(roleEl);
    footer.appendChild(userInfo);

    var logoutBtn = document.createElement('button');
    logoutBtn.className = 'btn-logout';
    logoutBtn.textContent = '⬅ Sign out';
    logoutBtn.onclick = function () {
      localStorage.clear();
      sessionStorage.clear();
      window.location.href = '/tenant-login.html';
    };
    footer.appendChild(logoutBtn);
    aside.appendChild(footer);

    /* Fetch user profile to fill in name + email */
    loadNavUserProfile();
    return isInjected;
  }

  /* ── Fetch /tenant/me to fill sidebar user info ────── */
  function loadNavUserProfile() {
    var token = localStorage.getItem('token');
    if (!token) return;
    try {
      var xhr = new XMLHttpRequest();
      xhr.open('GET', '/tenant/me', true);
      xhr.setRequestHeader('Authorization', 'Bearer ' + token);
      xhr.setRequestHeader('Content-Type', 'application/json');
      xhr.onload = function () {
        if (xhr.status === 200) {
          try {
            var u = JSON.parse(xhr.responseText);
            var nameEl = document.getElementById('nav-empName');
            var emailEl = document.getElementById('nav-empEmail');
            var roleEl = document.getElementById('nav-empRole');
            if (nameEl && u.full_name) nameEl.textContent = u.full_name;
            if (emailEl && u.email) emailEl.textContent = u.email;
            if (roleEl && u.role) roleEl.textContent = String(u.role).toUpperCase();
          } catch (_) {}
        }
      };
      xhr.send();
    } catch (_) {}
  }

  /* ── Build Bottom Navigation Bar ─────────────────── */
  function createBottomNav() {
    if (document.querySelector('.adaptive-bottom-nav')) return;

    var nav = document.createElement('nav');
    nav.className = 'adaptive-bottom-nav';
    nav.setAttribute('role', 'navigation');
    nav.setAttribute('aria-label', 'Primary navigation');

    var items = document.createElement('div');
    items.className = 'adaptive-bottom-nav-items';

    // Primary items
    for (var i = 0; i < BOTTOM_NAV_ITEMS.length; i++) {
      var item = BOTTOM_NAV_ITEMS[i];
      var a = document.createElement('a');
      a.href = item.href;
      a.className = 'adaptive-bottom-nav-item' + (itemIsActive(item) ? ' active' : '');
      a.setAttribute('aria-label', item.label);
      a.innerHTML =
        '<span class="nav-icon">' + item.icon + '</span>' +
        '<span class="nav-label">' + item.label + '</span>';
      items.appendChild(a);
    }

    // "More" button → opens sidebar slideover
    var more = document.createElement('button');
    more.className = 'adaptive-bottom-nav-item';
    more.type = 'button';
    more.setAttribute('aria-label', 'More navigation options');
    more.innerHTML =
      '<span class="nav-icon">☰</span>' +
      '<span class="nav-label">More</span>';
    more.addEventListener('click', function (e) {
      e.preventDefault();
      toggleSidebar();
    });
    items.appendChild(more);

    nav.appendChild(items);
    document.body.appendChild(nav);
  }

  /* ── Build Navigation Rail ───────────────────────── */
  function createNavRail() {
    if (document.querySelector('.adaptive-nav-rail')) return;

    var rail = document.createElement('nav');
    rail.className = 'adaptive-nav-rail';
    rail.setAttribute('role', 'navigation');
    rail.setAttribute('aria-label', 'Primary navigation');

    // Brand icon at top
    var brand = document.createElement('div');
    brand.className = 'adaptive-nav-rail-brand';
    brand.innerHTML = '<img src="/miguel_favicon.png" alt="Miguel CRM">';
    rail.appendChild(brand);

    // Items
    var items = document.createElement('div');
    items.className = 'adaptive-nav-rail-items';

    for (var i = 0; i < RAIL_NAV_ITEMS.length; i++) {
      var item = RAIL_NAV_ITEMS[i];
      var a = document.createElement('a');
      a.href = item.href;
      a.className = 'adaptive-nav-rail-item' + (itemIsActive(item) ? ' active' : '');
      a.setAttribute('aria-label', item.label);
      a.innerHTML =
        '<span class="nav-icon">' + item.icon + '</span>' +
        '<span class="nav-label">' + item.label + '</span>';
      items.appendChild(a);
    }

    rail.appendChild(items);
    document.body.appendChild(rail);
  }

  /* ── Toggle sidebar (slideover for "More" menu) ──── */
  function toggleSidebar(e) {
    if (e) { e.preventDefault(); e.stopPropagation(); }
    var sidebar = getSidebar();
    if (!sidebar) return;

    var isOpen = sidebar.classList.contains('open');
    if (isOpen) {
      closeSidebar();
    } else {
      sidebar.classList.add('open');
      document.body.style.overflow = 'hidden';
      ensureSidebarOverlay();
    }
  }

  function closeSidebar() {
    var sidebar = getSidebar();
    if (sidebar && sidebar.classList.contains('open')) {
      sidebar.classList.remove('open');
      document.body.style.overflow = '';
    }
    var overlay = document.querySelector('.adaptive-sidebar-overlay');
    if (overlay) overlay.classList.remove('open');
  }

  /* Overlay: CSS-only styling, no inline styles, no blur */
  function ensureSidebarOverlay() {
    var overlay = document.querySelector('.adaptive-sidebar-overlay');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.className = 'adaptive-sidebar-overlay';
      overlay.addEventListener('click', closeSidebar);
      document.body.appendChild(overlay);
    }
    overlay.classList.add('open');
  }

  /* ── Dismiss handlers ────────────────────────────── */
  function attachDismissHandlers() {
    document.addEventListener('click', function (e) {
      var sidebar = getSidebar();
      if (!sidebar || !sidebar.classList.contains('open')) return;
      if (sidebar.contains(e.target)) return;
      if (e.target.closest('.adaptive-bottom-nav-item')) return;
      closeSidebar();
    }, true);

    document.addEventListener('click', function (e) {
      if (e.target.closest('.sidebar nav a')) {
        closeSidebar();
      }
    }, false);
  }

  /* ── Init ─────────────────────────────────────────── */
  function init() {
    if (currentPath === '/platform-admin.html' || currentPath === '/platform-login.html') return;

    // Build all navigation variants (CSS controls visibility)
    ensureSidebar();
    createBottomNav();
    createNavRail();

    // Open deep-linked dashboard sections after the canonical sidebar exists.
    var initialSection = currentParams.get('section');
    if (currentPath === '/tenant-admin.html' && initialSection && typeof window.go === 'function') {
      var sectionLink = document.querySelector('.canonical-sidebar [data-nav-key="' + initialSection.replace('-config', '') + '"]');
      if (!sectionLink && initialSection === 'shipping-config') {
        sectionLink = document.querySelector('.canonical-sidebar [data-nav-key="shipping"]');
      }
      window.go(initialSection, sectionLink);
    }
    // NO hamburger injection — bottom nav "More" replaces it
    attachDismissHandlers();

    // Clean up sidebar state on bfcache restore (mobile Safari)
    window.addEventListener('pageshow', function (e) {
      if (e.persisted) { closeSidebar(); }
    });

    // Listen for size class changes (reserved for future use)
    if (window.MiguelAdaptive) {
      window.MiguelAdaptive.onSizeClassChange(function () {});
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
