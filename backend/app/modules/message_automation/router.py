from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.auth.tenant import get_current_tenant_user, require_roles
from app.database.session import get_db
from app.models.employee import RoleEnum
from app.modules.message_automation import schemas, service

router = APIRouter(prefix="/api/message-automation", tags=["Message Automation"])


@router.get("/templates", response_model=list[schemas.TemplateResponse])
def list_templates(current_user=Depends(get_current_tenant_user)):
    return service.templates_for_meta_manager()


@router.get("/meta-template-payloads", response_model=list[schemas.MetaTemplatePayloadResponse])
def list_meta_template_payloads(current_user=Depends(require_roles(RoleEnum.admin))):
    return service.meta_template_payloads()


@router.get("/settings", response_model=schemas.MessageAutomationSettingsResponse)
def get_settings(
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    settings_row = service.get_or_create_settings(db, current_user.tenant_id)
    return service.settings_to_dict(settings_row, db)


@router.put("/settings", response_model=schemas.MessageAutomationSettingsResponse)
def update_settings(
    data: schemas.MessageAutomationSettingsUpdate,
    current_user=Depends(require_roles(RoleEnum.admin)),
    db: Session = Depends(get_db),
):
    settings_row = service.update_settings(db, current_user.tenant_id, data.model_dump(exclude_none=True))
    db.commit()
    db.refresh(settings_row)
    return service.settings_to_dict(settings_row, db)


@router.get("/available-whatsapp-templates", response_model=list[schemas.AvailableWhatsAppTemplateResponse])
async def list_available_whatsapp_templates(
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    return await service.available_whatsapp_templates(db, current_user.tenant_id)


@router.post("/send-monthly-promo-backfill", response_model=schemas.GenericAutomationResponse)
async def send_monthly_promo_backfill(
    cutoff_date: date = Query(date(2026, 4, 15)),
    limit: int = Query(2000, ge=1, le=5000),
    current_user=Depends(require_roles(RoleEnum.admin)),
    db: Session = Depends(get_db),
):
    result = await service.send_monthly_promo_backfill(
        db,
        current_user.tenant_id,
        cutoff_date=cutoff_date,
        limit=limit,
    )
    return schemas.GenericAutomationResponse(success=result.get("success", False), details=result)


@router.get("/order-whatsapp-logs", response_model=list[schemas.OrderWhatsAppLogResponse])
def list_order_whatsapp_logs(
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(200, ge=1, le=500),
    event_type: Optional[str] = Query(None),
    template_key: Optional[str] = Query(None),
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    return service.list_order_whatsapp_logs(
        db,
        current_user.tenant_id,
        days=days,
        limit=limit,
        event_type=event_type,
        template_key=template_key,
    )


@router.get("/tasks", response_model=list[schemas.MessageTaskResponse])
def list_tasks(
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    current_user=Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    tasks = service.list_tasks(db, current_user.tenant_id, status=status, limit=limit)
    return [service.task_to_dict(task) for task in tasks]


@router.post("/process-due", response_model=schemas.GenericAutomationResponse)
async def process_due(
    data: schemas.ProcessDueRequest,
    current_user=Depends(require_roles(RoleEnum.admin)),
    db: Session = Depends(get_db),
):
    result = await service.process_due_tasks(db, limit=data.limit)
    return schemas.GenericAutomationResponse(success=result.get("success", False), details=result)


@router.post("/release-tasks", response_model=schemas.GenericAutomationResponse)
def release_tasks(
    data: schemas.ReleaseTasksRequest,
    current_user=Depends(require_roles(RoleEnum.admin)),
    db: Session = Depends(get_db),
):
    result = service.release_tasks(
        db,
        current_user.tenant_id,
        template_keys=data.template_keys,
        statuses=data.statuses,
        release_pending_only=data.release_pending_only,
    )
    db.commit()
    return schemas.GenericAutomationResponse(success=result.get("success", False), details=result)


@router.post("/orders/{order_id}/retry-whatsapp-task-now", response_model=schemas.GenericAutomationResponse)
async def retry_order_whatsapp_task_now(
    order_id: str,
    data: schemas.RetryOrderWhatsAppTaskRequest,
    current_user=Depends(require_roles(RoleEnum.admin, RoleEnum.sales, RoleEnum.operations)),
    db: Session = Depends(get_db),
):
    try:
        result = await service.retry_order_whatsapp_task_now(
            db,
            current_user.tenant_id,
            order_id=order_id,
            template_key=data.template_key,
        )
        db.commit()
        return schemas.GenericAutomationResponse(success=result.get("success", False), details=result)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/order-whatsapp-logs/retry-pending-now", response_model=schemas.GenericAutomationResponse)
async def retry_pending_order_whatsapp_tasks_now(
    data: schemas.RetryPendingOrderWhatsAppTasksRequest,
    current_user=Depends(require_roles(RoleEnum.admin, RoleEnum.sales, RoleEnum.operations)),
    db: Session = Depends(get_db),
):
    result = await service.retry_pending_order_whatsapp_tasks_now(
        db,
        current_user.tenant_id,
        days=data.days,
        limit=data.limit,
        template_keys=data.template_keys,
        task_ids=data.task_ids,
    )
    db.commit()
    return schemas.GenericAutomationResponse(success=result.get("success", False), details=result)


@router.post("/historical-review-requests/preview", response_model=schemas.GenericAutomationResponse)
def preview_historical_review_request_batch(
    data: schemas.HistoricalReviewRequestBatchRequest,
    current_user=Depends(require_roles(RoleEnum.admin)),
    db: Session = Depends(get_db),
):
    try:
        result = service.preview_historical_review_request_batch(
            db,
            current_user.tenant_id,
            older_than_days=data.older_than_days,
            batch_limit=data.batch_limit,
            resume_cursor=data.resume_cursor,
        )
        return schemas.GenericAutomationResponse(success=result.get("success", False), details=result)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/historical-review-requests/retry-now", response_model=schemas.GenericAutomationResponse)
async def retry_historical_review_request_batch_now(
    data: schemas.HistoricalReviewRequestBatchRequest,
    current_user=Depends(require_roles(RoleEnum.admin)),
    db: Session = Depends(get_db),
):
    try:
        result = await service.retry_historical_review_request_batch_now(
            db,
            current_user.tenant_id,
            older_than_days=data.older_than_days,
            batch_limit=data.batch_limit,
            resume_cursor=data.resume_cursor,
            confirmation_phrase=data.confirmation_phrase,
        )
        db.commit()
        return schemas.GenericAutomationResponse(success=result.get("success", False), details=result)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/bootstrap-existing-customers", response_model=schemas.GenericAutomationResponse)
async def bootstrap_existing_customers(
    data: schemas.BootstrapExistingCustomersRequest,
    current_user=Depends(require_roles(RoleEnum.admin)),
    db: Session = Depends(get_db),
):
    result = service.queue_existing_customer_review_campaign(
        db,
        current_user.tenant_id,
        include_phones=data.include_phones,
    )
    db.commit()
    if data.process_now:
        send_result = await service.process_due_tasks(db, limit=data.process_limit)
        result["process_due"] = send_result
    return schemas.GenericAutomationResponse(success=True, details=result)


@router.post("/preferences/cancel", response_model=schemas.GenericAutomationResponse)
def cancel_customer_messages(
    data: schemas.CustomerMessageCancelRequest,
    current_user=Depends(require_roles(RoleEnum.admin, RoleEnum.sales, RoleEnum.operations)),
    db: Session = Depends(get_db),
):
    try:
        result = service.cancel_customer_messages(
            db,
            current_user.tenant_id,
            customer_id=data.customer_id,
            phone=data.phone,
            whatsapp=data.whatsapp,
            email=data.email,
            reason=data.reason,
        )
        db.commit()
        return schemas.GenericAutomationResponse(success=True, details=result)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/preferences/resume", response_model=schemas.GenericAutomationResponse)
def resume_customer_messages(
    data: schemas.CustomerMessageResumeRequest,
    current_user=Depends(require_roles(RoleEnum.admin, RoleEnum.sales, RoleEnum.operations)),
    db: Session = Depends(get_db),
):
    try:
        result = service.resume_customer_messages(
            db,
            current_user.tenant_id,
            customer_id=data.customer_id,
            phone=data.phone,
        )
        db.commit()
        return schemas.GenericAutomationResponse(success=True, details=result)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
