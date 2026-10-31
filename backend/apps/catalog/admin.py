from django.contrib import admin

from .models import DiscountRule, Plan, Product, ProductVariant, QuotationTemplate, TaxRule, TemplateLine


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0


class TemplateLineInline(admin.TabularInline):
    model = TemplateLine
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "type", "sales_price", "cost_price", "tax_rule", "is_active"]
    list_filter = ["type", "is_active"]
    search_fields = ["name"]
    inlines = [ProductVariantInline]


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ["name", "price", "interval", "min_quantity", "auto_close", "closable", "pausable", "renewable", "is_active"]
    list_filter = ["interval", "is_active"]
    search_fields = ["name"]


@admin.register(TaxRule)
class TaxRuleAdmin(admin.ModelAdmin):
    list_display = ["name", "rate_percent", "is_active"]


@admin.register(DiscountRule)
class DiscountRuleAdmin(admin.ModelAdmin):
    list_display = ["name", "kind", "value", "scope", "starts_on", "ends_on", "times_used", "usage_limit", "is_active"]
    list_filter = ["kind", "scope", "is_active"]
    readonly_fields = ["times_used"]


@admin.register(QuotationTemplate)
class QuotationTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "plan", "validity_days"]
    inlines = [TemplateLineInline]
