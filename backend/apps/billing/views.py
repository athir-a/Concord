from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsAdminRole, IsTeam
from apps.subscriptions.selectors import subscriptions_visible_to
from apps.subscriptions.serializers import SubscriptionDetailSerializer

from . import services
from .filters import InvoiceFilter, PaymentFilter
from .models import BillingRun
from .selectors import invoices_visible_to, payments_visible_to
from .serializers import (
    BillingRunSerializer,
    BulkConfirmSerializer,
    InvoiceDetailSerializer,
    InvoiceListSerializer,
    PaymentSerializer,
    PreviewSerializer,
    RecordPaymentSerializer,
    RunBillingSerializer,
)

READ_ACTIONS = {"list", "retrieve"}


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    """Invoices are only ever created by billing, and only change through these actions."""

    filterset_class = InvoiceFilter
    search_fields = ["number", "customer_name", "subscription__number"]
    ordering_fields = ["number", "issue_date", "due_date", "total", "status"]

    def get_permissions(self):
        return [IsAuthenticated()] if self.action in READ_ACTIONS else [IsTeam()]

    def get_queryset(self):
        queryset = invoices_visible_to(self.request.user).select_related("subscription")
        if self.action == "list":
            return queryset
        return queryset.prefetch_related("lines", "payments__recorded_by", "payments__invoice")

    def get_serializer_class(self):
        return InvoiceListSerializer if self.action == "list" else InvoiceDetailSerializer

    def _respond(self, invoice, status_code=status.HTTP_200_OK):
        fresh = self.get_queryset().get(pk=invoice.pk)
        return Response(InvoiceDetailSerializer(fresh).data, status=status_code)

    @extend_schema(request=None, responses=InvoiceDetailSerializer)
    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        return self._respond(services.confirm_invoice(self.get_object()))

    @extend_schema(request=None, responses=InvoiceDetailSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self._respond(services.cancel_invoice(self.get_object()))

    @extend_schema(request=None, responses=InvoiceDetailSerializer)
    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        return self._respond(services.send_invoice(self.get_object()))

    @extend_schema(request=None, responses={201: InvoiceDetailSerializer})
    @action(detail=True, methods=["post"])
    def reissue(self, request, pk=None):
        return self._respond(services.reissue_invoice(self.get_object()), status.HTTP_201_CREATED)

    @extend_schema(request=RecordPaymentSerializer, responses={201: InvoiceDetailSerializer})
    @action(detail=True, methods=["post"])
    def payments(self, request, pk=None):
        serializer = RecordPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invoice = self.get_object()
        services.record_payment(invoice, actor=request.user, **serializer.validated_data)
        return self._respond(invoice, status.HTTP_201_CREATED)

    @extend_schema(request=BulkConfirmSerializer, responses={200: None})
    @action(detail=False, methods=["post"], url_path="bulk-confirm")
    def bulk_confirm(self, request):
        serializer = BulkConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"confirmed": services.bulk_confirm(serializer.validated_data["invoices"])})


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only. Payments are recorded against an invoice, at invoices/{id}/payments."""

    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer
    filterset_class = PaymentFilter
    search_fields = ["invoice__number", "invoice__customer_name", "note"]
    ordering_fields = ["paid_on", "amount"]

    def get_queryset(self):
        return payments_visible_to(self.request.user)


class RunBillingView(APIView):
    permission_classes = [IsAdminRole]

    @extend_schema(request=RunBillingSerializer, responses={201: BillingRunSerializer})
    def post(self, request):
        serializer = RunBillingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        run = services.run_billing(as_of=serializer.validated_data.get("as_of"), triggered_by=request.user)
        return Response(BillingRunSerializer(run).data, status=status.HTTP_201_CREATED)


class BillingDueView(APIView):
    """How many subscriptions a run on this date would bill."""

    permission_classes = [IsAdminRole]

    @extend_schema(parameters=[RunBillingSerializer], responses={200: None})
    def get(self, request):
        serializer = RunBillingSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        as_of = serializer.validated_data.get("as_of") or timezone.localdate()
        return Response({"as_of": as_of, "due": len(services._due_subscription_ids(as_of))})


class BillingRunListView(generics.ListAPIView):
    permission_classes = [IsAdminRole]
    serializer_class = BillingRunSerializer
    queryset = BillingRun.objects.select_related("triggered_by")


class ActivateSubscriptionView(APIView):
    """Lives in billing because activating creates the first invoice."""

    permission_classes = [IsTeam]

    @extend_schema(request=None, responses=SubscriptionDetailSerializer)
    def post(self, request, pk):
        subscription = get_object_or_404(subscriptions_visible_to(request.user), pk=pk)
        services.activate(subscription, actor=request.user)
        fresh = (
            subscriptions_visible_to(request.user)
            .prefetch_related("lines", "events__actor")
            .get(pk=pk)
        )
        return Response(SubscriptionDetailSerializer(fresh, context={"request": request}).data)


class SubscriptionPreviewView(APIView):
    """What the next invoice would be, including tax and discount. Saves nothing."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses=PreviewSerializer)
    def get(self, request, pk):
        subscription = get_object_or_404(subscriptions_visible_to(request.user), pk=pk)
        return Response(PreviewSerializer(services.preview_invoice(subscription)).data)
