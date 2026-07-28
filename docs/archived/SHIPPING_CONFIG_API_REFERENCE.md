# Shipping Configuration Dashboard — Complete API Reference

**Version:** 1.0  
**Base URL:** `/api/config`  
**Authentication:** Bearer token (tenant admin only)  
**Rate Limit:** 100 req/min per tenant  

---

## 📋 API Endpoints Overview

| Category | Endpoints | Purpose |
|----------|-----------|---------|
| Shopify Stores | 4 endpoints | Configure Shopify integrations |
| Delivery Partners | 4 endpoints | Configure delivery providers |
| Notifications | 4 endpoints | Configure notification channels |
| Business Rules | 2 endpoints | Configure shipping rules |
| **Total** | **14 endpoints** | Complete configuration API |

---

## 🛒 SHOPIFY STORES API

### 1. List All Shopify Stores

**Endpoint:** `GET /shopify-stores`

**Description:** Get all Shopify stores configured for the tenant

**Request:**
```bash
curl -X GET http://localhost:8000/api/config/shopify-stores \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

**Response (200 OK):**
```json
[
  {
    "id": "store-uuid-123",
    "store_name": "Main Store",
    "store_url": "purelevenexim.myshopify.com",
    "is_primary": true,
    "is_active": true,
    "is_connected": true,
    "last_sync": "2026-02-24T10:30:00",
    "last_connection_test": "2026-02-24T10:00:00"
  },
  {
    "id": "store-uuid-456",
    "store_name": "Secondary Store",
    "store_url": "pureleven.myshopify.com",
    "is_primary": false,
    "is_active": true,
    "is_connected": false,
    "last_sync": null,
    "last_connection_test": "2026-02-23T15:00:00"
  }
]
```

**Error (401 Unauthorized):**
```json
{
  "detail": "Invalid credentials"
}
```

---

### 2. Create Shopify Store

**Endpoint:** `POST /shopify-stores`

**Description:** Add a new Shopify store configuration

**Request Body:**
```json
{
  "store_name": "Pure Leven Main",
  "store_url": "purelevenexim.myshopify.com",
  "api_access_token": "shpat_abc123xyz...",
  "api_client_id": "0704646c7742dd2d8842e23a51d2a60e",
  "api_client_secret": "shpss_xyz789...",
  "is_primary": true
}
```

**Request:**
```bash
curl -X POST http://localhost:8000/api/config/shopify-stores \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "store_name": "Pure Leven Main",
    "store_url": "purelevenexim.myshopify.com",
    "api_access_token": "shpat_...",
    "api_client_id": "0704646c...",
    "api_client_secret": "shpss_...",
    "is_primary": true
  }'
```

**Response (201 Created):**
```json
{
  "id": "store-uuid-123",
  "store_name": "Pure Leven Main",
  "store_url": "purelevenexim.myshopify.com",
  "is_primary": true,
  "is_active": true,
  "is_connected": false,
  "last_sync": null,
  "last_connection_test": null
}
```

**Errors:**
```json
{
  "detail": "Store URL already configured"
}
```
Status: 400 Bad Request

---

### 3. Test Shopify Connection

**Endpoint:** `POST /shopify-stores/{store_id}/test-connection`

**Description:** Verify Shopify API credentials work

**Path Parameters:**
- `store_id` (string): UUID of the store

**Request:**
```bash
curl -X POST http://localhost:8000/api/config/shopify-stores/store-uuid-123/test-connection \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

**Response (200 OK - Success):**
```json
{
  "status": "connected",
  "message": "Connected to Pure Leven"
}
```

**Response (200 OK - Failed):**
```json
{
  "status": "failed",
  "message": "API Error: 401 - Invalid access token"
}
```

**Response (200 OK - Error):**
```json
{
  "status": "error",
  "message": "Connection timeout - check your internet connection"
}
```

---

### 4. Update Shopify Store

**Endpoint:** `PUT /shopify-stores/{store_id}`

**Description:** Update Shopify store configuration

**Path Parameters:**
- `store_id` (string): UUID of the store

**Request Body (all optional):**
```json
{
  "store_name": "New Store Name",
  "api_access_token": "shpat_new...",
  "is_primary": false,
  "is_active": true
}
```

**Request:**
```bash
curl -X PUT http://localhost:8000/api/config/shopify-stores/store-uuid-123 \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "store_name": "Updated Name",
    "is_primary": false
  }'
```

**Response (200 OK):**
```json
{
  "id": "store-uuid-123",
  "store_name": "Updated Name",
  "store_url": "purelevenexim.myshopify.com",
  "is_primary": false,
  "is_active": true,
  "is_connected": true,
  "last_sync": "2026-02-24T10:30:00",
  "last_connection_test": "2026-02-24T10:00:00"
}
```

---

## 🚚 DELIVERY PARTNERS API

### 5. List Available Partner Types

**Endpoint:** `GET /delivery-partners/available`

**Description:** Get list of supported delivery partner types

**Request:**
```bash
curl -X GET http://localhost:8000/api/config/delivery-partners/available \
  -H "Content-Type: application/json"
```

**Response (200 OK):**
```json
[
  {
    "id": "delhivery",
    "name": "Delhivery",
    "logo": "delhivery.png"
  },
  {
    "id": "bluedart",
    "name": "Blue Dart",
    "logo": "bluedart.png"
  },
  {
    "id": "dtdc",
    "name": "DTDC",
    "logo": "dtdc.png"
  },
  {
    "id": "india_post",
    "name": "India Post",
    "logo": "india_post.png"
  },
  {
    "id": "amazon",
    "name": "Amazon Logistics",
    "logo": "amazon.png"
  }
]
```

---

### 6. List Configured Delivery Partners

**Endpoint:** `GET /delivery-partners`

**Description:** Get all delivery partners configured for tenant

**Request:**
```bash
curl -X GET http://localhost:8000/api/config/delivery-partners \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

**Response (200 OK):**
```json
[
  {
    "id": "partner-uuid-123",
    "partner_type": "delhivery",
    "display_name": "Delhivery (Express)",
    "is_primary": true,
    "is_active": true,
    "is_connected": true,
    "supported_shipment_types": ["surface", "express", "same_day"],
    "last_connection_test": "2026-02-24T10:00:00"
  },
  {
    "id": "partner-uuid-456",
    "partner_type": "bluedart",
    "display_name": "Blue Dart",
    "is_primary": false,
    "is_active": true,
    "is_connected": false,
    "supported_shipment_types": ["surface", "express"],
    "last_connection_test": "2026-02-23T15:00:00"
  }
]
```

---

### 7. Add Delivery Partner

**Endpoint:** `POST /delivery-partners`

**Description:** Configure a new delivery partner

**Request Body:**
```json
{
  "partner_type": "delhivery",
  "display_name": "Delhivery Express",
  "api_key": "37ce9815dcdb4a259163ef6ac8bc56beb3e6b252",
  "client_name": "purelevenexim",
  "pickup_location_code": "685561",
  "warehouse_name": "Bangalore Warehouse",
  "is_primary": true
}
```

**Request:**
```bash
curl -X POST http://localhost:8000/api/config/delivery-partners \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "partner_type": "delhivery",
    "display_name": "Delhivery Express",
    "api_key": "37ce9815dcdb...",
    "client_name": "purelevenexim",
    "pickup_location_code": "685561",
    "is_primary": true
  }'
```

**Response (201 Created):**
```json
{
  "id": "partner-uuid-123",
  "partner_type": "delhivery",
  "display_name": "Delhivery Express",
  "is_primary": true,
  "is_active": true,
  "is_connected": false,
  "supported_shipment_types": ["surface", "express", "same_day"],
  "last_connection_test": null
}
```

---

### 8. Test Delivery Partner Connection

**Endpoint:** `POST /delivery-partners/{partner_id}/test-connection`

**Description:** Verify delivery partner API credentials work

**Path Parameters:**
- `partner_id` (string): UUID of the partner

**Request:**
```bash
curl -X POST http://localhost:8000/api/config/delivery-partners/partner-uuid-123/test-connection \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

**Response (200 OK - Success):**
```json
{
  "status": "connected",
  "message": "Connected to Delhivery",
  "client_name": "purelevenexim"
}
```

**Response (200 OK - Failed):**
```json
{
  "status": "failed",
  "message": "Invalid API key"
}
```

---

## 💬 NOTIFICATION CHANNELS API

### 9. List Notification Channels

**Endpoint:** `GET /notification-channels`

**Description:** Get all notification channels configured for tenant

**Request:**
```bash
curl -X GET http://localhost:8000/api/config/notification-channels \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

**Response (200 OK):**
```json
[
  {
    "id": "channel-uuid-123",
    "channel_type": "whatsapp",
    "provider": "meta",
    "is_active": true,
    "is_connected": true,
    "phone_number": "+91-9876543210",
    "last_connection_test": "2026-02-24T10:00:00"
  }
]
```

---

### 10. Create Notification Channel

**Endpoint:** `POST /notification-channels`

**Description:** Add a new notification channel

**Request Body:**
```json
{
  "channel_type": "whatsapp",
  "provider": "meta",
  "api_key": "EAAG5aZCWn...",
  "access_token": "EAAG5aZCWn...",
  "business_account_id": "1234567890",
  "phone_number_id": "1234567890",
  "is_primary": true
}
```

**Request:**
```bash
curl -X POST http://localhost:8000/api/config/notification-channels \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "channel_type": "whatsapp",
    "provider": "meta",
    "api_key": "EAAG5aZCWn...",
    "access_token": "EAAG5aZCWn...",
    "business_account_id": "1234567890",
    "phone_number_id": "1234567890",
    "is_primary": true
  }'
```

**Response (201 Created):**
```json
{
  "id": "channel-uuid-123",
  "channel_type": "whatsapp",
  "provider": "meta",
  "is_active": true,
  "is_connected": false,
  "phone_number": null
}
```

---

### 11. Test Notification Channel

**Endpoint:** `POST /notification-channels/{channel_id}/test-connection`

**Description:** Verify notification channel credentials work

**Request:**
```bash
curl -X POST http://localhost:8000/api/config/notification-channels/channel-uuid-123/test-connection \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

**Response (200 OK - Success):**
```json
{
  "status": "connected",
  "message": "Connected to WhatsApp"
}
```

---

## ⚙️ BUSINESS RULES API

### 12. Get Business Rules

**Endpoint:** `GET /business-rules`

**Description:** Get shipping business rules for tenant

**Request:**
```bash
curl -X GET http://localhost:8000/api/config/business-rules \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

**Response (200 OK):**
```json
{
  "max_order_value": 50000,
  "max_cod_amount": 10000,
  "require_cod_confirmation": true,
  "auto_create_on_order_created": true,
  "send_delivery_confirmation": true,
  "notify_via_whatsapp": true
}
```

---

### 13. Update Business Rules

**Endpoint:** `PUT /business-rules`

**Description:** Update shipping business rules (all fields optional)

**Request Body:**
```json
{
  "max_order_value": 100000,
  "max_cod_amount": 50000,
  "require_cod_confirmation": true,
  "auto_create_on_order_created": false,
  "send_delivery_confirmation": true,
  "notify_via_whatsapp": true,
  "notify_via_sms": true,
  "admin_emails": ["admin@example.com"]
}
```

**Request:**
```bash
curl -X PUT http://localhost:8000/api/config/business-rules \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "max_order_value": 100000,
    "max_cod_amount": 50000,
    "notify_via_sms": true,
    "admin_emails": ["admin@example.com"]
  }'
```

**Response (200 OK):**
```json
{
  "max_order_value": 100000,
  "max_cod_amount": 50000,
  "require_cod_confirmation": true,
  "auto_create_on_order_created": false,
  "send_delivery_confirmation": true,
  "notify_via_whatsapp": true
}
```

---

## 🔐 Authentication & Authorization

### Bearer Token

All authenticated endpoints require:
```
Authorization: Bearer <jwt_token>
```

**How to get token:**
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "password"
  }'

# Response
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

### Role Requirements

- **`GET` endpoints:** `tenant_admin` or `super_admin`
- **`POST/PUT/DELETE` endpoints:** `tenant_admin` or `super_admin`

**Error (403 Forbidden):**
```json
{
  "detail": "Only tenant admins can configure shipping"
}
```

---

## 📊 Request/Response Patterns

### Success Response (2xx)

```json
{
  "id": "uuid",
  "field1": "value1",
  "field2": "value2",
  "created_at": "2026-02-24T10:00:00",
  "updated_at": "2026-02-24T10:00:00"
}
```

### Error Response (4xx/5xx)

```json
{
  "detail": "Human-readable error message"
}
```

### List Response

```json
[
  { "id": "1", "name": "Item 1" },
  { "id": "2", "name": "Item 2" }
]
```

---

## 🔄 Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK - Request succeeded |
| 201 | Created - Resource created successfully |
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid/missing token |
| 403 | Forbidden - User lacks permissions |
| 404 | Not Found - Resource doesn't exist |
| 500 | Server Error - Unexpected error |

---

## 📝 Pagination (Future)

For list endpoints, add pagination:

```bash
curl -X GET "http://localhost:8000/api/config/shopify-stores?skip=0&limit=10"
```

---

## 🧪 Testing with Postman

1. **Import Collection:**
   - Create new Postman collection
   - Add folder "Shipping Config"
   - Add requests for each endpoint

2. **Set Variables:**
   - `{{base_url}}` = `http://localhost:8000`
   - `{{token}}` = Your bearer token

3. **Test Collection:**
   - Run all requests in order
   - Verify responses match documentation

**Example Postman request:**
```
GET {{base_url}}/api/config/shopify-stores
Authorization: Bearer {{token}}
Content-Type: application/json
```

---

## 🐛 Debugging

### Enable Query Logging

```python
# In app/main.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Credentials

```bash
# Verify encrypted credentials in database
SELECT id, store_name, is_connected FROM shopify_stores;
```

### Test Credentials Offline

```python
from app.modules.shipping_config.service import (
    decrypt_credential, ShopifyService
)

store = db.query(ShopifyStore).first()
token = decrypt_credential(store.api_access_token)
# Can now use token for manual testing
```

---

## 📚 Complete curl Examples

### Create and Test Shopify Store

```bash
# 1. Create store
STORE_ID=$(curl -s -X POST http://localhost:8000/api/config/shopify-stores \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "store_name": "Test",
    "store_url": "test.myshopify.com",
    "api_access_token": "shpat_...",
    "api_client_id": "...",
    "api_client_secret": "..."
  }' | jq -r '.id')

# 2. Test connection
curl -X POST http://localhost:8000/api/config/shopify-stores/$STORE_ID/test-connection \
  -H "Authorization: Bearer $TOKEN"

# 3. List stores
curl -X GET http://localhost:8000/api/config/shopify-stores \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🎯 Next Steps

1. ✅ Save this file as API reference
2. ✅ Use curl examples to test as you build
3. ✅ Share with frontend developer for integration
4. ✅ Generate Postman collection (if using Postman)

Ready to build! 🚀

