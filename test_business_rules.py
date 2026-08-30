"""
Test suite for SubLedger business rules and critical workflows.
"""
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from app.db import Base
from app.models import (
    Customer,
    Invoice,
    InvoiceStatus,
    LedgerEntry,
    PaymentAttempt,
    Plan,
    Subscription,
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
from app.services import (
    CustomerService,
    InvoiceService,
    LedgerService,
    PaymentService,
    PlanService,
    SubscriptionService,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# Test database setup
@pytest.fixture(scope="function")
def test_db():
    """Create in-memory test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()


# ===== Test Fixtures =====
@pytest.fixture
def sample_plan(test_db):
    """Create a sample plan for testing."""
    return PlanService.create_plan(
        test_db, "Premium Plan", "Premium features", "monthly", 
        Decimal("99.99"), "USD"
    )


@pytest.fixture
def sample_customer(test_db):
    """Create a sample customer for testing."""
    return CustomerService.create_customer(
        test_db, "John Doe", "john@example.com", "Acme Corp"
    )


@pytest.fixture
def sample_subscription(test_db, sample_plan, sample_customer):
    """Create a sample subscription for testing."""
    return SubscriptionService.create_subscription(
        test_db, sample_customer["id"], sample_plan["id"]
    )


# ===== Test 1: Plan price must be greater than 0 =====
def test_plan_price_must_be_positive(test_db):
    """
    BUSINESS RULE: Plan price must be greater than 0.
    
    Test that creating a plan with price <= 0 raises an error.
    """
    with pytest.raises(ValueError, match="Plan price must be greater than 0"):
        PlanService.create_plan(
            test_db, "Invalid Plan", "Should fail", "monthly",
            Decimal("0.00"), "USD"
        )

    with pytest.raises(ValueError, match="Plan price must be greater than 0"):
        PlanService.create_plan(
            test_db, "Invalid Plan", "Should fail", "monthly",
            Decimal("-50.00"), "USD"
        )


# ===== Test 2: Customer email must be unique =====
def test_customer_email_must_be_unique(test_db):
    """
    BUSINESS RULE: Customer email must be unique.
    
    Test that creating two customers with the same email fails.
    """
    CustomerService.create_customer(
        test_db, "John Doe", "john@example.com", "Company 1"
    )

    with pytest.raises(ValueError, match="Customer with email john@example.com already exists"):
        CustomerService.create_customer(
            test_db, "John Doe 2", "john@example.com", "Company 2"
        )


# ===== Test 3: Cannot subscribe to inactive plan =====
def test_cannot_subscribe_to_inactive_plan(test_db):
    """
    BUSINESS RULE: A subscription cannot be created for an inactive plan.
    
    Test that trying to subscribe to an inactive plan fails.
    """
    # Create a plan
    plan = PlanService.create_plan(
        test_db, "Basic Plan", "Basic", "monthly", 
        Decimal("49.99"), "USD"
    )

    # Create a customer
    customer = CustomerService.create_customer(
        test_db, "Jane Doe", "jane@example.com", "Tech Corp"
    )

    # Deactivate the plan
    PlanService.deactivate_plan(test_db, plan["id"])

    # Try to subscribe to inactive plan
    with pytest.raises(ValueError, match="Cannot create subscription to an inactive plan"):
        SubscriptionService.create_subscription(test_db, customer["id"], plan["id"])


# ===== Test 4: No duplicate active subscriptions to same plan =====
def test_no_duplicate_active_subscriptions(test_db, sample_plan, sample_customer):
    """
    BUSINESS RULE: A customer cannot have two active subscriptions to the same plan.
    
    Test that creating a second active subscription to the same plan fails.
    """
    # First subscription should succeed
    SubscriptionService.create_subscription(
        test_db, sample_customer["id"], sample_plan["id"]
    )

    # Second subscription to same plan should fail
    with pytest.raises(ValueError, match="Customer already has an active subscription"):
        SubscriptionService.create_subscription(
            test_db, sample_customer["id"], sample_plan["id"]
        )


# ===== Test 5: Payment cannot exceed unpaid amount =====
def test_payment_cannot_exceed_unpaid_amount(test_db, sample_subscription, sample_plan):
    """
    BUSINESS RULE: A successful payment cannot exceed the remaining unpaid amount on the invoice.
    
    Test that payment validation prevents overpayment.
    """
    # Generate an invoice
    invoice = InvoiceService.generate_invoice(test_db, sample_subscription["id"])

    # Calculate unpaid amount
    unpaid_amount = invoice["amount_due"] - invoice["amount_paid"]

    # Try to pay more than unpaid amount
    with pytest.raises(ValueError, match="Payment amount .* exceeds unpaid amount"):
        PaymentService.record_payment(
            test_db,
            invoice["id"],
            unpaid_amount + Decimal("10.00"),
            "USD",
            "success",
            "PROVIDER-REF-001"
        )


# ===== Test 6: Invoice amount_due comes from plan price =====
def test_invoice_amount_due_from_plan_price(test_db, sample_subscription, sample_plan):
    """
    BUSINESS RULE: Invoice amount_due should come from the plan price at the time invoice is generated.
    
    Test that invoice amount_due equals plan price.
    """
    invoice = InvoiceService.generate_invoice(test_db, sample_subscription["id"])

    assert invoice["amount_due"] == sample_plan["price"]
    assert invoice["currency"] == sample_plan["currency"]


# ===== Test 7: Successful payment updates invoice status =====
def test_successful_payment_updates_invoice_status(test_db, sample_subscription):
    """
    BUSINESS RULE: A fully paid invoice should move to paid status; 
    a partial payment should move to partially_paid status.
    
    Test invoice status transitions after successful payments.
    """
    # Generate invoice
    invoice = InvoiceService.generate_invoice(test_db, sample_subscription["id"])
    assert invoice["status"] == InvoiceStatus.ISSUED

    # Partial payment
    partial_amount = (invoice["amount_due"] / 2).quantize(Decimal('0.01'))
    payment1 = PaymentService.record_payment(
        test_db,
        invoice["id"],
        partial_amount,
        "USD",
        "success",
        "PAYMENT-001"
    )
    
    # Fetch updated invoice
    updated_invoice = InvoiceService.get_invoice(test_db, invoice["id"])
    assert updated_invoice["status"] == InvoiceStatus.PARTIALLY_PAID
    assert updated_invoice["amount_paid"] == partial_amount

    # Full payment
    remaining = invoice["amount_due"] - partial_amount
    payment2 = PaymentService.record_payment(
        test_db,
        invoice["id"],
        remaining,
        "USD",
        "success",
        "PAYMENT-002"
    )

    # Fetch fully paid invoice
    fully_paid_invoice = InvoiceService.get_invoice(test_db, invoice["id"])
    assert fully_paid_invoice["status"] == InvoiceStatus.PAID
    assert fully_paid_invoice["amount_paid"] == invoice["amount_due"]


# ===== Test 8: Failed payment does not increase amount_paid =====
def test_failed_payment_does_not_increase_amount_paid(test_db, sample_subscription):
    """
    BUSINESS RULE: A failed payment should not increase amount_paid.
    
    Test that failed payments don't affect invoice amount_paid.
    """
    invoice = InvoiceService.generate_invoice(test_db, sample_subscription["id"])
    initial_amount_paid = invoice["amount_paid"]

    # Record failed payment
    PaymentService.record_payment(
        test_db,
        invoice["id"],
        Decimal("50.00"),
        "USD",
        "failed",
        "FAILED-PAYMENT-001",
        "Card declined"
    )

    # Check that amount_paid didn't change
    updated_invoice = InvoiceService.get_invoice(test_db, invoice["id"])
    assert updated_invoice["amount_paid"] == initial_amount_paid
    assert updated_invoice["status"] == InvoiceStatus.ISSUED


# ===== Test 9: Ledger entries are append-only =====
def test_ledger_entries_are_append_only(test_db, sample_subscription, sample_customer):
    """
    BUSINESS RULE: Ledger entries should be append-only and traceable through reference_id.
    
    Test that ledger entries are created and can be traced.
    """
    # Generate invoice (creates ledger entry)
    invoice = InvoiceService.generate_invoice(test_db, sample_subscription["id"])

    # Get customer ledger
    ledger = LedgerService.get_customer_ledger(test_db, sample_customer["id"])
    
    assert len(ledger["entries"]) >= 2  # subscription_created + invoice_created
    
    # Check that entries have reference_id
    for entry in ledger["entries"]:
        assert entry["reference_id"] is not None
        assert entry["created_at"] is not None


# ===== Test 10: Idempotent payment recording =====
def test_idempotent_payment_recording(test_db, sample_subscription):
    """
    Test that recording the same payment twice (same provider_reference) returns existing payment.
    """
    invoice = InvoiceService.generate_invoice(test_db, sample_subscription["id"])

    # Record payment first time
    payment1 = PaymentService.record_payment(
        test_db,
        invoice["id"],
        Decimal("50.00"),
        "USD",
        "success",
        "IDEMPOTENT-001"
    )

    # Try to record same payment again
    payment2 = PaymentService.record_payment(
        test_db,
        invoice["id"],
        Decimal("50.00"),
        "USD",
        "success",
        "IDEMPOTENT-001"
    )

    # Should return same payment
    assert payment1["id"] == payment2["id"]
    assert "idempotent" in payment2.get("message", "").lower()


# ===== Test 11: Subscription cancellation creates ledger entry =====
def test_subscription_cancellation_creates_ledger_entry(test_db, sample_subscription, sample_customer):
    """
    Test that cancelling a subscription creates appropriate ledger entries.
    """
    subscription_id = sample_subscription["id"]
    
    # Cancel subscription
    SubscriptionService.cancel_subscription(test_db, subscription_id)

    # Get customer ledger
    ledger = LedgerService.get_customer_ledger(test_db, sample_customer["id"])

    # Should have subscription_created and subscription_cancelled entries
    entry_types = [entry["entry_type"] for entry in ledger["entries"]]
    assert "subscription_cancelled" in entry_types


# ===== Test 12: Cannot cancel inactive subscription =====
def test_cannot_cancel_inactive_subscription(test_db, sample_subscription):
    """
    Test that trying to cancel an already-cancelled subscription fails.
    """
    # Cancel subscription first time
    SubscriptionService.cancel_subscription(test_db, sample_subscription["id"])

    # Try to cancel again
    with pytest.raises(ValueError, match="Cannot cancel subscription"):
        SubscriptionService.cancel_subscription(test_db, sample_subscription["id"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
