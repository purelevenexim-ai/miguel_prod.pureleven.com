"""
Error Response Middleware & Handlers
──────────────────────────────────────
Catches exceptions and generates diagnostic error codes.
Logs every error to activity_logs with the code.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import traceback
import logging

from app.core.error_code import generate_error_code
from app.core.logger import log_activity
from app.models.activity_log import LogLevel, LogModule

logger = logging.getLogger("miguel.errors")


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors with error codes."""
    error_code = generate_error_code(
        error_msg=str(exc),
        error_type="VALIDATION",
        context={"path": str(request.url.path)},
    )

    # Try to log the error
    try:
        from app.database.session import SessionLocal
        db = SessionLocal()
        try:
            log_activity(
                db=db,
                module=LogModule.SYSTEM,
                action="validation.error",
                level=LogLevel.WARNING,
                message=f"Validation error on {request.method} {request.url.path}",
                detail={"error_count": len(exc.errors()), "first_error": str(exc.errors()[0]) if exc.errors() else None},
                status_code=422,
                method=request.method,
                path=str(request.url.path),
                user_agent=request.headers.get("user-agent"),
                error_code=error_code,
                request=request,
            )
        finally:
            db.close()
    except Exception as db_err:
        logger.warning(f"Failed to log validation error to database: {str(db_err)}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": [{"msg": e["msg"], "loc": e["loc"]} for e in exc.errors()],
            "error_code": error_code,
        },
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions with error codes."""
    error_code = generate_error_code(
        error_msg=str(exc),
        error_type=exc.__class__.__name__,
        context={"path": str(request.url.path)},
    )

    logger.error(f"[{error_code}] {exc.__class__.__name__}: {exc}", exc_info=True)

    # Try to log the error
    try:
        from app.database.session import SessionLocal
        db = SessionLocal()
        try:
            log_activity(
                db=db,
                module=LogModule.SYSTEM,
                action="exception.unhandled",
                level=LogLevel.ERROR,
                message=f"Unhandled {exc.__class__.__name__} on {request.method} {request.url.path}",
                detail={
                    "exception": exc.__class__.__name__, 
                    "message": str(exc),
                    "traceback": traceback.format_exc()
                },
                status_code=500,
                method=request.method,
                path=str(request.url.path),
                user_agent=request.headers.get("user-agent"),
                error_code=error_code,
                request=request,
            )
        finally:
            db.close()
    except Exception as db_err:
        logger.warning(f"Failed to log exception to database: {str(db_err)}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error_code": error_code,
        },
    )


def setup_error_handlers(app: FastAPI):
    """Register error handlers with the FastAPI app."""
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
