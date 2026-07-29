from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.models.customer_retarget import RetargetOutcome


CALLBACK_OUTCOMES = {
    RetargetOutcome.no_answer,
    RetargetOutcome.callback,
    RetargetOutcome.interested,
}


class RetargetCallCreate(BaseModel):
    outcome: RetargetOutcome
    phone_called: Optional[str] = Field(default=None, max_length=20)
    notes: Optional[str] = Field(default=None, max_length=5000)
    next_callback_at: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_outcome_requirements(self):
        if self.outcome in CALLBACK_OUTCOMES:
            if self.next_callback_at is None:
                raise ValueError("A callback date is required for this outcome")
            callback_at = self.next_callback_at
            if callback_at.tzinfo is None:
                callback_at = callback_at.replace(tzinfo=timezone.utc)
                self.next_callback_at = callback_at
            if callback_at <= datetime.now(timezone.utc):
                raise ValueError("Callback date must be in the future")

        if self.outcome == RetargetOutcome.risk and not (self.notes or "").strip():
            raise ValueError("Notes are required when marking a customer as risk")

        self.phone_called = (self.phone_called or "").strip() or None
        self.notes = (self.notes or "").strip() or None
        return self


class UnlinkedCustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    phone: str = Field(min_length=1, max_length=20)
    alternate_phone: Optional[str] = Field(default=None, max_length=20)
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    pincode: Optional[str] = Field(default=None, max_length=10)
    city: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default="India", max_length=100)
    notes: Optional[str] = None


class UnlinkedResolveRequest(BaseModel):
    customer_id: Optional[UUID] = None
    customer: Optional[UnlinkedCustomerCreate] = None

    @model_validator(mode="after")
    def validate_resolution_target(self):
        if bool(self.customer_id) == bool(self.customer):
            raise ValueError("Provide either customer_id or customer details")
        return self


class RetargetTemplateBulkSend(BaseModel):
    customer_ids: list[UUID] = Field(min_length=1, max_length=5000)
    template_name: str = Field(min_length=1, max_length=255)
    language_code: str = Field(default="en", min_length=2, max_length=20)
    header_image_url: Optional[str] = Field(default=None, max_length=2000)
    recipient_phone_override: Optional[str] = Field(
        default=None,
        max_length=20,
    )
    consent_confirmed: bool = False

    @model_validator(mode="after")
    def validate_bulk_template_send(self):
        self.customer_ids = list(dict.fromkeys(self.customer_ids))
        self.template_name = self.template_name.strip()
        self.language_code = self.language_code.strip()
        self.header_image_url = (self.header_image_url or "").strip() or None
        self.recipient_phone_override = (
            (self.recipient_phone_override or "").strip() or None
        )

        if not self.consent_confirmed:
            raise ValueError("Confirm that the selected customers permitted WhatsApp messages")
        if self.recipient_phone_override and len(self.customer_ids) != 1:
            raise ValueError(
                "A phone override can only be used for one customer"
            )
        if self.header_image_url and not self.header_image_url.startswith("https://"):
            raise ValueError("Header image URL must use HTTPS")
        return self


class RetargetManualCustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    phone: str = Field(min_length=10, max_length=20)
    alternate_phone: Optional[str] = Field(default=None, max_length=20)
    notes: Optional[str] = Field(default=None, max_length=5000)
    is_test_customer: bool = False

    @model_validator(mode="after")
    def normalize_contact(self):
        self.name = self.name.strip()
        self.phone = self.phone.strip()
        self.alternate_phone = (
            (self.alternate_phone or "").strip() or None
        )
        self.notes = (self.notes or "").strip() or None
        return self
