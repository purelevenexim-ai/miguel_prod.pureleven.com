"""
Shopify Admin API Client
Fetches orders and abandoned checkouts from Shopify.
Uses the Admin REST API (api_version from store config).
"""
import httpx
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


class ShopifyAPIClient:
    """
    Shopify Admin REST API client.
    Handles order fetching, abandoned checkout fetching, and order status updates.
    """

    def __init__(self, store_url: str, access_token: str, api_version: str = "2024-01"):
        """
        Args:
            store_url:    e.g. 'purelevenexim.myshopify.com'
            access_token: shpat_… (Admin API access token)
            api_version:  e.g. '2024-01'
        """
        self.store_url    = store_url.rstrip("/")
        self.access_token = access_token
        self.api_version  = api_version
        self.base_url     = f"https://{self.store_url}/admin/api/{self.api_version}"
        self.headers = {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json",
        }

    # ── Orders ──────────────────────────────────────────────────

    async def get_orders(
        self,
        limit: int = 50,
        status: str = "any",          # any | open | closed | cancelled
        since_id: Optional[str] = None,
        created_at_min: Optional[datetime] = None,
        updated_at_min: Optional[datetime] = None,
        fulfillment_status: Optional[str] = None,  # any | shipped | partial | unshipped | unfulfilled
        financial_status: Optional[str] = None,    # any | paid | pending | refunded
    ) -> Dict[str, Any]:
        """
        Fetch orders from Shopify Admin API.

        Returns:
            {"success": bool, "orders": [...], "count": int, "error": str|None}
        """
        params: Dict[str, Any] = {
            "limit": min(limit, 250),
            "status": status,
        }
        if since_id:
            params["since_id"] = since_id
        if created_at_min:
            params["created_at_min"] = created_at_min.isoformat()
        if updated_at_min:
            params["updated_at_min"] = updated_at_min.isoformat()
        if fulfillment_status:
            params["fulfillment_status"] = fulfillment_status
        if financial_status:
            params["financial_status"] = financial_status

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/orders.json",
                    headers=self.headers,
                    params=params,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    orders = data.get("orders", [])
                    return {"success": True, "orders": orders, "count": len(orders)}
                else:
                    logger.error(f"Shopify orders API {resp.status_code}: {resp.text[:300]}")
                    return {"success": False, "orders": [], "count": 0,
                            "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
            except Exception as e:
                logger.error(f"Shopify orders fetch error: {e}")
                return {"success": False, "orders": [], "count": 0, "error": str(e)}

    async def get_last_n_orders(self, n: int = 5) -> Dict[str, Any]:
        """Fetch the most recent N orders from Shopify."""
        return await self.get_orders(limit=n, status="any")

    async def get_orders_since(self, since: datetime) -> Dict[str, Any]:
        """Fetch all orders updated since a given datetime (for incremental sync)."""
        return await self.get_orders(
            limit=250,
            status="any",
            updated_at_min=since,
        )

    # ── Abandoned Checkouts ─────────────────────────────────────

    async def get_abandoned_checkouts(
        self,
        limit: int = 50,
        since_id: Optional[str] = None,
        created_at_min: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Fetch abandoned checkouts from Shopify Admin API.
        These become leads in the CRM.

        Returns:
            {"success": bool, "checkouts": [...], "count": int, "error": str|None}
        """
        params: Dict[str, Any] = {"limit": min(limit, 250)}
        if since_id:
            params["since_id"] = since_id
        if created_at_min:
            params["created_at_min"] = created_at_min.isoformat()

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/checkouts.json",
                    headers=self.headers,
                    params=params,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    checkouts = data.get("checkouts", [])
                    return {"success": True, "checkouts": checkouts, "count": len(checkouts)}
                else:
                    logger.error(f"Shopify checkouts API {resp.status_code}: {resp.text[:300]}")
                    return {"success": False, "checkouts": [], "count": 0,
                            "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
            except Exception as e:
                logger.error(f"Shopify checkouts fetch error: {e}")
                return {"success": False, "checkouts": [], "count": 0, "error": str(e)}

    # ── Single Order ────────────────────────────────────────────

    async def get_order(self, shopify_order_id: str) -> Dict[str, Any]:
        """Fetch a single order by Shopify order ID."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/orders/{shopify_order_id}.json",
                    headers=self.headers,
                )
                if resp.status_code == 200:
                    return {"success": True, "order": resp.json().get("order", {})}
                else:
                    return {"success": False, "order": None,
                            "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
            except Exception as e:
                return {"success": False, "order": None, "error": str(e)}

    # ── Delhivery shipment lookup ────────────────────────────────
    # (Delhivery uses its own client — this is just the Shopify part)

    async def test_connection(self) -> Dict[str, Any]:
        """Test that the access token is valid by fetching shop info."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/shop.json",
                    headers=self.headers,
                )
                if resp.status_code == 200:
                    shop = resp.json().get("shop", {})
                    return {
                        "success": True,
                        "shop_name": shop.get("name"),
                        "email": shop.get("email"),
                        "plan": shop.get("plan_name"),
                    }
                else:
                    return {"success": False, "error": f"HTTP {resp.status_code}"}
            except Exception as e:
                return {"success": False, "error": str(e)}

    # ── Webhook Registration ─────────────────────────────────────

    async def list_webhooks(self) -> Dict[str, Any]:
        """List currently registered webhooks."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/webhooks.json",
                    headers=self.headers,
                )
                if resp.status_code == 200:
                    return {"success": True, "webhooks": resp.json().get("webhooks", [])}
                return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
            except Exception as e:
                return {"success": False, "error": str(e)}

    async def register_webhook(self, topic: str, address: str) -> Dict[str, Any]:
        """Register a single webhook subscription."""
        payload = {"webhook": {"topic": topic, "address": address, "format": "json"}}
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/webhooks.json",
                    headers=self.headers,
                    json=payload,
                )
                if resp.status_code in (200, 201):
                    return {"success": True, "webhook": resp.json().get("webhook", {})}
                return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:300]}"}
            except Exception as e:
                return {"success": False, "error": str(e)}

    async def delete_webhook(self, webhook_id: int) -> Dict[str, Any]:
        """Delete an existing webhook subscription."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.delete(
                    f"{self.base_url}/webhooks/{webhook_id}.json",
                    headers=self.headers,
                )
                return {"success": resp.status_code == 200}
            except Exception as e:
                return {"success": False, "error": str(e)}

    async def register_crm_webhooks(self, crm_base_url: str) -> Dict[str, Any]:
        """
        Register all CRM-required webhooks on this Shopify store.
        Idempotent: skips already-registered topics.
        """
        topics_needed = [
            ("orders/create",  f"{crm_base_url}/webhooks/shopify/order-created"),
            ("orders/updated", f"{crm_base_url}/webhooks/shopify/order-updated"),
            ("orders/cancelled", f"{crm_base_url}/webhooks/shopify/order-updated"),
            ("orders/fulfilled", f"{crm_base_url}/webhooks/shopify/order-updated"),
        ]

        existing = await self.list_webhooks()
        existing_topics = {w["topic"] for w in (existing.get("webhooks") or [])}

        results = []
        for topic, address in topics_needed:
            if topic in existing_topics:
                results.append({"topic": topic, "status": "already_registered"})
                continue
            reg = await self.register_webhook(topic, address)
            results.append({
                "topic": topic,
                "status": "registered" if reg["success"] else "failed",
                "error": reg.get("error"),
            })

        success_count = sum(1 for r in results if r["status"] in ("registered", "already_registered"))
        return {
            "success": success_count == len(topics_needed),
            "results": results,
            "registered": success_count,
            "total": len(topics_needed),
        }

