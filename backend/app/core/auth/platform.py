"""
Platform Authentication Dependency
-----------------------------------
Used exclusively by SuperAdmin (platform-level) routes.

- Validates JWT type = "platform"
- Returns raw JWT payload dict (not a DB model)
- No tenant_id required or checked
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

from app.core.config import settings

ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/platform/login")


def get_current_platform_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Validates a platform-level JWT token.
    Returns the decoded JWT payload.

    JWT must contain:
        sub  → platform_user id
        role → superadmin
        type → platform
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != "platform":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: not a platform user",
            )

        if payload.get("role") != "superadmin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient platform role",
            )

        return payload

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired platform token",
            headers={"WWW-Authenticate": "Bearer"},
        )
