from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

from app.core.config import settings

ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ─────────────────────────────────────────
# Platform SuperAdmin Auth
# ─────────────────────────────────────────

def get_current_platform_user(token: str = Depends(oauth2_scheme)):
    """
    Validates JWT for platform-level (SuperAdmin) users.
    Returns the raw JWT payload dict.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != "platform":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a platform user",
            )

        return payload

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
