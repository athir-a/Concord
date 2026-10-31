from rest_framework import serializers

from apps.accounts.models import Customer
from apps.catalog.models import DiscountRule, Plan, Product, ProductVariant, QuotationTemplate

from . import services
from .models import Subscription, SubscriptionEvent, SubscriptionLine

# What a customer may do to their own subscription in the portal.
CUSTOMER_ACTIONS = {"confirm", "pause", "resume", "close"}


class SubscriptionListSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()
    plan_name = serializers.CharField(source="plan.name")
    interval = serializers.CharField(source="plan.interval")

    class Meta:
        model = Subscription
        fields = [
            "id", "number", "customer", "customer_name", "plan", "plan_name", "interval", "status",
            "start_date", "expiry_date", "next_billing_date", "recurring_subtotal",
        ]

    def get_customer_name(self, subscription) -> str:
        return subscription.customer.company or subscription.customer.name


class SubscriptionLineSerializer(serializers.ModelSerializer):
    amount = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionLine
        fields = ["id", "product", "variant", "description", "quantity", "unit_price", "amount"]

    def get_amount(self, line) -> str:
        return f"{line.unit_price * line.quantity:.2f}"


class SubscriptionEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionEvent
        fields = ["id", "from_status", "to_status", "actor_name", "note", "created_at"]

    def get_actor_name(self, event) -> str:
        if event.actor is None:
            return "Concord"
        return event.actor.name or event.actor.email


class SubscriptionDetailSerializer(SubscriptionListSerializer):
    lines = SubscriptionLineSerializer(many=True)
    events = SubscriptionEventSerializer(many=True)
    discount_name = serializers.CharField(source="discount.name", read_only=True, default=None)
    actions = serializers.SerializerMethodField()

    class Meta(SubscriptionListSerializer.Meta):
        fields = SubscriptionListSerializer.Meta.fields + [
            "payment_terms_days", "quote_valid_until", "discount", "discount_name", "closed_at",
            "lines", "events", "actions",
        ]

    def get_actions(self, subscription) -> list[str]:
        actions = services.available_actions(subscription)
        if self.context["request"].user.role == "customer":
            return [action for action in actions if action in CUSTOMER_ACTIONS]
        return actions


class LineInputSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    variant = serializers.PrimaryKeyRelatedField(queryset=ProductVariant.objects.all(), required=False, allow_null=True)
    quantity = serializers.IntegerField(min_value=1)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False, allow_null=True)


class SubscriptionUpdateSerializer(serializers.Serializer):
    plan = serializers.PrimaryKeyRelatedField(queryset=Plan.objects.all(), required=False)
    start_date = serializers.DateField(required=False)
    expiry_date = serializers.DateField(required=False)
    payment_terms_days = serializers.IntegerField(min_value=0, max_value=365, required=False)
    quote_valid_until = serializers.DateField(required=False, allow_null=True)
    discount = serializers.PrimaryKeyRelatedField(queryset=DiscountRule.objects.all(), required=False, allow_null=True)
    lines = LineInputSerializer(many=True, required=False)


class SubscriptionCreateSerializer(SubscriptionUpdateSerializer):
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all())
    plan = serializers.PrimaryKeyRelatedField(queryset=Plan.objects.all())
    start_date = serializers.DateField()
    lines = LineInputSerializer(many=True, default=list)


class FromTemplateSerializer(serializers.Serializer):
    template = serializers.PrimaryKeyRelatedField(queryset=QuotationTemplate.objects.select_related("plan"))
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all())
    start_date = serializers.DateField()


class CloseSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class SetDiscountSerializer(serializers.Serializer):
    discount = serializers.PrimaryKeyRelatedField(queryset=DiscountRule.objects.all(), allow_null=True)
