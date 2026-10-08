# API tests for POST /api/auth/login/ — issue #23.
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()

LOGIN_URL = "/api/auth/login/"
VALID_PASSWORD = "correct-horse-battery-staple-42"


class LoginEndpointTests(APITestCase):
    def setUp(self):
        # ScopedRateThrottle's counters live in Django's cache (LocMemCache
        # by default), which persists across test methods in the same
        # process unless cleared — without this, an earlier test's login
        # attempts count against a later test's throttle budget.
        cache.clear()
        self.user = User.objects.create_user(
            username="jane", email="jane@example.com", password=VALID_PASSWORD
        )

    def test_logs_in_with_correct_credentials(self):
        response = self.client.post(
            LOGIN_URL,
            {"email": "jane@example.com", "password": VALID_PASSWORD},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "jane@example.com")
        self.assertEqual(response.data["username"], "jane")
        self.assertNotIn("password", response.data)

    def test_establishes_a_session_on_success(self):
        response = self.client.post(
            LOGIN_URL,
            {"email": "jane@example.com", "password": VALID_PASSWORD},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("_auth_user_id", self.client.session)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.id)

    def test_rejects_a_wrong_password_generically(self):
        response = self.client.post(
            LOGIN_URL,
            {"email": "jane@example.com", "password": "wrong-password-entirely"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], "Invalid email or password.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_rejects_a_nonexistent_email_with_the_identical_response(self):
        """
        AC-2: no user-existence leakage. The response to "wrong password
        for a real account" and "no account at all" must be indistinguishable.
        """
        wrong_password_response = self.client.post(
            LOGIN_URL,
            {"email": "jane@example.com", "password": "wrong-password-entirely"},
            format="json",
        )
        cache.clear()  # don't let the throttle see the second request as attempt #2
        no_such_account_response = self.client.post(
            LOGIN_URL,
            {"email": "nobody-here@example.com", "password": "whatever-at-all"},
            format="json",
        )

        self.assertEqual(wrong_password_response.status_code, no_such_account_response.status_code)
        self.assertEqual(wrong_password_response.data, no_such_account_response.data)
        self.assertEqual(no_such_account_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_rejects_an_inactive_user(self):
        self.user.is_active = False
        self.user.save()

        response = self.client.post(
            LOGIN_URL,
            {"email": "jane@example.com", "password": VALID_PASSWORD},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_rejects_missing_email_or_password_with_400(self):
        response = self.client.post(LOGIN_URL, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        self.assertIn("password", response.data)

    def test_throttles_repeated_attempts_from_the_same_caller(self):
        # DEFAULT_THROTTLE_RATES["login"] is "5/min" (settings.py).
        for _ in range(5):
            response = self.client.post(
                LOGIN_URL,
                {"email": "jane@example.com", "password": "wrong-password-entirely"},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        sixth_response = self.client.post(
            LOGIN_URL,
            {"email": "jane@example.com", "password": "wrong-password-entirely"},
            format="json",
        )
        self.assertEqual(sixth_response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        # Correct credentials don't get a pass once throttled — the limit
        # is on the caller, not on whether they're currently "right."
        still_throttled_response = self.client.post(
            LOGIN_URL,
            {"email": "jane@example.com", "password": VALID_PASSWORD},
            format="json",
        )
        self.assertEqual(still_throttled_response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
