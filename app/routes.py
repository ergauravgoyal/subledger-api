"""
API Routes for SubLedger.
Defines HTTP endpoints for all billing operations.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    CustomerCreate,
    CustomerLedgerResponse,
    CustomerResponse,
    ErrorResponse,
    InvoiceGenerate,
    InvoiceResponse,
    LedgerEntryResponse,
    PaymentAttemptResponse,
    PaymentRecord,
    PlanCreate,
    PlanResponse,
    SubscriptionCancel,
    SubscriptionCreate,
    SubscriptionResponse,
)
from app.services import (
    CustomerService,
    InvoiceService,
    LedgerService,
    PaymentService,
    PlanService,
    SubscriptionService,
)

router = APIRouter(prefix="/api/v1", tags=["SubLedger"])


# ===== Plan Routes =====
@router.post("/plans", response_model=PlanResponse, status_code=201)
def create_plan(plan: PlanCreate, db: Session = Depends(get_db)):
    """Create a new plan."""
    try:
        result = PlanService.create_plan(
            db, plan.name, plan.description, plan.billing_cycle, plan.price, plan.currency
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/plans/{plan_id}", response_model=PlanResponse)
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    """Fetch plan by ID."""
    try:
        result = PlanService.get_plan(db, plan_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/plans", response_model=list[PlanResponse])
def list_plans(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000),
               db: Session = Depends(get_db)):
    """List all plans with pagination."""
    result = PlanService.list_plans(db, skip, limit)
    return result


# ===== Customer Routes =====
@router.post("/customers", response_model=CustomerResponse, status_code=201)
def create_customer(customer: CustomerCreate, db: Session = Depends(get_db)):
    """Create a new customer."""
    try:
        result = CustomerService.create_customer(
            db, customer.name, customer.email, customer.company_name
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/customers/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    """Fetch customer by ID."""
    try:
        result = CustomerService.get_customer(db, customer_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/customers", response_model=list[CustomerResponse])
def list_customers(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000),
                   db: Session = Depends(get_db)):
    """List all customers with pagination."""
    result = CustomerService.list_customers(db, skip, limit)
    return result


# ===== Subscription Routes =====
@router.post("/subscriptions", response_model=SubscriptionResponse, status_code=201)
def create_subscription(subscription: SubscriptionCreate, db: Session = Depends(get_db)):
    """Create a new subscription."""
    try:
        result = SubscriptionService.create_subscription(
            db, subscription.customer_id, subscription.plan_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
def get_subscription(subscription_id: int, db: Session = Depends(get_db)):
    """Fetch subscription by ID."""
    try:
        result = SubscriptionService.get_subscription(db, subscription_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/subscriptions", response_model=list[SubscriptionResponse])
def list_subscriptions(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000),
                       db: Session = Depends(get_db)):
    """List all subscriptions with pagination."""
    result = SubscriptionService.list_subscriptions(db, skip, limit)
    return result


@router.patch("/subscriptions/{subscription_id}/cancel", response_model=SubscriptionResponse)
def cancel_subscription(subscription_id: int, cancel_req: SubscriptionCancel = None,
                        db: Session = Depends(get_db)):
    """Cancel a subscription."""
    try:
        result = SubscriptionService.cancel_subscription(db, subscription_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===== Invoice Routes =====
@router.post("/invoices/generate", response_model=InvoiceResponse, status_code=201)
def generate_invoice(invoice_req: InvoiceGenerate, db: Session = Depends(get_db)):
    """Generate an invoice for a subscription."""
    try:
        result = InvoiceService.generate_invoice(
            db, invoice_req.subscription_id, invoice_req.period_start, invoice_req.period_end
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    """Fetch invoice by ID."""
    try:
        result = InvoiceService.get_invoice(db, invoice_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ===== Payment Routes =====
@router.post("/payments/record", response_model=PaymentAttemptResponse, status_code=201)
def record_payment(payment: PaymentRecord, db: Session = Depends(get_db)):
    """Record a payment attempt."""
    try:
        result = PaymentService.record_payment(
            db, payment.invoice_id, payment.amount, payment.currency,
            payment.status, payment.provider_reference, payment.failure_reason
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===== Ledger Routes =====
@router.get("/customers/{customer_id}/ledger", response_model=CustomerLedgerResponse)
def get_customer_ledger(customer_id: int, skip: int = Query(0, ge=0),
                        limit: int = Query(100, ge=1, le=1000),
                        db: Session = Depends(get_db)):
    """Fetch customer ledger history."""
    try:
        result = LedgerService.get_customer_ledger(db, customer_id, skip, limit)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ===== Health Check =====
@router.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}
