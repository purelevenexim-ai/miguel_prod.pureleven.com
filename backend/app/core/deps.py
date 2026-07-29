from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.employee import Employee
from app.models.user import User
from app.models.tenant import Tenant
from app.core.config import settings


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """
    Universal auth dependency.
    - If JWT type = 'platform'  → returns User (SuperAdmin)
    - If JWT type = 'employee'  → returns Employee (tenant-scoped)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")

        if user_id is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    # ── Platform SuperAdmin ──────────────────────────
    if token_type == "platform":
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise credentials_exception
        return user

    # ── Employee (tenant-scoped) ─────────────────────
    tenant_id: str = payload.get("tenant_id")
    if tenant_id is None:
        raise credentials_exception

    employee = (
        db.query(Employee)
        .filter(Employee.id == user_id, Employee.tenant_id == tenant_id)
        .first()
    )

    if employee is None:
        raise credentials_exception

    # 🔐 Employee active check
    if not employee.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employee account is inactive",
        )

    # 🔐 Tenant active + soft-delete check
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
            detail="Tenant account is deleted",
        )

    return employee
