"""
Activity Log Service
─────────────────────
Central writer used by every module to record operations.
Never raises an exception — logging must never break business logic.

Usage anywhere in the app:
    from app.core.logger import log_activity
    from app.models.activity_log import LogLevel, LogModule

    log_activity(
        db       = db,
        tenant_id= str(current_user.tenant_id),
        actor    = current_user,
        module   = LogModule.ORDERS,
        action   = "order.create",
        message  = f"Order {order.order_number} created",
        detail   = {"order_id": str(order.id), "total": float(order.grand_total)},
        level    = LogLevel.INFO,
        request  = request,   # optional FastAPI Request
        error_code = "ERR-1708589644-A3F7",  # optional error code
    )
"""

from __future__ import annotations

import traceback
from datetime import datetime, timezone, timedelta
from typing import Optional, Any

from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog, LogLevel, LogModule

# ── TTL for all log entries ────────────────────────────────────
LOG_TTL_HOURS = 6


def log_activity(
    db: Session,
    module: LogModule,
    action: str,
    *,
    tenant_id: Optional[str] = None,
    actor: Any = None,          # Employee or User model instance, or None
    actor_email: Optional[str] = None,
    actor_role: Optional[str] = None,
    actor_ip: Optional[str] = None,
    level: LogLevel = LogLevel.INFO,
    message: Optional[str] = None,
    detail: Optional[dict] = None,
    status_code: Optional[int] = None,
    method: Optional[str] = None,
    path: Optional[str] = None,
    user_agent: Optional[str] = None,
    request: Any = None,        # FastAPI Request object (optional)
    error_code: Optional[str] = None,   # diagnostic error code
) -> None:
    """
    Write one log entry.  Never raises — swallows all errors internally.
    """
    try:
        now = datetime.now(timezone.utc)

        # ── Resolve actor fields ──────────────────────────────
        _actor_id    = None
        _actor_email = actor_email
        _actor_role  = actor_role
        _actor_ip    = actor_ip

        if actor is not None:
            _actor_id    = str(getattr(actor, "id", "") or "")
            _actor_email = _actor_email or getattr(actor, "email", None)
            _actor_role  = _actor_role  or str(getattr(actor, "role", "") or "")

        # ── Resolve request context ───────────────────────────
        if request is not None:
            try:
                if method is None:
                    method = request.method
                if path is None:
                    path = str(request.url.path)
                if _actor_ip is None:
                    # honour X-Forwarded-For when behind nginx
                    forwarded = request.headers.get("x-forwarded-for")
                    _actor_ip = (forwarded.split(",")[0].strip()
                                 if forwarded
                                 else getattr(request.client, "host", None))
                if user_agent is None:
                    user_agent = request.headers.get("user-agent")
            except Exception:
                pass

        entry = ActivityLog(
            tenant_id   = tenant_id,
            actor_id    = _actor_id,
            actor_email = _actor_email,
            actor_role  = _actor_role,
            actor_ip    = _actor_ip,
            module      = module,
            action      = action,
            level       = level,
            status_code = status_code,
            message     = message,
            detail      = detail,
            method      = method,
            path        = path,
            user_agent  = user_agent,
            error_code  = error_code,
            created_at  = now,
            expires_at  = now + timedelta(hours=LOG_TTL_HOURS),
        )
        db.add(entry)
        db.commit()

    except Exception:
        # Never crash business logic over logging failure
        try:
            db.rollback()
        except Exception:
            pass


def purge_expired_logs(db: Session) -> int:
    """
    Delete all log entries whose expires_at < now.
    Called by the background cleanup scheduler.
    Returns the count of deleted rows.
    """
    try:
        now = datetime.now(timezone.utc)
        deleted = (
            db.query(ActivityLog)
            .filter(ActivityLog.expires_at < now)
            .delete(synchronize_session=False)
        )
        db.commit()
        return deleted
    except Exception:
        db.rollback()
        return 0


def get_tenant_logs(
    db: Session,
    tenant_id: str,
    *,
    level: Optional[str] = None,
    module: Optional[str] = None,
    action: Optional[str] = None,
    hours: int = 6,
    limit: int = 200,
    offset: int = 0,
) -> list[ActivityLog]:
    """
    Fetch live logs for a specific tenant — SuperAdmin only.
    Always filters to `hours` window to prevent large dumps.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=min(hours, LOG_TTL_HOURS))
    q = (
        db.query(ActivityLog)
        .filter(
            ActivityLog.tenant_id == tenant_id,
            ActivityLog.created_at >= cutoff,
        )
    )
    if level:
        q = q.filter(ActivityLog.level == level)
    if module:
        q = q.filter(ActivityLog.module == module)
    if action:
        q = q.filter(ActivityLog.action.ilike(f"%{action}%"))

    return (
        q.order_by(ActivityLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_platform_logs(
    db: Session,
    *,
    level: Optional[str] = None,
    hours: int = 6,
    limit: int = 200,
    offset: int = 0,
) -> list[ActivityLog]:
    """
    Fetch platform-level logs (tenant_id IS NULL) — SuperAdmin only.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=min(hours, LOG_TTL_HOURS))
    q = (
        db.query(ActivityLog)
        .filter(
            ActivityLog.tenant_id.is_(None),
            ActivityLog.created_at >= cutoff,
        )
    )
    if level:
        q = q.filter(ActivityLog.level == level)

    return (
        q.order_by(ActivityLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_all_logs(
    db: Session,
    *,
    tenant_id: Optional[str] = None,
    level: Optional[str] = None,
    module: Optional[str] = None,
    hours: int = 6,
    limit: int = 500,
    offset: int = 0,
) -> list[ActivityLog]:
    """
    Fetch all logs across all tenants — SuperAdmin dashboard.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=min(hours, LOG_TTL_HOURS))
    q = db.query(ActivityLog).filter(ActivityLog.created_at >= cutoff)
    if tenant_id:
        q = q.filter(ActivityLog.tenant_id == tenant_id)
    if level:
        q = q.filter(ActivityLog.level == level)
    if module:
        q = q.filter(ActivityLog.module == module)

    return (
        q.order_by(ActivityLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_log_summary(db: Session, tenant_id: str, hours: int = 6) -> dict:
    """
    Quick summary counts for a tenant's recent activity.
    """
    from sqlalchemy import func
    cutoff = datetime.now(timezone.utc) - timedelta(hours=min(hours, LOG_TTL_HOURS))

    rows = (
        db.query(ActivityLog.level, func.count(ActivityLog.id).label("cnt"))
        .filter(
            ActivityLog.tenant_id == tenant_id,
            ActivityLog.created_at >= cutoff,
        )
        .group_by(ActivityLog.level)
        .all()
    )

    summary = {lvl.value: 0 for lvl in LogLevel}
    for row in rows:
        summary[row.level.value] = row.cnt

    summary["total"] = sum(summary.values())
    return summary
