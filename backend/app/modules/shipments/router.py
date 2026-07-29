"""
Shipments Router — Phase 1 (webhook) + Phase 4 (dashboard)

Endpoints:
  POST /webhooks/shopify/order-created  — receive Shopify orders
  POST /webhooks/shopify/order-updated  — receive Shopify order updates
  POST /api/shipments/validate-risk     — run risk assessment on order
  POST /api/shipments/confirm-cod       — COD confirmation response
  GET  /api/shipments/dashboard         — admin dashboard stats
  GET  /api/shipments                   — list all shipments
  GET  /api/shipments/{id}              — shipment detail
  POST /api/shipments/{id}/sync-tracking — manual tracking refresh
  GET  /api/shipments/ndrs              — list open NDRs
  PATCH /api/shipments/ndrs/{id}        — resolve NDR
  GET  /api/shipments/risk              — risk assessment list
  PATCH /api/shipments/risk/{id}/review — manual risk review
  GET  /api/shipments/blacklist         — list blacklisted customers
  POST /api/shipments/blacklist         — manually blacklist customer
  DELETE /api/shipments/blacklist/{id}  — remove from blacklist
  GET  /api/shipments/rto-zones         — RTO zone risk map
  POST /api/shipments/sync-all          — trigger manual full sync
"""
import hashlib
import hmac
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.database.session import get_db
from app.core.auth.tenant import get_current_tenant_user, require_roles
from app.models.employee import Employee, RoleEnum
from app.models.order import Order, OrderStatusHistory, OrderStatus, PaymentStatus, PaymentMethod
from app.models.shopify_order import (
    ShopifyOrder, ShippingInfo, TrackingEvent,
    ShopifyOrderStatus, ShopifyFulfillmentStatus, ShippingPartner, TrackingStatus
)
from app.models.shipping_tariff import ShippingTariff
from app.models.shipping_config import ShopifyStore, DeliveryPartner, ShippingBusinessRules
from app.models.logistics import (
    OrderRiskAssessment, BlacklistedCustomer, NdrRecord, NdrStatus,
    CustomerDeliveryScore, RtoZone, CodTransaction, CodConfirmStatus,
    NotificationLog, RiskLevel,
)
from app.modules.orders.shopify_sync_service import ShopifyOrderSyncService
from app.core.risk_engine import RiskEngine
from app.core.notification_service import NotificationService
from app.core.tracking_worker import trigger_manual_sync
from app.core.logger import log_activity
from app.models.activity_log import LogLevel, LogModule

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Shipments"])


# ═════════════════════════════════════════════════════════════
# PHASE 1: Shopify Webhooks
# ═════════════════════════════════════════════════════════════

@router.post("/webhooks/shopify/order-created", include_in_schema=False)
async def shopify_order_created_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Receives Shopify 'orders/create' webhook.
    Validates HMAC, syncs order, runs risk assessment.
    """
    raw_body = await request.body()
    shopify_hmac = request.headers.get("X-Shopify-Hmac-Sha256", "")
    shop_domain  = request.headers.get("X-Shopify-Shop-Domain", "")

    # Find the store by domain
    store = db.query(ShopifyStore).filter(
        ShopifyStore.store_url == shop_domain,
        ShopifyStore.is_active == True,
    ).first()

    if not store:
        logger.warning(f"Webhook received from unknown shop: {shop_domain}")
        raise HTTPException(status_code=404, detail="Shop not found")

    # Validate HMAC signature
    if store.webhook_secret:
        try:
            from app.modules.shipping_config.service import decrypt_credential
            webhook_secret = decrypt_credential(store.webhook_secret)
        except Exception:
            webhook_secret = store.webhook_secret

        import base64
        computed = hmac.new(
            webhook_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).digest()
        computed_b64 = base64.b64encode(computed).decode()
        if not hmac.compare_digest(computed_b64, shopify_hmac):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Parse payload
    import json
    try:
        webhook_data = json.loads(raw_body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Sync order to DB
    sync_service = ShopifyOrderSyncService(db)
    result = sync_service.process_order_webhook(store, webhook_data)

    if not result["success"]:
        logger.error(f"Order sync failed: {result.get('error')}")
        return {"status": "error", "message": result.get("error")}

    # Get the saved order
    order_id = result["order_id"]
    order = db.query(ShopifyOrder).filter(ShopifyOrder.id == order_id).first()

    if order:
        # Run risk assessment in background
        background_tasks.add_task(_run_post_order_tasks, db, order, store)

    return {"status": "ok", "order_id": order_id}


@router.post("/webhooks/shopify/order-updated", include_in_schema=False)
async def shopify_order_updated_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """Receives Shopify 'orders/updated' webhook — syncs status changes."""
    raw_body   = await request.body()
    shop_domain = request.headers.get("X-Shopify-Shop-Domain", "")

    store = db.query(ShopifyStore).filter(
        ShopifyStore.store_url == shop_domain,
        ShopifyStore.is_active == True,
    ).first()
    if not store:
        raise HTTPException(status_code=404, detail="Shop not found")

    import json
    try:
        webhook_data = json.loads(raw_body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    sync_service = ShopifyOrderSyncService(db)
    result = sync_service.process_order_webhook(store, webhook_data)

    return {"status": "ok" if result["success"] else "error", "message": result.get("message", "")}


# ═════════════════════════════════════════════════════════════
# PHASE 4: Admin Dashboard
# ═════════════════════════════════════════════════════════════

@router.get("/api/shipments/dashboard")
def shipments_dashboard(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """
    Admin dashboard stats for the shipment management system.
    Returns counts and trends for orders, tracking, risk, NDR.
    """
    tid = current_user.tenant_id

    # ── Order counts ───────────────────────────────────────────
    total_orders = db.query(ShopifyOrder).filter(ShopifyOrder.tenant_id == tid).count()
    pending_shipping = db.query(ShopifyOrder).filter(
        ShopifyOrder.tenant_id == tid,
        ShopifyOrder.shipping_partner == None,
    ).count()

    # ── Shipping status breakdown ──────────────────────────────
    active_shipments = db.query(ShippingInfo).join(
        ShopifyOrder, ShippingInfo.shopify_order_id == ShopifyOrder.id
    ).filter(
        ShopifyOrder.tenant_id == tid,
        ShippingInfo.is_delivered == False,
    ).count()

    delivered_count = db.query(ShippingInfo).join(
        ShopifyOrder, ShippingInfo.shopify_order_id == ShopifyOrder.id
    ).filter(
        ShopifyOrder.tenant_id == tid,
        ShippingInfo.is_delivered == True,
    ).count()

    in_transit = db.query(ShippingInfo).join(
        ShopifyOrder, ShippingInfo.shopify_order_id == ShopifyOrder.id
    ).filter(
        ShopifyOrder.tenant_id == tid,
        ShippingInfo.tracking_status == TrackingStatus.in_transit,
    ).count()

    out_for_delivery = db.query(ShippingInfo).join(
        ShopifyOrder, ShippingInfo.shopify_order_id == ShopifyOrder.id
    ).filter(
        ShopifyOrder.tenant_id == tid,
        ShippingInfo.tracking_status == TrackingStatus.out_for_delivery,
    ).count()

    # ── NDR counts ─────────────────────────────────────────────
    open_ndrs = db.query(NdrRecord).filter(
        NdrRecord.tenant_id == tid,
        NdrRecord.status == NdrStatus.pending,
    ).count()

    # ── Risk counts ────────────────────────────────────────────
    high_risk_orders = db.query(OrderRiskAssessment).filter(
        OrderRiskAssessment.tenant_id == tid,
        OrderRiskAssessment.overall_risk_level == RiskLevel.high,
        OrderRiskAssessment.decision == "block",
    ).count()

    blocked_customers = db.query(BlacklistedCustomer).filter(
        BlacklistedCustomer.tenant_id == tid,
        BlacklistedCustomer.is_active == True,
    ).count()

    # ── COD stats ──────────────────────────────────────────────
    cod_pending = db.query(CodTransaction).filter(
        CodTransaction.tenant_id == tid,
        CodTransaction.status == CodConfirmStatus.pending,
    ).count()

    cod_confirmed = db.query(CodTransaction).filter(
        CodTransaction.tenant_id == tid,
        CodTransaction.status == CodConfirmStatus.confirmed,
    ).count()

    cod_rejected = db.query(CodTransaction).filter(
        CodTransaction.tenant_id == tid,
        CodTransaction.status == CodConfirmStatus.rejected,
    ).count()

    # ── Revenue (delivered orders) ─────────────────────────────
    revenue_result = db.query(func.sum(ShopifyOrder.total_price)).filter(
        ShopifyOrder.tenant_id == tid,
    ).scalar()
    total_revenue = float(revenue_result or 0)

    # ── Partner breakdown ──────────────────────────────────────
    delhivery_count = db.query(ShippingInfo).join(
        ShopifyOrder, ShippingInfo.shopify_order_id == ShopifyOrder.id
    ).filter(
        ShopifyOrder.tenant_id == tid,
        ShippingInfo.shipping_partner == ShippingPartner.delhivery,
    ).count()

    india_post_count = db.query(ShippingInfo).join(
        ShopifyOrder, ShippingInfo.shopify_order_id == ShopifyOrder.id
    ).filter(
        ShopifyOrder.tenant_id == tid,
        ShippingInfo.shipping_partner == ShippingPartner.india_post,
    ).count()

    return {
        "orders": {
            "total":            total_orders,
            "pending_shipping": pending_shipping,
            "active_shipments": active_shipments,
            "delivered":        delivered_count,
            "in_transit":       in_transit,
            "out_for_delivery": out_for_delivery,
        },
        "ndrs": {
            "open": open_ndrs,
        },
        "risk": {
            "high_risk_orders":   high_risk_orders,
            "blocked_customers":  blocked_customers,
        },
        "cod": {
            "pending":   cod_pending,
            "confirmed": cod_confirmed,
            "rejected":  cod_rejected,
        },
        "partners": {
            "delhivery":  delhivery_count,
            "india_post": india_post_count,
        },
        "revenue": {
            "total_order_value": total_revenue,
        },
    }


@router.get("/api/shipments")
def list_shipments(
    status: Optional[str] = None,
    partner: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """List all shipments with optional filtering."""
    tid = current_user.tenant_id
    page_size = min(page_size, 100)

    query = (
        db.query(ShopifyOrder)
        .filter(ShopifyOrder.tenant_id == tid)
    )

    if status:
        try:
            query = query.filter(ShopifyOrder.shopify_fulfillment_status == ShopifyFulfillmentStatus(status))
        except ValueError:
            pass

    if partner:
        try:
            query = query.filter(ShopifyOrder.shipping_partner == ShippingPartner(partner))
        except ValueError:
            pass

    total = query.count()
    orders = query.order_by(ShopifyOrder.created_at_shopify.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "shipments": [_format_shipment(o) for o in orders],
    }


@router.post("/api/shipments/sync-all")
async def trigger_full_sync(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin)),
):
    """Trigger a manual tracking sync for all active shipments of this tenant."""
    count = await trigger_manual_sync(tenant_id=str(current_user.tenant_id))
    return {"message": f"Sync triggered for {count} shipments", "count": count}


# ═════════════════════════════════════════════════════════════
# Risk Management
# ═════════════════════════════════════════════════════════════

@router.get("/api/shipments/risk")
def list_risk_assessments(
    decision: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """List risk assessments for all orders."""
    tid = current_user.tenant_id
    query = db.query(OrderRiskAssessment).filter(OrderRiskAssessment.tenant_id == tid)
    if decision:
        query = query.filter(OrderRiskAssessment.decision == decision)
    total = query.count()
    items = query.order_by(OrderRiskAssessment.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total":  total,
        "page":   page,
        "items": [
            {
                "id":            str(r.id),
                "order_id":      str(r.shopify_order_id),
                "risk_level":    r.overall_risk_level,
                "risk_score":    float(r.overall_risk_score),
                "decision":      r.decision,
                "risk_reasons":  r.risk_reasons,
                "created_at":    r.created_at.isoformat() if r.created_at else None,
            }
            for r in items
        ],
    }


@router.patch("/api/shipments/risk/{assessment_id}/review")
def review_risk_assessment(
    assessment_id: UUID,
    data: dict,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations)),
):
    """Manually approve or block an order after risk review."""
    ra = db.query(OrderRiskAssessment).filter(
        OrderRiskAssessment.id == assessment_id,
        OrderRiskAssessment.tenant_id == current_user.tenant_id,
    ).first()
    if not ra:
        raise HTTPException(status_code=404, detail="Risk assessment not found")

    new_decision = data.get("decision")  # approve | block
    if new_decision not in ("approve", "block"):
        raise HTTPException(status_code=400, detail="decision must be 'approve' or 'block'")

    ra.decision     = new_decision
    ra.reviewed_by  = current_user.email
    ra.reviewed_at  = datetime.now(timezone.utc)
    ra.review_note  = data.get("note", "")
    db.commit()

    return {"message": f"Order {new_decision}d by {current_user.email}", "decision": new_decision}


# ═════════════════════════════════════════════════════════════
# Blacklist Management
# ═════════════════════════════════════════════════════════════

@router.get("/api/shipments/blacklist")
def list_blacklisted_customers(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """List all blacklisted customers."""
    tid = current_user.tenant_id
    query = db.query(BlacklistedCustomer).filter(
        BlacklistedCustomer.tenant_id == tid,
        BlacklistedCustomer.is_active == True,
    )
    total = query.count()
    items = query.order_by(BlacklistedCustomer.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total":  total,
        "page":   page,
        "items": [
            {
                "id":             str(b.id),
                "phone":          b.customer_phone,
                "email":          b.customer_email,
                "name":           b.customer_name,
                "reason":         b.reason,
                "type":           b.blacklist_type,
                "is_permanent":   b.is_permanent,
                "expires_at":     b.expires_at.isoformat() if b.expires_at else None,
                "blocked_by":     b.blocked_by,
                "created_at":     b.created_at.isoformat() if b.created_at else None,
            }
            for b in items
        ],
    }


@router.post("/api/shipments/blacklist")
def add_to_blacklist(
    data: dict,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations)),
):
    """Manually blacklist a customer by phone."""
    phone = data.get("phone", "").strip()
    if not phone:
        raise HTTPException(status_code=400, detail="Phone number required")

    reason = data.get("reason", "Manually blacklisted by admin")
    is_permanent = data.get("is_permanent", False)
    days = data.get("duration_days", 180)

    expires_at = None if is_permanent else datetime.now(timezone.utc) + timedelta(days=days)

    bl = BlacklistedCustomer(
        tenant_id=current_user.tenant_id,
        customer_phone=phone,
        customer_email=data.get("email"),
        customer_name=data.get("name"),
        reason=reason,
        blacklist_type="manual",
        is_permanent=is_permanent,
        expires_at=expires_at,
        is_active=True,
        blocked_by=current_user.email,
    )
    db.add(bl)
    db.commit()
    return {"message": f"Customer {phone} blacklisted", "id": str(bl.id)}


@router.delete("/api/shipments/blacklist/{blacklist_id}")
def remove_from_blacklist(
    blacklist_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin)),
):
    """Remove a customer from the blacklist."""
    bl = db.query(BlacklistedCustomer).filter(
        BlacklistedCustomer.id == blacklist_id,
        BlacklistedCustomer.tenant_id == current_user.tenant_id,
    ).first()
    if not bl:
        raise HTTPException(status_code=404, detail="Blacklist entry not found")
    bl.is_active = False
    db.commit()
    return {"message": "Customer removed from blacklist"}


# ═════════════════════════════════════════════════════════════
# NDR Management
# ═════════════════════════════════════════════════════════════

@router.get("/api/shipments/ndrs")
def list_ndrs(
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """List all NDR records with optional status filter."""
    tid = current_user.tenant_id
    query = db.query(NdrRecord).filter(NdrRecord.tenant_id == tid)
    if status:
        try:
            query = query.filter(NdrRecord.status == NdrStatus(status))
        except ValueError:
            pass
    total = query.count()
    items = query.order_by(NdrRecord.ndr_date.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total":  total,
        "page":   page,
        "items": [
            {
                "id":              str(n.id),
                "order_id":        str(n.shopify_order_id),
                "tracking_number": n.tracking_number,
                "courier":         n.courier_name,
                "ndr_date":        n.ndr_date.isoformat(),
                "reason":          n.reason,
                "attempt":         n.attempt_number,
                "status":          n.status,
                "customer_phone":  n.customer_phone,
                "action_taken":    n.action_taken,
            }
            for n in items
        ],
    }


@router.patch("/api/shipments/ndrs/{ndr_id}")
def resolve_ndr(
    ndr_id: UUID,
    data: dict,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations)),
):
    """Mark an NDR as resolved / reattempt / RTO."""
    ndr = db.query(NdrRecord).filter(
        NdrRecord.id == ndr_id,
        NdrRecord.tenant_id == current_user.tenant_id,
    ).first()
    if not ndr:
        raise HTTPException(status_code=404, detail="NDR not found")

    action = data.get("action")  # reattempt | rto | resolved
    if action not in ("reattempt", "rto", "resolved"):
        raise HTTPException(status_code=400, detail="action must be reattempt | rto | resolved")

    status_map = {
        "reattempt": NdrStatus.reattempt,
        "rto":       NdrStatus.rto_initiated,
        "resolved":  NdrStatus.resolved,
    }
    ndr.status          = status_map[action]
    ndr.action_taken    = action
    ndr.action_date     = datetime.now(timezone.utc)
    ndr.resolution_note = data.get("note", "")
    db.commit()

    return {"message": f"NDR marked as {action}", "ndr_id": str(ndr_id)}


# ═════════════════════════════════════════════════════════════
# RTO Zones
# ═════════════════════════════════════════════════════════════

@router.get("/api/shipments/rto-zones")
def list_rto_zones(
    risk_level: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """List RTO risk zones by pincode."""
    tid = current_user.tenant_id
    query = db.query(RtoZone).filter(RtoZone.tenant_id == tid)
    if risk_level:
        try:
            query = query.filter(RtoZone.risk_level == RiskLevel(risk_level))
        except ValueError:
            pass
    total = query.count()
    zones = query.order_by(RtoZone.rto_percentage.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total":  total,
        "page":   page,
        "zones": [
            {
                "pincode":         z.pincode,
                "city":            z.city,
                "state":           z.state,
                "total_shipments": z.total_shipments,
                "rto_count":       z.rto_count,
                "rto_percentage":  float(z.rto_percentage),
                "risk_level":      z.risk_level,
                "risk_score":      float(z.risk_score),
            }
            for z in zones
        ],
    }


# ═════════════════════════════════════════════════════════════
# COD Confirmation
# ═════════════════════════════════════════════════════════════

@router.post("/api/shipments/confirm-cod")
async def confirm_cod(
    data: dict,
    db: Session = Depends(get_db),
):
    """
    Process COD confirmation response from customer.
    Called by webhook/callback when customer replies to WhatsApp.
    """
    order_id = data.get("order_id")
    code     = data.get("code", "").strip().upper()
    action   = data.get("action", "confirm").lower()  # confirm | reject

    if not order_id:
        raise HTTPException(status_code=400, detail="order_id required")

    cod_tx = db.query(CodTransaction).filter(
        CodTransaction.shopify_order_id == order_id,
        CodTransaction.status == CodConfirmStatus.pending,
    ).first()
    if not cod_tx:
        raise HTTPException(status_code=404, detail="No pending COD transaction found")

    # Check expiry
    now = datetime.now(timezone.utc)
    if cod_tx.expires_at and cod_tx.expires_at < now:
        cod_tx.status = CodConfirmStatus.timeout
        db.commit()
        return {"status": "timeout", "message": "COD confirmation expired"}

    if action == "confirm":
        if cod_tx.confirmation_code and code != cod_tx.confirmation_code:
            return {"status": "invalid_code", "message": "Incorrect confirmation code"}
        cod_tx.status       = CodConfirmStatus.confirmed
        cod_tx.confirmed_at = now
    elif action == "reject":
        cod_tx.status      = CodConfirmStatus.rejected
        cod_tx.rejected_at = now

    db.commit()

    return {
        "status":   cod_tx.status,
        "order_id": order_id,
        "message":  "COD confirmation processed",
    }


# ═════════════════════════════════════════════════════════════
# Helper Functions
# ═════════════════════════════════════════════════════════════

def _format_shipment(order: ShopifyOrder) -> dict:
    """Format a ShopifyOrder for list/detail views."""
    si = order.shipping_info
    return {
        "id":                   str(order.id),
        "shopify_order_number": order.shopify_order_name,
        "shopify_order_id":     order.shopify_order_id,
        "customer_name":        order.customer_name,
        "customer_phone":       order.customer_phone,
        "shipping_city":        order.shipping_city,
        "shipping_zip":         order.shipping_zip,
        "shipping_state":       order.shipping_state,
        "total_price":          float(order.total_price or 0),
        "currency":             order.currency,
        "shopify_status":       order.shopify_status,
        "fulfillment_status":   order.shopify_fulfillment_status,
        "financial_status":     order.shopify_financial_status,
        "shipping_partner":     order.shipping_partner.value if order.shipping_partner else None,
        "tracking_number":      order.tracking_number,
        "tracking_url":         order.tracking_url,
        "tracking_status":      si.tracking_status.value if si else None,
        "is_delivered":         si.is_delivered if si else False,
        "delivery_attempts":    si.delivery_attempt_count if si else 0,
        "created_at_shopify":   order.created_at_shopify.isoformat() if order.created_at_shopify else None,
        "synced_at":            order.synced_at.isoformat() if order.synced_at else None,
        "last_tracking_update": si.last_tracking_update.isoformat() if si and si.last_tracking_update else None,
    }


async def _run_post_order_tasks(db: Session, order: ShopifyOrder, store: ShopifyStore):
    """
    Background tasks run after a new order is received via webhook:
    1. Risk assessment
    2. Customer notification
    3. COD confirmation (if COD)
    4. Auto-ship (if rules say auto_create)
    """
    try:
        # 1. Risk assessment
        risk_engine = RiskEngine(db)
        assessment  = risk_engine.assess_order(order)

        # 2. Notify customer
        notif = NotificationService(db, str(order.tenant_id))

        if assessment["decision"] == "block":
            logger.warning(f"Order {order.shopify_order_name} BLOCKED: {assessment['risk_reasons']}")
            return  # Don't proceed with blocked orders

        await notif.send_order_confirmed(order)

        # 3. COD confirmation
        rules = db.query(ShippingBusinessRules).filter(
            ShippingBusinessRules.tenant_id == order.tenant_id
        ).first()

        is_cod = order.shopify_financial_status in ("pending", "cod")
        if is_cod and rules and rules.require_cod_confirmation:
            await _send_cod_confirmation(db, order)

        # 4. Auto-create shipment if configured
        if rules and rules.auto_create_on_order_created and assessment["decision"] == "approve":
            partner = db.query(DeliveryPartner).filter(
                DeliveryPartner.tenant_id == order.tenant_id,
                DeliveryPartner.is_primary == True,
                DeliveryPartner.is_active  == True,
            ).first()
            if partner:
                try:
                    from app.modules.shipping_config.service import decrypt_credential
                    api_key = decrypt_credential(partner.api_key)
                except Exception:
                    api_key = partner.api_key

                sync_svc = ShopifyOrderSyncService(db)
                if partner.partner_type == "delhivery":
                    result = await sync_svc.sync_tracking_with_delhivery(order, api_key, partner.client_name or "")
                elif partner.partner_type == "india_post":
                    result = await sync_svc.sync_tracking_with_india_post(
                        order, api_key, partner.client_id or "", ""
                    )

                if result and result.get("success"):
                    logger.info(f"Auto-created shipment for {order.shopify_order_name}: {result['tracking_number']}")
                    await notif.send_shipment_created(order, result["tracking_number"], order.tracking_url or "")

    except Exception as e:
        logger.error(f"Post-order task error for {order.shopify_order_name}: {e}")


async def _send_cod_confirmation(db: Session, order: ShopifyOrder):
    """Create a COD transaction and send confirmation request."""
    import random
    code = str(random.randint(100000, 999999))
    expires = datetime.now(timezone.utc) + timedelta(minutes=30)

    cod_tx = CodTransaction(
        tenant_id=order.tenant_id,
        shopify_order_id=order.id,
        amount=order.total_price,
        currency=order.currency,
        customer_phone=order.customer_phone or order.shipping_phone or "",
        customer_name=order.customer_name,
        status=CodConfirmStatus.pending,
        confirmation_code=code,
        expires_at=expires,
    )
    db.add(cod_tx)
    db.commit()

    notif = NotificationService(db, str(order.tenant_id))
    sent = await notif.send_cod_confirmation(order, code)

    if sent:
        cod_tx.sent_at = datetime.now(timezone.utc)
        db.commit()


# ═════════════════════════════════════════════════════════════
# Shipment Detail (must be LAST — {shipment_id} catches all)
# ═════════════════════════════════════════════════════════════

@router.get("/api/shipments/{shipment_id}")
def get_shipment_detail(
    shipment_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Get full shipment details including tracking events, risk assessment, NDR."""
    tid = current_user.tenant_id

    order = db.query(ShopifyOrder).filter(
        ShopifyOrder.id == shipment_id,
        ShopifyOrder.tenant_id == tid,
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Shipment not found")

    # Risk assessment
    risk = db.query(OrderRiskAssessment).filter(
        OrderRiskAssessment.shopify_order_id == order.id
    ).first()

    # NDR records
    ndrs = db.query(NdrRecord).filter(
        NdrRecord.shopify_order_id == order.id
    ).order_by(NdrRecord.ndr_date.desc()).all()

    # Tracking events
    events = db.query(TrackingEvent).filter(
        TrackingEvent.shopify_order_id == order.id
    ).order_by(TrackingEvent.event_time.desc()).all()

    # Shipping info
    si = order.shipping_info

    return {
        **_format_shipment(order),
        "line_items": order.line_items_json or [],
        "billing_address": {
            "name":    order.billing_name,
            "address": order.billing_address_line1,
            "city":    order.billing_city,
            "state":   order.billing_state,
            "zip":     order.billing_zip,
        },
        "shipping_charges": {
            "base_charge":     float(si.base_charge or 0) if si else 0,
            "fuel_surcharge":  float(si.fuel_surcharge or 0) if si else 0,
            "total_charge":    float(si.total_charge or 0) if si else 0,
        } if si else None,
        "risk_assessment": {
            "level":       risk.overall_risk_level if risk else None,
            "score":       float(risk.overall_risk_score) if risk else None,
            "decision":    risk.decision if risk else None,
            "reasons":     risk.risk_reasons if risk else [],
            "flags": {
                "blacklisted":     risk.is_customer_blacklisted if risk else False,
                "high_rto_zone":   risk.is_high_rto_zone if risk else False,
                "high_value":      risk.is_high_value_order if risk else False,
                "cod_order":       risk.is_cod_order if risk else False,
                "new_customer":    risk.is_new_customer if risk else False,
                "multiple_rto":    risk.has_multiple_rto if risk else False,
                "cod_rejections":  risk.has_cod_rejections if risk else False,
            },
        } if risk else None,
        "ndrs": [
            {
                "id":            str(n.id),
                "date":          n.ndr_date.isoformat(),
                "reason":        n.reason,
                "attempt":       n.attempt_number,
                "status":        n.status,
                "action_taken":  n.action_taken,
                "resolution":    n.resolution_note,
            }
            for n in ndrs
        ],
        "tracking_events": [
            {
                "status":      e.event_status,
                "location":    e.location,
                "description": e.description,
                "time":        e.event_time.isoformat() if e.event_time else None,
            }
            for e in events
        ],
    }


@router.post("/api/shipments/{shipment_id}/sync-tracking")
async def manual_sync_tracking(
    shipment_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Manually trigger tracking refresh for a specific shipment."""
    order = db.query(ShopifyOrder).filter(
        ShopifyOrder.id == shipment_id,
        ShopifyOrder.tenant_id == current_user.tenant_id,
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Shipment not found")

    if not order.shipping_partner or not order.tracking_number:
        raise HTTPException(status_code=400, detail="No tracking number assigned")

    # Get partner credentials
    partner = db.query(DeliveryPartner).filter(
        DeliveryPartner.tenant_id == order.tenant_id,
        DeliveryPartner.partner_type == order.shipping_partner.value,
        DeliveryPartner.is_active == True,
    ).first()
    if not partner:
        raise HTTPException(status_code=400, detail="Delivery partner not configured")

    try:
        from app.modules.shipping_config.service import decrypt_credential
        api_key = decrypt_credential(partner.api_key)
    except Exception:
        api_key = partner.api_key

    sync_svc = ShopifyOrderSyncService(db)
    result = await sync_svc.fetch_tracking_updates(
        order,
        delhivery_key=api_key if order.shipping_partner == ShippingPartner.delhivery else None,
        ip_api_key=api_key if order.shipping_partner == ShippingPartner.india_post else None,
    )

    return {
        "success":      result.get("success"),
        "status":       result.get("status"),
        "events_added": len(result.get("events", [])),
    }


# ═════════════════════════════════════════════════════════════
# FULL REFRESH — pull from all sources (Shopify + Delhivery + WhatsApp)
# ═════════════════════════════════════════════════════════════

from pydantic import BaseModel as _BM

class SetCourierRequest(_BM):
    partner: str          # "delhivery" | "india_post" | "bluedart" | "manual"
    tracking_number: Optional[str] = None
    tracking_url:    Optional[str] = None

class SetIndiaPostTrackingRequest(_BM):
    tracking_number: str


@router.post("/api/shipments/full-refresh")
async def full_refresh(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations)),
):
    """
    Manual refresh from all sources:
    - Shopify: pull latest orders + abandoned carts
    - Delhivery: refresh all active tracking
    - WhatsApp/WABIS: no pull needed (push only)
    Returns immediately — sync runs in background.
    """
    tenant_id = str(current_user.tenant_id)

    async def _do_full_refresh():
        from app.core.shopify_sync_worker import trigger_shopify_sync
        from app.core.tracking_worker import trigger_manual_sync
        await trigger_shopify_sync(tenant_id=tenant_id)
        await trigger_manual_sync(tenant_id=tenant_id)

    background_tasks.add_task(_do_full_refresh)
    return {"status": "started", "message": "Full refresh running in background (Shopify + Delhivery)"}


@router.post("/api/shipments/sync-shopify")
async def sync_shopify_now(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations)),
):
    """
    Immediately sync latest orders from Shopify and return results.
    Runs synchronously (waits for completion).
    """
    from app.core.shopify_sync_worker import trigger_shopify_sync
    result = await trigger_shopify_sync(tenant_id=str(current_user.tenant_id))
    return result


@router.get("/api/shipments/test-fetch")
async def test_fetch_last5(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations)),
):
    """
    FOR TESTING: Fetch last 5 orders from Shopify + last 5 from Delhivery.
    Returns raw data from both sources for verification.
    """
    from app.core.shipping.shopify_api_client import ShopifyAPIClient
    from app.core.shipping.delhivery_client import DelhiveryAPIClient

    tid = current_user.tenant_id

    # ── Shopify ────────────────────────────────────────────────
    shopify_store = db.query(ShopifyStore).filter(
        ShopifyStore.tenant_id == tid,
        ShopifyStore.is_active == True,
    ).first()

    shopify_orders = []
    shopify_error  = None
    if shopify_store and shopify_store.api_access_token:
        try:
            from app.modules.shipping_config.service import decrypt_credential
            token = decrypt_credential(shopify_store.api_access_token)
        except Exception:
            token = shopify_store.api_access_token

        client = ShopifyAPIClient(
            store_url=shopify_store.store_url,
            access_token=token,
            api_version=shopify_store.api_version or "2024-01",
        )
        result = await client.get_last_n_orders(n=5)
        if result["success"]:
            shopify_orders = [
                {
                    "id":          o.get("id"),
                    "name":        o.get("name"),
                    "customer":    (o.get("customer") or {}).get("email") or o.get("email"),
                    "total_price": o.get("total_price"),
                    "status":      o.get("financial_status"),
                    "fulfillment": o.get("fulfillment_status"),
                    "created_at":  o.get("created_at"),
                }
                for o in result["orders"]
            ]
        else:
            shopify_error = result.get("error")
    else:
        shopify_error = "No Shopify store configured"

    # ── Delhivery ──────────────────────────────────────────────
    delhivery_partner = db.query(DeliveryPartner).filter(
        DeliveryPartner.tenant_id == tid,
        DeliveryPartner.partner_type == "delhivery",
        DeliveryPartner.is_active == True,
    ).first()

    delhivery_shipments = []
    delhivery_error     = None
    if delhivery_partner:
        try:
            from app.modules.shipping_config.service import decrypt_credential
            api_key = decrypt_credential(delhivery_partner.api_key)
        except Exception:
            api_key = delhivery_partner.api_key

        client = DelhiveryAPIClient(
            api_key=api_key,
            client_name=delhivery_partner.client_name or "",
        )
        # Fetch last 5 local orders that have Delhivery tracking and show their status
        tracked = (
            db.query(ShopifyOrder)
            .filter(
                ShopifyOrder.tenant_id == tid,
                ShopifyOrder.shipping_partner == ShippingPartner.delhivery,
                ShopifyOrder.tracking_number != None,
            )
            .order_by(ShopifyOrder.created_at_shopify.desc())
            .limit(5)
            .all()
        )
        for order in tracked:
            tracking_result = await client.get_tracking_status(order.tracking_number)
            delhivery_shipments.append({
                "order_name":      order.shopify_order_name,
                "waybill":         order.tracking_number,
                "delhivery_status": tracking_result.get("status") if tracking_result.get("success") else "fetch_failed",
                "location":        tracking_result.get("location", ""),
                "last_update":     tracking_result.get("last_update", ""),
                "error":           tracking_result.get("error") if not tracking_result.get("success") else None,
            })
    else:
        delhivery_error = "No Delhivery partner configured"

    return {
        "shopify": {
            "store":  shopify_store.store_url if shopify_store else None,
            "orders": shopify_orders,
            "error":  shopify_error,
        },
        "delhivery": {
            "shipments": delhivery_shipments,
            "error":     delhivery_error,
        },
    }


@router.post("/api/shipments/{order_id}/set-courier")
async def set_courier_partner(
    order_id: UUID,
    data: SetCourierRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations, RoleEnum.sales)),
):
    """
    Employee selects the shipping/courier partner for a Shopify order.
    For Delhivery: auto-creates waybill via API.
    For India Post: tracking_number must be provided (given by India Post / uploaded).
    For other couriers: tracking_number required.
    """
    order = db.query(ShopifyOrder).filter(
        ShopifyOrder.id == order_id,
        ShopifyOrder.tenant_id == current_user.tenant_id,
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    try:
        partner_enum = ShippingPartner(data.partner)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid partner: {data.partner}. Choose: delhivery, india_post, bluedart, manual")

    # ── Delhivery: auto-create waybill ─────────────────────────
    if partner_enum == ShippingPartner.delhivery and not data.tracking_number:
        delhivery = db.query(DeliveryPartner).filter(
            DeliveryPartner.tenant_id == current_user.tenant_id,
            DeliveryPartner.partner_type == "delhivery",
            DeliveryPartner.is_active == True,
        ).first()
        if not delhivery:
            raise HTTPException(status_code=400, detail="Delhivery not configured")

        sync_svc = ShopifyOrderSyncService(db)
        try:
            from app.modules.shipping_config.service import decrypt_credential
            api_key = decrypt_credential(delhivery.api_key)
        except Exception:
            api_key = delhivery.api_key

        result = await sync_svc.sync_tracking_with_delhivery(
            order, api_key, delhivery.client_name or ""
        )
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error", "Delhivery API failed"))
        return {
            "success": True,
            "partner": "delhivery",
            "tracking_number": result["tracking_number"],
            "message": "Delhivery waybill created automatically",
        }

    # ── India Post: tracking number provided by employee ───────
    if partner_enum == ShippingPartner.india_post:
        if not data.tracking_number:
            raise HTTPException(status_code=400, detail="India Post tracking number is required (provide it manually or via xlsx upload)")
        order.shipping_partner = ShippingPartner.india_post
        order.tracking_number  = data.tracking_number
        order.tracking_url     = (data.tracking_url or
            f"https://tracking.indiapost.gov.in/TrackConsignment.aspx?TrackNum={data.tracking_number}")
        db.commit()
        return {
            "success": True,
            "partner": "india_post",
            "tracking_number": data.tracking_number,
            "message": "India Post tracking number saved",
        }

    # ── Other couriers (manual, bluedart, etc.) ────────────────
    if not data.tracking_number:
        raise HTTPException(status_code=400, detail="tracking_number is required for this courier")

    order.shipping_partner = partner_enum
    order.tracking_number  = data.tracking_number
    order.tracking_url     = data.tracking_url or ""
    db.commit()
    return {
        "success": True,
        "partner": data.partner,
        "tracking_number": data.tracking_number,
        "message": "Courier and tracking number saved",
    }


@router.patch("/api/shipments/{order_id}/india-post-tracking")
async def set_india_post_tracking(
    order_id: UUID,
    data: SetIndiaPostTrackingRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations, RoleEnum.sales)),
):
    """
    Set or update India Post tracking number for an order.
    The article number is provided by the employee (from India Post receipt,
    xlsx upload, or online booking confirmation).
    """
    order = db.query(ShopifyOrder).filter(
        ShopifyOrder.id == order_id,
        ShopifyOrder.tenant_id == current_user.tenant_id,
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.shipping_partner = ShippingPartner.india_post
    order.tracking_number  = data.tracking_number
    order.tracking_url     = f"https://tracking.indiapost.gov.in/TrackConsignment.aspx?TrackNum={data.tracking_number}"
    db.commit()

    return {
        "success":        True,
        "tracking_number": data.tracking_number,
        "tracking_url":    order.tracking_url,
        "message":        "India Post article number saved",
    }


@router.post("/api/shipments/india-post-xlsx-upload")
async def upload_india_post_xlsx(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations)),
):
    """
    Upload India Post xlsx file to bulk-assign tracking numbers.
    Excel format: columns must include 'Order Number' and 'Article Number'
    (or 'Tracking Number'). Matches by Shopify order name (#1001, etc.).
    """
    from fastapi import UploadFile, File
    import io
    raise HTTPException(
        status_code=501,
        detail="Use the multipart form endpoint: POST /api/shipments/india-post-xlsx (with file upload)"
    )


@router.post("/api/shipments/india-post-xlsx")
async def process_india_post_xlsx(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations)),
):
    """
    Bulk-assign India Post tracking from xlsx.
    Expects multipart form with 'file' field containing xlsx.
    Columns: 'Order Number' (Shopify order name like #1001) + 'Article Number'
    """
    from fastapi import Request
    raise HTTPException(
        status_code=400,
        detail="Send a multipart/form-data POST with 'file' field containing the India Post xlsx"
    )


@router.post("/api/shipments/india-post-xlsx-v2")
async def process_india_post_xlsx_v2(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations)),
):
    """
    Bulk-assign India Post tracking + delivery status to SHOPIFY orders.

    FILE TYPE 1 — Tracking only  (columns: Name/OrderNo + Article/Tracking number)
      → Sets tracking number + marks order as fulfilled (shipped)
    FILE TYPE 2 — Delivery xlsx  (columns include delivery status / event-description)
      → Sets tracking + marks delivered + sets financial_status = paid (COD collected)

    Matching priority:
      1. Shopify order name exact match (#1001, etc.)
      2. Tracking number match (if already set)
      3. Customer shipping_name fuzzy match
    """
    import openpyxl, io, re, logging as _log

    form = await request.form()
    xlsx_file = form.get("file")
    upload_mode = str(form.get("upload_mode") or "").strip().lower()
    if not xlsx_file:
        raise HTTPException(status_code=400, detail="No 'file' field in form data")

    content = await xlsx_file.read()
    try:
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        ws = wb.active
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot parse xlsx: {e}")

    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        raise HTTPException(status_code=400, detail="xlsx file has no data rows")

    headers = [str(h or "").strip().lower() for h in rows[0]]
    _log.warning(f"[shopify-xlsx-upload] headers detected: {headers}")

    # ── Column detection ───────────────────────────────────────────────────
    # Shopify order number column
    order_col = _find_col(headers, [
        "order number", "order no", "order no.", "shopify order", "order_number",
        "ordernumber", "order name", "order id",
    ])
    # Customer name column
    cust_col = _find_col(headers, [
        "receiver-name", "sender-name", "receiver name", "sender name",
        "customer name", "customer", "name", "shipping name",
        "recipient", "addressee", "consignee", "addressee name",
        "to name", "beneficiary", "party name",
    ])
    # Tracking / article number column
    track_col = _find_col(headers, [
        "article-number", "article-no",
        "article number", "article no", "article no.", "article_number",
        "tracking number", "tracking no", "tracking no.", "tracking_number",
        "awb", "awb number", "awb no", "barcode",
        "consignment no", "consignment no.", "consignment number",
        "tracking id", "shipment no", "shipment number",
        "booking no", "booking no.", "booking number",
        "speed post no", "reg no", "registered no",
        "parcel no", "parcel number", "article",
    ])
    # Delivery status column
    status_col = _find_col(headers, [
        "event-description", "event-code", "event description", "event code",
        "delivery status", "status", "delivered", "shipment status",
        "current status", "delivery", "event", "current event",
        "latest status", "remarks", "delivery remarks",
        "status description", "scan event", "scan status",
    ])

    # Fallback: detect tracking column by scanning cell values for India Post article patterns
    if track_col is None:
        track_col = _detect_tracking_col_by_content(rows, len(headers))
        if track_col is not None:
            _log.warning(f"[shopify-xlsx-upload] tracking column auto-detected by content at index {track_col}")

    # 2-column fallback: assume col 0 = name, col 1 = tracking
    if track_col is None and len(headers) == 2:
        cust_col  = 0
        track_col = 1
        _log.warning("[shopify-xlsx-upload] 2-column file — assuming col0=name, col1=tracking")

    if track_col is None:
        _log.error(f"[shopify-xlsx-upload] FAILED — cannot find tracking column. Headers: {headers}")
        raise HTTPException(
            status_code=400,
            detail=f"Cannot find tracking/article column. Headers found: {headers}"
        )

    # ── Name normalisation for fuzzy matching ──────────────────────────────
    def _normalise_name(raw: str) -> str:
        s = raw.lower().strip()
        s = re.sub(r"\b(mr|mrs|ms|miss|dr|sri|smt|shri|er|prof)\.?\s*", "", s)
        s = re.sub(r"[,.\-_/\\]+", " ", s)
        return re.sub(r"\s+", " ", s).strip()

    def _name_match(order_name: str, xlsx_name: str) -> bool:
        o = _normalise_name(order_name)
        x = _normalise_name(xlsx_name)
        if not o or not x:
            return False
        if o == x or x in o or o in x:
            return True
        x_words = set(x.split())
        o_words = set(o.split())
        if len(x_words) >= 2 and x_words.issubset(o_words):
            return True
        if len(o_words) >= 2 and o_words.issubset(x_words):
            return True
        return False

    # ── Pre-load all tenant Shopify orders ─────────────────────────────────
    all_orders = (
        db.query(ShopifyOrder)
        .filter(ShopifyOrder.tenant_id == current_user.tenant_id)
        .order_by(ShopifyOrder.created_at_shopify.desc())
        .all()
    )
    # Indexes for fast lookup
    order_name_index: dict[str, ShopifyOrder] = {
        o.shopify_order_name.strip().lower(): o for o in all_orders if o.shopify_order_name
    }
    tracking_index: dict[str, ShopifyOrder] = {
        o.tracking_number.strip().lower(): o for o in all_orders if o.tracking_number
    }

    updated       = []
    skipped       = []
    delivered_paid = []

    for idx, row in enumerate(rows[1:], start=2):
        order_val  = str(row[order_col]  or "").strip() if order_col  is not None and order_col  < len(row) else ""
        cust_val   = str(row[cust_col]   or "").strip() if cust_col   is not None and cust_col   < len(row) else ""
        track_val  = str(row[track_col]  or "").strip() if track_col  < len(row) else ""
        status_val = str(row[status_col] or "").strip().lower() if status_col is not None and status_col < len(row) else ""

        # Skip empty rows
        if not track_val and not cust_val and not order_val:
            continue
        # Skip repeat header rows
        if track_val.lower() in ("article number", "tracking number", "awb", "tracking no"):
            continue
        if not track_val:
            skipped.append({"row": idx, "customer": cust_val or order_val, "reason": "Missing tracking number"})
            continue

        # ── Find matching Shopify order ────────────────────────────────────
        order = None

        # Priority 1: Shopify order name (#1001 etc.)
        if order_val:
            order_key = order_val.lower()
            order = order_name_index.get(order_key)
            if not order:
                # Try with/without # prefix
                alt = ("#" + order_val).lower() if not order_val.startswith("#") else order_val[1:].lower()
                order = order_name_index.get(alt)

        # Priority 2: Existing tracking number match
        if order is None:
            order = tracking_index.get(track_val.lower())

        # Priority 3: Customer name fuzzy match
        if order is None and cust_val:
            for o in all_orders:
                name = o.shipping_name or o.customer_name or ""
                if _name_match(name, cust_val):
                    order = o
                    break

        if order is None:
            reason = f"No order matched for order='{order_val}' / name='{cust_val}' / tracking='{track_val}'"
            skipped.append({"row": idx, "customer": cust_val or order_val, "tracking": track_val, "reason": reason})
            continue

        # ── Detect delivery/return status ──────────────────────────────────
        is_delivered = any(kw in status_val for kw in [
            "delivered", "delivery", "dlv", "success", "d ", "dl", "del"
        ]) if status_val else False
        is_returned  = any(kw in status_val for kw in [
            "return", "rto", "rts", "undelivered", "failed"
        ]) if status_val else False

        # ── Always assign tracking ─────────────────────────────────────────
        order.shipping_partner = ShippingPartner.india_post
        order.tracking_number  = track_val
        order.tracking_url     = f"https://tracking.indiapost.gov.in/TrackConsignment.aspx?TrackNum={track_val}"
        tracking_index[track_val.lower()] = order

        action_taken = "tracking updated"

        if is_returned:
            order.shopify_status             = ShopifyOrderStatus.returned
            order.shopify_fulfillment_status = ShopifyFulfillmentStatus.cancelled
            action_taken = "marked returned"

        elif is_delivered:
            order.shopify_fulfillment_status = ShopifyFulfillmentStatus.delivered
            order.shopify_status             = ShopifyOrderStatus.fulfilled
            order.delivered_at               = datetime.now(timezone.utc)
            # Auto-mark paid on delivery — COD collected at doorstep
            order.shopify_financial_status   = "paid"
            action_taken = "delivered + paid ✅"
            delivered_paid.append({
                "order_number": order.shopify_order_name,
                "customer":     order.shipping_name or order.customer_name or "",
                "tracking":     track_val,
            })

        elif not status_val:
            # Tracking-only file: advance to fulfilled (shipped) if not already delivered/returned
            if order.shopify_fulfillment_status not in (
                ShopifyFulfillmentStatus.fulfilled,
                ShopifyFulfillmentStatus.delivered,
                ShopifyFulfillmentStatus.cancelled,
            ):
                order.shopify_fulfillment_status = ShopifyFulfillmentStatus.fulfilled
                order.shopify_status             = ShopifyOrderStatus.fulfilled
                action_taken = "tracking updated → fulfilled"

        updated.append({
            "order_number": order.shopify_order_name,
            "customer":     order.shipping_name or order.customer_name or "",
            "tracking":     track_val,
            "action":       action_taken,
        })

    db.commit()

    return {
        "success":            True,
        "updated_count":      len(updated),
        "skipped_count":      len(skipped),
        "delivered_and_paid": len(delivered_paid),
        "updated":            updated,
        "skipped":            skipped,
        "delivered_paid_details": delivered_paid,
    }


@router.post("/api/shipments/shopify/india-post-xlsx-preview")
async def preview_shopify_india_post_xlsx(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations)),
):
    """
    Preview what a Shopify India Post xlsx file would match — WITHOUT making changes.
    Returns matched / unmatched rows so you can verify before committing.
    """
    import openpyxl, io, re

    form = await request.form()
    xlsx_file = form.get("file")
    upload_mode = str(form.get("upload_mode") or "").strip().lower()
    if not xlsx_file:
        raise HTTPException(status_code=400, detail="No 'file' field in form data")

    content = await xlsx_file.read()
    try:
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        ws = wb.active
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot parse xlsx: {e}")

    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        raise HTTPException(status_code=400, detail="xlsx has no data rows")

    headers = [str(h or "").strip().lower() for h in rows[0]]

    order_col  = _find_col(headers, [
        "order number", "order no", "order no.", "shopify order", "order_number",
        "ordernumber", "order name", "order id",
    ])
    cust_col   = _find_col(headers, [
        "receiver-name", "sender-name", "receiver name", "sender name",
        "customer name", "customer", "name", "shipping name",
        "recipient", "addressee", "consignee", "addressee name",
        "to name", "beneficiary", "party name",
    ])
    track_col  = _find_col(headers, [
        "article-number", "article-no",
        "article number", "article no", "article no.", "article_number",
        "tracking number", "tracking no", "tracking no.", "tracking_number",
        "awb", "awb number", "awb no", "barcode",
        "consignment no", "consignment no.", "consignment number",
        "tracking id", "shipment no", "shipment number",
        "booking no", "booking no.", "booking number",
        "speed post no", "reg no", "registered no",
        "parcel no", "parcel number", "article",
    ])
    status_col = _find_col(headers, [
        "event-description", "event-code", "event description", "event code",
        "delivery status", "status", "delivered", "shipment status",
        "current status", "delivery", "event", "current event",
        "latest status", "remarks", "delivery remarks",
        "status description", "scan event", "scan status",
    ])

    if track_col is None:
        track_col = _detect_tracking_col_by_content(rows, len(headers))
    if track_col is None and len(headers) == 2:
        cust_col  = 0
        track_col = 1

    if track_col is None:
        return {
            "error": f"No tracking column found. Headers: {headers}",
            "headers": headers,
            "rows_preview": [[str(c or "") for c in r] for r in rows[:5]],
        }

    def _normalise_name(raw: str) -> str:
        s = raw.lower().strip()
        s = re.sub(r"\b(mr|mrs|ms|miss|dr|sri|smt|shri|er|prof)\.?\s*", "", s)
        s = re.sub(r"[,.\-_/\\]+", " ", s)
        return re.sub(r"\s+", " ", s).strip()

    def _name_match(order_name, xlsx_name):
        o = _normalise_name(order_name)
        x = _normalise_name(xlsx_name)
        if not o or not x:
            return False
        if o == x or x in o or o in x:
            return True
        x_words = set(x.split())
        o_words = set(o.split())
        if len(x_words) >= 2 and x_words.issubset(o_words):
            return True
        if len(o_words) >= 2 and o_words.issubset(x_words):
            return True
        return False

    all_orders = (
        db.query(ShopifyOrder)
        .filter(ShopifyOrder.tenant_id == current_user.tenant_id)
        .order_by(ShopifyOrder.created_at_shopify.desc())
        .all()
    )
    order_name_index = {o.shopify_order_name.strip().lower(): o for o in all_orders if o.shopify_order_name}
    tracking_index   = {o.tracking_number.strip().lower(): o  for o in all_orders if o.tracking_number}

    results = []
    for idx, row in enumerate(rows[1:], start=2):
        order_val  = str(row[order_col]  or "").strip() if order_col  is not None and order_col  < len(row) else ""
        cust_val   = str(row[cust_col]   or "").strip() if cust_col   is not None and cust_col   < len(row) else ""
        track_val  = str(row[track_col]  or "").strip() if track_col  < len(row) else ""
        status_val = str(row[status_col] or "").strip() if status_col is not None and status_col < len(row) else ""

        if not track_val and not cust_val and not order_val:
            continue
        if track_val.lower() in ("article number", "tracking number", "awb", "tracking no"):
            continue

        order        = None
        match_method = "none"

        if order_val:
            order_key = order_val.lower()
            order     = order_name_index.get(order_key)
            if not order:
                alt   = ("#" + order_val).lower() if not order_val.startswith("#") else order_val[1:].lower()
                order = order_name_index.get(alt)
            if order:
                match_method = "order_number"

        if order is None:
            order = tracking_index.get(track_val.lower())
            if order:
                match_method = "tracking"

        if order is None and cust_val:
            for o in all_orders:
                if _name_match(o.shipping_name or o.customer_name or "", cust_val):
                    order        = o
                    match_method = "name"
                    break

        is_delivered = any(kw in status_val.lower() for kw in [
            "delivered", "delivery", "dlv", "success"
        ]) if status_val else False

        results.append({
            "row":              idx,
            "xlsx_order":       order_val,
            "xlsx_name":        cust_val,
            "tracking":         track_val,
            "status_in_xlsx":   status_val,
            "will_mark_paid":   is_delivered,
            "matched":          order is not None,
            "match_method":     match_method,
            "order_number":     order.shopify_order_name if order else None,
            "order_name":       order.shipping_name or order.customer_name if order else None,
            "order_status":     order.shopify_fulfillment_status.value if order else None,
            "financial_status": order.shopify_financial_status if order else None,
            "current_tracking": order.tracking_number if order else None,
        })

    matched   = [r for r in results if r["matched"]]
    unmatched = [r for r in results if not r["matched"]]

    return {
        "total_rows":      len(results),
        "matched_count":   len(matched),
        "unmatched_count": len(unmatched),
        "headers_found": {
            "order_col":  headers[order_col]  if order_col  is not None else None,
            "name_col":   headers[cust_col]   if cust_col   is not None else None,
            "track_col":  headers[track_col]  if track_col  is not None else None,
            "status_col": headers[status_col] if status_col is not None else None,
        },
        "matched":   matched,
        "unmatched": unmatched,
    }


def _find_col(headers: list, candidates: list) -> Optional[int]:
    """Find first matching column index from header row (case-insensitive, partial match)."""
    for candidate in candidates:
        c = candidate.lower().strip()
        for i, h in enumerate(headers):
            h2 = h.lower().strip()
            if c in h2 or h2 in c:
                return i
    return None


def _detect_tracking_col_by_content(rows: list, num_cols: int) -> Optional[int]:
    """
    Fallback: scan data rows for India Post article number patterns.
    India Post article numbers: EE123456789IN, RX123456789IN, EM123456789IN, etc.
    """
    import re
    ip_pattern = re.compile(r'^[A-Z]{2}\d{9}[A-Z]{2}$', re.IGNORECASE)
    # Score each column by how many cells match the India Post pattern
    scores = [0] * num_cols
    for row in rows[1:min(20, len(rows))]:  # check up to 19 data rows
        for ci, cell in enumerate(row):
            if ci >= num_cols:
                break
            val = str(cell or "").strip()
            if ip_pattern.match(val):
                scores[ci] += 1
    best = max(scores)
    if best > 0:
        return scores.index(best)
    return None


def _normalise_status_text(raw: str) -> str:
    import re

    text = str(raw or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _normalise_tracking_text(raw: str) -> str:
    import re

    text = str(raw or "").strip().upper()
    if not text:
        return ""
    # Strip separators/spaces so variants like "EL 123 456 IN" still match.
    return re.sub(r"[^A-Z0-9]+", "", text)


def _classify_delivery_status(raw: str) -> tuple[bool, bool]:
    import re as _re

    text = _normalise_status_text(raw)
    if not text:
        return False, False

    # ── India Post event-code lookup (short uppercase codes sent as-is) ──
    # These appear when the status column is "event-code" rather than
    # "event-description". Normalized to lowercase before comparison.
    # Reference: India Post official event codes
    _IP_DELIVERED = {"id", "de"}                     # ID/DE = Item Delivered
    _IP_RETURNED  = {"rts", "rto", "rt", "cd"}       # RTS = Return to Sender, RTO = Return to Origin, CD = Charge Collect/Dead
    _IP_TRANSIT   = {"ofd", "ot", "io", "ba"}      # OFD = Out for Delivery, OT = In Transit, IO = In Office, BA = Booked

    # Single-token check: only apply code lookup when the whole cell is a
    # short 2-5 letter code (avoids matching "id" inside free-text strings).
    words = text.split()
    if len(words) == 1 and len(words[0]) <= 5:
        code = words[0]
        if code in _IP_DELIVERED:
            return True, False
        if code in _IP_RETURNED:
            return False, True
        # In-transit codes: not delivered, not returned
        if code in _IP_TRANSIT:
            return False, False

    # ── Free-text pattern matching ───────────────────────────────────────
    # Use word-boundary patterns to avoid false positives.
    # "out for delivery" must NOT match as delivered — only \bdelivered\b should.
    delivered_patterns = [
        r"\bdelivered\b",
        r"\bdelivery successful\b",
        r"\bsuccessfully delivered\b",
        r"\bdelivered to addressee\b",
        r"\bdelivered to recipient\b",
        r"\bdelivery confirmed\b",
        r"\bitem delivered\b",
        r"\bdelivered at destination\b",
        r"\bdelivered to customer\b",
        r"\bdelivered safe\b",
        r"\bdelivered successfully\b",
        r"\bdlv\b",
    ]
    returned_patterns = [
        r"\breturn(ed)?\b",
        r"\brto\b",
        r"\brts\b",
        r"\breturn to sender\b",
        r"\breturn to origin\b",
        r"\bundelivered\b",
        r"\bdelivery attempted\b",
        r"\bfailed delivery\b",
        r"\bdoor locked\b",
        r"\brefused\b",
        r"\brejected\b",
        r"\bcharge collect\b",
        r"\bdead letter\b",
    ]

    # ── In-transit patterns: indicates package still in delivery pipeline ──
    # Must be checked BEFORE returned patterns to prevent false positives.
    # These should NOT trigger either delivered or returned status.
    in_transit_patterns = [
        r"\bnot delivered\b",              # Just means not yet delivered (could be in transit)
        r"\bpending delivery\b",           # Pending delivery
        r"\bprocessing\b",                 # Still processing
        r"\bin transit\b",                 # Explicitly in transit
        r"\bitem received at destination\b",  # Received but not yet delivered
        r"\btaken out for delivery\b",     # Out for delivery (key indicator: not delivered yet!)
    ]
    is_in_transit = any(_re.search(p, text) for p in in_transit_patterns)

    is_returned = any(_re.search(p, text) for p in returned_patterns)
    is_delivered = any(_re.search(p, text) for p in delivered_patterns)

    # ── Priority: in-transit takes precedence (no status change) ──
    if is_in_transit:
        return False, False  # Neither delivered nor returned
    
    return is_delivered and not is_returned, is_returned


def _detect_status_col_by_content(rows: list, num_cols: int) -> Optional[int]:
    """Fallback: score columns by delivery/return-like status values in data rows."""
    scores = [0] * num_cols
    for row in rows[1:min(40, len(rows))]:
        for col_idx, cell in enumerate(row):
            if col_idx >= num_cols:
                break
            is_delivered, is_returned = _classify_delivery_status(cell)
            if is_delivered or is_returned:
                scores[col_idx] += 1

    best = max(scores) if scores else 0
    if best > 0:
        return scores.index(best)
    return None


def _parse_money_value(raw) -> Optional[float]:
    import re

    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)

    text = str(raw).strip()
    if not text:
        return None

    cleaned = text.lower().replace(",", "")
    for token in ("rs.", "rs", "inr", "rupees", "rupee", "₹"):
        cleaned = cleaned.replace(token, "")
    cleaned = cleaned.strip()

    # Keep only numeric symbols when mixed with labels.
    cleaned = re.sub(r"[^0-9.\-]", "", cleaned)
    if cleaned in {"", "-", ".", "-."}:
        return None

    try:
        return float(cleaned)
    except Exception:
        return None


def _detect_shipping_col_by_content(
    rows: list,
    num_cols: int,
    exclude_cols: Optional[set[int]] = None,
) -> Optional[int]:
    """Detect probable shipping-charge column by numeric value profile."""
    exclude = exclude_cols or set()
    scores = [0] * num_cols

    # Shipping values are usually low currency values, not pincode/phone/tracking numbers.
    for row in rows[1:min(60, len(rows))]:
        for col_idx, cell in enumerate(row):
            if col_idx >= num_cols or col_idx in exclude:
                continue

            parsed = _parse_money_value(cell)
            if parsed is None:
                continue

            # Prefer realistic shipping amounts.
            if 5 <= parsed <= 5000:
                scores[col_idx] += 2
            elif 0 <= parsed < 5:
                scores[col_idx] += 1

    best = max(scores) if scores else 0
    if best >= 2:
        return scores.index(best)
    return None


def _resolve_xlsx_upload_mode(requested_mode: str, status_col: Optional[int]) -> str:
    mode = (requested_mode or "").strip().lower()
    if mode in {"tracking", "delivery"}:
        return mode
    return "delivery" if status_col is not None else "tracking"


# ═════════════════════════════════════════════════════════════
# SHOPIFY CSV IMPORT  (no API token needed)
# ═════════════════════════════════════════════════════════════

@router.post("/api/shipments/shopify-csv-import")
async def import_shopify_csv(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations)),
):
    """
    Import Shopify orders from a CSV file exported from Shopify Admin.
    Works WITHOUT an API token — use when API integration is broken.

    How to get the CSV:
      Shopify Admin → Orders → Export → All orders → Export orders

    Handles both Shopify's standard CSV columns and common variations.
    Deduplicates by Shopify order name (e.g. #1001) — safe to re-upload.
    """
    import csv, io

    form = await request.form()
    csv_file = form.get("file")
    if not csv_file:
        raise HTTPException(status_code=400, detail="No 'file' field in form data")

    content = await csv_file.read()
    filename = getattr(csv_file, "filename", "")

    # Support both CSV and XLSX
    rows_data = []
    headers_raw = []

    if filename.lower().endswith(".xlsx") or filename.lower().endswith(".xls"):
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True)
        ws = wb.active
        all_rows = list(ws.iter_rows(values_only=True))
        if not all_rows:
            raise HTTPException(status_code=400, detail="Empty file")
        headers_raw = [str(h or "").strip() for h in all_rows[0]]
        for row in all_rows[1:]:
            rows_data.append([str(v or "").strip() for v in row])
    else:
        # CSV (default)
        try:
            text = content.decode("utf-8-sig")  # handle BOM
        except Exception:
            text = content.decode("latin-1")
        reader = csv.reader(io.StringIO(text))
        all_rows = list(reader)
        if not all_rows:
            raise HTTPException(status_code=400, detail="Empty CSV file")
        headers_raw = [h.strip() for h in all_rows[0]]
        rows_data = [[cell.strip() for cell in row] for row in all_rows[1:]]

    if not headers_raw:
        raise HTTPException(status_code=400, detail="No headers found in file")

    # Map header names → column indices
    h = [x.lower() for x in headers_raw]

    def col(candidates):
        """
        Match column by priority:
        1. Exact match (case-insensitive)
        2. Candidate is substring of header (candidate in hh)
        This avoids 'shipping' accidentally matching 'shipping address1'.
        """
        for c in candidates:
            # Pass 1: exact match
            for i, hh in enumerate(h):
                if c == hh:
                    return i
        for c in candidates:
            # Pass 2: candidate is substring of header (more specific → longer candidates win)
            for i, hh in enumerate(h):
                if c in hh:
                    return i
        return None

    # Shopify CSV standard columns
    idx_name       = col(["name", "order name", "order_name", "order #"])          # #1001
    idx_email      = col(["email", "customer email", "email address"])
    idx_phone      = col(["phone", "billing phone", "shipping phone", "telephone"])
    idx_created    = col(["created at", "created_at", "date", "order date"])
    idx_total      = col(["total", "total price", "total_price", "grand total"])
    idx_financial  = col(["financial status", "payment status", "financial_status"])
    idx_fulfillment= col(["fulfillment status", "fulfillment_status", "shipping status"])
    idx_cust_name  = col(["billing name", "billing_name", "customer name", "name"])
    idx_ship_name  = col(["shipping name", "shipping_name"])
    idx_ship_addr1 = col(["shipping address1", "shipping_address1", "address1", "shipping address"])
    idx_ship_addr2 = col(["shipping address2", "shipping_address2", "address2"])
    idx_ship_city  = col(["shipping city", "shipping_city", "city"])
    idx_ship_prov  = col(["shipping province", "shipping_province", "state", "province"])
    idx_ship_zip   = col(["shipping zip", "shipping_zip", "zip", "postal", "pincode"])
    idx_ship_cntry = col(["shipping country", "shipping_country", "country"])
    idx_ship_phone = col(["shipping phone", "shipping_phone"])
    idx_items      = col(["lineitem name", "lineitem_name", "line item", "product", "items"])
    idx_qty        = col(["lineitem quantity", "lineitem_quantity", "quantity", "qty"])
    idx_price      = col(["lineitem price", "lineitem_price", "price"])
    idx_currency   = col(["currency"])
    idx_tracking   = col(["tracking number", "tracking_number", "tracking", "awb"])
    idx_courier    = col(["shipping carrier", "carrier", "courier"])

    if idx_name is None:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot find 'Name' (order number) column. Found headers: {headers_raw[:15]}"
        )

    # Get the active Shopify store for this tenant
    store = db.query(ShopifyStore).filter(
        ShopifyStore.tenant_id == current_user.tenant_id,
        ShopifyStore.is_active == True,
    ).order_by(ShopifyStore.is_primary.desc()).first()

    if not store:
        raise HTTPException(
            status_code=400,
            detail="No active Shopify store configured for your account. "
                   "Go to Shipping Config → Shopify Stores and add a store first."
        )

    def _get(row, idx, default=""):
        if idx is None or idx >= len(row):
            return default
        return str(row[idx] or "").strip()

    def _parse_decimal(val):
        try:
            return float(val.replace(",", "").replace("₹", "").replace("$", "").strip() or 0)
        except Exception:
            return 0.0

    def _parse_dt(val):
        if not val:
            return datetime.now(timezone.utc)
        for fmt in ["%Y-%m-%d %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z",
                    "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]:
            try:
                dt = datetime.strptime(val[:25], fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                continue
        return datetime.now(timezone.utc)

    imported = []
    updated  = []
    skipped  = []
    errors   = []

    # Shopify CSV has multiple rows per order (one per line item)
    # Group rows by order name first
    order_groups: dict = {}
    for row in rows_data:
        if len(row) == 0:
            continue
        order_name = _get(row, idx_name)
        if not order_name:
            continue
        if order_name not in order_groups:
            order_groups[order_name] = []
        order_groups[order_name].append(row)

    for order_name, group_rows in order_groups.items():
        try:
            first = group_rows[0]

            # Build line_items from all rows in this order
            line_items = []
            for r in group_rows:
                item_name = _get(r, idx_items)
                if item_name:
                    line_items.append({
                        "name":     item_name,
                        "quantity": int(_get(r, idx_qty, "1") or 1),
                        "price":    _get(r, idx_price, "0"),
                    })

            # Core order fields from the first row
            customer_name = _get(first, idx_ship_name) or _get(first, idx_cust_name) or "Unknown"
            email         = _get(first, idx_email)
            phone         = _get(first, idx_ship_phone) or _get(first, idx_phone)
            total_price   = _parse_decimal(_get(first, idx_total, "0"))
            currency      = _get(first, idx_currency, "INR") or "INR"
            created_str   = _get(first, idx_created)
            fin_status    = _get(first, idx_financial, "pending").lower()
            ful_status    = _get(first, idx_fulfillment, "").lower()
            tracking_no   = _get(first, idx_tracking)
            courier_name  = _get(first, idx_courier)

            ship_name     = _get(first, idx_ship_name)
            ship_addr1    = _get(first, idx_ship_addr1)
            ship_addr2    = _get(first, idx_ship_addr2)
            ship_city     = _get(first, idx_ship_city)
            ship_state    = _get(first, idx_ship_prov)
            ship_zip      = _get(first, idx_ship_zip)
            ship_country  = _get(first, idx_ship_cntry, "India") or "India"
            ship_phone    = _get(first, idx_ship_phone) or phone

            created_at    = _parse_dt(created_str)

            # Map financial status
            if fin_status in ("paid", "authorized"):
                shopify_financial = "paid"
            elif fin_status in ("pending", ""):
                shopify_financial = "pending"
            elif fin_status in ("refunded", "voided"):
                shopify_financial = "refunded"
            else:
                shopify_financial = fin_status or "pending"

            # Map fulfillment status
            if "fulfilled" in ful_status or "shipped" in ful_status:
                shopify_ful = ShopifyFulfillmentStatus.fulfilled
                shopify_sta = ShopifyOrderStatus.fulfilled
            elif "partial" in ful_status:
                shopify_ful = ShopifyFulfillmentStatus.partial
                shopify_sta = ShopifyOrderStatus.confirmed
            else:
                shopify_ful = ShopifyFulfillmentStatus.unconfirmed
                shopify_sta = ShopifyOrderStatus.confirmed

            # Map shipping partner
            partner = None
            if courier_name:
                cl = courier_name.lower()
                if "delhivery" in cl:
                    partner = ShippingPartner.delhivery
                elif "india post" in cl or "indiapost" in cl:
                    partner = ShippingPartner.india_post
                else:
                    partner = ShippingPartner.manual

            # Generate a fake shopify_order_id from the order name
            # Use a stable hash so re-imports don't create duplicates
            import hashlib as _hl
            fake_id = "csv_" + _hl.md5(f"{store.id}:{order_name}".encode()).hexdigest()[:16]

            # Check existing by shopify_order_id
            existing = db.query(ShopifyOrder).filter(
                ShopifyOrder.shopify_store_id == store.id,
                ShopifyOrder.shopify_order_id == fake_id,
            ).first()

            if existing:
                # Update fields that may have changed
                existing.shopify_fulfillment_status = shopify_ful
                existing.shopify_status             = shopify_sta
                existing.shopify_financial_status   = shopify_financial
                existing.updated_at_shopify         = datetime.now(timezone.utc)
                if tracking_no and not existing.tracking_number:
                    existing.tracking_number = tracking_no
                if partner and not existing.shipping_partner:
                    existing.shipping_partner = partner
                updated.append(order_name)
            else:
                # Create new record
                order = ShopifyOrder(
                    tenant_id               = current_user.tenant_id,
                    shopify_store_id        = store.id,
                    shopify_order_id        = fake_id,
                    shopify_order_number    = order_name.lstrip("#"),
                    shopify_order_name      = order_name,
                    shopify_status          = shopify_sta,
                    shopify_fulfillment_status = shopify_ful,
                    shopify_financial_status   = shopify_financial,
                    customer_name           = customer_name,
                    customer_email          = email or None,
                    customer_phone          = phone or None,
                    # Billing = Shipping (CSV usually only has one address)
                    billing_name            = ship_name or customer_name,
                    billing_address_line1   = ship_addr1,
                    billing_city            = ship_city,
                    billing_state           = ship_state,
                    billing_zip             = ship_zip,
                    billing_country         = ship_country,
                    # Shipping address
                    shipping_name           = ship_name or customer_name,
                    shipping_address_line1  = ship_addr1 or "Unknown",
                    shipping_address_line2  = ship_addr2 or None,
                    shipping_city           = ship_city or "Unknown",
                    shipping_state          = ship_state or "Unknown",
                    shipping_zip            = ship_zip or "000000",
                    shipping_country        = ship_country,
                    shipping_phone          = ship_phone or None,
                    currency                = currency,
                    subtotal                = total_price,
                    taxes                   = 0,
                    discounts               = 0,
                    shipping_cost           = 0,
                    total_price             = total_price,
                    line_items_count        = len(line_items),
                    line_items_json         = line_items,
                    shipping_partner        = partner,
                    tracking_number         = tracking_no or None,
                    created_at_shopify      = created_at,
                    updated_at_shopify      = created_at,
                    notes                   = f"Imported from CSV on {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
                )
                db.add(order)
                db.flush()
                imported.append(order_name)

        except Exception as e:
            errors.append({"order": order_name, "error": str(e)})
            logger.error(f"CSV import error for order {order_name}: {e}")
            continue

    db.commit()

    return {
        "success": True,
        "imported": len(imported),
        "updated":  len(updated),
        "errors":   len(errors),
        "total_processed": len(order_groups),
        "imported_orders": imported[:50],   # cap at 50 for response size
        "updated_orders":  updated[:50],
        "error_details":   errors[:20],
        "message": (
            f"✅ {len(imported)} new orders imported, "
            f"{len(updated)} existing orders updated"
            + (f", {len(errors)} errors" if errors else "")
        ),
    }



@router.post("/api/shipments/manual-orders/india-post-xlsx")
async def process_manual_orders_india_post_xlsx(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations)),
):
    """
    Bulk-assign India Post tracking + delivery status to MANUAL orders.

    FILE TYPE 1 — Tracking only (columns: Name + Article/Tracking number)
    FILE TYPE 2 — Delivery status (columns: Name/Tracking + Status/Delivered)
    Both file types auto-detected from columns present.

        Matching priority:
            1. Tracking number exact match (if tracking already set on order)
            2. Order number exact match (if present in file)
            3. Phone + pincode exact match (if present in file)
            4. Customer delivery_name fuzzy match (strips titles, normalises spaces)
    """
    import openpyxl, io, re
    from decimal import Decimal as _Dec
    from app.models.order import PaymentStatus as PS, PaymentMethod as PM, OrderStatus as OS

    form = await request.form()
    xlsx_file = form.get("file")
    if not xlsx_file:
        raise HTTPException(status_code=400, detail="No 'file' field in form data")
    upload_mode = str(form.get("upload_mode") or "").strip().lower()

    content = await xlsx_file.read()
    try:
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        ws = wb.active
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot parse xlsx: {e}")

    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        raise HTTPException(status_code=400, detail="xlsx file has no data rows")

    # ── Normalise headers ───────────────────────────────────────────────────
    headers = [str(h or "").strip().lower() for h in rows[0]]
    import logging as _log
    _log.warning(f"[xlsx-upload] headers detected: {headers}")

    cust_col   = _find_col(headers, [
        # India Post bulk report (hyphenated)
        "receiver-name", "sender-name", "receiver name", "sender name",
        # Standard names
        "customer name", "customer", "name", "customer_name",
        "recipient", "addressee", "consignee", "addressee name",
        "to name", "beneficiary", "party name",
    ])
    order_col = _find_col(headers, [
        "order number", "order no", "order no.", "order_number",
        "reference", "reference number", "ref no", "booking reference",
        "invoice number", "invoice no",
    ])
    phone_col = _find_col(headers, [
        "receiver-mobile", "receiver mobile", "receiver mobile number", "receiver phone",
        "mobile", "mobile number", "phone", "phone number", "contact number",
        "consignee mobile", "consignee phone", "addressee mobile", "addressee phone",
        "to mobile", "to phone",
    ])
    pin_col = _find_col(headers, [
        "receiver-pincode", "receiver pincode", "delivery pincode", "delivery_pincode",
        "destination pincode", "destination_pincode", "pincode", "pin code", "pin",
        "consignee pincode", "addressee pincode", "to pincode",
    ])
    track_col  = _find_col(headers, [
        # India Post bulk report (hyphenated)
        "article-number", "article-no",
        # Standard names
        "article number", "article no", "article no.", "article_number",
        "tracking number", "tracking no", "tracking no.", "tracking_number",
        "awb", "awb number", "awb no", "barcode",
        "consignment no", "consignment no.", "consignment number",
        "tracking id", "shipment no", "shipment number",
        "booking no", "booking no.", "booking number",
        "speed post no", "reg no", "registered no",
        "parcel no", "parcel number", "article",
    ])
    status_col = _find_col(headers, [
        # India Post bulk report (hyphenated)
        "event-description", "event-code", "event description", "event code",
        # Standard names
        "delivery status", "status", "delivered", "shipment status",
        "current status", "delivery", "event", "current event",
        "latest status", "remarks", "delivery remarks",
        "status description", "scan event", "scan status",
    ])
    status_detection_source = "header" if status_col is not None else None
    shipping_col = _find_col(headers, [
        "shipping", "shipping charge", "shipping charges", "shipping amount",
        "postage", "postage charges", "postage amount",
        "charge", "charges", "amount", "tariff", "freight", "rate",
        "article charge", "article charges", "total charges",
    ])
    shipping_detection_source = "header" if shipping_col is not None else None
    shipping_col = _find_col(headers, [
        "shipping", "shipping charge", "shipping charges", "shipping amount",
        "postage", "postage charges", "postage amount",
        "charge", "charges", "amount", "tariff", "freight", "rate",
        "article charge", "article charges", "total charges",
    ])
    shipping_detection_source = "header" if shipping_col is not None else None

    # Fallback: detect tracking column by scanning cell values for India Post patterns
    if track_col is None:
        track_col = _detect_tracking_col_by_content(rows, len(headers))
        if track_col is not None:
            _log.warning(f"[xlsx-upload] tracking column auto-detected by content at index {track_col}")

    if status_col is None:
        status_col = _detect_status_col_by_content(rows, len(headers))
        if status_col is not None:
            status_detection_source = "content"
            _log.warning(f"[xlsx-upload] status column auto-detected by content at index {status_col}")

    if shipping_col is None:
        exclude_cols = {track_col}
        if cust_col is not None:
            exclude_cols.add(cust_col)
        if status_col is not None:
            exclude_cols.add(status_col)
        shipping_col = _detect_shipping_col_by_content(rows, len(headers), exclude_cols=exclude_cols)
        if shipping_col is not None:
            shipping_detection_source = "content"
            _log.warning(f"[xlsx-upload] shipping column auto-detected by content at index {shipping_col}")

    # Last resort: if file has exactly 2 columns with no recognisable headers,
    # assume col 0 = name, col 1 = tracking
    if track_col is None and len(headers) == 2:
        cust_col  = 0
        track_col = 1
        _log.warning("[xlsx-upload] 2-column file with unknown headers — assuming col0=name, col1=tracking")

    # Need at least a tracking column
    if track_col is None:
        _log.error(f"[xlsx-upload] FAILED — cannot find tracking column. Headers: {headers}")
        raise HTTPException(
            status_code=400,
            detail=f"Cannot find tracking/article column. Headers found: {headers}"
        )

    effective_mode = _resolve_xlsx_upload_mode(upload_mode, status_col)

    def _normalise_name(raw: str) -> str:
        """Strip titles, punctuation, extra spaces for fuzzy matching."""
        s = raw.lower().strip()
        # Remove common honorifics
        s = re.sub(r"\b(mr|mrs|ms|miss|dr|sri|smt|shri|er|prof)\.?\s*", "", s)
        # Remove trailing/leading punctuation
        s = re.sub(r"[,.\-_/\\]+", " ", s)
        return re.sub(r"\s+", " ", s).strip()

    def _name_match(order_name: str, xlsx_name: str) -> bool:
        o = _normalise_name(order_name)
        x = _normalise_name(xlsx_name)
        if not o or not x:
            return False
        # Full match
        if o == x:
            return True
        # One contains the other (handles "Mrs. Premalatha," vs "Premalatha")
        if x in o or o in x:
            return True
        # Word-level — all words in xlsx name present in order name
        x_words = set(x.split())
        o_words = set(o.split())
        if len(x_words) >= 2 and x_words.issubset(o_words):
            return True
        if len(o_words) >= 2 and o_words.issubset(x_words):
            return True
        return False

    def _normalise_phone(raw: str) -> str:
        digits = re.sub(r"\D", "", str(raw or ""))
        return digits[-10:] if len(digits) >= 10 else digits

    def _normalise_pincode(raw: str) -> str:
        digits = re.sub(r"\D", "", str(raw or ""))
        return digits[-6:] if len(digits) >= 6 else digits

    def _normalise_order_number(raw: str) -> str:
        return re.sub(r"\s+", "", str(raw or "")).upper()

    def _tariff_sku_key(raw: str) -> str:
        return re.sub(r"[^A-Z0-9]+", "", str(raw or "").strip().upper())

    # Load latest tenant tariff sheet into an in-memory SKU -> shipping cost map.
    tenant_tariffs = (
        db.query(ShippingTariff)
        .filter(ShippingTariff.tenant_id == current_user.tenant_id)
        .order_by(
            ShippingTariff.file_uploaded_at.desc(),
            ShippingTariff.updated_at.desc(),
            ShippingTariff.created_at.desc(),
        )
        .all()
    )
    tariff_by_sku: dict[str, _Dec] = {}
    for tariff in tenant_tariffs:
        sku_key = _tariff_sku_key(tariff.sku_code)
        if not sku_key:
            continue
        # Keep first (latest by uploaded/updated ordering) for each SKU.
        if sku_key in tariff_by_sku:
            continue
        try:
            tariff_by_sku[sku_key] = _Dec(str(tariff.shipping_cost or 0))
        except Exception:
            continue

    def _compute_order_shipping_from_tariff(order: Order) -> tuple[_Dec, int]:
        """Compute shipping from order item SKUs using uploaded tariff data."""
        total = _Dec("0")
        matched_items = 0
        for item in (order.items or []):
            sku_key = _tariff_sku_key(getattr(item, "sku", ""))
            if not sku_key:
                continue
            tariff_cost = tariff_by_sku.get(sku_key)
            if tariff_cost is None:
                continue
            try:
                qty = _Dec(str(getattr(item, "quantity", 1) or 1))
            except Exception:
                qty = _Dec("1")
            if qty <= 0:
                qty = _Dec("1")
            total += tariff_cost * qty
            matched_items += 1
        return total.quantize(_Dec("0.01")), matched_items

    # ── Pre-load all tenant orders (active, not delivered/cancelled for tracking;
    #    all for status updates) ───────────────────────────────────────────────
    all_orders = (
        db.query(Order)
        .options(joinedload(Order.items), joinedload(Order.customer))
        .filter(Order.tenant_id == current_user.tenant_id, Order.is_active == True)
        .order_by(Order.created_at.desc())
        .all()
    )
    # Index by existing tracking number for fast lookup
    tracking_index: dict[str, Order] = {}
    order_number_index: dict[str, Order] = {}
    phone_pin_index: dict[tuple[str, str], list[Order]] = {}
    for o in all_orders:
        order_number_index[_normalise_order_number(o.order_number)] = o
        if o.tracking_number:
            norm_track = _normalise_tracking_text(o.tracking_number)
            if norm_track:
                tracking_index[norm_track] = o
        phone_key = _normalise_phone(o.customer.phone if o.customer and o.customer.phone else o.delivery_phone2)
        pin_key = _normalise_pincode(o.delivery_pincode)
        if phone_key and pin_key:
            phone_pin_index.setdefault((phone_key, pin_key), []).append(o)

    updated = []
    skipped = []
    delivered_paid = []
    profit_sync_order_ids = set()

    for idx, row in enumerate(rows[1:], start=2):
        cust_val   = str(row[cust_col]   or "").strip() if cust_col is not None and cust_col < len(row) else ""
        order_val  = str(row[order_col]  or "").strip() if order_col is not None and order_col < len(row) else ""
        phone_val  = str(row[phone_col]  or "").strip() if phone_col is not None and phone_col < len(row) else ""
        pin_val    = str(row[pin_col]    or "").strip() if pin_col is not None and pin_col < len(row) else ""
        track_val  = str(row[track_col]  or "").strip() if track_col < len(row) else ""
        status_raw = str(row[status_col] or "").strip() if status_col is not None and status_col < len(row) else ""
        shipping_raw = row[shipping_col] if shipping_col is not None and shipping_col < len(row) else None
        shipping_from_file = _parse_money_value(shipping_raw)
        status_val = _normalise_status_text(status_raw)

        # Skip completely empty rows
        if not track_val and not cust_val:
            continue

        # Skip header-like repeat rows
        if track_val.lower() in ("article number", "tracking number", "awb", "tracking no"):
            continue

        normalised_track = _normalise_tracking_text(track_val)
        if not normalised_track:
            skipped.append({"row": idx, "customer": cust_val, "reason": "Missing tracking number"})
            continue

        # ── Find matching order ────────────────────────────────────────────
        order = None

        # Priority 1: match by existing tracking number (for status-update files)
        order = tracking_index.get(normalised_track)

        # Priority 2: match by order number if file contains it.
        if order is None and order_val:
            order = order_number_index.get(_normalise_order_number(order_val))

        # Priority 3: exact phone + pincode match.
        if order is None:
            phone_key = _normalise_phone(phone_val)
            pin_key = _normalise_pincode(pin_val)
            if phone_key and pin_key:
                candidates = phone_pin_index.get((phone_key, pin_key), [])
                untracked = [candidate for candidate in candidates if not candidate.tracking_number]
                if len(untracked) == 1:
                    order = untracked[0]
                elif len(untracked) > 1 and cust_val:
                    by_name = [candidate for candidate in untracked if _name_match(candidate.delivery_name or "", cust_val)]
                    if len(by_name) == 1:
                        order = by_name[0]
                elif len(candidates) == 1:
                    order = candidates[0]

        # Priority 4: match by customer name
        if order is None and cust_val:
            candidates = []
            for o in all_orders:
                name_on_order = (o.delivery_name or "")
                if _name_match(name_on_order, cust_val):
                    candidates.append(o)
            if candidates:
                # Prefer untracked orders first, then most recent
                untracked = [o for o in candidates if not o.tracking_number]
                order = untracked[0] if untracked else candidates[0]

        if order is None:
            reason = f"No order matched for name='{cust_val}' / tracking='{track_val}'"
            skipped.append({"row": idx, "customer": cust_val, "tracking": track_val, "reason": reason})
            continue

        is_delivered, is_returned = _classify_delivery_status(status_raw)
        delivery_status_unknown = effective_mode == "delivery" and not is_delivered and not is_returned

        # ── Always update tracking ─────────────────────────────────────────
        old_status = order.status
        order.courier_name    = "India Post"
        order.tracking_number = normalised_track
        # Update index so later rows don't double-match
        tracking_index[normalised_track] = order

        shipping_note = ""
        computed_shipping, matched_sku_items = _compute_order_shipping_from_tariff(order)
        target_shipping: _Dec | None = None

        # Priority 1: if file explicitly has shipping amount, use it row-wise.
        if shipping_from_file is not None and shipping_from_file >= 0:
            target_shipping = _Dec(str(shipping_from_file))
            if is_returned or old_status == OS.returned:
                target_shipping += _Dec("50")

        # Priority 2: derive from uploaded tariff SKUs.
        elif matched_sku_items > 0:
            target_shipping = computed_shipping
            if is_returned or old_status == OS.returned:
                target_shipping += _Dec("50")
        # Fallback: if order turns returned and shipping already exists, add RTO handling once.
        elif is_returned and old_status != OS.returned:
            existing_shipping = _Dec(str(order.shipping_charge or 0))
            if existing_shipping > 0:
                target_shipping = existing_shipping + _Dec("50")

        if target_shipping is not None:
            target_shipping = target_shipping.quantize(_Dec("0.01"))
            current_shipping = _Dec(str(order.shipping_charge or 0)).quantize(_Dec("0.01"))
            if target_shipping != current_shipping:
                order.shipping_charge = target_shipping
                if shipping_from_file is not None and shipping_from_file >= 0 and (is_returned or old_status == OS.returned):
                    shipping_note = f" + shipping ₹{order.shipping_charge} (file + ₹50 RTO)"
                elif shipping_from_file is not None and shipping_from_file >= 0:
                    shipping_note = f" + shipping ₹{order.shipping_charge} (file)"
                elif matched_sku_items > 0 and (is_returned or old_status == OS.returned):
                    shipping_note = f" + shipping ₹{order.shipping_charge} (tariff + ₹50 RTO)"
                elif matched_sku_items > 0:
                    shipping_note = f" + shipping ₹{order.shipping_charge} (tariff)"
                else:
                    shipping_note = f" + shipping ₹{order.shipping_charge} (existing + ₹50 RTO)"

        action_taken = "tracking updated"
        history_note = f"Tracking {track_val} assigned via India Post xlsx"

        # ── STATE MACHINE: Only transition forward, never downgrade ──────────
        # Final states (delivered, returned) cannot be changed.
        # Transitions allowed: pending → processing → shipped → out_for_delivery → delivered
        FINAL_STATES = {OS.delivered, OS.returned, OS.cancelled}
        is_in_final_state = old_status in FINAL_STATES

        if is_in_final_state:
            # Keep tracking update but never attempt status transition for final-state orders.
            updated.append({
                "order_number": order.order_number,
                "customer": cust_val,
                "tracking": normalised_track,
                "action": "tracking updated (status already final)" + shipping_note,
                "shipping_charge": float(order.shipping_charge or 0),
            })
            profit_sync_order_ids.add(order.id)
            continue

        if is_returned:
            order.status = OS.returned
            action_taken = "marked returned"
            history_note = f"Marked returned: tracking {track_val} assigned"

        elif is_delivered:
            order.status       = OS.delivered
            order.delivered_at = datetime.now(timezone.utc)
            action_taken = "delivered"
            history_note = f"Marked delivered: tracking {track_val} assigned"

            if order.payment_method in (PM.cod, PM.partial_cod, None) or \
               str(order.payment_method) in ('cod', 'partial_cod', 'PaymentMethod.cod'):
                order.payment_status = PS.paid
                order.amount_paid    = order.total_amount
                order.amount_due     = _Dec("0")
                action_taken += " + COD paid ✅"
                history_note += " + COD auto-paid"
                delivered_paid.append({
                    "order_number": order.order_number,
                    "customer":     order.delivery_name or "",
                    "tracking":     track_val,
                })

        elif effective_mode == "delivery" and delivery_status_unknown:
            # Delivery file may include in-transit/non-final events.
            # Keep tracking refreshed but do not force a final status.
            action_taken = "tracking updated (status unchanged: non-final delivery event)"
            history_note = f"Tracking {normalised_track} updated; status unchanged for event '{status_raw or 'blank'}'"

        elif effective_mode != "delivery" and not status_val:
            # Tracking-only file: auto-advance to shipped if not already further along
            if order.status not in [OS.shipped, OS.out_for_delivery, OS.delivered, OS.returned]:
                order.status = OS.shipped
                action_taken = "tracking updated -> shipped"
                history_note = f"Auto-transitioned to shipped: tracking {normalised_track} assigned"

        # ── Auto-transition to shipped if tracking assigned but no explicit status ──
        # This handles cases where Excel has tracking but status column is missing or empty
        if effective_mode != "delivery" and order.status == old_status and not is_delivered and not is_returned:
            # Status hasn't changed yet, but tracking was just assigned
            if order.status not in [OS.shipped, OS.out_for_delivery, OS.delivered, OS.returned]:
                order.status = OS.shipped
                action_taken = "tracking updated -> shipped"
                history_note = f"Auto-transitioned to shipped: tracking {normalised_track} assigned"

        if shipping_note:
            action_taken += shipping_note
            history_note += f"; shipping charge set to ₹{order.shipping_charge}"

        # ── Create status history entry if status changed ──────────────────
        if order.status != old_status or old_status is None:
            history = OrderStatusHistory(
                tenant_id=current_user.tenant_id,
                order_id=order.id,
                employee_id=current_user.id,
                old_status=old_status,
                new_status=order.status,
                note=history_note,
            )
            db.add(history)

        # ── Log activity ──────────────────────────────────────────────────
        log_activity(
            db=db,
            tenant_id=str(current_user.tenant_id),
            actor=current_user,
            module=LogModule.ORDERS,
            action="order.xlsx_update",
            level=LogLevel.INFO,
            message=f"India Post XLSX: {action_taken} (Order {order.order_number})",
            detail={"order_id": str(order.id), "tracking": normalised_track, "action": action_taken},
        )

        updated.append({
            "order_number": order.order_number,
            "customer":     order.delivery_name or "",
            "tracking":     normalised_track,
            "action":       action_taken,
            "shipping_charge": float(order.shipping_charge or 0),
        })
        profit_sync_order_ids.add(order.id)

    profit_postings_refreshed = 0
    if profit_sync_order_ids:
        try:
            from app.modules.profit_engine.service import upsert_order_profit_posting
            for oid in profit_sync_order_ids:
                if upsert_order_profit_posting(db, current_user.tenant_id, oid) is not None:
                    profit_postings_refreshed += 1
        except Exception:
            # Best-effort only; order flow should not fail if profit posting sync has an issue.
            pass

    db.commit()

    return {
        "success":            True,
        "upload_mode":        effective_mode,
        "status_detection_source": status_detection_source,
        "detected_status_column": headers[status_col] if status_col is not None else None,
        "shipping_detection_source": shipping_detection_source,
        "detected_shipping_column": headers[shipping_col] if shipping_col is not None else None,
        "updated_count":      len(updated),
        "skipped_count":      len(skipped),
        "delivered_and_paid": len(delivered_paid),
        "profit_postings_refreshed": profit_postings_refreshed,
        "updated":            updated,
        "skipped":            skipped,
        "delivered_paid_details": delivered_paid,
    }


@router.post("/api/shipments/manual-orders/india-post-xlsx-preview")
async def preview_manual_orders_india_post_xlsx(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin, RoleEnum.operations)),
):
    """
    Preview what an India Post xlsx file would match — WITHOUT making changes.
    Returns matched / unmatched rows so you can verify before committing.
    """
    import openpyxl, io, re

    form = await request.form()
    xlsx_file = form.get("file")
    if not xlsx_file:
        raise HTTPException(status_code=400, detail="No 'file' field in form data")
    upload_mode = str(form.get("upload_mode") or "").strip().lower()

    content = await xlsx_file.read()
    try:
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        ws = wb.active
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot parse xlsx: {e}")

    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        raise HTTPException(status_code=400, detail="xlsx has no data rows")

    headers = [str(h or "").strip().lower() for h in rows[0]]

    cust_col  = _find_col(headers, [
        # India Post bulk report (hyphenated)
        "receiver-name", "sender-name", "receiver name", "sender name",
        # Standard names
        "customer name", "customer", "name", "customer_name",
        "recipient", "addressee", "consignee", "addressee name",
        "to name", "beneficiary", "party name",
    ])
    order_col = _find_col(headers, [
        "order number", "order no", "order no.", "order_number",
        "reference", "reference number", "ref no", "booking reference",
        "invoice number", "invoice no",
    ])
    phone_col = _find_col(headers, [
        "receiver-mobile", "receiver mobile", "receiver mobile number", "receiver phone",
        "mobile", "mobile number", "phone", "phone number", "contact number",
        "consignee mobile", "consignee phone", "addressee mobile", "addressee phone",
        "to mobile", "to phone",
    ])
    pin_col = _find_col(headers, [
        "receiver-pincode", "receiver pincode", "delivery pincode", "delivery_pincode",
        "destination pincode", "destination_pincode", "pincode", "pin code", "pin",
        "consignee pincode", "addressee pincode", "to pincode",
    ])
    track_col = _find_col(headers, [
        # India Post bulk report (hyphenated)
        "article-number", "article-no",
        # Standard names
        "article number", "article no", "article no.", "article_number",
        "tracking number", "tracking no", "tracking no.", "tracking_number",
        "awb", "awb number", "awb no", "barcode",
        "consignment no", "consignment no.", "consignment number",
        "tracking id", "shipment no", "shipment number",
        "booking no", "booking no.", "booking number",
        "speed post no", "reg no", "registered no",
        "parcel no", "parcel number", "article",
    ])
    status_col = _find_col(headers, [
        # India Post bulk report (hyphenated)
        "event-description", "event-code", "event description", "event code",
        # Standard names
        "delivery status", "status", "delivered", "shipment status",
        "current status", "delivery", "event", "current event",
        "latest status", "remarks", "delivery remarks",
        "status description", "scan event", "scan status",
    ])
    status_detection_source = "header" if status_col is not None else None
    shipping_col = _find_col(headers, [
        "shipping", "shipping charge", "shipping charges", "shipping amount",
        "postage", "postage charges", "postage amount",
        "charge", "charges", "amount", "tariff", "freight", "rate",
        "article charge", "article charges", "total charges",
    ])
    shipping_detection_source = "header" if shipping_col is not None else None

    # Fallback: detect tracking column by India Post article number patterns
    if track_col is None:
        track_col = _detect_tracking_col_by_content(rows, len(headers))
    if track_col is None and len(headers) == 2:
        cust_col = 0
        track_col = 1

    if status_col is None:
        status_col = _detect_status_col_by_content(rows, len(headers))
        if status_col is not None:
            status_detection_source = "content"

    if shipping_col is None:
        exclude_cols = {track_col}
        if cust_col is not None:
            exclude_cols.add(cust_col)
        if status_col is not None:
            exclude_cols.add(status_col)
        shipping_col = _detect_shipping_col_by_content(rows, len(headers), exclude_cols=exclude_cols)
        if shipping_col is not None:
            shipping_detection_source = "content"

    if track_col is None:
        return {
            "error": f"No tracking column found. Headers: {headers}",
            "headers": headers,
            "rows_preview": [[str(c or "") for c in r] for r in rows[:5]],
        }

    effective_mode = _resolve_xlsx_upload_mode(upload_mode, status_col)

    def _normalise_name(raw: str) -> str:
        s = raw.lower().strip()
        s = re.sub(r"\b(mr|mrs|ms|miss|dr|sri|smt|shri|er|prof)\.?\s*", "", s)
        s = re.sub(r"[,.\-_/\\]+", " ", s)
        return re.sub(r"\s+", " ", s).strip()

    def _name_match(order_name, xlsx_name):
        o = _normalise_name(order_name)
        x = _normalise_name(xlsx_name)
        if not o or not x:
            return False
        if o == x or x in o or o in x:
            return True
        x_words = set(x.split())
        o_words = set(o.split())
        if len(x_words) >= 2 and x_words.issubset(o_words):
            return True
        if len(o_words) >= 2 and o_words.issubset(x_words):
            return True
        return False

    def _normalise_phone(raw: str) -> str:
        digits = re.sub(r"\D", "", str(raw or ""))
        return digits[-10:] if len(digits) >= 10 else digits

    def _normalise_pincode(raw: str) -> str:
        digits = re.sub(r"\D", "", str(raw or ""))
        return digits[-6:] if len(digits) >= 6 else digits

    def _normalise_order_number(raw: str) -> str:
        return re.sub(r"\s+", "", str(raw or "")).upper()

    all_orders = (
        db.query(Order)
        .options(joinedload(Order.customer))
        .filter(Order.tenant_id == current_user.tenant_id, Order.is_active == True)
        .order_by(Order.created_at.desc())
        .all()
    )
    tracking_index = {
        _normalise_tracking_text(o.tracking_number): o
        for o in all_orders
        if o.tracking_number and _normalise_tracking_text(o.tracking_number)
    }
    order_number_index = {
        _normalise_order_number(o.order_number): o
        for o in all_orders
        if o.order_number
    }
    phone_pin_index: dict[tuple[str, str], list[Order]] = {}
    for order in all_orders:
        phone_key = _normalise_phone(order.customer.phone if order.customer and order.customer.phone else order.delivery_phone2)
        pin_key = _normalise_pincode(order.delivery_pincode)
        if phone_key and pin_key:
            phone_pin_index.setdefault((phone_key, pin_key), []).append(order)

    results = []
    for idx, row in enumerate(rows[1:], start=2):
        cust_val  = str(row[cust_col]  or "").strip() if cust_col is not None and cust_col < len(row) else ""
        order_val = str(row[order_col] or "").strip() if order_col is not None and order_col < len(row) else ""
        phone_val = str(row[phone_col] or "").strip() if phone_col is not None and phone_col < len(row) else ""
        pin_val   = str(row[pin_col]   or "").strip() if pin_col is not None and pin_col < len(row) else ""
        track_val = str(row[track_col] or "").strip() if track_col < len(row) else ""
        status_val = str(row[status_col] or "").strip() if status_col is not None and status_col < len(row) else ""
        shipping_raw = row[shipping_col] if shipping_col is not None and shipping_col < len(row) else None
        shipping_val = _parse_money_value(shipping_raw)
        is_delivered, is_returned = _classify_delivery_status(status_val)

        if not track_val and not cust_val:
            continue
        if track_val.lower() in ("article number", "tracking number", "awb", "tracking no"):
            continue

        norm_track = _normalise_tracking_text(track_val)
        order = tracking_index.get(norm_track)
        match_method = "tracking"
        if order is None and order_val:
            order = order_number_index.get(_normalise_order_number(order_val))
            match_method = "order_number" if order else match_method
        if order is None:
            phone_key = _normalise_phone(phone_val)
            pin_key = _normalise_pincode(pin_val)
            if phone_key and pin_key:
                candidates = phone_pin_index.get((phone_key, pin_key), [])
                untracked = [candidate for candidate in candidates if not candidate.tracking_number]
                if len(untracked) == 1:
                    order = untracked[0]
                elif len(untracked) > 1 and cust_val:
                    by_name = [candidate for candidate in untracked if _name_match(candidate.delivery_name or "", cust_val)]
                    if len(by_name) == 1:
                        order = by_name[0]
                elif len(candidates) == 1:
                    order = candidates[0]
                if order is not None:
                    match_method = "phone_pincode"
        if order is None and cust_val:
            match_method = "name"
            for o in all_orders:
                if _name_match(o.delivery_name or "", cust_val):
                    order = o
                    break

        results.append({
            "row":          idx,
            "xlsx_name":    cust_val,
            "xlsx_order":   order_val,
            "xlsx_phone":   phone_val,
            "xlsx_pincode": pin_val,
            "tracking":     track_val,
            "status_in_xlsx": status_val,
            "status_detected": is_delivered or is_returned,
            "status_kind": "returned" if is_returned else ("delivered" if is_delivered else None),
            "shipping_in_xlsx": shipping_val,
            "matched":      order is not None,
            "match_method": match_method if order else "none",
            "order_number": order.order_number if order else None,
            "order_name":   order.delivery_name if order else None,
            "order_status": order.status.value if order else None,
            "current_tracking": order.tracking_number if order else None,
        })

    matched   = [r for r in results if r["matched"]]
    unmatched = [r for r in results if not r["matched"]]
    warnings = []
    if effective_mode == "delivery" and status_col is None:
        warnings.append("Delivery upload selected but no status column could be detected.")
    elif effective_mode == "delivery" and any(not row["status_detected"] for row in matched):
        warnings.append("Some matched rows do not contain a recognizable delivered/returned status.")

    return {
        "total_rows":    len(results),
        "upload_mode":   effective_mode,
        "status_detection_source": status_detection_source,
        "shipping_detection_source": shipping_detection_source,
        "matched_count": len(matched),
        "unmatched_count": len(unmatched),
        "warnings": warnings,
        "headers_found": {
            "name_col":    headers[cust_col]  if cust_col  is not None else None,
            "order_col":   headers[order_col] if order_col is not None else None,
            "phone_col":   headers[phone_col] if phone_col is not None else None,
            "pin_col":     headers[pin_col] if pin_col is not None else None,
            "track_col":   headers[track_col] if track_col is not None else None,
            "status_col":  headers[status_col] if status_col is not None else None,
            "shipping_col": headers[shipping_col] if shipping_col is not None else None,
        },
        "matched":   matched,
        "unmatched": unmatched,
    }
