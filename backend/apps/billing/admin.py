from django.contrib import admin

from .models import BillingRun, Invoice, InvoiceLine, Payment


class ReadOnlyAdmin(admin.ModelAdmin):
    """Money records are for viewing here. They only change through the billing services."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Invoice)
class InvoiceAdmin(ReadOnlyAdmin):
    list_display = ["number", "customer_name", "status", "period_start", "period_end", "due_date", "total", "amount_paid"]
    list_filter = ["status"]
    search_fields = ["number", "customer_name"]
    inlines = [InvoiceLineInline]


@admin.register(Payment)
class PaymentAdmin(ReadOnlyAdmin):
    list_display = ["invoice", "method", "amount", "paid_on", "recorded_by"]
    list_filter = ["method"]


@admin.register(BillingRun)
class BillingRunAdmin(ReadOnlyAdmin):
    list_display = ["id", "as_of", "created_count", "skipped_count", "failed_count", "started_at", "finished_at"]
