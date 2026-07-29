from pydantic import BaseModel, EmailStr


class TenantCreate(BaseModel):
    company_name: str
    owner_email: EmailStr
    admin_password: str

