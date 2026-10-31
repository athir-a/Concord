from rest_framework import viewsets

from apps.common.permissions import IsAdminOrTeamReadOnly

from .models import DiscountRule, Plan, Product, QuotationTemplate, TaxRule
from .serializers import (
    DiscountRuleSerializer,
    PlanSerializer,
    ProductSerializer,
    QuotationTemplateSerializer,
    TaxRuleSerializer,
)


class CatalogViewSet(viewsets.ModelViewSet):
    """The admin changes the catalog, staff read it, and customers can't reach it."""

    permission_classes = [IsAdminOrTeamReadOnly]


class TaxRuleViewSet(CatalogViewSet):
    serializer_class = TaxRuleSerializer
    queryset = TaxRule.objects.all()
    filterset_fields = ["is_active"]
    search_fields = ["name"]


class ProductViewSet(CatalogViewSet):
    serializer_class = ProductSerializer
    queryset = Product.objects.select_related("tax_rule").prefetch_related("variants")
    filterset_fields = ["type", "is_active"]
    search_fields = ["name"]
    ordering_fields = ["name", "sales_price"]


class PlanViewSet(CatalogViewSet):
    serializer_class = PlanSerializer
    queryset = Plan.objects.all()
    filterset_fields = ["interval", "is_active"]
    search_fields = ["name"]
    ordering_fields = ["name", "price"]


class DiscountRuleViewSet(CatalogViewSet):
    serializer_class = DiscountRuleSerializer
    queryset = DiscountRule.objects.prefetch_related("products")
    filterset_fields = ["kind", "scope", "is_active"]
    search_fields = ["name"]


class QuotationTemplateViewSet(CatalogViewSet):
    serializer_class = QuotationTemplateSerializer
    queryset = QuotationTemplate.objects.select_related("plan").prefetch_related("lines__product", "lines__variant")
    search_fields = ["name"]
