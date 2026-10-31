from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter(trailing_slash=False, use_regex_path=False)
router.include_root_view = False
router.register("invoices", views.InvoiceViewSet, basename="invoice")
router.register("payments", views.PaymentViewSet, basename="payment")

urlpatterns = [
    path("billing/run", views.RunBillingView.as_view()),
    path("billing/due", views.BillingDueView.as_view()),
    path("billing/runs", views.BillingRunListView.as_view()),
    path("subscriptions/<int:pk>/activate", views.ActivateSubscriptionView.as_view()),
    path("subscriptions/<int:pk>/preview", views.SubscriptionPreviewView.as_view()),
    *router.urls,
]
