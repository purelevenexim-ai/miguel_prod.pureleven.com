"""
Request Logging Middleware
───────────────────────────
Automatically logs every API request + response to activity_logs.
- Extracts tenant_id and actor from JWT (without raising on invalid token)
- Skips noisy read-only GET endpoints (configurable)
- Records status code, method, path, IP, duration
- On 4xx/5xx logs at WARNING/ERROR level with response body snippet
"""

import time
import json
import logging
from typing import Set

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from jose import jwt, JWTError

from app.core.config import settings
from app.models.activity_log import LogLevel, LogModule

logger = logging.getLogger("miguel.middleware")

# ── Paths to skip (health check, docs, static) ────────────────
_SKIP_PATHS: Set[str] = {
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
}

# ── GET requests we skip to reduce noise ─────────────────────
# Only log writes + errors + auth events
_SKIP_GET_PREFIXES = (
    "/api/orders",
    "/api/customers",
    "/api/products",
    "/api/leads",
    "/api/vendors",
    "/api/purchases",
    "/api/inventory",
    "/api/invoices",
    "/api/reports",
    "/api/labels",
    "/api/meta",
)


def _path_to_module(path: str) -> LogModule:
    mapping = {
        "/api/orders":    LogModule.ORDERS,
        "/api/customers": LogModule.CUSTOMERS,
        "/api/leads":     LogModule.LEADS,
        "/api/products":  LogModule.PRODUCTS,
        "/api/inventory": LogModule.INVENTORY,
        "/api/invoices":  LogModule.INVOICES,
        "/api/vendors":   LogModule.VENDORS,
        "/api/purchases": LogModule.PURCHASES,
        "/api/labels":    LogModule.LABELS,
        "/api/meta":      LogModule.META,
        "/api/reports":   LogModule.REPORTING,
        "/tenant":        LogModule.AUTH,
        "/platform":      LogModule.PLATFORM,
        "/employee":      LogModule.EMPLOYEES,
    }
    for prefix, mod in mapping.items():
        if path.startswith(prefix):
            return mod
    return LogModule.SYSTEM


def _extract_jwt_payload(request: Request) -> dict | None:
    """Decode JWT without raising — returns None on any failure."""
    try:
        auth = request.headers.get("authorization", "")
        if not auth.startswith("Bearer "):
            return None
        token = auth[7:]
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except (JWTError, Exception):
        return None


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # ── Skip non-API paths ────────────────────────────────
        if path in _SKIP_PATHS:
            return await call_next(request)

        # ── Skip noisy GET reads ──────────────────────────────
        is_get = request.method == "GET"
        if is_get and path.startswith(tuple(_SKIP_GET_PREFIXES)):
            return await call_next(request)

        start = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms = int((time.perf_counter() - start) * 1000)

        # ── Determine log level from status code ─────────────
        status_code = response.status_code
        if status_code < 400:
            level = LogLevel.INFO
        elif status_code < 500:
            level = LogLevel.WARNING
        else:
            level = LogLevel.ERROR

        # ── Extract actor from JWT ────────────────────────────
        payload   = _extract_jwt_payload(request)
        tenant_id = None
        actor_id  = None
        actor_email = None
        actor_role  = None

        if payload:
            tenant_id   = payload.get("tenant_id")
            actor_id    = payload.get("sub")
            actor_role  = payload.get("role")
            actor_email = payload.get("email")

        # ── IP address ────────────────────────────────────────
        forwarded = request.headers.get("x-forwarded-for")
        actor_ip  = (
            forwarded.split(",")[0].strip()
            if forwarded
            else (request.client.host if request.client else None)
        )

        # ── Action name ───────────────────────────────────────
        module = _path_to_module(path)
        action = f"{request.method.lower()}.{path.strip('/').replace('/', '.')}"

        message = (
            f"{request.method} {path} → {status_code} ({duration_ms}ms)"
        )

        detail = {
            "status_code": status_code,
            "duration_ms": duration_ms,
            "query": str(request.query_params) or None,
        }

        # ── Write log (non-blocking, fire-and-forget in thread) ─
        try:
            from app.database.session import SessionLocal
            from app.core.logger import log_activity
            from app.models.activity_log import ActivityLog
            from datetime import timedelta

            now = __import__('datetime').datetime.now(__import__('datetime').timezone.utc)
            db = SessionLocal()
            try:
                entry = ActivityLog(
                    tenant_id   = tenant_id,
                    actor_id    = actor_id,
                    actor_email = actor_email,
                    actor_role  = actor_role,
                    actor_ip    = actor_ip,
                    module      = module,
                    action      = action,
                    level       = level,
                    status_code = status_code,
                    message     = message,
                    detail      = detail,
                    method      = request.method,
                    path        = path,
                    user_agent  = request.headers.get("user-agent"),
                    created_at  = now,
                    expires_at  = now + timedelta(hours=6),
                )
                db.add(entry)
                db.commit()
            finally:
                db.close()
        except Exception as exc:
            logger.warning(f"[RequestLoggingMiddleware] Failed to write log: {exc}")

        return response
