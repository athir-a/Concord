from django.conf import settings
from django.db import models
from django.db.models import F, Q

from apps.accounts.models import Customer
from apps.catalog.models import DiscountRule, Plan, Product, ProductVariant
from apps.common.models import TimeStampedModel
from apps.common.money import money_field


class Subscription(TimeStampedModel):
    """A customer's order, from first draft to closure. A quotation is one stage of this, not a separate record."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        QUOTATION = "quotation", "Quotation"
        CONFIRMED = "confirmed", "Confirmed"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        CLOSED = "closed", "Closed"

    number = models.CharField(max_length=20, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="subscriptions")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    discount = models.ForeignKey(
        DiscountRule, null=True, blank=True, on_delete=models.PROTECT, related_name="subscriptions"
    )
    # Only services change this, through named actions, so the rules can't be bypassed.
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT, editable=False)
    start_date = models.DateField()
    expiry_date = models.DateField()
    payment_terms_days = models.PositiveIntegerField(default=30)
    quote_valid_until = models.DateField(null=True, blank=True)
    # Billing periods are calculated from the anchor, so Jan 31 gives Feb 28 and then Mar 31.
    billing_anchor = models.DateField(null=True, blank=True, editable=False)
    periods_billed = models.PositiveIntegerField(default=0, editable=False)
    next_billing_date = models.DateField(null=True, blank=True, editable=False)
    # Stored so reports don't add up every line of thousands of subscriptions.
    recurring_subtotal = money_field(default=0, editable=False)
    closed_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["status", "next_billing_date"], name="sub_due_for_billing_idx"),
            models.Index(fields=["customer", "status"], name="sub_customer_status_idx"),
            models.Index(fields=["status", "expiry_date"], name="sub_status_expiry_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(expiry_date__gt=F("start_date")), name="sub_expiry_after_start"),
        ]

    def __str__(self):
        return self.number


class SubscriptionLine(models.Model):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="lines")
    # Empty for the plan fee line, which has no product.
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    variant = models.ForeignKey(ProductVariant, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = money_field()

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gte=1), name="sub_line_quantity_at_least_1"),
            models.CheckConstraint(condition=Q(unit_price__gte=0), name="sub_line_price_not_negative"),
        ]

    def __str__(self):
        return self.description


class SubscriptionEvent(models.Model):
    """History of every status change: who, when and from what to what."""

    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="events")
    from_status = models.CharField(max_length=10, blank=True)
    to_status = models.CharField(max_length=10)
    # Empty when the system acted, such as closing a subscription at expiry.
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["subscription", "created_at"], name="sub_event_timeline_idx")]
