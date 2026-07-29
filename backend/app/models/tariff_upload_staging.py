"""
TariffUploadStaging model
Holds rows parsed from a shipment XLSX before any writes reach the orders table.
Rows graduate to orders only after explicit user approval.
"""
import uuid
from sqlalchemy import (
    Column, String, Integer, Boolean, Text, DateTime,
    Numeric, ForeignKey, Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class TariffUploadStaging(Base):
    """
    One row = one row from the uploaded XLSX.

    Lifecycle:
        parsed  →  pending  →  approved / rejected  →  applied
                                                      (writes orders.shipping_charge / tracking_number)
    """
    __tablename__ = "tariff_upload_staging"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id        = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    upload_batch_id  = Column(UUID(as_uuid=True), nullable=False)   # groups rows from the same file
    uploaded_by      = Column(UUID(as_uuid=True), nullable=True)    # employee who uploaded
    xlsx_row_num     = Column(Integer, nullable=True)

    # ── Raw data from the XLSX row ──────────────────────────────────────────
    xlsx_tracking      = Column(String(60),  nullable=True)
    xlsx_order_ref     = Column(String(80),  nullable=True)
    xlsx_customer_name = Column(String(200), nullable=True)
    xlsx_amount        = Column(Numeric(10, 2), nullable=True)
    xlsx_weight        = Column(Numeric(10, 3), nullable=True)
    xlsx_status_text   = Column(String(200), nullable=True)

    # ── Match result ────────────────────────────────────────────────────────
    order_id        = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    order_number    = Column(String(80), nullable=True)
    #   tracking_exact | order_number_exact | name_amount_close | pincode_match | sku_fallback | unmatched
    match_method    = Column(String(40), nullable=True)
    #   high | medium | low | none
    confidence      = Column(String(10), nullable=False, default="none")

    # ── Validation gates ────────────────────────────────────────────────────
    tracking_valid    = Column(Boolean, nullable=False, default=False)
    amount_valid      = Column(Boolean, nullable=False, default=False)
    amount_suspicious = Column(Boolean, nullable=False, default=False)

    # ── Diff: current values on the order vs proposed new values ───────────
    current_tracking  = Column(String(60),     nullable=True)
    proposed_tracking = Column(String(60),     nullable=True)
    current_shipping  = Column(Numeric(10, 2), nullable=True)
    proposed_shipping = Column(Numeric(10, 2), nullable=True)

    # ── Review state ────────────────────────────────────────────────────────
    #   pending | approved | rejected | applied | apply_error
    review_status    = Column(String(20), nullable=False, default="pending")
    reviewed_by      = Column(UUID(as_uuid=True), nullable=True)
    reviewed_at      = Column(DateTime(timezone=True), nullable=True)
    applied_at       = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    apply_error      = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # ── Relationships (read-only convenience) ───────────────────────────────
    order  = relationship("Order",  foreign_keys=[order_id],  lazy="select")
    tenant = relationship("Tenant", foreign_keys=[tenant_id], lazy="select")

    __table_args__ = (
        Index("ix_tus_tenant_batch",  "tenant_id", "upload_batch_id"),
        Index("ix_tus_order_id",      "order_id"),
        Index("ix_tus_review_status", "tenant_id", "review_status"),
    )

    def to_dict(self) -> dict:
        return {
            "id":               str(self.id),
            "upload_batch_id":  str(self.upload_batch_id),
            "xlsx_row_num":     self.xlsx_row_num,
            "xlsx_tracking":    self.xlsx_tracking,
            "xlsx_order_ref":   self.xlsx_order_ref,
            "xlsx_customer_name": self.xlsx_customer_name,
            "xlsx_amount":      float(self.xlsx_amount) if self.xlsx_amount is not None else None,
            "xlsx_status_text": self.xlsx_status_text,
            "order_id":         str(self.order_id) if self.order_id else None,
            "order_number":     self.order_number,
            "match_method":     self.match_method,
            "confidence":       self.confidence,
            "tracking_valid":   self.tracking_valid,
            "amount_valid":     self.amount_valid,
            "amount_suspicious": self.amount_suspicious,
            "current_tracking":  self.current_tracking,
            "proposed_tracking": self.proposed_tracking,
            "current_shipping":  float(self.current_shipping) if self.current_shipping is not None else None,
            "proposed_shipping": float(self.proposed_shipping) if self.proposed_shipping is not None else None,
            "review_status":    self.review_status,
            "rejection_reason": self.rejection_reason,
            "apply_error":      self.apply_error,
            "applied_at":       self.applied_at.isoformat() if self.applied_at else None,
            "created_at":       self.created_at.isoformat() if self.created_at else None,
        }
