"""The database's own guarantees. These bypass all app code on purpose."""
from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.accounts.models import Customer
from apps.billing.models import Invoice, Payment
from apps.catalog.models import DiscountRule, Plan
from apps.subscriptions.models import Subscription

pytestmark = pytest.mark.django_db


@pytest.fixture
def subscription():
    return Subscription.objects.create(
        number="SUB-1",
        customer=Customer.objects.create(name="Asha Stores", email="asha@shop.in"),
        plan=Plan.objects.create(name="Monthly", price=Decimal("999.00")),
        start_date=date(2026, 1, 1),
        expiry_date=date(2027, 1, 1),
    )


def make_invoice(subscription, number, **overrides):
    fields = {
        "number": number,
        "subscription": subscription,
        "customer": subscription.customer,
        "period_start": date(2026, 1, 1),
        "period_end": date(2026, 2, 1),
        "issue_date": date(2026, 1, 1),
        "due_date": date(2026, 1, 31),
        "customer_name": "Asha Stores",
        "customer_email": "asha@shop.in",
        "total": Decimal("1178.82"),
    }
    return Invoice.objects.create(**(fields | overrides))


def assert_rejected(create):
    with pytest.raises(IntegrityError), transaction.atomic():
        create()


def test_second_live_invoice_for_a_period_is_refused(subscription):
    make_invoice(subscription, "INV-1")
    assert_rejected(lambda: make_invoice(subscription, "INV-2"))


def test_cancelled_invoice_frees_its_period_for_reissue(subscription):
    make_invoice(subscription, "INV-1", status=Invoice.Status.CANCELLED)
    assert make_invoice(subscription, "INV-2").status == Invoice.Status.DRAFT


def test_next_period_is_allowed(subscription):
    make_invoice(subscription, "INV-1")
    make_invoice(subscription, "INV-2", period_start=date(2026, 2, 1), period_end=date(2026, 3, 1))
    assert subscription.invoices.count() == 2


def test_invoice_numbers_are_unique(subscription):
    make_invoice(subscription, "INV-1")
    assert_rejected(lambda: make_invoice(subscription, "INV-1", period_start=date(2026, 2, 1), period_end=date(2026, 3, 1)))


def test_paid_amount_cannot_exceed_total(subscription):
    assert_rejected(lambda: make_invoice(subscription, "INV-1", total=Decimal("100.00"), amount_paid=Decimal("100.01")))


def test_payment_must_be_positive(subscription):
    invoice = make_invoice(subscription, "INV-1")
    assert_rejected(lambda: Payment.objects.create(
        invoice=invoice, method="upi", amount=Decimal("0.00"), paid_on=date(2026, 1, 2)
    ))


def test_payment_idempotency_key_is_unique(subscription):
    invoice = make_invoice(subscription, "INV-1")
    payment = {"invoice": invoice, "method": "upi", "amount": Decimal("10.00"), "paid_on": date(2026, 1, 2)}
    Payment.objects.create(**payment, idempotency_key="abc")
    Payment.objects.create(**payment)  # payments without a key don't collide
    Payment.objects.create(**payment)
    assert_rejected(lambda: Payment.objects.create(**payment, idempotency_key="abc"))


def test_discount_cannot_exceed_usage_limit():
    rule = {"name": "Seats", "kind": "percent", "value": Decimal("10.00"), "starts_on": date(2026, 1, 1)}
    assert_rejected(lambda: DiscountRule.objects.create(**rule, usage_limit=1, times_used=2))


def test_percent_discount_cannot_exceed_100():
    assert_rejected(lambda: DiscountRule.objects.create(
        name="Too much", kind="percent", value=Decimal("100.01"), starts_on=date(2026, 1, 1)
    ))


def test_subscription_must_expire_after_it_starts(subscription):
    assert_rejected(lambda: Subscription.objects.create(
        number="SUB-2",
        customer=subscription.customer,
        plan=subscription.plan,
        start_date=date(2026, 1, 1),
        expiry_date=date(2026, 1, 1),
    ))
