from .models import Subscription


def subscriptions_visible_to(user):
    """The one rule for who sees what. A customer only gets their own, and never drafts.

    Other customers' records simply aren't in the queryset, so asking for one is a 404
    that doesn't even reveal whether it exists.
    """
    queryset = Subscription.objects.select_related("customer", "plan", "discount")
    if user.role == user.Role.CUSTOMER:
        return queryset.filter(customer__user=user).exclude(status=Subscription.Status.DRAFT)
    return queryset
