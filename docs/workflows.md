# Core Workflows

## Signup and access
1. Customer signs up with a unique email.
2. Backend validates password rules and securely hashes the password.
3. Login authenticates the user.
4. Backend permissions restrict records by role and ownership.
5. Password reset uses a short-lived, single-use token sent to the registered email.
6. Only an admin-authorized operation can create staff accounts.

## Product and plan setup
1. Admin creates a product.
2. Admin adds variants and price adjustments.
3. Admin creates a plan and selects its billing interval.
4. Admin sets quantity rules, availability dates and lifecycle options.
5. Backend validates prices, dates and supported intervals.

## Quotation to subscription
1. Staff selects a customer and quotation template.
2. Backend creates a quotation and snapshots proposed lines and prices.
3. Customer accepts and authorized staff confirms it.
4. Backend converts it to a subscription transactionally.
5. Subscription receives its own identifier and lifecycle dates.

## Recurring billing
1. Scheduler finds active subscriptions due for billing.
2. Billing service determines the billing period.
3. Tax and discount services calculate applicable values.
4. Invoice and invoice lines are created in one transaction.
5. A unique billing-period constraint prevents duplicates.
6. Notification service sends the invoice.
7. Next billing date advances only after successful processing.

## Payment recording
1. Staff records method, amount, date and reference/note.
2. Payment is allocated to invoice(s), according to supported rules.
3. Outstanding balances are recalculated.
4. Invoice status is derived from the balance.
5. Audit information records who made the change.

## Reporting
Calculate dashboard metrics from persisted records, not hardcoded values.
Document definitions for MRR, ARR, collected revenue and outstanding receivables.
