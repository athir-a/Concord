from django.urls import path

from . import views

urlpatterns = [
    path("reports/summary", views.SummaryView.as_view()),
    path("reports/revenue-series", views.RevenueSeriesView.as_view()),
    path("reports/overdue-ageing", views.OverdueAgeingView.as_view()),
    path("customers/<int:pk>/summary", views.CustomerSummaryView.as_view()),
]
