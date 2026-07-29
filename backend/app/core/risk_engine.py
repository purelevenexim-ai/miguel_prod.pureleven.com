"""
Risk Engine — Phase 2
Evaluates incoming orders for fraud, RTO risk, and COD risk.
Produces a risk score and decision (approve / review / block).
"""
import logging
from decimal import Decimal
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.models.logistics import (
    RtoZone, CustomerDeliveryScore, BlacklistedCustomer,
    OrderRiskAssessment, RiskLevel, CodTransaction, CodConfirmStatus,
)
from app.models.shopify_order import ShopifyOrder
from app.models.shipping_config import ShippingBusinessRules

logger = logging.getLogger(__name__)


class RiskEngine:
    """
    Evaluates order risk across 4 dimensions:
      1. Customer history (RTO, NDR, COD rejections)
      2. Pincode / delivery zone risk (RTO rate by area)
      3. Order value (high-value COD = higher risk)
      4. COD-specific patterns
    Returns a decision: approve | review | block
    """

    # Score weights (must sum to 100)
    WEIGHT_CUSTOMER = 35
    WEIGHT_PINCODE  = 25
    WEIGHT_ORDER    = 20
    WEIGHT_COD      = 20

    def __init__(self, db: Session):
        self.db = db

    def assess_order(self, order: ShopifyOrder) -> Dict[str, Any]:
        """
        Run full risk assessment for a Shopify order.
        Saves result to order_risk_assessments table.
        Returns the assessment dict.
        """
        tenant_id = order.tenant_id

        # Load business rules (fallbacks built-in)
        rules = self._get_rules(str(tenant_id))

        # ── 1. Blacklist check ─────────────────────────────────
        is_blacklisted = self._check_blacklist(str(tenant_id), order.customer_phone)
        if is_blacklisted:
            return self._save_assessment(order, {
                "overall_risk_level": RiskLevel.blocked,
                "overall_risk_score": 100.0,
                "decision": "block",
                "customer_risk_score": 100.0,
                "pincode_risk_score": 0.0,
                "order_value_score": 0.0,
                "cod_risk_score": 0.0,
                "is_customer_blacklisted": True,
                "is_high_rto_zone": False,
                "is_high_value_order": False,
                "is_cod_order": self._is_cod(order),
                "is_new_customer": False,
                "has_multiple_rto": False,
                "has_cod_rejections": False,
                "risk_reasons": ["Customer is blacklisted"],
            })

        # ── 2. Customer score ──────────────────────────────────
        customer_data = self._score_customer(str(tenant_id), order.customer_phone)
        customer_risk  = customer_data["risk_score"]
        is_new         = customer_data["is_new"]
        has_multi_rto  = customer_data["has_multiple_rto"]
        has_cod_rej    = customer_data["has_cod_rejections"]

        # ── 3. Pincode risk ────────────────────────────────────
        pincode_data     = self._score_pincode(str(tenant_id), order.shipping_zip or "")
        pincode_risk     = pincode_data["risk_score"]
        is_high_rto_zone = pincode_data["is_high_rto"]

        # ── 4. Order value ─────────────────────────────────────
        is_cod        = self._is_cod(order)
        order_val     = float(order.total_price or 0)
        max_cod       = float(rules.get("max_cod_amount", 10000))
        is_high_value = (is_cod and order_val > max_cod) or (order_val > float(rules.get("max_order_value", 50000)))
        order_risk    = 70.0 if (is_cod and is_high_value) else (40.0 if is_high_value else 10.0)

        # ── 5. COD risk ────────────────────────────────────────
        cod_risk = 0.0
        if is_cod:
            cod_risk = 30.0  # Base COD risk
            if has_cod_rej:
                cod_risk += 40.0
            if is_new:
                cod_risk += 20.0
            cod_risk = min(cod_risk, 100.0)

        # ── 6. Weighted composite score ─────────────────────────
        composite = (
            customer_risk  * self.WEIGHT_CUSTOMER / 100 +
            pincode_risk   * self.WEIGHT_PINCODE  / 100 +
            order_risk     * self.WEIGHT_ORDER    / 100 +
            cod_risk       * self.WEIGHT_COD      / 100
        )

        # ── 7. Decision ────────────────────────────────────────
        risk_reasons: List[str] = []
        if is_blacklisted:    risk_reasons.append("Customer blacklisted")
        if is_new:            risk_reasons.append("First-time buyer")
        if is_high_rto_zone:  risk_reasons.append(f"High-RTO pincode ({order.shipping_zip})")
        if is_high_value:     risk_reasons.append(f"High-value order (₹{order_val:,.0f})")
        if has_multi_rto:     risk_reasons.append("Customer has multiple past RTOs")
        if has_cod_rej:       risk_reasons.append("Customer previously rejected COD")
        if is_cod:            risk_reasons.append("COD order")

        high_threshold   = float(rules.get("high_rto_threshold", 15))
        medium_threshold = float(rules.get("medium_rto_threshold", 8))

        if composite >= 70:
            level    = RiskLevel.high
            decision = "block"
        elif composite >= 40:
            level    = RiskLevel.medium
            decision = "review"
        else:
            level    = RiskLevel.low
            decision = "approve"

        return self._save_assessment(order, {
            "overall_risk_level":    level,
            "overall_risk_score":    round(composite, 2),
            "decision":              decision,
            "customer_risk_score":   round(customer_risk, 2),
            "pincode_risk_score":    round(pincode_risk, 2),
            "order_value_score":     round(order_risk, 2),
            "cod_risk_score":        round(cod_risk, 2),
            "is_customer_blacklisted": is_blacklisted,
            "is_high_rto_zone":      is_high_rto_zone,
            "is_high_value_order":   is_high_value,
            "is_cod_order":          is_cod,
            "is_new_customer":       is_new,
            "has_multiple_rto":      has_multi_rto,
            "has_cod_rejections":    has_cod_rej,
            "risk_reasons":          risk_reasons,
        })

    # ── Helpers ────────────────────────────────────────────────

    def _check_blacklist(self, tenant_id: str, phone: Optional[str]) -> bool:
        if not phone:
            return False
        now = datetime.now(timezone.utc)
        bl = (
            self.db.query(BlacklistedCustomer)
            .filter(
                BlacklistedCustomer.tenant_id == tenant_id,
                BlacklistedCustomer.customer_phone == phone,
                BlacklistedCustomer.is_active == True,
            )
            .first()
        )
        if not bl:
            return False
        if bl.expires_at and bl.expires_at < now:
            # Expired — deactivate automatically
            bl.is_active = False
            self.db.commit()
            return False
        return True

    def _score_customer(self, tenant_id: str, phone: Optional[str]) -> Dict[str, Any]:
        """Score customer based on historical delivery outcomes."""
        if not phone:
            return {"risk_score": 20.0, "is_new": True, "has_multiple_rto": False, "has_cod_rejections": False}

        score_row = (
            self.db.query(CustomerDeliveryScore)
            .filter(
                CustomerDeliveryScore.tenant_id == tenant_id,
                CustomerDeliveryScore.customer_phone == phone,
            )
            .first()
        )
        if not score_row or score_row.total_orders == 0:
            return {"risk_score": 20.0, "is_new": True, "has_multiple_rto": False, "has_cod_rejections": False}

        total = score_row.total_orders
        rto   = score_row.rto_orders
        ndr   = score_row.ndr_orders
        cod_rej = score_row.cod_rejected

        rto_rate = (rto / total) * 100 if total > 0 else 0
        # Risk: 0 (perfect) → 100 (all RTO)
        risk_score = min(rto_rate * 2 + (ndr / total * 30) + (cod_rej * 15), 100.0)

        return {
            "risk_score":        round(risk_score, 2),
            "is_new":            False,
            "has_multiple_rto":  rto >= 3,
            "has_cod_rejections": cod_rej >= 2,
        }

    def _score_pincode(self, tenant_id: str, pincode: str) -> Dict[str, Any]:
        """Score pincode based on historical RTO rate for that zone."""
        if not pincode:
            return {"risk_score": 15.0, "is_high_rto": False}

        zone = (
            self.db.query(RtoZone)
            .filter(
                RtoZone.tenant_id == tenant_id,
                RtoZone.pincode == pincode,
            )
            .first()
        )
        if not zone or zone.total_shipments < 5:
            # Not enough data — low baseline risk
            return {"risk_score": 15.0, "is_high_rto": False}

        rto_pct = float(zone.rto_percentage or 0)
        risk_score = min(rto_pct * 3, 100.0)   # 33% RTO = 100 risk score

        return {
            "risk_score":  round(risk_score, 2),
            "is_high_rto": rto_pct >= 15.0,
        }

    def _is_cod(self, order: ShopifyOrder) -> bool:
        """Determine if this is a COD order from financial_status."""
        return order.shopify_financial_status in ("pending", "cod")

    def _get_rules(self, tenant_id: str) -> Dict[str, Any]:
        """Get shipping business rules for tenant (with defaults)."""
        rules = (
            self.db.query(ShippingBusinessRules)
            .filter(ShippingBusinessRules.tenant_id == tenant_id)
            .first()
        )
        if not rules:
            return {
                "max_order_value": 50000,
                "max_cod_amount": 10000,
                "high_rto_threshold": 15,
                "medium_rto_threshold": 8,
            }
        return {
            "max_order_value":    float(rules.max_order_value or 50000),
            "max_cod_amount":     float(rules.max_cod_amount or 10000),
            "high_rto_threshold":  float(rules.high_rto_threshold or 15),
            "medium_rto_threshold": float(rules.medium_rto_threshold or 8),
        }

    def _save_assessment(self, order: ShopifyOrder, data: Dict[str, Any]) -> Dict[str, Any]:
        """Persist assessment to DB and return the dict."""
        try:
            existing = (
                self.db.query(OrderRiskAssessment)
                .filter(OrderRiskAssessment.shopify_order_id == order.id)
                .first()
            )
            if existing:
                assessment = existing
            else:
                assessment = OrderRiskAssessment(
                    tenant_id=order.tenant_id,
                    shopify_order_id=order.id,
                )

            assessment.overall_risk_level    = data["overall_risk_level"]
            assessment.overall_risk_score    = data["overall_risk_score"]
            assessment.decision              = data["decision"]
            assessment.customer_risk_score   = data["customer_risk_score"]
            assessment.pincode_risk_score    = data["pincode_risk_score"]
            assessment.order_value_score     = data["order_value_score"]
            assessment.cod_risk_score        = data["cod_risk_score"]
            assessment.is_customer_blacklisted = data["is_customer_blacklisted"]
            assessment.is_high_rto_zone      = data["is_high_rto_zone"]
            assessment.is_high_value_order   = data["is_high_value_order"]
            assessment.is_cod_order          = data["is_cod_order"]
            assessment.is_new_customer       = data["is_new_customer"]
            assessment.has_multiple_rto      = data["has_multiple_rto"]
            assessment.has_cod_rejections    = data["has_cod_rejections"]
            assessment.risk_reasons          = data["risk_reasons"]

            self.db.add(assessment)
            self.db.commit()

        except Exception as e:
            logger.error(f"Failed to save risk assessment: {e}")
            self.db.rollback()

        return data

    def update_customer_score(self, tenant_id: str, phone: str, outcome: str) -> None:
        """
        Update customer delivery score after a shipment outcome.
        outcome: 'delivered' | 'rto' | 'ndr' | 'cod_confirmed' | 'cod_rejected'
        """
        try:
            row = (
                self.db.query(CustomerDeliveryScore)
                .filter(
                    CustomerDeliveryScore.tenant_id == tenant_id,
                    CustomerDeliveryScore.customer_phone == phone,
                )
                .first()
            )
            if not row:
                row = CustomerDeliveryScore(
                    tenant_id=tenant_id,
                    customer_phone=phone,
                )
                self.db.add(row)

            row.total_orders += 1
            if outcome == "delivered":
                row.delivered_orders += 1
            elif outcome == "rto":
                row.rto_orders += 1
            elif outcome == "ndr":
                row.ndr_orders += 1
            elif outcome == "cod_confirmed":
                row.cod_orders += 1
                row.cod_confirmed += 1
            elif outcome == "cod_rejected":
                row.cod_orders += 1
                row.cod_rejected += 1

            # Recalculate delivery score (higher = safer)
            total = row.total_orders or 1
            safe_rate    = row.delivered_orders / total
            row.delivery_score = round(safe_rate * 100, 2)

            rto_rate = (row.rto_orders / total) * 100
            if rto_rate >= 30 or row.cod_rejected >= 3:
                row.risk_level = RiskLevel.high
            elif rto_rate >= 15 or row.cod_rejected >= 1:
                row.risk_level = RiskLevel.medium
            else:
                row.risk_level = RiskLevel.low

            row.last_order_at = datetime.now(timezone.utc)
            row.last_updated  = datetime.now(timezone.utc)
            self.db.commit()

        except Exception as e:
            logger.error(f"Failed to update customer score: {e}")
            self.db.rollback()

    def update_rto_zone(self, tenant_id: str, pincode: str, city: str, state: str, outcome: str) -> None:
        """
        Update RTO zone stats after a delivery outcome.
        outcome: 'delivered' | 'rto' | 'ndr'
        """
        try:
            zone = (
                self.db.query(RtoZone)
                .filter(
                    RtoZone.tenant_id == tenant_id,
                    RtoZone.pincode == pincode,
                )
                .first()
            )
            if not zone:
                zone = RtoZone(
                    tenant_id=tenant_id,
                    pincode=pincode,
                    city=city,
                    state=state,
                )
                self.db.add(zone)

            zone.total_shipments += 1
            if outcome == "delivered":
                zone.delivered_count += 1
            elif outcome == "rto":
                zone.rto_count += 1
            elif outcome == "ndr":
                zone.ndr_count += 1

            total = zone.total_shipments or 1
            zone.rto_percentage = round((zone.rto_count / total) * 100, 2)
            rto_pct = float(zone.rto_percentage)

            if rto_pct >= 25:
                zone.risk_level  = RiskLevel.high
                zone.risk_score  = min(rto_pct * 3, 100)
            elif rto_pct >= 12:
                zone.risk_level  = RiskLevel.medium
                zone.risk_score  = rto_pct * 2
            else:
                zone.risk_level  = RiskLevel.low
                zone.risk_score  = rto_pct

            zone.last_updated = datetime.now(timezone.utc)
            self.db.commit()

        except Exception as e:
            logger.error(f"Failed to update RTO zone: {e}")
            self.db.rollback()

    def auto_blacklist_customer(self, tenant_id: str, phone: str, reason: str) -> bool:
        """Automatically blacklist a customer based on risk thresholds."""
        try:
            rules = self._get_rules(tenant_id)
            score_row = (
                self.db.query(CustomerDeliveryScore)
                .filter(
                    CustomerDeliveryScore.tenant_id == tenant_id,
                    CustomerDeliveryScore.customer_phone == phone,
                )
                .first()
            )
            if not score_row:
                return False

            should_blacklist = (
                score_row.rto_orders >= 5 or
                score_row.ndr_orders >= 5 or
                score_row.cod_rejected >= 3
            )
            if not should_blacklist:
                return False

            # Check not already blacklisted
            existing = (
                self.db.query(BlacklistedCustomer)
                .filter(
                    BlacklistedCustomer.tenant_id == tenant_id,
                    BlacklistedCustomer.customer_phone == phone,
                    BlacklistedCustomer.is_active == True,
                )
                .first()
            )
            if existing:
                return False

            bl = BlacklistedCustomer(
                tenant_id=tenant_id,
                customer_phone=phone,
                customer_name=score_row.customer_name,
                reason=reason,
                blacklist_type="auto",
                is_permanent=False,
                expires_at=datetime.now(timezone.utc) + timedelta(days=180),
                blocked_by="system",
            )
            self.db.add(bl)
            self.db.commit()
            logger.info(f"Auto-blacklisted customer {phone}: {reason}")
            return True

        except Exception as e:
            logger.error(f"Auto-blacklist error: {e}")
            self.db.rollback()
            return False
