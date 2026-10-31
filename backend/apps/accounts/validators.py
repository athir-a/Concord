import re

from django.core.exceptions import ValidationError


class PasswordComplexityValidator:
    """Requires an uppercase letter, a lowercase letter and a special character."""

    def validate(self, password, user=None):
        if not re.search(r"[A-Z]", password):
            raise ValidationError("Password must contain an uppercase letter.", code="password_no_upper")
        if not re.search(r"[a-z]", password):
            raise ValidationError("Password must contain a lowercase letter.", code="password_no_lower")
        if not re.search(r"[^A-Za-z0-9\s]", password):
            raise ValidationError("Password must contain a special character.", code="password_no_special")

    def get_help_text(self):
        return "Your password must contain an uppercase letter, a lowercase letter and a special character."
