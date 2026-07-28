/**
 * Mobile Navigation Handler  v3
 * ─────────────────────────────
 * 1. Injects a hamburger button into the topbar on every page.
 * 2. If the page already has <aside class="sidebar">, uses it.
 * 3. If NOT, creates a full slide-out navigation sidebar so the
 *    hamburger always works — even on leads, orders, customers, etc.
 * 4. CSS (mobile.css) hides the hamburger on desktop and styles
 *    the sidebar slide-out animation.
 */
(function () {
  'use strict';

  /* ── Selectors ───────────────────────────────────── */
  function getSidebar() {
    return document.querySelector('aside.sidebar') ||
           document.querySelector('.sidebar');
  }

  function getTopbar() {
    return document.querySelector('.gs-topbar') ||
           document.querySelector('.topbar');
  }

  /* ── Navigation links (same as tenant-admin sidebar) ── */
  var NAV_ITEMS = [
    { label: 'Overview',  type: 'heading' },
    { label: '📊 Dashboard',        href: '/tenant-admin.html' },
    { label: 'Business',  type: 'heading' },
    { label: '🎯 Leads',             href: '/leads.html' },
    { label: '🧑‍💼 Customers',        href: '/customers.html' },
    { label: '📦 Orders',            href: '/orders.html' },
    { label: '📄 Invoices & Labels', href: '/invoices.html' },
    { label: '🛒 Products',          href: '/products.html' },
    { label: '🏭 Vendors',           href: '/vendors.html' },
    { label: '🧮 GST & Accounting',  href: '/gst.html' },
    { label: 'Reports',  type: 'heading' },
    { label: '� Profit Checker',    href: '/profit-loss.html' },
    { label: 'Outreach', type: 'heading' },
    { label: '📣 Marketing',         href: '/marketing.html' },
    { label: '💬 WhatsApp',          href: '/whatsapp.html' },
  ];

  /* ── Build sidebar if page doesn't have one ───────── */
  function ensureSidebar() {
    if (getSidebar()) return;

    var aside = document.createElement('aside');
    aside.className = 'sidebar mobile-injected-sidebar';

    /* Brand header */
    var brand = document.createElement('div');
    brand.className = 'brand';
    brand.innerHTML =
      '<div class="brand-icon" style="background:none;padding:0;overflow:hidden;">' +
        '<img src="/miguel_favicon.png" alt="Miguel" style="width:30px;height:30px;display:block;">' +
      '</div>' +
      '<div>' +
        '<div class="brand-name">Miguel CRM</div>' +
        '<div class="brand-slug" style="font-size:11px;color:var(--md-sys-color-outline,#888);">Menu</div>' +
      '</div>';
    aside.appendChild(brand);

    /* Nav links */
    var nav = document.createElement('nav');
    var currentPath = window.location.pathname;

    for (var i = 0; i < NAV_ITEMS.length; i++) {
      var item = NAV_ITEMS[i];
      if (item.type === 'heading') {
        var lbl = document.createElement('div');
        lbl.className = 'nav-label';
        lbl.textContent = item.label;
        nav.appendChild(lbl);
      } else {
        var a = document.createElement('a');
        a.href = item.href;
        a.textContent = item.label;
        if (currentPath === item.href) {
          a.className = 'active';
        }
        nav.appendChild(a);
      }
    }
    aside.appendChild(nav);

    /* Footer with sign-out */
    var footer = document.createElement('div');
    footer.className = 'sidebar-footer';
    footer.innerHTML =
      '<button class="btn-logout" onclick="' +
        'localStorage.clear();sessionStorage.clear();' +
        'window.location.href=\'/tenant-login.html\';"' +
      '>⬅ Sign out</button>';
    aside.appendChild(footer);

    /* Insert as first child of body so mobile.css "body > .sidebar" selectors match */
    document.body.insertBefore(aside, document.body.firstChild);
  }

  /* ── Toggle sidebar ──────────────────────────────── */
  function toggleSidebar(e) {
    if (e) { e.preventDefault(); e.stopPropagation(); }
    var sidebar = getSidebar();
    if (!sidebar) return;

    var isOpen = sidebar.classList.contains('open');
    if (isOpen) {
      sidebar.classList.remove('open');
      document.body.style.overflow = '';
    } else {
      sidebar.classList.add('open');
      document.body.style.overflow = 'hidden';
    }
  }

  function closeSidebar() {
    var sidebar = getSidebar();
    if (sidebar && sidebar.classList.contains('open')) {
      sidebar.classList.remove('open');
      document.body.style.overflow = '';
    }
  }

  /* ── Inject hamburger button ─────────────────────── */
  function injectHamburger() {
    if (document.getElementById('mobile-hamburger-btn')) return;

    var topbar = getTopbar();
    if (!topbar) return;

    var btn = document.createElement('button');
    btn.id = 'mobile-hamburger-btn';
    btn.type = 'button';
    btn.setAttribute('aria-label', 'Open navigation menu');
    btn.innerHTML = '&#9776;';

    /* Click handler (desktop browsers & fallback) */
    btn.addEventListener('click', toggleSidebar, false);

    /* Touch handler for reliable mobile taps */
    btn.addEventListener('touchend', function (e) {
      e.preventDefault();
      toggleSidebar(e);
    }, { passive: false });

    topbar.insertBefore(btn, topbar.firstChild);
  }

  /* ── Dismiss handlers ────────────────────────────── */
  function attachDismissHandlers() {
    /* Tap outside sidebar -> close */
    document.addEventListener('click', function (e) {
      var sidebar = getSidebar();
      if (!sidebar || !sidebar.classList.contains('open')) return;
      if (sidebar.contains(e.target)) return;
      if (e.target.closest('#mobile-hamburger-btn')) return;
      closeSidebar();
    }, true);

    /* Clicking a nav link -> close sidebar */
    document.addEventListener('click', function (e) {
      if (e.target.closest('.sidebar nav a')) {
        closeSidebar();
      }
    }, false);
  }

  /* ── Init ─────────────────────────────────────────── */
  function init() {
    ensureSidebar();
    injectHamburger();
    attachDismissHandlers();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();