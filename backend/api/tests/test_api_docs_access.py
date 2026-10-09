from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient


User = get_user_model()


class APIDocumentationAccessTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @override_settings(DEBUG=True)
    def test_schema_and_swagger_ui_are_public_in_development(self):
        schema_response = self.client.get("/api/schema/")
        docs_response = self.client.get("/api/docs/")

        self.assertEqual(schema_response.status_code, 200)
        self.assertIn(b"openapi", schema_response.content)
        self.assertEqual(docs_response.status_code, 200)
        self.assertIn("text/html", docs_response["Content-Type"])

    @override_settings(DEBUG=False)
    def test_schema_and_swagger_ui_are_not_found_outside_development(self):
        schema_response = self.client.get("/api/schema/")
        docs_response = self.client.get("/api/docs/")

        self.assertEqual(schema_response.status_code, 404)
        self.assertEqual(docs_response.status_code, 404)

    @override_settings(DEBUG=False)
    def test_authenticated_application_routes_remain_available(self):
        user = User.objects.create_user(
            username="docs-access-user",
            email="docs-access@example.com",
            password="safe-test-password",
        )
        self.client.force_login(user)

        response = self.client.get("/api/categories/")

        self.assertEqual(response.status_code, 200)
