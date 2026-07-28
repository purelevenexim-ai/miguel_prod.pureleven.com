from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database.session import get_db
from app.models.employee import Employee, RoleEnum
from app.models.shipping_config import (
    DeliveryPartner,
    NotificationChannel,
    ShippingBusinessRules,
    ShopifyStore,
)

from . import schemas, service

router = APIRouter(prefix="/api/config", tags=["Shipping Config"])


# ─────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────

def _require_admin(current_user: Employee) -> Employee:
    """Raises 403 if the caller is not a tenant admin."""
    if current_user.role != RoleEnum.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tenant admins can manage shipping configuration",
        )
    return current_user


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────
#  SHOPIFY STORES
# ─────────────────────────────────────────────────────────────

@router.get("/shopify-stores", response_model=List[schemas.ShopifyStoreOut])
def list_shopify_stores(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_admin(current_user)
    return (
        db.query(ShopifyStore)
        .filter(ShopifyStore.tenant_id == current_user.tenant_id)
        .order_by(ShopifyStore.created_at)
        .all()
    )


@router.post("/shopify-stores", response_model=schemas.ShopifyStoreOut, status_code=201)
def create_shopify_store(
    payload: schemas.ShopifyStoreCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_admin(current_user)

    # Prevent duplicate store URLs within the SAME tenant only (multi-tenant safe)
    if db.query(ShopifyStore).filter(
        ShopifyStore.tenant_id == current_user.tenant_id,
        ShopifyStore.store_url == payload.store_url,
    ).first():
        raise HTTPException(status_code=400, detail="This store URL is already configured for your account")

    store = ShopifyStore(
        tenant_id         = current_user.tenant_id,
        store_name        = payload.store_name,
        store_url         = payload.store_url,
        api_access_token  = service.encrypt_credential(payload.api_access_token),
        api_client_id     = payload.api_client_id,
        api_client_secret = service.encrypt_credential(payload.api_client_secret),
        api_version       = "2024-01",
        is_primary        = payload.is_primary,
    )
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


@router.put("/shopify-stores/{store_id}", response_model=schemas.ShopifyStoreOut)
def update_shopify_store(
    store_id: UUID,
    payload: schemas.ShopifyStoreUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_admin(current_user)
    store = db.query(ShopifyStore).filter(
        ShopifyStore.id == store_id,
        ShopifyStore.tenant_id == current_user.tenant_id,
    ).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    updates = payload.model_dump(exclude_unset=True)
    if "api_access_token" in updates:
        updates["api_access_token"] = service.encrypt_credential(updates["api_access_token"])
        store.is_connected = False  # force re-test after credential change
    if "api_client_secret" in updates:
        updates["api_client_secret"] = service.encrypt_credential(updates["api_client_secret"])

    for field, val in updates.items():
        setattr(store, field, val)

    db.commit()
    db.refresh(store)
    return store


@router.delete("/shopify-stores/{store_id}", status_code=204)
def delete_shopify_store(
    store_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_admin(current_user)
    store = db.query(ShopifyStore).filter(
        ShopifyStore.id == store_id,
        ShopifyStore.tenant_id == current_user.tenant_id,
    ).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    db.delete(store)
    db.commit()


@router.post("/shopify-stores/{store_id}/test-connection", response_model=schemas.ConnectionTestOut)
async def test_shopify_store(
    store_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_admin(current_user)
    store = db.query(ShopifyStore).filter(
        ShopifyStore.id == store_id,
        ShopifyStore.tenant_id == current_user.tenant_id,
    ).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    result = await service.test_shopify_connection(store)
    store.is_connected         = result["success"]
    store.last_connection_test = _now()
    db.commit()

    return schemas.ConnectionTestOut(
        status  = "connected" if result["success"] else "failed",
        message = result["message"],
    )


@router.post("/shopify-stores/{store_id}/register-webhooks")
async def register_shopify_webhooks(
    store_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """
    Register all CRM-required webhooks on Shopify.
    Idempotent — safe to call multiple times.
    """
    import os
    from app.core.shipping.shopify_api_client import ShopifyAPIClient
    _require_admin(current_user)
    store = db.query(ShopifyStore).filter(
        ShopifyStore.id == store_id,
        ShopifyStore.tenant_id == current_user.tenant_id,
    ).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    token = service.decrypt_credential(store.api_access_token)
    client = ShopifyAPIClient(
        store_url=store.store_url,
        access_token=token,
        api_version=store.api_version or "2024-01",
    )

    # Use configured CRM base URL or fail with clear message
    crm_base_url = os.environ.get("CRM_WEBHOOK_BASE_URL", "").rstrip("/")
    if not crm_base_url:
        raise HTTPException(
            status_code=400,
            detail="CRM_WEBHOOK_BASE_URL environment variable not set. "
                   "Set it to your public CRM server URL, e.g. https://crm.yourcompany.com"
        )

    result = await client.register_crm_webhooks(crm_base_url)
    return result


# ─────────────────────────────────────────────────────────────
#  DELIVERY PARTNERS
# ─────────────────────────────────────────────────────────────

@router.get("/delivery-partners/available")
def list_available_partner_types():
    """Returns the list of supported delivery partner types — no auth required."""
    return [
        {"id": k, "name": v["name"], "shipment_types": v["shipment_types"]}
        for k, v in service.PARTNER_CONFIGS.items()
    ]


@router.get("/delivery-partners", response_model=List[schemas.DeliveryPartnerOut])
def list_delivery_partners(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_admin(current_user)
    return (
        db.query(DeliveryPartner)
        .filter(DeliveryPartner.tenant_id == current_user.tenant_id)
        .order_by(DeliveryPartner.created_at)
        .all()
    )


@router.post("/delivery-partners", response_model=schemas.DeliveryPartnerOut, status_code=201)
def create_delivery_partner(
    payload: schemas.DeliveryPartnerCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_admin(current_user)

    cfg = service.get_partner_config(payload.partner_type)   # validates type

    partner = DeliveryPartner(
        tenant_id                = current_user.tenant_id,
        partner_type             = payload.partner_type,
        display_name             = payload.display_name,
        api_key                  = service.encrypt_credential(payload.api_key),
        api_secret               = service.encrypt_credential(payload.api_secret),
        client_name              = payload.client_name,
        client_id                = payload.client_id,
        api_base_url             = cfg["base_url"],
        pickup_location_code     = payload.pickup_location_code,
        warehouse_name           = payload.warehouse_name,
        customer_ids             = payload.customer_ids or [],
        supported_shipment_types = cfg["shipment_types"],
        is_primary               = payload.is_primary,
    )
    db.add(partner)
    db.commit()
    db.refresh(partner)
    return partner


@router.put("/delivery-partners/{partner_id}", response_model=schemas.DeliveryPartnerOut)
def update_delivery_partner(
    partner_id: UUID,
    payload: schemas.DeliveryPartnerUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_admin(current_user)
    partner = db.query(DeliveryPartner).filter(
        DeliveryPartner.id == partner_id,
        DeliveryPartner.tenant_id == current_user.tenant_id,
    ).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    updates = payload.model_dump(exclude_unset=True)

    # Encrypt credential fields — handle None safely
    if "api_key" in updates:
        updates["api_key"] = service.encrypt_credential(updates["api_key"])
        partner.is_connected = False
    if "api_secret" in updates:
        updates["api_secret"] = service.encrypt_credential(updates["api_secret"])

    for field, val in updates.items():
        setattr(partner, field, val)

    db.commit()
    db.refresh(partner)
    return partner


@router.delete("/delivery-partners/{partner_id}", status_code=204)
def delete_delivery_partner(
    partner_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_admin(current_user)
    partner = db.query(DeliveryPartner).filter(
        DeliveryPartner.id == partner_id,
        DeliveryPartner.tenant_id == current_user.tenant_id,
    ).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    db.delete(partner)
    db.commit()


@router.post("/delivery-partners/{partner_id}/test-connection", response_model=schemas.ConnectionTestOut)
async def test_delivery_partner(
    partner_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_admin(current_user)
    partner = db.query(DeliveryPartner).filter(
        DeliveryPartner.id == partner_id,
        DeliveryPartner.tenant_id == current_user.tenant_id,
    ).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    result = await service.test_delivery_partner_connection(partner)
    partner.is_connected         = result["success"]
    partner.last_connection_test = _now()
    db.commit()

    return schemas.ConnectionTestOut(
        status  = "connected" if result["success"] else "failed",
        message = result["message"],
    )


# ─────────────────────────────────────────────────────────────
#  NOTIFICATION CHANNELS
# ─────────────────────────────────────────────────────────────

@router.get("/notification-channels", response_model=List[schemas.NotificationChannelOut])
def list_notification_channels(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_admin(current_user)
    return (
        db.query(NotificationChannel)
        .filter(NotificationChannel.tenant_id == current_user.tenant_id)
        .order_by(NotificationChannel.created_at)
        .all()
    )


@router.post("/notification-channels", response_model=schemas.NotificationChannelOut, status_code=201)
def create_notification_channel(
    payload: schemas.NotificationChannelCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_admin(current_user)

    channel = NotificationChannel(
        tenant_id           = current_user.tenant_id,
        channel_type        = payload.channel_type,
        provider            = payload.provider,
        api_key             = service.encrypt_credential(payload.api_key),
        api_secret          = service.encrypt_credential(payload.api_secret),
        access_token        = service.encrypt_credential(payload.access_token),
        phone_number        = payload.phone_number,
        business_account_id = payload.business_account_id,
        phone_number_id     = payload.phone_number_id,
        sender_email        = payload.sender_email,
        is_primary          = payload.is_primary,
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return channel


@router.put("/notification-channels/{channel_id}", response_model=schemas.NotificationChannelOut)
def update_notification_channel(
    channel_id: UUID,
    payload: schemas.NotificationChannelUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_admin(current_user)
    channel = db.query(NotificationChannel).filter(
        NotificationChannel.id == channel_id,
        NotificationChannel.tenant_id == current_user.tenant_id,
    ).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    updates = payload.model_dump(exclude_unset=True)
    # Encrypt credential fields safely — all handle None
    for cred_field in ("api_key", "api_secret", "access_token"):
        if cred_field in updates:
            updates[cred_field] = service.encrypt_credential(updates[cred_field])
            channel.is_connected = False

    for field, val in updates.items():
        setattr(channel, field, val)

    db.commit()
    db.refresh(channel)
    return channel


@router.delete("/notification-channels/{channel_id}", status_code=204)
def delete_notification_channel(
    channel_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_admin(current_user)
    channel = db.query(NotificationChannel).filter(
        NotificationChannel.id == channel_id,
        NotificationChannel.tenant_id == current_user.tenant_id,
    ).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    db.delete(channel)
    db.commit()


@router.post("/notification-channels/{channel_id}/test-connection", response_model=schemas.ConnectionTestOut)
async def test_notification_channel(
    channel_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_admin(current_user)
    channel = db.query(NotificationChannel).filter(
        NotificationChannel.id == channel_id,
        NotificationChannel.tenant_id == current_user.tenant_id,
    ).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    result = await service.test_notification_connection(channel)
    channel.is_connected         = result["success"]
    channel.last_connection_test = _now()
    db.commit()

    return schemas.ConnectionTestOut(
        status  = "connected" if result["success"] else "failed",
        message = result["message"],
    )


# ─────────────────────────────────────────────────────────────
#  BUSINESS RULES  (one row per tenant — auto-created on first GET)
# ─────────────────────────────────────────────────────────────

def _get_or_create_rules(tenant_id, db: Session) -> ShippingBusinessRules:
    rules = db.query(ShippingBusinessRules).filter(
        ShippingBusinessRules.tenant_id == tenant_id
    ).first()
    if not rules:
        rules = ShippingBusinessRules(tenant_id=tenant_id)
        db.add(rules)
        db.commit()
        db.refresh(rules)
    return rules


@router.get("/business-rules", response_model=schemas.BusinessRulesOut)
def get_business_rules(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_admin(current_user)
    return _get_or_create_rules(current_user.tenant_id, db)


@router.put("/business-rules", response_model=schemas.BusinessRulesOut)
def update_business_rules(
    payload: schemas.BusinessRulesUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    _require_admin(current_user)
    rules = _get_or_create_rules(current_user.tenant_id, db)

    for field, val in payload.model_dump(exclude_unset=True).items():
        setattr(rules, field, val)

    db.commit()
    db.refresh(rules)
    return rules
