from django.db import models
from django.db.models import F, Q

from apps.common.models import TimeStampedModel
from apps.common.money import money_field


class TaxRule(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    rate_percent = models.DecimalField(max_digits=5, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(rate_percent__gte=0, rate_percent__lte=100), name="tax_rate_0_to_100"
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.rate_percent}%)"


class Product(TimeStampedModel):
    class Type(models.TextChoices):
        SOFTWARE = "software", "Software"
        ADDON = "addon", "Add-on"
        SERVICE = "service", "Service"

    name = models.CharField(max_length=200)
    type = models.CharField(max_length=10, choices=Type.choices, default=Type.SOFTWARE)
    sales_price = money_field()
    cost_price = money_field(default=0)
    notes = models.TextField(blank=True)
    tax_rule = models.ForeignKey(TaxRule, null=True, blank=True, on_delete=models.PROTECT, related_name="products")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.CheckConstraint(condition=Q(sales_price__gte=0, cost_price__gte=0), name="product_prices_not_negative"),
        ]

    def __str__(self):
        return self.name


class ProductVariant(TimeStampedModel):
    """For example attribute "Brand", value "Odoo", which adds 560 to the price."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    attribute = models.CharField(max_length=60)
    value = models.CharField(max_length=60)
    extra_price = money_field(default=0)

    class Meta:
        ordering = ["attribute", "value"]
        constraints = [
            models.UniqueConstraint(fields=["product", "attribute", "value"], name="variant_unique_per_product"),
        ]

    def __str__(self):
        return f"{self.attribute}: {self.value}"


class Plan(TimeStampedModel):
    class Interval(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"
        YEARLY = "yearly", "Yearly"

    name = models.CharField(max_length=200)
    price = money_field(default=0)
    interval = models.CharField(max_length=10, choices=Interval.choices, default=Interval.MONTHLY)
    min_quantity = models.PositiveIntegerField(default=1)
    available_from = models.DateField(null=True, blank=True)
    available_to = models.DateField(null=True, blank=True)
    # How many billing periods a new term lasts. Sets the default expiry and each renewal.
    term_periods = models.PositiveIntegerField(default=12)
    # The admin decides these plan by plan.
    auto_close = models.BooleanField(default=False)
    closable = models.BooleanField(default=True)
    pausable = models.BooleanField(default=True)
    renewable = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.CheckConstraint(condition=Q(price__gte=0), name="plan_price_not_negative"),
            models.CheckConstraint(condition=Q(min_quantity__gte=1), name="plan_min_quantity_at_least_1"),
            models.CheckConstraint(condition=Q(term_periods__gte=1), name="plan_term_at_least_1"),
            models.CheckConstraint(
                condition=Q(available_from__isnull=True)
                | Q(available_to__isnull=True)
                | Q(available_to__gte=F("available_from")),
                name="plan_availability_ordered",
            ),
        ]

    def __str__(self):
        return self.name


class DiscountRule(TimeStampedModel):
    class Kind(models.TextChoices):
        FIXED = "fixed", "Fixed amount"
        PERCENT = "percent", "Percentage"

    class Scope(models.TextChoices):
        SUBSCRIPTION = "subscription", "Whole subscription"
        PRODUCTS = "products", "Specific products"

    name = models.CharField(max_length=200)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    value = money_field()
    min_amount = money_field(default=0)
    min_quantity = models.PositiveIntegerField(default=0)
    starts_on = models.DateField()
    ends_on = models.DateField(null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    times_used = models.PositiveIntegerField(default=0, editable=False)
    scope = models.CharField(max_length=15, choices=Scope.choices, default=Scope.SUBSCRIPTION)
    products = models.ManyToManyField(Product, blank=True, related_name="discount_rules")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-starts_on", "id"]
        constraints = [
            models.CheckConstraint(condition=Q(value__gt=0), name="discount_value_positive"),
            models.CheckConstraint(condition=~Q(kind="percent") | Q(value__lte=100), name="discount_percent_at_most_100"),
            models.CheckConstraint(
                condition=Q(ends_on__isnull=True) | Q(ends_on__gte=F("starts_on")), name="discount_dates_ordered"
            ),
            # The database itself refuses to go past the limit.
            models.CheckConstraint(
                condition=Q(usage_limit__isnull=True) | Q(times_used__lte=F("usage_limit")),
                name="discount_within_usage_limit",
            ),
        ]

    def __str__(self):
        return self.name


class QuotationTemplate(TimeStampedModel):
    name = models.CharField(max_length=200)
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="templates")
    validity_days = models.PositiveIntegerField(default=30)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class TemplateLine(models.Model):
    template = models.ForeignKey(QuotationTemplate, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="+")
    variant = models.ForeignKey(ProductVariant, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gte=1), name="template_line_quantity_at_least_1"),
        ]
