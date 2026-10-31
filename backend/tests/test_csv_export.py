import csv
from datetime import timedelta
import io

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Customer, User
from apps.billing import services as billing
from apps.billing.models import Invoice

pytestmark = pytest.mark.django_db
URL = "/api/v1/reports/invoices.csv"


def parse_csv(response):
    content = b"".join(response.streaming_content).decode("utf-8")
    return list(csv.reader(io.StringIO(content)))


def test_anonymous_and_customer_permissions(staff):
    client = APIClient()

    # Anonymous user gets 401
    response = client.get(URL)
    assert response.status_code == 401

    # Customer user gets 403
    customer_user = User.objects.create_user("customer@concord.test", "Pass!1234", role="customer")
    client.force_authenticate(customer_user)
    response = client.get(URL)
    assert response.status_code == 403

    # Staff user gets 200
    client.force_authenticate(staff)
    response = client.get(URL)
    assert response.status_code == 200


def test_staff_gets_right_columns_and_values(staff, make_active):
    sub = make_active()
    invoice = sub.invoices.first()

    client = APIClient()
    client.force_authenticate(staff)

    response = client.get(URL)
    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv"
    assert response["Content-Disposition"] == 'attachment; filename="concord-invoices.csv"'

    rows = parse_csv(response)
    expected_columns = [
        "number",
        "customer_name",
        "status",
        "issue_date",
        "due_date",
        "period_start",
        "period_end",
        "currency",
        "subtotal",
        "discount_total",
        "tax_total",
        "total",
        "amount_paid",
        "amount_due",
        "is_overdue",
    ]
    assert rows[0] == expected_columns

    data_row = rows[1]
    assert data_row[0] == invoice.number
    assert data_row[1] == invoice.customer_name
    assert data_row[2] == invoice.status
    assert data_row[3] == str(invoice.issue_date)
    assert data_row[4] == str(invoice.due_date)
    assert data_row[5] == str(invoice.period_start)
    assert data_row[6] == str(invoice.period_end)
    assert data_row[7] == invoice.currency
    assert data_row[8] == str(invoice.subtotal)
    assert data_row[9] == str(invoice.discount_total)
    assert data_row[10] == str(invoice.tax_total)
    assert data_row[11] == str(invoice.total)
    assert data_row[12] == str(invoice.amount_paid)
    assert data_row[13] == str(invoice.amount_due)
    assert data_row[14] == str(invoice.is_overdue)


def test_status_and_overdue_filters(staff, make_active):
    client = APIClient()
    client.force_authenticate(staff)

    today = timezone.localdate()

    # Create 3 invoices with different statuses and overdue states
    # 1. Draft invoice
    sub1 = make_active(today=today)
    draft_invoice = sub1.invoices.first()

    # 2. Confirmed invoice (not overdue, due in 10 days)
    sub2 = make_active(today=today)
    confirmed_invoice = sub2.invoices.first()
    confirmed_invoice = billing.confirm_invoice(confirmed_invoice)
    confirmed_invoice.due_date = today + timedelta(days=10)
    confirmed_invoice.save(update_fields=["due_date"])

    # 3. Overdue confirmed invoice (due 5 days ago)
    sub3 = make_active(today=today)
    overdue_invoice = sub3.invoices.first()
    overdue_invoice = billing.confirm_invoice(overdue_invoice)
    overdue_invoice.due_date = today - timedelta(days=5)
    overdue_invoice.save(update_fields=["due_date"])

    # Filter by status=draft
    resp = client.get(f"{URL}?status=draft")
    numbers = [row[0] for row in parse_csv(resp)[1:]]
    assert draft_invoice.number in numbers
    assert confirmed_invoice.number not in numbers
    assert overdue_invoice.number not in numbers

    # Filter by status=confirmed
    resp = client.get(f"{URL}?status=confirmed")
    numbers = [row[0] for row in parse_csv(resp)[1:]]
    assert draft_invoice.number not in numbers
    assert confirmed_invoice.number in numbers
    assert overdue_invoice.number in numbers

    # Filter by overdue=true
    resp = client.get(f"{URL}?overdue=true")
    numbers = [row[0] for row in parse_csv(resp)[1:]]
    assert overdue_invoice.number in numbers
    assert confirmed_invoice.number not in numbers
    assert draft_invoice.number not in numbers

    # Filter by overdue=false
    resp = client.get(f"{URL}?overdue=false")
    numbers = [row[0] for row in parse_csv(resp)[1:]]
    assert overdue_invoice.number not in numbers
    assert confirmed_invoice.number in numbers
    assert draft_invoice.number in numbers


def test_invalid_filter_returns_400(staff):
    client = APIClient()
    client.force_authenticate(staff)

    # Invalid status
    response = client.get(f"{URL}?status=unknown_status")
    assert response.status_code == 400
    assert response.data["code"] == "validation_error"
    assert "detail" in response.data
    assert "status" in response.data["fields"]

    # Invalid date
    response = client.get(f"{URL}?issued_from=not-a-date")
    assert response.status_code == 400
    assert response.data["code"] == "validation_error"
    assert "issued_from" in response.data["fields"]


def test_formula_injection_escaped(staff, make_active):
    client = APIClient()
    client.force_authenticate(staff)

    # Formula injection attempts in customer name
    cust_formula = Customer.objects.create(name="=SUM(A1:B1)", email="formula@example.com")
    sub_formula = make_active(customer=cust_formula)
    inv_formula = sub_formula.invoices.first()

    cust_plus = Customer.objects.create(name="+123456", email="plus@example.com")
    sub_plus = make_active(customer=cust_plus)
    inv_plus = sub_plus.invoices.first()

    cust_minus = Customer.objects.create(name="-5000", email="minus@example.com")
    sub_minus = make_active(customer=cust_minus)
    inv_minus = sub_minus.invoices.first()

    cust_at = Customer.objects.create(name="@cmd", email="at@example.com")
    sub_at = make_active(customer=cust_at)
    inv_at = sub_at.invoices.first()

    resp = client.get(f"{URL}?customer={cust_formula.id}")
    rows = parse_csv(resp)
    assert rows[1][0] == inv_formula.number
    assert rows[1][1] == "'=SUM(A1:B1)"

    resp = client.get(f"{URL}?customer={cust_plus.id}")
    rows = parse_csv(resp)
    assert rows[1][1] == "'+123456"

    resp = client.get(f"{URL}?customer={cust_minus.id}")
    rows = parse_csv(resp)
    assert rows[1][1] == "'-5000"

    resp = client.get(f"{URL}?customer={cust_at.id}")
    rows = parse_csv(resp)
    assert rows[1][1] == "'@cmd"
