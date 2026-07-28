from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Optional
from pydantic import BaseModel

from app.database.session import get_db
from app.models.employee import Employee, RoleEnum
from app.models.tenant import Tenant
from app.core.security import hash_password, verify_password, create_access_token
from app.core.password_utils import generate_secure_password
from app.core.auth.tenant import get_current_tenant_user, require_roles
from app.core.logger import log_activity
from app.models.activity_log import LogLevel, LogModule

router = APIRouter(prefix="/tenant", tags=["Tenant Auth"])

MAX_EMPLOYEES = 5   # hard cap per tenant


# ─────────────────────────────────────────
# Request Schemas
# ─────────────────────────────────────────

class EmployeeCreateRequest(BaseModel):
    full_name: str
    email: str
    password: str
    role: RoleEnum
    phone: Optional[str] = None


class EmployeeUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[RoleEnum] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None


class TenantLoginRequest(BaseModel):
    slug: str
    email: str
    password: str


# ─────────────────────────────────────────
# Tenant Login
# ─────────────────────────────────────────

@router.post("/login", summary="Tenant Employee Login")
def tenant_login(
    data: TenantLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Login for all tenant employees (admin, sales, marketing, operations, support).
    Requires slug to identify the tenant.
    Issues a JWT with type=tenant.
    """
    # 1️⃣ Find tenant by slug
    tenant = db.query(Tenant).filter(Tenant.slug == data.slug).first()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # 2️⃣ Tenant active checks
    if not tenant.is_active:
        raise HTTPException(status_code=403, detail="Tenant is inactive")

    if tenant.deleted_at is not None:
        raise HTTPException(status_code=403, detail="Tenant account is deleted")

    # 3️⃣ Find employee inside that tenant
    employee = db.query(Employee).filter(
        Employee.email == data.email,
        Employee.tenant_id == tenant.id
    ).first()

    if not employee:
        log_activity(
            db=db, tenant_id=str(tenant.id),
            module=LogModule.AUTH, action="auth.login_failed",
            level=LogLevel.WARNING, request=request,
            message=f"Failed login attempt for {data.email} (employee not found)",
            detail={"email": data.email, "slug": data.slug},
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 4️⃣ Verify password
    if not verify_password(data.password, employee.hashed_password):
        log_activity(
            db=db, tenant_id=str(tenant.id), actor=employee,
            module=LogModule.AUTH, action="auth.login_failed",
            level=LogLevel.WARNING, request=request,
            message=f"Failed login attempt for {data.email} (wrong password)",
            detail={"email": data.email, "slug": data.slug},
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 5️⃣ Employee active check
    if not employee.is_active:
        raise HTTPException(status_code=403, detail="Employee account is inactive")

    # 6️⃣ Issue JWT with type=tenant
    access_token = create_access_token(
        data={
            "sub": str(employee.id),
            "tenant_id": str(employee.tenant_id),
            "role": employee.role.value,
            "type": "tenant",
        },
        expires_delta=timedelta(hours=8),
    )

    # ── Log successful login ──────────────────────────────────
    log_activity(
        db=db, tenant_id=str(tenant.id), actor=employee,
        module=LogModule.AUTH, action="auth.login_success",
        level=LogLevel.INFO, request=request,
        message=f"{employee.email} ({employee.role.value}) logged in",
        detail={"slug": data.slug, "role": employee.role.value},
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": employee.role.value,
        "employee_id": str(employee.id),
        "tenant_id": str(employee.tenant_id),
    }


# ─────────────────────────────────────────
# Get Current Employee (Me)
# ─────────────────────────────────────────

@router.get("/me", summary="Current Employee Profile")
def get_me(current_employee: Employee = Depends(get_current_tenant_user)):
    return {
        "id": str(current_employee.id),
        "full_name": current_employee.full_name,
        "email": current_employee.email,
        "role": current_employee.role.value,
        "tenant_id": str(current_employee.tenant_id),
        "is_active": current_employee.is_active,
    }


# ─────────────────────────────────────────
# Create Employee (Admin Only)
# ─────────────────────────────────────────

@router.post("/employees", summary="Create New Employee")
def create_employee(
    data: EmployeeCreateRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    if current_user.role != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    # ── Enforce 5-employee cap (active employees) ─────────────
    active_count = db.query(Employee).filter(
        Employee.tenant_id == current_user.tenant_id,
        Employee.is_active == True,
    ).count()
    if active_count >= MAX_EMPLOYEES:
        raise HTTPException(
            status_code=400,
            detail=f"Employee limit reached ({MAX_EMPLOYEES} max active employees per tenant)"
        )

    existing = db.query(Employee).filter(
        Employee.email == data.email,
        Employee.tenant_id == current_user.tenant_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Email already registered in this tenant")

    new_employee = Employee(
        full_name=data.full_name,
        email=data.email,
        hashed_password=hash_password(data.password),
        role=data.role,
        phone=data.phone,
        tenant_id=current_user.tenant_id,
        is_active=True,
    )

    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)

    return {
        "message": "Employee created successfully",
        "employee_id": str(new_employee.id),
        "full_name": new_employee.full_name,
        "email": new_employee.email,
        "role": new_employee.role.value,
    }


# ─────────────────────────────────────────
# List Employees (Admin Only, Tenant Scoped)
# ─────────────────────────────────────────

@router.get("/employees", summary="List All Employees in Tenant")
def list_employees(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    if current_user.role != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    employees = db.query(Employee).filter(
        Employee.tenant_id == current_user.tenant_id
    ).order_by(Employee.full_name).all()

    return [_emp_dict(emp) for emp in employees]


# ─────────────────────────────────────────
# Get Single Employee
# ─────────────────────────────────────────

@router.get("/employees/{employee_id}", summary="Get Employee Detail")
def get_employee(
    employee_id: str,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin)),
):
    emp = db.query(Employee).filter(
        Employee.id == employee_id,
        Employee.tenant_id == current_user.tenant_id,
    ).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return _emp_dict(emp)


# ─────────────────────────────────────────
# Update Employee (role, name, phone)
# ─────────────────────────────────────────

@router.patch("/employees/{employee_id}", summary="Update Employee Role / Details")
def update_employee(
    employee_id: str,
    data: EmployeeUpdateRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin)),
):
    emp = db.query(Employee).filter(
        Employee.id == employee_id,
        Employee.tenant_id == current_user.tenant_id,
    ).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Cannot change own role
    if str(emp.id) == str(current_user.id) and data.role and data.role != emp.role:
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    if data.full_name is not None:
        emp.full_name = data.full_name
    if data.role is not None:
        emp.role = data.role
    if data.phone is not None:
        emp.phone = data.phone
    if data.is_active is not None:
        if not data.is_active and str(emp.id) == str(current_user.id):
            raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
        emp.is_active = data.is_active

    db.commit()
    db.refresh(emp)
    return _emp_dict(emp)


# ─────────────────────────────────────────
# Deactivate / Reactivate Employee
# ─────────────────────────────────────────

@router.patch("/employees/{employee_id}/deactivate", summary="Deactivate Employee")
def deactivate_employee(
    employee_id: str,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin)),
):
    emp = _get_emp_scoped(employee_id, current_user.tenant_id, db)
    if str(emp.id) == str(current_user.id):
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    emp.is_active = False
    db.commit()
    return {"message": "Employee deactivated", "employee_id": employee_id}


@router.patch("/employees/{employee_id}/activate", summary="Activate Employee")
def activate_employee(
    employee_id: str,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin)),
):
    emp = _get_emp_scoped(employee_id, current_user.tenant_id, db)
    emp.is_active = True
    db.commit()
    return {"message": "Employee activated", "employee_id": employee_id}


# ─────────────────────────────────────────
# Reset Employee Password (Admin Only)
# ─────────────────────────────────────────

@router.patch("/employees/{employee_id}/reset-password", summary="Reset Employee Password")
def reset_employee_password(
    employee_id: str,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin)),
):
    """
    Admin resets any employee's password (including their own).
    Returns a new secure generated password (shown once).
    """
    emp = _get_emp_scoped(employee_id, current_user.tenant_id, db)
    new_password = generate_secure_password()
    emp.hashed_password = hash_password(new_password)
    db.commit()
    return {
        "message": "Password reset successfully",
        "employee_id": employee_id,
        "employee_name": emp.full_name,
        "email": emp.email,
        "new_password": new_password,
    }


# ─────────────────────────────────────────
# Tenant Stats (admin summary)
# ─────────────────────────────────────────

@router.get("/stats", summary="Tenant Admin Stats")
def tenant_stats(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_roles(RoleEnum.admin)),
):
    from app.models.lead import Lead
    from app.models.customer import Customer
    from app.models.order import Order

    tid = current_user.tenant_id
    total_emp    = db.query(Employee).filter(Employee.tenant_id == tid).count()
    active_emp   = db.query(Employee).filter(Employee.tenant_id == tid, Employee.is_active == True).count()
    total_leads  = db.query(Lead).filter(Lead.tenant_id == tid).count()
    total_cust   = db.query(Customer).filter(Customer.tenant_id == tid).count()
    total_orders = db.query(Order).filter(Order.tenant_id == tid).count()

    return {
        "total_employees":  total_emp,
        "active_employees": active_emp,
        "employee_limit":   MAX_EMPLOYEES,
        "slots_remaining":  max(0, MAX_EMPLOYEES - active_emp),
        "total_leads":      total_leads,
        "total_customers":  total_cust,
        "total_orders":     total_orders,
    }


# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────

def _emp_dict(emp: Employee) -> dict:
    return {
        "id":         str(emp.id),
        "full_name":  emp.full_name,
        "email":      emp.email,
        "phone":      emp.phone or "",
        "role":       emp.role.value,
        "is_active":  emp.is_active,
        "tenant_id":  str(emp.tenant_id),
    }


def _get_emp_scoped(employee_id: str, tenant_id, db: Session) -> Employee:
    emp = db.query(Employee).filter(
        Employee.id == employee_id,
        Employee.tenant_id == tenant_id,
    ).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp
