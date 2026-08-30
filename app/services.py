"""
Service layer containing all business logic.
Services orchestrate repositories, enforce business rules, and manage workflows.
"""
from datetime import datetime, timedelta
from decimal import Decimal
import sys

if sys.version_info >= (3, 11):
    from datetime import UTC
else:
    from datetime import timezone
    UTC = timezone.utc

from sqlalchemy.orm import Session

from app.models import (
    InvoiceStatus,
    LedgerEntryType,
    PaymentAttemptStatus,
    SubscriptionStatus,
)
from app.repositories import (
    CustomerRepository,
    InvoiceRepository,
    LedgerRepository,
    PaymentAttemptRepository,
    PlanRepository,
    SubscriptionRepository,
)


class PlanService:
    """Business logic for Plans."""

    @staticmethod
    def create_plan(db: Session, name: str, description: str, billing_cycle: str,
                    price: Decimal, currency: str) -> dict:
        """Create a new plan with validation."""
        if price <= 0:
            raise ValueError("Plan price must be greater than 0")

        valid_cycles = ["monthly", "quarterly", "yearly", "custom"]
        if billing_cycle not in valid_cycles:
            raise ValueError(f"Invalid billing cycle. Must be one of: {valid_cycles}")

        plan = PlanRepository.create(
            db, name, description, billing_cycle, price, currency
        )
        return {
            "id": plan.id,
            "name": plan.name,
            "description": plan.description,
            "billing_cycle": plan.billing_cycle,
            "price": plan.price,
            "currency": plan.currency,
            "status": plan.status,
            "created_at": plan.created_at,
            "updated_at": plan.updated_at
        }

    @staticmethod
    def get_plan(db: Session, plan_id: int) -> dict:
        """Fetch plan by ID."""
        plan = PlanRepository.get_by_id(db, plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        return {
            "id": plan.id,
            "name": plan.name,
            "description": plan.description,
            "billing_cycle": plan.billing_cycle,
            "price": plan.price,
            "currency": plan.currency,
            "status": plan.status,
            "created_at": plan.created_at,
            "updated_at": plan.updated_at
        }

    @staticmethod
    def list_plans(db: Session, skip: int = 0, limit: int = 100) -> list:
        """List all plans."""
        plans = PlanRepository.get_all(db, skip, limit)
        return [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "billing_cycle": p.billing_cycle,
                "price": p.price,
                "currency": p.currency,
                "status": p.status,
                "created_at": p.created_at,
                "updated_at": p.updated_at
            }
            for p in plans
        ]

    @staticmethod
    def deactivate_plan(db: Session, plan_id: int) -> dict:
        """Deactivate a plan."""
        plan = PlanRepository.get_by_id(db, plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        plan = PlanRepository.update_status(db, plan_id, "inactive")
        return {
            "id": plan.id,
            "name": plan.name,
            "status": plan.status,
            "updated_at": plan.updated_at
        }


class CustomerService:
    """Business logic for Customers."""

    @staticmethod
    def create_customer(db: Session, name: str, email: str, company_name: str = None) -> dict:
        """Create a new customer with validation."""
        if CustomerRepository.email_exists(db, email):
            raise ValueError(f"Customer with email {email} already exists")

        customer = CustomerRepository.create(db, name, email, company_name)
        return {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "company_name": customer.company_name,
            "status": customer.status,
            "created_at": customer.created_at,
            "updated_at": customer.updated_at
        }

    @staticmethod
    def get_customer(db: Session, customer_id: int) -> dict:
        """Fetch customer by ID."""
        customer = CustomerRepository.get_by_id(db, customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")
        return {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "company_name": customer.company_name,
            "status": customer.status,
            "created_at": customer.created_at,
            "updated_at": customer.updated_at
        }

    @staticmethod
    def list_customers(db: Session, skip: int = 0, limit: int = 100) -> list:
        """List all customers."""
        customers = CustomerRepository.get_all(db, skip, limit)
        return [
            {
                "id": c.id,
                "name": c.name,
                "email": c.email,
                "company_name": c.company_name,
                "status": c.status,
                "created_at": c.created_at,
                "updated_at": c.updated_at
            }
            for c in customers
        ]


class SubscriptionService:
    """Business logic for Subscriptions."""

    @staticmethod
    def create_subscription(db: Session, customer_id: int, plan_id: int) -> dict:
        """Create a new subscription with business rule validation."""
        customer = CustomerRepository.get_by_id(db, customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")

        plan = PlanRepository.get_by_id(db, plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        if plan.status != "active":
            raise ValueError("Cannot create subscription to an inactive plan")

        existing = SubscriptionRepository.get_by_customer_and_plan(db, customer_id, plan_id)
        if existing:
            raise ValueError(f"Customer already has an active subscription to plan {plan_id}")

        start_date = datetime.now(UTC)
        if plan.billing_cycle == "monthly":
            end_date = start_date + timedelta(days=30)
        elif plan.billing_cycle == "quarterly":
            end_date = start_date + timedelta(days=90)
        elif plan.billing_cycle == "yearly":
            end_date = start_date + timedelta(days=365)
        else:
            end_date = start_date + timedelta(days=30)

        subscription = SubscriptionRepository.create(
            db, customer_id, plan_id, start_date, start_date, end_date
        )

        LedgerService.log_subscription_created(db, customer_id, subscription.id)

        return {
            "id": subscription.id,
            "customer_id": subscription.customer_id,
            "plan_id": subscription.plan_id,
            "status": subscription.status,
            "start_date": subscription.start_date,
            "current_period_start": subscription.current_period_start,
            "current_period_end": subscription.current_period_end,
            "cancelled_at": subscription.cancelled_at,
            "created_at": subscription.created_at,
            "updated_at": subscription.updated_at
        }

    @staticmethod
    def get_subscription(db: Session, subscription_id: int) -> dict:
        """Fetch subscription by ID."""
        subscription = SubscriptionRepository.get_by_id(db, subscription_id)
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")
        return {
            "id": subscription.id,
            "customer_id": subscription.customer_id,
            "plan_id": subscription.plan_id,
            "status": subscription.status,
            "start_date": subscription.start_date,
            "current_period_start": subscription.current_period_start,
            "current_period_end": subscription.current_period_end,
            "cancelled_at": subscription.cancelled_at,
            "created_at": subscription.created_at,
            "updated_at": subscription.updated_at
        }

    @staticmethod
    def list_subscriptions(db: Session, skip: int = 0, limit: int = 100) -> list:
        """List all subscriptions."""
        subscriptions = SubscriptionRepository.get_all(db, skip, limit)
        return [
            {
                "id": s.id,
                "customer_id": s.customer_id,
                "plan_id": s.plan_id,
                "status": s.status,
                "start_date": s.start_date,
                "current_period_start": s.current_period_start,
                "current_period_end": s.current_period_end,
                "cancelled_at": s.cancelled_at,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
            }
            for s in subscriptions
        ]

    @staticmethod
    def cancel_subscription(db: Session, subscription_id: int) -> dict:
        """Cancel a subscription."""
        subscription = SubscriptionRepository.get_by_id(db, subscription_id)
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")

        if subscription.status == SubscriptionStatus.CANCELLED:
            raise ValueError(f"Cannot cancel subscription {subscription_id}: it is already cancelled")

        cancelled_at = datetime.now(UTC)
        subscription = SubscriptionRepository.update_status(
            db, subscription_id, SubscriptionStatus.CANCELLED, cancelled_at
        )

        LedgerService.log_subscription_cancelled(db, subscription.customer_id, subscription.id)

        return {
            "id": subscription.id,
            "customer_id": subscription.customer_id,
            "plan_id": subscription.plan_id,
            "status": subscription.status,
            "cancelled_at": subscription.cancelled_at,
            "updated_at": subscription.updated_at,
        }


class InvoiceService:
    """Business logic for Invoices."""

    @staticmethod
    def generate_invoice(db: Session, subscription_id: int, period_start: datetime = None, period_end: datetime = None) -> dict:
        """Generate an invoice for a subscription."""
        subscription = SubscriptionRepository.get_by_id(db, subscription_id)
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")

        plan = PlanRepository.get_by_id(db, subscription.plan_id)
        if not plan:
            raise ValueError(f"Plan {subscription.plan_id} not found")

        if not period_start:
            period_start = subscription.current_period_start
        if not period_end:
            period_end = subscription.current_period_end

        invoice = InvoiceRepository.create(
            db,
            subscription_id,
            subscription.customer_id,
            plan.price,
            plan.currency,
            InvoiceStatus.ISSUED,
            period_start,
            period_end,
            period_end,
        )

        LedgerService.log_invoice_created(db, subscription.customer_id, invoice.id, plan.price, plan.currency, invoice.id)

        return {
            "id": invoice.id,
            "subscription_id": invoice.subscription_id,
            "customer_id": invoice.customer_id,
            "amount_due": invoice.amount_due,
            "amount_paid": invoice.amount_paid,
            "currency": invoice.currency,
            "status": invoice.status,
            "period_start": invoice.period_start,
            "period_end": invoice.period_end,
            "due_date": invoice.due_date,
            "created_at": invoice.created_at,
            "updated_at": invoice.updated_at,
        }

    @staticmethod
    def get_invoice(db: Session, invoice_id: int) -> dict:
        """Fetch invoice by ID."""
        invoice = InvoiceRepository.get_by_id(db, invoice_id)
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")
        return {
            "id": invoice.id,
            "subscription_id": invoice.subscription_id,
            "customer_id": invoice.customer_id,
            "amount_due": invoice.amount_due,
            "amount_paid": invoice.amount_paid,
            "currency": invoice.currency,
            "status": invoice.status,
            "period_start": invoice.period_start,
            "period_end": invoice.period_end,
            "due_date": invoice.due_date,
            "created_at": invoice.created_at,
            "updated_at": invoice.updated_at,
        }


class PaymentService:
    """Business logic for Payments."""

    @staticmethod
    def record_payment(db: Session, invoice_id: int, amount: Decimal, currency: str,
                       status: str, provider_reference: str, failure_reason: str = None) -> dict:
        """Record a payment attempt and update invoice."""
        invoice = InvoiceRepository.get_by_id(db, invoice_id)
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")

        existing_payment = PaymentAttemptRepository.get_by_provider_reference(db, provider_reference)
        if existing_payment:
            return {
                "id": existing_payment.id,
                "invoice_id": existing_payment.invoice_id,
                "amount": existing_payment.amount,
                "currency": existing_payment.currency,
                "status": existing_payment.status,
                "provider_reference": existing_payment.provider_reference,
                "failure_reason": existing_payment.failure_reason,
                "created_at": existing_payment.created_at,
                "message": "Payment already recorded (idempotent request)"
            }

        if status == "failed":
            payment = PaymentAttemptRepository.create(
                db, invoice_id, amount, currency, PaymentAttemptStatus.FAILED,
                provider_reference, failure_reason
            )
            LedgerService.log_payment_failed(db, invoice.customer_id, invoice_id, amount, currency, payment.id)
            return {
                "id": payment.id,
                "invoice_id": payment.invoice_id,
                "amount": payment.amount,
                "currency": payment.currency,
                "status": payment.status,
                "provider_reference": payment.provider_reference,
                "failure_reason": payment.failure_reason,
                "created_at": payment.created_at,
            }

        remaining = invoice.amount_due - invoice.amount_paid
        if amount > remaining:
            raise ValueError(f"Payment amount {amount} exceeds unpaid amount")

        payment = PaymentAttemptRepository.create(
            db, invoice_id, amount, currency, PaymentAttemptStatus.SUCCESS,
            provider_reference, failure_reason
        )

        new_amount_paid = invoice.amount_paid + amount
        if new_amount_paid >= invoice.amount_due:
            new_status = InvoiceStatus.PAID
        else:
            new_status = InvoiceStatus.PARTIALLY_PAID

        InvoiceRepository.update_payment_status(db, invoice_id, new_amount_paid, new_status)
        LedgerService.log_payment_success(db, invoice.customer_id, invoice_id, amount, currency, payment.id)

        return {
            "id": payment.id,
            "invoice_id": payment.invoice_id,
            "amount": payment.amount,
            "currency": payment.currency,
            "status": payment.status,
            "provider_reference": payment.provider_reference,
            "failure_reason": payment.failure_reason,
            "created_at": payment.created_at,
        }


class LedgerService:
    """Business logic for ledger entries."""

    @staticmethod
    def log_subscription_created(db: Session, customer_id: int, subscription_id: int):
        """Log a subscription creation event."""
        LedgerRepository.create(
            db,
            customer_id,
            LedgerEntryType.SUBSCRIPTION_CREATED,
            amount=None,
            currency=None,
            invoice_id=None,
            reference_id=str(subscription_id),
            description="Subscription created"
        )

    @staticmethod
    def log_subscription_cancelled(db: Session, customer_id: int, subscription_id: int):
        """Log a subscription cancellation event."""
        LedgerRepository.create(
            db,
            customer_id,
            LedgerEntryType.SUBSCRIPTION_CANCELLED,
            amount=None,
            currency=None,
            invoice_id=None,
            reference_id=str(subscription_id),
            description="Subscription cancelled"
        )

    @staticmethod
    def log_invoice_created(db: Session, customer_id: int, invoice_id: int, amount: Decimal, currency: str, reference_id: int):
        """Log invoice creation event."""
        LedgerRepository.create(
            db,
            customer_id,
            LedgerEntryType.INVOICE_CREATED,
            amount=amount,
            currency=currency,
            invoice_id=invoice_id,
            reference_id=str(reference_id),
            description="Invoice created"
        )

    @staticmethod
    def log_payment_success(db: Session, customer_id: int, invoice_id: int, amount: Decimal, currency: str, payment_attempt_id: int):
        """Log successful payment."""
        LedgerRepository.create(
            db,
            customer_id,
            LedgerEntryType.PAYMENT_SUCCESS,
            amount=amount,
            currency=currency,
            invoice_id=invoice_id,
            reference_id=str(payment_attempt_id),
            description="Payment successful"
        )

    @staticmethod
    def log_payment_failed(db: Session, customer_id: int, invoice_id: int, amount: Decimal, currency: str, payment_attempt_id: int):
        """Log failed payment."""
        LedgerRepository.create(
            db,
            customer_id,
            LedgerEntryType.PAYMENT_FAILED,
            amount=amount,
            currency=currency,
            invoice_id=invoice_id,
            reference_id=str(payment_attempt_id),
            description="Payment failed"
        )

    @staticmethod
    def get_customer_ledger(db: Session, customer_id: int, skip: int = 0, limit: int = 100) -> dict:
        """Get customer ledger history."""
        customer = CustomerRepository.get_by_id(db, customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")
        entries = LedgerRepository.get_by_customer(db, customer_id, skip, limit)
        return {
            "customer_id": customer_id,
            "entries": [
                {
                    "id": e.id,
                    "customer_id": e.customer_id,
                    "invoice_id": e.invoice_id,
                    "entry_type": e.entry_type,
                    "amount": e.amount,
                    "currency": e.currency,
                    "reference_id": e.reference_id,
                    "description": e.description,
                    "created_at": e.created_at,
                }
                for e in entries
            ],
        }
