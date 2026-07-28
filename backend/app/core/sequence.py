"""
Safe Sequential Code Generator
--------------------------------
Uses SELECT FOR UPDATE with row-level locking to avoid race conditions
when generating sequential codes for customers, orders, leads.

All generators use a per-tenant approach:
  COUNT(*) under advisory lock so two concurrent requests never get the same code.

PostgreSQL advisory locks guarantee safety even under parallel requests.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from uuid import UUID


def _advisory_lock_id(tenant_id: "UUID", resource: str) -> int:
    """
    Convert (tenant_id, resource) to a stable 64-bit int for pg_advisory_xact_lock.
    Uses the first 6 hex chars of tenant UUID XOR'd with a resource seed.
    """
    seeds = {"customer": 1, "lead": 2, "order": 3}
    seed = seeds.get(resource, 4)
    # Take first 15 hex chars of UUID (without dashes) as int, then mask to 63 bits
    raw = str(tenant_id).replace("-", "")[:15]
    return (int(raw, 16) ^ (seed * 0xDEADBEEF)) & 0x7FFFFFFFFFFFFFFF


def next_customer_code(db: "Session", tenant_id: "UUID") -> str:
    """
    Thread-safe customer code: CUST-00001, CUST-00002, ...
    Acquires a session-level advisory lock per tenant so concurrent
    requests cannot grab the same number.
    """
    from app.models.customer import Customer
    lock_id = _advisory_lock_id(tenant_id, "customer")
    db.execute(text(f"SELECT pg_advisory_xact_lock({lock_id})"))
    count = db.query(Customer).filter(Customer.tenant_id == tenant_id).count()
    return f"CUST-{str(count + 1).zfill(5)}"


def next_lead_number(db: "Session", tenant_id: "UUID") -> str:
    """
    Thread-safe lead number: LEAD-00001, LEAD-00002, ...
    """
    from app.models.lead import Lead
    from sqlalchemy import func
    lock_id = _advisory_lock_id(tenant_id, "lead")
    db.execute(text(f"SELECT pg_advisory_xact_lock({lock_id})"))
    count = (
        db.query(func.count(Lead.id))
        .filter(Lead.tenant_id == tenant_id)
        .scalar()
    ) or 0
    return f"LEAD-{str(count + 1).zfill(5)}"


def next_order_number(db: "Session", tenant_id: "UUID", slug: str = "") -> str:
    """
    Thread-safe order number: PLX-260225-001, PLX-260225-002, ...

    Uses a tenant-wide continuous suffix (no daily reset):
    ...-001, ...-002, ...-003 ... ...-10000

    The date segment remains for readability, but suffix allocation is global
    for the tenant and always max+1, so it never restarts at 001 each day.
    """
    import re

    lock_id = _advisory_lock_id(tenant_id, "order")
    db.execute(text(f"SELECT pg_advisory_xact_lock({lock_id})"))

    # Derive prefix from slug
    if slug:
        s = slug.upper().replace("-", "").replace("_", "")
        consonants = re.sub(r'[AEIOU0-9]', '', s)
        if len(consonants) >= 3:
            prefix = consonants[0] + consonants[1] + consonants[-1]
        else:
            prefix = s[:3] if len(s) >= 3 else s.ljust(3, 'X')
    else:
        prefix = "ORD"

    date_str = datetime.now(timezone.utc).strftime("%y%m%d")
    today_prefix = f"{prefix}-{date_str}-"

    # Fetch the maximum numeric suffix already used for this tenant/prefix.
    row = db.execute(
        text(
            "SELECT COALESCE(MAX(CAST(substring(order_number from '([0-9]+)$') AS INTEGER)), 0) "
            "FROM orders "
            "WHERE tenant_id = CAST(:tid AS UUID) "
            "AND order_number LIKE :prefix"
        ),
        {"tid": str(tenant_id), "prefix": f"{prefix}-%"},
    ).scalar()

    next_seq = int(row or 0) + 1

    seq = str(next_seq).zfill(3)
    return f"{today_prefix}{seq}"
