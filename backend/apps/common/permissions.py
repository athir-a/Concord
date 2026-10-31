from rest_framework.permissions import BasePermission

class IsAdminRole(BasePermission):
    # Placeholder: connect this to your actual role/membership model.
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.is_staff
        )
