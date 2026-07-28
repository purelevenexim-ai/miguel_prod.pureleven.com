"""
Meta Ads — Service
-------------------
Business logic for:
  1. MetaIntegration CRUD (tenant admin registers/manages pages)
  2. Webhook verification (Meta hub challenge)
  3. Webhook ingestion (parse incoming lead → create Lead record)
"""

from __future__ import annotations

import json
import os
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.meta import MetaIntegration, MetaWebhookLog
from app.models.lead import Lead, LeadSource, LeadPipelineStatus, LeadPriority, LeadActivity, LeadActivityType
from app.models.employee import Employee
from app.core.tenant_utils import apply_tenant_filter, assert_tenant_ownership
from app.modules.meta.schemas import MetaIntegrationCreate, MetaIntegrationUpdate

# Meta webhook verify token — set via env var META_VERIFY_TOKEN
# Default is fine for dev; set it in docker-compose or .env for production
META_VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "miguel_crm_meta_verify_2026")


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _next_lead_number(db: Session, tenant_id) -> str:
    count = (
        db.query(func.count(Lead.id))
        .filter(Lead.tenant_id == tenant_id)
        .scalar()
    ) or 0
    return f"LEAD-{str(count + 1).zfill(5)}"


def _extract_field(field_data: list[dict], field_name: str) -> str:
    """Pull a value from Meta's field_data list by name."""
    for field in field_data:
        if field.get("name") == field_name:
            vals = field.get("values", [])
            return vals[0] if vals else ""
    return ""


# ─────────────────────────────────────────────────────────────
# Integration CRUD
# ─────────────────────────────────────────────────────────────

def create_integration(
    db: Session,
    data: MetaIntegrationCreate,
    current_user: Employee,
) -> MetaIntegration:
    # Prevent duplicate page_id per tenant
    existing = (
        db.query(MetaIntegration)
        .filter(
            MetaIntegration.tenant_id == current_user.tenant_id,
            MetaIntegration.page_id == data.page_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Page ID '{data.page_id}' is already registered for this tenant.",
        )

    # Validate default_assignee belongs to this tenant
    if data.default_assignee_id:
        emp = db.query(Employee).filter(
            Employee.id == data.default_assignee_id,
            Employee.tenant_id == current_user.tenant_id,
            Employee.is_active == True,
        ).first()
        if not emp:
            raise HTTPException(
                status_code=404,
                detail="default_assignee_id not found in this tenant.",
            )

    integration = MetaIntegration(
        tenant_id=current_user.tenant_id,
        page_id=data.page_id,
        page_name=data.page_name,
        form_id=data.form_id,
        access_token=data.access_token,
        default_assignee_id=data.default_assignee_id,
        is_active=data.is_active,
    )
    db.add(integration)
    db.commit()
    db.refresh(integration)
    return integration


def list_integrations(db: Session, current_user: Employee) -> list[MetaIntegration]:
    query = db.query(MetaIntegration)
    query = apply_tenant_filter(query, MetaIntegration, current_user)
    return query.order_by(MetaIntegration.created_at.desc()).all()


def get_integration(db: Session, integration_id: UUID, current_user: Employee) -> MetaIntegration:
    obj = db.query(MetaIntegration).filter(MetaIntegration.id == integration_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Integration not found")
    assert_tenant_ownership(obj, current_user)
    return obj


def update_integration(
    db: Session,
    integration_id: UUID,
    data: MetaIntegrationUpdate,
    current_user: Employee,
) -> MetaIntegration:
    obj = get_integration(db, integration_id, current_user)

    if data.page_name is not None:
        obj.page_name = data.page_name
    if data.form_id is not None:
        obj.form_id = data.form_id
    if data.access_token is not None:
        obj.access_token = data.access_token
    if data.is_active is not None:
        obj.is_active = data.is_active
    if data.default_assignee_id is not None:
        emp = db.query(Employee).filter(
            Employee.id == data.default_assignee_id,
            Employee.tenant_id == current_user.tenant_id,
            Employee.is_active == True,
        ).first()
        if not emp:
            raise HTTPException(status_code=404, detail="default_assignee_id not found in this tenant.")
        obj.default_assignee_id = data.default_assignee_id

    db.commit()
    db.refresh(obj)
    return obj


def delete_integration(db: Session, integration_id: UUID, current_user: Employee) -> None:
    obj = get_integration(db, integration_id, current_user)
    db.delete(obj)
    db.commit()


# ─────────────────────────────────────────────────────────────
# Webhook Logs
# ─────────────────────────────────────────────────────────────

def list_webhook_logs(
    db: Session,
    current_user: Employee,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """
    Return webhook logs for the current tenant (matched by page_id).
    """
    # Get all page_ids registered by this tenant
    page_ids = [
        row.page_id
        for row in db.query(MetaIntegration.page_id)
        .filter(MetaIntegration.tenant_id == current_user.tenant_id)
        .all()
    ]
    query = db.query(MetaWebhookLog).filter(
        MetaWebhookLog.page_id.in_(page_ids)
    ).order_by(MetaWebhookLog.received_at.desc())

    total = query.count()
    logs = query.offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size, "data": logs}


# ─────────────────────────────────────────────────────────────
# Webhook Verification
# ─────────────────────────────────────────────────────────────

def verify_webhook(mode: str, token: str, challenge: str) -> str:
    """
    Handle Meta's hub.challenge verification handshake.
    Returns the challenge string on success, raises 403 on failure.
    """
    if mode != "subscribe":
        raise HTTPException(status_code=400, detail="Unexpected hub.mode")
    if token != META_VERIFY_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid verify token")
    return challenge


# ─────────────────────────────────────────────────────────────
# Webhook Ingestion
# ─────────────────────────────────────────────────────────────

def ingest_webhook(db: Session, payload: dict) -> dict:
    """
    Process a Meta webhook POST payload.
    For each leadgen change, find the matching tenant integration and
    create a Lead record. Logs every event regardless of outcome.
    """
    results = {"processed": 0, "skipped": 0, "errors": 0}

    entries = payload.get("entry", [])
    for entry in entries:
        page_id = str(entry.get("id", ""))
        changes = entry.get("changes", [])

        for change in changes:
            if change.get("field") != "leadgen":
                continue

            value = change.get("value", {})
            leadgen_id = str(value.get("leadgen_id", ""))
            form_id    = str(value.get("form_id", ""))

            # Log raw event immediately
            log = MetaWebhookLog(
                page_id=page_id,
                leadgen_id=leadgen_id,
                form_id=form_id,
                raw_payload=json.dumps(value),
                processed=False,
            )
            db.add(log)
            db.flush()

            # Dedup: skip if we already processed this leadgen_id
            existing_log = (
                db.query(MetaWebhookLog)
                .filter(
                    MetaWebhookLog.leadgen_id == leadgen_id,
                    MetaWebhookLog.processed == True,
                )
                .first()
            )
            if existing_log:
                log.error = "duplicate leadgen_id — already processed"
                results["skipped"] += 1
                continue

            # Find matching tenant integration by page_id
            integration = (
                db.query(MetaIntegration)
                .filter(
                    MetaIntegration.page_id == page_id,
                    MetaIntegration.is_active == True,
                )
                .first()
            )
            if not integration:
                log.error = f"No active integration found for page_id={page_id}"
                results["skipped"] += 1
                continue

            # If the integration has a form_id filter, check it
            if integration.form_id and integration.form_id != form_id:
                log.error = f"form_id {form_id} does not match integration filter {integration.form_id}"
                results["skipped"] += 1
                continue

            # Parse field_data
            field_data = value.get("field_data", [])
            name  = (
                _extract_field(field_data, "full_name")
                or _extract_field(field_data, "first_name")
                or "Unknown"
            )
            last  = _extract_field(field_data, "last_name")
            if last:
                name = f"{name} {last}".strip()

            phone  = _extract_field(field_data, "phone_number") or _extract_field(field_data, "phone")
            email  = _extract_field(field_data, "email")
            city   = _extract_field(field_data, "city")
            state  = _extract_field(field_data, "state")
            notes_raw = _extract_field(field_data, "message") or _extract_field(field_data, "notes")

            if not phone:
                log.error = "No phone number in lead form data"
                results["errors"] += 1
                continue

            # Create Lead
            try:
                lead_number = _next_lead_number(db, integration.tenant_id)
                lead = Lead(
                    tenant_id=integration.tenant_id,
                    lead_number=lead_number,
                    name=name,
                    phone=phone,
                    email=email or None,
                    city=city or None,
                    state=state or None,
                    source=LeadSource.meta,
                    priority=LeadPriority.medium,
                    status=LeadPipelineStatus.new_lead,
                    assigned_to_id=integration.default_assignee_id,
                    created_by_id=integration.default_assignee_id,  # system-created
                    notes=notes_raw or f"Meta Lead Gen — form_id: {form_id}, leadgen_id: {leadgen_id}",
                )
                db.add(lead)
                db.flush()

                # Log activity
                activity = LeadActivity(
                    tenant_id=integration.tenant_id,
                    lead_id=lead.id,
                    employee_id=integration.default_assignee_id,
                    activity_type=LeadActivityType.note,
                    note=f"Lead auto-created from Meta Lead Gen ad. leadgen_id={leadgen_id}",
                    new_status=LeadPipelineStatus.new_lead,
                )
                db.add(activity)

                log.processed = True
                log.lead_id = lead.id
                results["processed"] += 1

            except Exception as exc:
                log.error = str(exc)
                results["errors"] += 1

    db.commit()
    return results
