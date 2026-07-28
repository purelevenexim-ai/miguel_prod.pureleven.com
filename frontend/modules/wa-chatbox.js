/**
 * ═══════════════════════════════════════════════════════════
 *  WA CHATBOX  —  Shared WhatsApp slide-in panel  v2
 *  Used by: orders.html, customers.html, leads.html,
 *           invoices.html, gst.html
 * ═══════════════════════════════════════════════════════════
 */
(function () {
  'use strict';

  /* ── STATE ─────────────────────────────────────────────── */
  const WA = {
    phone:       null,
    name:        null,
    contextType: null,   // 'order'|'customer'|'lead'|'invoice'
    contextId:   null,
    windowOpen:  null,
    templates:   [],
    mode:        'wabis',
    bulkPhones:  [],
    quickReplies:[],
    TOKEN:       null,
    _docs:       [],
    orderDetail: null,
    _orderLoading:false,
  };

  /* ── HELPERS ────────────────────────────────────────────── */
  function tok() {
    return WA.TOKEN || localStorage.getItem('tenant_token') || localStorage.getItem('token') || sessionStorage.getItem('token') || '';
  }
  function authHdr() {
    const t = tok();
    return t ? { 'Authorization': 'Bearer ' + t } : {};
  }
  async function api(method, path, body) {
    const opts = { method, headers: { 'Content-Type': 'application/json', ...authHdr() } };
    if (body) opts.body = JSON.stringify(body);
    const r = await fetch(path, opts);
    return r.json();
  }
  function toast(msg, type='info') {
    const c = document.getElementById('waChatToast');
    if (!c) return;
    c.textContent = msg;
    c.className = 'wa-toast wa-toast-' + type + ' show';
    clearTimeout(WA._toastTimer);
    WA._toastTimer = setTimeout(() => c.classList.remove('show'), 3500);
  }
  function cleanPhone(p) {
    if (!p) return '';
    let d = p.replace(/\D/g, '');
    if (d.length === 10) d = '91' + d;
    return d;
  }
  function waWebUrl(phone, text='') {
    return `https://wa.me/${cleanPhone(phone)}?text=${encodeURIComponent(text)}`;
  }
  function fmtTime(ts) {
    if (!ts) return '';
    try {
      const d = new Date(ts.includes('T') ? ts : ts.replace(' ','T')+'Z');
      return d.toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit',hour12:true});
    } catch { return ''; }
  }
  function fmtDate(ts) {
    if (!ts) return '';
    try {
      const d = new Date(ts.includes('T') ? ts : ts.replace(' ','T')+'Z');
      return d.toLocaleDateString('en-IN',{day:'numeric',month:'short'});
    } catch { return ''; }
  }
  function parseMsg(raw) {
    if (!raw) return '';
    try {
      const o = typeof raw==='string' ? JSON.parse(raw) : raw;
      if (o.text?.body) return o.text.body;
      if (o.interactive?.body?.text) return o.interactive.body.text;
      if (o.template?.name) return `[Template: ${o.template.name}]`;
      if (o.image) return '📷 Image';
      if (o.document) return '📄 Document';
      return JSON.stringify(o).slice(0,80);
    } catch { return String(raw).slice(0,120); }
  }
  function esc(s) {
    return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
  function cap(s) { return s.charAt(0).toUpperCase()+s.slice(1); }

  /* ── CSS ────────────────────────────────────────────────── */
  const CSS = `
    :root{--wa-green:#25d366;--wa-dark:#075e54;--wa-lite:#dcf8c6;--wa-bg:#e5ddd5;--wa-panel:#fff;}
    #waChatPanel{
      position:fixed;left:0;top:0;bottom:0;width:420px;max-width:100vw;
      background:var(--wa-panel);box-shadow:4px 0 32px rgba(0,0,0,.2);
      z-index:10000;display:flex;flex-direction:column;
      transform:translateX(-110%);transition:transform .3s cubic-bezier(.4,0,.2,1);
      font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
    }
    #waChatPanel.open{transform:translateX(0);}
    /* Header */
    .wa-hdr{background:var(--wa-dark);color:#fff;padding:12px 14px;display:flex;align-items:center;gap:10px;flex-shrink:0;}
    .wa-avatar{width:40px;height:40px;border-radius:50%;background:var(--wa-green);display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:700;flex-shrink:0;}
    .wa-hdr-info{flex:1;min-width:0;}
    .wa-hdr-name{font-weight:700;font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
    .wa-hdr-phone{font-size:12px;opacity:.75;}
    .wa-win-badge{font-size:10px;font-weight:700;padding:3px 8px;border-radius:10px;white-space:nowrap;}
    .wa-win-badge.open{background:#e8f5e9;color:#2e7d32;}
    .wa-win-badge.closed{background:#fff3e0;color:#bf360c;}
    .wa-win-badge.unknown{background:#e3f2fd;color:#1565c0;}
    .wa-close-btn{background:none;border:none;color:#fff;font-size:20px;cursor:pointer;padding:4px;border-radius:50%;flex-shrink:0;line-height:1;}
    .wa-close-btn:hover{background:rgba(255,255,255,.15);}
    /* Mode bar */
    .wa-mode-bar{background:#f5f5f5;border-bottom:1px solid #e0e0e0;padding:6px 12px;display:flex;gap:6px;align-items:center;flex-shrink:0;}
    .wa-mode-lbl{font-size:11px;color:#555;font-weight:600;white-space:nowrap;}
    .wa-mode-btn{flex:1;padding:5px 8px;border:1px solid #ddd;border-radius:20px;background:#fff;font-size:12px;cursor:pointer;font-weight:500;transition:all .15s;}
    .wa-mode-btn.active{background:var(--wa-green);color:#fff;border-color:var(--wa-green);}
    /* 24h warning */
    #waWinWarn{background:#fff3e0;border-bottom:1px solid #ffe082;padding:8px 14px;font-size:12px;color:#bf360c;display:none;align-items:center;gap:8px;flex-shrink:0;}
    #waWinWarn a{color:var(--wa-dark);font-weight:700;cursor:pointer;text-decoration:underline;}
    /* Tabs */
    .wa-tabs{display:flex;background:#fafafa;border-bottom:1px solid #e0e0e0;flex-shrink:0;overflow-x:auto;}
    .wa-tab{flex:1;min-width:60px;padding:9px 4px;font-size:11px;font-weight:600;text-align:center;cursor:pointer;color:#666;border-bottom:2px solid transparent;transition:all .15s;white-space:nowrap;}
    .wa-tab.active{color:var(--wa-dark);border-bottom-color:var(--wa-green);}
    /* Chat */
    #waChatHist{flex:1;overflow-y:auto;padding:10px;background:var(--wa-bg);display:flex;flex-direction:column;gap:5px;min-height:0;}
    .wa-msg{max-width:82%;padding:7px 11px;border-radius:12px;font-size:13px;line-height:1.45;word-break:break-word;position:relative;}
    .wa-msg-out{background:var(--wa-lite);margin-left:auto;border-bottom-right-radius:3px;}
    .wa-msg-in{background:#fff;margin-right:auto;border-bottom-left-radius:3px;}
    .wa-msg-time{font-size:10px;color:#888;margin-top:3px;text-align:right;}
    .wa-msg-sender{font-size:10px;color:#1565c0;margin-bottom:2px;font-weight:600;}
    .wa-date-sep{text-align:center;font-size:10px;color:#888;background:#d1d7db;border-radius:8px;padding:2px 10px;margin:6px auto;}
    .wa-hist-empty{text-align:center;color:#aaa;font-size:12px;padding:30px 10px;}
    /* Compose */
    .wa-compose{border-top:1px solid #e0e0e0;padding:8px 10px;background:#f5f5f5;flex-shrink:0;}
    .wa-compose-row{display:flex;gap:8px;align-items:flex-end;}
    #waMsgInput{flex:1;border:1px solid #ddd;border-radius:20px;padding:8px 14px;font-size:13px;resize:none;max-height:100px;overflow-y:auto;outline:none;background:#fff;font-family:inherit;transition:border-color .15s;}
    #waMsgInput:focus{border-color:var(--wa-green);}
    #waMsgInput:disabled{background:#f5f5f5;color:#999;}
    .wa-send-btn{width:38px;height:38px;border-radius:50%;background:var(--wa-green);color:#fff;border:none;font-size:17px;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:transform .15s;}
    .wa-send-btn:hover{transform:scale(1.1);}
    .wa-send-btn:disabled{background:#ccc;cursor:not-allowed;transform:none;}
    .wa-toolbar{display:flex;gap:4px;padding:4px 0 0;}
    .wa-tool-btn{background:none;border:none;cursor:pointer;font-size:15px;padding:4px 6px;border-radius:8px;color:#555;transition:background .15s;}
    .wa-tool-btn:hover{background:#e0e0e0;}
    /* Templates */
    #waTabTplContent{display:none;flex-direction:column;flex:1;min-height:0;}
    .wa-tpl-hdr{padding:8px 10px;border-bottom:1px solid #eee;display:flex;align-items:center;justify-content:space-between;flex-shrink:0;background:#fafafa;}
    .wa-tpl-hdr-title{font-size:13px;font-weight:700;color:#333;}
    .wa-refresh-btn{background:none;border:1px solid #ccc;border-radius:8px;padding:4px 10px;font-size:12px;cursor:pointer;color:#555;display:flex;align-items:center;gap:4px;}
    .wa-refresh-btn:hover{background:#e8f5e9;border-color:var(--wa-green);color:var(--wa-dark);}
    #waTplList{overflow-y:auto;flex:1;padding:8px;min-height:0;}
    .wa-tpl-card{border:1px solid #e0e0e0;border-radius:10px;padding:10px 12px;margin-bottom:8px;cursor:pointer;background:#fff;transition:all .15s;}
    .wa-tpl-card:hover{border-color:var(--wa-green);background:#f1fff4;box-shadow:0 2px 8px rgba(37,211,102,.15);}
    .wa-tpl-card-hdr{display:flex;align-items:center;gap:6px;margin-bottom:4px;}
    .wa-tpl-name{font-weight:700;font-size:13px;color:#333;}
    .wa-tpl-badge{font-size:10px;font-weight:600;padding:2px 7px;border-radius:10px;}
    .wa-tpl-badge.Marketing{background:#fce4ec;color:#c62828;}
    .wa-tpl-badge.Utility{background:#e3f2fd;color:#1565c0;}
    .wa-tpl-badge.Authentication{background:#f3e5f5;color:#6a1b9a;}
    .wa-tpl-body{font-size:12px;color:#555;line-height:1.45;white-space:pre-wrap;}
    .wa-tpl-footer{font-size:10px;color:#aaa;margin-top:4px;font-style:italic;}
    .wa-tpl-empty{text-align:center;color:#aaa;font-size:13px;padding:30px;}
    /* Quick */
    #waTabQuickContent{display:none;flex:1;overflow-y:auto;padding:8px;}
    .wa-quick-item{border:1px solid #e0e0e0;border-radius:8px;padding:8px 12px;margin-bottom:6px;cursor:pointer;background:#fff;font-size:13px;display:flex;align-items:center;gap:8px;transition:border-color .15s;}
    .wa-quick-item:hover{border-color:var(--wa-green);background:#f1fff4;}
    .wa-quick-title{font-weight:600;font-size:12px;color:#333;}
    .wa-quick-prev{font-size:11px;color:#888;margin-top:1px;}
    /* File */
    #waTabFileContent{display:none;flex:1;overflow-y:auto;padding:12px;}
    .wa-file-zone{border:2px dashed #ccc;border-radius:12px;padding:22px;text-align:center;cursor:pointer;transition:border-color .15s;background:#fafafa;margin-bottom:8px;}
    .wa-file-zone:hover{border-color:var(--wa-green);background:#f1fff4;}
    .wa-file-zone-icon{font-size:30px;margin-bottom:6px;}
    .wa-file-zone-text{font-size:12px;color:#666;}
    .wa-file-preview{display:flex;align-items:center;gap:10px;background:#fff;border-radius:8px;padding:10px;border:1px solid #e0e0e0;margin-top:8px;}
    .wa-file-name{font-size:12px;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
    /* Docs */
    #waTabDocContent{display:none;flex:1;overflow-y:auto;padding:10px;}
    .wa-doc-card{border:1px solid #e0e0e0;border-radius:10px;padding:12px;margin-bottom:8px;background:#fff;display:flex;align-items:center;gap:12px;}
    .wa-doc-icon{font-size:26px;flex-shrink:0;}
    .wa-doc-info{flex:1;min-width:0;}
    .wa-doc-title{font-weight:600;font-size:13px;color:#333;}
    .wa-doc-sub{font-size:11px;color:#888;margin-top:2px;}
    .wa-doc-btns{display:flex;flex-direction:column;gap:5px;flex-shrink:0;}
    .wa-doc-send{background:var(--wa-green);color:#fff;border:none;border-radius:8px;padding:6px 12px;cursor:pointer;font-size:12px;font-weight:600;white-space:nowrap;}
    .wa-doc-send:hover{opacity:.88;}
    .wa-doc-preview{background:none;border:1px solid var(--wa-dark);color:var(--wa-dark);border-radius:8px;padding:5px 10px;cursor:pointer;font-size:11px;}
    .wa-doc-preview:hover{background:#e8f5e9;}
    .wa-doc-loading{text-align:center;color:#aaa;font-size:12px;padding:20px;}
    /* Toast */
    .wa-toast{position:fixed;bottom:20px;left:50%;transform:translateX(-50%) translateY(80px);background:#333;color:#fff;padding:10px 20px;border-radius:20px;font-size:13px;z-index:11000;opacity:0;transition:all .3s;pointer-events:none;max-width:320px;text-align:center;}
    .wa-toast.show{transform:translateX(-50%) translateY(0);opacity:1;}
    .wa-toast.wa-toast-success{background:#2e7d32;}
    .wa-toast.wa-toast-error{background:#c62828;}
    .wa-toast.wa-toast-info{background:#1565c0;}
    /* Bulk bar */
    #waBulkBar{position:fixed;bottom:0;left:0;right:0;z-index:9997;background:var(--wa-dark);color:#fff;padding:10px 20px;display:none;align-items:center;gap:12px;flex-wrap:wrap;box-shadow:0 -2px 12px rgba(0,0,0,.2);}
    #waBulkBar.visible{display:flex;}
    .wa-bulk-count{font-weight:700;font-size:14px;}
    .wa-bulk-btn{background:var(--wa-green);color:#fff;border:none;border-radius:8px;padding:8px 16px;cursor:pointer;font-weight:600;font-size:13px;}
    .wa-bulk-clear{background:none;border:1px solid rgba(255,255,255,.4);color:#fff;border-radius:8px;padding:8px 12px;cursor:pointer;font-size:12px;}
    /* Overlay */
    #waChatOverlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.3);z-index:9999;}
    #waChatOverlay.show{display:block;}
    #waChatHist::-webkit-scrollbar{width:4px;}
    #waChatHist::-webkit-scrollbar-thumb{background:#ccc;border-radius:3px;}
    @media(max-width:480px){#waChatPanel{width:100vw;}}
  `;

  /* ── HTML ───────────────────────────────────────────────── */
  const HTML = `
    <div id="waChatOverlay" onclick="WaChatbox.close()"></div>
    <div id="waChatPanel">
      <!-- Header -->
      <div class="wa-hdr">
        <div class="wa-avatar" id="waAvatar">?</div>
        <div class="wa-hdr-info">
          <div class="wa-hdr-name" id="waContactName">—</div>
          <div class="wa-hdr-phone" id="waContactPhone">—</div>
        </div>
        <span class="wa-win-badge unknown" id="waWinBadge">⏳ Checking…</span>
        <button class="wa-close-btn" onclick="WaChatbox.close()" title="Close">✕</button>
      </div>
      <!-- Mode switcher -->
      <div class="wa-mode-bar">
        <span class="wa-mode-lbl">Send via:</span>
        <button class="wa-mode-btn active" id="waModeWabis" onclick="WaChatbox.setMode('wabis')">🤖 WABIS API</button>
        <button class="wa-mode-btn" id="waModeWeb" onclick="WaChatbox.setMode('web')">🌐 WhatsApp Web</button>
      </div>
      <!-- 24h warning -->
      <div id="waWinWarn">
        ⚠️ <strong>Outside 24h window</strong> — Free text unavailable. Use a <a onclick="WaChatbox.showTab('tpl')">Template</a> instead.
      </div>
      <!-- Tabs -->
      <div class="wa-tabs">
        <div class="wa-tab active" id="waTabChat"     onclick="WaChatbox.showTab('chat')">💬 Chat</div>
        <div class="wa-tab"        id="waTabTpl"      onclick="WaChatbox.showTab('tpl')">📋 Templates</div>
        <div class="wa-tab"        id="waTabQuick"    onclick="WaChatbox.showTab('quick')">⚡ Quick</div>
        <div class="wa-tab"        id="waTabFile"     onclick="WaChatbox.showTab('file')">📎 File</div>
        <div class="wa-tab"        id="waTabDoc"      onclick="WaChatbox.showTab('doc')">🧾 Docs</div>
        <div class="wa-tab"        id="waTabConfig"   onclick="WaChatbox.showTab('config')">⚙️ Config</div>
      </div>

      <!-- TAB: Chat -->
      <div id="waTabChatContent" style="display:flex;flex-direction:column;flex:1;min-height:0;">
        <div id="waChatHist"><div class="wa-hist-empty">⏳ Loading…</div></div>
        <div class="wa-compose">
          <div class="wa-compose-row">
            <textarea id="waMsgInput" rows="1" placeholder="Type a message…"
              oninput="this.style.height='auto';this.style.height=Math.min(this.scrollHeight,100)+'px'"
              onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();WaChatbox.sendText();}"></textarea>
            <button class="wa-send-btn" id="waSendBtn" onclick="WaChatbox.sendText()" title="Send">➤</button>
          </div>
          <div class="wa-toolbar">
            <button class="wa-tool-btn" title="Attach file" onclick="document.getElementById('waFileInput').click()">📎</button>
            <button class="wa-tool-btn" title="Camera" onclick="document.getElementById('waCameraInput').click()">📷</button>
            <button class="wa-tool-btn" title="Templates" onclick="WaChatbox.showTab('tpl')">📋</button>
            <button class="wa-tool-btn" title="Quick replies" onclick="WaChatbox.showTab('quick')">⚡</button>
            <button class="wa-tool-btn" title="Invoice & Label" onclick="WaChatbox.showTab('doc')">🧾</button>
            <button class="wa-tool-btn" title="Refresh chat" onclick="WaChatbox.loadHistory()">🔄</button>
          </div>
        </div>
        <input type="file" id="waFileInput" style="display:none" accept="*/*" onchange="WaChatbox.onFileSelected(this)">
        <input type="file" id="waCameraInput" style="display:none" accept="image/*" capture="environment" onchange="WaChatbox.onFileSelected(this)">
      </div>

      <!-- TAB: Templates -->
      <div id="waTabTplContent" style="display:none;flex-direction:column;flex:1;min-height:0;">
        <div class="wa-tpl-hdr">
          <span class="wa-tpl-hdr-title">📋 WhatsApp Templates</span>
          <button class="wa-refresh-btn" onclick="WaChatbox.loadTemplates(true)" title="Refresh templates">🔄 Refresh</button>
        </div>
        <div id="waTplList"><div class="wa-tpl-empty">⏳ Loading templates…</div></div>
      </div>

      <!-- TAB: Quick -->
      <div id="waTabQuickContent" style="display:none;flex:1;overflow-y:auto;padding:8px;">
        <div id="waQuickList"><div class="wa-tpl-empty">Loading…</div></div>
      </div>

      <!-- TAB: File -->
      <div id="waTabFileContent" style="display:none;flex:1;overflow-y:auto;padding:12px;">
        <div class="wa-file-zone" onclick="document.getElementById('waFileInput').click()">
          <div class="wa-file-zone-icon">📎</div>
          <div class="wa-file-zone-text"><strong>Click to attach a file</strong><br><span style="font-size:11px;color:#aaa;">Images, PDFs, docs</span></div>
        </div>
        <div class="wa-file-zone" onclick="document.getElementById('waCameraInput').click()">
          <div class="wa-file-zone-icon">📷</div>
          <div class="wa-file-zone-text"><strong>Take a photo</strong><br><span style="font-size:11px;color:#aaa;">Opens camera</span></div>
        </div>
        <div id="waFilePreviewArea"></div>
      </div>

      <!-- TAB: Docs (Invoice / Label) -->
      <div id="waTabDocContent" style="display:none;flex:1;overflow-y:auto;padding:10px;">
        <div id="waDocList"><div class="wa-doc-loading">📄 Loading documents…</div></div>
      </div>

      <!-- TAB: Config (Template Configuration) -->
      <div id="waTabConfigContent" style="display:none;flex:1;overflow-y:auto;padding:12px;">
        <div style="text-align:center;padding:20px 10px;color:#555;">
          <div style="font-size:24px;margin-bottom:10px;">⚙️</div>
          <div style="font-size:13px;font-weight:600;margin-bottom:6px;">Template Configuration</div>
          <div style="font-size:11px;color:#999;margin-bottom:16px;">Design and manage WhatsApp templates</div>
          <button onclick="WaChatbox.openConfigPage()" style="background:var(--wa-green);color:#fff;border:none;border-radius:8px;padding:9px 18px;font-size:12px;font-weight:600;cursor:pointer;transition:all .15s;">
            Open Template Editor
          </button>
        </div>
      </div>
    </div>
    <!-- Toast -->
    <div class="wa-toast" id="waChatToast"></div>
    <!-- Bulk bar -->
    <div id="waBulkBar">
      <span class="wa-bulk-count" id="waBulkCount">0 selected</span>
      <button class="wa-bulk-btn" onclick="WaChatbox.openBulkSend()">💬 Send WhatsApp</button>
      <button class="wa-bulk-clear" onclick="WaChatbox.clearBulk()">✕ Clear</button>
      <span style="font-size:11px;opacity:.7;margin-left:auto;">Note: Invoices & labels not available in bulk</span>
    </div>
  `;

  /* ── INJECT ─────────────────────────────────────────────── */
  function inject() {
    if (document.getElementById('waChatPanel')) return;
    const style = document.createElement('style');
    style.textContent = CSS;
    document.head.appendChild(style);
    const wrap = document.createElement('div');
    wrap.innerHTML = HTML;
    document.body.appendChild(wrap);
  }

  /* ── TAB SWITCHER ───────────────────────────────────────── */
  function showTab(tab) {
    const tabs    = ['chat','tpl','quick','file','doc','config'];
    const tabIds  = { chat:'Chat', tpl:'Tpl', quick:'Quick', file:'File', doc:'Doc', config:'Config' };
    tabs.forEach(t => {
      const tabEl = document.getElementById('waTab'+cap(t));
      const cnt   = document.getElementById('waTab'+cap(t)+'Content');
      if (tabEl) tabEl.classList.toggle('active', t===tab);
      if (cnt)   cnt.style.display = t===tab ? (t==='chat'?'flex':t==='tpl'?'flex':'block') : 'none';
    });
    if (tab==='tpl'  && WA.templates.length===0) loadTemplates();
    if (tab==='quick') renderQuickReplies();
    if (tab==='doc')   renderDocs();
  }

  /* ── OPEN / CLOSE ───────────────────────────────────────── */
  function open({ phone, name, contextType, contextId, invoiceUrl, labelUrl }) {
    if (!phone) { toast('No phone number for this contact', 'error'); return; }
    WA.phone        = cleanPhone(phone);
    WA.name         = name || 'Contact';
    WA.contextType  = contextType || null;
    WA.contextId    = contextId   || null;
    WA.invoiceUrl   = invoiceUrl  || null;
    WA.labelUrl     = labelUrl    || null;
    WA.windowOpen   = null;
    WA._docs        = [];
    WA.orderDetail  = null;
    WA._orderLoading = false;

    document.getElementById('waAvatar').textContent       = (WA.name).charAt(0).toUpperCase();
    document.getElementById('waContactName').textContent  = WA.name;
    document.getElementById('waContactPhone').textContent = '+' + WA.phone;

    const badge = document.getElementById('waWinBadge');
    badge.className = 'wa-win-badge unknown';
    badge.textContent = '⏳ Checking…';
    document.getElementById('waWinWarn').style.display = 'none';

    document.getElementById('waChatPanel').classList.add('open');
    document.getElementById('waChatOverlay').classList.add('show');
    showTab('chat');
    if (WA.contextType === 'order' && WA.contextId) loadOrderContext(false);
    loadHistory();
  }

  function close() {
    document.getElementById('waChatPanel').classList.remove('open');
    document.getElementById('waChatOverlay').classList.remove('show');
  }

  /* ── HISTORY ────────────────────────────────────────────── */
  async function loadHistory() {
    const box = document.getElementById('waChatHist');
    box.innerHTML = '<div class="wa-hist-empty">⏳ Loading…</div>';
    try {
      const r = await fetch(`/api/wa/conversation-by-phone?phone=${WA.phone}&limit=40`, { headers: authHdr() });
      const d = await r.json();
      WA.windowOpen = d.window_open;
      console.log('[WA CHATBOX] 24h window check:', { phone: WA.phone, window_open: d.window_open, last_inbound: d.last_inbound_at, messages_count: (d.messages||[]).length });
      updateWindowBadge();
      renderMessages(d.messages || []);
    } catch (err) {
      console.error('[WA CHATBOX] Error loading history:', err);
      box.innerHTML = '<div class="wa-hist-empty">Could not load conversation</div>';
    }
  }

  function renderMessages(msgs) {
    const box = document.getElementById('waChatHist');
    if (!msgs.length) {
      box.innerHTML = '<div class="wa-hist-empty">📭 No conversation yet<br><small>Send a message to start</small></div>';
      return;
    }
    const sorted = [...msgs].sort((a,b) => new Date(a.conversation_time||0) - new Date(b.conversation_time||0));
    let html = '';
    let lastDate = '';
    for (const m of sorted) {
      const ts     = m.conversation_time || m.delivery_status_updated_at || '';
      const dateStr = fmtDate(ts);
      if (dateStr && dateStr !== lastDate) {
        html += `<div class="wa-date-sep">${dateStr}</div>`;
        lastDate = dateStr;
      }
      const isOut = m.sender === 'bot' || m.sender === 'agent';
      const body  = parseMsg(m.message_content || m.message || '');
      const stat  = m.message_status ? `<span style="font-size:9px;opacity:.6;margin-left:4px;">${m.message_status}</span>` : '';
      html += `<div class="wa-msg ${isOut?'wa-msg-out':'wa-msg-in'}">
        ${!isOut && m.agent_name ? `<div class="wa-msg-sender">${esc(m.agent_name)}</div>` : ''}
        ${esc(body)}
        <div class="wa-msg-time">${fmtTime(ts)}${stat}</div>
      </div>`;
    }
    box.innerHTML = html;
    box.scrollTop = box.scrollHeight;
  }

  function updateWindowBadge() {
    const badge = document.getElementById('waWinBadge');
    const warn  = document.getElementById('waWinWarn');
    const inp   = document.getElementById('waMsgInput');
    if (WA.windowOpen === null) {
      badge.className   = 'wa-win-badge unknown';
      badge.textContent = '⏳ Checking…';
      warn.style.display = 'none';
      if (inp) inp.disabled = false;
    } else if (WA.windowOpen) {
      badge.className   = 'wa-win-badge open';
      badge.textContent = '✅ 24h Window Open';
      warn.style.display = 'none';
      if (inp) { inp.disabled = false; inp.placeholder = 'Type a message…'; }
    } else {
      badge.className   = 'wa-win-badge closed';
      badge.textContent = '⛔ Outside 24h Window';
      warn.style.display = 'flex';
      if (inp && WA.mode === 'wabis') {
        inp.disabled = true;
        inp.placeholder = 'Outside 24h window — use Templates tab';
      }
    }
  }

  /* ── SEND TEXT ──────────────────────────────────────────── */
  async function sendText() {
    const inp = document.getElementById('waMsgInput');
    const msg = (inp.value || '').trim();
    if (!msg) return;
    if (WA.windowOpen === false && WA.mode === 'wabis') {
      // Offer SMS fallback instead of blocking
      const doSms = confirm('The WhatsApp 24-hour window is closed.\n\nSend as SMS instead? (Requires SMS provider configured in your CRM settings)');
      if (doSms) {
        await sendSmsFallback(msg);
        inp.value = ''; inp.style.height = 'auto';
      } else {
        toast('Use the Templates tab to send a template message', 'info');
        showTab('tpl');
      }
      return;
    }
    if (WA.mode === 'web') {
      window.open(waWebUrl(WA.phone, msg), '_blank');
      inp.value = ''; inp.style.height = 'auto';
      return;
    }
    const btn = document.getElementById('waSendBtn');
    if (btn) btn.disabled = true;
    try {
      const r = await api('POST', '/api/wa/send-direct', { phone_number: WA.phone, message_text: msg });
      if (r.success) {
        appendOutMsg(msg);
        inp.value = ''; inp.style.height = 'auto';
        toast('Sent ✓', 'success');
      } else {
        // Offer SMS fallback on any failure
        const doSms = confirm('WhatsApp send failed: ' + (r.message || 'Error') + '\n\nTry SMS fallback?');
        if (doSms) await sendSmsFallback(msg);
      }
    } catch { toast('Network error', 'error'); }
    if (btn) btn.disabled = false;
  }

  async function sendSmsFallback(msg) {
    try {
      const r = await api('POST', '/api/wa/send-with-sms-fallback', {
        phone_number: WA.phone,
        message_text: msg,
        force_sms: true,
      });
      if (r.success) {
        appendOutMsg(msg, `📱 SMS: ${msg}`);
        toast('Sent via SMS ✓', 'success');
      } else {
        toast('SMS failed: ' + (r.error || 'No SMS provider configured'), 'error');
      }
    } catch(e) { toast('SMS error: ' + e.message, 'error'); }
  }

  function appendOutMsg(text, label) {
    const box = document.getElementById('waChatHist');
    const now = new Date().toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit',hour12:true});
    const div = document.createElement('div');
    div.className = 'wa-msg wa-msg-out';
    div.innerHTML = `${esc(label || text)}<div class="wa-msg-time">${now} <span style="font-size:9px;opacity:.5">sending…</span></div>`;
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
  }

  /* ── TEMPLATES ──────────────────────────────────────────── */
  async function loadTemplates(force) {
    if (!force && WA.templates.length > 0) { renderTemplates(); return; }
    const box = document.getElementById('waTplList');
    if (box) box.innerHTML = '<div class="wa-tpl-empty">⏳ Loading templates…</div>';
    try {
      const r = await fetch('/api/wa/templates', { headers: authHdr() });
      const d = await r.json();
      WA.templates = d.templates || [];
      renderTemplates();
      if (force) toast(`${WA.templates.length} templates loaded`, 'success');
    } catch {
      if (box) box.innerHTML = '<div class="wa-tpl-empty">⚠ Could not load templates</div>';
    }
  }

  function renderTemplates() {
    const box = document.getElementById('waTplList');
    if (!box) return;
    if (!WA.templates.length) {
      box.innerHTML = '<div class="wa-tpl-empty">No approved templates found.<br><small>Configure templates in WABIS console.</small></div>';
      return;
    }
    box.innerHTML = WA.templates.map((t, i) => {
      const cat  = t.template_category || 'Utility';
      const body = t.body_content || '';
      const header = t.header_content ? `<div style="font-size:12px;font-weight:700;color:#333;margin-bottom:3px;">${esc(t.header_content)}</div>` : '';
      const footer = t.footer_content ? `<div class="wa-tpl-footer">— ${esc(t.footer_content)}</div>` : '';
      const status = t.status && t.status !== 'Approved' ? `<span style="font-size:10px;color:#888;margin-left:auto;">${esc(t.status)}</span>` : '';
      return `<div class="wa-tpl-card" onclick="WaChatbox.sendTemplate(${i})">
        <div class="wa-tpl-card-hdr">
          <span class="wa-tpl-name">${esc(t.template_name || 'Template')}</span>
          <span class="wa-tpl-badge ${cat}">${esc(cat)}</span>
          ${status}
        </div>
        ${header}
        <div class="wa-tpl-body">${esc(body.slice(0, 160))}${body.length > 160 ? '…' : ''}</div>
        ${footer}
      </div>`;
    }).join('');
  }

  async function sendTemplate(idx) {
    const t = WA.templates[idx];
    if (!t) return;
    if (WA.mode === 'web') {
      const body = t.body_content || t.template_name;
      window.open(waWebUrl(WA.phone, body), '_blank');
      return;
    }
    toast('Sending template…', 'info');

    // Extract Meta creds from template_json
    let accessToken = null;
    let components  = [];
    let locale      = t.locale || 'en';
    try {
      const tj = typeof t.template_json === 'string' ? JSON.parse(t.template_json) : t.template_json;
      if (tj && tj.access_token) accessToken = tj.access_token;
      if (tj && tj.components)   components  = tj.components.filter(c => c.type !== 'HEADER' && c.type !== 'FOOTER');
      if (tj && tj.language)     locale      = tj.language;
    } catch {}

    try {
      const r = await api('POST', '/api/wa/send-template-direct', {
        phone_number:  WA.phone,
        template_name: t.template_name,
        template_id:   t.template_id,
        locale:        locale,
        access_token:  accessToken,
        body_text:     t.body_content || '',
        components:    [],  // No variables needed for simple templates
      });
      if (r.success) {
        appendOutMsg('', `📋 Template: ${t.template_name}`);
        showTab('chat');
        toast('Template sent ✓', 'success');
      } else {
        toast('Send failed: ' + (r.message || r.detail || 'Error'), 'error');
      }
    } catch { toast('Network error', 'error'); }
  }

  /* ── QUICK REPLIES ──────────────────────────────────────── */
  const DEFAULT_QUICK = [
    { title:'👋 Hi',           text:"Hi! Hope you're doing well 😊" },
    { title:'📦 Order update',  text:'Your order is being processed. We\'ll update you shortly!' },
    { title:'✅ Confirmed',     text:'Your order has been confirmed. Thank you!' },
    { title:'🚚 Shipped',       text:'Your order has been shipped and is on its way!' },
    { title:'💳 Payment',       text:'Please complete your payment. Let us know if you need help.' },
    { title:'📞 Call me',       text:'Can we have a quick call to discuss this further?' },
  ];

  async function loadOrderContext(force) {
    if (WA.contextType !== 'order' || !WA.contextId) return null;
    if (WA.orderDetail && !force) return WA.orderDetail;
    if (WA._orderLoading) return WA.orderDetail;
    WA._orderLoading = true;
    try {
      const r = await fetch(`/api/orders/${WA.contextId}`, { headers: authHdr() });
      if (r.ok) WA.orderDetail = await r.json();
    } catch {}
    WA._orderLoading = false;
    return WA.orderDetail;
  }

  function firstName(name) {
    return String(name || WA.name || 'there').trim().split(/\s+/)[0] || 'there';
  }

  function orderTrackingUrl(order) {
    if (!order?.tracking_number) return '';
    const courier = String(order.courier_name || order.courier_code || '').toLowerCase();
    if (courier.includes('india') || courier.includes('post')) {
      return 'https://www.indiapost.gov.in/_layouts/15/dop.portal.tracking/trackconsignment.aspx';
    }
    return '';
  }

  function buildOrderQuickReplies(order) {
    if (WA.contextType !== 'order') return [];
    const name = firstName(order?.customer_name || order?.delivery_name || WA.name);
    const orderNo = order?.order_number || 'your order';
    const tracking = order?.tracking_number || '';
    const status = (order?.tracking_status_text || order?.status || 'being processed').replace(/_/g, ' ');
    const location = order?.tracking_last_location ? ` Current location: ${order.tracking_last_location}.` : '';
    const trackUrl = orderTrackingUrl(order);
    const trackLine = tracking ? `\nTracking ID: ${tracking}${trackUrl ? `\nTrack here: ${trackUrl}` : ''}` : '';
    const amount = order?.total_amount ? ` Amount: ₹${Number(order.total_amount).toFixed(0)}.` : '';
    return [
      {
        title:'📍 Order tracking',
        text:`Hi ${name}, update for ${orderNo}: your shipment is ${status}.${location}${trackLine}`,
      },
      {
        title:'🚨 Urgent tracking',
        text:`Hi ${name}, we are checking ${orderNo} urgently with the courier.${tracking ? ` Tracking ID: ${tracking}.` : ''} We will update you as soon as there is movement.`,
      },
      {
        title:'🧾 Invoice / bill',
        text:`Hi ${name}, your invoice/bill for ${orderNo} is ready.${amount} We are sending the PDF here.`,
      },
    ];
  }

  function renderQuickReplies() {
    const saved = JSON.parse(localStorage.getItem('waQuickReplies') || 'null') || DEFAULT_QUICK;
    if (WA.contextType === 'order' && WA.contextId && !WA.orderDetail && !WA._orderLoading) {
      loadOrderContext(false).then(() => renderQuickReplies());
    }
    const replies = [...buildOrderQuickReplies(WA.orderDetail), ...saved];
    WA.quickReplies = replies;
    const box = document.getElementById('waQuickList');
    if (!box) return;
    box.innerHTML = replies.map((q, i) => `
      <div class="wa-quick-item" onclick="WaChatbox.useQuick(${i})">
        <span>⚡</span>
        <div style="flex:1">
          <div class="wa-quick-title">${esc(q.title)}</div>
          <div class="wa-quick-prev">${esc(q.text.slice(0,60))}${q.text.length>60?'…':''}</div>
        </div>
      </div>`).join('') + `
      <button onclick="WaChatbox.addQuick()" style="width:100%;background:none;border:1px dashed #ccc;border-radius:8px;padding:8px;cursor:pointer;color:#888;font-size:12px;margin-top:4px;">
        ＋ Add quick reply
      </button>`;
  }

  function useQuick(idx) {
    const q = WA.quickReplies[idx];
    if (!q) return;
    const inp = document.getElementById('waMsgInput');
    inp.value = q.text;
    inp.style.height = 'auto';
    inp.style.height = Math.min(inp.scrollHeight, 100) + 'px';
    showTab('chat');
    inp.focus();
  }

  function addQuick() {
    const title = prompt('Quick reply title (e.g. 👋 Hi):');
    if (!title) return;
    const text = prompt('Message text:');
    if (!text) return;
    const saved = JSON.parse(localStorage.getItem('waQuickReplies') || 'null') || [...DEFAULT_QUICK];
    saved.push({ title, text });
    localStorage.setItem('waQuickReplies', JSON.stringify(saved));
    renderQuickReplies();
  }

  /* ── FILE / CAMERA ──────────────────────────────────────── */
  function onFileSelected(input) {
    const file = input.files[0];
    if (!file) return;
    showTab('file');
    const area = document.getElementById('waFilePreviewArea');
    const reader = new FileReader();
    reader.onload = (e) => {
      area.innerHTML = `<div class="wa-file-preview">
        <span style="font-size:22px;">${file.type.startsWith('image/')? '🖼':'📄'}</span>
        <span class="wa-file-name">${esc(file.name)}</span>
        <button class="wa-doc-send" onclick="WaChatbox._sendFile('${esc(e.target.result)}','${esc(file.name)}','${esc(file.type)}')">Send</button>
      </div>`;
    };
    reader.readAsDataURL(file);
    input.value = '';
  }

  async function _sendFile(dataUrl, filename, mimeType) {
    if (WA.mode === 'web') {
      window.open(waWebUrl(WA.phone, `[File: ${filename}]`), '_blank'); return;
    }
    toast('Sending file…', 'info');
    try {
      // Note: WABIS plain send doesn't support binary. Sends filename as text message.
      const r = await api('POST', '/api/wa/send-direct', {
        phone_number: WA.phone,
        message_text: `📎 ${filename}`,
      });
      if (r.success) { toast('File sent ✓', 'success'); showTab('chat'); }
      else toast('Failed: ' + (r.message || 'Error'), 'error');
    } catch { toast('Network error', 'error'); }
  }

  /* ── DOCS (Invoice / Label) ─────────────────────────────── */
  async function renderDocs() {
    const box = document.getElementById('waDocList');
    if (!box) return;
    box.innerHTML = '<div class="wa-doc-loading">📄 Loading documents…</div>';

    // Build doc list based on context
    const docs = [];

    // If invoiceUrl / labelUrl were passed directly (e.g. from invoices.html)
    if (WA.invoiceUrl) docs.push({ icon:'🧾', title:'Tax Invoice', sub:'PDF invoice', url: WA.invoiceUrl, type:'invoice' });
    if (WA.labelUrl)   docs.push({ icon:'📦', title:'Shipping Label', sub:'Shipping label', url: WA.labelUrl, type:'label' });

    // If context is an order → auto-generate URLs
    if (!docs.length && WA.contextType === 'order' && WA.contextId) {
      const invoiceUrl = `/api/invoices/order/${WA.contextId}/quick-pdf`;
      const labelUrl   = null; // label needs POST, handle separately
      docs.push({ icon:'🧾', title:'Tax Invoice',    sub:`Order invoice PDF`, url: invoiceUrl, type:'invoice' });
      docs.push({ icon:'📦', title:'Shipping Label', sub:`Print & send label`, url: null, type:'label_gen', orderId: WA.contextId });
    }

    if (!docs.length) {
      box.innerHTML = `<div class="wa-doc-loading">📄 No documents available.<br><small style="color:#aaa;margin-top:4px;display:block;">Open from an order to access invoice & label.</small></div>`;
      WA._docs = [];
      return;
    }

    WA._docs = docs;
    box.innerHTML = docs.map((d, i) => `
      <div class="wa-doc-card">
        <div class="wa-doc-icon">${d.icon}</div>
        <div class="wa-doc-info">
          <div class="wa-doc-title">${esc(d.title)}</div>
          <div class="wa-doc-sub">${esc(d.sub)}</div>
        </div>
        <div class="wa-doc-btns">
          ${d.url ? `<button class="wa-doc-preview" onclick="WaChatbox.previewAuthPdf('${d.url}')" title="Preview PDF">👁 Preview</button>` : ''}
          <button class="wa-doc-send" onclick="WaChatbox.sendDoc(${i})">💬 Send</button>
        </div>
      </div>`).join('');
  }

  async function sendDoc(idx) {
    const doc = (WA._docs || [])[idx];
    if (!doc) return;

    if (WA.mode === 'web') {
      const url = doc.url || '';
      window.open(waWebUrl(WA.phone, `${doc.title}: ${url}`), '_blank');
      return;
    }

    toast(`Sending ${doc.title}…`, 'info');

    try {
      let docUrl = doc.url;

      // For label_gen: first generate the label PDF (POST)
      if (doc.type === 'label_gen' && doc.orderId) {
        try {
          const resp = await fetch('/api/labels/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...authHdr() },
            body: JSON.stringify({ order_ids: [doc.orderId] }),
          });
          if (!resp.ok) { toast('Could not generate label', 'error'); return; }
          // Get blob URL and open it
          const blob = await resp.blob();
          docUrl = URL.createObjectURL(blob);
          window.open(docUrl, '_blank');
          // Also send the link via WA
          const r = await api('POST', '/api/wa/send-direct', {
            phone_number: WA.phone,
            message_text: `🏷 Shipping label for your order is ready. Please check with our team.`,
          });
          if (r.success) { toast('Label message sent ✓', 'success'); showTab('chat'); }
          else toast('Failed: ' + (r.message || 'Error'), 'error');
          return;
        } catch { toast('Label generation failed', 'error'); return; }
      }

      // For invoice/label: try sending as media via Meta, fall back to text notification
      if (docUrl) {
        // Always open PDF locally first so agent can view it
        try { await WaChatbox.previewAuthPdf(docUrl); } catch { /* skip */ }

        // Try Meta media send (requires Meta Cloud API configured)
        const absoluteUrl = docUrl.startsWith('http') ? docUrl : (window.location.origin + docUrl);
        const mediaResult = await api('POST', '/api/wa/send-media', {
          phone_number: WA.phone,
          media_url:    absoluteUrl,
          media_type:   'document',
          filename:     doc.title.replace(/\s+/g,'-').toLowerCase() + '.pdf',
          caption:      doc.title,
        });

        if (mediaResult.success) {
          appendOutMsg('', `📎 ${doc.title} sent as document`);
          toast(`${doc.title} sent via WhatsApp ✓`, 'success');
          showTab('chat');
        } else {
          // Fallback to text notification
          const r = await api('POST', '/api/wa/send-direct', {
            phone_number: WA.phone,
            message_text: `🧾 Your ${doc.title} is ready! Our team will send it to you shortly.`,
          });
          if (r.success) {
            appendOutMsg('', `🧾 ${doc.title} notification sent`);
            toast('Notification sent ✓ (PDF send not configured)', 'success');
            showTab('chat');
          } else {
            toast('Failed: ' + (r.message || 'Error'), 'error');
          }
        }
      }
    } catch { toast('Network error', 'error'); }
  }

  /* ── MODE ───────────────────────────────────────────────── */
  function setMode(m) {
    WA.mode = m;
    document.getElementById('waModeWabis').classList.toggle('active', m==='wabis');
    document.getElementById('waModeWeb').classList.toggle('active', m==='web');
    const inp = document.getElementById('waMsgInput');
    if (!inp) return;
    if (m === 'web') {
      inp.disabled = false;
      inp.placeholder = 'Type a message (opens WhatsApp Web)…';
    } else {
      updateWindowBadge();
    }
  }

  /* ── BULK ───────────────────────────────────────────────── */
  function addToBulk(phone, name) {
    const p = cleanPhone(phone);
    if (!p) return;
    if (!WA.bulkPhones.find(x => x.phone===p)) WA.bulkPhones.push({ phone:p, name:name||p });
    updateBulkBar();
  }
  function removeFromBulk(phone) {
    WA.bulkPhones = WA.bulkPhones.filter(x => x.phone !== cleanPhone(phone));
    updateBulkBar();
  }
  function clearBulk() { WA.bulkPhones = []; updateBulkBar(); }
  function updateBulkBar() {
    const bar = document.getElementById('waBulkBar');
    const cnt = document.getElementById('waBulkCount');
    if (!bar || !cnt) return;
    cnt.textContent = WA.bulkPhones.length + ' selected';
    bar.classList.toggle('visible', WA.bulkPhones.length > 0);
  }
  async function openBulkSend() {
    if (!WA.bulkPhones.length) return;
    const msg = prompt(`Send message to ${WA.bulkPhones.length} contact(s):\n(Invoices & labels not available in bulk)`);
    if (!msg) return;
    let ok=0, fail=0;
    for (const { phone } of WA.bulkPhones) {
      try {
        const r = await api('POST', '/api/wa/send-direct', { phone_number: phone, message_text: msg });
        if (r.success) ok++; else fail++;
      } catch { fail++; }
      await new Promise(res => setTimeout(res, 1200));
    }
    toast(`Bulk: ${ok} sent, ${fail} failed`, ok>0?'success':'error');
    clearBulk();
  }

  /* ── INIT ───────────────────────────────────────────────── */
  function init(token) {
    if (token) WA.TOKEN = token;
    inject();
  }

  function openConfigPage() {
    close();
    window.location.href = '/whatsapp.html';
  }

  /* ── AUTH PDF PREVIEW ───────────────────────────────────── */
  async function previewAuthPdf(url) {
    try {
      const token = tok();
      if (!token) { toast('Not authenticated — please login again', 'error'); return; }
      const resp = await fetch(url, { 
        headers: { 'Authorization': 'Bearer ' + token },
        credentials: 'include'
      });
      if (!resp.ok) { toast('Could not open PDF (' + resp.status + ' ' + resp.statusText + ')', 'error'); return; }
      const contentType = resp.headers.get('content-type');
      if (!contentType || !contentType.includes('application/pdf')) { 
        toast('Not a PDF — invalid response', 'error'); 
        return; 
      }
      const blob = await resp.blob();
      const blobUrl = URL.createObjectURL(blob);
      window.open(blobUrl, '_blank');
      // Release the object URL after 60 s so memory is freed
      setTimeout(() => URL.revokeObjectURL(blobUrl), 60000);
    } catch(e) { toast('PDF preview error: ' + e.message, 'error'); }
  }

  /* ── PUBLIC API ─────────────────────────────────────────── */
  window.WaChatbox = {
    init, open, close,
    showTab, setMode,
    loadHistory, loadTemplates,
    sendText, sendTemplate, sendDoc,
    _sendFile, onFileSelected,
    useQuick, addQuick, renderQuickReplies,
    addToBulk, removeFromBulk, clearBulk, updateBulkBar, openBulkSend,
    openConfigPage, previewAuthPdf, sendSmsFallback,
  };
})();
