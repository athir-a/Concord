from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import generics, serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.common.exceptions import DomainError
from apps.common.permissions import IsAdminRole

from . import services
from .models import User
from .serializers import (
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    SignupSerializer,
    StaffCreateSerializer,
    StaffSerializer,
    UserSerializer,
    _check_password,
)


class CsrfView(APIView):
    """The frontend calls this once so the CSRF cookie exists before the first POST."""

    permission_classes = [AllowAny]

    @extend_schema(responses={204: None})
    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response(status=status.HTTP_204_NO_CONTENT)


class PublicFormView(APIView):
    """Base for anonymous POST forms.

    DRF only checks CSRF for logged-in users, so these turn it on explicitly.
    Without it, another site could silently log a visitor into an attacker's account.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]

    @method_decorator(csrf_protect)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class SignupView(PublicFormView):
    throttle_scope = "signup"

    @extend_schema(request=SignupSerializer, responses={201: UserSerializer})
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.register_customer(**serializer.validated_data)
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(PublicFormView):
    throttle_scope = "login"

    @extend_schema(request=LoginSerializer, responses={200: UserSerializer})
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data["email"].strip().lower(),
            password=serializer.validated_data["password"],
        )
        if user is None:
            raise DomainError("Incorrect email or password.", code="invalid_credentials", status_code=400)
        login(request, user)
        return Response(UserSerializer(user).data)


class LogoutView(APIView):
    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    @extend_schema(responses=UserSerializer)
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class PasswordResetRequestView(PublicFormView):
    throttle_scope = "password_reset"

    @extend_schema(request=PasswordResetRequestSerializer, responses={200: None})
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.request_password_reset(serializer.validated_data["email"])
        # Same answer whether or not the account exists, so this can't be used
        # to discover who has an account.
        return Response({"detail": "If that email has an account, a reset link is on its way."})


class PasswordResetConfirmView(PublicFormView):
    throttle_scope = "password_reset"

    @extend_schema(request=PasswordResetConfirmSerializer, responses={200: None})
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = services.find_user_for_reset(data["uid"], data["token"])
        try:
            _check_password(data["password"], user=user)
        except serializers.ValidationError as exc:
            raise serializers.ValidationError({"password": exc.detail})
        user.set_password(data["password"])
        user.save(update_fields=["password"])
        return Response({"detail": "Your password has been changed. You can now log in."})


class StaffListCreateView(generics.ListAPIView):
    """Only the admin can see or add members of staff."""

    permission_classes = [IsAdminRole]
    serializer_class = StaffSerializer
    queryset = User.objects.filter(role=User.Role.STAFF).order_by("name", "id")

    @extend_schema(request=StaffCreateSerializer, responses={201: StaffSerializer})
    def post(self, request):
        serializer = StaffCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.create_staff(**serializer.validated_data)
        return Response(StaffSerializer(user).data, status=status.HTTP_201_CREATED)
