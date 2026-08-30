"""
Database models for SubLedger.
Implements the domain entities: Plan, Customer, Subscription, Invoice, PaymentAttempt, and LedgerEntry.
"""
import enum
import sys
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import relationship

from app.db import Base

if sys.version_info >= (3, 11):
    from datetime import UTC
else:
    from datetime import timezone
    UTC = timezone.utc


def utc_now():
    """Return current UTC datetime."""
    return datetime.now(UTC)


class PlanStatus(str, enum.Enum):
    """Status values for plans."""
    ACTIVE = "active"
    INACTIVE = "inactive"


class BillingCycle(str, enum.Enum):
    """Billing cycle options for plans."""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class CustomerStatus(str, enum.Enum):
    """Status values for customers."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class SubscriptionStatus(str, enum.Enum):
    """Status values for subscriptions."""
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class InvoiceStatus(str, enum.Enum):
    """Status values for invoices."""
    DRAFT = "draft"
    ISSUED = "issued"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    OVERDUE = "overdue"
    VOID = "void"


class PaymentAttemptStatus(str, enum.Enum):
    """Status values for payment attempts."""
    SUCCESS = "success"
    FAILED = "failed"


class LedgerEntryType(str, enum.Enum):
    """Types of ledger entries."""
    INVOICE_CREATED = "invoice_created"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    INVOICE_VOID = "invoice_void"
    SUBSCRIPTION_CREATED = "subscription_created"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"


class Plan(Base):
    """Plan entity: defines pricing and billing terms."""
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1024), nullable=True)
    billing_cycle = Column(Enum(BillingCycle), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    status = Column(Enum(PlanStatus), default=PlanStatus.ACTIVE, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    subscriptions = relationship("Subscription", back_populates="plan")


class Customer(Base):
    """Customer entity: represents a customer account."""
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    company_name = Column(String(255), nullable=True)
    status = Column(Enum(CustomerStatus), default=CustomerStatus.ACTIVE, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    subscriptions = relationship("Subscription", back_populates="customer")
    invoices = relationship("Invoice", back_populates="customer")
    ledger_entries = relationship("LedgerEntry", back_populates="customer")


class Subscription(Base):
    """Subscription entity: links a customer to a plan."""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False, index=True)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE, nullable=False)
    start_date = Column(DateTime, nullable=False)
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    cancelled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    customer = relationship("Customer", back_populates="subscriptions")
    plan = relationship("Plan", back_populates="subscriptions")
    invoices = relationship("Invoice", back_populates="subscription")


class Invoice(Base):
    """Invoice entity: represents a billing statement."""
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    amount_due = Column(Numeric(10, 2), nullable=False)
    amount_paid = Column(Numeric(10, 2), default=0, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT, nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    due_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    subscription = relationship("Subscription", back_populates="invoices")
    customer = relationship("Customer", back_populates="invoices")
    payment_attempts = relationship("PaymentAttempt", back_populates="invoice")
    ledger_entries = relationship("LedgerEntry", back_populates="invoice")


class PaymentAttempt(Base):
    """PaymentAttempt entity: records payment transactions."""
    __tablename__ = "payment_attempts"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    status = Column(Enum(PaymentAttemptStatus), nullable=False)
    provider_reference = Column(String(255), nullable=False, unique=True)
    failure_reason = Column(String(1024), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    invoice = relationship("Invoice", back_populates="payment_attempts")


class LedgerEntry(Base):
    """LedgerEntry entity: append-only audit log of all ledger events."""
    __tablename__ = "ledger_entries"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True, index=True)
    entry_type = Column(Enum(LedgerEntryType), nullable=False)
    amount = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(3), nullable=True)
    reference_id = Column(String(255), nullable=True, index=True)
    description = Column(String(1024), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)

    customer = relationship("Customer", back_populates="ledger_entries")
    invoice = relationship("Invoice", back_populates="ledger_entries")
