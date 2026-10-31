from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from .models import DiscountRule, Plan, Product, ProductVariant, QuotationTemplate, TaxRule, TemplateLine


class TaxRuleSerializer(serializers.ModelSerializer):
    rate_percent = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0, max_value=100)

    class Meta:
        model = TaxRule
        fields = ["id", "name", "rate_percent", "is_active"]


class ProductVariantSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    extra_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, default=0)

    class Meta:
        model = ProductVariant
        fields = ["id", "attribute", "value", "extra_price"]
        validators = []  # Duplicates within the list are checked by the parent.


class ProductSerializer(serializers.ModelSerializer):
    variants = ProductVariantSerializer(many=True, required=False)
    sales_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    cost_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, default=0)
    tax_rule_name = serializers.CharField(source="tax_rule.name", read_only=True, default=None)

    class Meta:
        model = Product
        fields = [
            "id", "name", "type", "sales_price", "cost_price", "notes", "tax_rule", "tax_rule_name",
            "is_active", "variants",
        ]

    def validate_variants(self, variants):
        keys = [(v["attribute"].strip().lower(), v["value"].strip().lower()) for v in variants]
        if len(keys) != len(set(keys)):
            raise serializers.ValidationError("Each variant must be different.")
        return variants

    def _save_variants(self, product, variants):
        """Match by attribute and value, so a variant in use keeps its identity."""
        kept = []
        for variant in variants:
            saved, _ = ProductVariant.objects.update_or_create(
                product=product, attribute=variant["attribute"], value=variant["value"],
                defaults={"extra_price": variant["extra_price"]},
            )
            kept.append(saved.pk)
        product.variants.exclude(pk__in=kept).delete()

    @transaction.atomic
    def create(self, validated_data):
        variants = validated_data.pop("variants", [])
        product = super().create(validated_data)
        self._save_variants(product, variants)
        return product

    @transaction.atomic
    def update(self, instance, validated_data):
        variants = validated_data.pop("variants", None)
        product = super().update(instance, validated_data)
        if variants is not None:
            self._save_variants(product, variants)
        return product


class PlanSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, default=0)
    min_quantity = serializers.IntegerField(min_value=1, default=1)
    term_periods = serializers.IntegerField(min_value=1, default=12)

    class Meta:
        model = Plan
        fields = [
            "id", "name", "price", "interval", "min_quantity", "available_from", "available_to", "term_periods",
            "tax_rule", "auto_close", "closable", "pausable", "renewable", "is_active",
        ]

    def validate(self, attrs):
        start = attrs.get("available_from", getattr(self.instance, "available_from", None))
        end = attrs.get("available_to", getattr(self.instance, "available_to", None))
        if start and end and end < start:
            raise serializers.ValidationError({"available_to": "This must be on or after the start date."})
        return attrs


class DiscountRuleSerializer(serializers.ModelSerializer):
    value = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    min_amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, default=0)
    usage_limit = serializers.IntegerField(min_value=1, required=False, allow_null=True)

    class Meta:
        model = DiscountRule
        fields = [
            "id", "name", "kind", "value", "min_amount", "min_quantity", "starts_on", "ends_on",
            "usage_limit", "times_used", "scope", "products", "is_active",
        ]
        read_only_fields = ["times_used"]
        extra_kwargs = {"products": {"required": False}}

    def validate(self, attrs):
        def current(name, default=None):
            return attrs.get(name, getattr(self.instance, name, default))

        if current("kind") == DiscountRule.Kind.PERCENT and current("value") > 100:
            raise serializers.ValidationError({"value": "A percentage can't be more than 100."})
        if current("ends_on") and current("ends_on") < current("starts_on"):
            raise serializers.ValidationError({"ends_on": "This must be on or after the start date."})
        if current("usage_limit") is not None and self.instance and current("usage_limit") < self.instance.times_used:
            raise serializers.ValidationError({"usage_limit": f"It has already been used {self.instance.times_used} times."})
        if current("scope", DiscountRule.Scope.SUBSCRIPTION) == DiscountRule.Scope.PRODUCTS:
            products = attrs.get("products")
            if products is None and self.instance:
                has_products = self.instance.products.exists()
            else:
                has_products = bool(products)
            if not has_products:
                raise serializers.ValidationError({"products": "Choose at least one product."})
        return attrs


class TemplateLineSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    quantity = serializers.IntegerField(min_value=1, default=1)
    product_name = serializers.CharField(source="product.name", read_only=True)
    variant_label = serializers.CharField(source="variant.value", read_only=True, default=None)

    class Meta:
        model = TemplateLine
        fields = ["id", "product", "product_name", "variant", "variant_label", "quantity"]

    def validate(self, attrs):
        variant = attrs.get("variant")
        if variant and variant.product_id != attrs["product"].id:
            raise serializers.ValidationError({"variant": f"{variant} isn't a variant of {attrs['product'].name}."})
        return attrs


class QuotationTemplateSerializer(serializers.ModelSerializer):
    lines = TemplateLineSerializer(many=True)
    validity_days = serializers.IntegerField(min_value=1, default=30)
    plan_name = serializers.CharField(source="plan.name", read_only=True)

    class Meta:
        model = QuotationTemplate
        fields = ["id", "name", "plan", "plan_name", "validity_days", "notes", "lines"]

    def _save_lines(self, template, lines):
        template.lines.all().delete()
        TemplateLine.objects.bulk_create([TemplateLine(template=template, **line) for line in lines])

    @transaction.atomic
    def create(self, validated_data):
        lines = validated_data.pop("lines")
        template = super().create(validated_data)
        self._save_lines(template, lines)
        return template

    @transaction.atomic
    def update(self, instance, validated_data):
        lines = validated_data.pop("lines", None)
        template = super().update(instance, validated_data)
        if lines is not None:
            self._save_lines(template, lines)
        return template
