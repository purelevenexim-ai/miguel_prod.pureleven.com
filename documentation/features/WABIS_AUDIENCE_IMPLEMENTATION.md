## 🎯 WABIS Leads on Audience Page — Implementation Complete ✅

### What Changed

You can now see leads from your WABIS bots (e.g., bot ID `389699`) on the **Audience** page in Miguel.

### How It Works

1. **Leads come into WABIS** via your bot (e.g., bot ID 389699)
2. **WABIS sends webhook** to Miguel's `/api/wa/inbound/{tenant_id}`
3. **Miguel stores** as `WaSubscriber` (WABIS contact)
4. **Audience page** has new **💬 WABIS** filter button
5. **Click 💬 WABIS** → see all your bot's subscribers
6. **Select + Send** → bulk WhatsApp messages to them

### Setup Requirements

✅ **Already Done:**
- WABIS API Token + Phone Number ID configured
- Connection test passing (✅ badge shows "Ready")

⚠️ **YOU NEED TO VERIFY:**
- Inbound webhook URL is configured in WABIS
- "Message Received" event is enabled in WABIS webhooks

### Quick Test

1. Open **Marketing → 🎯 Audience**
2. In the filter section, click **💬 WABIS** button
3. Should show all subscribers who have messaged your bot
4. If empty, the webhook may not be receiving messages yet

### Files Changed

**Backend:**
- `/opt/miguel/backend/app/modules/wa_engine/router.py` — Added `GET /api/wa/subscribers/as-leads/list` endpoint

**Frontend:**
- `/opt/miguel/frontend/marketing.html` — Added WABIS filter + fetch logic in `fetchAudienceRows()`

**Documentation:**
- `/opt/miguel/docs/general/WABIS_AUDIENCE_SYNC_GUIDE.md` — Full guide with troubleshooting

### API Endpoint

```
GET /api/wa/subscribers/as-leads/list
  ?page=1&limit=100&search=query
```

Returns WABIS subscribers formatted as "leads" for compatibility with the audience table.

---

**📖 Full Guide:** See `docs/general/WABIS_AUDIENCE_SYNC_GUIDE.md` for detailed instructions, troubleshooting, and use cases.
