# SubLedger LLD (Low-Level Design)

## 1. System Overview

SubLedger is a simplified billing backend for SaaS companies that manages plans, customers, subscriptions, invoices, payments, and ledger events. The system demonstrates clean architecture with clear separation between routes, services, repositories, models, and database logic.

### Key Principles
- **SOLID Principles**: Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
- **Repository Pattern**: All database access isolated in repository layer
- **Service Layer**: All business logic centralized in service classes
- **Append-only Ledger**: Immutable audit trail for all billing events
- **Idempotent Payments**: Safe payment recording with provider references

---

## 2. Entity Relationship Diagram (ERD)

```
┌─────────────────┐
│      Plan       │
├─────────────────┤
│ id (PK)         │
│ name            │
│ description     │
│ billing_cycle   │
│ price           │
│ currency        │
│ status          │
│ created_at      │
│ updated_at      │
└────────┬────────┘
         │
         │ has many
         │
         └────┬─────────────────────────┐
              │                         │
         ┌────▼──────────────┐   ┌─────▼────────────────┐
         │  Subscription     │   │ (no direct to Plan)  │
         ├───────────────────┤   └──────────────────────┘
         │ id (PK)           │
         │ customer_id (FK)  │
         │ plan_id (FK)      │
         │ status            │
         │ start_date        │
         │ current_period_   │
         │   start/end       │
         │ cancelled_at      │
         │ created_at        │
         │ updated_at        │
         └────┬──────────────┘
              │
              │ has many
              │
         ┌────▼──────────────┐
         │   Invoice         │
         ├───────────────────┤
         │ id (PK)           │
         │ subscription_id(FK)
         │ customer_id (FK)  │
         │ amount_due        │
         │ amount_paid       │
         │ currency          │
         │ status            │
         │ period_start      │
         │ period_end        │
         │ due_date          │
         │ created_at        │
         │ updated_at        │
         └────┬──────────────┘
              │
              │ has many
              │
    ┌─────────┴──────────────┐
    │                        │
┌───▼──────────────┐  ┌──────▼─────────────┐
│ PaymentAttempt   │  │ LedgerEntry       │
├──────────────────┤  ├───────────────────┤
│ id (PK)          │  │ id (PK)           │
│ invoice_id (FK)  │  │ customer_id (FK)  │
│ amount           │  │ invoice_id (FK)   │
│ currency         │  │ entry_type        │
│ status           │  │ amount            │
│ provider_ref     │  │ currency          │
│ failure_reason   │  │ reference_id      │
│ created_at       │  │ description       │
└──────────────────┘  │ created_at        │
                      └───────────────────┘

┌──────────────┐
│  Customer    │
├──────────────┤
│ id (PK)      │
│ name         │
│ email(UNIQUE)│
│ company_name │
│ status       │
│ created_at   │
│ updated_at   │
└──────┬───────┘
       │ has many
       ├──────────┬──────────┬─────────────┐
       │          │          │             │
    (Sub) (Invoice)(LedgerEntry)

Relationships:
- Customer ──┬─→ Subscription
             ├─→ Invoice
             └─→ LedgerEntry

- Plan ──→ Subscription

- Subscription ──┬─→ Invoice
                 └─→ LedgerEntry

- Invoice ──┬─→ PaymentAttempt
            └─→ LedgerEntry

- LedgerEntry: append-only, traceable via reference_id
```

---

## 3. Service Responsibility Table

| Service | Owns | Should NOT do |
|---------|------|---------------|
| **PlanService** | Validate price > 0, validate billing cycle, activate/deactivate plans | Create subscriptions, manage payments, generate invoices |
| **CustomerService** | Validate email uniqueness, create/fetch customer profiles | Manage subscriptions, process payments |
| **SubscriptionService** | Create/cancel subscriptions, validate plan is active, prevent duplicate active subscriptions | Generate invoices, record payments, manage ledger |
| **InvoiceService** | Generate invoices, calculate amount_due from plan price, update invoice status after payment | Record payments, manage customer accounts, track ledger |
| **PaymentService** | Record payment attempts, validate amount ≤ unpaid, update invoice status on success, create ledger entries | Manage subscriptions, generate invoices |
| **LedgerService** | Create append-only ledger entries, track all events via reference_id, fetch customer history | Manage entities directly, create subscriptions/invoices |

---

## 4. Repository Responsibility Table

| Repository | Manages | Operations |
|-----------|---------|-----------|
| **PlanRepository** | Plan entity CRUD | `create()`, `get_by_id()`, `get_all()`, `update_status()` |
| **CustomerRepository** | Customer entity CRUD | `create()`, `get_by_id()`, `get_by_email()`, `get_all()`, `email_exists()`, `update_status()` |
| **SubscriptionRepository** | Subscription entity CRUD | `create()`, `get_by_id()`, `get_by_customer_and_plan()`, `get_all()`, `get_by_customer()`, `update_status()` |
| **InvoiceRepository** | Invoice entity CRUD | `create()`, `get_by_id()`, `get_all()`, `get_by_customer()`, `get_by_subscription()`, `update_payment_status()` |
| **PaymentAttemptRepository** | PaymentAttempt entity CRUD | `create()`, `get_by_id()`, `get_by_provider_reference()`, `get_by_invoice()` |
| **LedgerRepository** | LedgerEntry entity (append-only) | `create()`, `get_by_id()`, `get_customer_ledger()`, `get_by_invoice()` |

All repositories:
- Read from database
- Write to database
- Handle data persistence only
- No business logic

---

## 5. Business Rule Ownership

| Rule | Owner | Implementation Location |
|------|-------|--------------------------|
| Plan price > 0 | PlanService + Plan schema | `PlanService.create_plan()` + Pydantic validator |
| Customer email unique | CustomerService + CustomerRepository | `CustomerService.create_customer()` + DB unique constraint |
| Cannot subscribe to inactive plan | SubscriptionService | `SubscriptionService.create_subscription()` |
| No duplicate active subscriptions to same plan | SubscriptionService + SubscriptionRepository | Query with customer_id, plan_id, status filters |
| Invoice amount_due from plan price | InvoiceService | `InvoiceService.generate_invoice()` |
| Payment cannot exceed unpaid amount | PaymentService | `PaymentService.record_payment()` |
| Successful payment updates invoice status | PaymentService + InvoiceRepository | Amount validation & status transitions |
| Failed payment does not increase amount_paid | PaymentService | Only update amount_paid on "success" status |
| Ledger entries append-only | LedgerRepository | No UPDATE operations, only INSERT |
| Ledger entries traceable via reference_id | LedgerService | Generate reference_id for each entry |

---

## 6. Design Patterns Used

### 1. **Repository Pattern**
- Isolates data access logic from business logic
- Makes testing easier with in-memory repositories
- Allows easy switching between database implementations

```python
# Service depends on repository abstraction
class InvoiceService:
    @staticmethod
    def generate_invoice(db: Session, subscription_id: int):
        subscription = SubscriptionRepository.get_by_id(db, subscription_id)
        invoice = InvoiceRepository.create(db, ...)
```

### 2. **Service Layer Pattern**
- Centralizes all business logic
- Routes don't contain logic—just validation and error handling
- Services orchestrate repositories

```python
# Route delegates to service
@router.post("/subscriptions", response_model=SubscriptionResponse)
def create_subscription(subscription: SubscriptionCreate, db: Session = Depends(get_db)):
    result = SubscriptionService.create_subscription(
        db, subscription.customer_id, subscription.plan_id
    )
    return result
```

### 3. **Dependency Injection**
- Database session injected via FastAPI `Depends()`
- Services receive repositories (repositories receive session)
- Easier testing with test databases

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/customers")
def create_customer(customer: CustomerCreate, db: Session = Depends(get_db)):
    ...
```

### 4. **Append-Only Ledger**
- Every billing event creates immutable ledger entry
- No UPDATE operations on ledger
- Audit trail for compliance and debugging

```python
LedgerEntry(
    customer_id=customer_id,
    entry_type=LedgerEntryType.INVOICE_CREATED,
    reference_id=f"INV-{invoice_id}",
    description="Invoice created"
)
```

### 5. **Idempotent Payment Processing**
- Provider reference used as idempotency key
- Same payment recorded twice returns existing record
- Safe for retry scenarios

```python
existing_payment = PaymentAttemptRepository.get_by_provider_reference(db, provider_reference)
if existing_payment:
    return existing_payment  # Idempotent response
```

---

## 7. Invoice Generation Flow

```
Request: POST /invoices/generate
├── Input: { subscription_id, period_start (optional), period_end (optional) }
│
└── InvoiceService.generate_invoice()
    │
    ├─ Step 1: Validate subscription exists and is active
    │   └─ SubscriptionRepository.get_by_id()
    │
    ├─ Step 2: Fetch plan and verify active status
    │   └─ PlanRepository.get_by_id()
    │
    ├─ Step 3: Calculate billing period
    │   └─ Use provided dates or subscription current_period
    │
    ├─ Step 4: Calculate amount_due from plan.price
    │   ├─ Business Rule: Snapshot plan price at invoice time
    │   └─ Set due_date = now + 30 days
    │
    ├─ Step 5: Create invoice with status=ISSUED
    │   └─ InvoiceRepository.create()
    │       └─ INSERT into invoices table
    │
    ├─ Step 6: Create ledger entry for invoice_created
    │   └─ LedgerService.log_invoice_created()
    │       └─ INSERT into ledger_entries table
    │
    └─ Response: InvoiceResponse {
        id, subscription_id, customer_id,
        amount_due, amount_paid=0,
        status=ISSUED, period_start, period_end,
        due_date, created_at, updated_at
    }
```

---

## 8. Payment Recording Flow

```
Request: POST /payments/record
├── Input: {
│     invoice_id, amount, currency,
│     status (success/failed),
│     provider_reference, failure_reason (optional)
│   }
│
└── PaymentService.record_payment()
    │
    ├─ Step 1: Validate invoice exists
    │   └─ InvoiceRepository.get_by_id()
    │
    ├─ Step 2: Check idempotency (same provider_reference)
    │   └─ PaymentAttemptRepository.get_by_provider_reference()
    │       └─ If exists, return existing (idempotent)
    │
    ├─ Step 3: Validate payment amount
    │   ├─ Calculate unpaid_amount = amount_due - amount_paid
    │   ├─ Validate: amount > 0
    │   └─ Business Rule: amount ≤ unpaid_amount
    │
    ├─ Step 4: Create payment attempt record
    │   └─ PaymentAttemptRepository.create()
    │       └─ INSERT into payment_attempts table
    │
    ├─ Step 5: If status == SUCCESS
    │   │
    │   ├─ new_amount_paid = invoice.amount_paid + amount
    │   │
    │   ├─ Determine new status:
    │   │   ├─ If new_amount_paid >= amount_due: status = PAID
    │   │   └─ Else: status = PARTIALLY_PAID
    │   │
    │   ├─ Update invoice
    │   │   └─ InvoiceRepository.update_payment_status()
    │   │       └─ UPDATE invoices SET amount_paid, status
    │   │
    │   └─ Create success ledger entry
    │       └─ LedgerService.log_payment_success()
    │           └─ INSERT into ledger_entries
    │
    ├─ Step 6: Else (status == FAILED)
    │   │
    │   ├─ Business Rule: Do NOT increase amount_paid
    │   │
    │   └─ Create failure ledger entry
    │       └─ LedgerService.log_payment_failed()
    │           └─ INSERT into ledger_entries
    │
    └─ Response: PaymentAttemptResponse {
        id, invoice_id, amount, currency, status,
        provider_reference, failure_reason, created_at,
        invoice_status (if success)
    }
```

---

## 9. Database Schema Notes

### Enums Used
- **PlanStatus**: active, inactive
- **BillingCycle**: monthly, quarterly, yearly, custom
- **CustomerStatus**: active, inactive, suspended
- **SubscriptionStatus**: active, cancelled, expired
- **InvoiceStatus**: draft, issued, partially_paid, paid, overdue, void
- **PaymentAttemptStatus**: success, failed
- **LedgerEntryType**: invoice_created, payment_success, payment_failed, invoice_void, subscription_created, subscription_cancelled

### Indexes
- `Customer.email` - unique, for uniqueness check
- `Subscription.customer_id` - for customer subscriptions query
- `Invoice.customer_id` - for customer invoices query
- `Invoice.subscription_id` - for subscription invoices query
- `LedgerEntry.customer_id` - for customer ledger query
- `LedgerEntry.reference_id` - for tracing payments
- `LedgerEntry.created_at` - for time-ordered queries

---

## 10. Configuration & Environment

```
DATABASE_URL=sqlite:///./database.db  (or PostgreSQL in production)
ENVIRONMENT=development
LOG_LEVEL=INFO
API_TITLE=SubLedger API
API_VERSION=1.0.0
```

---

## 11. API Structure

### Health Check
- `GET /api/v1/health` → `{ status, version }`

### Plans
- `POST /api/v1/plans` → Create plan
- `GET /api/v1/plans/{plan_id}` → Fetch plan
- `GET /api/v1/plans` → List plans (paginated)

### Customers
- `POST /api/v1/customers` → Create customer
- `GET /api/v1/customers/{customer_id}` → Fetch customer
- `GET /api/v1/customers` → List customers (paginated)

### Subscriptions
- `POST /api/v1/subscriptions` → Create subscription
- `GET /api/v1/subscriptions/{subscription_id}` → Fetch subscription
- `GET /api/v1/subscriptions` → List subscriptions (paginated)
- `PATCH /api/v1/subscriptions/{subscription_id}/cancel` → Cancel subscription

### Invoices
- `POST /api/v1/invoices/generate` → Generate invoice
- `GET /api/v1/invoices/{invoice_id}` → Fetch invoice

### Payments
- `POST /api/v1/payments/record` → Record payment attempt

### Ledger
- `GET /api/v1/customers/{customer_id}/ledger` → Fetch customer ledger history (paginated)

---

## 12. In-Scope vs Out-of-Scope

### In Scope
✅ Plan management (CRUD + status)
✅ Customer management (create, list)
✅ Subscription lifecycle (create, cancel)
✅ Invoice generation with period tracking
✅ Payment attempt recording and status tracking
✅ Append-only ledger with audit trail
✅ Business rule validation
✅ Comprehensive tests
✅ Local Docker setup

### Out of Scope
❌ Real payment gateway integration (Stripe, Razorpay)
❌ Frontend UI
❌ Authentication/Authorization
❌ Complex taxation
❌ Proration (partial billing period)
❌ Multi-currency conversion
❌ Usage-based billing
❌ Dunning management
❌ Invoice PDF generation

---

## 13. Key Assumptions & Limitations

### Assumptions
1. All dates/times in UTC
2. SQLite for local development (PostgreSQL recommended for production)
3. Synchronous operations (no async workers)
4. Provider references are globally unique
5. Single currency per invoice (no multi-currency invoices)
6. Billing periods are predefined by plan (no custom periods)
7. No complex proration logic

### Limitations
1. No real-time payment gateway callback handling
2. No scheduled invoice generation (manual via API)
3. No retry mechanisms for failed payments
4. No advanced reporting/analytics
5. No webhook notifications
6. No rate limiting or authentication
7. Not horizontally scalable (single process)

---

## 14. Testing Strategy

### Unit Tests (12+ tests in `test_business_rules.py`)
- Plan price validation
- Email uniqueness validation
- Inactive plan subscription prevention
- Duplicate active subscription prevention
- Payment amount validation
- Invoice amount_due calculation
- Invoice status transitions
- Failed payment handling
- Ledger append-only behavior
- Idempotent payment processing
- Subscription cancellation
- Ledger entry creation

### Test Database
- In-memory SQLite for fast test execution
- Full isolation between tests
- No side effects across tests

### Coverage
- All business rules tested
- Happy path and error paths
- Edge cases (zero amounts, duplicate attempts, etc.)

---

## 15. Deployment Checklist

- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Set environment variables
- [ ] Initialize database: `python -c "from db import init_db; init_db()"`
- [ ] Run tests: `pytest test_business_rules.py -v`
- [ ] Start server: `uvicorn main:app --host 0.0.0.0 --port 8000`
- [ ] Test health: `curl http://localhost:8000/api/v1/health`
- [ ] Access Swagger: `http://localhost:8000/docs`
- [ ] (Optional) Run with Docker: `docker-compose up`

---

## 16. Future Enhancements

1. **Scheduled Jobs**: Invoice generation on schedule (via Celery)
2. **Webhooks**: Notify external systems of billing events
3. **Advanced Reporting**: Revenue analytics, customer metrics
4. **Proration**: Handle mid-cycle subscription changes
5. **Multi-Currency**: Support multiple currencies and conversion
6. **Refunds**: Reverse payments and adjust invoices
7. **Discounts**: Apply coupons and promotions
8. **Usage-Based**: Charge per unit of resource used
9. **Dunning**: Automated retry for failed payments
10. **Performance**: Query optimization and caching

