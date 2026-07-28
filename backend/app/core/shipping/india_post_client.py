"""
India Post Bulk Customer API Integration
─────────────────────────────────────────
API Gateway : set via INDIA_POST_PROD_URL  (production)
Sandbox     : https://test.cept.gov.in/beextcustomer  (testing)

Auth        : POST /v1/access/login → Bearer token (15 min)
Refresh     : POST /v1/access/TokenWithRtoken
Tariff      : GET  /v1/speed-post/tariffs
              GET  /v1/parcel-tariff/calculate
              GET  /v1/letter-tariff/calculate
              GET  /v1/business-parcel-tariff/calculate
Pincode     : GET  /v1/pincode-search
Tracking    : GET  /v1/tracking/{trackingNumber}
              POST /v1/tracking/bulk
Booking     : POST /process-articles-file/:customerID
Label       : POST /v1/label/create/domestic
              POST /v1/label/create

Updated: 2026-03-02 — Full rewrite based on official API docs
"""
import httpx
import os
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Token cache — per customer_id
# ─────────────────────────────────────────────────────────────
_token_cache: Dict[str, Dict[str, Any]] = {}


class IndiaPostAPIClient:
    """
    India Post Bulk Customer API Client.
    Handles auth, tariff calculation, tracking, booking, and labels.
    """

    SANDBOX_URL = "https://test.cept.gov.in/beextcustomer"
    # Pincode/office lookup is on a SEPARATE base path (`bemasterdata`),
    # not the bulk-customer (`beextcustomer`) base.
    SANDBOX_MASTERDATA_URL = "https://test.cept.gov.in/bemasterdata"
    DEFAULT_PROD_URL = "https://apigw.indiapost.gov.in"
    DEFAULT_PROD_MASTERDATA_URL = "https://apigw.indiapost.gov.in"
    # Production base URLs — overridable via env vars.
    # The previous default `https://apigw.indiapost.gov.in` does not resolve in public DNS.
    # Production base URLs MUST be obtained from your India Post Developer Portal
    # (Subscribed APIs section shows the {base_path} for each environment).
    PROD_URL            = os.getenv("INDIA_POST_PROD_URL", DEFAULT_PROD_URL).strip()
    PROD_MASTERDATA_URL = os.getenv("INDIA_POST_PROD_MASTERDATA_URL", DEFAULT_PROD_MASTERDATA_URL).strip()

    def __init__(
        self,
        username: str,
        password: str,
        customer_id: str,
        sandbox: bool = True,
    ):
        self.username        = username
        self.customer_id     = customer_id
        self.password        = password
        self.sandbox         = sandbox
        self.base_url        = self.SANDBOX_URL if sandbox else self.PROD_URL
        self.masterdata_url  = self.SANDBOX_MASTERDATA_URL if sandbox else self.PROD_MASTERDATA_URL

    @staticmethod
    def _uses_placeholder_url(value: str, placeholder: str) -> bool:
        return not value or value.rstrip("/") == placeholder.rstrip("/")

    def _configuration_error(self, *, masterdata: bool = False) -> Optional[str]:
        if self.sandbox:
            return None

        missing = []
        if self._uses_placeholder_url(self.base_url, self.DEFAULT_PROD_URL):
            missing.append("INDIA_POST_PROD_URL")
        if masterdata and self._uses_placeholder_url(self.masterdata_url, self.DEFAULT_PROD_MASTERDATA_URL):
            missing.append("INDIA_POST_PROD_MASTERDATA_URL")
        if not missing:
            return None

        return (
            "ConfigurationError: India Post production base URL is not configured "
            f"({', '.join(missing)}). Use the subscribed API base path from the India Post portal."
        )

    def _raise_if_configuration_missing(self, *, masterdata: bool = False) -> None:
        error = self._configuration_error(masterdata=masterdata)
        if error:
            raise RuntimeError(error)

    # ═════════════════════════════════════════════════════════
    # AUTH
    # ═════════════════════════════════════════════════════════

    async def _get_token(self) -> str:
        """Get a valid access token, refreshing or re-authenticating as needed."""
        cache_key = f"{self.customer_id}:{self.base_url}"
        cached = _token_cache.get(cache_key)

        if cached and cached.get("expires_at", 0) > time.time() + 30:
            return cached["access_token"]

        if not self.username or not self.password:
            raise RuntimeError("India Post username/password are not configured")

        # Try refresh token first
        if cached and cached.get("refresh_token") and cached.get("refresh_expires_at", 0) > time.time() + 30:
            try:
                token_data = await self._refresh_token(cached["refresh_token"])
                _token_cache[cache_key] = self._parse_token_response(token_data)
                return _token_cache[cache_key]["access_token"]
            except Exception:
                logger.warning("India Post token refresh failed, re-authenticating")

        # Full login
        token_data = await self._login()
        _token_cache[cache_key] = self._parse_token_response(token_data)
        return _token_cache[cache_key]["access_token"]

    async def _login(self) -> Dict:
        """POST /v1/access/login — get access + refresh tokens."""
        self._raise_if_configuration_missing()
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/v1/access/login",
                headers={"Content-Type": "application/json", "accept": "application/json"},
                json={"username": self.username, "password": self.password},
            )
            resp.raise_for_status()
            body = resp.json()
            if not body.get("success"):
                raise Exception(f"India Post login failed: {body}")
            return body["data"]

    async def _refresh_token(self, refresh_token: str) -> Dict:
        """POST /v1/access/TokenWithRtoken — refresh access token."""
        self._raise_if_configuration_missing()
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/v1/access/TokenWithRtoken",
                headers={
                    "accept": "application/json",
                    "Authorization": f"Bearer {refresh_token}",
                },
            )
            resp.raise_for_status()
            body = resp.json()
            if not body.get("success"):
                raise Exception(f"India Post token refresh failed: {body}")
            return body["data"]

    @staticmethod
    def _parse_token_response(data: Dict) -> Dict:
        now = time.time()
        return {
            "access_token":       data["access_token"],
            "refresh_token":      data.get("refresh_token", ""),
            "expires_at":         now + data.get("expires_in", 900),
            "refresh_expires_at": now + data.get("refresh_expires_in", 1800),
        }

    async def _auth_headers(self) -> Dict[str, str]:
        token = await self._get_token()
        return {
            "Authorization": f"Bearer {token}",
            "accept": "application/json",
            "Content-Type": "application/json",
        }

    # ═════════════════════════════════════════════════════════
    # PINCODE SEARCH
    # ═════════════════════════════════════════════════════════

    async def pincode_search(self, pincode: str, limit: int = 50, office_type: str = "post") -> Dict[str, Any]:
        """
        GET {masterdata}/v1/offices/limited-details?pincode=...&limit=...&office-type=post
        Validates a pincode and returns post office details.
        Per India Post docs: lives on the `bemasterdata` base path (NOT `beextcustomer`)
        and REQUIRES Bearer authentication + `office-type` query param.
        """
        try:
            self._raise_if_configuration_missing(masterdata=True)
            if not self.username or not self.password:
                return {
                    "success": False,
                    "error": "AuthError: India Post username/password are required for pincode lookup",
                }
            token = await self._get_token()
        except Exception as e:
            err_msg = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
            return {"success": False, "error": f"Auth failed: {err_msg}"}
        headers = {"accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(
                    f"{self.masterdata_url}/v1/offices/limited-details",
                    params={"pincode": pincode, "limit": limit, "office-type": office_type},
                    headers=headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    # API returns a bare list; wrap for consistency with rest of client
                    if isinstance(data, list):
                        return {"success": True, "data": data, "count": len(data)}
                    return data
                return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:300]}"}
            except Exception as e:
                err_msg = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
                logger.error(f"India Post pincode search error: {err_msg}")
                return {"success": False, "error": err_msg}

    # ═════════════════════════════════════════════════════════
    # TARIFF CALCULATION
    # ═════════════════════════════════════════════════════════

    async def calculate_speed_post_tariff(
        self,
        weight: int,
        source_pincode: str,
        destination_pincode: str,
        length: Optional[float] = None,
        width: Optional[float] = None,
        height: Optional[float] = None,
        ins_amount: Optional[float] = None,
        pod: bool = False,
        reg: bool = False,
        otp: bool = False,
    ) -> Dict[str, Any]:
        """
        GET /v1/speed-post/tariffs
        Calculate Speed Post tariff.
        Weight in grams. Dimensions in cm.
        """
        params: Dict[str, Any] = {
            "product-code": "SP",
            "weight": weight,
            "source-pincode": source_pincode,
            "destination-pincode": destination_pincode,
        }
        if length: params["length"] = length
        if width:  params["width"]  = width
        if height: params["height"] = height
        if ins_amount: params["INS"] = ins_amount
        if pod: params["POD"] = "YES"
        if reg: params["REG"] = "YES"
        if otp: params["OTP"] = "YES"

        return await self._get_tariff("/v1/speed-post/tariffs", params)

    async def calculate_parcel_tariff(
        self,
        weight: int,
        source_pincode: str,
        destination_pincode: str,
        length: float,
        width: float,
        height: float,
        cod: bool = False,
        cod_amount: float = 0,
        insurance: bool = False,
        ins_amount: float = 0,
    ) -> Dict[str, Any]:
        """
        GET /v1/parcel-tariff/calculate
        Calculate Parcel tariff.
        Weight in grams. Dimensions in cm.
        """
        params: Dict[str, Any] = {
            "product-code": "PARCEL",
            "weight": weight,
            "source-pincode": source_pincode,
            "destination-pincode": destination_pincode,
            "length": length,
            "width": width,
            "height": height,
        }
        if cod:
            params["cod"] = "true"
            params["cod-amount"] = cod_amount
        if insurance:
            params["insurance"] = "true"
            params["ins-amount"] = ins_amount

        return await self._get_tariff("/v1/parcel-tariff/calculate", params)

    async def calculate_business_parcel_tariff(
        self,
        weight: int,
        source_pincode: str,
        destination_pincode: str,
        length: Optional[float] = None,
        width: Optional[float] = None,
        height: Optional[float] = None,
        ins_amount: Optional[float] = None,
        cod: bool = False,
        cod_amount: float = 0,
    ) -> Dict[str, Any]:
        """
        GET /v1/business-parcel-tariff/calculate
        Calculate Business Parcel tariff.
        """
        params: Dict[str, Any] = {
            "product-code": "BP",
            "weight": weight,
            "source-pincode": source_pincode,
            "destination-pincode": destination_pincode,
        }
        if length: params["length"] = length
        if width:  params["width"]  = width
        if height: params["height"] = height
        if ins_amount: params["ins"] = ins_amount
        if cod:
            params["cod"] = "true"
            params["cod-amount"] = cod_amount

        return await self._get_tariff("/v1/business-parcel-tariff/calculate", params)

    async def calculate_letter_tariff(
        self,
        weight: int,
        source_pincode: str,
        destination_pincode: str,
        reg: bool = False,
        ack: bool = False,
        ins: bool = False,
        ins_amount: float = 0,
    ) -> Dict[str, Any]:
        """
        GET /v1/letter-tariff/calculate
        Calculate Letter tariff.
        """
        params: Dict[str, Any] = {
            "product-code": "LETTER",
            "weight": weight,
            "source-pincode": source_pincode,
            "destination-pincode": destination_pincode,
        }
        if reg: params["reg"] = "true"
        if ack: params["ack"] = "true"
        if ins:
            params["ins"] = "true"
            params["ins-amount"] = ins_amount

        return await self._get_tariff("/v1/letter-tariff/calculate", params)

    async def _get_tariff(self, endpoint: str, params: Dict) -> Dict[str, Any]:
        """Shared tariff GET request. India Post tariff endpoints require Bearer auth."""
        try:
            self._raise_if_configuration_missing()
            headers = await self._auth_headers()
        except Exception as e:
            err_msg = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
            logger.error(f"India Post tariff configuration error: {err_msg}")
            return {"success": False, "error": err_msg}
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(
                    f"{self.base_url}{endpoint}",
                    params=params,
                    headers=headers,
                )
                if resp.status_code == 200:
                    return resp.json()
                logger.error(f"India Post tariff error {resp.status_code}: {resp.text}")
                return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text}"}
            except Exception as e:
                err_msg = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
                logger.error(f"India Post tariff calculation error: {err_msg}")
                return {"success": False, "error": err_msg}

    # ═════════════════════════════════════════════════════════
    # TRACKING
    # ═════════════════════════════════════════════════════════

    async def track_article(self, tracking_number: str) -> Dict[str, Any]:
        """
        GET /v1/tracking/{trackingNumber}
        Track a single article. Requires auth.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                headers = await self._auth_headers()
                resp = await client.get(
                    f"{self.base_url}/v1/tracking/{tracking_number}",
                    headers=headers,
                )
                if resp.status_code == 401:
                    _token_cache.pop(f"{self.customer_id}:{self.base_url}", None)
                    headers = await self._auth_headers()
                    resp = await client.get(
                        f"{self.base_url}/v1/tracking/{tracking_number}",
                        headers=headers,
                    )
                if resp.status_code == 200:
                    data = resp.json()
                    status_map = {
                        "In Transit": "in_transit",
                        "Delivered": "delivered",
                        "Out for Delivery": "out_for_delivery",
                        "Item received at origin facility": "picked_up",
                        "Booked": "pending",
                        "Return to Sender": "returned",
                        "Cancelled": "cancelled",
                    }

                    def to_status(value: str) -> str:
                        lower = (value or "").lower()
                        if "out for delivery" in lower:
                            return "out_for_delivery"
                        if "deliver" in lower and "not deliver" not in lower and "undeliver" not in lower:
                            return "delivered"
                        if any(token in lower for token in ("rto", "return", "returned")):
                            return "returned"
                        if any(token in lower for token in ("booked", "bagged", "dispatched", "received", "transit")):
                            return "in_transit"
                        return status_map.get(value, "in_transit")

                    if isinstance(data, list):
                        first = data[0] if data and isinstance(data[0], dict) else {}
                        booking_details = first.get("booking_details") if isinstance(first.get("booking_details"), dict) else {}
                        events = first.get("tracking_details") or first.get("trackingDetails") or data
                        latest_event = events[0] if events and isinstance(events[0], dict) else {}
                        delivered_status = first.get("del_status") if isinstance(first.get("del_status"), dict) else {}
                        current_status = (
                            latest_event.get("event")
                            or latest_event.get("remarks")
                            or delivered_status.get("del_status")
                            or first.get("currentStatus")
                            or first.get("status")
                            or first.get("event")
                            or first.get("description")
                            or "In Transit"
                        )
                        return {
                            "success": True,
                            "tracking_number": tracking_number,
                            "status": to_status(current_status),
                            "status_text": current_status,
                            "origin": booking_details.get("booked_at", ""),
                            "destination": booking_details.get("delivery_location", ""),
                            "events": events,
                            "booking_details": booking_details,
                            "raw": data,
                        }

                    if not isinstance(data, dict):
                        return {"success": False, "error": "Unexpected tracking response", "raw": data}

                    if data.get("success") is False:
                        return {"success": False, "error": data.get("message", "Unknown error"), "raw": data}

                    td = data.get("data", data)
                    if isinstance(td, list):
                        first = td[0] if td and isinstance(td[0], dict) else {}
                        events = first.get("tracking_details") or first.get("trackingDetails") or td
                        td = first
                    elif isinstance(td, dict):
                        events = td.get("history") or td.get("events") or td.get("trackingHistory") or td.get("tracking_details") or td.get("trackingDetails") or []
                    else:
                        events = []
                        td = {}

                    latest_event = events[0] if events and isinstance(events[0], dict) else {}
                    booking_details = td.get("booking_details") if isinstance(td.get("booking_details"), dict) else {}
                    delivered_status = td.get("del_status") if isinstance(td.get("del_status"), dict) else {}
                    current_status = (
                        latest_event.get("event")
                        or latest_event.get("remarks")
                        or delivered_status.get("del_status")
                        or td.get("currentStatus")
                        or td.get("current_status")
                        or td.get("status")
                        or td.get("deliveryStatus")
                        or "In Transit"
                    )
                    return {
                        "success": True,
                        "tracking_number": tracking_number,
                        "status": to_status(current_status),
                        "status_text": current_status,
                        "origin": td.get("origin", "") or booking_details.get("booked_at", ""),
                        "destination": td.get("destination", "") or booking_details.get("delivery_location", ""),
                        "estimated_delivery": td.get("estimatedDelivery"),
                        "booking_details": booking_details,
                        "events": events,
                        "raw": data,
                    }
                return {"success": False, "error": f"HTTP {resp.status_code}"}
            except Exception as e:
                logger.error(f"India Post tracking error: {e}")
                return {"success": False, "error": str(e)}

    async def track_bulk(self, tracking_numbers: List[str]) -> Dict[str, Any]:
        """
        POST /v1/tracking/bulk
        Track up to 50 articles at once. Requires auth.
        """
        if len(tracking_numbers) > 50:
            return {"success": False, "error": "Maximum 50 articles per bulk request"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                headers = await self._auth_headers()
                resp = await client.post(
                    f"{self.base_url}/v1/tracking/bulk",
                    headers=headers,
                    json={"bulk": tracking_numbers},
                )
                if resp.status_code == 200:
                    return resp.json()
                return {"success": False, "error": f"HTTP {resp.status_code}"}
            except Exception as e:
                logger.error(f"India Post bulk tracking error: {e}")
                return {"success": False, "error": str(e)}

    async def get_tracking_status(self, tracking_number: str) -> Dict[str, Any]:
        """Compatibility wrapper used by older shipping workers."""
        return await self.track_article(tracking_number)

    async def fetch_recent_tracking(self, days: int = 7) -> Dict[str, Any]:
        """
        Fetch recent India Post article/tracking rows for reconciliation.

        India Post exposes this report under tenant-specific subscribed API paths.
        Configure INDIA_POST_RECENT_TRACKING_ENDPOINT with either a full URL or a
        path under the bulk-customer base URL. If the endpoint is not configured,
        the application still refreshes orders that already have tracking numbers.
        """
        endpoint = os.getenv("INDIA_POST_RECENT_TRACKING_ENDPOINT", "").strip()
        if not endpoint:
            return {
                "success": False,
                "unsupported": True,
                "error": "INDIA_POST_RECENT_TRACKING_ENDPOINT is not configured",
            }

        method = os.getenv("INDIA_POST_RECENT_TRACKING_METHOD", "GET").strip().upper() or "GET"
        to_date = datetime.now(timezone.utc).date()
        from_date = to_date - timedelta(days=max(days, 1))
        url = endpoint if endpoint.startswith("http") else f"{self.base_url}{endpoint}"
        payload = {
            "customerId": self.customer_id,
            "customerID": self.customer_id,
            "fromDate": from_date.isoformat(),
            "toDate": to_date.isoformat(),
            "days": max(days, 1),
        }

        try:
            headers = await self._auth_headers()
        except Exception as e:
            err_msg = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
            return {"success": False, "error": err_msg}

        async with httpx.AsyncClient(timeout=45.0) as client:
            try:
                if method == "POST":
                    resp = await client.post(url, headers=headers, json=payload)
                else:
                    resp = await client.get(url, headers=headers, params=payload)
                if resp.status_code == 200:
                    body = resp.json()
                    if isinstance(body, dict):
                        body.setdefault("success", True)
                        return body
                    return {"success": True, "data": body}
                return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:300]}"}
            except Exception as e:
                err_msg = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
                logger.error(f"India Post recent tracking fetch error: {err_msg}")
                return {"success": False, "error": err_msg}

    # ═════════════════════════════════════════════════════════
    # LABEL GENERATION
    # ═════════════════════════════════════════════════════════

    async def generate_domestic_label(self, label_data: Dict) -> Dict[str, Any]:
        """
        POST /v1/label/create/domestic
        Generate printable address label PDF. Requires auth.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                headers = await self._auth_headers()
                resp = await client.post(
                    f"{self.base_url}/v1/label/create/domestic",
                    headers=headers,
                    json=label_data,
                )
                if resp.status_code == 200:
                    ct = resp.headers.get("content-type", "")
                    if "application/pdf" in ct:
                        return {"success": True, "pdf_bytes": resp.content, "format": "pdf"}
                    elif "application/json" in ct:
                        return {"success": True, "data": resp.json()}
                    else:
                        return {"success": True, "data": resp.content, "format": ct}
                return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text}"}
            except Exception as e:
                logger.error(f"India Post label generation error: {e}")
                return {"success": False, "error": str(e)}

    # ═════════════════════════════════════════════════════════
    # CONNECTION TEST
    # ═════════════════════════════════════════════════════════

    async def test_connection(self) -> Dict[str, Any]:
        """Test API connectivity by attempting login + pincode search."""
        try:
            token = await self._get_token()
            if not token:
                return {"success": False, "message": "Authentication failed"}
            result = await self.pincode_search("685561", limit=1)
            if result.get("success"):
                return {
                    "success": True,
                    "message": "India Post API connected successfully",
                    "environment": "sandbox" if self.sandbox else "production",
                }
            return {
                "success": False,
                "message": result.get("error") or result.get("message") or "Pincode lookup failed after authentication",
                "environment": "sandbox" if self.sandbox else "production",
            }
        except Exception as e:
            return {"success": False, "message": f"Connection failed: {str(e)}"}


# ─────────────────────────────────────────────────────────────
# Convenience functions
# ─────────────────────────────────────────────────────────────

async def test_india_post_api(username: str, password: str, customer_id: str, sandbox: bool = True) -> Dict[str, Any]:
    """Quick connection test."""
    client = IndiaPostAPIClient(username, password, customer_id, sandbox=sandbox)
    return await client.test_connection()


async def calculate_tariff(
    service_type: str,
    weight: int,
    source_pincode: str,
    destination_pincode: str,
    username: str = "",
    password: str = "",
    customer_id: str = "",
    length: float = 0,
    width: float = 0,
    height: float = 0,
    cod: bool = False,
    cod_amount: float = 0,
    insurance: bool = False,
    ins_amount: float = 0,
    sandbox: bool = True,
) -> Dict[str, Any]:
    """
    Standalone tariff calculation.
    service_type: 'speed_post' | 'parcel' | 'business_parcel' | 'letter'
    weight: grams
    """
    client = IndiaPostAPIClient(username, password, customer_id, sandbox=sandbox)

    if service_type == "speed_post":
        return await client.calculate_speed_post_tariff(
            weight=weight,
            source_pincode=source_pincode,
            destination_pincode=destination_pincode,
            length=length or None,
            width=width or None,
            height=height or None,
            ins_amount=ins_amount or None,
            pod=cod,
        )
    elif service_type == "parcel":
        return await client.calculate_parcel_tariff(
            weight=weight,
            source_pincode=source_pincode,
            destination_pincode=destination_pincode,
            length=length or 10,
            width=width or 10,
            height=height or 10,
            cod=cod,
            cod_amount=cod_amount,
            insurance=insurance,
            ins_amount=ins_amount,
        )
    elif service_type == "business_parcel":
        return await client.calculate_business_parcel_tariff(
            weight=weight,
            source_pincode=source_pincode,
            destination_pincode=destination_pincode,
            length=length or None,
            width=width or None,
            height=height or None,
            ins_amount=ins_amount or None,
            cod=cod,
            cod_amount=cod_amount,
        )
    elif service_type == "letter":
        return await client.calculate_letter_tariff(
            weight=weight,
            source_pincode=source_pincode,
            destination_pincode=destination_pincode,
        )
    else:
        return {"success": False, "error": f"Unknown service type: {service_type}"}
