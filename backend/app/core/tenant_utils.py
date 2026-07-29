"""
Tenant Isolation Utility
-------------------------
Used in ALL tenant-scoped queries to enforce data isolation.

Every list/get query in customers, orders, leads etc.
MUST pass through apply_tenant_filter().
"""

from sqlalchemy.orm import Query
from fastapi import HTTPException, status


def apply_tenant_filter(query: Query, model, current_user) -> Query:
    """
    Applies tenant_id filter to any SQLAlchemy query.

    - SuperAdmin (platform): no filtering, sees all
    - Tenant employee: filtered strictly by their tenant_id

    Usage:
        query = db.query(Customer)
        query = apply_tenant_filter(query, Customer, current_user)
        results = query.all()
    """
    role = getattr(current_user, "role", None)

    # Platform SuperAdmin — bypass tenant filter
    if isinstance(role, str) and role == "superadmin":
        return query

    # Tenant employee — must have tenant_id
    tenant_id = getattr(current_user, "tenant_id", None)

    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant context missing from token",
        )

    return query.filter(model.tenant_id == tenant_id)


def assert_tenant_ownership(record, current_user):
    """
    Verifies a single record belongs to the current user's tenant.
    Used for GET /resource/{id} endpoints.

    Raises 404 if not found or belongs to another tenant.
    """
    role = getattr(current_user, "role", None)

    # SuperAdmin can access anything
    if isinstance(role, str) and role == "superadmin":
        return

    tenant_id = getattr(current_user, "tenant_id", None)

    if str(getattr(record, "tenant_id", None)) != str(tenant_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record not found",
        )


# ─────────────────────────────────────────────────────────────
# Tenant sender/FROM-address helper (used by label generators)
# ─────────────────────────────────────────────────────────────

def get_tenant_label_fields(tenant) -> dict:
    """
    Return a dict of sender fields for shipping labels, read from the
    tenant profile.  All fields fall back to empty string if not set —
    the PDF generator then simply omits blank lines.

    Keys returned:
        from_name, from_address, from_pincode, from_phone, slogan, logo_url
    """
    if tenant is None:
        return {
            "from_name": "", "from_address": "", "from_pincode": "",
            "from_phone": "", "slogan": "", "logo_url": "",
        }

    # Build address from available fields (address_line1/2 preferred,
    # fall back to gst_address)
    parts = []
    if getattr(tenant, "address_line1", None):
        parts.append(tenant.address_line1.strip())
    if getattr(tenant, "address_line2", None):
        parts.append(tenant.address_line2.strip())
    city  = (getattr(tenant, "gst_city",  None) or "").strip()
    state = (getattr(tenant, "gst_state", None) or "").strip()
    if city and state:
        parts.append(f"{city}, {state}")
    elif city:
        parts.append(city)
    elif state:
        parts.append(state)

    address = ", ".join(parts) if parts else (getattr(tenant, "gst_address", None) or "").strip()

    return {
        "from_name":    (tenant.company_name or "").strip(),
        "from_address": address,
        "from_pincode": (getattr(tenant, "gst_pincode", None) or "").strip(),
        "from_phone":   (getattr(tenant, "phone",       None) or "").strip(),
        "slogan":       (getattr(tenant, "slogan",      None) or "").strip(),
        "logo_url":     (getattr(tenant, "logo_url",    None) or ""),
    }
