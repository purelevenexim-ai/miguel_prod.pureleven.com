# 🔄 WhatsApp Engine — Redesign (February 23, 2026)

## Understanding WABIS Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                          WABIS DASHBOARD                         │
│                      (admin.workpex.com)                         │
│                                                                  │
│  ┌────────────────────┐    ┌─────────────────────────────┐       │
│  │  BOT FLOWS         │    │  OUT-BOUND WEBHOOK           │      │
│  │  (templates,       │    │  (fires POST to YOUR server  │      │
│  │   buttons,         │    │   when user taps a button    │      │
│  │   menus)           │    │   or submits a flow)         │      │
│  │                    │    │                               │      │
│  │  ► Workflow URL    │    │  Fields: subscriber_id,      │      │
│  │    (for INBOUND    │    │  subscriber_name, phone,     │      │
│  │     to WA message) │    │  postback_id, labels,        │      │
│  └────────────────────┘    │  input_flow_data, location   │      │
│                            └─────────────────────────────┘       │
└──────────────────────────────────────────────────────────────────┘
```

### Two Traffic Directions:

| Direction | Flow | Purpose | Mechanism |
|-----------|------|---------|-----------|
| **INBOUND to Miguel** | WhatsApp User → WABIS → Miguel | Collect leads, receive messages | WABIS "Out-bound Webhook" POSTs to `/api/wa/inbound/{tenant_id}` |
| **OUTBOUND from Miguel** | Miguel → WABIS Workflow URL → WhatsApp User | Send order confirmations, tracking, marketing blasts | Miguel POSTs JSON to WABIS Workflow URLs |

### Key Insight:
- **WABIS "Out-bound Webhook"** = data flowing OUT of WABIS, INTO our server (confusing name!)
- **WABIS "Workflow URL"** = URL we POST data TO, which triggers WABIS to send a WhatsApp message

---

## What Needs to Work

### 1. INBOUND: WABIS → Miguel (Lead Collection)
- User taps button/submits flow in WhatsApp
- WABIS fires POST to our webhook URL
- Miguel creates/updates subscriber → creates lead → stores message
- Lead appears in Marketing tab and Leads page
- **Already implemented ✅** (just needs the WABIS out-bound webhook configured)

### 2. OUTBOUND: Miguel → WABIS → WhatsApp (Notifications)
Triggered automatically by business events:

| Event | Template | Variables Sent |
|-------|----------|----------------|
| Order Created (confirmed) | "Order Confirmation" | customer_name, order_number, total_amount |
| Order Packed | "Order Packed" | customer_name, order_number |
| Tracking Number Added | "Shipping Update" | customer_name, order_number, tracking_number, courier_name |
| Marketing Blast | User-defined | customer_name, phone, custom fields |

Each outbound message type maps to a **WABIS Workflow URL** (created in WABIS dashboard).

### 3. Marketing Tab — What the User Sees
- **Audience tab**: All leads + customers with phone numbers (existing ✅)
- **Campaigns tab**: WhatsApp blast campaigns — send marketing messages to selected audience
- **Analytics tab**: Delivery stats (existing ✅)
- **WhatsApp Inbox**: See conversations, reply to messages (existing ✅)
- **Settings tab**: Configure WABIS connection + outbound message templates + inbound webhook

---

## Configuration Steps (for the User)

### Step 1: Connect WABIS (already done)
- Enter Bot ID + Access Token from admin.workpex.com

### Step 2: Create WABIS Flows (in WABIS dashboard)
Create 4+ flows in WABIS for outbound messages:
1. **Order Confirmed** flow — receives: `customer_name`, `order_number`, `total_amount`, `phone`
2. **Order Packed** flow — receives: `customer_name`, `order_number`, `phone`
3. **Shipped + Tracking** flow — receives: `customer_name`, `order_number`, `tracking_number`, `courier_name`, `phone`
4. **Marketing Promo** flow — receives: `customer_name`, `phone`, `promo_text`

Each flow has a **Workflow URL** that Miguel will POST to.

### Step 3: Register Message Templates in Miguel
In Settings → "Outbound Message Templates":
- Create template: name="Order Confirmed", trigger=`order.confirmed`, workflow_url=`<from WABIS>`
- Create template: name="Order Packed", trigger=`order.packed`, workflow_url=`<from WABIS>`
- Create template: name="Shipped", trigger=`order.shipped`, workflow_url=`<from WABIS>`
- Create template: name="Marketing Blast", trigger=`manual`, workflow_url=`<from WABIS>`

### Step 4: Configure WABIS Inbound Webhook (in WABIS dashboard)
- Create an Out-bound Webhook in WABIS
- Name: "Miguel CRM"
- URL: `/api/wa/inbound/{tenant_id}` (shown in Settings)
- Enable triggers: POSTBACK ✅, USER INPUT FLOW ✅
- Enable fields: SUBSCRIBER ID ✅, SUBSCRIBER NAME ✅, PHONE NUMBER ✅, LABELS ✅, POSTBACK ID ✅, INPUT FLOW DATA ✅

---

## Implementation Plan

### Backend Changes:
1. **Rename `wa_campaign_types` → use as "Message Templates"** — already has workflow_url, payload_template
2. **Add `trigger` column** to `wa_campaign_types` — values: `order.confirmed`, `order.packed`, `order.shipped`, `order.tracking`, `manual`
3. **Add hooks in `update_order_status()`** — when status changes to confirmed/packed/shipped, auto-fire the matching WA template
4. **Add hook for tracking number** — when tracking_number is set, fire the "shipped" template

### Frontend Changes:
1. **Rename Campaign Types → "Message Templates"** in Settings
2. **Add trigger selector** to template creation modal
3. **Campaigns tab** — show real WA campaigns from DB, let user create marketing campaigns
4. **Help guide** — update with actual WABIS setup flow screenshots

### No New Tables Needed — existing schema already supports this!
