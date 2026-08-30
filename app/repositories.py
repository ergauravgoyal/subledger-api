"""
Repository layer for data access.
Each repository handles database operations for its entity.
"""
import sys
from datetime import datetime
from decimal import Decimal

if sys.version_info >= (3, 11):
    from datetime import UTC
else:
    from datetime import timezone
    UTC = timezone.utc

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from app.models import (
    Customer,
    CustomerStatus,
    Invoice,
    LedgerEntry,
    PaymentAttempt,
    Plan,
    PlanStatus,
    Subscription,
    SubscriptionStatus,
)


class PlanRepository:
    """Repository for Plan entity."""

    @staticmethod
    def create(db: Session, name: str, description: str, billing_cycle: str,
               price: Decimal, currency: str) -> Plan:
        """Create a new plan."""
        plan = Plan(
            name=name,
            description=description,
            billing_cycle=billing_cycle,
            price=price,
            currency=currency,
            status=PlanStatus.ACTIVE
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        return plan

    @staticmethod
    def get_by_id(db: Session, plan_id: int) -> Plan:
        """Fetch plan by ID."""
        return db.query(Plan).filter(Plan.id == plan_id).first()

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> list:
        """Fetch all plans with pagination."""
        return db.query(Plan).offset(skip).limit(limit).all()

    @staticmethod
    def update_status(db: Session, plan_id: int, status: str) -> Plan:
        """Update plan status."""
        plan = PlanRepository.get_by_id(db, plan_id)
        if plan:
            plan.status = status
            plan.updated_at = datetime.now(UTC)
            db.commit()
            db.refresh(plan)
        return plan


class CustomerRepository:
    """Repository for Customer entity."""

    @staticmethod
    def create(db: Session, name: str, email: str, company_name: str = None) -> Customer:
        """Create a new customer."""
        customer = Customer(
            name=name,
            email=email,
            company_name=company_name,
            status=CustomerStatus.ACTIVE
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        return customer

    @staticmethod
    def get_by_id(db: Session, customer_id: int) -> Customer:
        """Fetch customer by ID."""
        return db.query(Customer).filter(Customer.id == customer_id).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Customer:
        """Fetch customer by email."""
        return db.query(Customer).filter(Customer.email == email).first()

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> list:
        """Fetch all customers with pagination."""
        return db.query(Customer).offset(skip).limit(limit).all()

    @staticmethod
    def email_exists(db: Session, email: str) -> bool:
        """Check if email already exists."""
        return db.query(Customer).filter(Customer.email == email).first() is not None

    @staticmethod
    def update_status(db: Session, customer_id: int, status: str) -> Customer:
        """Update customer status."""
        customer = CustomerRepository.get_by_id(db, customer_id)
        if customer:
            customer.status = status
            customer.updated_at = datetime.now(UTC)
            db.commit()
            db.refresh(customer)
        return customer


class SubscriptionRepository:
    """Repository for Subscription entity."""

    @staticmethod
    def create(db: Session, customer_id: int, plan_id: int, start_date: datetime,
               current_period_start: datetime, current_period_end: datetime) -> Subscription:
        """Create a new subscription."""
        subscription = Subscription(
            customer_id=customer_id,
            plan_id=plan_id,
            status=SubscriptionStatus.ACTIVE,
            start_date=start_date,
            current_period_start=current_period_start,
            current_period_end=current_period_end
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        return subscription

    @staticmethod
    def get_by_id(db: Session, subscription_id: int) -> Subscription:
        """Fetch subscription by ID."""
        return db.query(Subscription).filter(Subscription.id == subscription_id).first()

    @staticmethod
    def get_by_customer_and_plan(db: Session, customer_id: int, plan_id: int) -> Subscription:
        """Fetch active subscription for customer and plan."""
        return db.query(Subscription).filter(
            and_(
                Subscription.customer_id == customer_id,
                Subscription.plan_id == plan_id,
                Subscription.status == SubscriptionStatus.ACTIVE
            )
        ).first()

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> list:
        """Fetch all subscriptions with pagination."""
        return db.query(Subscription).offset(skip).limit(limit).all()

    @staticmethod
    def get_by_customer(db: Session, customer_id: int, skip: int = 0, limit: int = 100) -> list:
        """Fetch subscriptions for a customer."""
        return db.query(Subscription).filter(
            Subscription.customer_id == customer_id
        ).offset(skip).limit(limit).all()

    @staticmethod
    def update_status(db: Session, subscription_id: int, status: str, cancelled_at: datetime = None) -> Subscription:
        """Update subscription status."""
        subscription = SubscriptionRepository.get_by_id(db, subscription_id)
        if subscription:
            subscription.status = status
            subscription.cancelled_at = cancelled_at
            subscription.updated_at = datetime.now(UTC)
            db.commit()
            db.refresh(subscription)
        return subscription


class InvoiceRepository:
    """Repository for Invoice entity."""

    @staticmethod
    def create(db: Session, subscription_id: int, customer_id: int, amount_due: Decimal,
               currency: str, status: str, period_start: datetime, period_end: datetime,
               due_date: datetime) -> Invoice:
        """Create a new invoice."""
        invoice = Invoice(
            subscription_id=subscription_id,
            customer_id=customer_id,
            amount_due=amount_due,
            amount_paid=Decimal("0.00"),
            currency=currency,
            status=status,
            period_start=period_start,
            period_end=period_end,
            due_date=due_date
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        return invoice

    @staticmethod
    def get_by_id(db: Session, invoice_id: int) -> Invoice:
        """Fetch invoice by ID."""
        return db.query(Invoice).filter(Invoice.id == invoice_id).first()

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> list:
        """Fetch all invoices with pagination."""
        return db.query(Invoice).offset(skip).limit(limit).all()

    @staticmethod
    def get_by_customer(db: Session, customer_id: int, skip: int = 0, limit: int = 100) -> list:
        """Fetch invoices for a customer."""
        return db.query(Invoice).filter(
            Invoice.customer_id == customer_id
        ).offset(skip).limit(limit).all()

    @staticmethod
    def get_by_subscription(db: Session, subscription_id: int) -> list:
        """Fetch invoices for a subscription."""
        return db.query(Invoice).filter(
            Invoice.subscription_id == subscription_id
        ).order_by(desc(Invoice.created_at)).all()

    @staticmethod
    def update_payment_status(db: Session, invoice_id: int, amount_paid: Decimal, status: str) -> Invoice:
        """Update invoice payment status and amount_paid."""
        invoice = InvoiceRepository.get_by_id(db, invoice_id)
        if invoice:
            invoice.amount_paid = amount_paid
            invoice.status = status
            invoice.updated_at = datetime.now(UTC)
            db.commit()
            db.refresh(invoice)
        return invoice


class PaymentAttemptRepository:
    """Repository for PaymentAttempt entity."""

    @staticmethod
    def create(db: Session, invoice_id: int, amount: Decimal, currency: str,
               status: str, provider_reference: str, failure_reason: str = None) -> PaymentAttempt:
        """Create a new payment attempt."""
        payment_attempt = PaymentAttempt(
            invoice_id=invoice_id,
            amount=amount,
            currency=currency,
            status=status,
            provider_reference=provider_reference,
            failure_reason=failure_reason
        )
        db.add(payment_attempt)
        db.commit()
        db.refresh(payment_attempt)
        return payment_attempt

    @staticmethod
    def get_by_id(db: Session, payment_attempt_id: int) -> PaymentAttempt:
        """Fetch payment attempt by ID."""
        return db.query(PaymentAttempt).filter(PaymentAttempt.id == payment_attempt_id).first()

    @staticmethod
    def get_by_provider_reference(db: Session, provider_reference: str) -> PaymentAttempt:
        """Fetch a payment attempt by external provider reference."""
        return db.query(PaymentAttempt).filter(
            PaymentAttempt.provider_reference == provider_reference
        ).first()

    @staticmethod
    def get_by_invoice(db: Session, invoice_id: int) -> list:
        """Fetch payment attempts for an invoice."""
        return db.query(PaymentAttempt).filter(PaymentAttempt.invoice_id == invoice_id).order_by(desc(PaymentAttempt.created_at)).all()


class LedgerRepository:
    """Repository for LedgerEntry entity."""

    @staticmethod
    def create(db: Session, customer_id: int, entry_type: str, amount: Decimal = None,
               currency: str = None, invoice_id: int = None, reference_id: str = None,
               description: str = None) -> LedgerEntry:
        """Create a ledger entry."""
        ledger_entry = LedgerEntry(
            customer_id=customer_id,
            invoice_id=invoice_id,
            entry_type=entry_type,
            amount=amount,
            currency=currency,
            reference_id=reference_id,
            description=description
        )
        db.add(ledger_entry)
        db.commit()
        db.refresh(ledger_entry)
        return ledger_entry

    @staticmethod
    def get_by_customer(db: Session, customer_id: int, skip: int = 0, limit: int = 100) -> list:
        """Fetch ledger entries for a customer."""
        return db.query(LedgerEntry).filter(
            LedgerEntry.customer_id == customer_id
        ).order_by(desc(LedgerEntry.created_at)).offset(skip).limit(limit).all()
