from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.views import exception_handler


class DomainError(APIException):
    """A business rule said no. Raised by services, rendered by the handler below."""

    status_code = status.HTTP_409_CONFLICT
    default_code = "conflict"

    def __init__(self, detail, code=None, status_code=None, fields=None):
        super().__init__(detail, code or self.default_code)
        if status_code:
            self.status_code = status_code
        self.fields = fields or {}


def _flatten_errors(errors):
    """Turn DRF's nested error lists into {field: "first message"}."""
    if isinstance(errors, dict):
        return {key: _flatten_errors(value) for key, value in errors.items()}
    if isinstance(errors, list) and errors:
        return _flatten_errors(errors[0])
    return str(errors)


def api_exception_handler(exc, context):
    """Every API error has one shape: {"code", "detail", "fields"}."""
    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, ValidationError):
        fields = _flatten_errors(exc.detail)
        if not isinstance(fields, dict):
            fields = {"non_field_errors": fields}
        non_field = fields.pop("non_field_errors", None)
        first = non_field or next(
            (v for v in fields.values() if isinstance(v, str)), "Please check the highlighted fields."
        )
        response.data = {"code": "validation_error", "detail": first, "fields": fields}
    else:
        code = getattr(exc.detail, "code", None) or getattr(exc, "default_code", "error")
        response.data = {
            "code": code,
            "detail": str(exc.detail),
            "fields": getattr(exc, "fields", {}),
        }
    return response
