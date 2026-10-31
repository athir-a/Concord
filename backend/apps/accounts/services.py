from django.contrib.auth.tokens import default_token_generator
from django.db import IntegrityError, transaction
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from apps.common.email import send_password_reset
from apps.common.exceptions import DomainError

from .models import Customer, User


def _email_taken():
    return DomainError(
        "An account with this email already exists.",
        code="validation_error",
        status_code=400,
        fields={"email": "An account with this email already exists."},
    )


@transaction.atomic
def register_customer(*, name, email, password, company=""):
    """Create the login and the customer record together, or neither.

    A new account never attaches to an existing customer with the same email:
    email addresses aren't verified, so that would let anyone claim someone
    else's invoices by signing up with their address.
    """
    try:
        with transaction.atomic():
            user = User.objects.create_user(email, password, name=name, role=User.Role.CUSTOMER)
    except IntegrityError:
        raise _email_taken()
    Customer.objects.create(user=user, name=name, company=company, email=user.email)
    return user


def create_staff(*, name, email, password):
    try:
        with transaction.atomic():
            return User.objects.create_user(email, password, name=name, role=User.Role.STAFF)
    except IntegrityError:
        raise _email_taken()


def request_password_reset(email):
    """Send a reset link if the account exists. Callers answer the same either way."""
    user = User.objects.filter(email=email.strip().lower(), is_active=True).first()
    if user is None:
        return
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    send_password_reset(user, uid, default_token_generator.make_token(user))


def find_user_for_reset(uid, token):
    """Tokens hash the current password, so a used token stops working by itself."""
    invalid = DomainError(
        "This reset link is invalid or has expired. Please request a new one.",
        code="invalid_token",
        status_code=400,
    )
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uid)), is_active=True)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        raise invalid
    if not default_token_generator.check_token(user, token):
        raise invalid
    return user
