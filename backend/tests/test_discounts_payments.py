import threading
import time
from datetime import date
from decimal import Decimal

import pytest
from django.db import connection

from apps.billing import services as billing
from apps.billing.models import Invoice, Payment
from apps.catalog.models import DiscountRule
from apps.common.exceptions import DomainError
from apps.subscriptions import services as subscriptions

from .conftest import JAN_1

FEB_1 = date(2026, 2, 1)
MAR_1 = date(2026, 3, 1)
pytestmark = pytest.mark.django_db


def refuses(code, action, *args, **kwargs):
    with pytest.raises(DomainError) as caught:
        action(*args, **kwargs)
    assert caught.value.detail.code == code


# --- Discounts ---

def test_attached_discount_appears_on_the_next_invoice_by_itself(make_active, make_discount):
    subscription = make_active()
    assert subscription.invoices.get().discount_total == 0

    subscriptions.set_discount(subscription, make_discount())
    billing.run_billing(as_of=FEB_1)

    invoice = subscription.invoices.get(period_start=FEB_1)
    assert invoice.discount_total == Decimal("99.90")
    assert invoice.total == Decimal("1060.94")  # 899.10 + 18% tax of 161.84 (161.838 rounded)


def test_discount_stops_after_its_end_date(make_active, make_discount):
    subscription = make_active(discount=make_discount(ends_on=FEB_1))
    billing.run_billing(as_of=MAR_1)
    assert subscription.invoices.get(period_start=FEB_1).discount_total > 0
    assert subscription.invoices.get(period_start=MAR_1).discount_total == 0


def test_discount_waits_for_its_start_date(make_active, make_discount):
    subscription = make_active(discount=make_discount(starts_on=FEB_1))
    billing.run_billing(as_of=FEB_1)
    assert subscription.invoices.get(period_start=JAN_1).discount_total == 0
    assert subscription.invoices.get(period_start=FEB_1).discount_total > 0


def test_discount_stops_when_it_runs_out(make_active, make_discount):
    rule = make_discount(usage_limit=2)
    subscription = make_active(discount=rule)
    billing.run_billing(as_of=MAR_1)
    rule.refresh_from_db()
    assert rule.times_used == 2
    discounts = [i.discount_total for i in subscription.invoices.order_by("period_start")]
    assert [d > 0 for d in discounts] == [True, True, False]


def test_unmet_minimum_does_not_use_up_a_turn(make_active, make_discount):
    rule = make_discount(min_quantity=5, usage_limit=1)
    invoice = make_active(discount=rule, quantity=4).invoices.get()
    rule.refresh_from_db()
    assert invoice.discount_total == 0
    assert invoice.discount_rule is None
    assert rule.times_used == 0


def test_cancelling_an_invoice_gives_the_use_back(make_active, make_discount):
    rule = make_discount(usage_limit=1)
    invoice = make_active(discount=rule).invoices.get()
    rule.refresh_from_db()
    assert rule.times_used == 1
    billing.cancel_invoice(invoice)
    rule.refresh_from_db()
    assert rule.times_used == 0


def test_product_scoped_discount_through_billing(make_active, make_discount, product):
    rule = make_discount(scope=DiscountRule.Scope.PRODUCTS, value=Decimal("50.00"))
    rule.products.add(product)
    invoice = make_active(discount=rule).invoices.get()
    assert invoice.discount_total == Decimal("499.50")


def test_preview_matches_the_real_invoice_and_writes_nothing(make_active, make_discount, make_subscription):
    rule = make_discount(usage_limit=5)
    draft = make_subscription(discount=rule, quantity=3)
    preview = billing.preview_invoice(draft, on_date=JAN_1)
    rule.refresh_from_db()
    assert rule.times_used == 0
    assert not Invoice.objects.exists()

    invoice = make_active(discount=rule, quantity=3).invoices.get()
    assert (preview.total, preview.discount_total) == (invoice.total, invoice.discount_total)


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(connection.vendor != "postgresql", reason="SQLite has no row locks")
def test_a_discount_never_goes_past_its_limit(make_active, make_discount, monkeypatch):
    """The delay falls between checking the limit and using it up, so runs must collide there."""
    rule = make_discount(usage_limit=2)
    for _ in range(6):
        make_active(start_date=FEB_1, discount=rule)  # nothing billed yet
    real_price = billing.price_invoice

    def slow_price(*args, **kwargs):
        time.sleep(0.05)
        return real_price(*args, **kwargs)

    monkeypatch.setattr(billing, "price_invoice", slow_price)
    start = threading.Barrier(3)
    runs = []

    def worker():
        connection.ensure_connection()
        start.wait(timeout=10)
        runs.append(billing.run_billing(as_of=FEB_1))
        connection.close()

    threads = [threading.Thread(target=worker) for _ in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    rule.refresh_from_db()
    assert rule.times_used == 2
    assert Invoice.objects.filter(discount_total__gt=0).count() == 2
    assert Invoice.objects.count() == 6
    assert sum(run.failed_count for run in runs) == 0


# --- Payments ---

@pytest.fixture
def invoice(make_active):
    return billing.confirm_invoice(make_active().invoices.get())  # total 1178.82


def pay(invoice, amount, **overrides):
    fields = {"method": "upi", "amount": Decimal(amount), "paid_on": date(2026, 1, 5), "today": date(2026, 1, 5)}
    return billing.record_payment(invoice, **(fields | overrides))


def test_partial_payment_stays_outstanding_then_full_payment_settles(invoice, staff):
    payment = pay(invoice, "1000.00", note="UTR 4471", actor=staff)
    assert payment.note == "UTR 4471"
    assert payment.recorded_by == staff
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.CONFIRMED
    assert invoice.amount_paid == Decimal("1000.00")

    pay(invoice, "178.82")
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.PAID


def test_overpayment_is_refused(invoice):
    pay(invoice, "1000.00")
    refuses("overpayment", pay, invoice, "178.83")
    invoice.refresh_from_db()
    assert invoice.amount_paid == Decimal("1000.00")


@pytest.mark.parametrize("amount", ["0.00", "-5.00"])
def test_amount_must_be_positive(invoice, amount):
    refuses("validation_error", pay, invoice, amount)


def test_future_payment_date_is_refused(invoice):
    refuses("validation_error", pay, invoice, "10.00", paid_on=date(2026, 1, 6))


def test_draft_can_not_be_paid(make_active):
    refuses("invoice_not_payable", pay, make_active().invoices.get(), "1.00")


def test_paid_invoice_can_not_be_paid_again(invoice):
    pay(invoice, "1178.82")
    refuses("invoice_not_payable", pay, invoice, "1.00")


def test_same_key_records_one_payment(invoice):
    first = pay(invoice, "100.00", idempotency_key="click-1")
    again = pay(invoice, "100.00", idempotency_key="click-1")
    assert first.pk == again.pk
    invoice.refresh_from_db()
    assert invoice.amount_paid == Decimal("100.00")


def test_retry_after_settling_returns_the_payment_not_an_error(invoice):
    first = pay(invoice, "1178.82", idempotency_key="click-1")
    assert pay(invoice, "1178.82", idempotency_key="click-1").pk == first.pk


def test_key_can_not_be_reused_on_another_invoice(invoice, make_active):
    pay(invoice, "1.00", idempotency_key="click-1")
    other = billing.confirm_invoice(make_active().invoices.get())
    refuses("idempotency_conflict", pay, other, "1.00", idempotency_key="click-1")


def test_invoice_with_payments_can_not_be_cancelled(invoice):
    pay(invoice, "1.00")
    refuses("invoice_has_payments", billing.cancel_invoice, invoice)


def test_fully_discounted_invoice_is_paid_on_confirmation(make_active, make_discount):
    rule = make_discount(value=Decimal("100.00"))
    invoice = billing.confirm_invoice(make_active(discount=rule).invoices.get())
    assert invoice.total == 0
    assert invoice.status == Invoice.Status.PAID


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(connection.vendor != "postgresql", reason="SQLite has no row locks")
def test_simultaneous_payments_can_not_overpay(make_active, monkeypatch):
    """The delay falls between checking the balance and recording the payment."""
    invoice = billing.confirm_invoice(make_active().invoices.get())
    real_create = Payment.objects.create

    def slow_create(**kwargs):
        time.sleep(0.1)
        return real_create(**kwargs)

    monkeypatch.setattr(Payment.objects, "create", slow_create)
    start = threading.Barrier(4)
    refused = []

    def worker():
        connection.ensure_connection()
        start.wait(timeout=10)
        try:
            pay(invoice, "700.00")
        except DomainError:
            refused.append(True)
        finally:
            connection.close()

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    invoice.refresh_from_db()
    assert invoice.amount_paid == Decimal("700.00")
    assert Payment.objects.count() == 1
    assert len(refused) == 3
