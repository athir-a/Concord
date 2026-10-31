# Architecture Notes

## Approach: modular monolith

Use one Django backend and one PostgreSQL database, separated into domain-focused Django apps.
This keeps the system straightforward to build and deploy while maintaining clear module boundaries.
Do not start with microservices for this project.

## Conceptual entities

User, Role/Membership, Customer, Product, ProductVariant, Plan, QuotationTemplate, Quotation,
QuotationLine, Subscription, SubscriptionLine, DiscountRule, DiscountRedemption, TaxRule,
Invoice, InvoiceLine, Payment, PaymentAllocation, Notification.

## Conceptual relationships

- A customer can have many subscriptions.
- A product can have many variants.
- A quotation belongs to a customer and can be converted into a subscription.
- A subscription has one or more subscription lines.
- A subscription can produce many invoices over time.
- An invoice has one or more invoice lines.
- An invoice can have multiple payment allocations.
- A payment can be allocated according to the payment rules you choose.

## Duplicate billing protection

Represent each billing period explicitly with subscription ID, period start and period end.
Add a database uniqueness constraint for the subscription and billing period. Generate invoices
inside a transaction so retries cannot create duplicate invoices.

## Suggested API boundaries

- /api/auth/
- /api/customers/
- /api/products/
- /api/plans/
- /api/quotation-templates/
- /api/quotations/
- /api/subscriptions/
- /api/invoices/
- /api/discount-rules/
- /api/payments/
- /api/analytics/

## State management

Do not let clients arbitrarily set status fields. Implement explicit backend transition operations.
An invoice should become paid based on its recorded payment allocations and outstanding balance,
not because a frontend request sends a paid status.
