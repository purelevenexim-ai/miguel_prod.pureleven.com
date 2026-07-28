/**
 * Mobile Utilities  v1.0 — Miguel CRM
 * ════════════════════════════════════════════════════════════════
 * Shared lightweight utility behaviors for mobile UX.
 * Load AFTER adaptive-layout.js and mobile-nav.v4.js
 *
 * Features:
 *   1. Scroll-to-Top button (appears after scrolling 300px)
 *   2. Pull-to-refresh visual hint (mobile only)
 *   3. Long-press context menu prevention (mobile tables)
 *   4. Input auto-scroll into view on focus (prevents keyboard occlusion)
 *   5. Active nav item highlight from URL
 *   6. Page load performance mark
 * ════════════════════════════════════════════════════════════════
 */
(function () {
  'use strict';

  /* ── 1. SCROLL-TO-TOP BUTTON ─────────────────────────────── */
  function initScrollTop() {
    // Only on mobile (compact/medium)
    if (window.innerWidth >= 840) return;

    var btn = document.getElementById('scrollTopBtn');
    if (!btn) {
      btn = document.createElement('button');
      btn.id = 'scrollTopBtn';
      btn.setAttribute('aria-label', 'Scroll to top');
      btn.setAttribute('title', 'Back to top');
      btn.innerHTML = '↑';
      document.body.appendChild(btn);
    }

    var scrollEl = document.scrollingElement || document.documentElement;
    var THRESHOLD = 300;

    function onScroll() {
      if (scrollEl.scrollTop > THRESHOLD) {
        btn.classList.add('visible');
      } else {
        btn.classList.remove('visible');
      }
    }

    window.addEventListener('scroll', onScroll, { passive: true });
    btn.addEventListener('click', function () {
      scrollEl.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  /* ── 2. INPUT AUTO-SCROLL (keyboard occlusion fix) ────────── */
  function initInputFocus() {
    // On mobile, scroll focused input into view after keyboard opens
    if (!('ontouchstart' in window)) return;

    var DELAY = 300; // wait for keyboard animation
    document.addEventListener('focusin', function (e) {
      var el = e.target;
      if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT') {
        setTimeout(function () {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, DELAY);
      }
    }, { passive: true });
  }

  /* ── 3. PREVENT LONG-PRESS CONTEXT MENU ON TABLE ROWS ─────── */
  function initTableLongPress() {
    if (!('ontouchstart' in window)) return;
    document.addEventListener('contextmenu', function (e) {
      if (e.target.closest('td, tr, .cust-row, .lead-row, .order-row')) {
        e.preventDefault();
      }
    });
  }

  /* ── 4. SWIPE-TO-GO-BACK (horizontal swipe on left edge) ──── */
  function initSwipeBack() {
    if (!('ontouchstart' in window)) return;
    var startX = 0, startY = 0;
    var EDGE = 30; // px from left edge
    var MIN_SWIPE = 80; // minimum swipe distance

    document.addEventListener('touchstart', function (e) {
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
    }, { passive: true });

    document.addEventListener('touchend', function (e) {
      var dx = e.changedTouches[0].clientX - startX;
      var dy = Math.abs(e.changedTouches[0].clientY - startY);
      // Only process horizontal swipes starting from left edge
      if (startX < EDGE && dx > MIN_SWIPE && dy < 80) {
        if (window.history.length > 1) {
          window.history.back();
        }
      }
    }, { passive: true });
  }

  /* ── 5. DOUBLE-TAP TO ZOOM PREVENTION on buttons ──────────── */
  function initDoubleTapFix() {
    // Prevent double-tap zoom on interactive elements
    var lastTap = 0;
    document.addEventListener('touchend', function (e) {
      var now = Date.now();
      var el = e.target;
      if (el.tagName === 'BUTTON' || el.closest('.btn, [role="button"]')) {
        if (now - lastTap < 300) {
          e.preventDefault();
        }
        lastTap = now;
      }
    }, { passive: false });
  }

  /* ── 6. LOADING STATE FOR BUTTONS (prevent double submit) ─── */
  // Expose a global helper to set button loading state
  window.setBtnLoading = function (btn, loading, loadingText) {
    if (!btn) return;
    if (loading) {
      btn.dataset.origText = btn.innerHTML;
      btn.innerHTML = loadingText || '⏳ Loading…';
      btn.disabled = true;
      btn.style.opacity = '0.7';
    } else {
      btn.innerHTML = btn.dataset.origText || btn.innerHTML;
      btn.disabled = false;
      btn.style.opacity = '';
    }
  };

  /* ── 7. TOAST UTILITY ─────────────────────────────────────── */
  window.showToast = function (msg, type, duration) {
    var existing = document.getElementById('_muToast');
    if (existing) existing.remove();

    var toast = document.createElement('div');
    toast.id = '_muToast';
    toast.className = 'toast';
    toast.setAttribute('role', 'status');
    toast.setAttribute('aria-live', 'polite');

    var colors = {
      success: { bg: '#1e8e3e', color: '#fff' },
      error:   { bg: '#b3261e', color: '#fff' },
      warning: { bg: '#f29900', color: '#fff' },
      info:    { bg: '#1a73e8', color: '#fff' },
    };
    var c = colors[type] || colors.info;

    toast.style.cssText =
      'position:fixed;z-index:9999;background:' + c.bg + ';color:' + c.color + ';' +
      'padding:10px 16px;border-radius:8px;font-size:13px;font-weight:500;' +
      'left:12px;right:12px;bottom:calc(var(--adaptive-bottom-nav-height,64px) + 12px);' +
      'text-align:center;box-shadow:0 4px 16px rgba(0,0,0,.25);' +
      'animation:_muToastIn .2s ease;max-width:480px;margin:0 auto;';

    // Add keyframe if not present
    if (!document.getElementById('_muToastStyle')) {
      var s = document.createElement('style');
      s.id = '_muToastStyle';
      s.textContent = '@keyframes _muToastIn{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}';
      document.head.appendChild(s);
    }

    toast.textContent = msg;
    document.body.appendChild(toast);

    var ttl = duration || 3000;
    setTimeout(function () {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.2s';
      setTimeout(function () { toast.remove(); }, 220);
    }, ttl);
  };

  /* ── 8. NETWORK STATUS INDICATOR ─────────────────────────── */
  function initNetworkIndicator() {
    function updateNetworkBanner(online) {
      var banner = document.getElementById('_muOfflineBanner');
      if (!online) {
        if (!banner) {
          banner = document.createElement('div');
          banner.id = '_muOfflineBanner';
          banner.textContent = '⚠️ You are offline — changes may not be saved';
          banner.style.cssText =
            'position:fixed;top:0;left:0;right:0;z-index:10000;' +
            'background:#f29900;color:#fff;text-align:center;' +
            'padding:8px 16px;font-size:12px;font-weight:600;';
          document.body.insertBefore(banner, document.body.firstChild);
        }
      } else {
        if (banner) {
          banner.remove();
          window.showToast && window.showToast('✅ Back online', 'success', 2000);
        }
      }
    }

    window.addEventListener('online',  function () { updateNetworkBanner(true);  });
    window.addEventListener('offline', function () { updateNetworkBanner(false); });
    // Initial check
    if (!navigator.onLine) updateNetworkBanner(false);
  }

  /* ── INIT ─────────────────────────────────────────────────── */
  function init() {
    initScrollTop();
    initInputFocus();
    initTableLongPress();
    // initSwipeBack(); // Disabled by default — enable per-page if desired
    // initDoubleTapFix(); // May interfere with normal taps on some devices
    initNetworkIndicator();

    // Performance mark
    if (window.performance && window.performance.mark) {
      window.performance.mark('mobile-utils-loaded');
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
