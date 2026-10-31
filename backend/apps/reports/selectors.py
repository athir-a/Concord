"""Finance numbers, all calculated by the database from real records.

Invoiced is what we asked for, collected is what arrived, outstanding is the gap, and
MRR is a run rate. None of them is profit. See docs/metrics.md for the definitions.
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, F, Q, Sum
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone

from apps.billing.models import Invoice, Payment
from apps.common.money import round_money
from apps.subscriptions.models import Subscription
from apps.subscriptions.periods import add_periods

ZERO = Decimal("0.00")
MONTHLY_FACTOR = {
    "daily": Decimal(365) / 12,
    "weekly": Decimal(52) / 12,
    "monthly": Decimal(1),
    "yearly": Decimal(1) / 12,
}
LIVE_INVOICE = [Invoice.Status.CONFIRMED, Invoice.Status.PAID]
RENEWAL_WINDOW_DAYS = 30


def _subscriptions(filters):
    queryset = Subscription.objects.all()
    if filters.get("plan"):
        queryset = queryset.filter(plan=filters["plan"])
    if filters.get("customer"):
        queryset = queryset.filter(customer=filters["customer"])
    return queryset


def _invoices(filters):
    queryset = Invoice.objects.all()
    if filters.get("plan"):
        queryset = queryset.filter(subscription__plan=filters["plan"])
    if filters.get("customer"):
        queryset = queryset.filter(customer=filters["customer"])
    return queryset


def _payments(filters):
    queryset = Payment.objects.all()
    if filters.get("plan"):
        queryset = queryset.filter(invoice__subscription__plan=filters["plan"])
    if filters.get("customer"):
        queryset = queryset.filter(invoice__customer=filters["customer"])
    return queryset


def _in_range(queryset, field, filters):
    if filters.get("date_from"):
        queryset = queryset.filter(**{f"{field}__gte": filters["date_from"]})
    if filters.get("date_to"):
        queryset = queryset.filter(**{f"{field}__lte": filters["date_to"]})
    return queryset


def _monthly_recurring(filters):
    """Active subscriptions normalised to a month. Excludes tax and is before discounts."""
    by_interval = (
        _subscriptions(filters)
        .filter(status=Subscription.Status.ACTIVE)
        .values("plan__interval")
        .annotate(amount=Sum("recurring_subtotal"))
    )
    return round_money(sum((row["amount"] * MONTHLY_FACTOR[row["plan__interval"]] for row in by_interval), ZERO))


def _sum(queryset, expression):
    return queryset.aggregate(value=Coalesce(Sum(expression), ZERO))["value"]


def _balance_due():
    return F("total") - F("amount_paid")


def summary(filters, today=None):
    """Dates narrow invoiced and collected. The rest describe the position as it is today."""
    today = today or timezone.localdate()
    subscriptions = _subscriptions(filters)
    counts = subscriptions.aggregate(
        active=Count("id", filter=Q(status=Subscription.Status.ACTIVE)),
        paused=Count("id", filter=Q(status=Subscription.Status.PAUSED)),
        quotations=Count("id", filter=Q(status=Subscription.Status.QUOTATION)),
        confirmed=Count("id", filter=Q(status=Subscription.Status.CONFIRMED)),
        renewals_due=Count("id", filter=Q(
            status=Subscription.Status.ACTIVE,
            expiry_date__lte=today + timedelta(days=RENEWAL_WINDOW_DAYS),
        )),
    )
    invoices = _invoices(filters)
    unpaid = invoices.filter(status=Invoice.Status.CONFIRMED)
    overdue = unpaid.filter(due_date__lt=today)
    mrr = _monthly_recurring(filters)
    return {
        "active_subscriptions": counts["active"],
        "paused_subscriptions": counts["paused"],
        "quotations_awaiting_reply": counts["quotations"],
        "confirmed_awaiting_activation": counts["confirmed"],
        "renewals_due": counts["renewals_due"],
        "mrr": mrr,
        "arr": mrr * 12,
        "invoiced": _sum(_in_range(invoices.filter(status__in=LIVE_INVOICE), "issue_date", filters), "total"),
        "collected": _sum(_in_range(_payments(filters), "paid_on", filters), "amount"),
        "outstanding": _sum(unpaid, _balance_due()),
        "outstanding_count": unpaid.count(),
        "overdue": _sum(overdue, _balance_due()),
        "overdue_count": overdue.count(),
        "draft_invoices": invoices.filter(status=Invoice.Status.DRAFT).count(),
    }


def revenue_series(filters, months=12, today=None):
    """Invoiced and collected per month, with zeros for empty months so charts have no gaps."""
    today = today or timezone.localdate()
    this_month = today.replace(day=1)
    first = add_periods(this_month, "monthly", -(months - 1))

    def by_month(queryset, field, amount):
        rows = (
            queryset.filter(**{f"{field}__gte": first})
            .annotate(month=TruncMonth(field))
            .values("month")
            .annotate(value=Sum(amount))
        )
        return {row["month"]: row["value"] for row in rows}

    invoiced = by_month(_invoices(filters).filter(status__in=LIVE_INVOICE), "issue_date", "total")
    collected = by_month(_payments(filters), "paid_on", "amount")
    series = []
    for index in range(months):
        month = add_periods(first, "monthly", index)
        series.append({"month": month, "invoiced": invoiced.get(month, ZERO), "collected": collected.get(month, ZERO)})
    return series


def overdue_ageing(filters, today=None):
    """How late the money is. The older the bucket, the less likely it arrives."""
    today = today or timezone.localdate()
    overdue = _invoices(filters).filter(status=Invoice.Status.CONFIRMED, due_date__lt=today)
    buckets = [
        ("1-30 days", Q(due_date__gte=today - timedelta(days=30))),
        ("31-60 days", Q(due_date__lt=today - timedelta(days=30), due_date__gte=today - timedelta(days=60))),
        ("61+ days", Q(due_date__lt=today - timedelta(days=60))),
    ]
    result = []
    for label, condition in buckets:
        rows = overdue.filter(condition)
        result.append({"label": label, "count": rows.count(), "amount": _sum(rows, _balance_due())})
    return result


def customer_summary(customer, today=None):
    today = today or timezone.localdate()
    subscriptions = Subscription.objects.filter(customer=customer)
    invoices = Invoice.objects.filter(customer=customer)
    unpaid = invoices.filter(status=Invoice.Status.CONFIRMED)
    return {
        "active_subscriptions": subscriptions.filter(status=Subscription.Status.ACTIVE).count(),
        "total_subscriptions": subscriptions.count(),
        "invoiced": _sum(invoices.filter(status__in=LIVE_INVOICE), "total"),
        "collected": _sum(Payment.objects.filter(invoice__customer=customer), "amount"),
        "outstanding": _sum(unpaid, _balance_due()),
        "overdue": _sum(unpaid.filter(due_date__lt=today), _balance_due()),
    }
