from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


class CurrentUserEndpointTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="jane",
            email="jane@example.com",
            password="correct-horse-battery-staple-42",
        )
        self.url = "/api/auth/me/"

    def test_anonymous_request_is_rejected_with_401(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response["WWW-Authenticate"], "Session")

    def test_authenticated_session_returns_only_the_current_user(self):
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(response.data),
            {
                "id",
                "email",
                "username",
                "first_name",
                "last_name",
                "is_active",
                "created_at",
                "updated_at",
            },
        )
        self.assertEqual(response.data["id"], self.user.pk)
        self.assertEqual(response.data["email"], self.user.email)
        self.assertNotIn("password", response.data)

    def test_basic_authentication_is_not_accepted(self):
        self.client.credentials(HTTP_AUTHORIZATION="Basic dXNlcjpwYXNz")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
