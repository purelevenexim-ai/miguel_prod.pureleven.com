import enum
import uuid
from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Numeric, Text, UniqueConstraint, Index,
    Boolean, Integer, Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class ProfitCostConfig(Base):
    __tablename__ = "profit_cost_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, unique=True)

    # Box rule examples:
    # {"small_cost": 10, "large_cost": 24, "large_min_items": 3, "large_min_weight_grams": 500}
    box_rule = Column(JSONB, nullable=False, default=lambda: {
        "small_cost": 10,
        "large_cost": 24,
        "large_min_items": 3,
        "large_min_weight_grams": 500,
    })

    # Pouch slabs examples:
    # [{"max_grams": 250, "cost": 0}, {"max_grams": 500, "cost": 0}, {"max_grams": 1000, "cost": 0}]
    pouch_slabs = Column(JSONB, nullable=False, default=lambda: [])

    # Sticker rule examples:
    # {"per_order": 0, "per_item": 0}
    sticker_rule = Column(JSONB, nullable=False, default=lambda: {
        "per_order": 0,
        "per_item": 0,
    })

    # Fee rule examples:
    # {"gateway_fee_pct": 0, "rto_loss_pct": 0}
    fee_rule = Column(JSONB, nullable=False, default=lambda: {
        "gateway_fee_pct": 0,
        "rto_loss_pct": 0,
    })

    note = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_profit_cost_config_tenant"),
        Index("ix_profit_cost_config_tenant", "tenant_id"),
    )


class ProfitMonthlyOverhead(Base):
    __tablename__ = "profit_monthly_overheads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    # Format: YYYY-MM
    month = Column(String(7), nullable=False)

    ads_cost = Column(Numeric(12, 2), nullable=False, default=0)
    dispatch_cost = Column(Numeric(12, 2), nullable=False, default=0)
    misc_cost = Column(Numeric(12, 2), nullable=False, default=0)
    other_fixed_cost = Column(Numeric(12, 2), nullable=False, default=0)

    # Manual cost inputs — no auto-data used for these
    shipping_cost = Column(Numeric(14, 2), nullable=False, default=0)  # actual shipping spend for the month
    gateway_fee = Column(Numeric(14, 2), nullable=False, default=0)    # payment gateway fee (typically 0 until configured)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "month", name="uq_profit_overhead_tenant_month"),
        Index("ix_profit_overhead_tenant_month", "tenant_id", "month"),
    )


class ProfitMonthlyPlanner(Base):
    __tablename__ = "profit_monthly_planner"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    # Format: YYYY-MM
    month = Column(String(7), nullable=False)

    revenue = Column(Numeric(14, 2), nullable=False, default=0)
    orders = Column(Numeric(14, 2), nullable=False, default=0)
    cogs = Column(Numeric(14, 2), nullable=False, default=0)
    returns_loss = Column(Numeric(14, 2), nullable=False, default=0)

    small_box_cost = Column(Numeric(14, 2), nullable=False, default=0)
    small_box_qty = Column(Numeric(14, 2), nullable=False, default=0)
    large_box_cost = Column(Numeric(14, 2), nullable=False, default=0)
    large_box_qty = Column(Numeric(14, 2), nullable=False, default=0)

    pouch_250_cost = Column(Numeric(14, 2), nullable=False, default=0)
    pouch_250_qty = Column(Numeric(14, 2), nullable=False, default=0)
    pouch_500_cost = Column(Numeric(14, 2), nullable=False, default=0)
    pouch_500_qty = Column(Numeric(14, 2), nullable=False, default=0)
    pouch_1kg_cost = Column(Numeric(14, 2), nullable=False, default=0)
    pouch_1kg_qty = Column(Numeric(14, 2), nullable=False, default=0)

    sticker_total = Column(Numeric(14, 2), nullable=False, default=0)
    indian_post_total = Column(Numeric(14, 2), nullable=False, default=0)
    delivery_convenience = Column(Numeric(14, 2), nullable=False, default=0)
    platform_gateway = Column(Numeric(14, 2), nullable=False, default=0)

    ads_monthly = Column(Numeric(14, 2), nullable=False, default=0)
    salary_monthly = Column(Numeric(14, 2), nullable=False, default=0)
    rent_utilities = Column(Numeric(14, 2), nullable=False, default=0)
    software_tools = Column(Numeric(14, 2), nullable=False, default=0)
    misc_monthly = Column(Numeric(14, 2), nullable=False, default=0)
    other_fixed = Column(Numeric(14, 2), nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "month", name="uq_profit_monthly_planner_tenant_month"),
        Index("ix_profit_monthly_planner_tenant_month", "tenant_id", "month"),
    )


class OrderProfitPosting(Base):
    __tablename__ = "order_profit_postings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, unique=True)

    month = Column(String(7), nullable=False)
    cost_source = Column(String(30), nullable=False, default="wac_or_catalog")

    product_cost = Column(Numeric(12, 2), nullable=False, default=0)
    box_cost = Column(Numeric(12, 2), nullable=False, default=0)
    pouch_cost = Column(Numeric(12, 2), nullable=False, default=0)
    sticker_cost = Column(Numeric(12, 2), nullable=False, default=0)
    packaging_cost = Column(Numeric(12, 2), nullable=False, default=0)
    courier_material_cost = Column(Numeric(12, 2), nullable=False, default=0)

    shipping_cost = Column(Numeric(12, 2), nullable=False, default=0)
    ads_allocated = Column(Numeric(12, 2), nullable=False, default=0)
    dispatch_allocated = Column(Numeric(12, 2), nullable=False, default=0)
    misc_allocated = Column(Numeric(12, 2), nullable=False, default=0)
    other_fixed_allocated = Column(Numeric(12, 2), nullable=False, default=0)

    gateway_fee = Column(Numeric(12, 2), nullable=False, default=0)
    rto_expected_loss = Column(Numeric(12, 2), nullable=False, default=0)

    total_cost = Column(Numeric(12, 2), nullable=False, default=0)
    profit = Column(Numeric(12, 2), nullable=False, default=0)
    margin_pct = Column(Numeric(7, 2), nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    order = relationship("Order", foreign_keys=[order_id])

    __table_args__ = (
        UniqueConstraint("tenant_id", "order_id", name="uq_order_profit_posting_tenant_order"),
        Index("ix_order_profit_posting_tenant_month", "tenant_id", "month"),
    )


# ═════════════════════════════════════════════════════════════
# PROFIT CHECKER — new transactional ledger (Phase 2)
# ═════════════════════════════════════════════════════════════

class PcGroupType(str, enum.Enum):
    product_purchase = "product_purchase"   # raw product / inventory purchases
    packaging        = "packaging"          # boxes, pouches, labels, stickers
    salary_ops       = "salary_ops"         # staff + operations
    ads_marketing    = "ads_marketing"      # ads & marketing spend
    sales            = "sales"              # sales revenue (read-only, from orders)
    custom           = "custom"             # any user-defined group


class PcAllocationType(str, enum.Enum):
    monthly   = "monthly"    # fixed or variable monthly cost
    per_order = "per_order"  # allocated per order (e.g. 1 box per 4 items)
    per_unit  = "per_unit"   # cost per unit sold


class PcAlertType(str, enum.Enum):
    negative_order = "negative_order"   # individual order has negative margin
    negative_month = "negative_month"   # whole month ended in loss
    low_margin_sku = "low_margin_sku"   # SKU below target margin
    low_margin_month = "low_margin_month"  # month margin below threshold


class ProfitCheckerGroup(Base):
    """
    Tenant-level expense category.
    Default groups are seeded on first use; custom groups are user-created.
    System groups cannot be deleted.
    """
    __tablename__ = "pc_groups"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id   = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    name        = Column(String(100), nullable=False)
    group_type  = Column(SAEnum(PcGroupType), nullable=False, default=PcGroupType.custom)
    # 'packing_material' → cost per product sold; 'courier_material' → cost per order dispatched
    sub_type    = Column(String(30), nullable=True)
    sort_order  = Column(Integer, nullable=False, default=100)
    is_system   = Column(Boolean, nullable=False, default=False)   # cannot be deleted
    is_active   = Column(Boolean, nullable=False, default=True)

    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    items       = relationship("ProfitCheckerGroupItem", back_populates="group",
                               cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_pc_groups_tenant_id", "tenant_id"),
        UniqueConstraint("tenant_id", "name", name="uq_pc_group_tenant_name"),
    )


class ProfitCheckerGroupItem(Base):
    """
    A configurable cost line item inside a ProfitCheckerGroup.
    Can optionally be backed by a catalog product (e.g. a corrugated box product).
    """
    __tablename__ = "pc_group_items"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id       = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    group_id        = Column(UUID(as_uuid=True), ForeignKey("pc_groups.id"), nullable=False)

    name            = Column(String(100), nullable=False)
    allocation_type = Column(SAEnum(PcAllocationType), nullable=False, default=PcAllocationType.monthly)

    # Optional link to a catalog product (e.g. corrugated box)
    product_id      = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    # For per_order allocation: how many items in an order triggers one unit of this item
    # e.g. items_per_trigger=4 means 1 box per 4 ordered items
    items_per_trigger = Column(Numeric(6, 2), nullable=True)

    is_active       = Column(Boolean, nullable=False, default=True)
    sort_order      = Column(Integer, nullable=False, default=100)

    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    group           = relationship("ProfitCheckerGroup", back_populates="items")

    __table_args__ = (
        Index("ix_pc_group_items_tenant_group", "tenant_id", "group_id"),
    )


class ProfitCheckerEntry(Base):
    """
    Actual expense entry for a group (and optionally a group item) in a specific month.
    Product Purchase entries are typically auto-linked from received Purchase Orders.
    Other entries (salary, ads, rent) are entered manually or imported.
    """
    __tablename__ = "pc_entries"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id       = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    group_id        = Column(UUID(as_uuid=True), ForeignKey("pc_groups.id"), nullable=False)
    item_id         = Column(UUID(as_uuid=True), ForeignKey("pc_group_items.id"), nullable=True)

    # Format: YYYY-MM
    month           = Column(String(7), nullable=False)
    description     = Column(String(255), nullable=False)   # was 'label'

    amount          = Column(Numeric(14, 2), nullable=False, default=0)
    quantity        = Column(Numeric(12, 3), nullable=True)    # e.g. 50 kg
    unit_cost       = Column(Numeric(12, 2), nullable=True)    # e.g. ₹200/kg

    # Optional link to a product being purchased (for product_purchase entries)
    # for product_purchase entries only
    product_id      = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)

    # For packing material entries: sellable product categories this material applies to.
    # Stored on the entry because packing applicability is entered together with the cost pool.
    applicable_categories = Column(JSONB, nullable=True)

    # For packing/courier material entries:
    #   packing_material entry → units consumed per product unit sold
    #   courier_material entry → units consumed per order dispatched
    consumption_rate = Column(Numeric(10, 4), nullable=True)

    # Optional link to a received Purchase Order for auto-population
    reference_po_id = Column(UUID(as_uuid=True), ForeignKey("purchase_orders.id"), nullable=True)
    note            = Column(Text, nullable=True)

    created_by_id   = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_pc_entries_tenant_month", "tenant_id", "month"),
        Index("ix_pc_entries_group_id", "group_id"),
        Index("ix_pc_entries_po_id", "reference_po_id"),
    )


class ProfitCheckerProductMap(Base):
    """
    Maps a raw / bulk purchased product to one or more sellable variant products.
    Used for carry-forward inventory calculation: consumption of sellable variants
    depletes the mapped raw material stock.

    Example: "Cardamom Bulk (raw_material)" → "Cardamom 100g", "Cardamom 200g", "Cardamom 500g"
    Uses 1:1 base-unit conversion (1 gram sold = 1 gram deducted from bulk).
    """
    __tablename__ = "pc_product_maps"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id           = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    source_product_id   = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    target_product_id   = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)

    # Conversion ratio for base-unit matching (default 1.0 for same base unit).
    # e.g. 1kg bulk → 1kg total packaged, regardless of pack size.
    conversion_ratio    = Column(Numeric(10, 6), nullable=False, default=1.0)
    is_active           = Column(Boolean, nullable=False, default=True)

    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "source_product_id", "target_product_id",
                         name="uq_pc_product_map_src_tgt"),
        Index("ix_pc_product_maps_tenant_source", "tenant_id", "source_product_id"),
    )


class ProfitCheckerPeriodSnapshot(Base):
    """
    Computed P&L snapshot for a period (monthly / quarterly / yearly).
    Persisted so historical months remain stable even when costs change.
    Quarterly and yearly snapshots are derived by summing monthly snapshots.
    """
    __tablename__ = "pc_period_snapshots"

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id               = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    # For monthly: "2026-05".  For quarterly: "2026-Q2".  For yearly: "2026".
    period                  = Column(String(10), nullable=False)
    period_type             = Column(String(10), nullable=False, default="monthly")  # monthly|quarterly|yearly

    # ── Sales ──────────────────────────────────────────────
    sales_revenue           = Column(Numeric(14, 2), nullable=False, default=0)
    order_count             = Column(Integer, nullable=False, default=0)

    # ── Cost buckets ──────────────────────────────────────
    cogs                    = Column(Numeric(14, 2), nullable=False, default=0)   # product cost from OrderProfitPosting
    packaging_cost          = Column(Numeric(14, 2), nullable=False, default=0)
    courier_material_cost   = Column(Numeric(14, 2), nullable=False, default=0)
    shipping_cost           = Column(Numeric(14, 2), nullable=False, default=0)   # shipping from OrderProfitPosting
    gateway_fee             = Column(Numeric(14, 2), nullable=False, default=0)   # payment gateway fee from OrderProfitPosting
    rto_loss                = Column(Numeric(14, 2), nullable=False, default=0)   # RTO expected loss from OrderProfitPosting
    salary_ops_cost         = Column(Numeric(14, 2), nullable=False, default=0)
    ads_marketing_cost      = Column(Numeric(14, 2), nullable=False, default=0)
    other_cost              = Column(Numeric(14, 2), nullable=False, default=0)
    total_expense           = Column(Numeric(14, 2), nullable=False, default=0)

    # ── Inventory ─────────────────────────────────────────
    opening_stock_value     = Column(Numeric(14, 2), nullable=False, default=0)
    closing_stock_value     = Column(Numeric(14, 2), nullable=False, default=0)
    purchases_value         = Column(Numeric(14, 2), nullable=False, default=0)

    # ── Profit ────────────────────────────────────────────
    gross_profit            = Column(Numeric(14, 2), nullable=False, default=0)   # revenue - cogs
    net_profit              = Column(Numeric(14, 2), nullable=False, default=0)   # gross_profit - other expenses
    margin_pct              = Column(Numeric(7, 2), nullable=False, default=0)

    # ── Group breakdown (JSONB for flexibility) ────────────
    group_totals            = Column(JSONB, nullable=True)   # {group_id: total_amount}

    is_locked               = Column(Boolean, nullable=False, default=False)
    computed_at             = Column(DateTime(timezone=True), server_default=func.now())
    created_at              = Column(DateTime(timezone=True), server_default=func.now())
    updated_at              = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "period", "period_type",
                         name="uq_pc_snapshot_tenant_period_type"),
        Index("ix_pc_period_snapshots_tenant_period", "tenant_id", "period"),
    )


class ProfitCheckerAlert(Base):
    """
    Persisted alerts raised when a sale or period is unprofitable.
    Dismissed manually from the Profit Checker UI.
    """
    __tablename__ = "pc_alerts"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id       = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    alert_type      = Column(SAEnum(PcAlertType), nullable=False)
    reference_id    = Column(UUID(as_uuid=True), nullable=True)   # order_id or product_id
    month           = Column(String(7), nullable=False)           # YYYY-MM
    message         = Column(Text, nullable=False)
    severity        = Column(String(10), nullable=False, default="warning")  # critical | warning

    is_dismissed    = Column(Boolean, nullable=False, default=False)
    dismissed_at    = Column(DateTime(timezone=True), nullable=True)
    dismissed_by_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True)

    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_pc_alerts_tenant_month", "tenant_id", "month"),
        Index("ix_pc_alerts_tenant_dismissed", "tenant_id", "is_dismissed"),
    )

