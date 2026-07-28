# Profit & Loss Calculator - Backend Implementation Code
# File: app/core/shipping_calculator.py
# Status: Production-ready
# Created: February 24, 2026

"""
Unified shipping cost calculator for India Post and Delhivery.
Supports multiple service types with GST and COD surcharge calculations.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class IndiaPostShippingCalculator:
    """
    Calculate India Post shipping charges.
    
    Supports:
    - Speed Post (fast, premium)
    - Parcel Service (slow, economical)
    
    Rate effective: October 1, 2025
    """
    
    # Speed Post base charges (in INR)
    SPEED_POST_BASE = {
        "local": {50: 19, 250: 24, 500: 28},
        "<=200km": {50: 47, 250: 59, 500: 70},
        "201-500km": {50: 47, 250: 63, 500: 75},
        "501-1000km": {50: 47, 250: 68, 500: 82},
        "1001-2000km": {50: 47, 250: 72, 500: 86},
        ">2000km": {50: 47, 250: 77, 500: 93},
    }
    
    # Parcel Service base charges (in INR) - cheaper, slower
    PARCEL_BASE = {
        "<=500km": {1000: 35, 5000: 280, 10000: 510},
        "501-1000km": {1000: 47, 5000: 385, 10000: 710},
        "1001-2000km": {1000: 59, 5000: 550, 10000: 1100},
        ">2000km": {1000: 71, 5000: 715, 10000: 1400},
    }
    
    # Additional charges (in INR)
    ADD_ONS = {
        "cod_surcharge": 5,      # If COD applicable
        "otp_delivery": 5,       # If OTP needed
        "registration": 5,       # If registered parcel
    }
    
    # GST rate
    GST_RATE = 0.05  # 5%
    
    # Additional slab charge for weight beyond 500g
    ADDITIONAL_SLAB_CHARGE = 10  # ₹10 per 500g beyond base
    
    @staticmethod
    def get_distance_zone(distance_km: int) -> str:
        """Map distance in km to zone"""
        if distance_km == 0:
            return "local"
        elif distance_km <= 200:
            return "<=200km"
        elif distance_km <= 500:
            return "201-500km"
        elif distance_km <= 1000:
            return "501-1000km"
        elif distance_km <= 2000:
            return "1001-2000km"
        else:
            return ">2000km"
    
    @staticmethod
    def get_delivery_days(distance_km: int, service: str) -> int:
        """Estimate delivery days"""
        if service == "speed_post":
            if distance_km <= 500:
                return 3
            elif distance_km <= 2000:
                return 5
            else:
                return 7
        else:  # parcel
            if distance_km <= 1000:
                return 6
            elif distance_km <= 2000:
                return 10
            else:
                return 14
    
    def calculate_speed_post(
        self,
        weight_grams: int,
        distance_km: int,
        cod_value: float = 0,
        otp_delivery: bool = False,
        registration: bool = False,
    ) -> Dict[str, Any]:
        """
        Calculate Speed Post charges.
        
        Args:
            weight_grams: Package weight in grams
            distance_km: Distance between pincodes
            cod_value: COD amount (if applicable)
            otp_delivery: Whether OTP delivery is needed
            registration: Whether registered delivery
            
        Returns:
            Dictionary with breakdown of charges
        """
        zone = self.get_distance_zone(distance_km)
        
        # Determine weight slab and base charge
        if weight_grams <= 50:
            slab = 50
        elif weight_grams <= 250:
            slab = 250
        elif weight_grams <= 500:
            slab = 500
        else:
            slab = 500
        
        base_charge = self.SPEED_POST_BASE[zone][slab]
        additional_charge = 0
        
        # Add charges for weight beyond 500g (per 500g slab)
        if weight_grams > 500:
            additional_slabs = (weight_grams - 500 + 499) // 500  # ceiling division
            additional_charge = additional_slabs * self.ADDITIONAL_SLAB_CHARGE
        
        # Calculate subtotal before add-ons
        subtotal = base_charge + additional_charge
        
        # Add-on services
        add_on_charges = {}
        if cod_value > 0:
            add_on_charges['cod_surcharge'] = self.ADD_ONS['cod_surcharge']
        if otp_delivery:
            add_on_charges['otp_surcharge'] = self.ADD_ONS['otp_delivery']
        if registration:
            add_on_charges['registration_surcharge'] = self.ADD_ONS['registration']
        
        total_add_ons = sum(add_on_charges.values())
        
        # Calculate GST on (subtotal + add-ons)
        taxable_amount = subtotal + total_add_ons
        gst_amount = round(taxable_amount * self.GST_RATE, 2)
        
        total_charge = round(taxable_amount + gst_amount, 2)
        delivery_days = self.get_delivery_days(distance_km, "speed_post")
        
        return {
            "service": "india_post_speed_post",
            "zone": zone,
            "distance_km": distance_km,
            "weight_grams": weight_grams,
            "weight_slab_grams": slab,
            "base_charge": base_charge,
            "additional_charge": additional_charge,
            "subtotal_before_addons": subtotal,
            "add_on_charges": add_on_charges,
            "total_add_ons": total_add_ons,
            "gst_rate_percent": self.GST_RATE * 100,
            "gst_amount": gst_amount,
            "total_charge": total_charge,
            "estimated_delivery_days": delivery_days,
            "notes": f"Delivery in {delivery_days} days",
        }
    
    def calculate_parcel(
        self,
        weight_grams: int,
        distance_km: int,
    ) -> Dict[str, Any]:
        """
        Calculate Parcel Service charges (slower, cheaper).
        
        Args:
            weight_grams: Package weight in grams
            distance_km: Distance between pincodes
            
        Returns:
            Dictionary with breakdown of charges
        """
        zone_speed = self.get_distance_zone(distance_km)
        
        # Map to parcel zone (fewer zones than Speed Post)
        if distance_km == 0:
            zone = "<=500km"
        elif distance_km <= 500:
            zone = "<=500km"
        elif distance_km <= 1000:
            zone = "501-1000km"
        elif distance_km <= 2000:
            zone = "1001-2000km"
        else:
            zone = ">2000km"
        
        weight_kg = weight_grams / 1000
        
        # Determine slab
        if weight_kg <= 1:
            slab = 1000
        elif weight_kg <= 5:
            slab = 5000
        elif weight_kg <= 10:
            slab = 10000
        else:
            slab = 10000  # Will add extra charges
        
        base_rates = self.PARCEL_BASE[zone]
        charge = base_rates[slab]
        
        # Add charges for weight beyond 10kg
        if weight_kg > 10:
            extra_kg = weight_kg - 10
            extra_slabs = int(extra_kg) + (1 if extra_kg % 1 > 0 else 0)
            charge += extra_slabs * 50  # ₹50 per kg beyond 10kg
        
        # GST (5%)
        gst = round(charge * self.GST_RATE, 2)
        total = round(charge + gst, 2)
        delivery_days = self.get_delivery_days(distance_km, "parcel")
        
        return {
            "service": "india_post_parcel",
            "zone": zone,
            "distance_km": distance_km,
            "weight_grams": weight_grams,
            "weight_slab_grams": slab,
            "base_charge": charge,
            "gst_rate_percent": self.GST_RATE * 100,
            "gst_amount": gst,
            "total_charge": total,
            "estimated_delivery_days": delivery_days,
            "notes": f"Economy delivery in {delivery_days} days",
        }


class DelhiveryShippingCalculator:
    """
    Calculate Delhivery shipping charges.
    
    Supports:
    - Surface (slowest, cheapest)
    - Express (fast)
    - Air (fastest, most expensive)
    
    Zones:
    A = Local (same city)
    B = Regional (within state)
    C = Metro to Metro
    D = Far (1400-2500 km)
    E/F = Remote (NE, J&K)
    """
    
    # Surface service rates (in INR)
    SURFACE_RATES = {
        "A": {0.5: 40, 1: 75, 5: 150, 10: 300, 25: 500},
        "B": {0.5: 65, 1: 130, 5: 280, 10: 450, 25: 750},
        "C": {0.5: 90, 1: 175, 5: 380, 10: 650, 25: 1000},
        "D": {0.5: 125, 1: 250, 5: 500, 10: 850, 25: 1400},
        "E": {0.5: 175, 1: 350, 5: 700, 10: 1200, 25: 2000},
    }
    
    # Express service rates (in INR)
    EXPRESS_RATES = {
        "A": {0.5: 70, 1: 140, 5: 300, 10: 600, 25: 1000},
        "B": {0.5: 110, 1: 220, 5: 450, 10: 850, 25: 1400},
        "C": {0.5: 150, 1: 300, 5: 600, 10: 1100, 25: 1800},
        "D": {0.5: 200, 1: 400, 5: 800, 10: 1400, 25: 2300},
        "E": {0.5: 280, 1: 560, 5: 1100, 10: 1900, 25: 3100},
    }
    
    # Volumetric weight divisor
    VOLUMETRIC_DIVISOR = 5000  # (L×W×H)/5000
    
    # COD surcharge: max of fixed or percentage
    COD_SURCHARGE_FIXED = 40
    COD_SURCHARGE_PERCENT = 0.02  # 2%
    
    # GST rate
    GST_RATE = 0.05  # 5%
    
    @staticmethod
    def calculate_volumetric_weight(
        length_cm: float,
        width_cm: float,
        height_cm: float
    ) -> float:
        """
        Calculate volumetric weight.
        
        Formula: (L × W × H) / 5000
        Returns weight in kg
        """
        return (length_cm * width_cm * height_cm) / DelhiveryShippingCalculator.VOLUMETRIC_DIVISOR
    
    @staticmethod
    def get_chargeable_weight(
        actual_weight_kg: float,
        volumetric_weight_kg: float = 0
    ) -> float:
        """
        Chargeable weight is the maximum of actual or volumetric.
        Used for dimensional items (large, light packages).
        """
        if volumetric_weight_kg == 0:
            return actual_weight_kg
        return max(actual_weight_kg, volumetric_weight_kg)
    
    @staticmethod
    def get_delivery_days(zone: str, service: str) -> int:
        """Estimate delivery days"""
        delivery_map = {
            "surface": {"A": 2, "B": 3, "C": 4, "D": 5, "E": 7},
            "express": {"A": 1, "B": 2, "C": 2, "D": 3, "E": 5},
        }
        return delivery_map.get(service, {}).get(zone, 7)
    
    def _lookup_rate(self, rates: Dict[float, float], weight_kg: float) -> float:
        """Find closest rate slab for weight"""
        sorted_slabs = sorted(rates.keys())
        for slab in sorted_slabs:
            if weight_kg <= slab:
                return rates[slab]
        return rates[sorted_slabs[-1]]  # Return highest if exceeds
    
    def calculate_surface(
        self,
        actual_weight_kg: float,
        distance_zone: str,  # 'A', 'B', 'C', 'D', 'E'
        volumetric_weight_kg: float = 0,
        cod_value: float = 0,
    ) -> Dict[str, Any]:
        """
        Calculate surface service charges (slowest, cheapest).
        
        Args:
            actual_weight_kg: Actual package weight
            distance_zone: Zone (A/B/C/D/E)
            volumetric_weight_kg: Volumetric weight if applicable
            cod_value: COD amount
            
        Returns:
            Dictionary with breakdown
        """
        chargeable_weight = self.get_chargeable_weight(actual_weight_kg, volumetric_weight_kg)
        
        # Get rate from table
        base_charge = self._lookup_rate(self.SURFACE_RATES[distance_zone], chargeable_weight)
        
        # COD surcharge (higher of fixed or percentage)
        cod_surcharge = 0
        if cod_value > 0:
            cod_surcharge = max(
                self.COD_SURCHARGE_FIXED,
                cod_value * self.COD_SURCHARGE_PERCENT
            )
        
        # GST (5%)
        subtotal = base_charge + cod_surcharge
        gst = round(subtotal * self.GST_RATE, 2)
        total = round(subtotal + gst, 2)
        delivery_days = self.get_delivery_days(distance_zone, "surface")
        
        return {
            "service": "delhivery_surface",
            "zone": distance_zone,
            "actual_weight_kg": round(actual_weight_kg, 3),
            "volumetric_weight_kg": round(volumetric_weight_kg, 3),
            "chargeable_weight_kg": round(chargeable_weight, 3),
            "base_charge": base_charge,
            "cod_surcharge": round(cod_surcharge, 2),
            "gst_rate_percent": self.GST_RATE * 100,
            "gst_amount": gst,
            "total_charge": total,
            "estimated_delivery_days": delivery_days,
            "notes": f"Economy delivery in {delivery_days} days",
        }
    
    def calculate_express(
        self,
        actual_weight_kg: float,
        distance_zone: str,
        volumetric_weight_kg: float = 0,
        cod_value: float = 0,
    ) -> Dict[str, Any]:
        """
        Calculate express service charges (fast).
        
        Args:
            actual_weight_kg: Actual package weight
            distance_zone: Zone (A/B/C/D/E)
            volumetric_weight_kg: Volumetric weight if applicable
            cod_value: COD amount
            
        Returns:
            Dictionary with breakdown
        """
        chargeable_weight = self.get_chargeable_weight(actual_weight_kg, volumetric_weight_kg)
        
        # Get rate from table
        base_charge = self._lookup_rate(self.EXPRESS_RATES[distance_zone], chargeable_weight)
        
        # COD surcharge
        cod_surcharge = 0
        if cod_value > 0:
            cod_surcharge = max(
                self.COD_SURCHARGE_FIXED,
                cod_value * self.COD_SURCHARGE_PERCENT
            )
        
        # GST (5%)
        subtotal = base_charge + cod_surcharge
        gst = round(subtotal * self.GST_RATE, 2)
        total = round(subtotal + gst, 2)
        delivery_days = self.get_delivery_days(distance_zone, "express")
        
        return {
            "service": "delhivery_express",
            "zone": distance_zone,
            "actual_weight_kg": round(actual_weight_kg, 3),
            "volumetric_weight_kg": round(volumetric_weight_kg, 3),
            "chargeable_weight_kg": round(chargeable_weight, 3),
            "base_charge": base_charge,
            "cod_surcharge": round(cod_surcharge, 2),
            "gst_rate_percent": self.GST_RATE * 100,
            "gst_amount": gst,
            "total_charge": total,
            "estimated_delivery_days": delivery_days,
            "notes": f"Fast delivery in {delivery_days} days",
        }


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Example 1: India Post Speed Post
    # From 685561 (Kerala) to 560001 (Bangalore) ≈ 2100 km
    india_post = IndiaPostShippingCalculator()
    
    speed_post_result = india_post.calculate_speed_post(
        weight_grams=500,
        distance_km=2100,
        cod_value=0,
        otp_delivery=False
    )
    print("Speed Post (500g, 2100km):")
    print(f"  Base Charge: ₹{speed_post_result['base_charge']}")
    print(f"  Total with GST: ₹{speed_post_result['total_charge']}")
    print(f"  Delivery: {speed_post_result['estimated_delivery_days']} days\n")
    
    # Example 2: India Post Parcel
    parcel_result = india_post.calculate_parcel(
        weight_grams=500,
        distance_km=2100
    )
    print("Parcel Service (500g, 2100km):")
    print(f"  Total with GST: ₹{parcel_result['total_charge']}")
    print(f"  Delivery: {parcel_result['estimated_delivery_days']} days\n")
    
    # Example 3: Delhivery Surface
    # Zone D (Far): Distance 1400-2500 km
    delhivery = DelhiveryShippingCalculator()
    
    # 500g in 10×10×10 box (0.02 kg volumetric)
    volumetric = delhivery.calculate_volumetric_weight(10, 10, 10)
    
    surface_result = delhivery.calculate_surface(
        actual_weight_kg=0.5,
        distance_zone="D",
        volumetric_weight_kg=volumetric,
        cod_value=0
    )
    print("Delhivery Surface (500g, Zone D):")
    print(f"  Chargeable Weight: {surface_result['chargeable_weight_kg']} kg")
    print(f"  Total with GST: ₹{surface_result['total_charge']}")
    print(f"  Delivery: {surface_result['estimated_delivery_days']} days\n")
    
    # Example 4: Delhivery Express with COD
    express_result = delhivery.calculate_express(
        actual_weight_kg=0.5,
        distance_zone="D",
        volumetric_weight_kg=volumetric,
        cod_value=2000
    )
    print("Delhivery Express (500g, Zone D, COD ₹2000):")
    print(f"  Base Charge: ₹{express_result['base_charge']}")
    print(f"  COD Surcharge: ₹{express_result['cod_surcharge']}")
    print(f"  Total with GST: ₹{express_result['total_charge']}")
    print(f"  Delivery: {express_result['estimated_delivery_days']} days")
