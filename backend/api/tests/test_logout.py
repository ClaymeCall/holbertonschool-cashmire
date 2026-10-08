# API tests for POST /api/auth/logout/ — issue #24.
#
# Uses `APIClient(enforce_csrf_checks=True)` rather than the plain
# `self.client` `APITestCase` sets up by default: a default APIClient
# doesn't enforce CSRF at all, which would let this endpoint's one real
# risk — decision 0003 point 5's "logout needs a CSRF token" — pass
# completely untested.
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

User = get_user_model()

LOGIN_URL = "/api/auth/login/"
LOGOUT_URL = "/api/auth/logout/"
VALID_PASSWORD = "correct-horse-battery-staple-42"


class LogoutEndpointTests(APITestCase):
    def setUp(self):
        # LoginView's ScopedRateThrottle counters live in Django's cache and
        # persist across test methods/files in the same process — every
        # test here logs in via the real endpoint, so an uncleared counter
        # from test_login.py (or an earlier test here) throttles logins
        # that have nothing to do with what's being tested.
        cache.clear()
        self.user = User.objects.create_user(
            username="jane", email="jane@example.com", password=VALID_PASSWORD
        )
        self.client = APIClient(enforce_csrf_checks=True)

    def _login_and_get_csrf_token(self):
        response = self.client.post(
            LOGIN_URL,
            {"email": "jane@example.com", "password": VALID_PASSWORD},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        return self.client.cookies["csrftoken"].value

    def test_logs_out_with_a_valid_csrf_token(self):
        csrf_token = self._login_and_get_csrf_token()

        response = self.client.post(LOGOUT_URL, HTTP_X_CSRFTOKEN=csrf_token)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.data, None)

    def test_rejects_logout_without_a_csrf_token(self):
        self._login_and_get_csrf_token()

        response = self.client.post(LOGOUT_URL)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_rejects_an_unauthenticated_logout_attempt(self):
        # No prior login at all — not even a session cookie.
        response = self.client.post(LOGOUT_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_old_session_cookie_is_rejected_after_logout(self):
        """AC-2: subsequent requests with the logged-out credential are rejected."""
        csrf_token = self._login_and_get_csrf_token()
        old_sessionid = self.client.cookies["sessionid"].value

        logout_response = self.client.post(LOGOUT_URL, HTTP_X_CSRFTOKEN=csrf_token)
        self.assertEqual(logout_response.status_code, status.HTTP_204_NO_CONTENT)

        # A fresh client replaying the pre-logout session cookie — a stale
        # browser tab, or an attacker who captured it — knows nothing else
        # about this session.
        replay_client = APIClient(enforce_csrf_checks=True)
        replay_client.cookies["sessionid"] = old_sessionid

        response = replay_client.post(LOGOUT_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logging_out_twice_rejects_the_second_attempt(self):
        csrf_token = self._login_and_get_csrf_token()

        first = self.client.post(LOGOUT_URL, HTTP_X_CSRFTOKEN=csrf_token)
        second = self.client.post(LOGOUT_URL, HTTP_X_CSRFTOKEN=csrf_token)

        self.assertEqual(first.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(second.status_code, status.HTTP_401_UNAUTHORIZED)
