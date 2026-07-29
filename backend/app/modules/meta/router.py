"""
Meta Ads — Router
------------------
GET  /api/meta/webhook                   Meta hub challenge verification (no auth)
POST /api/meta/webhook                   Receive Meta lead webhook (no auth — verified by token)
POST /api/meta/integrations              Register a new Meta page (admin only)
GET  /api/meta/integrations              List registered pages (admin only)
PATCH /api/meta/integrations/{id}        Update integration (admin only)
DELETE /api/meta/integrations/{id}       Remove integration (admin only)
GET  /api/meta/webhook-logs              View recent webhook events (admin only)
"""

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.core.auth.tenant import get_current_tenant_user, require_roles
from app.models.employee import Employee, RoleEnum
from app.modules.meta.schemas import (
    MetaIntegrationCreate,
    MetaIntegrationUpdate,
    MetaIntegrationResponse,
    WebhookLogResponse,
)
from app.modules.meta import service

router = APIRouter(prefix="/api/meta", tags=["Meta Ads"])


# ─────────────────────────────────────────────────────────────
# Webhook (public — authenticated by verify token / Meta signature)
# ─────────────────────────────────────────────────────────────

@router.get("/webhook", response_class=PlainTextResponse)
def webhook_verify(
    hub_mode:         str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge:    str = Query(..., alias="hub.challenge"),
):
    """
    Meta sends a GET request to verify the webhook endpoint.
    Responds with the hub.challenge string if the verify token matches.
    """
    return service.verify_webhook(hub_mode, hub_verify_token, hub_challenge)


@router.post("/webhook", status_code=200)
async def webhook_receive(request: Request, db: Session = Depends(get_db)):
    """
    Receive Meta Lead Gen webhook events.
    Parses the payload, matches to a tenant by page_id, creates Lead records.
    Always returns 200 — Meta will retry on non-200.
    """
    try:
        payload = await request.json()
    except Exception:
        # Return 200 even on bad payload to prevent Meta retry loops
        return {"status": "ignored", "reason": "invalid JSON"}

    results = service.ingest_webhook(db, payload)
    return {"status": "ok", **results}


# ─────────────────────────────────────────────────────────────
# Integration Management (admin only)
# ─────────────────────────────────────────────────────────────

@router.post("/integrations", response_model=MetaIntegrationResponse, status_code=201)
def create_integration(
    data: MetaIntegrationCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin)),
):
    """Register a Meta page with this tenant. Admin only."""
    return service.create_integration(db, data, current_user)


@router.get("/integrations", response_model=list[MetaIntegrationResponse])
def list_integrations(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin)),
):
    """List all Meta page integrations for this tenant."""
    return [
        MetaIntegrationResponse.model_validate(obj)
        for obj in service.list_integrations(db, current_user)
    ]


@router.get("/integrations/{integration_id}", response_model=MetaIntegrationResponse)
def get_integration(
    integration_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin)),
):
    """Get a single Meta integration by ID."""
    return MetaIntegrationResponse.model_validate(
        service.get_integration(db, integration_id, current_user)
    )


@router.patch("/integrations/{integration_id}", response_model=MetaIntegrationResponse)
def update_integration(
    integration_id: UUID,
    data: MetaIntegrationUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin)),
):
    """Update access token, assignee, active status etc."""
    return MetaIntegrationResponse.model_validate(
        service.update_integration(db, integration_id, data, current_user)
    )


@router.delete("/integrations/{integration_id}", status_code=204)
def delete_integration(
    integration_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin)),
):
    """Remove a Meta page integration."""
    service.delete_integration(db, integration_id, current_user)


# ─────────────────────────────────────────────────────────────
# Webhook Logs (admin only)
# ─────────────────────────────────────────────────────────────

@router.get("/webhook-logs", response_model=dict)
def webhook_logs(
    page:      int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin)),
):
    """View recent Meta webhook events for this tenant's pages."""
    result = service.list_webhook_logs(db, current_user, page, page_size)
    result["data"] = [WebhookLogResponse.model_validate(l) for l in result["data"]]
    return result
