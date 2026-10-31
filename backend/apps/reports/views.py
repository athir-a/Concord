from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Customer
from apps.catalog.models import Plan
from apps.common.permissions import IsTeam

from . import selectors


class ReportFilterSerializer(serializers.Serializer):
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    plan = serializers.PrimaryKeyRelatedField(queryset=Plan.objects.all(), required=False)
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all(), required=False)

    def validate(self, attrs):
        if attrs.get("date_from") and attrs.get("date_to") and attrs["date_to"] < attrs["date_from"]:
            raise serializers.ValidationError({"date_to": "This must be on or after the start date."})
        return attrs


class ReportView(APIView):
    permission_classes = [IsTeam]

    def filters(self, request):
        serializer = ReportFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data


def _money_as_strings(value):
    """Money stays a string in JSON, the same as everywhere else in the API."""
    if isinstance(value, dict):
        return {key: _money_as_strings(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_money_as_strings(item) for item in value]
    if hasattr(value, "quantize"):
        return f"{value:.2f}"
    return value


class SummaryView(ReportView):
    @extend_schema(parameters=[ReportFilterSerializer], responses={200: None})
    def get(self, request):
        return Response(_money_as_strings(selectors.summary(self.filters(request))))


class RevenueSeriesView(ReportView):
    @extend_schema(parameters=[ReportFilterSerializer], responses={200: None})
    def get(self, request):
        return Response(_money_as_strings(selectors.revenue_series(self.filters(request))))


class OverdueAgeingView(ReportView):
    @extend_schema(parameters=[ReportFilterSerializer], responses={200: None})
    def get(self, request):
        return Response(_money_as_strings(selectors.overdue_ageing(self.filters(request))))


class CustomerSummaryView(ReportView):
    @extend_schema(responses={200: None})
    def get(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        return Response(_money_as_strings(selectors.customer_summary(customer)))
