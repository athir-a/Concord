from django.contrib import admin

from .models import Subscription, SubscriptionEvent, SubscriptionLine


class SubscriptionLineInline(admin.TabularInline):
    model = SubscriptionLine
    extra = 0
    raw_id_fields = ["product", "variant"]


class SubscriptionEventInline(admin.TabularInline):
    model = SubscriptionEvent
    extra = 0
    can_delete = False
    readonly_fields = ["from_status", "to_status", "actor", "note", "created_at"]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    # Status and billing fields are read-only here, so the admin can't bypass the rules.
    list_display = ["number", "customer", "plan", "status", "start_date", "expiry_date", "next_billing_date"]
    list_filter = ["status", "plan"]
    search_fields = ["number", "customer__name"]
    raw_id_fields = ["customer"]
    readonly_fields = ["status", "billing_anchor", "periods_billed", "next_billing_date", "recurring_subtotal", "closed_at"]
    inlines = [SubscriptionLineInline, SubscriptionEventInline]
