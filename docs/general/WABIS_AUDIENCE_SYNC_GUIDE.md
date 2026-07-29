# 📱 Sync WABIS Leads to Audience Page

## Overview

When leads come into your WABIS bot (e.g., via bot ID `389699`), they are stored in Miguel as **WABIS Subscribers**. You can now view these subscribers on the **Audience** page alongside your regular leads and customers.

---

## Quick Start

### 1. Ensure WABIS Inbound Webhook is Configured

For leads to arrive in Miguel from WABIS, the **inbound webhook** must be set up:

1. Go to **⚙️ Settings** → **Inbound Webhook** section
2. Copy your unique webhook URL
3. In WABIS → Your Bot → **Webhook Settings**
4. Paste the Miguel webhook URL
5. Enable **Message Received** event
6. Save

→ Now when leads contact your bot in WABIS, they automatically sync to Miguel.

---

## View WABIS Leads on Audience Page

### Step 1: Open Audience Tab

1. Go to **Marketing** → **🎯 Audience** tab (top left)

### Step 2: Filter by WABIS Source

In the filter section, under **"Source"** click:
- **💬 WABIS** button

This will load all your WABIS subscribers (people who have contacted your bot).

### Step 3: Search or Bulk Select

- **Search:** Type a name or phone number to find specific contacts
- **Select All:** Check the top checkbox to select all displayed WABIS contacts
- **Bulk Actions:** Send a WhatsApp blast to selected subscribers

---

## Understanding the Data

### What fields appear for WABIS subscribers?

| Field | Value | Notes |
|-------|-------|-------|
| **Name** | Subscriber name from WABIS | May be "Unknown" if not set |
| **Phone** | Phone number | The actual WhatsApp number they used to contact you |
| **Email** | — | WABIS doesn't store email; leave empty |
| **Status** | `subscriber` | Virtual status — indicates it came from WABIS |
| **Orders** | 0 | WABIS doesn't track orders; shows 0 |
| **Last Active** | When they last messaged | Auto-updated from WABIS |

### How are WABIS subscribers different from leads/customers?

| Source | Created By | Updated | Phone | Email |
|--------|-----------|---------|-------|-------|
| **Lead** | You manually in Miguel | Manual entry | Optional | Optional |
| **Customer** | Orders API sync | Auto via orders | Required | Optional |
| **WABIS Subscriber** | Webhook from WABIS | Auto on each message | Required | Not available |

---

## Common Use Cases

### Use Case 1: Send a WhatsApp Blast to New WABIS Subscribers

1. Go **Audience** → filter by **💬 WABIS**
2. Select all (or specific subscribers) with the checkboxes
3. Click **📤 Send WhatsApp Blast** (top right)
4. Choose a **Message Template** (Campaign Type)
5. Click **Send**

→ Miguel sends the template to all selected WABIS subscribers via WhatsApp.

### Use Case 2: Convert a WABIS Subscriber to a Lead

1. Open **Audience** → filter by **💬 WABIS**
2. Click on the subscriber's phone number or name
3. Create a **new lead** in the leads tab with their info
4. Add them manually to your leads database

→ Now they appear in both WABIS subscribers AND leads.

### Use Case 3: Tag and Auto-Respond to WABIS Leads

1. Set up **Postback Rules** in **Settings**
   - When a customer clicks a button in your WABIS bot, the postback triggers
2. The rule can automatically:
   - Tag the subscriber (e.g., "Interested")
   - Change their status
   - Start a campaign

→ WABIS subscribers flow seamlessly into your automation.

---

## Troubleshooting

### "No WABIS subscribers appear on Audience page"

**Check:**
1. Is your WABIS API connected? → Go **Settings** → check ✅ badge at top
2. Did you configure the **inbound webhook**? → Settings → Inbound Webhook section
3. Have any leads actually messaged your bot? → Check WABIS bot activity

**Fix:**
- Re-copy your webhook URL from Miguel Settings
- Paste it in WABIS → Webhooks → ensure "Message Received" is enabled
- Send a test message to your WABIS bot from WhatsApp
- Refresh Miguel → Audience page (should appear within 1-2 seconds)

### "WABIS subscribers show but I can't send them messages"

**Check:**
1. Do you have **API Token + Phone Number ID** set? → ✅ badge should say "Ready"
2. Is the subscriber's WhatsApp number **active** (green badge in WABIS)?

**Fix:**
- Ensure your **API Token** is fresh (not expired) → re-copy from WABIS Developer
- Confirm **Phone Number ID** is correct → re-copy from WABIS → WhatsApp Accounts
- Test connection: Settings → click **🔌 Test Connection** → should show ✅

### "I see WABIS subscribers but their names are all 'Unknown'"

This is normal! WABIS only stores the phone number by default. Names are set when:
- The subscriber replies with their name
- You manually update their name in WABIS

→ You can still send messages; names will populate over time.

---

## API Reference (for developers)

### Get WABIS Subscribers as Leads

```http
GET /api/wa/subscribers/as-leads/list?page=1&limit=100&search=query
Authorization: Bearer <token>
```

**Response:**
```json
{
  "total": 42,
  "page": 1,
  "limit": 100,
  "results": [
    {
      "id": "uuid-here",
      "name": "John Doe",
      "phone": "919876543210",
      "email": null,
      "status": "subscriber",
      "city": null,
      "product_interest": null,
      "updated_at": "2026-02-23T14:30:00Z",
      "created_at": "2026-02-22T10:15:00Z"
    },
    ...
  ]
}
```

**Query Parameters:**
- `page` (int, default 1) — page number
- `limit` (int, default 100, max 200) — results per page
- `search` (string, optional) — search by name or phone

---

## Integration Architecture

```
┌─────────────────────────────────────────┐
│  Customer WhatsApp Message               │
│  → "Hi, I'm interested in your product"  │
└──────────────────┬──────────────────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │  WABIS Bot 389699    │
        │  (Receives message)  │
        └──────────┬───────────┘
                   │ (Webhook POST)
                   ▼
    ┌─────────────────────────────┐
    │ Miguel /api/wa/inbound/      │
    │ Creates WaSubscriber + msg   │
    └──────────────┬────────────────┘
                   │
         ┌─────────┴──────────┐
         │                    │
         ▼                    ▼
    ┌──────────┐      ┌──────────────┐
    │  Inbox   │      │  Audience    │
    │💬Messages│      │ 🎯 WABIS Tab │
    └──────────┘      └──────────────┘
                      (This page!)
```

---

## Next Steps

- 📱 [Send WhatsApp Direct Messages](README.md#direct-messaging)
- 🎯 [Set Up Postback Rules](README.md#postback-rules)
- 📊 [Create Message Templates](README.md#campaign-types)
- 🔗 [Full Setup Guide](wa-setup-guide.html)
