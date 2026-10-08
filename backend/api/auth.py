from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView


class SessionCookieAuthentication(SessionAuthentication):
    def authenticate_header(self, request):
        # DRF otherwise downgrades anonymous session requests from 401 to 403.
        return "Session"


class SessionCookieAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "api.auth.SessionCookieAuthentication"
    name = "sessionCookieAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "cookie",
            "name": "sessionid",
        }


SESSION_AUTHENTICATION_CLASSES = [SessionCookieAuthentication]
SESSION_PERMISSION_CLASSES = [IsAuthenticated]


class SessionAuthenticatedAPIView(APIView):
    authentication_classes = SESSION_AUTHENTICATION_CLASSES
    permission_classes = SESSION_PERMISSION_CLASSES


def session_authenticated_api_view(methods):
    def decorate(view_func):
        view_func = authentication_classes(SESSION_AUTHENTICATION_CLASSES)(view_func)
        view_func = permission_classes(SESSION_PERMISSION_CLASSES)(view_func)
        return api_view(methods)(view_func)

    return decorate
