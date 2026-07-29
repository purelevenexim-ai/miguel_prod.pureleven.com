"""
Tenant Authentication Dependency
-----------------------------------
Used exclusively by tenant-scoped (employee) routes.

- Validates JWT type = "tenant"
- Returns Employee ORM object
- Always validates tenant_id, is_active, deleted_at
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import get_db
from app.models.employee import Employee, RoleEnum
from app.models.tenant import Tenant

ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/tenant/login")


def get_current_tenant_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Employee:
    """
    Validates a tenant-level JWT token.
    Returns the authenticated Employee ORM object.

    JWT must contain:
        sub       → employee id
        tenant_id → tenant uuid
        role      → admin | sales | marketing | operations | support
        type      → tenant
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate tenant credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])

        user_id: str = payload.get("sub")
        tenant_id: str = payload.get("tenant_id")
        token_type: str = payload.get("type")

        if not user_id or not tenant_id:
            raise credentials_exception

        if token_type != "tenant":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: not a tenant token",
            )

    except JWTError:
        raise credentials_exception

    # ── Fetch Employee ────────────────────────────────────────
    employee = (
        db.query(Employee)
        .filter(Employee.id == user_id, Employee.tenant_id == tenant_id)
        .first()
    )

    if employee is None:
        raise credentials_exception

    # ── Employee Active Check ─────────────────────────────────
    if not employee.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employee account is inactive",
        )

    # ── Tenant Active + Soft Delete Check ────────────────────
    tenant = db.query(Tenant).filter(Tenant.id == employee.tenant_id).first()

    if tenant is None:
        raise credentials_exception

    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant is inactive",
        )

    if tenant.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant account has been deleted",
        )

    return employee


def require_roles(*roles: RoleEnum):
    """
    Role-based access guard factory.

    Usage:
        @router.get("/admin-only")
        def my_route(employee = Depends(require_roles(RoleEnum.admin))):
            ...
    """
    def guard(current_employee: Employee = Depends(get_current_tenant_user)):
        if current_employee.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: requires one of {[r.value for r in roles]}",
            )
        return current_employee
    return guard
