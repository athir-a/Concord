import django_filters
from django.utils import timezone

from .models import Invoice, Payment


class InvoiceFilter(django_filters.FilterSet):
    overdue = django_filters.BooleanFilter(method="filter_overdue")
    issued_from = django_filters.DateFilter(field_name="issue_date", lookup_expr="gte")
    issued_to = django_filters.DateFilter(field_name="issue_date", lookup_expr="lte")

    class Meta:
        model = Invoice
        fields = ["status", "customer", "subscription", "billing_run"]

    def filter_overdue(self, queryset, name, value):
        overdue = {"status": Invoice.Status.CONFIRMED, "due_date__lt": timezone.localdate()}
        return queryset.filter(**overdue) if value else queryset.exclude(**overdue)


class PaymentFilter(django_filters.FilterSet):
    paid_from = django_filters.DateFilter(field_name="paid_on", lookup_expr="gte")
    paid_to = django_filters.DateFilter(field_name="paid_on", lookup_expr="lte")

    class Meta:
        model = Payment
        fields = ["method", "invoice"]
