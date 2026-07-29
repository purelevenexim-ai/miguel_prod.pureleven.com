"""
Courier & India Post Configuration Service
-------------------------------------------
Tenant admin manages:
- Courier partners (add / enable / disable)
- India Post Customer IDs (multiple per tenant, one default)
"""
from __future__ import annotations
import uuid as _uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.order import Courier, IndiaPostCustomerId
from app.models.employee import Employee
from app.core.tenant_utils import apply_tenant_filter


# ─────────────────────────────────────────────────────────────
# Couriers
# ─────────────────────────────────────────────────────────────

def list_couriers(db: Session, current_user: Employee) -> list[Courier]:
    return (
        db.query(Courier)
        .filter(Courier.tenant_id == current_user.tenant_id)
        .order_by(Courier.is_default.desc(), Courier.name)
        .all()
    )


def create_courier(db: Session, data: dict, current_user: Employee) -> Courier:
    # If setting as default, unset existing default
    if data.get("is_default"):
        db.query(Courier).filter(
            Courier.tenant_id == current_user.tenant_id,
            Courier.is_default == True,
        ).update({"is_default": False})

    courier = Courier(
        id=_uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        name=data["name"],
        code=data["code"].upper(),
        is_active=data.get("is_active", True),
        is_default=data.get("is_default", False),
        notes=data.get("notes"),
    )
    db.add(courier)
    db.commit()
    db.refresh(courier)
    return courier


def update_courier(db: Session, courier_id: str, data: dict, current_user: Employee) -> Courier:
    courier = db.query(Courier).filter(
        Courier.id == courier_id,
        Courier.tenant_id == current_user.tenant_id,
    ).first()
    if not courier:
        raise HTTPException(status_code=404, detail="Courier not found")

    if data.get("is_default"):
        db.query(Courier).filter(
            Courier.tenant_id == current_user.tenant_id,
            Courier.is_default == True,
        ).update({"is_default": False})

    for k, v in data.items():
        if hasattr(courier, k):
            setattr(courier, k, v)

    db.commit()
    db.refresh(courier)
    return courier


def delete_courier(db: Session, courier_id: str, current_user: Employee) -> dict:
    courier = db.query(Courier).filter(
        Courier.id == courier_id,
        Courier.tenant_id == current_user.tenant_id,
    ).first()
    if not courier:
        raise HTTPException(status_code=404, detail="Courier not found")
    db.delete(courier)
    db.commit()
    return {"message": f"Courier {courier.name} deleted"}


# ─────────────────────────────────────────────────────────────
# India Post Customer IDs
# ─────────────────────────────────────────────────────────────

def list_ip_customer_ids(db: Session, current_user: Employee) -> list[IndiaPostCustomerId]:
    return (
        db.query(IndiaPostCustomerId)
        .filter(
            IndiaPostCustomerId.tenant_id == current_user.tenant_id,
            IndiaPostCustomerId.is_active == True,
        )
        .order_by(IndiaPostCustomerId.is_default.desc(), IndiaPostCustomerId.label)
        .all()
    )


def create_ip_customer_id(db: Session, data: dict, current_user: Employee) -> IndiaPostCustomerId:
    if data.get("is_default"):
        db.query(IndiaPostCustomerId).filter(
            IndiaPostCustomerId.tenant_id == current_user.tenant_id,
            IndiaPostCustomerId.is_default == True,
        ).update({"is_default": False})

    rec = IndiaPostCustomerId(
        id=_uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        customer_id=data["customer_id"],
        label=data.get("label"),
        is_default=data.get("is_default", False),
        is_active=data.get("is_active", True),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def update_ip_customer_id(db: Session, rec_id: str, data: dict, current_user: Employee) -> IndiaPostCustomerId:
    rec = db.query(IndiaPostCustomerId).filter(
        IndiaPostCustomerId.id == rec_id,
        IndiaPostCustomerId.tenant_id == current_user.tenant_id,
    ).first()
    if not rec:
        raise HTTPException(status_code=404, detail="India Post Customer ID not found")

    if data.get("is_default"):
        db.query(IndiaPostCustomerId).filter(
            IndiaPostCustomerId.tenant_id == current_user.tenant_id,
            IndiaPostCustomerId.is_default == True,
        ).update({"is_default": False})

    for k, v in data.items():
        if hasattr(rec, k):
            setattr(rec, k, v)

    db.commit()
    db.refresh(rec)
    return rec


def delete_ip_customer_id(db: Session, rec_id: str, current_user: Employee) -> dict:
    rec = db.query(IndiaPostCustomerId).filter(
        IndiaPostCustomerId.id == rec_id,
        IndiaPostCustomerId.tenant_id == current_user.tenant_id,
    ).first()
    if not rec:
        raise HTTPException(status_code=404, detail="India Post Customer ID not found")
    rec.is_active = False
    db.commit()
    return {"message": "India Post Customer ID deactivated"}


# ─────────────────────────────────────────────────────────────
# Seed default India Post courier for a tenant (call on setup)
# ─────────────────────────────────────────────────────────────

def seed_default_couriers(db: Session, tenant_id) -> None:
    """Called when tenant is first set up — adds India Post as default courier."""
    existing = db.query(Courier).filter(Courier.tenant_id == tenant_id).count()
    if existing:
        return
    defaults = [
        {"name": "India Post", "code": "INDIA_POST", "is_default": True},
        {"name": "DTDC",       "code": "DTDC",       "is_default": False},
        {"name": "Blue Dart",  "code": "BLUEDART",   "is_default": False},
        {"name": "Delhivery",  "code": "DELHIVERY",  "is_default": False},
        {"name": "Ekart",      "code": "EKART",      "is_default": False},
    ]
    for d in defaults:
        c = Courier(
            id=_uuid.uuid4(),
            tenant_id=tenant_id,
            name=d["name"],
            code=d["code"],
            is_default=d["is_default"],
            is_active=True,
        )
        db.add(c)
    db.commit()
