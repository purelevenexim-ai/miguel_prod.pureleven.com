#!/usr/bin/env python3
"""
Miguel CRM — Comprehensive Session/Cache/Auth Fix Script
=========================================================
Fixes:
  1. Cache-Control meta tags on all pages (prevent stale auth state)
  2. CSS versioning — all pages use consistent version
  3. auth.js loaded before page scripts on all pages
  4. logout() function added to all pages that are missing it
  5. api() / apiFetch() improved to handle 401 → auto logout
  6. invoices.html: fix relative CSS path ds.css → /ds.css
  7. Standardize token retrieval patterns
  8. whatsapp.html / lead-messages.html: remove sessionStorage/tenant_token fallbacks
"""

import re
import os

FRONTEND = '/opt/miguel/frontend'
CSS_VERSION = '20260228'

# ── Cache-Control meta block ──────────────────────────────────────────────────
CACHE_META = (
    '<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">\n'
    '<meta http-equiv="Pragma" content="no-cache">\n'
    '<meta http-equiv="Expires" content="0">\n'
)

# ── auth.js script tag ────────────────────────────────────────────────────────
AUTH_JS_TAG = '<script src="/modules/auth.js"></script>\n'

def read(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'  ✅ Written: {os.path.basename(path)}')

# ── 1. Add Cache-Control meta (if not present) ────────────────────────────────
def add_cache_meta(html, filename):
    if 'Cache-Control' in html:
        return html  # already has it
    # Insert after <meta name="viewport"...> line
    html = re.sub(
        r'(<meta name="viewport"[^>]*>)',
        r'\1\n' + CACHE_META.rstrip('\n'),
        html
    )
    print(f'    + cache-meta added to {filename}')
    return html

# ── 2. Fix CSS versions ───────────────────────────────────────────────────────
def fix_css_versions(html, filename):
    # Fix ds.css — all variants: ds.css, /ds.css, ds.css?v=..., /ds.css?v=...
    # Also fix relative path (no leading /) 
    new_html = re.sub(
        r'href=["\']/?ds\.css(?:\?v=[^"\']*)?["\']',
        f'href="/ds.css?v={CSS_VERSION}"',
        html
    )
    # Fix mobile.css
    new_html = re.sub(
        r'href=["\']/?styles/mobile\.css(?:\?v=[^"\']*)?["\']',
        f'href="/styles/mobile.css?v={CSS_VERSION}"',
        new_html
    )
    if new_html != html:
        print(f'    + css versions fixed in {filename}')
    return new_html

# ── 3. Add auth.js script tag (if not present) ────────────────────────────────
def add_auth_js(html, filename):
    if '/modules/auth.js' in html:
        return html
    # Insert just before the first <script> tag (inline scripts)
    # But after the last <link> stylesheet
    # Strategy: add right before </head> or before first <script>
    # We want it before the first inline <script> block
    html = re.sub(
        r'(<script>)',
        AUTH_JS_TAG + r'\1',
        html,
        count=1  # only first occurrence
    )
    print(f'    + auth.js script tag added to {filename}')
    return html

# ── 4. Add logout function (if missing) ──────────────────────────────────────
LOGOUT_TENANT = """
function logout() {
  ['token','type','role','slug','user_id','email','tenant_token'].forEach(k => {
    localStorage.removeItem(k); sessionStorage.removeItem(k);
  });
  window.location.replace('/tenant-login.html');
}
"""

LOGOUT_PLATFORM = """
function logout() {
  localStorage.clear();
  sessionStorage.clear();
  window.location.replace('/platform-login.html');
}
"""

def add_logout_fn(html, filename, page_type='tenant'):
    if 'function logout()' in html or 'function logout (' in html:
        return html
    fn = LOGOUT_TENANT if page_type == 'tenant' else LOGOUT_PLATFORM
    # Insert just after the auth guard / token init block
    # Strategy: insert after the line with window.location.replace(...login.html) for guards
    # or just after const H = {...} block
    # Use a reliable anchor: after "const H = {" or token init
    inserted = False

    # Try to add right after the auth guard line
    for pattern in [
        r'(if \(!TOKEN[^;]*;\s*)',
        r'(if \(!tok[^;]*;\s*)',
        r'(const H\s*=\s*\{[^}]*\};\s*)',
    ]:
        m = re.search(pattern, html)
        if m:
            pos = m.end()
            html = html[:pos] + fn + html[pos:]
            inserted = True
            break

    if not inserted:
        # Fallback: add before </script> of the first script block
        html = re.sub(r'(</script>)', fn + r'\1', html, count=1)

    print(f'    + logout() added to {filename}')
    return html

# ── 5. Fix api() / apiFetch() to handle 401 → logout ────────────────────────

def fix_api_401(html, filename):
    changed = False

    # tenant-admin.html style: sync fetch, no 401 handling
    # Replace: function api(method, path, body) { ... return fetch(path, opts); }
    old_api = r'function api\(method,\s*path,\s*body\)\s*\{[^}]+return fetch\(path,\s*opts\);\s*\}'
    new_api = """function api(method, path, body) {
  const opts = { method, headers: H };
  if (body) opts.body = JSON.stringify(body);
  return fetch(path, opts).then(r => {
    if (r.status === 401) { logout(); throw new Error('Session expired'); }
    return r;
  });
}"""
    if re.search(old_api, html, re.DOTALL):
        html = re.sub(old_api, new_api, html, flags=re.DOTALL)
        changed = True

    # whatsapp.html style: async api, no 401 handling, returns r.json() directly
    old_wa_api = r'async function api\(method,\s*path,\s*body\)\s*\{[^}]+return r\.json\(\);\s*\}'
    new_wa_api = """async function api(method, path, body) {
  const opts = { method, headers: getH() };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const r = await fetch(HOST + path, opts);
  if (r.status === 401) { logout(); throw new Error('Session expired'); }
  return r.json();
}"""
    if re.search(old_wa_api, html, re.DOTALL):
        html = re.sub(old_wa_api, new_wa_api, html, flags=re.DOTALL)
        changed = True

    # lead-messages.html style: async apiFetch, no 401 handling
    old_lm_api = r'async function apiFetch\(method,\s*path,\s*body\)\s*\{[^}]+return r\.json\(\);\s*\}'
    new_lm_api = """async function apiFetch(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json', ...authHdr() } };
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch(path, opts);
  if (r.status === 401) { logout(); throw new Error('Session expired'); }
  return r.json();
}"""
    if re.search(old_lm_api, html, re.DOTALL):
        html = re.sub(old_lm_api, new_lm_api, html, flags=re.DOTALL)
        changed = True

    if changed:
        print(f'    + 401 handling added to api() in {filename}')
    return html

# ── 6. Standardize token variable name and remove fallback chains ─────────────

def fix_token_patterns(html, filename):
    changed = False

    # invoices.html: tenant_token || token → just token
    old = "localStorage.getItem('tenant_token') || localStorage.getItem('token') || ''"
    new = "localStorage.getItem('token') || ''"
    if old in html:
        html = html.replace(old, new)
        changed = True

    # lead-messages.html tok(): remove 4-level chain
    old_lm = ("return token || localStorage.getItem('tenant_token') || "
               "localStorage.getItem('token') || sessionStorage.getItem('token') || '';")
    new_lm = "return localStorage.getItem('token') || '';"
    if old_lm in html:
        html = html.replace(old_lm, new_lm)
        changed = True

    # lead-messages.html boot token init
    old_lm2 = ("token = localStorage.getItem('tenant_token') || localStorage.getItem('token') || '';")
    new_lm2 = "token = localStorage.getItem('token') || '';"
    if old_lm2 in html:
        html = html.replace(old_lm2, new_lm2)
        changed = True

    # lead-messages.html token var init at top
    old_lm3 = "let token = localStorage.getItem('tenant_token') || localStorage.getItem('token') || '';"
    new_lm3 = "let token = localStorage.getItem('token') || '';"
    if old_lm3 in html:
        html = html.replace(old_lm3, new_lm3)
        changed = True

    # whatsapp.html TOKEN fallback with sessionStorage
    old_wa = "let TOKEN = localStorage.getItem('token') || sessionStorage.getItem('token') || '';"
    new_wa = "let TOKEN = localStorage.getItem('token') || '';"
    if old_wa in html:
        html = html.replace(old_wa, new_wa)
        changed = True

    # whatsapp.html getH redundant fallback inside
    old_wa2 = ("return localStorage.getItem('tenant_token') || localStorage.getItem('token') || "
                "sessionStorage.getItem('token') || TOKEN || '';")
    new_wa2 = "return localStorage.getItem('token') || TOKEN || '';"
    if old_wa2 in html:
        html = html.replace(old_wa2, new_wa2)
        changed = True

    if changed:
        print(f'    + token patterns standardized in {filename}')
    return html

# ── 7. Add logout to marketing.html (improve existing one) ───────────────────

def fix_marketing_logout(html):
    # marketing.html has: function logout(){ localStorage.clear(); location.href='/tenant-login.html'; }
    # Improve to also clear sessionStorage and use replace() instead of href
    old = "function logout(){\n  localStorage.clear(); location.href='/tenant-login.html';\n}"
    new = """function logout(){
  localStorage.clear();
  sessionStorage.clear();
  window.location.replace('/tenant-login.html');
}"""
    if old in html:
        html = html.replace(old, new)
        print('    + marketing.html logout improved')
    return html

# ── 8. Fix profit-loss.html logout (currently removes only 3 keys) ───────────

def fix_profit_loss_logout(html):
    old = """function logout() {
  localStorage.removeItem('token');
  localStorage.removeItem('type');
  localStorage.removeItem('slug');"""
    new = """function logout() {
  ['token','type','role','slug','user_id','email','tenant_token'].forEach(k => {
    localStorage.removeItem(k); sessionStorage.removeItem(k);
  });"""
    if old in html:
        html = html.replace(old, new)
        print('    + profit-loss.html logout improved')
    return html

# ── Main ──────────────────────────────────────────────────────────────────────

# Files and their types
TENANT_PAGES = [
    'tenant-admin.html',
    'orders.html',
    'customers.html',
    'leads.html',
    'products.html',
    'vendors.html',
    'invoices.html',
    'whatsapp.html',
    'lead-messages.html',
    'gst.html',
    'marketing.html',
    'profit-loss.html',
]

PLATFORM_PAGES = [
    'platform-admin.html',
]

# Pages that already have logout
ALREADY_HAS_LOGOUT = {'marketing.html', 'platform-admin.html', 'profit-loss.html'}

ALL_PAGES = TENANT_PAGES + PLATFORM_PAGES

def process_file(filename, page_type='tenant'):
    path = os.path.join(FRONTEND, filename)
    if not os.path.exists(path):
        print(f'  ⚠️  SKIP (not found): {filename}')
        return

    print(f'\n🔧 Processing: {filename}')
    html = read(path)

    html = add_cache_meta(html, filename)
    html = fix_css_versions(html, filename)
    html = add_auth_js(html, filename)
    html = fix_api_401(html, filename)
    html = fix_token_patterns(html, filename)

    if filename not in ALREADY_HAS_LOGOUT:
        html = add_logout_fn(html, filename, page_type)
    elif filename == 'marketing.html':
        html = fix_marketing_logout(html)
    elif filename == 'profit-loss.html':
        html = fix_profit_loss_logout(html)

    write(path, html)

if __name__ == '__main__':
    print('Miguel CRM — Session/Cache/Auth Best Practices Fix')
    print('=' * 52)

    for page in TENANT_PAGES:
        process_file(page, 'tenant')

    for page in PLATFORM_PAGES:
        process_file(page, 'platform')

    print('\n✅ All pages processed.')
    print('📋 Summary:')
    print('   • Cache-Control meta added to all pages')
    print('   • CSS versioned at ?v=' + CSS_VERSION)
    print(f'   • auth.js loaded on all pages')
    print('   • logout() function added to all pages')
    print('   • api() 401 handling added')
    print('   • Token patterns standardized')
