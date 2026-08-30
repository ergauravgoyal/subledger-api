# SubLedger: Simplified Billing Backend

A clean, production-ready billing system backend for SaaS companies. Demonstrates proper separation of concerns with repositories, services, models, and routes. Includes comprehensive business rule validation, append-only ledger, and idempotent payment processing.

## 🎯 Features

- **Plan Management**: Create and manage billing plans with pricing and cycles
- **Customer Management**: Track customers with unique email validation
- **Subscription Lifecycle**: Create, manage, and cancel subscriptions
- **Invoice Generation**: Automatically generate invoices from subscriptions
- **Payment Processing**: Record payment attempts with success/failure tracking
- **Append-Only Ledger**: Immutable audit trail of all billing events
- **Business Rule Enforcement**: 8+ core business rules validated at service layer
- **Idempotent Payments**: Safe payment recording with provider references
- **Comprehensive Tests**: 12+ tests covering all critical workflows
- **Swagger Documentation**: Auto-generated API docs via FastAPI

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [API Endpoints](#api-endpoints)
- [Database Schema](#database-schema)
- [Business Rules](#business-rules)
- [Testing](#testing)
- [Docker Setup](#docker-setup)
- [Design Patterns](#design-patterns)
- [Assumptions & Limitations](#assumptions--limitations)

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- pip or poetry

### Local Setup

1. **Navigate to the project root**
```bash
cd /Subledger
```

2. **Create or use the project virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Initialize the database**
```bash
python -c "from app.db import init_db; init_db()"
```

This creates a `database.db` SQLite file.

5. **Run tests**
```bash
python -m pytest test_business_rules.py -q
```

You should see all tests passing.

6. **Start development server**
```bash
python main.py
```

This starts the FastAPI app with Uvicorn and serves it at `http://localhost:8000`.

7. **Access Swagger UI**
```
http://localhost:8000/docs
```

All endpoints are documented with request/response schemas.

### Quick Test with curl

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Create a plan
curl -X POST http://localhost:8000/api/v1/plans \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Premium Plan",
    "description": "Premium features",
    "billing_cycle": "monthly",
    "price": "99.99",
    "currency": "USD"
  }'

# Create a customer
curl -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "company_name": "Acme Corp"
  }'

# Create a subscription
curl -X POST http://localhost:8000/api/v1/subscriptions \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "plan_id": 1
  }'
```

---

## 📁 Project Structure

```
Subledger/
├── app/                       # Application package
│   ├── __init__.py
│   ├── config.py              # Environment settings
│   ├── db.py                  # Database engine/session setup
│   ├── models.py              # SQLAlchemy models
│   ├── repositories.py        # Data access layer
│   ├── schemas.py             # Pydantic schemas
│   ├── services.py            # Business logic
│   └── routes.py              # FastAPI routes
├── main.py                    # App entry point
├── test_business_rules.py     # Business rule tests
├── DESIGN.md                  # Low-level design notes
├── README.md                  # Project documentation
├── Dockerfile                 # Container build config
├── docker-compose.yml         # Container orchestration
├── requirements.txt           # Python dependencies
├── .env.example               # Example environment file
├── .gitignore                 # Git ignore rules
├── database.db                # SQLite database (auto-created)
└── .venv/                     # Local virtual environment
```

### Layer Breakdown

```
HTTP Requests
    ↓
┌─────────────────────────────────────────────┐
│ routes.py (Endpoint handlers)               │
│ - Receive requests, call services           │
│ - Validate inputs with Pydantic             │
│ - Return responses                          │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│ services.py (Business logic)                │
│ - Implement business rules                  │
│ - Orchestrate repositories                  │
│ - Manage workflows                          │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│ repositories.py (Data access)               │
│ - Read/write database operations            │
│ - Entity-specific queries                   │
│ - No business logic                         │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│ models.py (Database schema)                 │
│ - SQLAlchemy ORM models                     │
│ - Table definitions                         │
│ - Relationships                             │
└─────────────────────────────────────────────┘
    ↓
Database (SQLite or PostgreSQL)
```

---

## 📡 API Endpoints

### Health Check
```
GET /api/v1/health
Response: { "status": "healthy", "version": "1.0.0" }
```

### Plans API

```
POST /api/v1/plans
Create a plan.

Request:
{
  "name": "Premium Plan",
  "description": "For power users",
  "billing_cycle": "monthly",  # monthly, quarterly, yearly, custom
  "price": "99.99",
  "currency": "USD"
}

Response: { id, name, description, billing_cycle, price, currency, status, created_at, updated_at }
Error: 400 if price <= 0 or invalid billing_cycle
```

```
GET /api/v1/plans/{plan_id}
Fetch a plan by ID.

Response: { ...plan details }
Error: 404 if plan not found
```

```
GET /api/v1/plans?skip=0&limit=100
List all plans (paginated).

Response: [ {...plan1}, {...plan2}, ... ]
```

### Customers API

```
POST /api/v1/customers
Create a customer.

Request:
{
  "name": "John Doe",
  "email": "john@example.com",
  "company_name": "Acme Corp"  # optional
}

Response: { id, name, email, company_name, status, created_at, updated_at }
Error: 400 if email already exists
```

```
GET /api/v1/customers/{customer_id}
Fetch customer by ID.

Response: { ...customer details }
Error: 404 if customer not found
```

```
GET /api/v1/customers?skip=0&limit=100
List all customers (paginated).

Response: [ {...customer1}, {...customer2}, ... ]
```

### Subscriptions API

```
POST /api/v1/subscriptions
Create a subscription.

Request:
{
  "customer_id": 1,
  "plan_id": 1
}

Response: { id, customer_id, plan_id, status, start_date, current_period_start, current_period_end, created_at, updated_at }
Error: 400 if:
  - customer not found
  - plan not found
  - plan is inactive
  - customer already has active subscription to this plan
```

```
GET /api/v1/subscriptions/{subscription_id}
Fetch subscription by ID.

Response: { ...subscription details }
Error: 404 if subscription not found
```

```
GET /api/v1/subscriptions?skip=0&limit=100
List all subscriptions (paginated).

Response: [ {...subscription1}, {...subscription2}, ... ]
```

```
PATCH /api/v1/subscriptions/{subscription_id}/cancel
Cancel a subscription.

Request: { "reason": "optional cancellation reason" }

Response: { id, customer_id, plan_id, status, cancelled_at, updated_at }
Error: 400 if subscription is not active
```

### Invoices API

```
POST /api/v1/invoices/generate
Generate an invoice for a subscription.

Request:
{
  "subscription_id": 1,
  "period_start": "2026-08-30T00:00:00",  # optional
  "period_end": "2026-09-30T00:00:00"     # optional
}

Response: { id, subscription_id, customer_id, amount_due, amount_paid, currency, status, period_start, period_end, due_date, created_at, updated_at }
Error: 400 if:
  - subscription not found
  - subscription is not active
```

```
GET /api/v1/invoices/{invoice_id}
Fetch invoice by ID.

Response: { ...invoice details }
Error: 404 if invoice not found
```

### Payments API

```
POST /api/v1/payments/record
Record a payment attempt.

Request:
{
  "invoice_id": 1,
  "amount": "50.00",
  "currency": "USD",
  "status": "success",  # or "failed"
  "provider_reference": "TXN-12345",
  "failure_reason": "Card declined"  # only for failed payments
}

Response: { id, invoice_id, amount, currency, status, provider_reference, failure_reason, created_at, invoice_status }
Error: 400 if:
  - invoice not found
  - amount <= 0
  - amount > unpaid amount
```

### Ledger API

```
GET /api/v1/customers/{customer_id}/ledger?skip=0&limit=100
Fetch customer's ledger history (append-only).

Response: {
  "customer_id": 1,
  "entries": [
    {
      "id": 1,
      "customer_id": 1,
      "invoice_id": null,
      "entry_type": "subscription_created",
      "amount": null,
      "currency": null,
      "reference_id": "SUB-1",
      "description": "Subscription 1 created",
      "created_at": "2026-08-30T12:00:00"
    },
    {
      "id": 2,
      "customer_id": 1,
      "invoice_id": 1,
      "entry_type": "invoice_created",
      "amount": "99.99",
      "currency": "USD",
      "reference_id": "INV-1",
      "description": "Invoice 1 created for 99.99 USD",
      "created_at": "2026-08-30T12:00:01"
    },
    ...
  ]
}
Error: 404 if customer not found
```

---

## 🗄️ Database Schema

### Core Tables

**plans**
- id (PK)
- name, description
- billing_cycle (monthly/quarterly/yearly/custom)
- price, currency
- status (active/inactive)
- created_at, updated_at

**customers**
- id (PK)
- name, email (UNIQUE), company_name
- status (active/inactive/suspended)
- created_at, updated_at

**subscriptions**
- id (PK)
- customer_id (FK), plan_id (FK)
- status (active/cancelled/expired)
- start_date, current_period_start, current_period_end, cancelled_at
- created_at, updated_at

**invoices**
- id (PK)
- subscription_id (FK), customer_id (FK)
- amount_due, amount_paid, currency
- status (draft/issued/partially_paid/paid/overdue/void)
- period_start, period_end, due_date
- created_at, updated_at

**payment_attempts**
- id (PK)
- invoice_id (FK)
- amount, currency
- status (success/failed)
- provider_reference (UNIQUE)
- failure_reason
- created_at

**ledger_entries** (append-only)
- id (PK)
- customer_id (FK), invoice_id (FK, nullable)
- entry_type (invoice_created/payment_success/payment_failed/...)
- amount, currency
- reference_id, description
- created_at (indexed)

---

## ✅ Business Rules

All enforced at service layer:

1. **Plan price must be greater than 0**
   - Validated in `PlanService.create_plan()`
   - Also validated in Pydantic schema

2. **Customer email must be unique**
   - Validated in `CustomerService.create_customer()`
   - Database constraint: UNIQUE on customers.email

3. **Cannot subscribe to inactive plan**
   - Validated in `SubscriptionService.create_subscription()`
   - Checks plan.status == "active"

4. **No duplicate active subscriptions to same plan**
   - Validated in `SubscriptionService.create_subscription()`
   - Queries for existing active subscription with (customer_id, plan_id)

5. **Invoice amount_due comes from plan price**
   - Enforced in `InvoiceService.generate_invoice()`
   - Snapshots plan.price at invoice time

6. **Payment cannot exceed unpaid amount**
   - Validated in `PaymentService.record_payment()`
   - Calculates: unpaid = amount_due - amount_paid
   - Rejects if payment > unpaid

7. **Successful payment updates invoice status**
   - Enforced in `PaymentService.record_payment()`
   - Status transitions: ISSUED → PARTIALLY_PAID → PAID

8. **Failed payment does not increase amount_paid**
   - Enforced in `PaymentService.record_payment()`
   - Only updates amount_paid when status == "success"

9. **Ledger entries are append-only**
   - Enforced in `LedgerRepository.create()`
   - No UPDATE or DELETE operations on ledger_entries table

10. **Ledger entries traceable via reference_id**
    - Enforced in `LedgerService`
    - Each entry has: reference_id = provider_reference or "INV-{id}" or "SUB-{id}"

---

## 🧪 Testing

### Run All Tests
```bash
pytest test_business_rules.py -v
```

### Run Specific Test
```bash
pytest test_business_rules.py::test_plan_price_must_be_positive -v
```

### Test Coverage
```bash
pytest test_business_rules.py --cov=services --cov=repositories --cov-report=html
```

### Test Categories

**Validation Tests**
- `test_plan_price_must_be_positive`
- `test_customer_email_must_be_unique`
- `test_cannot_subscribe_to_inactive_plan`
- `test_no_duplicate_active_subscriptions`
- `test_payment_cannot_exceed_unpaid_amount`

**Workflow Tests**
- `test_invoice_amount_due_from_plan_price`
- `test_successful_payment_updates_invoice_status`
- `test_failed_payment_does_not_increase_amount_paid`

**Audit Tests**
- `test_ledger_entries_are_append_only`
- `test_subscription_cancellation_creates_ledger_entry`

**Idempotency Tests**
- `test_idempotent_payment_recording`

**Edge Cases**
- `test_cannot_cancel_inactive_subscription`

---

## 🐳 Docker Setup

### Build Image
```bash
docker build -t subledger:latest .
```

### Run Container
```bash
docker run -p 8000:8000 subledger:latest
```

### Docker Compose
```bash
docker-compose up
```

Compose file includes:
- SubLedger API service (port 8000)
- PostgreSQL database (port 5432)
- Volume for data persistence

---

## 🏗️ Design Patterns

### 1. Repository Pattern
Isolates data access logic from business logic. Makes testing easier.

```python
# Service uses repository abstraction
subscription = SubscriptionRepository.get_by_id(db, subscription_id)
```

### 2. Service Layer Pattern
Centralizes business logic. Routes remain thin.

```python
# Route delegates to service
result = SubscriptionService.create_subscription(db, customer_id, plan_id)
```

### 3. Dependency Injection
Database session injected via FastAPI Depends().

```python
@router.post("/subscriptions")
def create_subscription(subscription: SubscriptionCreate, db: Session = Depends(get_db)):
    ...
```

### 4. Append-Only Ledger
Immutable audit trail for compliance and debugging.

```python
LedgerEntry(entry_type=LedgerEntryType.PAYMENT_SUCCESS, reference_id=provider_ref)
```

### 5. Idempotent Payment Processing
Safe retry with provider reference as idempotency key.

```python
existing = PaymentAttemptRepository.get_by_provider_reference(db, provider_ref)
if existing:
    return existing  # Safe retry
```

---

## 💡 Assumptions & Limitations

### Assumptions
✅ All dates/times in UTC
✅ SQLite for development (PostgreSQL for production)
✅ Synchronous operations (no async workers)
✅ Provider references globally unique
✅ Single currency per invoice
✅ Predefined billing periods per plan
✅ No complex proration logic

### Limitations
❌ No real payment gateway integration
❌ No frontend UI
❌ No authentication/authorization
❌ No complex taxation
❌ No usage-based billing
❌ No automated invoice generation
❌ No webhook notifications
❌ Single-process, not horizontally scalable

### Future Enhancements
- [ ] Scheduled invoice generation (Celery)
- [ ] Webhook notifications
- [ ] Advanced reporting & analytics
- [ ] Proration support
- [ ] Multi-currency support
- [ ] Refund handling
- [ ] Discount/coupon system
- [ ] Usage-based billing
- [ ] Dunning (retry failed payments)
- [ ] Performance optimization & caching

---

## 📚 Additional Documentation

See [DESIGN.md](DESIGN.md) for:
- Complete Entity Relationship Diagram (ERD)
- Service responsibility table
- Repository responsibility table
- Business rule ownership mapping
- Detailed invoice generation flow
- Detailed payment recording flow
- Design pattern explanations
- Deployment checklist

---

## 🔧 Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from db import init_db; init_db()"

# Run tests
pytest test_business_rules.py -v

# Run with auto-reload
uvicorn main:app --reload

# Run tests with coverage
pytest test_business_rules.py --cov=services

# Format code
black . && isort .

# Lint code
flake8 .

# Type checking
mypy .
```

---

## 📞 Support

### Common Issues

**Q: ModuleNotFoundError: No module named 'sqlalchemy'**
A: Run `pip install -r requirements.txt`

**Q: database.db already exists, can I reset it?**
A: Yes, delete it and run `python -c "from db import init_db; init_db()"`

**Q: How do I connect to PostgreSQL instead of SQLite?**
A: Update `.env` with:
```
DATABASE_URL=postgresql://user:password@localhost:5432/subledger
```

**Q: Tests are failing, what should I do?**
A: Run `pytest test_business_rules.py -v` to see detailed output

## Collection can be checked from 

https://garv-36-s-team.postman.co/workspace/My-Workspace~dfae84be-1c1d-442f-83ab-c3f90a31d96d/collection/4050601-10e440fd-2bf5-477e-931b-2272279c3a9e?action=share&source=copy-link&creator=4050601


## Complete Workflow Example

Run this sequence to test the full billing workflow:

```bash
# 1. Create a plan
curl -X POST http://localhost:8000/api/v1/plans \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Premium Plan",
    "description": "Premium features",
    "billing_cycle": "monthly",
    "price": "99.99",
    "currency": "USD"
  }'

# 2. Create a customer
curl -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "company_name": "Acme Corp"
  }'

# 3. Create a subscription (assumes plan_id=1, customer_id=1)
curl -X POST http://localhost:8000/api/v1/subscriptions \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "plan_id": 1
  }'

# 4. Generate an invoice (assumes subscription_id=1)
curl -X POST http://localhost:8000/api/v1/invoices/generate \
  -H "Content-Type: application/json" \
  -d '{
    "subscription_id": 1
  }'

# 5. Record a successful payment (assumes invoice_id=1)
curl -X POST http://localhost:8000/api/v1/payments/record \
  -H "Content-Type: application/json" \
  -d '{
    "invoice_id": 1,
    "amount": "99.99",
    "currency": "USD",
    "status": "success",
    "provider_reference": "TXN-001"
  }'

# 6. View customer ledger (assumes customer_id=1)
curl http://localhost:8000/api/v1/customers/1/ledger

# 7. Check health
curl http://localhost:8000/api/v1/health
```

---

## 📄 License

This project is provided as an example for billing system design.

---