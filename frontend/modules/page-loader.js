/**
 * Page Loader  v2.0 — Miguel CRM
 * ══════════════════════════════════════════════════════════════════════
 * Shows a spinning squirrel splash screen on MOBILE page loads only.
 * On desktop (≥600px), this script does nothing — no overlay, no body
 * opacity changes, no DOM injection. FOUC is already solved by
 * adaptive.css using @media queries.
 *
 * v2.0 CHANGES:
 *   - Desktop-safe: skips entirely on screens ≥600px
 *   - Body opacity hidden via CSS @media rule (not global)
 *   - Removes injected <style> after hiding to leave zero trace
 *   - Shorter fallback timeout (2s)
 *
 * USAGE: Include this script in <head> BEFORE any stylesheets
 * ══════════════════════════════════════════════════════════════════════
 */
(function () {
  'use strict';

  /* ── Skip on desktop — FOUC is a mobile-only problem ── */
  if (window.innerWidth >= 600) {
    window.MiguelLoader = { hide: function(){}, show: function(){} };
    return;
  }

  var LOADER_ID = '__miguel-loader';
  var MIN_SHOW_MS = 400;   // minimum time loader is visible
  var FADE_MS     = 300;   // fade-out duration

  /* ── Inject loader styles into <head> immediately ── */
  var style = document.createElement('style');
  style.id = '__miguel-loader-style';
  style.textContent = [
    /* Lock body invisible — ONLY on compact screens */
    '@media(max-width:599px){body{opacity:0!important;}}',

    /* Loader overlay */
    '#' + LOADER_ID + '{',
      'position:fixed;inset:0;z-index:99999;',
      'display:flex;flex-direction:column;align-items:center;justify-content:center;',
      'background:#ffffff;',
      'transition:opacity ' + FADE_MS + 'ms ease,visibility ' + FADE_MS + 'ms ease;',
    '}',

    /* Squirrel image */
    '#' + LOADER_ID + ' .ml-img{',
      'width:80px;height:80px;',
      'border-radius:50%;',
      'object-fit:cover;',
      'animation:ml-spin 1.1s cubic-bezier(0.4,0,0.2,1) infinite;',
      'filter:drop-shadow(0 4px 12px rgba(0,0,0,0.18));',
    '}',

    /* Tagline */
    '#' + LOADER_ID + ' .ml-text{',
      'margin-top:16px;',
      'font-size:13px;font-weight:600;',
      'color:#888;',
      'letter-spacing:0.5px;',
      'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;',
    '}',

    /* Dot pulse */
    '#' + LOADER_ID + ' .ml-dots{',
      'display:inline-flex;gap:4px;margin-top:8px;',
    '}',
    '#' + LOADER_ID + ' .ml-dot{',
      'width:5px;height:5px;border-radius:50%;',
      'background:#bbb;',
      'animation:ml-pulse 1.2s ease-in-out infinite;',
    '}',
    '#' + LOADER_ID + ' .ml-dot:nth-child(2){animation-delay:0.2s;}',
    '#' + LOADER_ID + ' .ml-dot:nth-child(3){animation-delay:0.4s;}',

    /* Hidden state */
    '#' + LOADER_ID + '.ml-hidden{opacity:0;visibility:hidden;pointer-events:none;}',

    /* Spin keyframe */
    '@keyframes ml-spin{',
      '0%{transform:rotate(0deg) scale(1);}',
      '50%{transform:rotate(180deg) scale(1.08);}',
      '100%{transform:rotate(360deg) scale(1);}',
    '}',

    /* Pulse keyframe */
    '@keyframes ml-pulse{',
      '0%,100%{transform:scale(0.8);background:#ccc;}',
      '50%{transform:scale(1.2);background:#888;}',
    '}',

    /* Reduced motion */
    '@media(prefers-reduced-motion:reduce){',
      '#' + LOADER_ID + ' .ml-img{animation:none;}',
      '#' + LOADER_ID + ' .ml-dot{animation:none;}',
    '}'
  ].join('');
  document.head.appendChild(style);

  var hidden = false;

  /* ── Create the loader DOM ── */
  function buildLoader() {
    var div = document.createElement('div');
    div.id = LOADER_ID;
    div.setAttribute('aria-hidden', 'true');
    div.setAttribute('role', 'presentation');

    var img = document.createElement('img');
    img.className = 'ml-img';
    img.src = '/squirrel.png';
    img.alt = '';
    div.appendChild(img);

    var text = document.createElement('div');
    text.className = 'ml-text';
    text.textContent = 'Miguel CRM';
    div.appendChild(text);

    var dots = document.createElement('div');
    dots.className = 'ml-dots';
    for (var i = 0; i < 3; i++) {
      var dot = document.createElement('span');
      dot.className = 'ml-dot';
      dots.appendChild(dot);
    }
    div.appendChild(dots);

    return div;
  }

  /* ── Hide loader, reveal body ── */
  function hideLoader() {
    if (hidden) return;
    hidden = true;

    var loader = document.getElementById(LOADER_ID);

    /* Remove the injected style so body opacity rule is gone completely */
    var s = document.getElementById('__miguel-loader-style');
    if (s && s.parentNode) s.parentNode.removeChild(s);

    /* Reveal body immediately (style tag is gone, so opacity rule is removed) */
    if (document.body) {
      document.body.style.opacity = '1';
      /* Clear inline style after a tick so it doesn't linger */
      setTimeout(function(){ document.body.style.removeProperty('opacity'); }, 50);
    }

    if (!loader) return;

    /* Fade out loader (use inline styles since the style tag is removed) */
    loader.style.opacity = '0';
    loader.style.visibility = 'hidden';
    loader.style.pointerEvents = 'none';
    loader.style.transition = 'opacity ' + FADE_MS + 'ms ease, visibility ' + FADE_MS + 'ms ease';

    /* Remove from DOM after transition */
    setTimeout(function () {
      if (loader && loader.parentNode) {
        loader.parentNode.removeChild(loader);
      }
    }, FADE_MS + 50);
  }

  /* ── Insert loader as first child of body ── */
  function insertLoader() {
    if (document.getElementById(LOADER_ID)) return;
    var loader = buildLoader();

    if (document.body) {
      document.body.insertBefore(loader, document.body.firstChild);
    } else {
      document.addEventListener('DOMContentLoaded', function () {
        if (!hidden) {
          document.body.insertBefore(loader, document.body.firstChild);
        }
      });
    }
  }

  /* ── Main init ── */
  var startTime = Date.now();

  /* Insert loader as soon as body is available */
  if (document.body) {
    insertLoader();
  } else {
    /* Script in <head> — wait for body tag */
    var obs = new MutationObserver(function (mutations, o) {
      if (document.body) {
        o.disconnect();
        insertLoader();
      }
    });
    obs.observe(document.documentElement, { childList: true });
  }

  /* Hide after page is fully loaded + minimum display time */
  window.addEventListener('load', function () {
    var elapsed = Date.now() - startTime;
    var remaining = MIN_SHOW_MS - elapsed;
    if (remaining > 0) {
      setTimeout(hideLoader, remaining);
    } else {
      requestAnimationFrame(function () {
        requestAnimationFrame(hideLoader);
      });
    }
  });

  /* Fallback: hide after 2s no matter what */
  setTimeout(hideLoader, 2000);

  /* Expose for manual control if needed */
  window.MiguelLoader = {
    hide: hideLoader,
    show: insertLoader
  };

})();
