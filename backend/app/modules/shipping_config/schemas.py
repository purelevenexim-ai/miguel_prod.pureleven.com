from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


# ─────────────────────────────────────────────────────────────
#  SHOPIFY STORES
# ─────────────────────────────────────────────────────────────

class ShopifyStoreCreate(BaseModel):
    store_name:        str
    store_url:         str
    api_access_token:  str
    api_client_id:     str
    api_client_secret: str
    is_primary:        bool = False

    @field_validator("store_url")
    @classmethod
    def normalise_store_url(cls, v: str) -> str:
        """Strip https:// prefix — we store only the hostname."""
        return v.replace("https://", "").replace("http://", "").rstrip("/")


class ShopifyStoreUpdate(BaseModel):
    store_name:        Optional[str]  = None
    is_primary:        Optional[bool] = None
    api_access_token:  Optional[str]  = None
    api_client_id:     Optional[str]  = None
    api_client_secret: Optional[str]  = None
    is_active:         Optional[bool] = None


class ShopifyStoreOut(BaseModel):
    id:                   UUID
    store_name:           str
    store_url:            str
    is_primary:           bool
    is_active:            bool
    is_connected:         bool
    last_sync:            Optional[datetime] = None
    last_connection_test: Optional[datetime] = None
    created_at:           datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────
#  DELIVERY PARTNERS
# ─────────────────────────────────────────────────────────────

class DeliveryPartnerCreate(BaseModel):
    partner_type:         str
    display_name:         str
    api_key:              Optional[str] = None   # Optional - can be left blank
    api_secret:           Optional[str] = None
    client_name:          Optional[str] = None
    client_id:            Optional[str] = None
    pickup_location_code: Optional[str] = None
    warehouse_name:       Optional[str] = None
    customer_ids:         Optional[List[Dict[str, str]]] = None   # [{"id": "12345", "name": "Parcel"}]
    is_primary:           bool = False

    @field_validator("partner_type")
    @classmethod
    def validate_partner_type(cls, v: str) -> str:
        allowed = {"delhivery", "bluedart", "dtdc", "india_post", "amazon"}
        if v not in allowed:
            raise ValueError(f"partner_type must be one of {allowed}")
        return v


class DeliveryPartnerUpdate(BaseModel):
    display_name:         Optional[str]  = None
    api_key:              Optional[str]  = None
    api_secret:           Optional[str]  = None
    client_name:          Optional[str]  = None
    client_id:            Optional[str]  = None
    pickup_location_code: Optional[str]  = None
    warehouse_name:       Optional[str]  = None
    customer_ids:         Optional[List[Dict[str, str]]] = None   # [{"id": "12345", "name": "Parcel"}]
    is_primary:           Optional[bool] = None
    is_active:            Optional[bool] = None


class DeliveryPartnerOut(BaseModel):
    id:                      UUID
    partner_type:            str
    display_name:            str
    is_primary:              bool
    is_active:               bool
    is_connected:            bool
    client_name:             Optional[str] = None
    pickup_location_code:    Optional[str] = None
    supported_shipment_types: Optional[List[str]] = None
    customer_ids:            Optional[List[Dict[str, str]]] = None
    last_connection_test:    Optional[datetime] = None
    created_at:              datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────
#  NOTIFICATION CHANNELS
# ─────────────────────────────────────────────────────────────

class NotificationChannelCreate(BaseModel):
    channel_type:        str   # whatsapp | sms | email
    provider:            str   # meta | twilio | sendgrid
    api_key:             Optional[str] = None
    api_secret:          Optional[str] = None
    access_token:        Optional[str] = None
    phone_number:        Optional[str] = None
    business_account_id: Optional[str] = None
    phone_number_id:     Optional[str] = None
    sender_email:        Optional[str] = None
    is_primary:          bool = False

    @field_validator("channel_type")
    @classmethod
    def validate_channel_type(cls, v: str) -> str:
        allowed = {"whatsapp", "sms", "email"}
        if v not in allowed:
            raise ValueError(f"channel_type must be one of {allowed}")
        return v


class NotificationChannelUpdate(BaseModel):
    api_key:             Optional[str]  = None
    api_secret:          Optional[str]  = None
    access_token:        Optional[str]  = None
    phone_number:        Optional[str]  = None
    business_account_id: Optional[str]  = None
    phone_number_id:     Optional[str]  = None
    sender_email:        Optional[str]  = None
    is_primary:          Optional[bool] = None
    is_active:           Optional[bool] = None


class NotificationChannelOut(BaseModel):
    id:           UUID
    channel_type: str
    provider:     str
    is_active:    bool
    is_connected: bool
    is_primary:   bool
    phone_number: Optional[str] = None
    sender_email: Optional[str] = None
    last_connection_test: Optional[datetime] = None
    created_at:   datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────
#  BUSINESS RULES
# ─────────────────────────────────────────────────────────────

class BusinessRulesUpdate(BaseModel):
    max_order_value:                  Optional[Decimal] = None
    max_cod_amount:                   Optional[Decimal] = None
    high_rto_threshold:               Optional[Decimal] = None
    medium_rto_threshold:             Optional[Decimal] = None
    require_cod_confirmation:         Optional[bool]    = None
    cod_confirmation_timeout_minutes: Optional[str]     = None
    auto_create_on_order_created:     Optional[bool]    = None
    auto_create_on_payment_confirmed: Optional[bool]    = None
    require_manual_approval:          Optional[bool]    = None
    send_delivery_confirmation:       Optional[bool]    = None
    send_rto_alerts:                  Optional[bool]    = None
    send_ndr_alerts:                  Optional[bool]    = None
    notify_via_whatsapp:              Optional[bool]    = None
    notify_via_sms:                   Optional[bool]    = None
    notify_via_email:                 Optional[bool]    = None
    admin_alert_on_rto:               Optional[bool]    = None
    admin_alert_on_ndr:               Optional[bool]    = None
    admin_emails:                     Optional[List[str]] = None


class BusinessRulesOut(BaseModel):
    id:                               UUID
    max_order_value:                  Decimal
    max_cod_amount:                   Decimal
    high_rto_threshold:               Decimal
    medium_rto_threshold:             Decimal
    require_cod_confirmation:         bool
    auto_create_on_order_created:     bool
    auto_create_on_payment_confirmed: bool
    require_manual_approval:          bool
    send_delivery_confirmation:       bool
    send_rto_alerts:                  bool
    send_ndr_alerts:                  bool
    notify_via_whatsapp:              bool
    notify_via_sms:                   bool
    notify_via_email:                 bool
    admin_alert_on_rto:               bool
    admin_alert_on_ndr:               bool
    admin_alert_on_high_value_order:  bool
    admin_emails:                     Optional[List[str]] = None
    updated_at:                       datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────
#  GENERIC CONNECTION TEST RESPONSE
# ─────────────────────────────────────────────────────────────

class ConnectionTestOut(BaseModel):
    status:  str    # "connected" | "failed" | "error"
    message: str
