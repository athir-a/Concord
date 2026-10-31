# Concord

**One platform. Every operation in sync.**

Concord runs a subscription business from end to end: products and plans, quotations, subscriptions, recurring invoices, discounts, payments and revenue reporting. It's built for the Brightloop Software problem statement in the Odoo x Make-A-Ton 9.0 hackathon.

Brightloop tracks subscriptions in a spreadsheet, types invoices by hand and matches payments by scrolling through bank statements. Renewals get missed, invoices go out wrong, and nobody can say how much recurring revenue the company has. Concord replaces all of that with one chain:

```text
plan -> subscription -> invoice -> payment -> report
```

## What it does

| Scene from the statement | In Concord |
|---|---|
| A new customer signs up | Email and password signup with the stated password rules, unique email, and a password reset link by email |
| Different people, different access | Admin controls everything, staff handle daily work, customers see only their own records in a portal. Only the admin adds staff |
| Launching a new plan | Products with variants (Brand: Odoo adds 560), plans billed daily, weekly, monthly or yearly, minimum quantity, availability dates, and per-plan close, pause and renew rules |
| Turning a quote into a subscription | Quotation templates with a validity period, numbered subscriptions moving Draft → Quotation → Confirmed → Active → Closed, with a full history |
| Billing day | One button or command bills everything due. Taxes apply automatically. Invoices move Draft → Confirmed → Paid and can be confirmed, cancelled, sent or printed |
| A customer asks for a better price | Admin-only discount rules: fixed or percentage, minimums, dates, usage limits, product or subscription scope. They appear on the next invoice and stop by themselves |
| The money comes in | Record method, amount, date and note against an invoice. Partial payments work, overpayments are refused |
| The finance lead | Active subscriptions, MRR, revenue, payments and overdue invoices with filters and a summary, calculated live |

## Nothing billed twice, nothing skipped

- **Not twice:** each subscription is locked while it's billed, and its next billing date moves in the same database transaction as the invoice. If that ever failed, a database constraint still refuses a second live invoice for the same subscription and period.
- **Not skipped:** billing loops through every period that has come due, so three missed months produce three invoices.
- **Tested for real:** tests run several billing runs at once on separate connections, with overlap forced. We checked those tests by removing each lock and confirming the test fails.

## Measured performance

The statement asks for every page in under two seconds with thousands of subscriptions. With **5,000 subscriptions, 40,923 invoices and 33,610 payments**, this is the total time for all of each page's API calls:

| Page | Time | | Page | Time |
|---|---:|---|---|---:|
| Reports | 128 ms | | Invoices, search | 68 ms |
| Overview | 116 ms | | Subscription detail | 38 ms |
| Customer detail | 26 ms | | Subscriptions list | 24 ms |
| Subscriptions, search | 19 ms | | Invoice detail | 15 ms |
| Payments list | 14 ms | | Invoices list | 11 ms |

A billing day creating 351 invoices took 5.6 seconds. Measured on a Windows laptop with Postgres running locally, in development mode. This times the server, not browser rendering. Reproduce it with `python manage.py measure_pages`.

## Stack

| Layer | Technology | Why |
|---|---|---|
| Frontend | React, Vite, Tailwind CSS, TanStack Query, Recharts | Fast to build, with loading and error states handled consistently |
| Backend | Python 3.12, Django 5.2, Django REST Framework | Auth, migrations and admin come included, so effort goes into billing |
| Database | PostgreSQL 16 | Row locks and partial unique constraints are what make billing safe |

Everything runs locally with no cloud services. There's no Celery or Redis: duplicate protection lives in the database, so the billing command can simply be run by cron.

More detail: [architecture](docs/architecture.md), [workflows](docs/workflows.md), [how the numbers are calculated](docs/metrics.md), [decisions and trade-offs](docs/decisions.md).

## Run it

You need **Python 3.12** (newer versions may not have the packages we use), **Node 22** and **PostgreSQL 16**.

**1. Configure.** From the project root:

```bash
cp .env.example .env
```

Set `DJANGO_SECRET_KEY` in `.env` to any long random string. Never commit `.env`.

**2. Start the database.** Pick one:

- **Docker:** `docker compose up -d`
- **Your own Postgres:** create a `concord` user and database matching `DATABASE_URL` in `.env`
- **No Postgres (trying the app or doing frontend work only):** delete the `DATABASE_URL` line and Django uses SQLite. Don't rely on it for billing, because it has no row locks. A few simultaneous-run tests are skipped there.

**3. Start the backend.**

```bash
cd backend
py -3.12 -m venv .venv            # macOS/Linux: python3.12 -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
python manage.py migrate
python manage.py seed_demo        # 5,000 subscriptions, about a minute. Add --subscriptions 300 for a quick start.
python manage.py runserver
```

**4. Start the frontend** in a second terminal.

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173> and log in. The password for all three is `Concord!demo1`. These are local demo accounts, and the seed command refuses to run outside debug mode.

| Role | Email |
|---|---|
| Admin | `admin@concord.test` |
| Staff | `staff@concord.test` |
| Customer | `customer@concord.test` |

API docs are at <http://localhost:5173/api/docs>.

**A billing day to try:** log in as admin, open **Billing**, set the date to tomorrow and run it. Then run it again: nothing new is created.

## Tests

```bash
cd backend
pytest
```

There are 204 backend tests, including role and ownership checks on the API, money calculations worked out by hand, billing edge cases, and simultaneous runs. `e2e/` holds browser walks of the whole demo path (see its README).

## What's real and what isn't

**Real:** every number comes from the database. Billing, tax, discounts, payments and access rules are enforced on the server.

**Simplified or simulated:**

- **Payments are recorded, not processed.** Staff enter money that has arrived, as the statement describes. There's no payment gateway.
- **Email needs SMTP.** By default, reset links and invoices print in the backend terminal. Add SMTP details to `.env` to deliver them.
- **Demo data is generated.** `seed_demo` inserts history directly so it finishes in about a minute, using the real pricing code. Everything you do afterwards goes through the real services.
- **The future date on the Billing page is a demo control.** It's allowed only in debug mode.

**Not built:** refunds and credit notes, correcting a recorded payment, proration (a final period cut short by expiry is charged in full), mid-period plan changes, multiple currencies, more than one discount on a subscription, PDF files (invoices print from the browser), reminder emails, a built-in scheduler (run `python manage.py run_billing` from cron), and a production deployment setup.

**Known limits:** billing runs while the admin waits, which suits hundreds or a few thousand invoices but would move to a background job at larger scale. MRR is before discounts, so it can be higher than what's actually billed.

## Working in this repo

We work on `main`. Commit small changes often, from your own GitHub account:

```bash
git pull --rebase
git add <your files>
git commit -m "Describe the change"
git push
```
