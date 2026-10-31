from decimal import Decimal

from rest_framework import serializers

from .models import BillingRun, Invoice, InvoiceLine, Payment


class InvoiceListSerializer(serializers.ModelSerializer):
    amount_due = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    subscription_number = serializers.CharField(source="subscription.number", read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id", "number", "subscription", "subscription_number", "customer", "customer_name", "status",
            "period_start", "period_end", "issue_date", "due_date", "currency", "total", "amount_paid",
            "amount_due", "is_overdue", "sent_at",
        ]


class InvoiceLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLine
        fields = [
            "id", "description", "quantity", "unit_price", "discount_amount", "tax_name", "tax_rate",
            "tax_amount", "line_total",
        ]


class PaymentSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(source="invoice.number", read_only=True)
    customer_name = serializers.CharField(source="invoice.customer_name", read_only=True)
    recorded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            "id", "invoice", "invoice_number", "customer_name", "method", "amount", "paid_on", "note",
            "recorded_by_name", "created_at",
        ]

    def get_recorded_by_name(self, payment) -> str | None:
        if payment.recorded_by is None:
            return None
        return payment.recorded_by.name or payment.recorded_by.email


class InvoiceDetailSerializer(InvoiceListSerializer):
    lines = InvoiceLineSerializer(many=True)
    payments = PaymentSerializer(many=True)

    class Meta(InvoiceListSerializer.Meta):
        fields = InvoiceListSerializer.Meta.fields + [
            "customer_email", "customer_address", "subtotal", "discount_total", "tax_total",
            "confirmed_at", "cancelled_at", "lines", "payments",
        ]


class RecordPaymentSerializer(serializers.Serializer):
    method = serializers.ChoiceField(choices=Payment.Method.choices)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    paid_on = serializers.DateField()
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    idempotency_key = serializers.CharField(max_length=64, required=False, allow_blank=True, allow_null=True)


class BulkConfirmSerializer(serializers.Serializer):
    invoices = serializers.ListField(child=serializers.IntegerField(), allow_empty=False, max_length=500)


class RunBillingSerializer(serializers.Serializer):
    as_of = serializers.DateField(required=False, allow_null=True)


class BillingRunSerializer(serializers.ModelSerializer):
    triggered_by_name = serializers.SerializerMethodField()

    class Meta:
        model = BillingRun
        fields = [
            "id", "as_of", "triggered_by_name", "created_count", "skipped_count", "failed_count",
            "errors", "started_at", "finished_at",
        ]

    def get_triggered_by_name(self, run) -> str | None:
        if run.triggered_by is None:
            return None
        return run.triggered_by.name or run.triggered_by.email


class PreviewLineSerializer(serializers.Serializer):
    description = serializers.CharField()
    quantity = serializers.IntegerField()
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    discount_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    tax_name = serializers.CharField()
    tax_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    tax_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2)


class PreviewSerializer(serializers.Serializer):
    lines = PreviewLineSerializer(many=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2)
    discount_total = serializers.DecimalField(max_digits=12, decimal_places=2)
    tax_total = serializers.DecimalField(max_digits=12, decimal_places=2)
    total = serializers.DecimalField(max_digits=12, decimal_places=2)
