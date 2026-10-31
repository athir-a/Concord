from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Customer, User


class CustomerSerializer(serializers.ModelSerializer):
    has_login = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            "id", "name", "company", "email", "phone", "address", "tax_id", "is_active",
            "has_login", "created_at",
        ]
        read_only_fields = ["created_at"]

    def get_has_login(self, customer) -> bool:
        return customer.user_id is not None


def _check_password(password, user=None):
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(exc.messages[0])
    return password


def _check_email_free(email):
    email = email.strip().lower()
    if User.objects.filter(email=email).exists():
        raise serializers.ValidationError("An account with this email already exists.")
    return email


class UserSerializer(serializers.ModelSerializer):
    customer_id = serializers.IntegerField(source="customer.id", read_only=True, default=None)

    class Meta:
        model = User
        fields = ["id", "email", "name", "role", "customer_id"]
        read_only_fields = fields


class SignupSerializer(serializers.Serializer):
    # No role field: signup can only ever create a customer.
    name = serializers.CharField(max_length=150)
    company = serializers.CharField(max_length=200, required=False, allow_blank=True)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, value):
        return _check_email_free(value)

    def validate(self, attrs):
        probe = User(email=attrs["email"], name=attrs["name"])
        try:
            _check_password(attrs["password"], user=probe)
        except serializers.ValidationError as exc:
            raise serializers.ValidationError({"password": exc.detail})
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class StaffCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, value):
        return _check_email_free(value)

    def validate(self, attrs):
        probe = User(email=attrs["email"], name=attrs["name"])
        try:
            _check_password(attrs["password"], user=probe)
        except serializers.ValidationError as exc:
            raise serializers.ValidationError({"password": exc.detail})
        return attrs


class StaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "name", "role", "is_active", "date_joined"]
        read_only_fields = fields
