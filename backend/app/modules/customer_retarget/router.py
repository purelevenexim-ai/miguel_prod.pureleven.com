from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth.tenant import require_roles
from app.database.session import get_db
from app.models.employee import Employee, RoleEnum
from app.modules.customer_retarget import service
from app.modules.customer_retarget.schemas import (
    RetargetCallCreate,
    RetargetManualCustomerCreate,
    RetargetTemplateBulkSend,
    UnlinkedResolveRequest,
)


router = APIRouter(prefix="/api/customer-retarget", tags=["Customer Retarget"])

retarget_roles = require_roles(
    RoleEnum.admin,
    RoleEnum.sales,
    RoleEnum.marketing,
)


@router.get("/queue")
def get_queue(
    view: str = Query("to_contact"),
    search: Optional[str] = Query(None, max_length=120),
    repeat_only: bool = Query(False),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(retarget_roles),
):
    return service.get_queue(
        db,
        current_user,
        view=view,
        search=search,
        repeat_only=repeat_only,
        page=page,
        limit=limit,
    )


@router.get("/selection")
def get_queue_selection(
    view: str = Query("to_contact"),
    search: Optional[str] = Query(None, max_length=120),
    repeat_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(retarget_roles),
):
    return service.get_queue_selection(
        db,
        current_user,
        view=view,
        search=search,
        repeat_only=repeat_only,
    )


@router.post("/manual-customers", status_code=201)
def add_manual_retarget_customer(
    data: RetargetManualCustomerCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(retarget_roles),
):
    return service.add_manual_retarget_customer(db, current_user, data)


@router.post("/unlinked/{shopify_order_id}/resolve")
def resolve_unlinked_buyer(
    shopify_order_id: UUID,
    data: UnlinkedResolveRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(retarget_roles),
):
    return service.resolve_unlinked_buyer(
        db,
        current_user,
        shopify_order_id,
        data,
    )


@router.post("/whatsapp/send-template", status_code=202)
async def send_retarget_template(
    data: RetargetTemplateBulkSend,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(retarget_roles),
):
    return await service.queue_retarget_template(
        db,
        current_user,
        data,
    )


@router.get("/whatsapp/campaigns")
def list_retarget_campaigns(
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=200),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(retarget_roles),
):
    return service.list_retarget_campaigns(
        db,
        current_user,
        page=page,
        limit=limit,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/whatsapp/campaigns/{batch_id}")
def get_retarget_campaign_detail(
    batch_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(retarget_roles),
):
    return service.get_retarget_campaign_detail(db, current_user, batch_id, page=page, limit=limit)


@router.get("/{customer_id}")
def get_customer_workspace(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(retarget_roles),
):
    return service.get_customer_workspace(db, current_user, customer_id)


@router.post("/{customer_id}/calls", status_code=201)
def log_customer_call(
    customer_id: UUID,
    data: RetargetCallCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(retarget_roles),
):
    return service.log_customer_call(
        db,
        current_user,
        customer_id,
        data,
    )
