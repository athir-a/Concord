from datetime import date
from decimal import Decimal

import pytest

from apps.billing import services as billing
from apps.catalog.models import Plan, ProductVariant, QuotationTemplate, TemplateLine
from apps.common.exceptions import DomainError
from apps.subscriptions import services
from apps.subscriptions.models import Subscription

from .conftest import JAN_1

Status = Subscription.Status
pytestmark = pytest.mark.django_db


def refuses(code, action, *args, **kwargs):
    with pytest.raises(DomainError) as caught:
        action(*args, **kwargs)
    assert caught.value.detail.code == code


def test_full_lifecycle_and_history(make_subscription, staff):
    subscription = make_subscription(actor=staff)
    assert subscription.status == Status.DRAFT
    assert subscription.number.startswith("SUB-")

    services.send_quotation(subscription, actor=staff, today=JAN_1)
    services.confirm_quotation(subscription, actor=staff, today=JAN_1)
    billing.activate(subscription, actor=staff, today=JAN_1)
    services.close(subscription, actor=staff)

    subscription.refresh_from_db()
    assert subscription.status == Status.CLOSED
    assert subscription.next_billing_date is None
    assert [e.to_status for e in subscription.events.all()] == ["draft", "quotation", "confirmed", "active", "closed"]
    assert all(e.actor == staff for e in subscription.events.all())


INVALID_MOVES = [
    (Status.DRAFT, Status.CONFIRMED), (Status.DRAFT, Status.ACTIVE), (Status.DRAFT, Status.PAUSED),
    (Status.QUOTATION, Status.ACTIVE), (Status.CONFIRMED, Status.DRAFT), (Status.CONFIRMED, Status.PAUSED),
    (Status.ACTIVE, Status.DRAFT), (Status.ACTIVE, Status.CONFIRMED), (Status.PAUSED, Status.CONFIRMED),
    (Status.CLOSED, Status.ACTIVE), (Status.CLOSED, Status.DRAFT),
]


@pytest.mark.parametrize("from_status, to_status", INVALID_MOVES)
def test_invalid_moves_are_refused(make_subscription, from_status, to_status):
    subscription = make_subscription()
    Subscription.objects.filter(pk=subscription.pk).update(status=from_status)
    subscription.refresh_from_db()
    refuses("invalid_transition", services.transition, subscription, to_status)


def test_new_subscription_gets_default_expiry_from_plan(make_subscription):
    assert make_subscription().expiry_date == date(2027, 1, 1)


def test_plan_fee_becomes_a_line_and_counts_in_subtotal(make_subscription, plan):
    plan.price = Decimal("499.00")
    plan.save()
    subscription = make_subscription(quantity=2)
    assert [line.description for line in subscription.lines.all()] == ["Monthly plan", "Concord Suite"]
    assert subscription.recurring_subtotal == Decimal("2497.00")


def test_variant_adds_its_extra_price(make_subscription, product):
    odoo = ProductVariant.objects.create(product=product, attribute="Brand", value="Odoo", extra_price=Decimal("560.00"))
    subscription = make_subscription(line_specs=[{"product": product, "variant": odoo, "quantity": 1}])
    line = subscription.lines.get()
    assert line.unit_price == Decimal("1559.00")
    assert line.description == "Concord Suite (Odoo)"


def test_variant_must_belong_to_the_product(make_subscription, product):
    other = type(product).objects.create(name="Other", sales_price=Decimal("1.00"))
    wrong = ProductVariant.objects.create(product=other, attribute="Brand", value="X")
    refuses("validation_error", make_subscription, line_specs=[{"product": product, "variant": wrong, "quantity": 1}])
    assert not Subscription.objects.exists()  # all or nothing


def test_minimum_quantity_is_enforced(make_subscription, plan):
    plan.min_quantity = 5
    plan.save()
    refuses("validation_error", make_subscription, quantity=4)
    assert make_subscription(quantity=5).lines.get().quantity == 5


@pytest.mark.parametrize("window", [
    {"available_from": date(2026, 6, 1)},
    {"available_to": date(2025, 12, 31)},
    {"is_active": False},
])
def test_unavailable_plan_is_refused(make_subscription, plan, window):
    Plan.objects.filter(pk=plan.pk).update(**window)
    plan.refresh_from_db()
    refuses("validation_error", make_subscription)


def test_template_creates_a_quote_valid_for_its_days(customer, plan, product):
    template = QuotationTemplate.objects.create(name="Starter", plan=plan, validity_days=15)
    TemplateLine.objects.create(template=template, product=product, quantity=3)
    subscription = services.create_from_template(template=template, customer=customer, start_date=JAN_1, today=JAN_1)
    assert subscription.quote_valid_until == date(2026, 1, 16)
    assert subscription.lines.get().quantity == 3


def test_expired_quote_can_not_be_confirmed(make_subscription):
    subscription = make_subscription(quote_valid_until=date(2026, 1, 10))
    services.send_quotation(subscription, today=date(2026, 1, 10))
    refuses("quote_expired", services.confirm_quotation, subscription, today=date(2026, 1, 11))
    services.confirm_quotation(subscription, today=date(2026, 1, 10))


def test_only_a_draft_can_be_edited(make_subscription, product):
    subscription = make_subscription()
    services.update_draft(subscription, line_specs=[{"product": product, "quantity": 4}], payment_terms_days=15)
    subscription.refresh_from_db()
    assert subscription.payment_terms_days == 15
    assert subscription.recurring_subtotal == Decimal("3996.00")

    services.send_quotation(subscription, today=JAN_1)
    refuses("invalid_transition", services.update_draft, subscription, payment_terms_days=7)


def test_quote_with_no_lines_can_not_be_sent(make_subscription):
    subscription = make_subscription(line_specs=[])
    refuses("validation_error", services.send_quotation, subscription, today=JAN_1)


def test_plan_flags_decide_what_is_allowed(make_active, plan):
    subscription = make_active()
    Plan.objects.filter(pk=plan.pk).update(pausable=False, closable=False, renewable=False)
    refuses("invalid_transition", services.pause, subscription)
    refuses("invalid_transition", services.close, subscription)
    refuses("invalid_transition", services.renew, subscription)


def test_a_quote_can_be_closed_even_if_the_plan_is_not_closable(make_subscription, plan):
    Plan.objects.filter(pk=plan.pk).update(closable=False)
    assert services.close(make_subscription()).status == Status.CLOSED


def test_renew_extends_expiry_by_one_term(make_active):
    subscription = make_active()
    subscription = services.renew(subscription)
    assert subscription.expiry_date == date(2028, 1, 1)
    assert "Renewed" in subscription.events.last().note


def test_closed_subscription_can_not_be_renewed(make_active):
    subscription = make_active()
    services.close(subscription)
    refuses("invalid_transition", services.renew, subscription)
