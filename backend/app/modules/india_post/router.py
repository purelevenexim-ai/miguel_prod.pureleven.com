"""
India Post Tariff & Pincode API Router
───────────────────────────────────────
Endpoints for the frontend to auto-calculate shipping tariff
when India Post is selected as the delivery partner.

GET  /api/india-post/tariff      — Calculate tariff (speed_post or parcel)
GET  /api/india-post/pincode     — Validate & lookup pincode
POST /api/india-post/test-connection — Test API auth
GET  /api/india-post/track/{tracking_number} — Track single article
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.core.auth.tenant import get_current_tenant_user, require_roles
from app.models.employee import Employee, RoleEnum
from app.core.shipping.india_post_client import IndiaPostAPIClient, calculate_tariff
from app.modules.shipping_config import service
from app.modules.orders import tracking_sync_service

router = APIRouter(prefix="/api/india-post", tags=["India Post"])


def _india_post_error_is_unreachable(err: str) -> bool:
    return (
        not err
        or "ConnectTimeout" in err
        or "ConnectError" in err
        or "Name or service not known" in err
        or "nodename nor servname" in err
        or "NameResolutionError" in err
        or "getaddrinfo" in err
    )


def _india_post_error_is_config(err: str) -> bool:
    return "ConfigurationError" in err


def _india_post_error_is_validation(err: str) -> bool:
    return "Validation failed" in err or err.startswith("HTTP 400:")


# ─────────────────────────────────────────────────────────────
# TARIFF CALCULATION
# ─────────────────────────────────────────────────────────────

@router.get("/tariff")
async def get_tariff(
    service_type: str = Query(..., alias="service", description="speed_post | parcel | business_parcel | letter"),
    weight: int = Query(..., description="Weight in grams"),
    source_pincode: str = Query(..., description="Origin pincode (e.g., 685561)"),
    destination_pincode: str = Query(..., description="Destination pincode"),
    length: float = Query(0, description="Length in cm"),
    width: float = Query(0, description="Width in cm"),
    height: float = Query(0, description="Height in cm"),
    cod: bool = Query(False, description="Is COD?"),
    cod_amount: float = Query(0, description="COD amount in INR"),
    insurance: bool = Query(False, description="Insurance opted?"),
    ins_amount: float = Query(0, description="Insurance value in INR"),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """
    Calculate India Post tariff for a given service type.
    Environment (sandbox vs production) is read from the tenant's
    India Post DeliveryPartner config (client_name field).
    """
    if service_type not in ("speed_post", "parcel", "business_parcel", "letter"):
        raise HTTPException(400, "service must be: speed_post, parcel, business_parcel, or letter")
    if weight <= 0:
        raise HTTPException(400, "weight must be > 0 grams")
    if service_type == "parcel" and not 501 <= weight <= 35000:
        raise HTTPException(400, "Parcel service requires weight between 501 and 35000 grams. Use Speed Post for lighter shipments.")
    if len(source_pincode) != 6 or len(destination_pincode) != 6:
        raise HTTPException(400, "pincodes must be 6 digits")

    # Read environment from tenant's India Post partner config
    from app.models.shipping_config import DeliveryPartner
    ip_partner = db.query(DeliveryPartner).filter(
        DeliveryPartner.tenant_id == current_user.tenant_id,
        DeliveryPartner.partner_type == "india_post",
        DeliveryPartner.is_active == True,
    ).first()
    if not ip_partner:
        raise HTTPException(400, "India Post not configured — add in Tenant Admin → Shipping Config")

    username = ip_partner.client_id or ""
    password = service.decrypt_credential(ip_partner.api_key) if ip_partner.api_key else ""
    cust_id = (ip_partner.customer_ids[0]["id"] if ip_partner.customer_ids else "") or ""
    use_sandbox = (ip_partner.client_name or "sandbox") != "production"

    if not username or not password:
        raise HTTPException(400, "India Post username/password not configured — edit the delivery partner in Shipping Config")

    result = await calculate_tariff(
        service_type=service_type,
        weight=weight,
        source_pincode=source_pincode,
        destination_pincode=destination_pincode,
        username=username,
        password=password,
        customer_id=cust_id,
        length=length,
        width=width,
        height=height,
        cod=cod,
        cod_amount=cod_amount,
        insurance=insurance,
        ins_amount=ins_amount,
        sandbox=use_sandbox,
    )

    if result.get("success") is False:
        err = result.get("error", "") or ""
        if _india_post_error_is_config(err):
            env_label = "production" if not use_sandbox else "sandbox"
            raise HTTPException(
                503,
                f"India Post {env_label} API is not configured on this server. "
                "Set INDIA_POST_PROD_URL before retrying. Please enter shipping cost manually."
            )
        # ConnectTimeout / ConnectError / NXDOMAIN → API unreachable
        # (IP whitelisting, DNS, or wrong production base URL)
        if _india_post_error_is_unreachable(err):
            env_label = "production" if not use_sandbox else "sandbox"
            raise HTTPException(
                503,
                f"India Post {env_label} API is not reachable from the server. "
                "Check IP whitelisting, DNS, and the configured base URL "
                "(set INDIA_POST_PROD_URL env var if needed). "
                "Please enter shipping cost manually."
            )
        if _india_post_error_is_validation(err):
            raise HTTPException(400, f"India Post request validation failed: {err}")
        raise HTTPException(502, f"India Post API error: {err}")

    return result


# ─────────────────────────────────────────────────────────────
# PINCODE LOOKUP
# ─────────────────────────────────────────────────────────────

@router.get("/pincode")
async def lookup_pincode(
    pincode: str = Query(..., description="6-digit pincode"),
    limit: int = Query(10, description="Max results"),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """
    Validate a pincode and get post office details.
    Useful for auto-filling city/state from pincode.
    """
    if len(pincode) != 6 or not pincode.isdigit():
        raise HTTPException(400, "Pincode must be 6 digits")

    from app.models.shipping_config import DeliveryPartner
    ip_partner = db.query(DeliveryPartner).filter(
        DeliveryPartner.tenant_id == current_user.tenant_id,
        DeliveryPartner.partner_type == "india_post",
        DeliveryPartner.is_active == True,
    ).first()
    if not ip_partner:
        raise HTTPException(400, "India Post not configured — add in Tenant Admin → Shipping Config")

    username = ip_partner.client_id or ""
    password = service.decrypt_credential(ip_partner.api_key) if ip_partner.api_key else ""
    cust_id = (ip_partner.customer_ids[0]["id"] if ip_partner.customer_ids else "") or ""
    use_sandbox = (ip_partner.client_name or "sandbox") != "production"

    if not username or not password:
        raise HTTPException(400, "India Post username/password not configured — edit the delivery partner in Shipping Config")

    client = IndiaPostAPIClient(username, password, cust_id, sandbox=use_sandbox)
    result = await client.pincode_search(pincode, limit=limit)

    if result.get("success") is False:
        err = result.get("error", "") or ""
        if _india_post_error_is_config(err):
            env_label = "production" if not use_sandbox else "sandbox"
            raise HTTPException(
                503,
                f"India Post {env_label} pincode lookup is not configured on this server. "
                "Set INDIA_POST_PROD_URL and INDIA_POST_PROD_MASTERDATA_URL before retrying."
            )
        if _india_post_error_is_unreachable(err):
            env_label = "production" if not use_sandbox else "sandbox"
            raise HTTPException(
                503,
                f"India Post {env_label} masterdata API is not reachable from the server. "
                "Check IP whitelisting, DNS, and the configured base URL."
            )
        raise HTTPException(502, f"India Post API error: {result.get('error', 'Unknown')}")

    return result


# ─────────────────────────────────────────────────────────────
# TRACKING
# ─────────────────────────────────────────────────────────────

@router.get("/track/{tracking_number}")
async def track_article(
    tracking_number: str,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Track a single India Post article. Requires India Post auth."""
    from app.models.shipping_config import DeliveryPartner

    ip_partner = db.query(DeliveryPartner).filter(
        DeliveryPartner.tenant_id == current_user.tenant_id,
        DeliveryPartner.partner_type == "india_post",
        DeliveryPartner.is_active == True,
    ).first()

    if not ip_partner:
        raise HTTPException(400, "India Post not configured — add in Tenant Admin → Shipping Config")

    # client_id = username, api_key = password (encrypted), client_name = 'sandbox'|'production'
    username  = ip_partner.client_id or ""
    password  = service.decrypt_credential(ip_partner.api_key) if ip_partner.api_key else ""
    cust_id   = (ip_partner.customer_ids[0]["id"] if ip_partner.customer_ids else "") or ""
    use_sandbox = (ip_partner.client_name or "sandbox") != "production"

    if not username or not password:
        raise HTTPException(400, "India Post username/password not configured — edit the delivery partner in Shipping Config")

    client = IndiaPostAPIClient(
        username=username,
        password=password,
        customer_id=cust_id,
        sandbox=use_sandbox,
    )

    result = await client.track_article(tracking_number)
    if result.get("success") is False:
        raise HTTPException(502, f"Tracking error: {result.get('error', 'Unknown')}")

    return result


@router.post("/sync-orders")
async def sync_orders_tracking(
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations)),
):
    """Refresh India Post tracking fields on the latest active manual orders."""
    return await tracking_sync_service.sync_tenant_india_post_orders(
        db,
        current_user.tenant_id,
        actor_id=current_user.id,
        days=days,
        limit=limit,
    )


# ─────────────────────────────────────────────────────────────
# PRE-SAVE CREDENTIAL TEST  (tests raw creds, never stored)
# ─────────────────────────────────────────────────────────────

from pydantic import BaseModel

class CredentialTestRequest(BaseModel):
    username:    str
    password:    str
    environment: str = "sandbox"   # "sandbox" | "production"

@router.post("/test-credentials")
async def test_credentials_preflight(
    payload: CredentialTestRequest,
    current_user: Employee = Depends(require_roles(RoleEnum.admin)),
):
    """
    Test India Post credentials BEFORE saving.
    Accepts raw (plaintext) username + password — never stored.
    Returns success/failure so the user can verify before hitting Save.
    """
    if not payload.username.strip() or not payload.password.strip():
        raise HTTPException(400, "Username and password are required")

    use_sandbox = payload.environment != "production"
    client = IndiaPostAPIClient(
        username=payload.username.strip(),
        password=payload.password.strip(),
        customer_id="",   # not needed for login test
        sandbox=use_sandbox,
    )

    try:
        result = await client.test_connection()
    except Exception as e:
        err = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
        if "ConfigurationError" in err:
            return {
                "success": False,
                "message": "India Post production base URLs are not configured on this server. "
                           "Set INDIA_POST_PROD_URL and INDIA_POST_PROD_MASTERDATA_URL, then test again.",
            }
        if "ConnectTimeout" in err or "ConnectError" in err or "Name or service not known" in err:
            return {
                "success": False,
                "message": "India Post API server is not reachable from this server (IP whitelisting pending). "
                           "Your credentials cannot be verified yet — save them and test once whitelisting is done.",
                "unreachable": True,
            }
        return {"success": False, "message": f"Connection error: {err}"}

    if not result.get("success"):
        msg = result.get("message", "")
        if "ConfigurationError" in msg:
            return {
                "success": False,
                "message": "India Post production base URLs are not configured on this server. "
                           "Set INDIA_POST_PROD_URL and INDIA_POST_PROD_MASTERDATA_URL, then test again.",
            }
        if "ConnectTimeout" in msg or "ConnectError" in msg or not msg:
            return {
                "success": False,
                "message": "India Post API server is not reachable from this server (IP whitelisting pending). "
                           "Your credentials cannot be verified yet — save them and test once whitelisting is done.",
                "unreachable": True,
            }
    return result


# ─────────────────────────────────────────────────────────────
# CONNECTION TEST  (uses already-saved partner credentials)
# ─────────────────────────────────────────────────────────────

@router.post("/test-connection")
async def test_connection(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin)),
):
    """Test India Post API connection using stored credentials."""
    from app.models.shipping_config import DeliveryPartner

    ip_partner = db.query(DeliveryPartner).filter(
        DeliveryPartner.tenant_id == current_user.tenant_id,
        DeliveryPartner.partner_type == "india_post",
        DeliveryPartner.is_active == True,
    ).first()

    if not ip_partner:
        raise HTTPException(400, "India Post not configured")

    username    = ip_partner.client_id or ""
    password    = service.decrypt_credential(ip_partner.api_key) if ip_partner.api_key else ""
    cust_id     = (ip_partner.customer_ids[0]["id"] if ip_partner.customer_ids else "") or ""
    use_sandbox = (ip_partner.client_name or "sandbox") != "production"

    client = IndiaPostAPIClient(
        username=username,
        password=password,
        customer_id=cust_id,
        sandbox=use_sandbox,
    )

    result = await client.test_connection()
    return result
