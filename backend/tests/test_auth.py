import re

import pytest
from django.core import mail
from django.core.cache import cache
from django.db import IntegrityError, transaction
from rest_framework.test import APIClient

from apps.accounts.models import Customer, User

GOOD_PASSWORD = "Str0ng!pass"
pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_throttles():
    cache.clear()


@pytest.fixture
def client():
    return APIClient()


def signup(client, **overrides):
    payload = {"name": "Asha", "email": "asha@shop.in", "password": GOOD_PASSWORD} | overrides
    return client.post("/api/v1/auth/signup", payload, format="json")


def make_user(role, email=None):
    return User.objects.create_user(email or f"{role}@concord.test", GOOD_PASSWORD, role=role)


def test_signup_creates_customer_and_logs_in(client):
    response = signup(client, company="Asha Stores")
    assert response.status_code == 201
    assert response.data["role"] == "customer"
    customer = Customer.objects.get(user__email="asha@shop.in")
    assert customer.company == "Asha Stores"
    assert response.data["customer_id"] == customer.id
    assert client.get("/api/v1/auth/me").data["email"] == "asha@shop.in"


def test_signup_cannot_choose_a_role(client):
    response = signup(client, role="admin", is_staff=True, is_superuser=True)
    assert response.status_code == 201
    user = User.objects.get(email="asha@shop.in")
    assert (user.role, user.is_staff, user.is_superuser) == ("customer", False, False)


@pytest.mark.parametrize("password, reason", [
    ("Sh0rt!pas", None),  # exactly nine characters is allowed
    ("Sh0rt!pa", "at least 9"),
    ("nouppercase1!", "uppercase"),
    ("NOLOWERCASE1!", "lowercase"),
    ("NoSpecial123", "special"),
])
def test_password_rules(client, password, reason):
    response = signup(client, password=password)
    if reason is None:
        assert response.status_code == 201
    else:
        assert response.status_code == 400
        assert reason in response.data["fields"]["password"]


def test_email_is_unique_ignoring_case(client):
    assert signup(client).status_code == 201
    client = APIClient()
    response = signup(client, email="ASHA@Shop.IN")
    assert response.status_code == 400
    assert "email" in response.data["fields"]
    assert User.objects.count() == 1


def test_database_rejects_mixed_case_email():
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.bulk_create([User(email="Mixed@Case.com")])


def test_login_is_case_insensitive_and_logout_ends_session(client):
    make_user("staff", "sam@concord.test")
    response = client.post(
        "/api/v1/auth/login", {"email": "SAM@concord.test", "password": GOOD_PASSWORD}, format="json"
    )
    assert response.status_code == 200
    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401


def test_bad_login_has_a_generic_message(client):
    make_user("staff", "sam@concord.test")
    wrong_password = client.post(
        "/api/v1/auth/login", {"email": "sam@concord.test", "password": "nope"}, format="json"
    )
    no_account = client.post(
        "/api/v1/auth/login", {"email": "ghost@concord.test", "password": "nope"}, format="json"
    )
    assert wrong_password.status_code == no_account.status_code == 400
    assert wrong_password.data == no_account.data


def test_login_is_throttled(client):
    responses = [
        client.post("/api/v1/auth/login", {"email": "a@b.co", "password": "x"}, format="json").status_code
        for _ in range(11)
    ]
    assert responses[-1] == 429


def test_login_requires_csrf_token():
    client = APIClient(enforce_csrf_checks=True)
    make_user("staff", "sam@concord.test")
    payload = {"email": "sam@concord.test", "password": GOOD_PASSWORD}
    assert client.post("/api/v1/auth/login", payload, format="json").status_code == 403

    client.get("/api/v1/auth/csrf")
    token = client.cookies["csrftoken"].value
    response = client.post("/api/v1/auth/login", payload, format="json", HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 200


def reset_link_parts():
    match = re.search(r"/reset-password/([^/\s]+)/([^/\s]+)", mail.outbox[-1].body)
    return match.group(1), match.group(2)


def test_password_reset_works_once(client):
    make_user("customer", "asha@shop.in")
    assert client.post("/api/v1/auth/password-reset", {"email": "asha@shop.in"}, format="json").status_code == 200
    assert mail.outbox[-1].to == ["asha@shop.in"]
    uid, token = reset_link_parts()

    new = {"uid": uid, "token": token, "password": "N3w!password"}
    assert client.post("/api/v1/auth/password-reset/confirm", new, format="json").status_code == 200
    assert client.login(username="asha@shop.in", password="N3w!password")

    again = client.post("/api/v1/auth/password-reset/confirm", new, format="json")
    assert again.status_code == 400
    assert again.data["code"] == "invalid_token"


def test_password_reset_enforces_password_rules(client):
    make_user("customer", "asha@shop.in")
    client.post("/api/v1/auth/password-reset", {"email": "asha@shop.in"}, format="json")
    uid, token = reset_link_parts()
    response = client.post(
        "/api/v1/auth/password-reset/confirm", {"uid": uid, "token": token, "password": "weak"}, format="json"
    )
    assert response.status_code == 400
    assert "password" in response.data["fields"]


def test_password_reset_does_not_reveal_accounts(client):
    make_user("customer", "asha@shop.in")
    known = client.post("/api/v1/auth/password-reset", {"email": "asha@shop.in"}, format="json")
    unknown = client.post("/api/v1/auth/password-reset", {"email": "ghost@shop.in"}, format="json")
    assert known.status_code == unknown.status_code == 200
    assert known.data == unknown.data
    assert len(mail.outbox) == 1


STAFF_PAYLOAD = {"name": "Sam", "email": "sam@concord.test", "password": GOOD_PASSWORD}


def test_only_admin_can_add_staff(client):
    assert client.post("/api/v1/users/staff", STAFF_PAYLOAD, format="json").status_code == 401

    for role in ["staff", "customer"]:
        client.force_authenticate(make_user(role))
        assert client.post("/api/v1/users/staff", STAFF_PAYLOAD, format="json").status_code == 403
        assert client.get("/api/v1/users/staff").status_code == 403

    client.force_authenticate(make_user("admin"))
    response = client.post("/api/v1/users/staff", STAFF_PAYLOAD, format="json")
    assert response.status_code == 201
    assert response.data["role"] == "staff"
    assert "password" not in response.data


def test_errors_have_one_shape(client):
    response = client.post("/api/v1/auth/login", {"email": "not-an-email"}, format="json")
    assert set(response.data) == {"code", "detail", "fields"}
    assert response.data["code"] == "validation_error"
    assert set(response.data["fields"]) == {"email", "password"}
