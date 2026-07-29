"""
Shipping Tariff Model
Stores product-level shipping costs imported from XLSX files.
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Index, UniqueConstraint, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class ShippingTariff(Base):
    """
    Shipping tariff entry per product.
    Populated from XLSX uploads with product SKU → shipping cost mapping.
    
    Fields:
    - product_id: Link to catalog product (nullable, match by SKU if missing)
    - sku_code: SKU to match if product_id is null
    - shipping_cost: Delivery charge in rupees
    - rto_handling_charge: Fixed RTO handling charge (default ₹50)
    - file_uploaded_at: When this tariff was uploaded
    """
    __tablename__ = "shipping_tariffs"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id           = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    product_id          = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    sku_code            = Column(String(100), nullable=True)
    shipping_cost       = Column(Numeric(10, 2), nullable=False, default=0)
    rto_handling_charge = Column(Numeric(10, 2), nullable=False, default=50)  # Fixed ₹50 charge
    file_uploaded_at    = Column(DateTime(timezone=True), nullable=True)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    product             = relationship("Product", back_populates="shipping_tariffs", foreign_keys=[product_id])
    tenant              = relationship("Tenant", back_populates="shipping_tariffs")

    # Indices
    __table_args__ = (
        Index("ix_shipping_tariffs_tenant_id", "tenant_id"),
        Index("ix_shipping_tariffs_product_id", "product_id"),
        Index("ix_shipping_tariffs_sku_code", "tenant_id", "sku_code"),
        Index("ix_shipping_tariffs_uploaded_at", "file_uploaded_at"),
        UniqueConstraint("tenant_id", "product_id", "sku_code", name="uq_shipping_tariff_tenant_product_sku"),
    )

    def __repr__(self):
        return f"<ShippingTariff(tenant={self.tenant_id}, sku={self.sku_code}, cost={self.shipping_cost})>"
