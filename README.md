# Concord

**One platform. Every operation in sync.**

Concord runs a subscription business from end to end: products and plans, quotations, subscriptions, recurring invoices, discounts, payments and revenue reporting. It is built for the Brightloop Software problem statement in the Odoo x Make-A-Ton 9.0 hackathon.

> **Status:** in active development. Accounts and login work; the rest is being built. This README only describes what exists.

## Stack

| Layer | Technology |
|---|---|
| Frontend | React, Vite, Tailwind CSS, TanStack Query |
| Backend | Python 3.12, Django 5.2, Django REST Framework |
| Database | PostgreSQL 16, running locally |

Everything runs locally with no cloud services.

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
- **No Postgres (frontend work only):** delete the `DATABASE_URL` line and Django uses SQLite. Don't test billing on SQLite, because it ignores row locks.

**3. Start the backend.**

```bash
cd backend
py -3.12 -m venv .venv            # macOS/Linux: python3.12 -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

**4. Start the frontend** in a second terminal.

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. API docs are at <http://localhost:5173/api/docs> while `DJANGO_DEBUG=True`.

Emails print in the backend terminal unless SMTP is configured in `.env`, so that's where password reset links appear by default.

## Tests

```bash
cd backend
pytest
```

## Working in this repo

We work on `main` only. Commit small changes often, from your own GitHub account:

```bash
git pull --rebase
git add <your files>
git commit -m "Describe the change"
git push
```

## Architecture

A modular monolith: one Django project, one database, and apps that depend in one direction only.

```text
common <- accounts <- catalog <- subscriptions <- billing <- reports
```

Business rules live in each app's `services.py`. Views handle HTTP and serializers check input shape. Statuses can only change through named actions, never by editing a field.
