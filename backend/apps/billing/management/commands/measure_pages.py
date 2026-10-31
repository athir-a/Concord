"""Time every page's API calls against whatever data is in the database.

The statement says every page must respond in under two seconds with thousands of
subscriptions. This produces the numbers in the README, so they're measured, not claimed.
"""
import time
from math import ceil

from django.core.management.base import BaseCommand
from django.test import Client

from apps.accounts.models import User
from apps.billing.models import Invoice, Payment
from apps.subscriptions.models import Subscription

LIMIT_SECONDS = 2.0


class Command(BaseCommand):
    help = "Measure API response times for each page."

    def handle(self, *args, **options):
        admin = User.objects.filter(role="admin").first()
        if admin is None:
            self.stderr.write("No admin user. Run seed_demo first.")
            return
        client = Client(HTTP_HOST="localhost")
        client.force_login(admin)

        subscription = Subscription.objects.filter(status="active").order_by("-id").first()
        invoice = Invoice.objects.filter(status="confirmed").order_by("id").first()
        customer = subscription.customer_id
        pages = {
            "Overview": ["reports/summary", "reports/revenue-series"],
            "Reports": ["reports/summary?date_from=2026-01-01", "reports/revenue-series", "reports/overdue-ageing"],
            "Subscriptions list": ["subscriptions", "plans?page_size=100"],
            "Subscriptions, last page": [f"subscriptions?page={ceil(Subscription.objects.count() / 25)}"],
            "Subscriptions, search": ["subscriptions?search=menon"],
            "Subscription detail": [f"subscriptions/{subscription.id}", f"subscriptions/{subscription.id}/preview", f"invoices?subscription={subscription.id}"],
            "Invoices list": ["invoices"],
            "Invoices, overdue": ["invoices?overdue=true&ordering=due_date"],
            "Invoices, search": ["invoices?search=menon"],
            "Invoice detail": [f"invoices/{invoice.id}"],
            "Payments list": ["payments"],
            "Customers list": ["customers"],
            "Customers, search": ["customers?search=nair"],
            "Customer detail": [f"customers/{customer}", f"customers/{customer}/summary", f"subscriptions?customer={customer}", f"invoices?customer={customer}"],
            "Billing": ["billing/due", "billing/runs"],
        }

        self.stdout.write(
            f"{Subscription.objects.count():,} subscriptions, {Invoice.objects.count():,} invoices, "
            f"{Payment.objects.count():,} payments\n"
        )
        slowest = 0.0
        for name, paths in pages.items():
            total = 0.0
            for path in paths:
                started = time.perf_counter()
                response = client.get(f"/api/v1/{path}")
                total += time.perf_counter() - started
                if response.status_code != 200:
                    self.stderr.write(f"{path} returned {response.status_code}")
            slowest = max(slowest, total)
            flag = "" if total < LIMIT_SECONDS else "  OVER LIMIT"
            self.stdout.write(f"{total * 1000:7.0f} ms  {name}{flag}")
        self.stdout.write(f"\nSlowest page: {slowest * 1000:.0f} ms (all of its API calls, one after another)")
