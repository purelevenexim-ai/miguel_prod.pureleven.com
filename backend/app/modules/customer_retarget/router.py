from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.core.auth.tenant import require_roles
from app.database.session import get_db
from app.models.employee import Employee, RoleEnum
from app.modules.customer_retarget import service
from app.modules.customer_retarget.schemas import (
    RetargetCallCreate,
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
