from datetime import date
from decimal import Decimal

import pytest

from apps.accounts.models import Customer, User
from apps.billing import services as billing
from apps.catalog.models import DiscountRule, Plan, Product, TaxRule
from apps.subscriptions import services as subscriptions

JAN_1 = date(2026, 1, 1)


@pytest.fixture
def staff(db):
    return User.objects.create_user("staff@concord.test", "Str0ng!pass", role="staff")


@pytest.fixture
def customer(db):
    return Customer.objects.create(name="Asha", company="Asha Stores", email="asha@shop.in")


@pytest.fixture
def gst(db):
    return TaxRule.objects.create(name="GST 18%", rate_percent=Decimal("18.00"))


@pytest.fixture
def product(db, gst):
    return Product.objects.create(name="Concord Suite", sales_price=Decimal("999.00"), tax_rule=gst)


@pytest.fixture
def plan(db):
    """Products carry the price here, so invoice amounts are easy to check by hand."""
    return Plan.objects.create(name="Monthly", interval="monthly", term_periods=12)


@pytest.fixture
def make_subscription(customer, plan, product):
    def make(**overrides):
        quantity = overrides.pop("quantity", 1)
        fields = {
            "customer": customer,
            "plan": plan,
            "start_date": JAN_1,
            "line_specs": [{"product": product, "quantity": quantity}],
        }
        return subscriptions.create_subscription(**(fields | overrides))
    return make


@pytest.fixture
def make_active(make_subscription):
    """An active subscription whose first invoice exists. It's been billed up to `today`."""
    def make(today=JAN_1, **overrides):
        subscription = make_subscription(**overrides)
        subscriptions.send_quotation(subscription, today=today)
        subscriptions.confirm_quotation(subscription, today=today)
        return billing.activate(subscription, today=today)
    return make


@pytest.fixture
def make_discount(db):
    def make(**overrides):
        fields = {"name": "Seats", "kind": "percent", "value": Decimal("10.00"), "starts_on": date(2025, 1, 1)}
        return DiscountRule.objects.create(**(fields | overrides))
    return make
