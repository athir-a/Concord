from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.permissions import IsTeam

from . import services
from .models import SubscriptionEvent
from .selectors import subscriptions_visible_to
from .serializers import (
    CUSTOMER_ACTIONS,
    CloseSerializer,
    FromTemplateSerializer,
    SetDiscountSerializer,
    SubscriptionCreateSerializer,
    SubscriptionDetailSerializer,
    SubscriptionListSerializer,
    SubscriptionUpdateSerializer,
)

READ_ACTIONS = {"list", "retrieve"}


class SubscriptionViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
    mixins.UpdateModelMixin, viewsets.GenericViewSet,
):
    """Status never changes through PATCH, only through the named actions below."""

    filterset_fields = ["status", "customer", "plan"]
    search_fields = ["number", "customer__name", "customer__company"]
    ordering_fields = ["number", "start_date", "expiry_date", "next_billing_date", "recurring_subtotal"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_permissions(self):
        if self.action in READ_ACTIONS or self.action in CUSTOMER_ACTIONS:
            return [IsAuthenticated()]
        return [IsTeam()]

    def get_queryset(self):
        queryset = subscriptions_visible_to(self.request.user)
        if self.action == "list":
            return queryset
        events = SubscriptionEvent.objects.select_related("actor")
        return queryset.prefetch_related("lines", Prefetch("events", queryset=events))

    def get_serializer_class(self):
        return SubscriptionListSerializer if self.action == "list" else SubscriptionDetailSerializer

    def _respond(self, subscription, status_code=status.HTTP_200_OK):
        """Read it back fresh, with lines and history, for the screen to show."""
        fresh = self.get_queryset().get(pk=subscription.pk)
        return Response(self.get_serializer(fresh).data, status=status_code)

    @extend_schema(request=SubscriptionCreateSerializer, responses={201: SubscriptionDetailSerializer})
    def create(self, request, *args, **kwargs):
        serializer = SubscriptionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        subscription = services.create_subscription(
            line_specs=data.pop("lines"), actor=request.user, **data
        )
        return self._respond(subscription, status.HTTP_201_CREATED)

    @extend_schema(request=SubscriptionUpdateSerializer, responses=SubscriptionDetailSerializer)
    def partial_update(self, request, *args, **kwargs):
        serializer = SubscriptionUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        subscription = services.update_draft(
            self.get_object(), line_specs=data.pop("lines", None), actor=request.user, **data
        )
        return self._respond(subscription)

    @extend_schema(request=FromTemplateSerializer, responses={201: SubscriptionDetailSerializer})
    @action(detail=False, methods=["post"], url_path="from-template")
    def from_template(self, request):
        serializer = FromTemplateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscription = services.create_from_template(actor=request.user, **serializer.validated_data)
        return self._respond(subscription, status.HTTP_201_CREATED)

    @extend_schema(request=None, responses=SubscriptionDetailSerializer)
    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        return self._respond(services.send_quotation(self.get_object(), actor=request.user))

    @extend_schema(request=None, responses=SubscriptionDetailSerializer)
    @action(detail=True, methods=["post"])
    def revise(self, request, pk=None):
        return self._respond(services.revise_quotation(self.get_object(), actor=request.user))

    @extend_schema(request=None, responses=SubscriptionDetailSerializer)
    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        return self._respond(services.confirm_quotation(self.get_object(), actor=request.user))

    @extend_schema(request=None, responses=SubscriptionDetailSerializer)
    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        return self._respond(services.pause(self.get_object(), actor=request.user))

    @extend_schema(request=None, responses=SubscriptionDetailSerializer)
    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        return self._respond(services.resume(self.get_object(), actor=request.user))

    @extend_schema(request=None, responses=SubscriptionDetailSerializer)
    @action(detail=True, methods=["post"])
    def renew(self, request, pk=None):
        return self._respond(services.renew(self.get_object(), actor=request.user))

    @extend_schema(request=CloseSerializer, responses=SubscriptionDetailSerializer)
    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        serializer = CloseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscription = services.close(self.get_object(), actor=request.user, note=serializer.validated_data["note"])
        return self._respond(subscription)

    @extend_schema(request=SetDiscountSerializer, responses=SubscriptionDetailSerializer)
    @action(detail=True, methods=["post"])
    def discount(self, request, pk=None):
        serializer = SetDiscountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscription = services.set_discount(
            self.get_object(), serializer.validated_data["discount"], actor=request.user
        )
        return self._respond(subscription)
