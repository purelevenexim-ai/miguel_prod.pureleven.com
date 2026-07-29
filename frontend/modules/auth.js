/**
 * Miguel CRM — Shared Auth & Session Module
 * ─────────────────────────────────────────
 * Handles:
 *   • Token retrieval & validation
 *   • Role-based page guards
 *   • Unified logout (clears all storage)
 *   • Auth headers helper
 *   • Session expiry detection (401 → popup + redirect to login)
 *   • Auth-aware fetch wrapper
 *   • Global fetch interceptor — catches ALL 401/4xx/5xx automatically
 *   • Global JS error handler — catches unhandled errors & promise rejections
 *
 * Usage:
 *   <script src="/modules/auth.js"></script>
 *   Then call:  MiguelAuth.guard('tenant')   — on tenant pages
 *               MiguelAuth.guard('platform') — on platform pages
 *               MiguelAuth.guard('any')      — any logged-in user
 *
 * Error coverage:
 *   401 Unauthorized     → Session-expired popup + redirect to login
 *   403 Forbidden        → Toast: "Access denied"
 *   404 Not Found        → Toast: "Not found"
 *   422 Validation       → Toast: validation detail message
 *   429 Rate Limit       → Toast: "Too many requests"
 *   4xx Other            → Toast: error detail from response body
 *   500 Server Error     → Modal popup: "Server error, try again"
 *   502/503/504          → Modal popup: "Service unavailable"
 *   5xx Other            → Modal popup: server error
 *   JS TypeError etc.    → Toast: error message (unhandled errors)
 *   Unhandled rejection  → Toast: rejection reason
 */
(function(w) {
  'use strict';

  const STORAGE_KEYS = ['token', 'type', 'role', 'slug', 'user_id', 'email', 'tenant_token'];
  const LOGIN_ROUTES = {
    tenant:   '/tenant-login.html',
    platform: '/platform-login.html',
    any:      '/tenant-login.html',
  };

  /** Get a value from localStorage (with optional sessionStorage fallback) */
  function get(key) {
    return localStorage.getItem(key) || sessionStorage.getItem(key) || null;
  }

  /** Clear all auth-related storage (does NOT redirect) */
  function clearAuth() {
    STORAGE_KEYS.forEach(k => {
      localStorage.removeItem(k);
      sessionStorage.removeItem(k);
    });
  }

  /** Clear all auth-related storage and redirect to login */
  function logout(type) {
    clearAuth();
    const dest = LOGIN_ROUTES[type || get('type') || 'tenant'];
    w.location.replace(dest);
  }

  // ═══════════════════════════════════════════════════════════════
  // TOAST NOTIFICATION (4xx, JS errors, info, success)
  // ═══════════════════════════════════════════════════════════════

  // Inject toast styles once
  function _ensureToastStyles() {
    if (document.getElementById('_crmToastStyle')) return;
    const s = document.createElement('style');
    s.id = '_crmToastStyle';
    s.textContent = `
      #_crmToastContainer {
        position: fixed;
        top: 18px;
        right: 18px;
        z-index: 999990;
        display: flex;
        flex-direction: column;
        gap: 8px;
        max-width: 360px;
        pointer-events: none;
      }
      ._crmToast {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        padding: 13px 16px;
        border-radius: 10px;
        font-family: Inter, system-ui, sans-serif;
        font-size: 13px;
        line-height: 1.45;
        color: #fff;
        box-shadow: 0 4px 20px rgba(0,0,0,0.18);
        pointer-events: all;
        animation: _crmToastIn .22s ease;
        cursor: pointer;
        min-width: 260px;
        word-break: break-word;
      }
      ._crmToast._crmToastErr  { background: #c0392b; }
      ._crmToast._crmToastWarn { background: #b06000; }
      ._crmToast._crmToastOk   { background: #1a7f4f; }
      ._crmToast._crmToastInfo { background: #1d4ed8; }
      ._crmToast ._crmToastIcon { font-size: 16px; flex-shrink: 0; margin-top: 1px; }
      ._crmToast ._crmToastMsg  { flex: 1; }
      ._crmToast ._crmToastClose {
        font-size: 16px; opacity: .75; flex-shrink: 0;
        cursor: pointer; background: none; border: none; color: #fff; padding: 0;
      }
      @keyframes _crmToastIn {
        from { opacity: 0; transform: translateX(24px); }
        to   { opacity: 1; transform: translateX(0); }
      }
    `;
    document.head.appendChild(s);
  }

  function _getToastContainer() {
    let c = document.getElementById('_crmToastContainer');
    if (!c) {
      c = document.createElement('div');
      c.id = '_crmToastContainer';
      document.body.appendChild(c);
    }
    return c;
  }

  /**
   * Show a toast notification.
   * @param {string} msg      Message text
   * @param {'err'|'warn'|'ok'|'info'} type
   * @param {number} duration ms before auto-dismiss (0 = sticky)
   */
  function toast(msg, type, duration) {
    if (!msg) return;
    type     = type     || 'err';
    duration = (duration === undefined) ? (type === 'err' ? 6000 : 3500) : duration;

    _ensureToastStyles();
    const container = _getToastContainer();

    const icons = { err: '❌', warn: '⚠️', ok: '✅', info: 'ℹ️' };
    const cls   = { err: '_crmToastErr', warn: '_crmToastWarn', ok: '_crmToastOk', info: '_crmToastInfo' };

    const el = document.createElement('div');
    el.className = `_crmToast ${cls[type] || cls.err}`;
    el.innerHTML = `
      <span class="_crmToastIcon">${icons[type] || '❌'}</span>
      <span class="_crmToastMsg">${_esc(String(msg))}</span>
      <button class="_crmToastClose" title="Dismiss">✕</button>
    `;

    function dismiss() {
      el.style.opacity = '0';
      el.style.transition = 'opacity 0.2s';
      setTimeout(() => el.remove(), 220);
    }

    el.querySelector('._crmToastClose').addEventListener('click', dismiss);
    el.addEventListener('click', dismiss);

    container.appendChild(el);
    if (duration > 0) setTimeout(dismiss, duration);
  }

  // ═══════════════════════════════════════════════════════════════
  // SERVER ERROR MODAL (5xx)
  // ═══════════════════════════════════════════════════════════════

  let _serverErrorShown = false;

  function showServerError(status, detail) {
    // Deduplicate — only one modal per page load
    if (_serverErrorShown) { toast(detail || `Server error (${status})`, 'err'); return; }
    _serverErrorShown = true;
    setTimeout(() => { _serverErrorShown = false; }, 8000); // reset after 8s

    const overlay = document.createElement('div');
    overlay.id = '_crmServerErrOverlay';
    overlay.style.cssText = 'position:fixed;inset:0;z-index:99998;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;font-family:Inter,system-ui,sans-serif;';

    const icon = status >= 502 ? '🔌' : '💥';
    const title = status === 500 ? 'Server Error'
                : status === 502 ? 'Bad Gateway'
                : status === 503 ? 'Service Unavailable'
                : status === 504 ? 'Gateway Timeout'
                : `Server Error (${status})`;
    const hint = status >= 502
      ? 'The server is temporarily unavailable. Please wait a moment and try again.'
      : 'An unexpected server error occurred. Please try again or contact support if this persists.';

    overlay.innerHTML = `
      <div style="background:#fff;border-radius:14px;padding:32px 36px;max-width:420px;width:92%;
                  box-shadow:0 12px 48px rgba(0,0,0,0.22);text-align:center;">
        <div style="font-size:38px;margin-bottom:10px;">${icon}</div>
        <div style="font-size:17px;font-weight:700;color:#111;margin-bottom:6px;">${title}</div>
        <div style="font-size:13px;color:#555;margin-bottom:6px;line-height:1.5;">${hint}</div>
        ${detail ? `<div style="font-size:12px;color:#e53e3e;background:#fff5f5;border:1px solid #fecaca;border-radius:6px;padding:8px 12px;margin:10px 0;text-align:left;word-break:break-word;">${_esc(detail)}</div>` : ''}
        <div style="display:flex;gap:10px;margin-top:20px;justify-content:center;">
          <button id="_crmSrvErrClose"
            style="padding:9px 24px;border-radius:8px;border:1px solid #ddd;background:#f5f5f5;cursor:pointer;font-size:13px;font-weight:600;">
            Dismiss
          </button>
          <button id="_crmSrvErrRetry"
            style="padding:9px 24px;border-radius:8px;border:none;background:#2563eb;color:#fff;cursor:pointer;font-size:13px;font-weight:600;">
            Retry Page
          </button>
        </div>
      </div>`;

    document.body.appendChild(overlay);

    overlay.querySelector('#_crmSrvErrClose').addEventListener('click', () => {
      overlay.remove();
    });
    overlay.querySelector('#_crmSrvErrRetry').addEventListener('click', () => {
      w.location.reload();
    });
  }

  // ═══════════════════════════════════════════════════════════════
  // SESSION-EXPIRED MODAL (401)
  // ═══════════════════════════════════════════════════════════════

  let _sessionExpiredShown = false;

  function sessionExpired() {
    if (_sessionExpiredShown) return;
    _sessionExpiredShown = true;

    clearAuth();

    const overlay = document.createElement('div');
    overlay.id = '_crmAuthExpiredOverlay';
    overlay.style.cssText = 'position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,0.55);display:flex;align-items:center;justify-content:center;font-family:Inter,system-ui,sans-serif;';

    overlay.innerHTML = `
      <div style="background:#fff;border-radius:14px;padding:36px 40px;max-width:400px;width:90%;
                  box-shadow:0 12px 48px rgba(0,0,0,0.22);text-align:center;">
        <div style="font-size:40px;margin-bottom:12px;">🔒</div>
        <div style="font-size:18px;font-weight:700;color:#111;margin-bottom:8px;">Session Expired</div>
        <div style="font-size:14px;color:#555;margin-bottom:24px;line-height:1.5;">
          Your session has expired or is no longer valid.<br>
          Please log in again to continue.
        </div>
        <div style="font-size:12px;color:#999;margin-bottom:20px;" id="_crmAuthCountdown">
          Redirecting in <b>3</b>s…
        </div>
        <button id="_crmAuthLoginBtn"
          style="padding:10px 28px;border-radius:8px;border:none;background:#2563eb;color:#fff;
                 font-size:14px;font-weight:600;cursor:pointer;width:100%;">
          Log In Now
        </button>
      </div>`;

    document.body.appendChild(overlay);

    const loginDest = LOGIN_ROUTES[get('type') || 'tenant'];
    let secs = 3;
    const cdEl = overlay.querySelector('#_crmAuthCountdown b');
    const tick = setInterval(() => {
      secs--;
      if (cdEl) cdEl.textContent = secs;
      if (secs <= 0) { clearInterval(tick); w.location.replace(loginDest); }
    }, 1000);

    overlay.querySelector('#_crmAuthLoginBtn').addEventListener('click', () => {
      clearInterval(tick);
      w.location.replace(loginDest);
    });
  }

  // ═══════════════════════════════════════════════════════════════
  // GLOBAL FETCH INTERCEPTOR
  // Intercepts every fetch() call on every page automatically.
  // ═══════════════════════════════════════════════════════════════

  (function installFetchInterceptor() {
    const _orig = w.fetch.bind(w);
    const LOGIN_PAGES = ['/tenant-login.html', '/platform-login.html'];

    // Status-to-user-friendly message map
    function _statusMsg(status) {
      if (status === 400) return 'Bad request — please check your input.';
      if (status === 403) return 'Access denied. You don\'t have permission for this action.';
      if (status === 404) return 'Not found — the requested resource does not exist.';
      if (status === 409) return 'Conflict — this item may already exist.';
      if (status === 413) return 'File too large — please reduce the size and try again.';
      if (status === 422) return null;  // show server detail instead
      if (status === 429) return 'Too many requests — please slow down and try again.';
      if (status >= 400 && status < 500) return `Request failed (${status}).`;
      return null;
    }

    w.fetch = async function(...args) {
      const currentPath = w.location.pathname;
      const onLoginPage = LOGIN_PAGES.some(p => currentPath.endsWith(p));

      let response;
      try {
        response = await _orig(...args);
      } catch (networkErr) {
        // Network failure (offline, DNS failure, etc.)
        if (!onLoginPage) {
          toast('Network error — check your connection and try again.', 'warn');
        }
        throw networkErr;
      }

      if (onLoginPage) return response;

      const s = response.status;

      // ── 401: Session expired ────────────────────────────────
      if (s === 401) {
        if (get('token')) { sessionExpired(); }
        else { w.location.replace(LOGIN_ROUTES[get('type') || 'tenant']); }
        return response;
      }

      // ── 5xx: Server errors → modal popup ────────────────────
      if (s >= 500) {
        // Try to get detail from body (clone to avoid consuming it)
        let detail = '';
        try {
          const clone = response.clone();
          const body  = await clone.json().catch(() => null);
          detail = (body && (body.detail || body.message || body.error)) || '';
        } catch(_) {}
        showServerError(s, detail);
        return response;
      }

      // ── 4xx: Client errors → toast ───────────────────────────
      if (s >= 400 && s < 500) {
        // 401 already handled above; skip 304 etc.
        let detail = _statusMsg(s);
        if (!detail || s === 422) {
          // Pull detail from response body
          try {
            const clone = response.clone();
            const body  = await clone.json().catch(() => null);
            if (body) {
              // FastAPI validation errors have body.detail as array
              if (Array.isArray(body.detail)) {
                detail = body.detail.map(d => d.msg || JSON.stringify(d)).join('; ');
              } else {
                detail = body.detail || body.message || body.error || detail || `Error ${s}`;
              }
            } else {
              detail = detail || `Error ${s}`;
            }
          } catch(_) { detail = detail || `Error ${s}`; }
        }
        toast(detail, 'err');
        return response;
      }

      return response;
    };
  })();

  // ═══════════════════════════════════════════════════════════════
  // GLOBAL JS ERROR HANDLERS
  // Catches unhandled synchronous errors and promise rejections.
  // ═══════════════════════════════════════════════════════════════

  (function installErrorHandlers() {
    const LOGIN_PAGES = ['/tenant-login.html', '/platform-login.html'];
    function onLoginPage() {
      return LOGIN_PAGES.some(p => w.location.pathname.endsWith(p));
    }

    // Unhandled synchronous JS errors
    const _prevOnerror = w.onerror;
    w.onerror = function(msg, src, line, col, err) {
      if (!onLoginPage()) {
        // Ignore cross-origin script errors (no useful info available)
        if (msg === 'Script error.' || msg === 'Script error') {
          if (_prevOnerror) return _prevOnerror.apply(this, arguments);
          return false;
        }
        const text = (err && err.message) ? err.message : String(msg);
        // Don't show toasts for errors we already handle via fetch interceptor
        if (!text.includes('Session expired')) {
          toast('Unexpected error: ' + text, 'err', 7000);
        }
      }
      if (_prevOnerror) return _prevOnerror.apply(this, arguments);
      return false;
    };

    // Unhandled promise rejections
    w.addEventListener('unhandledrejection', function(event) {
      if (onLoginPage()) return;
      const reason = event.reason;
      let msg = '';
      if (reason instanceof Error) {
        msg = reason.message;
      } else if (typeof reason === 'string') {
        msg = reason;
      } else if (reason && reason.detail) {
        msg = reason.detail;
      } else {
        return; // unknown shape, skip
      }
      // Skip 401 session errors (already handled) and abort errors
      if (!msg || msg.includes('Session expired') || msg.includes('AbortError') || msg.toLowerCase().includes('abort')) return;
      toast('Unhandled error: ' + msg, 'err', 7000);
    });
  })();

  // ═══════════════════════════════════════════════════════════════
  // HELPER — also replaces native alert() on non-login pages
  // ═══════════════════════════════════════════════════════════════

  (function patchAlert() {
    const LOGIN_PAGES = ['/tenant-login.html', '/platform-login.html'];
    // Only patch after DOM is ready, so login pages still work
    function maybePatch() {
      if (LOGIN_PAGES.some(p => w.location.pathname.endsWith(p))) return;
      const _origAlert = w.alert.bind(w);
      w.alert = function(msg) {
        // Show as toast instead of blocking dialog
        toast(String(msg || ''), 'info', 6000);
      };
    }
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', maybePatch);
    } else {
      maybePatch();
    }
  })();

  // ═══════════════════════════════════════════════════════════════
  // PAGE GUARD
  // ═══════════════════════════════════════════════════════════════

  function guard(requiredType) {
    const token = get('token');
    const type  = get('type');
    if (!token) {
      w.location.replace(LOGIN_ROUTES[requiredType]);
      return false;
    }
    if (requiredType !== 'any' && type !== requiredType) {
      w.location.replace(LOGIN_ROUTES[requiredType]);
      return false;
    }
    return true;
  }

  // ═══════════════════════════════════════════════════════════════
  // AUTH HEADERS & API WRAPPER
  // ═══════════════════════════════════════════════════════════════

  function headers() {
    const token = get('token');
    return {
      'Authorization': token ? `Bearer ${token}` : '',
      'Content-Type':  'application/json',
    };
  }

  async function api(method, path, body) {
    const opts = { method, headers: headers() };
    if (body !== undefined) opts.body = JSON.stringify(body);
    return fetch(path, opts); // fetch is already intercepted
  }

  function isLoggedIn() { return !!get('token'); }

  function user() {
    return {
      token: get('token'),
      type:  get('type'),
      role:  get('role'),
      slug:  get('slug'),
      email: get('email'),
    };
  }

  // ── Utility ────────────────────────────────────────────────────
  function _esc(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // Expose globally
  w.MiguelAuth = { guard, logout, sessionExpired, toast, headers, api, isLoggedIn, user, get };

  // Also expose toast as global CRMToast for convenience
  w.CRMToast = toast;

})(window);
