import os
from typing import Any, Dict, Optional
from datetime import datetime

import httpx
from cryptography.fernet import Fernet

from app.core.config import settings


# ─────────────────────────────────────────────────────────────
#  CREDENTIAL ENCRYPTION
# ─────────────────────────────────────────────────────────────

def _get_cipher() -> Fernet:
    # Prefer the Pydantic settings object; fall back to raw os.getenv
    key = settings.ENCRYPTION_KEY or os.getenv("ENCRYPTION_KEY", "")
    if not key:
        raise RuntimeError(
            "ENCRYPTION_KEY is not configured. "
            "Add it to docker-compose.yml environment section or the backend .env file."
        )
    return Fernet(key.encode())


def encrypt_credential(value: Optional[str]) -> Optional[str]:
    """Encrypt a plaintext credential before saving to DB. Returns None if value is empty/None."""
    if not value or not value.strip():
        return None
    return _get_cipher().encrypt(value.strip().encode()).decode()


def decrypt_credential(value: Optional[str]) -> Optional[str]:
    """Decrypt a stored credential for use in API calls. Returns None if value is empty/None."""
    if not value:
        return None
    return _get_cipher().decrypt(value.encode()).decode()


# ─────────────────────────────────────────────────────────────
#  PARTNER BASE CONFIGURATIONS  (no secrets here)
# ─────────────────────────────────────────────────────────────

PARTNER_CONFIGS: Dict[str, Dict[str, Any]] = {
    "delhivery": {
        "name": "Delhivery",
        "base_url": "https://track.delhivery.com/api",
        "shipment_types": ["surface", "express", "same_day"],
        "required_fields": ["api_key", "client_name", "pickup_location_code"],
    },
    "bluedart": {
        "name": "Blue Dart",
        "base_url": "https://omapi.bluedart.com/api",
        "shipment_types": ["surface", "express"],
        "required_fields": ["api_key", "client_id"],
    },
    "dtdc": {
        "name": "DTDC",
        "base_url": "https://apiv2.dtdc.com",
        "shipment_types": ["surface"],
        "required_fields": ["api_key", "client_id"],
    },
    "india_post": {
        "name": "India Post",
        "base_url": os.getenv("INDIA_POST_PROD_URL", "").strip() or None,
        "shipment_types": ["surface"],
        # client_id = login username, api_key = login password (encrypted)
        # client_name = 'sandbox' | 'production' (environment flag)
        "required_fields": ["client_id", "api_key"],
    },
    "amazon": {
        "name": "Amazon Logistics",
        "base_url": "https://sellercentral.amazon.in/fba",
        "shipment_types": ["surface", "express"],
        "required_fields": ["api_key", "api_secret"],
    },
}


def get_partner_config(partner_type: str) -> Dict[str, Any]:
    config = PARTNER_CONFIGS.get(partner_type)
    if not config:
        raise ValueError(f"Unknown partner type: '{partner_type}'. "
                         f"Supported: {list(PARTNER_CONFIGS.keys())}")
    return config


# ─────────────────────────────────────────────────────────────
#  SHOPIFY CONNECTION TEST
# ─────────────────────────────────────────────────────────────

async def test_shopify_connection(store) -> Dict[str, Any]:
    """
    Hit GET /admin/api/{version}/shop.json — if 200, we're connected.
    `store` is a ShopifyStore ORM instance.
    """
    try:
        token    = decrypt_credential(store.api_access_token)
        base_url = store.store_url.rstrip("/")
        if not base_url.startswith("http"):
            base_url = f"https://{base_url}"
        url = f"{base_url}/admin/api/{store.api_version}/shop.json"

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers={"X-Shopify-Access-Token": token})

        if resp.status_code == 200:
            shop = resp.json().get("shop", {})
            return {"success": True,  "message": f"Connected to {shop.get('name', store.store_url)}"}
        if resp.status_code == 401:
            return {"success": False, "message": "Invalid access token — please re-check your Shopify API token"}
        return {"success": False, "message": f"Shopify returned HTTP {resp.status_code}"}

    except httpx.TimeoutException:
        return {"success": False, "message": "Connection timed out — check the store URL"}
    except Exception as exc:
        return {"success": False, "message": str(exc)}


# ─────────────────────────────────────────────────────────────
#  DELHIVERY CONNECTION TEST
# ─────────────────────────────────────────────────────────────

async def test_delhivery_connection(partner) -> Dict[str, Any]:
    """
    Hit GET /api/kinko/v1/invoice/charges/?format=json — a lightweight
    authenticated endpoint Delhivery exposes for token verification.
    """
    try:
        api_key = decrypt_credential(partner.api_key)
        url     = "https://track.delhivery.com/api/kinko/v1/invoice/charges/?format=json"

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                url,
                headers={"Authorization": f"Token {api_key}",
                         "Content-Type": "application/json"},
            )

        if resp.status_code in (200, 400):   # 400 = auth ok but bad params — still connected
            return {"success": True,  "message": f"Connected to Delhivery (client: {partner.client_name})"}
        if resp.status_code == 401:
            return {"success": False, "message": "Invalid API key — please re-check your Delhivery token"}
        return {"success": False, "message": f"Delhivery returned HTTP {resp.status_code}"}

    except httpx.TimeoutException:
        return {"success": False, "message": "Connection timed out"}
    except Exception as exc:
        return {"success": False, "message": str(exc)}


# ─────────────────────────────────────────────────────────────
#  BLUEDART CONNECTION TEST
# ─────────────────────────────────────────────────────────────

async def test_bluedart_connection(partner) -> Dict[str, Any]:
    try:
        api_key = decrypt_credential(partner.api_key)
        url     = "https://omapi.bluedart.com/in/transportation/waybill/v1/GenerateWayBill"

        # A lightweight auth probe — we expect 401 or 200 depending on key validity
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                url,
                headers={"JWTToken": api_key, "accept": "application/json"},
            )

        if resp.status_code in (200, 400, 422):
            return {"success": True,  "message": "Connected to Blue Dart"}
        if resp.status_code == 401:
            return {"success": False, "message": "Invalid Blue Dart API key"}
        return {"success": False, "message": f"Blue Dart returned HTTP {resp.status_code}"}

    except httpx.TimeoutException:
        return {"success": False, "message": "Connection timed out"}
    except Exception as exc:
        return {"success": False, "message": str(exc)}


# ─────────────────────────────────────────────────────────────
#  WHATSAPP META CONNECTION TEST
# ─────────────────────────────────────────────────────────────

async def test_whatsapp_connection(channel) -> Dict[str, Any]:
    """
    GET /{phone_number_id}?access_token=... — fetches phone number metadata.
    """
    try:
        token           = decrypt_credential(channel.access_token or channel.api_key)
        phone_number_id = channel.phone_number_id
        if not phone_number_id:
            return {"success": False, "message": "Phone Number ID is required for WhatsApp"}

        url = f"https://graph.facebook.com/v18.0/{phone_number_id}"

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params={"access_token": token})

        if resp.status_code == 200:
            data = resp.json()
            return {"success": True, "message": f"Connected — display number: {data.get('display_phone_number', phone_number_id)}"}
        if resp.status_code in (401, 403):
            return {"success": False, "message": "Invalid access token — re-check your Meta API token"}
        return {"success": False, "message": f"Meta API returned HTTP {resp.status_code}"}

    except httpx.TimeoutException:
        return {"success": False, "message": "Connection timed out"}
    except Exception as exc:
        return {"success": False, "message": str(exc)}


# ─────────────────────────────────────────────────────────────
#  UNIFIED DISPATCHER
# ─────────────────────────────────────────────────────────────

async def test_delivery_partner_connection(partner) -> Dict[str, Any]:
    if partner.partner_type == "delhivery":
        return await test_delhivery_connection(partner)
    if partner.partner_type == "bluedart":
        return await test_bluedart_connection(partner)
    if partner.partner_type == "india_post":
        # India Post: validate config completeness
        missing = []
        if not partner.customer_ids:
            missing.append("Contract IDs")
        if not partner.pickup_location_code:
            missing.append("Pickup Location Code")
        if not partner.client_id:
            missing.append("India Post Username")
        if not partner.api_key:
            missing.append("India Post Password")
        if missing:
            return {"success": False, "message": f"Missing required fields: {', '.join(missing)}"}
        env = "production" if partner.client_name == "production" else "sandbox"
        return {"success": True, "message": f"India Post configured ({env}) — {len(partner.customer_ids)} contract ID(s) saved"}
    # dtdc / amazon / others — config saved, live test not yet integrated
    return {"success": True, "message": f"{partner.display_name} configuration saved successfully"}


async def test_notification_connection(channel) -> Dict[str, Any]:
    if channel.channel_type == "whatsapp":
        return await test_whatsapp_connection(channel)
    if channel.channel_type in ("sms", "email"):
        return {"success": True, "message": f"{channel.channel_type.upper()} channel saved — no live test available yet"}
    return {"success": False, "message": f"Unknown channel type: {channel.channel_type}"}
