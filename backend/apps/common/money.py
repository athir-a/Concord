from decimal import ROUND_HALF_UP, Decimal

from django.db import models

CENT = Decimal("0.01")


def money_field(**kwargs):
    """Every amount in the system. Decimal, because floats can't represent 0.10 exactly."""
    return models.DecimalField(max_digits=12, decimal_places=2, **kwargs)


def round_money(value):
    """The one place amounts are rounded, so every calculation agrees."""
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)
