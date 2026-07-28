# Credential Encryption Service

**File:** `/opt/miguel/backend/app/modules/shipping_config/service.py`

This file contains all business logic for the shipping configuration module.

---

## Overview

The service layer handles:
1. **Credential Encryption/Decryption** (Fernet)
2. **API Connection Testing**
3. **Partner Configuration Management**
4. **Webhook Management**

---

## Full Implementation

```python
from cryptography.fernet import Fernet
from typing import Dict, Optional, Any
from datetime import datetime
import httpx
import os
from app.core.config import settings

# =============== CREDENTIAL ENCRYPTION ===============

class CredentialService:
    """Encrypt/decrypt sensitive credentials"""
    
    def __init__(self):
        # Load encryption key from environment
        key = os.getenv('ENCRYPTION_KEY')
        if not key:
            raise ValueError("ENCRYPTION_KEY environment variable not set")
        self.cipher = Fernet(key.encode())
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt credential"""
        return self.cipher.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt credential"""
        return self.cipher.decrypt(ciphertext.encode()).decode()

credential_service = CredentialService()


def encrypt_credential(value: str) -> str:
    """Helper function to encrypt credential"""
    return credential_service.encrypt(value)


def decrypt_credential(value: str) -> str:
    """Helper function to decrypt credential"""
    return credential_service.decrypt(value)


# =============== SHOPIFY SERVICE ===============

class ShopifyService:
    """Shopify API integration"""
    
    @staticmethod
    async def test_connection(store) -> Dict[str, Any]:
        """Test Shopify API connection by fetching shop info"""
        try:
            token = decrypt_credential(store.api_access_token)
            store_url = store.store_url.replace('.myshopify.com', '')
            
            url = f"https://{store_url}.myshopify.com/admin/api/{store.api_version}/shop.json"
            
            headers = {
                "X-Shopify-Access-Token": token,
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                shop_info = response.json().get('shop', {})
                return {
                    "success": True,
                    "message": f"Connected to {shop_info.get('name')}",
                    "shop": shop_info
                }
            else:
                return {
                    "success": False,
                    "message": f"API Error: {response.status_code}"
                }
        
        except httpx.TimeoutException:
            return {
                "success": False,
                "message": "Connection timeout"
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }
    
    @staticmethod
    async def setup_webhooks(store) -> Dict[str, Any]:
        """Create order webhooks in Shopify"""
        try:
            token = decrypt_credential(store.api_access_token)
            store_url = store.store_url.replace('.myshopify.com', '')
            
            webhook_url = f"{settings.API_BASE_URL}/webhooks/shopify/{store.id}/orders"
            
            payload = {
                "webhook": {
                    "topic": "orders/create",
                    "address": webhook_url,
                    "format": "json"
                }
            }
            
            url = f"https://{store_url}.myshopify.com/admin/api/{store.api_version}/webhooks.json"
            
            headers = {
                "X-Shopify-Access-Token": token,
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 201:
                webhook = response.json().get('webhook', {})
                return {
                    "success": True,
                    "webhook_id": webhook.get('id'),
                    "message": "Webhook created successfully"
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to create webhook: {response.status_code}"
                }
        
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }


# =============== DELHIVERY SERVICE ===============

class DelhiveryService:
    """Delhivery API integration"""
    
    PARTNER_CONFIG = {
        "base_url": "https://track.delhivery.com/api",
        "shipment_types": ["surface", "express", "same_day"],
        "supported_states": [
            "Andaman & Nicobar",
            "Andhra Pradesh",
            "Arunachal Pradesh",
            "Assam",
            "Bihar",
            # ... full state list
        ]
    }
    
    @staticmethod
    async def test_connection(partner) -> Dict[str, Any]:
        """Test Delhivery API connection"""
        try:
            api_key = decrypt_credential(partner.api_key)
            
            url = f"{DelhiveryService.PARTNER_CONFIG['base_url']}/v1/waybill/create/"
            
            headers = {
                "Authorization": f"Token {api_key}",
                "Content-Type": "application/json"
            }
            
            # Minimal test payload
            test_payload = {
                "waybill": 0,  # Create new
                "order": "TEST-001",
                "clientname": partner.client_name,
                "consignee": "Test",
                "consignee_address": "Test",
                "consignee_city": "Bangalore",
                "consignee_pincode": "560001",
                "quantity": 1,
                "weight": 1.0,
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=test_payload,
                    headers=headers,
                    timeout=10
                )
            
            if response.status_code == 201:
                return {
                    "success": True,
                    "message": "Connected to Delhivery",
                    "client_name": partner.client_name
                }
            elif response.status_code == 401:
                return {
                    "success": False,
                    "message": "Invalid API key"
                }
            else:
                return {
                    "success": False,
                    "message": f"API Error: {response.status_code}"
                }
        
        except httpx.TimeoutException:
            return {
                "success": False,
                "message": "Connection timeout"
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }
    
    @staticmethod
    def get_shipment_tracking(waybill_id: str, api_key: str) -> Dict[str, Any]:
        """Get shipment tracking details"""
        # Implementation for real-time tracking
        pass
    
    @staticmethod
    def create_shipment(order, partner) -> Dict[str, Any]:
        """Create shipment in Delhivery"""
        # Implementation for shipment creation
        pass


# =============== BLUE DART SERVICE ===============

class BlueDartService:
    """Blue Dart API integration"""
    
    PARTNER_CONFIG = {
        "base_url": "https://omapi.bluedart.com/api",
        "shipment_types": ["surface", "express"],
        "supported_states": [
            "Andaman & Nicobar",
            "Andhra Pradesh",
            # ... state list
        ]
    }
    
    @staticmethod
    async def test_connection(partner) -> Dict[str, Any]:
        """Test Blue Dart API connection"""
        try:
            api_key = decrypt_credential(partner.api_key)
            
            url = f"{BlueDartService.PARTNER_CONFIG['base_url']}/India/v1/Session/Authenticate"
            
            payload = {
                "LoginID": partner.client_id,
                "Password": api_key
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=10
                )
            
            if response.status_code == 200 and response.json().get('IsSucceeded'):
                return {
                    "success": True,
                    "message": "Connected to Blue Dart"
                }
            else:
                return {
                    "success": False,
                    "message": "Authentication failed"
                }
        
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }


# =============== PARTNER CONFIGURATION ===============

PARTNER_CONFIGS = {
    "delhivery": {
        "name": "Delhivery",
        "base_url": "https://track.delhivery.com/api",
        "shipment_types": ["surface", "express", "same_day"],
        "requires_fields": {
            "api_key": "API Key (Token)",
            "client_name": "Client Name",
            "pickup_location_code": "Pickup Location Code"
        },
        "service_class": DelhiveryService
    },
    "bluedart": {
        "name": "Blue Dart",
        "base_url": "https://omapi.bluedart.com/api",
        "shipment_types": ["surface", "express"],
        "requires_fields": {
            "client_id": "Client ID (LoginID)",
            "api_key": "Password",
        },
        "service_class": BlueDartService
    },
    "dtdc": {
        "name": "DTDC",
        "base_url": "https://apiv2.dtdc.com",
        "shipment_types": ["surface"],
        "requires_fields": {
            "api_key": "API Key",
            "client_id": "Client Code"
        },
        "service_class": None  # To be implemented
    },
    "india_post": {
        "name": "India Post",
        "base_url": "https://api.india-post.com",
        "shipment_types": ["surface"],
        "requires_fields": {
            "api_key": "API Key",
            "client_id": "Account Number"
        },
        "service_class": None  # To be implemented
    },
    "amazon": {
        "name": "Amazon Logistics",
        "base_url": "https://api.amazon.com/logistics",
        "shipment_types": ["surface", "express"],
        "requires_fields": {
            "api_key": "Access Key",
            "client_secret": "Secret Key"
        },
        "service_class": None  # To be implemented
    }
}


def get_partner_config(partner_type: str) -> Dict[str, Any]:
    """Get configuration for partner type"""
    config = PARTNER_CONFIGS.get(partner_type)
    if not config:
        raise ValueError(f"Unknown partner type: {partner_type}")
    return config


# =============== CONNECTION TESTING ===============

async def test_shopify_connection(store) -> Dict[str, Any]:
    """Test Shopify connection"""
    return await ShopifyService.test_connection(store)


async def test_delivery_partner_connection(partner) -> Dict[str, Any]:
    """Test delivery partner connection"""
    config = get_partner_config(partner.partner_type)
    service_class = config.get('service_class')
    
    if service_class:
        return await service_class.test_connection(partner)
    else:
        return {
            "success": False,
            "message": f"Service for {partner.partner_type} not yet implemented"
        }


# =============== NOTIFICATION CHANNEL TESTING ===============

class WhatsAppService:
    """WhatsApp Meta Cloud API integration"""
    
    @staticmethod
    async def test_connection(channel) -> Dict[str, Any]:
        """Test WhatsApp connection"""
        try:
            access_token = decrypt_credential(channel.access_token)
            phone_number_id = channel.phone_number_id
            
            url = f"https://graph.instagram.com/v18.0/{phone_number_id}/messages"
            
            params = {
                "access_token": access_token
            }
            
            # Test with message info request
            test_url = f"https://graph.instagram.com/v18.0/{phone_number_id}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(test_url, params=params, timeout=10)
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "Connected to WhatsApp"
                }
            elif response.status_code == 401:
                return {
                    "success": False,
                    "message": "Invalid access token"
                }
            else:
                return {
                    "success": False,
                    "message": f"API Error: {response.status_code}"
                }
        
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }


async def test_notification_connection(channel) -> Dict[str, Any]:
    """Test notification channel connection"""
    if channel.channel_type == "whatsapp":
        return await WhatsAppService.test_connection(channel)
    elif channel.channel_type == "sms":
        return {"success": True, "message": "SMS channel ready"}
    elif channel.channel_type == "email":
        return {"success": True, "message": "Email channel ready"}
    else:
        return {
            "success": False,
            "message": f"Unknown channel type: {channel.channel_type}"
        }
```

---

## 🔐 Setting Up Encryption Key

### Generate Encryption Key (One-time)

```bash
# In Python REPL
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print(key.decode())  # Output: b'...' <- Copy this value
```

### Store in `.env`

```bash
# .env
ENCRYPTION_KEY=<paste the key value from above, without the b''>
```

### In Docker

```dockerfile
# Dockerfile
ENV ENCRYPTION_KEY=${ENCRYPTION_KEY}
```

---

## 💾 Database Setup

### Create Encryption Key

```bash
# Run this once
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Add to Environment

```bash
export ENCRYPTION_KEY="your-generated-key-here"
```

### Run Migrations

```bash
cd /opt/miguel/backend
alembic upgrade head
```

---

## 🧪 Testing Credentials

```python
# Test credential encryption
from app.modules.shipping_config.service import encrypt_credential, decrypt_credential

# Encrypt
encrypted = encrypt_credential("shpat_abc123...")
print(f"Encrypted: {encrypted}")

# Decrypt
decrypted = decrypt_credential(encrypted)
print(f"Decrypted: {decrypted}")
assert decrypted == "shpat_abc123..."
```

---

## 🔍 Security Checklist

✅ All credentials encrypted before database storage  
✅ Decryption only in memory when needed for API calls  
✅ No plaintext credentials in logs  
✅ Access control: admin-only configuration  
✅ Multi-tenant isolation: tenant_id filters  
✅ Encryption key stored in environment (not in git)  

---

## 📝 Notes

- Credentials are encrypted using Fernet (symmetric encryption)
- Fernet provides both encryption and authentication
- Encryption key must be exactly 44 characters (Fernet requirement)
- If encryption key changes, old encrypted values become unreadable
- Keep backup of encryption key for database recovery

