from .models import Invoice, Payment


def invoices_visible_to(user):
    """A customer only gets their own, and never drafts the team hasn't confirmed yet."""
    queryset = Invoice.objects.all()
    if user.role == user.Role.CUSTOMER:
        return queryset.filter(customer__user=user).exclude(status=Invoice.Status.DRAFT)
    return queryset


def payments_visible_to(user):
    queryset = Payment.objects.select_related("invoice", "recorded_by")
    if user.role == user.Role.CUSTOMER:
        return queryset.filter(invoice__customer__user=user)
    return queryset
