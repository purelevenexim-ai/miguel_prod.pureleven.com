"""
ActivityLog Model
──────────────────
- One table for ALL tenant operations
- Scoped by tenant_id (multi-tenant safe)
- Auto-expires after 6 hours (TTL enforced at query level + cleanup job)
- SuperAdmin-only read access via platform routes
- Never exposed to employees or tenants
"""

import enum
import uuid
from sqlalchemy import (
    Column, String, Text, DateTime, Enum, Index,
    ForeignKey, Integer
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from .base import Base


class LogLevel(str, enum.Enum):
    INFO    = "INFO"
    WARNING = "WARNING"
    ERROR   = "ERROR"
    CRITICAL = "CRITICAL"


class LogModule(str, enum.Enum):
    AUTH        = "auth"
    ORDERS      = "orders"
    CUSTOMERS   = "customers"
    LEADS       = "leads"
    PRODUCTS    = "products"
    INVENTORY   = "inventory"
    INVOICES    = "invoices"
    VENDORS     = "vendors"
    PURCHASES   = "purchases"
    LABELS      = "labels"
    META        = "meta"
    REPORTING   = "reporting"
    EMPLOYEES   = "employees"
    PLATFORM    = "platform"
    SYSTEM      = "system"


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ── Tenant scoping ─────────────────────────────────────────
    tenant_id   = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
                         nullable=True, index=True)
    # nullable=True → platform-level events (login, tenant create) have no tenant_id

    # ── Actor ─────────────────────────────────────────────────
    actor_id    = Column(UUID(as_uuid=True), nullable=True)   # employee_id or platform user id
    actor_email = Column(String(255), nullable=True)
    actor_role  = Column(String(50), nullable=True)           # admin/sales/superadmin etc.
    actor_ip    = Column(String(45), nullable=True)           # IPv4 or IPv6

    # ── Action classification ──────────────────────────────────
    module      = Column(Enum(LogModule), nullable=False, index=True)
    action      = Column(String(100), nullable=False, index=True)
    # e.g. "order.create", "order.status_advance", "customer.create",
    #      "auth.login_success", "auth.login_failed", "inventory.reduce"

    # ── Outcome ───────────────────────────────────────────────
    level       = Column(Enum(LogLevel), nullable=False, default=LogLevel.INFO, index=True)
    status_code = Column(Integer, nullable=True)              # HTTP status if applicable
    message     = Column(Text, nullable=True)                 # Human-readable summary
    detail      = Column(JSONB, nullable=True)
    # detail stores structured context: order_id, old_status, new_status, error msg, etc.

    # ── Request context ────────────────────────────────────────
    method      = Column(String(10), nullable=True)           # GET/POST/PATCH/DELETE
    path        = Column(String(500), nullable=True)          # /api/orders/
    user_agent  = Column(Text, nullable=True)

    # ── Error Diagnostics ──────────────────────────────────────
    error_code  = Column(String(50), nullable=True, index=True)  # ERR-<timestamp>-<hash>

    # ── Timestamp ─────────────────────────────────────────────
    created_at  = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    # TTL: rows older than 6 hours are pruned by the cleanup job
    # expires_at is computed = created_at + 6h (stored for fast range deletes)
    expires_at  = Column(DateTime(timezone=True), nullable=False, index=True)

    __table_args__ = (
        # Fast queries: all logs for a tenant sorted by time
        Index("ix_actlog_tenant_created", "tenant_id", "created_at"),
        # Fast queries: filter by level within a tenant
        Index("ix_actlog_tenant_level", "tenant_id", "level"),
        # Fast expiry cleanup
        Index("ix_actlog_expires", "expires_at"),
    )
