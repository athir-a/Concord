"""The API as each role sees it. The services are tested elsewhere; this tests the doors."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Customer, User
from apps.billing import services as billing
from apps.billing.models import Invoice, Payment
from apps.catalog.models import DiscountRule, Plan, Product, ProductVariant, QuotationTemplate, TemplateLine, TaxRule
from apps.subscriptions.models import Subscription

pytestmark = pytest.mark.django_db
API = "/api/v1"
TODAY = timezone.localdate()


def client_for(user=None):
    client = APIClient()
    if user:
        client.force_authenticate(user)
    return client


@pytest.fixture
def admin(db):
    return User.objects.create_user("admin@concord.test", "Str0ng!pass", role="admin")


@pytest.fixture
def owner(db):
    """A customer with a portal login."""
    user = User.objects.create_user("asha@shop.in", "Str0ng!pass", role="customer")
    Customer.objects.create(user=user, name="Asha", email=user.email)
    return user


@pytest.fixture
def stranger(db):
    user = User.objects.create_user("ravi@shop.in", "Str0ng!pass", role="customer")
    Customer.objects.create(user=user, name="Ravi", email=user.email)
    return user


@pytest.fixture
def active(make_active, owner):
    return make_active(today=TODAY, start_date=TODAY, customer=owner.customer, quantity=2)


# --- The full journey, through the API only ---

def test_quote_to_paid_through_the_api(admin, staff, owner, plan, product, gst):
    team = client_for(staff)
    portal = client_for(owner)

    response = team.post(f"{API}/subscriptions", {
        "customer": owner.customer.id, "plan": plan.id, "start_date": str(TODAY),
        "lines": [{"product": product.id, "quantity": 3}],
    }, format="json")
    assert response.status_code == 201
    subscription = response.data["id"]
    assert response.data["status"] == "draft"
    assert response.data["actions"] == ["send", "close"]

    preview = team.get(f"{API}/subscriptions/{subscription}/preview")
    assert preview.data["total"] == "3536.46"

    # A draft isn't visible to the customer until it's sent.
    assert portal.get(f"{API}/subscriptions/{subscription}").status_code == 404
    assert team.post(f"{API}/subscriptions/{subscription}/send").status_code == 200

    response = portal.get(f"{API}/subscriptions/{subscription}")
    assert response.status_code == 200
    assert "confirm" in response.data["actions"]
    assert "revise" not in response.data["actions"]
    assert portal.post(f"{API}/subscriptions/{subscription}/confirm").data["status"] == "confirmed"

    response = team.post(f"{API}/subscriptions/{subscription}/activate")
    assert response.data["status"] == "active"
    assert [event["to_status"] for event in response.data["events"]] == ["draft", "quotation", "confirmed", "active"]

    invoice = team.get(f"{API}/invoices", {"subscription": subscription}).data["results"][0]
    assert invoice["status"] == "draft"
    assert invoice["total"] == "3536.46"
    # The team hasn't confirmed it, so the customer can't see it yet.
    assert portal.get(f"{API}/invoices").data["count"] == 0

    assert team.post(f"{API}/invoices/{invoice['id']}/confirm").data["status"] == "confirmed"
    assert portal.get(f"{API}/invoices").data["count"] == 1

    payment = {"method": "upi", "paid_on": str(TODAY), "note": "UTR 4471"}
    response = team.post(f"{API}/invoices/{invoice['id']}/payments", payment | {"amount": "1000.00"}, format="json")
    assert response.status_code == 201
    assert (response.data["status"], response.data["amount_due"]) == ("confirmed", "2536.46")

    response = team.post(f"{API}/invoices/{invoice['id']}/payments", payment | {"amount": "2536.46"}, format="json")
    assert (response.data["status"], response.data["amount_due"]) == ("paid", "0.00")
    assert len(response.data["payments"]) == 2

    summary = team.get(f"{API}/reports/summary").data
    assert summary["active_subscriptions"] == 1
    assert summary["collected"] == "3536.46"
    assert summary["outstanding"] == "0.00"
    assert summary["mrr"] == "2997.00"
    assert summary["arr"] == "35964.00"


# --- Who can reach what ---

@pytest.mark.parametrize("path", [
    "customers", "products", "plans", "tax-rules", "discount-rules", "quotation-templates",
    "subscriptions", "invoices", "payments", "reports/summary", "reports/revenue-series",
    "reports/overdue-ageing", "billing/runs", "billing/due", "users/staff",
])
def test_everything_needs_a_login(db, path):
    assert client_for().get(f"{API}/{path}").status_code == 401


@pytest.mark.parametrize("path", [
    "customers", "products", "plans", "tax-rules", "discount-rules", "quotation-templates",
    "reports/summary", "reports/revenue-series", "reports/overdue-ageing", "billing/runs", "billing/due", "users/staff",
])
def test_customers_are_kept_out_of_internal_data(owner, path):
    assert client_for(owner).get(f"{API}/{path}").status_code == 403


@pytest.mark.parametrize("path, body", [
    ("products", {"name": "X", "sales_price": "1.00"}),
    ("plans", {"name": "X"}),
    ("tax-rules", {"name": "X", "rate_percent": "5.00"}),
    ("discount-rules", {"name": "X", "kind": "fixed", "value": "5.00", "starts_on": "2026-01-01"}),
    ("billing/run", {}),
])
def test_only_admin_can_change_the_catalog_or_run_billing(staff, admin, path, body):
    assert client_for(staff).post(f"{API}/{path}", body, format="json").status_code == 403
    assert client_for(admin).post(f"{API}/{path}", body, format="json").status_code == 201


def test_staff_can_read_the_catalog(staff, product):
    assert client_for(staff).get(f"{API}/products").data["count"] == 1


# --- A customer only ever sees their own ---

def test_other_customers_records_are_a_404(active, stranger):
    invoice = active.invoices.get()
    billing.confirm_invoice(invoice)
    billing.record_payment(invoice, method="upi", amount=Decimal("1.00"), paid_on=TODAY)
    client = client_for(stranger)

    assert client.get(f"{API}/subscriptions/{active.id}").status_code == 404
    assert client.get(f"{API}/subscriptions/{active.id}/preview").status_code == 404
    assert client.get(f"{API}/invoices/{invoice.id}").status_code == 404
    assert client.get(f"{API}/subscriptions").data["count"] == 0
    assert client.get(f"{API}/invoices").data["count"] == 0
    assert client.get(f"{API}/payments").data["count"] == 0
    assert client.post(f"{API}/subscriptions/{active.id}/pause").status_code == 404
    assert client.post(f"{API}/subscriptions/{active.id}/close").status_code == 404


def test_not_found_has_the_standard_error_shape(owner):
    response = client_for(owner).get(f"{API}/invoices/999999")
    assert response.status_code == 404
    assert set(response.data) == {"code", "detail", "fields"}
    assert response.data["code"] == "not_found"


def test_customer_filters_can_not_reach_other_customers(active, stranger, owner):
    billing.confirm_invoice(active.invoices.get())
    response = client_for(stranger).get(f"{API}/invoices", {"customer": owner.customer.id})
    assert response.data["count"] == 0


@pytest.mark.parametrize("action", ["send", "revise", "activate", "renew", "discount"])
def test_customers_can_not_use_team_actions_on_their_own(active, owner, action):
    assert client_for(owner).post(f"{API}/subscriptions/{active.id}/{action}", {}, format="json").status_code == 403


def test_customer_can_not_touch_their_own_invoice_or_payments(active, owner):
    invoice = active.invoices.get()
    billing.confirm_invoice(invoice)
    client = client_for(owner)
    for action in ["confirm", "cancel", "send", "reissue"]:
        assert client.post(f"{API}/invoices/{invoice.id}/{action}").status_code == 403
    body = {"method": "upi", "amount": "1.00", "paid_on": str(TODAY)}
    assert client.post(f"{API}/invoices/{invoice.id}/payments", body, format="json").status_code == 403
    assert client.post(f"{API}/subscriptions", {}, format="json").status_code == 403


def test_customer_can_pause_and_resume_their_own(active, owner):
    client = client_for(owner)
    assert client.post(f"{API}/subscriptions/{active.id}/pause").data["status"] == "paused"
    assert client.post(f"{API}/subscriptions/{active.id}/resume").data["status"] == "active"


# --- Status can't be set directly ---

def test_patch_can_not_set_status_or_billing_fields(make_subscription, staff):
    subscription = make_subscription()
    response = client_for(staff).patch(f"{API}/subscriptions/{subscription.id}", {
        "status": "active", "next_billing_date": "2020-01-01", "periods_billed": 9, "payment_terms_days": 7,
    }, format="json")
    assert response.status_code == 200
    subscription.refresh_from_db()
    assert subscription.status == "draft"
    assert subscription.next_billing_date is None
    assert subscription.periods_billed == 0
    assert subscription.payment_terms_days == 7


def test_invoices_can_not_be_created_or_edited_directly(active, staff):
    client = client_for(staff)
    invoice = active.invoices.get()
    assert client.post(f"{API}/invoices", {"total": "1.00"}, format="json").status_code == 405
    assert client.patch(f"{API}/invoices/{invoice.id}", {"status": "paid"}, format="json").status_code == 405
    assert client.delete(f"{API}/invoices/{invoice.id}").status_code == 405


def test_payments_can_not_be_edited_or_deleted(active, staff):
    invoice = active.invoices.get()
    billing.confirm_invoice(invoice)
    payment = billing.record_payment(invoice, method="upi", amount=Decimal("1.00"), paid_on=TODAY)
    client = client_for(staff)
    assert client.patch(f"{API}/payments/{payment.id}", {"amount": "99.00"}, format="json").status_code == 405
    assert client.delete(f"{API}/payments/{payment.id}").status_code == 405


def test_invalid_transition_is_a_409(make_subscription, staff):
    subscription = make_subscription()
    response = client_for(staff).post(f"{API}/subscriptions/{subscription.id}/pause")
    assert response.status_code == 409
    assert response.data["code"] == "invalid_transition"


# --- Input validation ---

@pytest.mark.parametrize("path, body, field", [
    ("products", {"name": "X", "sales_price": "-1.00"}, "sales_price"),
    ("products", {"name": "", "sales_price": "1.00"}, "name"),
    ("products", {"name": "X", "sales_price": "1.999"}, "sales_price"),
    ("products", {"name": "X", "sales_price": "abc"}, "sales_price"),
    ("plans", {"name": "X", "min_quantity": 0}, "min_quantity"),
    ("plans", {"name": "X", "interval": "hourly"}, "interval"),
    ("plans", {"name": "X", "available_from": "2026-02-01", "available_to": "2026-01-01"}, "available_to"),
    ("tax-rules", {"name": "X", "rate_percent": "101.00"}, "rate_percent"),
    ("discount-rules", {"name": "X", "kind": "percent", "value": "101", "starts_on": "2026-01-01"}, "value"),
    ("discount-rules", {"name": "X", "kind": "fixed", "value": "0", "starts_on": "2026-01-01"}, "value"),
    ("discount-rules", {"name": "X", "kind": "fixed", "value": "5", "starts_on": "2026-02-01", "ends_on": "2026-01-01"}, "ends_on"),
    ("discount-rules", {"name": "X", "kind": "fixed", "value": "5", "starts_on": "2026-01-01", "scope": "products"}, "products"),
    ("customers", {"name": "X", "email": "not-an-email"}, "email"),
])
def test_bad_input_is_refused_with_the_field_named(admin, path, body, field):
    response = client_for(admin).post(f"{API}/{path}", body, format="json")
    assert response.status_code == 400
    assert field in response.data["fields"]


@pytest.mark.parametrize("amount, status_code", [("0.00", 400), ("-1.00", 400), ("abc", 400), ("99999.00", 422)])
def test_bad_payment_amounts(active, staff, amount, status_code):
    invoice = active.invoices.get()
    billing.confirm_invoice(invoice)
    body = {"method": "upi", "amount": amount, "paid_on": str(TODAY)}
    response = client_for(staff).post(f"{API}/invoices/{invoice.id}/payments", body, format="json")
    assert response.status_code == status_code
    assert "amount" in response.data["fields"]


def test_payment_needs_a_known_method(active, staff):
    invoice = active.invoices.get()
    billing.confirm_invoice(invoice)
    body = {"method": "bitcoin", "amount": "1.00", "paid_on": str(TODAY)}
    response = client_for(staff).post(f"{API}/invoices/{invoice.id}/payments", body, format="json")
    assert "method" in response.data["fields"]


def test_double_clicked_payment_is_recorded_once(active, staff):
    invoice = active.invoices.get()
    billing.confirm_invoice(invoice)
    body = {"method": "upi", "amount": "10.00", "paid_on": str(TODAY), "idempotency_key": "click-1"}
    client = client_for(staff)
    for _ in range(2):
        assert client.post(f"{API}/invoices/{invoice.id}/payments", body, format="json").status_code == 201
    assert Payment.objects.count() == 1


def test_deleting_something_in_use_is_a_clear_409(active, admin, plan):
    response = client_for(admin).delete(f"{API}/plans/{plan.id}")
    assert response.status_code == 409
    assert response.data["code"] == "in_use"


# --- Catalog writes ---

def test_product_with_variants(admin):
    body = {
        "name": "Suite", "type": "software", "sales_price": "1000.00", "cost_price": "400.00", "notes": "Flagship",
        "variants": [{"attribute": "Brand", "value": "Odoo", "extra_price": "560.00"}],
    }
    client = client_for(admin)
    response = client.post(f"{API}/products", body, format="json")
    assert response.status_code == 201
    assert response.data["variants"][0]["extra_price"] == "560.00"

    body["variants"] = [{"attribute": "Brand", "value": "Other", "extra_price": "10.00"}]
    response = client.patch(f"{API}/products/{response.data['id']}", {"variants": body["variants"]}, format="json")
    assert [v["value"] for v in response.data["variants"]] == ["Other"]


def test_duplicate_variants_are_refused(admin):
    variant = {"attribute": "Brand", "value": "Odoo", "extra_price": "1.00"}
    body = {"name": "Suite", "sales_price": "1.00", "variants": [variant, variant]}
    response = client_for(admin).post(f"{API}/products", body, format="json")
    assert "variants" in response.data["fields"]


def test_template_to_quote(admin, staff, customer, plan, product):
    response = client_for(admin).post(f"{API}/quotation-templates", {
        "name": "Starter", "plan": plan.id, "validity_days": 15, "lines": [{"product": product.id, "quantity": 2}],
    }, format="json")
    assert response.status_code == 201

    response = client_for(staff).post(f"{API}/subscriptions/from-template", {
        "template": response.data["id"], "customer": customer.id, "start_date": str(TODAY),
    }, format="json")
    assert response.status_code == 201
    assert response.data["quote_valid_until"] == str(TODAY + timedelta(days=15))
    assert response.data["lines"][0]["quantity"] == 2


def test_changing_a_drafts_plan_replaces_the_fee_line(make_subscription, staff, plan):
    plan.price = Decimal("100.00")
    plan.save()
    other = Plan.objects.create(name="Annual", price=Decimal("900.00"), interval="yearly")
    subscription = make_subscription()
    response = client_for(staff).patch(f"{API}/subscriptions/{subscription.id}", {"plan": other.id}, format="json")
    assert [line["description"] for line in response.data["lines"]] == ["Annual plan", "Concord Suite"]
    assert response.data["recurring_subtotal"] == "1899.00"


# --- Billing through the API ---

def test_billing_run_twice_through_the_api(make_active, admin):
    make_active(today=TODAY, start_date=TODAY)
    client = client_for(admin)
    next_month = str(TODAY + timedelta(days=40))
    assert client.get(f"{API}/billing/due", {"as_of": next_month}).data["due"] == 1

    assert client.post(f"{API}/billing/run", {"as_of": next_month}, format="json").data["created_count"] >= 1
    second = client.post(f"{API}/billing/run", {"as_of": next_month}, format="json")
    assert (second.data["created_count"], second.data["skipped_count"], second.data["failed_count"]) == (0, 0, 0)
    assert client.get(f"{API}/billing/due", {"as_of": next_month}).data["due"] == 0
    assert client.get(f"{API}/billing/runs").data["count"] == 2


def test_future_billing_refused_when_the_setting_is_off(admin, settings):
    settings.BILLING_ALLOW_FUTURE_AS_OF = False
    response = client_for(admin).post(f"{API}/billing/run", {"as_of": "2999-01-01"}, format="json")
    assert response.status_code == 422
    assert response.data["code"] == "future_as_of"


def test_send_invoice_through_the_api(active, staff, mailoutbox):
    invoice = active.invoices.get()
    billing.confirm_invoice(invoice)
    response = client_for(staff).post(f"{API}/invoices/{invoice.id}/send")
    assert response.status_code == 200
    assert response.data["sent_at"] is not None
    assert mailoutbox[0].to == ["asha@shop.in"]


# --- Filters and reports ---

def test_invoice_filters_and_overdue(make_active, staff):
    old = make_active(today=TODAY - timedelta(days=60), start_date=TODAY - timedelta(days=60), payment_terms_days=10)
    overdue = billing.confirm_invoice(old.invoices.order_by("id").first())
    current = make_active(today=TODAY, start_date=TODAY)
    billing.confirm_invoice(current.invoices.get())
    client = client_for(staff)

    results = client.get(f"{API}/invoices", {"overdue": "true"}).data["results"]
    assert [row["id"] for row in results] == [overdue.id]
    assert results[0]["is_overdue"] is True
    assert client.get(f"{API}/invoices", {"status": "confirmed"}).data["count"] == 2
    assert client.get(f"{API}/invoices", {"search": overdue.number}).data["count"] == 1
    assert client.get(f"{API}/invoices", {"overdue": "false"}).data["count"] == 1
    assert client.get(f"{API}/invoices", {"ordering": "-total", "page_size": 1}).data["count"] == 2


def test_report_numbers_worked_out_by_hand(make_active, staff, plan, gst, customer):
    """Yearly 12,000 + monthly 999 x 2 = MRR 2,998. Tax isn't part of MRR."""
    yearly = Plan.objects.create(name="Annual", interval="yearly")
    product = Product.objects.create(name="Annual suite", sales_price=Decimal("12000.00"))
    start = TODAY - timedelta(days=45)

    monthly = make_active(today=start, start_date=start, payment_terms_days=10, quantity=2)
    annual = make_active(
        today=TODAY, start_date=TODAY, plan=yearly, line_specs=[{"product": product, "quantity": 1}],
        expiry_date=TODAY + timedelta(days=400),
    )
    overdue = billing.confirm_invoice(monthly.invoices.get())  # 1998 + 18% = 2357.64, due 35 days ago
    paid = billing.confirm_invoice(annual.invoices.get())  # 12000, no tax
    billing.record_payment(paid, method="upi", amount=Decimal("12000.00"), paid_on=TODAY)
    billing.record_payment(overdue, method="cash", amount=Decimal("357.64"), paid_on=TODAY)

    client = client_for(staff)
    summary = client.get(f"{API}/reports/summary").data
    assert summary["active_subscriptions"] == 2
    assert summary["mrr"] == "2998.00"
    assert summary["arr"] == "35976.00"
    assert summary["invoiced"] == "14357.64"
    assert summary["collected"] == "12357.64"
    assert summary["outstanding"] == "2000.00"
    assert summary["overdue"] == "2000.00"
    assert summary["overdue_count"] == 1

    ageing = client.get(f"{API}/reports/overdue-ageing").data
    assert [(row["label"], row["amount"]) for row in ageing][1] == ("31-60 days", "2000.00")

    filtered = client.get(f"{API}/reports/summary", {"plan": yearly.id}).data
    assert (filtered["active_subscriptions"], filtered["mrr"], filtered["collected"]) == (1, "1000.00", "12000.00")

    series = client.get(f"{API}/reports/revenue-series").data
    assert len(series) == 12
    assert series[-1]["collected"] == "12357.64"

    assert client.get(f"{API}/customers/{customer.id}/summary").data["outstanding"] == "2000.00"


def test_report_date_filters_and_bad_dates(staff):
    client = client_for(staff)
    assert client.get(f"{API}/reports/summary", {"date_from": "2026-02-01", "date_to": "2026-01-01"}).status_code == 400
    assert client.get(f"{API}/reports/summary", {"date_from": "nonsense"}).status_code == 400


def test_lists_do_not_run_a_query_per_row(make_active, staff):
    """If this fails, pages get slower as the data grows, breaking the two-second requirement."""
    def count_queries(path):
        with CaptureQueriesContext(connection) as queries:
            assert client_for(staff).get(f"{API}/{path}").status_code == 200
        return len(queries)

    make_active(today=TODAY, start_date=TODAY)
    few = {path: count_queries(path) for path in ["subscriptions", "invoices", "customers", "payments"]}
    for _ in range(5):
        make_active(today=TODAY, start_date=TODAY)
    many = {path: count_queries(path) for path in few}
    assert many == few
