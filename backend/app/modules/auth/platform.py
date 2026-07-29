from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.user import PlatformUser
from app.core.security import verify_password, create_access_token

router = APIRouter()

@router.post("/platform/login")
def platform_login(email: str, password: str, db: Session = Depends(get_db)):
    user = db.query(PlatformUser).filter(PlatformUser.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user.id, "role": "superadmin", "type": "platform"})
    return {"access_token": token}