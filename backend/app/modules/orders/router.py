from uuid import UUID
from typing import Optional
from datetime import date
from pydantic import BaseModel as _BM
from fastapi import APIRouter, Depends, Query, HTTPException, Header
from sqlalchemy.orm import Session
import os as _os

from app.database.session import get_db
from app.core.auth.tenant import get_current_tenant_user, require_roles
from app.models.employee import Employee, RoleEnum
from app.models.order import OrderStatus, PaymentStatus
from app.core.address_parser import parse_address_dict
from app.modules.orders.schemas import (
    OrderCreate, OrderUpdate, OrderResponse, OrderDetail,
    OrderStatusUpdate, OrderPaymentCreate, OrderPaymentResponse,
    OrderFilters, OrderStats,
)
from app.modules.orders import service
from app.modules.orders import courier_service
from app.modules.orders import tracking_sync_service
from app.modules.orders.shopify_sync_service import ShopifyOrderSyncService
from app.models.shopify_order import ShopifyOrder, ShippingInfo, TrackingEvent
from app.models.shipping_config import ShopifyStore

router = APIRouter(prefix="/api/orders", tags=["Orders"])

# ─────────────────────────────────────────────────────────────
# Inline request schemas
# ─────────────────────────────────────────────────────────────

class AddressParseRequest(_BM):
    raw_text: str

class PhoneLookupRequest(_BM):
    phone: str

class CourierCreate(_BM):
    name: str
    code: str
    is_active: bool = True
    is_default: bool = False
    notes: Optional[str] = None

class IPCustomerIdCreate(_BM):
    customer_id: str
    label: Optional[str] = None
    is_default: bool = False
    is_active: bool = True


# ─────────────────────────────────────────────────────────────
# CRUD
# ─────────────────────────────────────────────────────────────

@router.post("/", response_model=OrderDetail, status_code=201)
def create_order(
    data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(
        require_roles(RoleEnum.admin, RoleEnum.sales, RoleEnum.operations)
    ),
):
    """Create a new order with line items. Admin, Sales, Operations."""
    return service.create_order(db, data, current_user)


@router.get("/", response_model=dict)
def list_orders(
    status: Optional[OrderStatus]         = Query(None),
    payment_status: Optional[PaymentStatus] = Query(None),
    customer_id: Optional[UUID]           = Query(None),
    assigned_to_id: Optional[UUID]        = Query(None),
    search: Optional[str]                 = Query(None),
    created_after: Optional[date]         = Query(None),
    created_before: Optional[date]        = Query(None),
    is_active: Optional[bool]             = Query(True),
    page: int                             = Query(1, ge=1),
    page_size: int                        = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """List orders with filters and pagination. All roles."""
    filters = OrderFilters(
        status=status,
        payment_status=payment_status,
        customer_id=customer_id,
        assigned_to_id=assigned_to_id,
        search=search,
        created_after=created_after,
        created_before=created_before,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )
    return service.list_orders(db, filters, current_user)


@router.get("/stats", response_model=OrderStats)
def get_order_stats(
    status: Optional[OrderStatus]         = Query(None),
    payment_status: Optional[PaymentStatus] = Query(None),
    customer_id: Optional[UUID]           = Query(None),
    assigned_to_id: Optional[UUID]        = Query(None),
    search: Optional[str]                 = Query(None),
    created_after: Optional[date]         = Query(None),
    created_before: Optional[date]        = Query(None),
    is_active: Optional[bool]             = Query(True),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Revenue and order stats using optional list-style filters. All roles."""
    filters = OrderFilters(
        status=status,
        payment_status=payment_status,
        customer_id=customer_id,
        assigned_to_id=assigned_to_id,
        search=search,
        created_after=created_after,
        created_before=created_before,
        is_active=is_active,
        page=1,
        page_size=20,
    )
    return service.get_order_stats(
        db,
        current_user,
        filters=filters,
        cache_tenant=str(current_user.tenant_id),
    )


# ─────────────────────────────────────────────────────────────
# Address Parse & Phone Lookup  (static — must precede /{order_id})
# ─────────────────────────────────────────────────────────────

@router.post("/parse-address", response_model=dict)
def parse_address_endpoint(
    data: AddressParseRequest,
    current_user: Employee = Depends(get_current_tenant_user),
):
    """
    Parse raw WhatsApp / freeform address text into structured fields.
    Returns confidence level. Low confidence → employee must fill manually.
    """
    return parse_address_dict(data.raw_text)


@router.post("/phone-lookup", response_model=dict)
def phone_lookup(
    data: PhoneLookupRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Check if a phone number belongs to an existing customer or lead."""
    return service.lookup_phone(db, data.phone, current_user)


# ─────────────────────────────────────────────────────────────
# Couriers  (static)
# ─────────────────────────────────────────────────────────────

@router.get("/couriers", response_model=list)
def list_couriers(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """List all active delivery partners for the tenant with their customer IDs."""
    from app.models.shipping_config import DeliveryPartner

    delivery_partners = db.query(DeliveryPartner).filter(
        DeliveryPartner.tenant_id == current_user.tenant_id,
        DeliveryPartner.is_active == True,
    ).order_by(DeliveryPartner.is_primary.desc(), DeliveryPartner.display_name).all()

    result = []
    for dp in delivery_partners:
        result.append({
            "id":           str(dp.id),
            "name":         dp.display_name,
            "code":         dp.partner_type.upper(),
            "partner_type": dp.partner_type,
            "is_active":    dp.is_active,
            "is_default":   dp.is_primary,
            "customer_ids": dp.customer_ids if dp.customer_ids else [],
        })

    return result


@router.post("/couriers", response_model=dict, status_code=201)
def create_courier(
    data: CourierCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin)),
):
    """Create a courier partner. Admin only."""
    c = courier_service.create_courier(db, data.model_dump(), current_user)
    return {"id": str(c.id), "name": c.name, "code": c.code, "is_default": c.is_default}


@router.patch("/couriers/{courier_id}", response_model=dict)
def update_courier(
    courier_id: UUID,
    data: CourierCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin)),
):
    """Update a courier. Admin only."""
    c = courier_service.update_courier(
        db, str(courier_id), data.model_dump(exclude_unset=True), current_user
    )
    return {"id": str(c.id), "name": c.name, "code": c.code, "is_default": c.is_default}


@router.delete("/couriers/{courier_id}", response_model=dict)
def delete_courier(
    courier_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin)),
):
    """Delete a courier. Admin only."""
    return courier_service.delete_courier(db, str(courier_id), current_user)


# ─────────────────────────────────────────────────────────────
# India Post Customer IDs  (static)
# ─────────────────────────────────────────────────────────────

@router.get("/india-post-ids", response_model=list)
def list_india_post_ids(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """List India Post customer IDs for the tenant."""
    recs = courier_service.list_ip_customer_ids(db, current_user)
    return [
        {
            "id": str(r.id), "customer_id": r.customer_id,
            "label": r.label, "is_default": r.is_default, "is_active": r.is_active,
        }
        for r in recs
    ]


@router.post("/india-post-ids", response_model=dict, status_code=201)
def create_india_post_id(
    data: IPCustomerIdCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin)),
):
    """Add an India Post customer ID. Admin only."""
    r = courier_service.create_ip_customer_id(db, data.model_dump(), current_user)
    return {"id": str(r.id), "customer_id": r.customer_id, "label": r.label, "is_default": r.is_default}


@router.patch("/india-post-ids/{rec_id}", response_model=dict)
def update_india_post_id(
    rec_id: UUID,
    data: IPCustomerIdCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin)),
):
    """Update an India Post customer ID. Admin only."""
    r = courier_service.update_ip_customer_id(
        db, str(rec_id), data.model_dump(exclude_unset=True), current_user
    )
    return {"id": str(r.id), "customer_id": r.customer_id, "label": r.label, "is_default": r.is_default}


@router.delete("/india-post-ids/{rec_id}", response_model=dict)
def delete_india_post_id(
    rec_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin)),
):
    """Deactivate an India Post customer ID. Admin only."""
    return courier_service.delete_ip_customer_id(db, str(rec_id), current_user)


# ─────────────────────────────────────────────────────────────
# SHOPIFY ORDERS (auto-synced from Shopify)
# ─────────────────────────────────────────────────────────────

@router.get("/shopify/orders", response_model=dict)
def list_shopify_orders(
    status: Optional[str] = Query(None),
    shipping_partner: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """List Shopify orders synced from store with optional filters. All roles."""
    query = db.query(ShopifyOrder).filter(ShopifyOrder.tenant_id == current_user.tenant_id)
    
    if status:
        query = query.filter(ShopifyOrder.shopify_status == status)
    if shipping_partner:
        query = query.filter(ShopifyOrder.shipping_partner == shipping_partner)
    
    total = query.count()
    orders = query.order_by(ShopifyOrder.created_at_shopify.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    
    def _extract_risk(raw: dict | None) -> str:
        """Extract risk level from Shopify tags (fastrr injects low/medium/high)."""
        if not raw:
            return ""
        tags = raw.get("tags", "") or ""
        tags_lower = tags.lower()
        if "high" in tags_lower:
            return "high"
        if "medium" in tags_lower:
            return "medium"
        if "low" in tags_lower:
            return "low"
        return ""

    def _extract_gateway(raw: dict | None) -> str:
        """Return first payment gateway name from raw Shopify data."""
        if not raw:
            return ""
        gateways = raw.get("payment_gateway_names") or []
        return gateways[0] if gateways else (raw.get("payment_gateway") or "")

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "orders": [
            {
                "id": str(o.id),
                "shopify_order_number": o.shopify_order_name,
                "customer_name": o.customer_name,
                "shipping_city": o.shipping_city,
                "shipping_zip": o.shipping_zip,
                "shipping_state": o.shipping_state,
                "total_price": float(o.total_price),
                "financial_status": o.shopify_financial_status or "pending",
                "shopify_status": o.shopify_status,
                "fulfillment_status": o.shopify_fulfillment_status,
                "payment_gateway": _extract_gateway(o.raw_shopify_data),
                "risk_level": _extract_risk(o.raw_shopify_data),
                "shipping_partner": o.shipping_partner,
                "tracking_number": o.tracking_number,
                "tracking_url": o.tracking_url,
                "customer_phone": o.customer_phone,
                "created_at": o.created_at_shopify.isoformat() if o.created_at_shopify else None,
            }
            for o in orders
        ],
    }


@router.get("/shopify/orders/{order_id}", response_model=dict)
def get_shopify_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Get full Shopify order details with shipping and tracking."""
    order = db.query(ShopifyOrder).filter(
        ShopifyOrder.id == order_id,
        ShopifyOrder.tenant_id == current_user.tenant_id,
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    shipping_info = order.shipping_info
    tracking_events = db.query(TrackingEvent).filter(
        TrackingEvent.shopify_order_id == order_id
    ).order_by(TrackingEvent.event_time.desc()).all()
    
    return {
        "id": str(order.id),
        "shopify_order_number": order.shopify_order_name,
        "shopify_order_id": order.shopify_order_id,
        "customer_name": order.customer_name,
        "customer_email": order.customer_email,
        "customer_phone": order.customer_phone,
        "shipping_address": f"{order.shipping_address_line1}, {order.shipping_city}, {order.shipping_state} {order.shipping_zip}",
        "shipping_city": order.shipping_city,
        "shipping_zip": order.shipping_zip,
        "shipping_state": order.shipping_state,
        "total_price": float(order.total_price),
        "subtotal": float(order.subtotal),
        "shipping_cost": float(order.shipping_cost),
        "taxes": float(order.taxes),
        "discounts": float(order.discounts),
        "currency": order.currency,
        "items_count": order.line_items_count,
        "items": order.line_items_json,
        "shopify_status": order.shopify_status,
        "fulfillment_status": order.shopify_fulfillment_status,
        "financial_status": order.shopify_financial_status or "pending",
        "payment_gateway": (order.raw_shopify_data or {}).get("payment_gateway_names", [""])[0] if (order.raw_shopify_data or {}).get("payment_gateway_names") else "",
        "risk_level": next((t for t in ["high","medium","low"] if t in ((order.raw_shopify_data or {}).get("tags","") or "").lower()), ""),
        "tags": (order.raw_shopify_data or {}).get("tags", ""),
        "notes": order.notes,
        "shipping": {
            "partner": order.shipping_partner,
            "courier": shipping_info.courier_name if shipping_info else None,
            "tracking_number": order.tracking_number,
            "tracking_url": order.tracking_url,
            "status": shipping_info.tracking_status if shipping_info else None,
            "last_update": shipping_info.last_tracking_update.isoformat() if shipping_info and shipping_info.last_tracking_update else None,
        },
        "tracking_events": [
            {
                "status": e.event_status,
                "location": e.location,
                "description": e.description,
                "time": e.event_time.isoformat() if e.event_time else None,
            }
            for e in tracking_events
        ],
        "created_at": order.created_at_shopify.isoformat() if order.created_at_shopify else None,
        "updated_at": order.updated_at_shopify.isoformat() if order.updated_at_shopify else None,
    }


@router.post("/shopify/orders/{order_id}/assign-delhivery")
async def assign_delhivery_shipping(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations)),
):
    """Assign Delhivery as shipping partner for a Shopify order."""
    from app.models.shipping_config import DeliveryPartner
    
    order = db.query(ShopifyOrder).filter(
        ShopifyOrder.id == order_id,
        ShopifyOrder.tenant_id == current_user.tenant_id,
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Get Delhivery credentials from delivery partner config
    delhivery_partner = db.query(DeliveryPartner).filter(
        DeliveryPartner.tenant_id == current_user.tenant_id,
        DeliveryPartner.partner_type == "delhivery",
        DeliveryPartner.is_active == True,
    ).first()
    
    if not delhivery_partner:
        raise HTTPException(status_code=400, detail="Delhivery not configured for tenant")
    
    sync_service = ShopifyOrderSyncService(db)
    result = await sync_service.sync_tracking_with_delhivery(
        order,
        delhivery_partner.api_key,
        delhivery_partner.client_name or "",
    )
    
    if result["success"]:
        return {
            "success": True,
            "tracking_number": result["tracking_number"],
            "message": "Delhivery waybill created successfully",
        }
    else:
        raise HTTPException(status_code=400, detail=result.get("error"))


@router.post("/shopify/orders/{order_id}/assign-india-post")
async def assign_india_post_shipping(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations)),
):
    """Assign India Post as shipping partner for a Shopify order."""
    from app.models.shipping_config import DeliveryPartner
    
    order = db.query(ShopifyOrder).filter(
        ShopifyOrder.id == order_id,
        ShopifyOrder.tenant_id == current_user.tenant_id,
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Get India Post credentials
    ip_partner = db.query(DeliveryPartner).filter(
        DeliveryPartner.tenant_id == current_user.tenant_id,
        DeliveryPartner.partner_type == "india_post",
        DeliveryPartner.is_active == True,
    ).first()
    
    if not ip_partner:
        raise HTTPException(status_code=400, detail="India Post not configured for tenant")
    
    sync_service = ShopifyOrderSyncService(db)
    result = await sync_service.sync_tracking_with_india_post(
        order,
        ip_partner.api_key,
        ip_partner.client_id or "",
        ip_partner.client_name or "",
    )
    
    if result["success"]:
        return {
            "success": True,
            "tracking_number": result["tracking_number"],
            "message": "India Post Speed Post booked successfully",
        }
    else:
        raise HTTPException(status_code=400, detail=result.get("error"))


@router.post("/shopify/orders/{order_id}/refresh-tracking")
async def refresh_tracking_status(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Fetch latest tracking status from courier."""
    from app.models.shipping_config import DeliveryPartner
    
    order = db.query(ShopifyOrder).filter(
        ShopifyOrder.id == order_id,
        ShopifyOrder.tenant_id == current_user.tenant_id,
    ).first()
    
    if not order or not order.shipping_partner:
        raise HTTPException(status_code=404, detail="Order or shipping info not found")
    
    # Get courier credentials
    partner = db.query(DeliveryPartner).filter(
        DeliveryPartner.tenant_id == current_user.tenant_id,
        DeliveryPartner.partner_type == order.shipping_partner.value,
    ).first()
    
    if not partner:
        raise HTTPException(status_code=400, detail="Courier not configured")
    
    sync_service = ShopifyOrderSyncService(db)
    result = await sync_service.fetch_tracking_updates(
        order,
        delhivery_key=partner.api_key if order.shipping_partner.value == "delhivery" else None,
        ip_api_key=partner.api_key if order.shipping_partner.value == "india_post" else None,
    )
    
    if result["success"]:
        return {
            "success": True,
            "status": result["status"],
            "events_count": len(result.get("events", [])),
        }
    else:
        raise HTTPException(status_code=400, detail=result.get("error"))


# ─────────────────────────────────────────────────────────────
# Parameterized routes — MUST come after all static routes
# ─────────────────────────────────────────────────────────────

@router.post("/shopify/orders/sync-all")
async def sync_all_shopify_orders(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations)),
):
    """
    Full re-sync of all Shopify orders: re-fetches every order from Shopify API
    and updates fulfillment_status, financial_status, courier, and tracking number.
    """
    from app.models.shipping_config import ShopifyStore
    from app.core.shipping.shopify_api_client import ShopifyAPIClient
    from app.modules.shipping_config.service import decrypt_credential
    from app.modules.orders.shopify_sync_service import ShopifyOrderSyncService

    store = db.query(ShopifyStore).filter(
        ShopifyStore.tenant_id == current_user.tenant_id,
        ShopifyStore.is_active == True,
    ).order_by(ShopifyStore.is_primary.desc()).first()

    if not store:
        raise HTTPException(status_code=400, detail="No active Shopify store configured")

    token = decrypt_credential(store.api_access_token)
    client = ShopifyAPIClient(
        store_url=store.store_url,
        access_token=token,
        api_version=store.api_version or "2024-01",
    )

    # Fetch all orders with all fields (fulfillments, tracking, etc.)
    result = await client.get_orders(limit=250, status="any")
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=f"Shopify API error: {result.get('error')}")

    shopify_orders = result.get("orders", [])
    sync_svc = ShopifyOrderSyncService(db)

    synced = 0
    updated_tracking = 0
    errors = []

    for order_data in shopify_orders:
        try:
            res = sync_svc.process_order_webhook(store, order_data)
            if res["success"]:
                synced += 1
                # Check if tracking was populated
                fulfillments = order_data.get("fulfillments") or []
                if any(f.get("tracking_number") for f in fulfillments):
                    updated_tracking += 1
        except Exception as e:
            errors.append(str(e))

    db.commit()
    return {
        "success": True,
        "shopify_orders_fetched": len(shopify_orders),
        "orders_synced": synced,
        "orders_with_tracking": updated_tracking,
        "errors": errors[:5],
        "message": f"✅ Synced {synced} orders from Shopify ({updated_tracking} have tracking)",
    }


@router.post("/shopify/orders/sync-payment-status")
async def sync_shopify_payment_status(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations)),
):
    """
    Re-fetch financial_status for all Shopify orders from Shopify API
    and update payment status in local DB.
    Marks COD pending orders as paid if Shopify says 'paid'.
    """
    from app.models.shipping_config import ShopifyStore
    from app.core.shipping.shopify_api_client import ShopifyAPIClient
    from app.modules.shipping_config.service import decrypt_credential

    store = db.query(ShopifyStore).filter(
        ShopifyStore.tenant_id == current_user.tenant_id,
        ShopifyStore.is_active == True,
    ).order_by(ShopifyStore.is_primary.desc()).first()

    if not store:
        raise HTTPException(status_code=400, detail="No active Shopify store configured")

    token = decrypt_credential(store.api_access_token)
    client = ShopifyAPIClient(store_url=store.store_url, access_token=token,
                              api_version=store.api_version or "2024-01")

    # Fetch all orders (paginate in batches of 250)
    result = await client.get_orders(limit=250, status="any")

    # Build a map: shopify_order_name → financial_status
    # (CSV-imported orders use a hash ID, so match by order name)
    if not result.get("success"):
        raise HTTPException(status_code=502,
                            detail=f"Shopify API error: {result.get('error')}")

    shopify_map = {}
    for o in result.get("orders", []):
        name = o.get("name", "")          # e.g. "#1001"
        fin  = o.get("financial_status", "")
        gw   = (o.get("gateway") or
                (o.get("payment_gateway_names") or [""])[0] or "").lower()
        shopify_map[name] = {"financial_status": fin, "gateway": gw}

    # Fetch all local Shopify orders for this tenant
    local_orders = db.query(ShopifyOrder).filter(
        ShopifyOrder.shopify_store_id == store.id,
    ).all()

    updated = 0
    for order in local_orders:
        info = shopify_map.get(order.shopify_order_name)
        if not info:
            continue
        fin = info["financial_status"]
        gw  = info["gateway"]

        if order.shopify_financial_status != fin:
            order.shopify_financial_status = fin
            updated += 1

        # Also infer payment method from gateway if missing
        if not order.notes or "gateway" not in order.notes:
            if "cod" in gw or "cash" in gw:
                order.notes = (order.notes or "") + f" [gateway: {gw}]"

    db.commit()
    return {
        "success": True,
        "shopify_orders_checked": len(shopify_map),
        "local_orders_updated":   updated,
        "message": f"✅ {updated} orders updated from Shopify payment status",
    }


@router.post("/shopify/sync-abandoned-carts")
async def force_sync_abandoned_carts(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations)),
):
    """
    Force-sync abandoned carts from Shopify to CRM Leads.
    Fetches all abandoned checkouts from the active Shopify store and creates leads.
    """
    from app.models.shipping_config import ShopifyStore
    from app.core.shipping.shopify_api_client import ShopifyAPIClient
    from app.modules.shipping_config.service import decrypt_credential
    from app.core.shopify_sync_worker import _process_abandoned_carts

    store = db.query(ShopifyStore).filter(
        ShopifyStore.tenant_id == current_user.tenant_id,
        ShopifyStore.is_active == True,
    ).order_by(ShopifyStore.is_primary.desc()).first()

    if not store:
        raise HTTPException(status_code=400, detail="No active Shopify store configured")

    token = decrypt_credential(store.api_access_token)
    client = ShopifyAPIClient(
        store_url=store.store_url,
        access_token=token,
        api_version=store.api_version or "2024-01",
    )

    # Fetch all abandoned checkouts (no date filter for force sync)
    result = await client.get_abandoned_checkouts(limit=250)
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=f"Shopify API error: {result.get('error')}")

    checkouts = result.get("checkouts", [])
    lead_count = _process_abandoned_carts(db, store, checkouts)

    return {
        "success": True,
        "checkouts_fetched": len(checkouts),
        "leads_created": lead_count,
        "message": f"✅ Created {lead_count} new leads from {len(checkouts)} abandoned carts",
    }


@router.patch("/shopify/orders/{order_id}/payment-status")
def update_shopify_payment_status(
    order_id: UUID,
    data: dict,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations)),
):
    """
    Manually override payment status on a Shopify order.
    Body: { "financial_status": "paid" | "pending" | "refunded" }
    """
    from fastapi import Body
    order = db.query(ShopifyOrder).filter(
        ShopifyOrder.id == order_id,
        ShopifyOrder.tenant_id == current_user.tenant_id,
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    new_status = data.get("financial_status", "").lower()
    allowed = ("paid", "pending", "refunded", "partially_paid", "voided")
    if new_status not in allowed:
        raise HTTPException(status_code=400,
                            detail=f"Invalid status. Allowed: {allowed}")

    order.shopify_financial_status = new_status
    db.commit()
    return {"success": True, "financial_status": new_status,
            "order": order.shopify_order_name}


@router.post("/india-post/sync", response_model=dict)
async def sync_india_post_orders(
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations)),
):
    """Refresh India Post tracking for the latest active manual orders. Admin, Operations."""
    return await tracking_sync_service.sync_tenant_india_post_orders(
        db,
        current_user.tenant_id,
        actor_id=current_user.id,
        days=days,
        limit=limit,
    )


@router.post("/{order_id}/sync-tracking", response_model=dict)
async def sync_order_tracking(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.sales, RoleEnum.operations)),
):
    """Refresh live tracking for a single order when supported by its courier."""
    try:
        return await tracking_sync_service.refresh_order_tracking_detail(db, str(order_id), current_user)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{order_id}/tracking-detail", response_model=dict)
async def get_order_tracking_detail(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Return stored tracking detail and refresh India Post when possible."""
    try:
        return await tracking_sync_service.refresh_order_tracking_detail(db, str(order_id), current_user)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{order_id}", response_model=OrderDetail)
def get_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Full order detail with items, payments, status history. All roles."""
    return service.get_order(db, str(order_id), current_user)


@router.patch("/{order_id}", response_model=OrderResponse)
def update_order(
    order_id: UUID,
    data: OrderUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(
        require_roles(RoleEnum.admin, RoleEnum.sales, RoleEnum.operations)
    ),
):
    """Update order fields (not status). Admin, Sales, Operations."""
    return service.update_order(db, str(order_id), data, current_user)


class UpdateTrackingRequest(_BM):
    """Update courier and tracking for an order."""
    shipping_partner_id: Optional[UUID] = None
    courier_name: Optional[str] = None
    courier_code: Optional[str] = None
    tracking_number: Optional[str] = None


@router.patch("/{order_id}/tracking", response_model=OrderResponse)
def update_order_tracking(
    order_id: UUID,
    data: UpdateTrackingRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(
        require_roles(RoleEnum.admin, RoleEnum.sales, RoleEnum.operations)
    ),
):
    """Update order courier and tracking number. Admin, Sales, Operations."""
    update_data = OrderUpdate(
        shipping_partner_id=data.shipping_partner_id,
        courier_name=data.courier_name,
        courier_code=data.courier_code,
        tracking_number=data.tracking_number,
    )
    return service.update_order(db, str(order_id), update_data, current_user)


@router.delete("/{order_id}", response_model=dict)
def delete_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.sales, RoleEnum.operations)),
):
    """Soft-delete draft or cancelled orders. Admin, Sales, Operations."""
    return service.delete_order(db, str(order_id), current_user)


@router.post("/{order_id}/reactivate", response_model=dict)
def reactivate_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.sales, RoleEnum.operations)),
):
    """Restore a soft-deleted order. Admin, Sales, Operations."""
    return service.reactivate_order(db, str(order_id), current_user)


@router.post("/{order_id}/status", response_model=OrderResponse)
def update_status(
    order_id: UUID,
    data: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(
        require_roles(RoleEnum.admin, RoleEnum.sales, RoleEnum.operations)
    ),
):
    """
    Advance order through status pipeline.
    draft→confirmed→processing→packed→shipped→out_for_delivery→delivered
    Admin, Sales, Operations.
    """
    return service.update_order_status(db, str(order_id), data, current_user)


@router.post("/{order_id}/payments", response_model=OrderPaymentResponse, status_code=201)
def record_payment(
    order_id: UUID,
    data: OrderPaymentCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(
        require_roles(RoleEnum.admin, RoleEnum.sales, RoleEnum.operations)
    ),
):
    """
    Record a payment against an order. Supports partial payments.
    Automatically updates payment_status (pending→partial→paid).
    Admin, Sales, Operations.
    """
    return service.record_payment(db, str(order_id), data, current_user)


# ── Label & Invoice PDF Downloads (for WhatsApp attachments) ──────

from fastapi.responses import StreamingResponse
from io import BytesIO

@router.get("/{order_id}/label")
def get_order_label(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Download shipping label PDF for an order. All roles."""
    from app.modules.customers import service as cust_service
    order = service.get_order(db, str(order_id), current_user)
    if not order.customer_id:
        raise HTTPException(status_code=400, detail="Order has no customer assigned")
    
    pdf_bytes = cust_service.generate_customer_label(
        db, order.customer_id, order_id, current_user
    )
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=label-{order.order_number}.pdf",
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@router.get("/{order_id}/invoice")
def get_order_invoice(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Download invoice PDF for an order. All roles."""
    from app.modules.customers import service as cust_service
    order = service.get_order(db, str(order_id), current_user)
    if not order.customer_id:
        raise HTTPException(status_code=400, detail="Order has no customer assigned")
    
    return cust_service.generate_customer_invoice(
        db, order.customer_id, order_id, current_user
    )


# ─────────────────────────────────────────────────────────────
# AI Engine — Internal tracking lookup (no JWT, service key auth)
# Called by WhatsApp AI to answer shipping queries from customers.
# Auth: X-AI-Service-Key header.
# ─────────────────────────────────────────────────────────────

_AI_SERVICE_KEY = _os.environ.get("AI_SERVICE_KEY", "pureleven-ai-internal-2026")


def _require_ai_key(x_ai_service_key: Optional[str] = Header(None)):
    if x_ai_service_key != _AI_SERVICE_KEY:
        raise HTTPException(status_code=403, detail="Invalid AI service key")


@router.get("/ai/tracking-lookup", tags=["AI Internal"])
def ai_tracking_lookup(
    phone: Optional[str] = Query(None, description="Customer phone (primary)"),
    name:  Optional[str] = Query(None, description="Customer name (fallback)"),
    tenant_slug: str = Query("pureleven"),
    db: Session = Depends(get_db),
    _: None = Depends(_require_ai_key),
):
    """
    Internal endpoint for the WhatsApp AI engine.
    Returns recent order + tracking info for a customer identified by phone or name.
    Returns up to 5 most recent orders; no pagination.
    """
    from sqlalchemy import or_
    from app.models.tenant import Tenant
    from app.models.customer import Customer
    from app.models.order import Order, OrderItem

    if not phone and not name:
        raise HTTPException(status_code=400, detail="Provide phone or name")

    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tid = tenant.id

    q = db.query(Customer).filter(Customer.tenant_id == tid)
    if phone:
        _p = phone.strip().lstrip("+")
        _p10 = _p[2:] if (_p.startswith("91") and len(_p) == 12) else (_p[-10:] if len(_p) >= 10 else _p)
        q = q.filter(or_(Customer.phone.ilike(f"%{_p10}%"), Customer.phone.ilike(f"%{_p}%")))
    else:
        q = q.filter(Customer.name.ilike(f"%{name.strip()}%"))

    customers = q.limit(10).all()
    if not customers:
        return {"found": False, "orders": [], "message": "No customer found"}

    cust_ids = [str(c.id) for c in customers]
    orders = (
        db.query(Order)
        .filter(Order.tenant_id == tid, Order.customer_id.in_(cust_ids))
        .order_by(Order.created_at.desc())
        .limit(5)
        .all()
    )

    if not orders:
        return {"found": True, "orders": [], "message": "Customer found but no orders"}

    result = []
    for o in orders:
        cust = next((c for c in customers if str(c.id) == str(o.customer_id)), None)
        items = db.query(OrderItem).filter(OrderItem.order_id == o.id).all()
        items_summary = ", ".join(
            f"{it.product_name} x{float(it.quantity)}{it.unit.value}" for it in items
        )
        result.append({
            "order_number":           o.order_number,
            "status":                 o.status.value if o.status else None,
            "payment_status":         o.payment_status.value if o.payment_status else None,
            "total_amount":           float(o.total_amount) if o.total_amount else 0,
            "tracking_number":        o.tracking_number,
            "courier_name":           o.courier_name,
            "tracking_status_text":   o.tracking_status_text,
            "tracking_last_location": o.tracking_last_location,
            "tracking_last_event_at": o.tracking_last_event_at.isoformat() if o.tracking_last_event_at else None,
            "expected_delivery":      o.expected_delivery.isoformat() if o.expected_delivery else None,
            "delivered_at":           o.delivered_at.isoformat() if o.delivered_at else None,
            "items":                  items_summary,
            "customer_name":          cust.name if cust else None,
            "customer_phone":         cust.phone if cust else None,
            "created_at":             o.created_at.isoformat() if o.created_at else None,
        })

    return {"found": True, "orders": result, "customer_count": len(customers)}
