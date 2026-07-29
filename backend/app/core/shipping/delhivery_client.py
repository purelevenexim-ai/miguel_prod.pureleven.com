"""
Delhivery Shipping Integration
API Documentation: https://dlv.in/docs/
"""
import httpx
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class DelhiveryAPIClient:
    """
    Delhivery API Client
    Handles waybill creation, tracking, and shipping updates
    """

    BASE_URL = "https://track.delhivery.com/api"
    TEST_BASE_URL = "https://track.delhivery.com/test/api"

    def __init__(self, api_key: str, client_name: str, pickup_location: str = "685561", sandbox: bool = False):
        """
        Initialize Delhivery client
        
        Args:
            api_key: Delhivery API key from dashboard
            client_name: Your business name registered with Delhivery
            pickup_location: Location code (default: 685561 for Mumbai)
            sandbox: Use sandbox/test mode if True
        """
        self.api_key = api_key
        self.client_name = client_name
        self.pickup_location = pickup_location
        self.base_url = self.TEST_BASE_URL if sandbox else self.BASE_URL
        self.headers = {
            "Authorization": f"Token {api_key}",
            "Content-Type": "application/json",
        }

    async def create_waybill(
        self,
        order_id: str,
        customer_name: str,
        customer_phone: str,
        customer_email: str,
        shipping_address: str,
        city: str,
        state: str,
        pincode: str,
        weight_kg: float = 1.0,
        amount: Decimal = None,
        shipment_type: str = "FORWARD",  # FORWARD or RETURN
        reference_id: str = None,  # Your order ID for reference
    ) -> Dict[str, Any]:
        """
        Create a waybill (tracking number) in Delhivery
        
        Returns:
            {
                "success": bool,
                "waybill": "1234567890",  # Tracking number
                "message": str,
                "error": Optional[str]
            }
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Delhivery Waybill Creation API
                payload = {
                    "name": customer_name,
                    "email": customer_email,
                    "phone": customer_phone.replace("+91", "").replace("-", ""),  # Clean phone
                    "address": shipping_address,
                    "city": city,
                    "state": state,
                    "pin": pincode,
                    "order_date": datetime.now(timezone.utc).isoformat(),
                    "shipment_type": shipment_type,
                    "weight": weight_kg,
                    "amount": float(amount) if amount else 0,
                    "order_id": order_id,
                    "reference_id": reference_id or order_id,
                    "cod": float(amount) if amount else 0,  # COD amount
                }

                response = await client.post(
                    f"{self.base_url}/shipment/create/",
                    json=payload,
                    headers=self.headers,
                )

                if response.status_code == 200:
                    data = response.json()
                    if "waybill" in data:
                        return {
                            "success": True,
                            "waybill": data["waybill"],
                            "tracking_number": data["waybill"],
                            "message": "Waybill created successfully",
                        }
                    else:
                        return {
                            "success": False,
                            "error": data.get("detail", "No waybill returned"),
                            "message": "Failed to create waybill",
                        }
                else:
                    logger.error(f"Delhivery API error {response.status_code}: {response.text}")
                    return {
                        "success": False,
                        "error": response.text,
                        "message": f"API returned {response.status_code}",
                    }

            except Exception as e:
                logger.error(f"Delhivery waybill creation error: {str(e)}")
                return {
                    "success": False,
                    "error": str(e),
                    "message": "Network/connection error",
                }

    async def get_tracking_status(self, waybill: str) -> Dict[str, Any]:
        """
        Get current tracking status for a waybill
        
        Returns:
            {
                "success": bool,
                "status": "delivered" | "in_transit" | etc,
                "location": str,
                "last_update": datetime,
                "events": [...],
                "error": Optional[str]
            }
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Delhivery Tracking API
                response = await client.get(
                    f"{self.base_url}/shipment/track/?waybill={waybill}",
                    headers=self.headers,
                )

                if response.status_code == 200:
                    data = response.json()
                    
                    # Extract latest status
                    scans = data.get("scans", [])
                    latest_scan = scans[0] if scans else {}
                    
                    # Map Delhivery status to our enum
                    status_map = {
                        "Shipment Picked": "picked_up",
                        "In Transit": "in_transit",
                        "Out for Delivery": "out_for_delivery",
                        "Delivered": "delivered",
                        "Shipment Cancelled": "cancelled",
                        "Shipment Lost": "failed",
                        "RTO Delivered": "returned",
                    }
                    
                    delhivery_status = latest_scan.get("status", "pending")
                    mapped_status = status_map.get(delhivery_status, "in_transit")
                    
                    return {
                        "success": True,
                        "waybill": waybill,
                        "status": mapped_status,
                        "location": latest_scan.get("location", ""),
                        "location_code": latest_scan.get("facility_code", ""),
                        "last_update": latest_scan.get("date", ""),
                        "description": delhivery_status,
                        "events": [
                            {
                                "status": status_map.get(s.get("status", ""), "in_transit"),
                                "location": s.get("location", ""),
                                "time": s.get("date", ""),
                                "description": s.get("status", ""),
                            }
                            for s in scans[:10]  # Last 10 events
                        ],
                        "raw_data": data,
                    }
                else:
                    return {
                        "success": False,
                        "error": response.text,
                        "message": f"API returned {response.status_code}",
                    }

            except Exception as e:
                logger.error(f"Delhivery tracking error: {str(e)}")
                return {
                    "success": False,
                    "error": str(e),
                    "message": "Network/connection error",
                }

    async def get_tracking_by_reference(self, reference_id: str) -> Dict[str, Any]:
        """
        Look up a Delhivery shipment by your reference_id (Shopify order ID).
        Returns the waybill if found.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/shipment/track/?ref={reference_id}",
                    headers=self.headers,
                )
                if response.status_code == 200:
                    data = response.json()
                    # Delhivery returns ShipmentData list
                    shipments = data.get("ShipmentData", [])
                    if shipments:
                        waybill = shipments[0].get("Shipment", {}).get("WaybillNumber", "")
                        if waybill:
                            return {"success": True, "waybill": waybill, "raw": data}
                    return {"success": False, "waybill": None}
                else:
                    return {"success": False, "waybill": None, "error": response.text[:200]}
            except Exception as e:
                return {"success": False, "waybill": None, "error": str(e)}

    async def cancel_waybill(self, waybill: str) -> Dict[str, Any]:
        """Cancel a waybill"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/shipment/cancel/",
                    json={"waybill": waybill},
                    headers=self.headers,
                )

                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": "Waybill cancelled successfully",
                    }
                else:
                    return {
                        "success": False,
                        "error": response.text,
                    }

            except Exception as e:
                logger.error(f"Delhivery cancel error: {str(e)}")
                return {
                    "success": False,
                    "error": str(e),
                }

    async def get_pickup_locations(self) -> Dict[str, Any]:
        """
        Get available pickup locations
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/warehouse/",
                    headers=self.headers,
                )

                if response.status_code == 200:
                    return {
                        "success": True,
                        "locations": response.json(),
                    }
                else:
                    return {
                        "success": False,
                        "error": response.text,
                    }

            except Exception as e:
                logger.error(f"Delhivery locations error: {str(e)}")
                return {
                    "success": False,
                    "error": str(e),
                }

    async def test_connection(self) -> Dict[str, Any]:
        """
        Test Delhivery API connection
        """
        return await self.get_pickup_locations()


# Convenience function
async def test_delhivery_api(api_key: str, client_name: str) -> Dict[str, Any]:
    """Test Delhivery connection"""
    client = DelhiveryAPIClient(api_key, client_name)
    return await client.test_connection()
