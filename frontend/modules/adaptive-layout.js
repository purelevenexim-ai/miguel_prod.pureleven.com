/**
 * Adaptive Layout Runtime  v2.0
 * ══════════════════════════════════════════════════════════════════════
 * Implements Google's Window Size Classes for the web.
 * Ref: developer.android.com/develop/ui/compose/layouts/adaptive
 *
 * v2.0 CHANGES:
 *   - apply() runs SYNCHRONOUSLY on load (fixes FOUC)
 *   - CSS now uses @media queries, not data-attributes for layout
 *   - data-attributes still set for JS consumers
 *
 * WHAT IT DOES
 * ────────────
 * 1. Computes width + height Window Size Classes (compact/medium/expanded/large/xlarge)
 * 2. Sets data-attributes on <html>: data-size-width, data-size-height
 * 3. Sets CSS classes on <html>: .size-compact, .size-medium, .size-expanded, .size-large
 * 4. Detects pixel density → data-dpr="1|2|3"
 * 5. Detects orientation → data-orientation="portrait|landscape"
 * 6. Exposes global MiguelAdaptive API
 *
 * CONSUMED BY
 * ───────────
 * - adaptive.css  → layout rules now use @media queries (CSS-first, no FOUC)
 * - mobile-nav.js → reads size class to decide bottom-nav vs rail vs drawer
 * - Any page JS   → MiguelAdaptive.onSizeClassChange(cb)
 *
 * SIZE CLASSES (matching Android exactly)
 * ───────────────────────────────────────
 * Width:  compact <600  |  medium 600-839  |  expanded 840-1199  |  large 1200-1599  |  xlarge ≥1600
 * Height: compact <480  |  medium 480-899  |  expanded ≥900
 */
(function () {
  'use strict';

  /* ── Constants ──────────────────────────────────── */
  var WIDTH_BREAKPOINTS = [
    { name: 'compact',  max: 599  },
    { name: 'medium',   max: 839  },
    { name: 'expanded', max: 1199 },
    { name: 'large',    max: 1599 },
    { name: 'xlarge',   max: Infinity }
  ];

  var HEIGHT_BREAKPOINTS = [
    { name: 'compact',  max: 479 },
    { name: 'medium',   max: 899 },
    { name: 'expanded', max: Infinity }
  ];

  var ALL_WIDTH_CLASSES = WIDTH_BREAKPOINTS.map(function (b) { return 'size-' + b.name; });
  var DEBOUNCE_MS = 100;

  /* ── State ──────────────────────────────────────── */
  var currentWidthClass  = '';
  var currentHeightClass = '';
  var listeners = [];
  var resizeTimer = null;

  /* ── Compute size class ─────────────────────────── */
  function getWidthClass(w) {
    for (var i = 0; i < WIDTH_BREAKPOINTS.length; i++) {
      if (w <= WIDTH_BREAKPOINTS[i].max) return WIDTH_BREAKPOINTS[i].name;
    }
    return 'xlarge';
  }

  function getHeightClass(h) {
    for (var i = 0; i < HEIGHT_BREAKPOINTS.length; i++) {
      if (h <= HEIGHT_BREAKPOINTS[i].max) return HEIGHT_BREAKPOINTS[i].name;
    }
    return 'expanded';
  }

  /* ── Apply classes and data attributes ──────────── */
  function apply() {
    var root = document.documentElement;
    var w = window.innerWidth;
    var h = window.innerHeight;

    var newWidth  = getWidthClass(w);
    var newHeight = getHeightClass(h);
    var changed = (newWidth !== currentWidthClass || newHeight !== currentHeightClass);

    // Width data attribute
    root.setAttribute('data-size-width', newWidth);

    // Height data attribute
    root.setAttribute('data-size-height', newHeight);

    // CSS classes — remove all, add current
    for (var i = 0; i < ALL_WIDTH_CLASSES.length; i++) {
      root.classList.remove(ALL_WIDTH_CLASSES[i]);
    }
    root.classList.add('size-' + newWidth);

    // Pixel density
    var dpr = Math.round(window.devicePixelRatio || 1);
    if (dpr > 3) dpr = 3;
    root.setAttribute('data-dpr', String(dpr));

    // Orientation
    root.setAttribute('data-orientation', w >= h ? 'landscape' : 'portrait');

    // Touch capability
    var hasTouch = ('ontouchstart' in window) || (navigator.maxTouchPoints > 0);
    root.setAttribute('data-touch', hasTouch ? 'true' : 'false');

    // Input modality
    if (hasTouch && newWidth === 'compact') {
      root.setAttribute('data-input', 'touch');
    } else if (hasTouch) {
      root.setAttribute('data-input', 'hybrid');
    } else {
      root.setAttribute('data-input', 'pointer');
    }

    // Notify listeners
    if (changed) {
      var oldWidth = currentWidthClass;
      var oldHeight = currentHeightClass;
      currentWidthClass = newWidth;
      currentHeightClass = newHeight;
      for (var j = 0; j < listeners.length; j++) {
        try {
          listeners[j]({
            widthClass: newWidth,
            heightClass: newHeight,
            prevWidthClass: oldWidth,
            prevHeightClass: oldHeight,
            width: w,
            height: h
          });
        } catch (e) {
          console.error('[AdaptiveLayout] Listener error:', e);
        }
      }
    } else {
      currentWidthClass = newWidth;
      currentHeightClass = newHeight;
    }
  }

  /* ── Debounced resize handler ───────────────────── */
  function onResize() {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(apply, DEBOUNCE_MS);
  }

  /* ── Public API ─────────────────────────────────── */
  var API = {
    /** Get current width size class */
    getWidthClass: function () { return currentWidthClass; },

    /** Get current height size class */
    getHeightClass: function () { return currentHeightClass; },

    /** Check if current width class is one of the given classes */
    isWidth: function (/* ...classes */) {
      for (var i = 0; i < arguments.length; i++) {
        if (arguments[i] === currentWidthClass) return true;
      }
      return false;
    },

    /** Check if compact width (phone) */
    isCompact: function () { return currentWidthClass === 'compact'; },

    /** Check if medium width (small tablet) */
    isMedium: function () { return currentWidthClass === 'medium'; },

    /** Check if expanded or larger (tablet landscape / desktop) */
    isExpandedOrLarger: function () {
      return currentWidthClass === 'expanded' ||
             currentWidthClass === 'large' ||
             currentWidthClass === 'xlarge';
    },

    /** Register a callback for size class changes */
    onSizeClassChange: function (fn) {
      if (typeof fn === 'function') listeners.push(fn);
    },

    /** Remove a listener */
    offSizeClassChange: function (fn) {
      listeners = listeners.filter(function (l) { return l !== fn; });
    },

    /** Force re-evaluation (call after dynamic layout changes) */
    refresh: function () { apply(); },

    /** Get all current info */
    getInfo: function () {
      return {
        widthClass: currentWidthClass,
        heightClass: currentHeightClass,
        width: window.innerWidth,
        height: window.innerHeight,
        dpr: Math.round(window.devicePixelRatio || 1),
        orientation: window.innerWidth >= window.innerHeight ? 'landscape' : 'portrait',
        touch: ('ontouchstart' in window) || (navigator.maxTouchPoints > 0)
      };
    }
  };

  /* ── Initialize ─────────────────────────────────── */
  function init() {
    window.addEventListener('resize', onResize, false);
    window.addEventListener('orientationchange', function () {
      // Orientation change needs a slight delay for viewport update
      setTimeout(apply, 150);
    }, false);

    // Also re-apply on page show (back/forward cache)
    window.addEventListener('pageshow', apply, false);
  }

  // CRITICAL: Run apply() SYNCHRONOUSLY to set data-attributes immediately.
  // This prevents any FOUC since CSS uses @media queries (not data-attributes),
  // but JS consumers (mobile-nav.v4.js etc.) still need the attributes.
  apply();

  // Defer event listener setup until DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Expose globally
  window.MiguelAdaptive = API;

})();
