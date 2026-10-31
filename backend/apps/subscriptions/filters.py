import django_filters

from .models import Subscription


class SubscriptionFilter(django_filters.FilterSet):
    # Powers the "renewals due" list, so nobody has to remember them.
    expires_by = django_filters.DateFilter(field_name="expiry_date", lookup_expr="lte")

    class Meta:
        model = Subscription
        fields = ["status", "customer", "plan"]
