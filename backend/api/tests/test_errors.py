from django.test import override_settings
from django.urls import path
from rest_framework.decorators import api_view
from rest_framework.test import APITestCase


@api_view(["GET"])
def trigger_unhandled_error(request):
    raise RuntimeError("database password=private-value")


urlpatterns = [
    path("api/test/unhandled-error/", trigger_unhandled_error),
]


class SanitizedErrorResponseTests(APITestCase):
    @override_settings(ROOT_URLCONF=__name__, DEBUG=False)
    def test_unhandled_api_exception_returns_generic_response(self):
        response = self.client.get("/api/test/unhandled-error/")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json(),
            {
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred.",
            },
        )
        self.assertNotIn(b"RuntimeError", response.content)
        self.assertNotIn(b"database password", response.content)
        self.assertNotIn(b"private-value", response.content)
