import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    company_name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)

    contact_person_name = Column(String(255), nullable=False)
    contact_phone = Column(String(20), nullable=True)
    owner_email = Column(String(255), nullable=False)

    # ── Branding / Contact ────────────────────────────────
    logo_url     = Column(String, nullable=True)
    slogan       = Column(String(255), nullable=True)
    phone        = Column(String(30), nullable=True)
    email        = Column(String(255), nullable=True)
    address_line1 = Column(String, nullable=True)
    address_line2 = Column(String, nullable=True)

    # ── GST / Accounting fields ───────────────────────────
    gstin        = Column(String(15), nullable=True)          # Tenant's own GSTIN
    gst_state    = Column(String(100), nullable=True)         # Home state for CGST/SGST vs IGST
    gst_address  = Column(String, nullable=True)              # Registered address
    gst_city     = Column(String(100), nullable=True)
    gst_pincode  = Column(String(10), nullable=True)

    # ── Banking ───────────────────────────────────────────
    bank_name    = Column(String(100), nullable=True)
    bank_account = Column(String(30), nullable=True)
    bank_ifsc    = Column(String(20), nullable=True)
    bank_branch  = Column(String(100), nullable=True)
    upi_id       = Column(String(100), nullable=True)

    # ── Invoice Numbering Prefixes ────────────────────────
    invoice_prefix  = Column(String(10), nullable=True, default="INV")
    proforma_prefix = Column(String(10), nullable=True, default="PRF")
    bill_prefix     = Column(String(10), nullable=True, default="BILL")

    # ── Label Customization ────────────────────────────────
    label_show_logo    = Column(Boolean, default=True)
    label_show_slogan  = Column(Boolean, default=True)
    label_show_barcode = Column(Boolean, default=False)
    label_footer_note  = Column(String, nullable=True)

    # ── Template JSON configs (label & invoice editors) ────
    label_template     = Column(JSONB, nullable=True)     # full drag-drop label config
    invoice_template   = Column(JSONB, nullable=True)     # full drag-drop invoice config

    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationship
    employees = relationship("Employee", back_populates="tenant")
    shipping_tariffs = relationship("ShippingTariff", back_populates="tenant")
