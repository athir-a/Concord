from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter(trailing_slash=False, use_regex_path=False)
router.include_root_view = False
router.register("customers", views.CustomerViewSet)

urlpatterns = [
    path("auth/csrf", views.CsrfView.as_view()),
    path("auth/signup", views.SignupView.as_view()),
    path("auth/login", views.LoginView.as_view()),
    path("auth/logout", views.LogoutView.as_view()),
    path("auth/me", views.MeView.as_view()),
    path("auth/password-reset", views.PasswordResetRequestView.as_view()),
    path("auth/password-reset/confirm", views.PasswordResetConfirmView.as_view()),
    path("users/staff", views.StaffListCreateView.as_view()),
    *router.urls,
]
