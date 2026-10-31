# Brightloop — Subscription Management System

A modular monolith starter for products, plans, quotations, subscriptions, recurring invoices,
discounts, payments and revenue reporting.

## Stack
- Frontend: React + Vite
- Backend: Django + Django REST Framework
- Database: PostgreSQL
- Background jobs: Celery + Redis (planned)
- Local infrastructure: Docker Compose

## Structure

```text
brightloop/
├── frontend/                 # React application
│   └── src/
│       ├── app/               # App shell and routing
│       ├── components/        # Reusable UI
│       ├── features/          # Feature-oriented screens and logic
│       ├── hooks/
│       ├── layouts/
│       ├── lib/               # API client and utilities
│       ├── pages/
│       └── styles/
├── backend/
│   ├── config/                # Django settings and URL configuration
│   ├── apps/
│   │   ├── accounts/
│   │   ├── customers/
│   │   ├── catalog/
│   │   ├── plans/
│   │   ├── quotations/
│   │   ├── subscriptions/
│   │   ├── billing/
│   │   ├── discounts/
│   │   ├── payments/
│   │   ├── notifications/
│   │   └── analytics/
│   ├── common/                # Shared utilities and permissions
│   └── tests/
├── docs/
├── infra/
├── .env.example
├── .gitignore
└── docker-compose.yml
```

## How the system connects

```text
Accounts & Roles
      |
Products -> Variants -> Plans
                       |
                   Quotations
                       |
                  Subscriptions
                       |
                Scheduled Billing
                       |
                    Invoices
                       |
                    Payments
                       |
                 Finance Reports
```

## Backend module responsibilities

| App | Responsibility |
|---|---|
| accounts | Login, password reset, roles and staff access |
| customers | Customer/company profiles |
| catalog | Products, variants, selling price and cost |
| plans | Billing frequency, quantity and availability rules |
| quotations | Templates, quotations and conversion |
| subscriptions | Lifecycle, renewals, pauses and closures |
| billing | Invoice generation, invoice lines and taxes |
| discounts | Fixed/percentage rules, eligibility and usage limits |
| payments | Payment records, allocations and balances |
| notifications | Email and in-app notifications |
| analytics | MRR, ARR, collected revenue and receivables |

## Local setup

1. Clone the repository and enter the project folder.
2. Copy `.env.example` to `.env` and change the development credentials.
3. Start local infrastructure:

```bash
docker compose up -d
```

4. Start the backend:

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

5. Start the frontend in another terminal:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

## Suggested implementation order

1. Project setup and health checks.
2. Accounts, authentication and role-based permissions.
3. Customers, products, variants and plans.
4. Quotation templates and quotations.
5. Subscription lifecycle and state transitions.
6. Tax and discount calculation services.
7. Invoice generation and duplicate-billing protection.
8. Payment recording and invoice reconciliation.
9. Customer portal and notifications.
10. Analytics, pagination, indexes and performance tests.

## Important engineering rules

- Use decimal database fields for money, never floating point.
- Use timezone-aware datetimes and define the business timezone.
- Enforce customer ownership in backend permissions, not only in the UI.
- Use database transactions for quotation conversion, invoice creation and payment allocation.
- Prevent duplicate invoices with a unique subscription + billing-period constraint.
- Snapshot invoice line descriptions, prices, taxes and discounts at invoice time.
- Validate status transitions on the backend.
- Paginate list endpoints and index frequently filtered fields.
- Never commit `.env` or real credentials.

## Git workflow

```bash
git checkout -b feature/subscription-lifecycle
git add .
git commit -m "Add subscription lifecycle foundation"
git push -u origin feature/subscription-lifecycle
```

This is an architectural scaffold, not a complete production billing system. Payment gateway integration,
production email delivery, and full authentication flows still need to be implemented.
