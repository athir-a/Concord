"""Fill an empty database with a believable Brightloop.

Prices and totals go through the real pricing code, so the numbers are consistent.
Rows are bulk inserted rather than sent through services one at a time, because
thousands of subscriptions would take many minutes otherwise. Live billing, quotes
and payments in the demo all run through the real services.
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.models import Sum
from django.utils import timezone

from apps.accounts.models import Customer, User
from apps.billing.models import Invoice, InvoiceLine, Payment
from apps.billing.pricing import DiscountInput, LineInput, price_invoice
from apps.catalog.models import DiscountRule, Plan, Product, ProductVariant, QuotationTemplate, TaxRule, TemplateLine
from apps.common.models import DocumentSequence
from apps.common.money import round_money
from apps.subscriptions.models import Subscription, SubscriptionEvent, SubscriptionLine
from apps.subscriptions.periods import add_periods

# Local demo logins, printed in the README. The command refuses to run with DEBUG off.
DEMO_PASSWORD = "Concord!demo1"
FIRST = ["Asha", "Ravi", "Meera", "Arjun", "Divya", "Karthik", "Nisha", "Rahul", "Priya", "Vivek", "Anita", "Sanjay"]
LAST = ["Menon", "Nair", "Sharma", "Iyer", "Reddy", "Kapoor", "Das", "Pillai", "Gupta", "Thomas", "Rao", "Joshi"]
BUSINESS = ["Traders", "Stores", "Logistics", "Foods", "Textiles", "Pharma", "Motors", "Studios", "Exports", "Systems"]
PLACES = ["Kochi", "Chennai", "Pune", "Jaipur", "Mysuru", "Indore", "Surat", "Nagpur", "Vizag", "Thrissur"]
METHODS = ["bank_transfer", "upi", "upi", "card", "cash", "cheque"]


class Command(BaseCommand):
    help = "Create demo data. Only runs on an empty database, and only with DEBUG on."

    def add_arguments(self, parser):
        parser.add_argument("--subscriptions", type=int, default=5000)
        parser.add_argument("--customers", type=int, default=0, help="Defaults to a third of the subscriptions.")

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo creates known passwords, so it only runs with DJANGO_DEBUG=True.")
        if Subscription.objects.exists() or Product.objects.exists():
            raise CommandError("The database already has data. Seed only runs on an empty one.")

        self.rng = random.Random(9)
        self.today = timezone.localdate()
        count = options["subscriptions"]
        with transaction.atomic():
            self._users()
            self._catalog()
            self._customers(options["customers"] or max(20, count // 3))
            self._subscriptions(count)
        self._refresh_statistics()
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {Customer.objects.count()} customers, {Subscription.objects.count()} subscriptions, "
            f"{Invoice.objects.count()} invoices and {Payment.objects.count()} payments."
        ))
        self.stdout.write(f"Log in with admin@concord.test, staff@concord.test or customer@concord.test / {DEMO_PASSWORD}")

    def _refresh_statistics(self):
        """After a huge bulk insert the database doesn't yet know how big its tables are.

        Until its background job catches up it can pick a terrible query plan: we measured
        the payments list at 15 seconds instead of milliseconds. This tells it straight away.
        """
        with connection.cursor() as cursor:
            if connection.vendor == "postgresql":
                cursor.execute("ANALYZE")

    def _users(self):
        if not User.objects.filter(email="admin@concord.test").exists():
            User.objects.create_superuser("admin@concord.test", DEMO_PASSWORD, name="Anjali Varma")
        if not User.objects.filter(email="staff@concord.test").exists():
            User.objects.create_user("staff@concord.test", DEMO_PASSWORD, name="Sam Kurian", role="staff")
        portal = User.objects.filter(email="customer@concord.test").first()
        if portal is None:
            portal = User.objects.create_user("customer@concord.test", DEMO_PASSWORD, name="Asha Menon", role="customer")
        self.portal_customer = Customer.objects.create(
            user=portal, name="Asha Menon", company="Menon Textiles", email=portal.email,
            phone="+91 98470 12345", address="MG Road, Kochi, Kerala 682016", tax_id="32ABCDE1234F1Z5",
        )

    def _catalog(self):
        gst18 = TaxRule.objects.create(name="GST 18%", rate_percent=Decimal("18.00"))
        TaxRule.objects.create(name="GST 5%", rate_percent=Decimal("5.00"))
        product = Product.objects.create
        suite = product(name="Concord Suite", type="software", sales_price=Decimal("999.00"), cost_price=Decimal("300.00"),
                        tax_rule=gst18, notes="Core business software, per seat.")
        ProductVariant.objects.create(product=suite, attribute="Brand", value="Odoo", extra_price=Decimal("560.00"))
        ProductVariant.objects.create(product=suite, attribute="Brand", value="Zoho", extra_price=Decimal("300.00"))
        analytics = product(name="Analytics add-on", type="addon", sales_price=Decimal("299.00"),
                            cost_price=Decimal("60.00"), tax_rule=gst18)
        storage = product(name="Extra storage", type="addon", sales_price=Decimal("199.00"),
                          cost_price=Decimal("40.00"), tax_rule=gst18)
        support = product(name="Priority support", type="service", sales_price=Decimal("1499.00"),
                          cost_price=Decimal("700.00"), tax_rule=gst18)
        self.products = [suite, analytics, storage, support]

        plan = Plan.objects.create
        monthly = plan(name="Monthly", interval="monthly", term_periods=12)
        business = plan(name="Business Monthly", price=Decimal("499.00"), interval="monthly", term_periods=12,
                        tax_rule=gst18, min_quantity=2)
        yearly = plan(name="Enterprise Yearly", price=Decimal("9999.00"), interval="yearly", term_periods=1,
                      tax_rule=gst18, min_quantity=5, pausable=False)
        weekly = plan(name="Weekly", interval="weekly", term_periods=52)
        trial = plan(name="Daily Pilot", interval="daily", term_periods=30, auto_close=True, renewable=False)
        # Weighted so the mix looks like a real business. Daily plans are rare pilots.
        self.plans = [monthly] * 8 + [business] * 5 + [yearly] * 3 + [weekly] * 2 + [trial]

        template = QuotationTemplate.objects.create(name="Enterprise rollout", plan=yearly, validity_days=30,
                                                    notes="Standard offer for large customers.")
        TemplateLine.objects.create(template=template, product=suite, quantity=25)
        TemplateLine.objects.create(template=template, product=support, quantity=5)
        starter = QuotationTemplate.objects.create(name="Small shop starter", plan=monthly, validity_days=14)
        TemplateLine.objects.create(template=starter, product=suite, quantity=2)
        TemplateLine.objects.create(template=starter, product=analytics, quantity=1)

        start = self.today - timedelta(days=720)
        self.volume = DiscountRule.objects.create(name="Volume 10%", kind="percent", value=Decimal("10.00"),
                                                  min_quantity=5, starts_on=start)
        DiscountRule.objects.create(name="Launch ₹500 off", kind="fixed", value=Decimal("500.00"), usage_limit=100,
                                    starts_on=start, ends_on=self.today + timedelta(days=90))
        support_deal = DiscountRule.objects.create(name="Support at half price", kind="percent", value=Decimal("50.00"),
                                                   scope="products", usage_limit=50, starts_on=start)
        support_deal.products.add(support)

    def _customers(self, count):
        rows = []
        for i in range(count):
            first, last = self.rng.choice(FIRST), self.rng.choice(LAST)
            place = self.rng.choice(PLACES)
            rows.append(Customer(
                name=f"{first} {last}",
                company=f"{last} {self.rng.choice(BUSINESS)}",
                email=f"{first}.{last}.{i}@example.com".lower(),
                phone=f"+91 9{self.rng.randint(100000000, 999999999)}",
                address=f"{self.rng.randint(1, 200)}, Main Road, {place}",
            ))
        self.customers = Customer.objects.bulk_create(rows, batch_size=1000) + [self.portal_customer]

    def _status(self, position):
        """The first few belong to the portal customer, so the demo login has one of each."""
        roll = self.rng.random()
        for limit, status in [(0.72, "active"), (0.78, "paused"), (0.90, "closed"),
                              (0.95, "quotation"), (0.98, "confirmed"), (1.0, "draft")]:
            if roll < limit:
                return status
        return "active"

    def _line_specs(self, plan):
        # Short billing cycles are small purchases. Twenty-five seats billed daily would
        # dwarf every other customer and make the revenue figures look absurd.
        if plan.interval == "daily":
            return [(self.products[2], 1, Decimal("19.00"))]
        if plan.interval == "weekly":
            return [(self.products[1], self.rng.choice([1, 2]), Decimal("79.00"))]
        chosen = self.rng.sample(self.products, self.rng.randint(1, 2))
        specs = []
        for product in chosen:
            quantity = max(plan.min_quantity, self.rng.choice([1, 2, 3, 5, 10, 25]))
            specs.append((product, quantity, product.sales_price))
        return specs

    def _subscriptions(self, count):
        tax_rate, tax_name = Decimal("18.00"), "GST 18%"
        subscriptions, lines, events = [], [], []
        self.sub_plans = {}
        for i in range(count):
            plan = self.rng.choice(self.plans)
            customer = self.portal_customer if i < 4 else self.rng.choice(self.customers)
            status = ["active", "active", "quotation", "active"][i] if i < 4 else self._status(i)
            specs = self._line_specs(plan)
            subtotal = sum((price * quantity for _, quantity, price in specs), plan.price)
            history = {"daily": 25, "weekly": 200, "monthly": 540, "yearly": 1000}[plan.interval]
            start = self.today - timedelta(days=self.rng.randint(0 if status in ("quotation", "draft", "confirmed") else 1, history))
            term = plan.term_periods + (0 if plan.interval == "daily" else self.rng.randint(0, 24))
            subscriptions.append(Subscription(
                number=f"SUB-{i + 1:06d}",
                customer=customer,
                plan=plan,
                status=status,
                start_date=start,
                expiry_date=add_periods(start, plan.interval, max(term, 2)),
                payment_terms_days=self.rng.choice([15, 30, 30, 45]),
                quote_valid_until=self.today + timedelta(days=14) if status == "quotation" else None,
                recurring_subtotal=round_money(subtotal),
                closed_at=timezone.now() if status == "closed" else None,
            ))
            self.sub_plans[i] = specs
        Subscription.objects.bulk_create(subscriptions, batch_size=1000)

        invoices, invoice_lines, payments = [], [], []
        volume_uses = 0
        sequence = {}
        for i, subscription in enumerate(subscriptions):
            specs = self.sub_plans[i]
            plan = subscription.plan
            if plan.price > 0:
                lines.append(SubscriptionLine(subscription=subscription, description=f"{plan.name} plan", quantity=1, unit_price=plan.price))
            for product, quantity, price in specs:
                lines.append(SubscriptionLine(subscription=subscription, product=product, description=product.name, quantity=quantity, unit_price=price))
            events.append(SubscriptionEvent(subscription=subscription, to_status="draft", note="Created"))
            if subscription.status != "draft":
                events.append(SubscriptionEvent(subscription=subscription, from_status="draft", to_status=subscription.status))
            if subscription.status not in ("active", "paused", "closed"):
                continue

            # Bill every period from the start to today, the same way a billing run would.
            inputs = ([LineInput(description=f"{plan.name} plan", quantity=1, unit_price=plan.price, tax_name=tax_name, tax_rate=tax_rate)]
                      if plan.price > 0 else [])
            inputs += [LineInput(description=p.name, quantity=q, unit_price=u, tax_name=tax_name, tax_rate=tax_rate, product_id=p.id)
                       for p, q, u in specs]
            use_volume = self.rng.random() < 0.25
            subscription.discount = self.volume if use_volume else None
            discount = DiscountInput(kind="percent", value=self.volume.value, min_quantity=self.volume.min_quantity) if use_volume else None
            priced = price_invoice(inputs, discount)

            subscription.billing_anchor = subscription.start_date
            index, period_start = 0, subscription.start_date
            while period_start <= self.today and period_start < subscription.expiry_date:
                period_end = add_periods(subscription.start_date, plan.interval, index + 1)
                issue = period_start
                due = issue + timedelta(days=subscription.payment_terms_days)
                year = issue.year
                sequence[year] = sequence.get(year, 0) + 1
                age = (self.today - issue).days
                status, paid = self._invoice_outcome(age, priced.total, due)
                invoice = Invoice(
                    number=f"INV-{year}-{sequence[year]:06d}",
                    subscription=subscription,
                    customer=subscription.customer,
                    status=status,
                    period_start=period_start,
                    period_end=min(period_end, subscription.expiry_date),
                    issue_date=issue,
                    due_date=due,
                    customer_name=subscription.customer.company or subscription.customer.name,
                    customer_email=subscription.customer.email,
                    customer_address=subscription.customer.address,
                    subtotal=priced.subtotal,
                    discount_total=priced.discount_total,
                    tax_total=priced.tax_total,
                    total=priced.total,
                    amount_paid=paid,
                    discount_rule=self.volume if priced.discount_total > 0 else None,
                    confirmed_at=timezone.now() if status != "draft" else None,
                )
                invoices.append(invoice)
                invoice_lines += [
                    InvoiceLine(invoice=invoice, description=p.description, quantity=p.quantity, unit_price=p.unit_price,
                                discount_amount=p.discount_amount, tax_name=p.tax_name, tax_rate=p.tax_rate,
                                tax_amount=p.tax_amount, line_total=p.line_total)
                    for p in priced.lines
                ]
                if paid > 0:
                    paid_on = min(self.today, issue + timedelta(days=self.rng.randint(1, max(1, subscription.payment_terms_days))))
                    payments.append(Payment(invoice=invoice, method=self.rng.choice(METHODS), amount=paid, paid_on=paid_on))
                if priced.discount_total > 0:
                    volume_uses += 1
                index += 1
                period_start = period_end
            subscription.periods_billed = index
            subscription.next_billing_date = None if subscription.status == "closed" else period_start

        Subscription.objects.bulk_update(
            subscriptions, ["discount", "billing_anchor", "periods_billed", "next_billing_date"], batch_size=1000
        )
        SubscriptionLine.objects.bulk_create(lines, batch_size=2000)
        SubscriptionEvent.objects.bulk_create(events, batch_size=2000)
        Invoice.objects.bulk_create(invoices, batch_size=2000)
        InvoiceLine.objects.bulk_create(invoice_lines, batch_size=2000)
        Payment.objects.bulk_create(payments, batch_size=2000)

        DiscountRule.objects.filter(pk=self.volume.pk).update(times_used=volume_uses)
        DocumentSequence.objects.create(name="subscription", next_value=len(subscriptions) + 1)
        for year, value in sequence.items():
            DocumentSequence.objects.create(name=f"invoice-{year}", next_value=value + 1)

    def _invoice_outcome(self, age, total, due):
        """Older invoices are mostly settled. Recent ones are a realistic mix."""
        roll = self.rng.random()
        if total == 0:
            return "paid", Decimal("0.00")
        if age <= 5 and roll < 0.5:
            return "draft", Decimal("0.00")
        settled = 0.97 if age > 90 else 0.75 if age > 45 else 0.45
        if roll < settled:
            return "paid", total
        if roll < settled + (1 - settled) * 0.25:
            return "confirmed", round_money(total * Decimal("0.4"))
        return "confirmed", Decimal("0.00")
