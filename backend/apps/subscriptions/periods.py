"""Billing period arithmetic. Pure functions, with no database access."""
from dateutil.relativedelta import relativedelta

_STEP = {
    "daily": lambda n: relativedelta(days=n),
    "weekly": lambda n: relativedelta(weeks=n),
    "monthly": lambda n: relativedelta(months=n),
    "yearly": lambda n: relativedelta(years=n),
}


def add_periods(anchor, interval, count):
    """Always count from the anchor, never from the previous date.

    Jan 31 + 1 month is Feb 28. Adding another month to Feb 28 would give Mar 28 and
    the customer's billing day would drift forever. Jan 31 + 2 months is Mar 31.
    """
    return anchor + _STEP[interval](count)


def period_bounds(anchor, interval, index):
    """Start and end of the period with this index. The end is the next period's start."""
    return add_periods(anchor, interval, index), add_periods(anchor, interval, index + 1)
