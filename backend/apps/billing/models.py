from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from apps.accounts.models import Customer
from apps.common.models import TimeStampedModel
from apps.common.money import money_field
from apps.subscriptions.models import Subscription


class BillingRun(models.Model):
    """A record of one billing run, so anyone can see what it created, skipped or failed on."""

    as_of = models.DateField()
    triggered_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    errors = models.JSONField(default=list, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-id"]


class Invoice(TimeStampedModel):
    """A snapshot of a subscription for one billing period.

    Names, prices and tax rates are copied here, so later catalog changes can't rewrite it.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        CONFIRMED = "confirmed", "Confirmed"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    number = models.CharField(max_length=24, unique=True)
    subscription = models.ForeignKey(Subscription, on_delete=models.PROTECT, related_name="invoices")
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="invoices")
    billing_run = models.ForeignKey(BillingRun, null=True, blank=True, on_delete=models.SET_NULL, related_name="invoices")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT, editable=False)
    period_start = models.DateField()
    period_end = models.DateField()
    issue_date = models.DateField()
    due_date = models.DateField()
    currency = models.CharField(max_length=3, default="INR")
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()
    customer_address = models.TextField(blank=True)
    subtotal = money_field(default=0)
    discount_total = money_field(default=0)
    tax_total = money_field(default=0)
    total = money_field(default=0)
    # Stored so list pages don't add up payments on every row. Only record_payment changes it.
    amount_paid = money_field(default=0, editable=False)
    # Which rule was used, so that cancelling this invoice can give the use back.
    discount_rule = models.ForeignKey(
        "catalog.DiscountRule", null=True, blank=True, on_delete=models.SET_NULL, related_name="invoices"
    )
    confirmed_at = models.DateTimeField(null=True, blank=True, editable=False)
    sent_at = models.DateTimeField(null=True, blank=True, editable=False)
    cancelled_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["status", "due_date"], name="invoice_status_due_idx"),
            models.Index(fields=["customer", "status"], name="invoice_customer_status_idx"),
            models.Index(fields=["issue_date"], name="invoice_issue_date_idx"),
        ]
        constraints = [
            # The guarantee against double billing: however the code behaves, the database
            # refuses a second live invoice for the same subscription and period.
            # Cancelled invoices don't count, so a period can be correctly reissued.
            models.UniqueConstraint(
                fields=["subscription", "period_start"],
                condition=~Q(status="cancelled"),
                name="invoice_one_live_per_period",
            ),
            models.CheckConstraint(condition=Q(period_end__gt=F("period_start")), name="invoice_period_ordered"),
            models.CheckConstraint(condition=Q(total__gte=0), name="invoice_total_not_negative"),
            models.CheckConstraint(
                condition=Q(amount_paid__gte=0, amount_paid__lte=F("total")), name="invoice_paid_within_total"
            ),
        ]

    def __str__(self):
        return self.number

    @property
    def amount_due(self):
        return self.total - self.amount_paid

    @property
    def is_overdue(self):
        """Worked out each time rather than stored, so it can never go stale."""
        return self.status == self.Status.CONFIRMED and self.due_date < timezone.localdate()


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField()
    unit_price = money_field()
    discount_amount = money_field(default=0)
    tax_name = models.CharField(max_length=100, blank=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = money_field(default=0)
    line_total = money_field()

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.description


class Payment(TimeStampedModel):
    class Method(models.TextChoices):
        BANK_TRANSFER = "bank_transfer", "Bank transfer"
        UPI = "upi", "UPI"
        CARD = "card", "Card"
        CASH = "cash", "Cash"
        CHEQUE = "cheque", "Cheque"
        OTHER = "other", "Other"

    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="payments")
    method = models.CharField(max_length=15, choices=Method.choices)
    amount = money_field()
    paid_on = models.DateField()
    note = models.CharField(max_length=255, blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    # Sent by the form, so a double-click or a retry can't record the same payment twice.
    idempotency_key = models.CharField(max_length=64, null=True, blank=True, unique=True)

    class Meta:
        ordering = ["-paid_on", "-id"]
        indexes = [models.Index(fields=["paid_on"], name="payment_paid_on_idx")]
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="payment_amount_positive"),
        ]
