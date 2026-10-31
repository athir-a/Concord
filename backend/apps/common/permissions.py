from rest_framework.permissions import SAFE_METHODS, BasePermission


def _has_role(request, *roles):
    return bool(request.user and request.user.is_authenticated and request.user.role in roles)


class IsAdminRole(BasePermission):
    """Admin only: catalog changes, discount rules, staff accounts, billing runs."""

    def has_permission(self, request, view):
        return _has_role(request, "admin")


class IsTeam(BasePermission):
    """Admin or staff: the day-to-day work of the internal team."""

    def has_permission(self, request, view):
        return _has_role(request, "admin", "staff")


class IsAdminOrTeamReadOnly(BasePermission):
    """Admin writes, staff reads. Customers get nothing."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return _has_role(request, "admin", "staff")
        return _has_role(request, "admin")
