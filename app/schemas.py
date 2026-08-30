"""
Pydantic schemas for request validation and response serialization.
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, validator


# ===== Plan Schemas =====
class PlanCreate(BaseModel):
    """Schema for creating a new plan."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1024)
    billing_cycle: str = Field(..., description="monthly, quarterly, yearly, or custom")
    price: Decimal = Field(..., gt=0, decimal_places=2)
    currency: str = Field("USD", max_length=3)

    @validator('price')
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Plan price must be greater than 0')
        return v


class PlanUpdate(BaseModel):
    """Schema for updating a plan."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1024)
    status: Optional[str] = None


class PlanResponse(BaseModel):
    """Schema for plan API response."""
    id: int
    name: str
    description: Optional[str]
    billing_cycle: str
    price: Decimal
    currency: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===== Customer Schemas =====
class CustomerCreate(BaseModel):
    """Schema for creating a new customer."""
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    company_name: Optional[str] = Field(None, max_length=255)

    @validator('email')
    def email_must_be_unique(cls, v):
        return v


class CustomerUpdate(BaseModel):
    """Schema for updating a customer."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    company_name: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = None


class CustomerResponse(BaseModel):
    """Schema for customer API response."""
    id: int
    name: str
    email: str
    company_name: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===== Subscription Schemas =====
class SubscriptionCreate(BaseModel):
    """Schema for creating a new subscription."""
    customer_id: int = Field(...)
    plan_id: int = Field(...)


class SubscriptionCancel(BaseModel):
    """Schema for cancelling a subscription."""
    reason: Optional[str] = Field(None, max_length=1024)


class SubscriptionResponse(BaseModel):
    """Schema for subscription API response."""
    id: int
    customer_id: int
    plan_id: int
    status: str
    start_date: datetime
    current_period_start: datetime
    current_period_end: datetime
    cancelled_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    plan: Optional[PlanResponse] = None
    customer: Optional[CustomerResponse] = None

    class Config:
        from_attributes = True


# ===== Invoice Schemas =====
class InvoiceGenerate(BaseModel):
    """Schema for generating an invoice."""
    subscription_id: int = Field(...)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class InvoiceResponse(BaseModel):
    """Schema for invoice API response."""
    id: int
    subscription_id: int
    customer_id: int
    amount_due: Decimal
    amount_paid: Decimal
    currency: str
    status: str
    period_start: datetime
    period_end: datetime
    due_date: datetime
    created_at: datetime
    updated_at: datetime
    subscription: Optional[SubscriptionResponse] = None
    customer: Optional[CustomerResponse] = None

    class Config:
        from_attributes = True


# ===== Payment Schemas =====
class PaymentRecord(BaseModel):
    """Schema for recording a payment attempt."""
    invoice_id: int = Field(...)
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    currency: str = Field("USD", max_length=3)
    status: str = Field(..., description="success or failed")
    provider_reference: str = Field(..., max_length=255)
    failure_reason: Optional[str] = Field(None, max_length=1024)

    @validator('status')
    def status_must_be_valid(cls, v):
        if v not in ["success", "failed"]:
            raise ValueError('Status must be success or failed')
        return v


class PaymentAttemptResponse(BaseModel):
    """Schema for payment attempt API response."""
    id: int
    invoice_id: int
    amount: Decimal
    currency: str
    status: str
    provider_reference: str
    failure_reason: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Ledger Schemas =====
class LedgerEntryResponse(BaseModel):
    """Schema for ledger entry API response."""
    id: int
    customer_id: int
    invoice_id: Optional[int]
    entry_type: str
    amount: Optional[Decimal]
    currency: Optional[str]
    reference_id: Optional[str]
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class CustomerLedgerResponse(BaseModel):
    """Schema for customer ledger history."""
    customer_id: int
    entries: List[LedgerEntryResponse]


# ===== Generic Schemas =====
class ErrorResponse(BaseModel):
    """Schema for error responses."""
    detail: str
    error_code: Optional[str] = None


class SuccessResponse(BaseModel):
    """Schema for generic success responses."""
    message: str
    data: Optional[dict] = None
