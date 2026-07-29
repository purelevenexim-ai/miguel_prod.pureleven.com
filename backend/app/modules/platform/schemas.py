from pydantic import BaseModel, EmailStr
from typing import Optional


class TenantCreateRequest(BaseModel):
    company_name: str
    contact_person_name: str
    contact_phone: Optional[str] = None
    owner_email: EmailStr
    slug: Optional[str] = None
