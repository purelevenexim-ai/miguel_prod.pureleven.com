# Shipping Configuration — Visual Guide

## Access Flow

```
┌─────────────────────────────────────┐
│  Tenant Login (tenant-login.html)   │
│  Enter: Email + Password            │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Tenant Admin Dashboard             │
│  (tenant-admin.html)                │
│  ┌─────────────────────────────────┐│
│  │ SIDEBAR NAVIGATION              ││
│  │ 📊 Dashboard                    ││
│  │ 👥 Employees (admin only)       ││
│  │ 📈 Reports                      ││
│  │ ... other modules ...           ││
│  │                                 ││
│  │ INTEGRATIONS                    ││
│  │ 🚚 Shipping Config ⭐ (admin)   ││
│  └─────────────────────────────────┘│
└──────────────┬──────────────────────┘
               │ Click: 🚚 Shipping Config
               ▼
┌─────────────────────────────────────┐
│  SHIPPING CONFIGURATION PANEL       │
│  ┌─────────────────────────────────┐│
│  │ TAB NAVIGATION:                 ││
│  │                                 ││
│  │ ▸ Shopify Stores                ││
│  │ ▪ Delivery Partners             ││
│  │ ▪ Notification Channels         ││
│  │ ▪ Business Rules                ││
│  └─────────────────────────────────┘│
│  ┌─────────────────────────────────┐│
│  │ SHOPIFY STORES TAB (selected)   ││
│  │                                 ││
│  │ [+ Add Store]                   ││
│  │                                 ││
│  │ Store Name | URL | Status | ... ││
│  │ ────────────────────────────────││
│  │ My Shopify | ... | ✓ Connected  ││
│  │ [Edit] [⚡ Test] [Delete]       ││
│  │                                 ││
│  └─────────────────────────────────┘│
└─────────────────────────────────────┘
```

## Tab 1: Shopify Stores

```
┌────────────────────────────────────────────────────────┐
│ Connected Shopify Stores                               │
│                                        [+ Add Store]   │
├────────────────────────────────────────────────────────┤
│ Store Name    │ URL              │ Status         │ ... │
├────────────────────────────────────────────────────────┤
│ My Main Shop  │ myshop.shop...   │ ✓ Connected   │ ... │
│ [Edit] [⚡] [Delete]                                    │
├────────────────────────────────────────────────────────┤
│ Test Store    │ test.shopify.com │ ⚠ Not tested  │ ... │
│ [Edit] [⚡] [Delete]                                    │
└────────────────────────────────────────────────────────┘

Modal: Add Shopify Store
┌────────────────────────────────────┐
│ Add Shopify Store                  │
├────────────────────────────────────┤
│ Store Name *                        │
│ [_______________________]           │
│                                    │
│ Store URL *                        │
│ [_______________________]           │
│                                    │
│ API Access Token *                 │
│ [_______________________]           │
│                                    │
│ API Client ID                      │
│ [_______________________]           │
│                                    │
│ API Client Secret                  │
│ [_______________________]           │
│                                    │
│ ☐ Set as primary store             │
│                                    │
│         [Cancel]  [Save]           │
└────────────────────────────────────┘
```

## Tab 2: Delivery Partners

```
┌────────────────────────────────────────────────────────┐
│ Delivery Partners                                      │
│                                  [+ Add Partner]       │
├────────────────────────────────────────────────────────┤
│ Partner      │ Type       │ Status         │ Pickup ... │
├────────────────────────────────────────────────────────┤
│ Primary      │ delhivery  │ ✓ Connected   │ DEL001 ...│
│ Delhivery    │ (Primary)  │               │           │
│ [Edit] [⚡] [Delete]                                    │
├────────────────────────────────────────────────────────┤
│ Blue Dart    │ bluedart   │ ⚠ Not tested  │ BOM002 ...│
│ [Edit] [⚡] [Delete]                                    │
└────────────────────────────────────────────────────────┘

Modal: Add Delivery Partner
┌────────────────────────────────────┐
│ Add Delivery Partner                │
├────────────────────────────────────┤
│ Partner Type *                      │
│ [Select a partner... ▼]             │
│   • Delhivery                       │
│   • Blue Dart                       │
│   • DTDC                            │
│   • India Post                      │
│   • Amazon Logistics                │
│                                    │
│ Display Name *                      │
│ [Primary Delhivery      ]           │
│                                    │
│ API Key *                           │
│ [_______________________]           │
│                                    │
│ Pickup Location Code                │
│ [DEL001________________]            │
│                                    │
│ Warehouse Name                      │
│ [Delhi HQ________________]          │
│                                    │
│ ☐ Set as primary partner            │
│                                    │
│         [Cancel]  [Save]           │
└────────────────────────────────────┘
```

## Tab 3: Notification Channels

```
┌────────────────────────────────────────────────────────┐
│ Notification Channels                                  │
│                                 [+ Add Channel]        │
├────────────────────────────────────────────────────────┤
│ Channel    │ Type      │ Provider    │ Status          │
├────────────────────────────────────────────────────────┤
│ WHATSAPP   │ whatsapp  │ Meta        │ ✓ Connected    │
│ (Primary)  │           │             │                │
│ [Edit] [⚡] [Delete]                                    │
├────────────────────────────────────────────────────────┤
│ SMS        │ sms       │ Twilio      │ ⚠ Not tested   │
│ [Edit] [⚡] [Delete]                                    │
├────────────────────────────────────────────────────────┤
│ EMAIL      │ email     │ SendGrid    │ ⚠ Not tested   │
│ [Edit] [⚡] [Delete]                                    │
└────────────────────────────────────────────────────────┘

Modal: Add Notification Channel
┌────────────────────────────────────┐
│ Add Notification Channel             │
├────────────────────────────────────┤
│ Channel Type *                      │
│ [Select a channel... ▼]             │
│   • WhatsApp                        │
│   • SMS                             │
│   • Email                           │
│                                    │
│ Provider                            │
│ [Meta________________]              │
│                                    │
│ API Key *                           │
│ [_______________________]           │
│                                    │
│ Phone Number (WhatsApp)             │
│ [_______________________]           │
│                                    │
│ Phone Number ID (WhatsApp)          │
│ [_______________________]           │
│                                    │
│ Business Account ID (WhatsApp)      │
│ [_______________________]           │
│                                    │
│ ☐ Set as primary channel            │
│                                    │
│         [Cancel]  [Save]           │
└────────────────────────────────────┘
```

## Tab 4: Business Rules

```
┌────────────────────────────────────────────────────────┐
│ Shipping Business Rules                                │
│                                                        │
│ AUTOMATION                          PAYMENT METHODS    │
│ ☐ Auto-create shipments on order    ☐ Cash on Delivery│
│ ☐ Auto-confirm after payment        ☑ Prepaid shipping│
│                                                        │
│ CUSTOMER NOTIFICATIONS              DEFAULT LOGISTICS  │
│ ☑ Notify on dispatch                • Shipment Type   │
│ ☑ Notify on delivery                  [Surface ▼]    │
│                                                        │
│ Default Weight (kg)                                    │
│ [0.5_]                                                 │
│                                                        │
│ Default Dimensions (cm)                                │
│ [15_] [10_] [10_]  ← Length, Width, Height           │
│                                                        │
│ Notification Channel                                   │
│ [WhatsApp ▼]                                          │
│                                                        │
│ Changes save automatically ✓                          │
│                                                        │
└────────────────────────────────────────────────────────┘
```

## User Feedback

```
SUCCESS MESSAGE
┌────────────────────────────────────┐
│ ✓ Store added successfully!        │ ← Auto-hides after 3s
└────────────────────────────────────┘

ERROR MESSAGE
┌────────────────────────────────────┐
│ ✗ Connection failed: Invalid token │ ← Auto-hides after 5s
└────────────────────────────────────┘
```

## Access Control

```
LOGIN: email + password

AUTHENTICATION CHECK
     │
     ├─ Valid JWT token? 
     │  └─ No → Redirect to /tenant-login.html
     │
     └─ Yes → Check user role

ROLE CHECK (from localStorage['role'])
     │
     ├─ role == "admin"
     │  └─ Show full dashboard + Shipping Config menu ✓
     │
     └─ role != "admin" (sales/marketing/support/ops)
        └─ Hide Shipping Config menu (role visibility)
           If user tries to access API:
           └─ 403 Forbidden (backend auth guard)
```

## Data Flow (Example: Add Shopify Store)

```
Frontend (HTML/JS)
    │
    ├─ User fills form:
    │  • Store Name: "My Shop"
    │  • Store URL: "myshop.myshopify.com"
    │  • API Token: "shpat_..."
    │
    └─ Click [Save] button
         │
         ▼
    api('POST', '/api/config/shopify-stores', {...})
         │
         ├─ Fetch with auth header:
         │  "Authorization: Bearer <token>"
         │
         ▼
Backend (FastAPI)
    │
    ├─ Route: POST /api/config/shopify-stores
    │
    ├─ Dependency injection:
    │  • get_current_user → returns Employee object
    │  • get_db → returns SQLAlchemy session
    │
    ├─ Permission check:
    │  if employee.role != RoleEnum.admin:
    │      raise HTTPException(403 Forbidden)
    │
    ├─ Validation (Pydantic schema):
    │  • store_name: required
    │  • store_url: required, unique across all tenants
    │  • api_access_token: required
    │
    ├─ Encryption:
    │  encrypted_token = service.encrypt_credential(token)
    │
    ├─ Database insert:
    │  ShopifyStore(
    │      tenant_id = employee.tenant_id,
    │      store_name = "My Shop",
    │      store_url = "myshop.myshopify.com",
    │      api_access_token = "gAAAAAB...",  ← encrypted
    │      is_primary = False,
    │      is_connected = False
    │  )
    │
    └─ Return:
         {
           "id": "550e8400-e29b-41d4-a716-446655440000",
           "tenant_id": "...",
           "store_name": "My Shop",
           "store_url": "myshop.myshopify.com",
           "is_primary": false,
           "is_connected": false,
           "created_at": "2026-02-24T..."
         }
         │
         ▼
Frontend receives response
    │
    ├─ if response.ok:
    │   • Close modal
    │   • Show success banner: "✓ Store added successfully!"
    │   • Reload table (call loadShippingStores())
    │   • New store appears in table
    │
    └─ else:
        • Show error banner with error details
```

---

**Legend:**
- ✓ = Connected/Active
- ⚠ = Not tested/Inactive
- ⭐ = New feature
- [Button] = Clickable button
- [...] = Optional/Additional fields
- ▼ = Dropdown menu
