"""Shipping tariff service for parsing and managing XLSX tariff files."""

import uuid
from io import BytesIO
from typing import List, Dict, Tuple
from decimal import Decimal
from datetime import datetime

from openpyxl import load_workbook
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.shipping_tariff import ShippingTariff
from app.models.product import Product
from app.database.session import get_db


class TariffParseError(Exception):
    """Raised when tariff file parsing fails."""
    pass


def _sku_compare_key(value) -> str:
    import re

    text = str(value or "").strip().upper()
    if not text:
        return ""
    return re.sub(r"[^A-Z0-9]+", "", text)


class ShippingTariffService:
    """Service for parsing and managing shipping tariffs from XLSX files."""

    @staticmethod
    def parse_tariff_xlsx(
        file_content: bytes,
        tenant_id: str,
        db: Session
    ) -> Tuple[List[Dict], List[str]]:
        """
        Parse XLSX tariff file and return tariff records and any errors.

        Expected XLSX structure:
        - Sheet name: "tariff_raw"
        - Columns: SKU (A), Shipping Cost (B), [optional: Product Name (C), Courier (D)]
        - Header row: Row 1
        - Data rows: Row 2 onwards

        Args:
            file_content: Raw bytes of XLSX file
            tenant_id: UUID of the tenant
            db: SQLAlchemy session

        Returns:
            Tuple of (tariff_records, error_messages)
            - tariff_records: List of dicts with keys: sku_code, product_id, shipping_cost, warnings
            - error_messages: List of validation errors (file-level issues)
        """
        errors = []
        tariff_records = []

        try:
            def _norm_header(value) -> str:
                text = str(value or "").strip().lower()
                text = text.replace("_", " ").replace("-", " ")
                return " ".join(text.split())

            def _norm_sku(value) -> str:
                text = str(value or "").strip()
                if not text:
                    return ""
                return " ".join(text.split()).upper()

            def _find_col(header_map: Dict[str, int], aliases: List[str]):
                for alias in aliases:
                    idx = header_map.get(alias)
                    if idx is not None:
                        return idx
                return None

            def _score_numeric_col(ws, col_idx: int, sample_rows: int = 30) -> float:
                total = 0
                numeric = 0
                max_row = min(ws.max_row or 1, sample_rows + 1)
                for row in ws.iter_rows(min_row=2, max_row=max_row, values_only=True):
                    if (col_idx - 1) >= len(row):
                        continue
                    value = row[col_idx - 1]
                    if value is None or str(value).strip() == "":
                        continue
                    total += 1
                    if _to_numeric(value) is not None:
                        numeric += 1
                return (numeric / total) if total > 0 else 0.0

            def _to_numeric(value):
                if value is None:
                    return None
                if isinstance(value, (int, float)):
                    return float(value)

                text = str(value).strip()
                if not text:
                    return None

                # Allow formats like "1,234.50", "Rs 99", "INR 120.00"
                cleaned = text.lower().replace(",", "")
                for token in ("rs.", "rs", "inr", "rupees", "rupee", "\u20b9"):
                    cleaned = cleaned.replace(token, "")
                cleaned = cleaned.strip()

                try:
                    return float(cleaned)
                except (ValueError, TypeError):
                    return None

            # Load workbook from bytes
            workbook = load_workbook(BytesIO(file_content))

            sku_aliases = [
                "sku", "sku code", "product sku", "product code", "sku id", "item sku",
            ]
            shipping_cost_aliases = [
                "shipping cost", "shipping charge", "shipping charges", "shipping", "courier charge",
                "courier cost", "freight", "tariff", "shipping amount",
            ]
            product_name_aliases = [
                "product name", "name", "item name", "product",
            ]
            courier_aliases = [
                "courier", "carrier", "delivery partner", "service", "logistics",
            ]

            selected_sheet_name = None
            sheet = None
            headers: Dict[str, int] = {}
            sku_col = None
            shipping_cost_col = None

            candidate_sheets = ["tariff_raw"] + [s for s in workbook.sheetnames if s != "tariff_raw"]

            for sheet_name in candidate_sheets:
                if sheet_name not in workbook.sheetnames:
                    continue

                ws = workbook[sheet_name]
                header_map: Dict[str, int] = {}
                for col_idx, cell in enumerate(ws[1], 1):
                    norm = _norm_header(cell.value)
                    if norm:
                        header_map[norm] = col_idx

                local_sku_col = _find_col(header_map, sku_aliases)
                local_cost_col = _find_col(header_map, shipping_cost_aliases)

                # Heuristic: pick the most numeric-looking shipping-like column.
                cost_candidates: List[int] = []
                if local_cost_col is not None:
                    cost_candidates.append(local_cost_col)
                for header_name, idx in header_map.items():
                    if any(tok in header_name for tok in ("shipping", "charge", "cost", "tariff", "freight", "courier")):
                        if idx not in cost_candidates:
                            cost_candidates.append(idx)

                if cost_candidates:
                    best_idx = None
                    best_score = -1.0
                    for idx in cost_candidates:
                        score = _score_numeric_col(ws, idx)
                        if score > best_score:
                            best_idx = idx
                            best_score = score
                    # Only override when column has meaningful numeric signal.
                    if best_idx is not None and best_score >= 0.40:
                        local_cost_col = best_idx

                if local_sku_col is not None and local_cost_col is not None:
                    selected_sheet_name = sheet_name
                    sheet = ws
                    headers = header_map
                    sku_col = local_sku_col
                    shipping_cost_col = local_cost_col
                    break

            if sheet is None:
                errors.append(
                    "Could not detect tariff data. Required columns not found together: "
                    "SKU + Shipping Cost (or aliases)"
                )
                errors.append(f"Available sheets: {workbook.sheetnames}")
                return [], errors

            if selected_sheet_name != "tariff_raw":
                errors.append(
                    f"Using sheet '{selected_sheet_name}' because 'tariff_raw' was not suitable"
                )

            product_name_col = _find_col(headers, product_name_aliases)
            courier_col = _find_col(headers, courier_aliases)

            # Parse data rows (skip header)
            product_cache = {}  # Cache SKU -> Product mapping

            for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=False), start=2):
                sku_cell = row[sku_col - 1]
                shipping_cost_cell = row[shipping_cost_col - 1]

                sku = _norm_sku(sku_cell.value)
                shipping_cost_val = shipping_cost_cell.value

                # Skip empty rows
                if not sku:
                    continue

                # Validate SKU and shipping cost
                row_errors = []

                if not sku:
                    row_errors.append(f"Row {row_idx}: SKU is empty")

                if shipping_cost_val is None:
                    row_errors.append(f"Row {row_idx}: Shipping Cost is empty")
                else:
                    parsed_cost = _to_numeric(shipping_cost_val)
                    if parsed_cost is None:
                        row_errors.append(
                            f"Row {row_idx}: Shipping Cost '{shipping_cost_val}' is not a valid number"
                        )
                    else:
                        shipping_cost_val = parsed_cost

                if isinstance(shipping_cost_val, (int, float)) and shipping_cost_val < 0:
                    row_errors.append(f"Row {row_idx}: Shipping Cost cannot be negative")

                if row_errors:
                    errors.extend(row_errors)
                    continue

                # Look up product by SKU
                product_id = None
                if sku not in product_cache:
                    sku_key = _sku_compare_key(sku)
                    # Query database for product with this SKU
                    product = db.query(Product).filter(
                        Product.tenant_id == uuid.UUID(tenant_id),
                        func.upper(func.regexp_replace(Product.sku, "[^A-Za-z0-9]+", "", "g")) == sku_key
                    ).first()
                    product_cache[sku] = product

                product = product_cache[sku]

                if product:
                    product_id = product.id
                else:
                    # Optional warning if product not found
                    errors.append(f"Row {row_idx}: Product with SKU '{sku}' not found in catalog (will still be stored)")

                # Extract optional fields
                product_name = None
                courier = None

                if product_name_col:
                    product_name_cell = row[product_name_col - 1]
                    product_name = (product_name_cell.value or "").strip() if product_name_cell.value else None

                if courier_col:
                    courier_cell = row[courier_col - 1]
                    courier = (courier_cell.value or "").strip() if courier_cell.value else None

                # Build tariff record
                record = {
                    "sku_code": sku,
                    "product_id": product_id,
                    "shipping_cost": Decimal(str(shipping_cost_val)),
                    "rto_handling_charge": Decimal("50"),  # Default RTO handling charge
                    "product_name": product_name,
                    "courier": courier,
                    "row": row_idx,
                }

                tariff_records.append(record)

            if not tariff_records and not errors:
                errors.append("No valid tariff records found in file")

        except Exception as e:
            errors.append(f"Error parsing XLSX file: {str(e)}")
            return [], errors

        return tariff_records, errors

    @staticmethod
    def upsert_shipping_tariffs(
        tariff_records: List[Dict],
        tenant_id: str,
        db: Session,
        file_uploaded_at: datetime = None
    ) -> Tuple[int, List[str]]:
        """
        Upsert tariff records into database using bulk insert.

        Args:
            tariff_records: List of tariff record dicts
            tenant_id: UUID of the tenant
            db: SQLAlchemy session
            file_uploaded_at: Timestamp of file upload (defaults to now)

        Returns:
            Tuple of (inserted_count, error_messages)
        """
        if not tariff_records:
            return 0, ["No records to insert"]

        try:
            tenant_uuid = uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
            now = file_uploaded_at or datetime.utcnow()

            # Normalize + dedupe per SKU (latest row in file wins).
            deduped_by_sku: Dict[str, Dict] = {}
            for record in tariff_records:
                sku_code = str(record.get("sku_code") or "").strip().upper()
                sku_key = _sku_compare_key(sku_code)
                if not sku_code or not sku_key:
                    continue
                clean = dict(record)
                clean["sku_code"] = sku_code
                deduped_by_sku[sku_key] = clean

            deduped_records = list(deduped_by_sku.values())
            if not deduped_records:
                return 0, ["No valid SKU rows to insert"]

            # Replace existing rows for these SKUs to avoid stale duplicates
            # (especially older rows with null product_id).
            affected_skus = list(deduped_by_sku.keys())
            db.query(ShippingTariff).filter(
                ShippingTariff.tenant_id == tenant_uuid,
                func.upper(func.regexp_replace(ShippingTariff.sku_code, "[^A-Za-z0-9]+", "", "g")).in_(affected_skus),
            ).delete(synchronize_session=False)

            insert_values = []
            for record in deduped_records:
                insert_values.append({
                    "id": uuid.uuid4(),
                    "tenant_id": tenant_uuid,
                    "product_id": record.get("product_id"),
                    "sku_code": record["sku_code"],
                    "shipping_cost": record["shipping_cost"],
                    "rto_handling_charge": record.get("rto_handling_charge", Decimal("50")),
                    "file_uploaded_at": now,
                    "created_at": now,
                    "updated_at": now,
                })

            db.execute(pg_insert(ShippingTariff).values(insert_values))
            db.commit()

            return len(insert_values), []

        except Exception as e:
            db.rollback()
            return 0, [f"Database error during upsert: {str(e)}"]

    @staticmethod
    def get_shipping_cost_by_sku(
        sku: str,
        tenant_id: str,
        db: Session
    ) -> Decimal:
        """
        Get shipping cost for a SKU.

        Args:
            sku: Product SKU
            tenant_id: UUID of tenant
            db: SQLAlchemy session

        Returns:
            Shipping cost as Decimal, or Decimal("0") if not found
        """
        sku_norm = _sku_compare_key(sku)
        if not sku_norm:
            return Decimal("0")

        tariff = db.query(ShippingTariff).filter(
            ShippingTariff.tenant_id == uuid.UUID(tenant_id),
            func.upper(func.regexp_replace(ShippingTariff.sku_code, "[^A-Za-z0-9]+", "", "g")) == sku_norm
        ).order_by(
            ShippingTariff.file_uploaded_at.desc(),
            ShippingTariff.updated_at.desc(),
            ShippingTariff.created_at.desc(),
        ).first()

        return tariff.shipping_cost if tariff else Decimal("0")

    @staticmethod
    def backfill_order_shipping_from_tariffs(
        tenant_id: str,
        db: Session,
    ) -> Dict[str, int]:
        """
        Recompute order.shipping_charge from the latest uploaded tariff rows.

        Rules:
        - Sum tariff cost by order item SKU * quantity
        - For returned orders, add fixed ₹50 RTO handling
        - Skip cancelled/inactive orders
        """
        from app.models.order import Order, OrderStatus

        tenant_uuid = uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id

        tariffs = (
            db.query(ShippingTariff)
            .filter(ShippingTariff.tenant_id == tenant_uuid)
            .order_by(
                ShippingTariff.file_uploaded_at.desc(),
                ShippingTariff.updated_at.desc(),
                ShippingTariff.created_at.desc(),
            )
            .all()
        )

        tariff_by_sku: Dict[str, Decimal] = {}
        for row in tariffs:
            sku_key = _sku_compare_key(row.sku_code)
            if not sku_key or sku_key in tariff_by_sku:
                continue
            tariff_by_sku[sku_key] = Decimal(str(row.shipping_cost or 0))

        if not tariff_by_sku:
            return {
                "orders_scanned": 0,
                "orders_with_sku_match": 0,
                "orders_updated": 0,
                "orders_without_sku_match": 0,
                "returned_orders_with_rto_added": 0,
                "profit_postings_refreshed": 0,
                "posting_refresh_errors": 0,
            }

        orders = (
            db.query(Order)
            .options(joinedload(Order.items))
            .filter(
                Order.tenant_id == tenant_uuid,
                Order.is_active == True,
                Order.status != OrderStatus.cancelled,
            )
            .all()
        )

        orders_scanned = len(orders)
        orders_with_sku_match = 0
        orders_updated = 0
        orders_without_sku_match = 0
        returned_orders_with_rto_added = 0
        profit_postings_refreshed = 0
        posting_refresh_errors = 0

        # Local import to avoid module import cycles.
        from app.modules.profit_engine.service import upsert_order_profit_posting

        for order in orders:
            total = Decimal("0")
            matched_items = 0

            for item in (order.items or []):
                sku_key = _sku_compare_key(getattr(item, "sku", ""))
                if not sku_key:
                    continue
                unit_cost = tariff_by_sku.get(sku_key)
                if unit_cost is None:
                    continue

                try:
                    qty = Decimal(str(getattr(item, "quantity", 1) or 1))
                except Exception:
                    qty = Decimal("1")
                if qty <= 0:
                    qty = Decimal("1")

                total += unit_cost * qty
                matched_items += 1

            if matched_items == 0:
                orders_without_sku_match += 1
                # Shipping may have been set manually from consignment files.
                # Refresh posting so Profit Checker reflects current order shipping.
                try:
                    current_shipping = Decimal(str(order.shipping_charge or 0)).quantize(Decimal("0.01"))
                except Exception:
                    current_shipping = Decimal("0.00")
                if current_shipping > 0:
                    try:
                        if upsert_order_profit_posting(db, tenant_uuid, order.id) is not None:
                            profit_postings_refreshed += 1
                    except Exception:
                        posting_refresh_errors += 1
                continue

            orders_with_sku_match += 1

            if order.status == OrderStatus.returned:
                total += Decimal("50")
                returned_orders_with_rto_added += 1

            target_shipping = total.quantize(Decimal("0.01"))
            current_shipping = Decimal(str(order.shipping_charge or 0)).quantize(Decimal("0.01"))

            if target_shipping != current_shipping:
                order.shipping_charge = target_shipping
                orders_updated += 1

            try:
                if upsert_order_profit_posting(db, tenant_uuid, order.id) is not None:
                    profit_postings_refreshed += 1
            except Exception:
                posting_refresh_errors += 1

        if orders_updated or profit_postings_refreshed:
            db.commit()

        return {
            "orders_scanned": orders_scanned,
            "orders_with_sku_match": orders_with_sku_match,
            "orders_updated": orders_updated,
            "orders_without_sku_match": orders_without_sku_match,
            "returned_orders_with_rto_added": returned_orders_with_rto_added,
            "profit_postings_refreshed": profit_postings_refreshed,
            "posting_refresh_errors": posting_refresh_errors,
        }

    @staticmethod
    def get_all_tariffs(
        tenant_id: str,
        db: Session,
        limit: int = None,
        offset: int = 0
    ) -> Tuple[List[ShippingTariff], int]:
        """
        Get all tariffs for a tenant with pagination.

        Returns:
            Tuple of (tariff_list, total_count)
        """
        query = db.query(ShippingTariff).filter(
            ShippingTariff.tenant_id == uuid.UUID(tenant_id)
        ).order_by(ShippingTariff.created_at.desc())

        total = query.count()

        if limit:
            query = query.limit(limit).offset(offset)

        return query.all(), total

    @staticmethod
    def delete_old_tariffs(
        tenant_id: str,
        keep_days: int = 30,
        db: Session = None
    ) -> int:
        """
        Delete tariff entries older than keep_days.
        This is useful for maintaining only recent tariff uploads.

        Args:
            tenant_id: UUID of tenant
            keep_days: Days to keep (default 30)
            db: SQLAlchemy session (if None, uses get_db())

        Returns:
            Number of records deleted
        """
        if db is None:
            db = next(get_db())

        try:
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=keep_days)

            result = db.query(ShippingTariff).filter(
                ShippingTariff.tenant_id == uuid.UUID(tenant_id),
                ShippingTariff.file_uploaded_at < cutoff_date
            ).delete()

            db.commit()
            return result

        except Exception as e:
            db.rollback()
            raise TariffParseError(f"Error deleting old tariffs: {str(e)}")
