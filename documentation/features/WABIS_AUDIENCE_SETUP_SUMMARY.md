# 📱 WABIS Leads Sync to Audience — Setup Complete ✅

## What You Can Do Now

**Your WABIS leads (from bot ID 389699 or any bot) now appear on the Miguel Audience page!**

### Quick Steps to See Your Leads

1. **Go to:** Marketing → **🎯 Audience** tab
2. **Click:** **💬 WABIS** button in the Source filters
3. **Result:** All your WhatsApp subscribers from WABIS appear in a table
4. **Action:** Select + Send WhatsApp messages to them

---

## Important: Webhook Configuration

For leads to sync automatically from WABIS → Miguel, you need to configure the **inbound webhook** in WABIS.

### Configure Webhook in WABIS

1. Go to **bot.wabis.in** → Your Bot → **Webhooks** (or **Outbound Webhook**)
2. Paste this URL (from Miguel Settings → Inbound Webhook):
   ```
   https://yourdomain.com/api/wa/inbound/{your-tenant-id}
   ```
3. Add custom header:
   - **Name:** `X-Webhook-Secret`
   - **Value:** Copy from Miguel Settings → Inbound Webhook (click 👁 to reveal)
4. Enable these events:
   - ✅ **Message Received**
   - ✅ **Button/Postback** (for auto-replies)
5. **Save in WABIS**

### Verify It Works

1. Send yourself a WhatsApp message to your bot in WABIS
2. Come back to Miguel, go to **Audience** → filter **💬 WABIS**
3. Your number should appear within 1-2 seconds

---

## What Changed in Miguel

### Backend (Python)
- **New Route:** `GET /api/wa/subscribers/as-leads/list`
- **Purpose:** Returns WABIS subscribers formatted like leads
- **Used by:** Frontend Audience page

### Frontend (JavaScript)
- **New Filter:** 💬 WABIS button added to "Source" filters
- **New Logic:** When WABIS is selected, loads subscribers instead of leads
- **Result:** Seamless integration with Audience table

### Database
- **No changes** — uses existing `WaSubscriber` table

---

## Documentation & Guides

| File | Purpose |
|------|---------|
| `WABIS_AUDIENCE_SYNC_GUIDE.md` | Full detailed guide with use cases & troubleshooting |
| `WABIS_AUDIENCE_QUICKSTART.html` | Visual quick-start guide (open in browser) |
| `WABIS_AUDIENCE_IMPLEMENTATION.md` | Technical implementation details |

---

## FAQ

### Q: Where do WABIS subscribers come from?
**A:** When someone sends a message to your WABIS bot, WABIS sends a webhook to Miguel. Miguel stores them as `WaSubscriber` records and displays them on the Audience page.

### Q: Can I merge WABIS subscribers with existing leads?
**A:** Not automatically. If you want to track them as leads too, you can:
- Manually create a lead with their info
- Or use the Inbox to message them directly

### Q: What if I don't see any WABIS subscribers?
**A:** The webhook may not be configured. See "Webhook Configuration" section above. Then send a test message to your bot and refresh.

### Q: Can I send bulk messages to WABIS subscribers?
**A:** Yes! Select them on Audience page → click "Send WhatsApp Blast" → choose a template → send.

### Q: Do I lose any data from previous leads/customers?
**A:** No. WABIS subscribers are a separate view. Your existing leads and customers are unchanged.

---

## Next Steps

1. **Configure the webhook** (see above)
2. **Test it** — send a message to your bot
3. **View leads** on Audience page → filter by 💬 WABIS
4. **Send messages** to your WABIS subscribers

---

**Questions?** See the full guides in `/docs/general/WABIS_AUDIENCE_SYNC_GUIDE.md` or ask support.
