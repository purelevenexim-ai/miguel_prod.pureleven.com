from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

from app.database.session import get_db
from app.models.user import User
from app.models.tenant import Tenant
from app.models.employee import Employee, RoleEnum
from app.modules.platform.schemas import TenantCreateRequest
from app.core.auth.platform import get_current_platform_user
from app.core.slug_utils import generate_slug
from app.core.password_utils import generate_secure_password
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/platform", tags=["Platform"])


# ─────────────────────────────────────────────────────────────
# Platform Login  (SuperAdmin only)
# ─────────────────────────────────────────────────────────────

@router.post("/login", summary="SuperAdmin Login")
def platform_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Login endpoint for platform SuperAdmin.
    Issues a JWT with type=platform.
    """
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.role != "superadmin":
        raise HTTPException(status_code=403, detail="Not a platform user")

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role,
            "type": "platform",
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
    }


# ─────────────────────────────────────────────────────────────
# Platform Me  (SuperAdmin profile)
# ─────────────────────────────────────────────────────────────

@router.get("/me", summary="SuperAdmin Profile")
def platform_me(
    current_user: dict = Depends(get_current_platform_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == current_user.get("sub")).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
    }


# ─────────────────────────────────────────────────────────────
# Tenant Management
# ─────────────────────────────────────────────────────────────

@router.post("/tenants", summary="Create Tenant")
def create_tenant(
    data: TenantCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_platform_user),
):
    try:
        # 1️⃣ Generate slug
        slug = generate_slug(
            db=db,
            owner_email=data.owner_email,
            provided_slug=data.slug
        )

        # 2️⃣ Generate secure random password
        generated_password = generate_secure_password()

        # 3️⃣ Create tenant
        new_tenant = Tenant(
            company_name=data.company_name,
            slug=slug,
            contact_person_name=data.contact_person_name,
            contact_phone=data.contact_phone,
            owner_email=data.owner_email,
            is_active=True,
        )

        db.add(new_tenant)
        db.flush()

        # 4️⃣ Create first admin employee
        admin_employee = Employee(
            full_name=data.contact_person_name,
            email=data.owner_email,
            hashed_password=hash_password(generated_password),
            role=RoleEnum.admin,
            tenant_id=new_tenant.id,
            is_active=True,
        )

        db.add(admin_employee)

        # 5️⃣ Commit atomically
        db.commit()

        return {
            "tenant_id": str(new_tenant.id),
            "company_name": new_tenant.company_name,
            "slug": new_tenant.slug,
            "admin_email": admin_employee.email,
            "generated_password": generated_password,
        }

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Tenant creation failed due to duplicate data")

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tenants", summary="List All Tenants")
def list_tenants(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_platform_user),
):
    # Only show non-deleted tenants
    tenants = db.query(Tenant).filter(Tenant.deleted_at == None).order_by(Tenant.created_at.desc()).all()
    return [_tenant_dict(t) for t in tenants]


@router.get("/tenants/archived/list", summary="List Archived Tenants")
def list_archived_tenants(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_platform_user),
):
    # Only show deleted tenants
    tenants = db.query(Tenant).filter(Tenant.deleted_at != None).order_by(Tenant.deleted_at.desc()).all()
    return [_tenant_dict(t) for t in tenants]


@router.get("/tenants/{tenant_id}", summary="Get Single Tenant")
def get_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_platform_user),
):
    t = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tenant not found")
    # include employee count
    emp_count = db.query(Employee).filter(Employee.tenant_id == t.id).count()
    d = _tenant_dict(t)
    d["employee_count"] = emp_count
    return d


@router.patch("/tenants/{tenant_id}/activate", summary="Activate Tenant")
def activate_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_platform_user),
):
    t = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tenant not found")
    t.is_active = True
    t.deleted_at = None  # Clear soft-delete timestamp when restoring
    db.commit()
    return {"message": "Tenant activated", "tenant_id": tenant_id, "is_active": True}


@router.patch("/tenants/{tenant_id}/deactivate", summary="Deactivate Tenant")
def deactivate_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_platform_user),
):
    t = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tenant not found")
    t.is_active = False
    db.commit()
    return {"message": "Tenant deactivated", "tenant_id": tenant_id, "is_active": False}


@router.patch("/tenants/{tenant_id}/reset-password", summary="Reset Tenant Admin Password")
def reset_tenant_password(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_platform_user),
):
    """
    Generate a new secure password for the tenant's admin employee.
    Returns the new plain-text password (shown once).
    """
    t = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Find the admin employee for this tenant
    admin_emp = db.query(Employee).filter(
        Employee.tenant_id == tenant_id,
        Employee.role == RoleEnum.admin,
    ).first()
    if not admin_emp:
        raise HTTPException(status_code=404, detail="No admin employee found for this tenant")

    new_password = generate_secure_password()
    admin_emp.hashed_password = hash_password(new_password)
    db.commit()

    return {
        "message": "Password reset successfully",
        "tenant_id": tenant_id,
        "admin_email": admin_emp.email,
        "new_password": new_password,
    }


@router.delete("/tenants/{tenant_id}", summary="Delete Tenant (soft)")
def delete_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_platform_user),
):
    from datetime import datetime, timezone
    t = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tenant not found")
    t.is_active = False
    t.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Tenant deleted", "tenant_id": tenant_id}


@router.delete("/tenants/{tenant_id}/permanent", summary="Permanently Delete Tenant (hard delete)")
def permanently_delete_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_platform_user),
):
    """
    Permanently delete a tenant and ALL associated data.
    Deletes in FK-safe order (children before parents).
    This operation is IRREVERSIBLE.
    """
    t = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if t.deleted_at is None:
        raise HTTPException(status_code=400, detail="Tenant must be soft-deleted first. Use DELETE endpoint.")

    tid = tenant_id  # string UUID — used as bind param

    try:
        p = {"tid": tid}

        # ── WA leaf tables ───────────────────────────────────────────
        db.execute(text("DELETE FROM wa_status_history          WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM wa_status                  WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM wa_campaign_recipients     WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM wa_messages                WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM wa_conversations           WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM wa_subscribers             WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM wa_campaigns               WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM wa_campaign_types          WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM wa_postback_rules          WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM wa_outbound_webhooks       WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM whatsapp_api_message_log   WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM wa_settings                WHERE tenant_id = CAST(:tid AS UUID)"), p)

        # ── Meta ─────────────────────────────────────────────────────
        db.execute(text("DELETE FROM meta_webhook_logs          WHERE lead_id IN (SELECT id FROM leads WHERE tenant_id = CAST(:tid AS UUID))"), p)
        db.execute(text("DELETE FROM meta_integrations          WHERE tenant_id = CAST(:tid AS UUID)"), p)

        # ── Logistics / risk tables ───────────────────────────────────
        db.execute(text("DELETE FROM notification_logs          WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM ndr_records                WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM cod_transactions           WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM blacklisted_customers      WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM customer_delivery_scores   WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM order_risk_assessments     WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM rto_zones                  WHERE tenant_id = CAST(:tid AS UUID)"), p)

        # ── Customer child tables (before customers) ──────────────────
        db.execute(text("DELETE FROM customer_interactions      WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM customer_products          WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM customer_tag_map           WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM customer_tags              WHERE tenant_id = CAST(:tid AS UUID)"), p)

        # ── Leads (NULLify back-refs first, then children, then leads) ─
        db.execute(text("DELETE FROM meta_webhook_logs          WHERE lead_id IN (SELECT id FROM leads WHERE tenant_id = CAST(:tid AS UUID))"), p)
        db.execute(text("DELETE FROM lead_messages              WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM lead_activities            WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM leads                      WHERE tenant_id = CAST(:tid AS UUID)"), p)

        # ── Orders and children ───────────────────────────────────────
        db.execute(text("DELETE FROM order_status_history       WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM order_payments             WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM order_items                WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM orders                     WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM india_post_customer_ids    WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM couriers                   WHERE tenant_id = CAST(:tid AS UUID)"), p)

        # ── Invoices ──────────────────────────────────────────────────
        db.execute(text("DELETE FROM invoice_items              WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM invoice_counters           WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM invoices                   WHERE tenant_id = CAST(:tid AS UUID)"), p)

        # ── Purchases ─────────────────────────────────────────────────
        db.execute(text("DELETE FROM purchase_order_items       WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM purchase_orders            WHERE tenant_id = CAST(:tid AS UUID)"), p)

        # ── Inventory ─────────────────────────────────────────────────
        db.execute(text("DELETE FROM inventory_movements        WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM inventory_summary          WHERE tenant_id = CAST(:tid AS UUID)"), p)

        # ── Vendors & products ────────────────────────────────────────
        db.execute(text("DELETE FROM vendor_products            WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM vendors                    WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM products                   WHERE tenant_id = CAST(:tid AS UUID) AND variation_of IS NOT NULL"), p)
        db.execute(text("DELETE FROM products                   WHERE tenant_id = CAST(:tid AS UUID)"), p)

        # ── Shopify (children before shopify_orders before customers) ─
        db.execute(text("DELETE FROM tracking_events            WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM shipping_info              WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM shopify_orders             WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM shopify_stores             WHERE tenant_id = CAST(:tid AS UUID)"), p)

        # ── Customers (after all child tables cleared) ────────────────
        db.execute(text("DELETE FROM customers                  WHERE tenant_id = CAST(:tid AS UUID)"), p)

        # ── Shipping config ───────────────────────────────────────────
        db.execute(text("DELETE FROM notification_channels      WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM delivery_partners          WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM shipping_business_rules    WHERE tenant_id = CAST(:tid AS UUID)"), p)

        # ── Activity logs ─────────────────────────────────────────────
        db.execute(text("DELETE FROM activity_logs              WHERE tenant_id = CAST(:tid AS UUID)"), p)

        # ── Employees then Tenant (last) ──────────────────────────────
        db.execute(text("DELETE FROM employees                  WHERE tenant_id = CAST(:tid AS UUID)"), p)
        db.execute(text("DELETE FROM tenants                    WHERE id = CAST(:tid AS UUID)"),        p)

        db.commit()

        return {
            "message": "Tenant permanently deleted with all associated data",
            "tenant_id": tenant_id,
            "status": "destroyed",
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to permanently delete tenant: {str(e)}")


@router.get("/stats", summary="Platform Stats")
def platform_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_platform_user),
):
    from app.models.employee import Employee as Emp
    total    = db.query(Tenant).count()
    active   = db.query(Tenant).filter(Tenant.is_active == True).count()
    inactive = total - active
    deleted  = db.query(Tenant).filter(Tenant.deleted_at != None).count()
    total_emp = db.query(Emp).count()
    return {
        "total_tenants":    total,
        "active_tenants":   active,
        "inactive_tenants": inactive,
        "deleted_tenants":  deleted,
        "total_employees":  total_emp,
    }


# ── Helper ────────────────────────────────────────────────────
def _tenant_dict(t: Tenant) -> dict:
    return {
        "id":                   str(t.id),
        "company_name":         t.company_name,
        "slug":                 t.slug,
        "owner_email":          t.owner_email,
        "contact_person_name":  t.contact_person_name,
        "contact_phone":        t.contact_phone or "",
        "is_active":            t.is_active,
        "created_at":           t.created_at.isoformat() if t.created_at else None,
        "deleted_at":           t.deleted_at.isoformat() if t.deleted_at else None,
    }
