from rest_framework.authentication import SessionAuthentication as DRFSessionAuthentication


class SessionAuthentication(DRFSessionAuthentication):
    """Answers 401 rather than 403 for anonymous requests.

    DRF only sends 401 when the auth class names a challenge. This lets the frontend
    tell "not logged in" (401) apart from "logged in but not allowed" (403).
    """

    def authenticate_header(self, request):
        return "Session"
