# API tests for POST /api/auth/register/ — issue #22.
#
# docs/api-design.md §2.1 documents `username` as a required request field;
# this implementation makes it optional (see serializers.py's module
# docstring) because the shipped register form (issue #28,
# frontend/src/routes/register/+page.svelte) sends only `{email, password}`.
# These tests cover both that real shape and the documented optional one.
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()

REGISTER_URL = "/api/auth/register/"

# Long and unusual enough to clear every AUTH_PASSWORD_VALIDATORS check in
# settings.py (min length, not entirely numeric, not a common password).
VALID_PASSWORD = "correct-horse-battery-staple-42"


class RegisterEndpointTests(APITestCase):
    def setUp(self):
        cache.clear()

    def test_registers_with_only_email_and_password(self):
        """AC-1: the exact shape the shipped register form sends."""
        response = self.client.post(
            REGISTER_URL,
            {"email": "jane@example.com", "password": VALID_PASSWORD},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(
            response.data,
            {"detail": "If registration can be completed, sign in to continue."},
        )
        user = User.objects.get(email="jane@example.com")
        self.assertTrue(user.check_password(VALID_PASSWORD))
        self.assertNotEqual(user.password, VALID_PASSWORD)  # AC-3: hashed, not plaintext

    def test_auto_derives_a_username_from_the_email(self):
        response = self.client.post(
            REGISTER_URL,
            {"email": "jane.doe@example.com", "password": VALID_PASSWORD},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        user = User.objects.get(email="jane.doe@example.com")
        self.assertEqual(user.username, "jane.doe")

    def test_disambiguates_usernames_derived_from_colliding_local_parts(self):
        User.objects.create_user(username="jane", email="jane@other.example", password="x")

        response = self.client.post(
            REGISTER_URL,
            {"email": "jane@example.com", "password": VALID_PASSWORD},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        user = User.objects.get(email="jane@example.com")
        self.assertEqual(user.username, "jane-2")

    def test_accepts_an_explicit_username_matching_the_documented_contract(self):
        """docs/api-design.md §2.1's documented request shape still works."""
        response = self.client.post(
            REGISTER_URL,
            {
                "email": "alice@example.com",
                "username": "alice_wonderland",
                "password": VALID_PASSWORD,
                "first_name": "Alice",
                "last_name": "Wonderland",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        user = User.objects.get(email="alice@example.com")
        self.assertEqual(user.username, "alice_wonderland")
        self.assertEqual(user.first_name, "Alice")

    def test_new_and_existing_emails_have_the_same_neutral_response(self):
        User.objects.create_user(
            username="existing", email="jane@example.com", password=VALID_PASSWORD
        )

        duplicate_response = self.client.post(
            REGISTER_URL,
            {"email": "jane@example.com", "password": VALID_PASSWORD},
            format="json",
        )
        new_response = self.client.post(
            REGISTER_URL,
            {"email": "new@example.com", "password": VALID_PASSWORD},
            format="json",
        )

        self.assertEqual(duplicate_response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(new_response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(duplicate_response.data, new_response.data)
        self.assertEqual(
            duplicate_response.data,
            {"detail": "If registration can be completed, sign in to continue."},
        )
        self.assertNotIn("sessionid", duplicate_response.cookies)
        self.assertNotIn("sessionid", new_response.cookies)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_duplicate_email_does_not_change_other_validation_feedback(self):
        User.objects.create_user(
            username="existing", email="jane@example.com", password=VALID_PASSWORD
        )

        duplicate_response = self.client.post(
            REGISTER_URL,
            {"email": "jane@example.com", "password": "short"},
            format="json",
        )
        new_response = self.client.post(
            REGISTER_URL,
            {"email": "new@example.com", "password": "short"},
            format="json",
        )

        self.assertEqual(duplicate_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(duplicate_response.status_code, new_response.status_code)
        self.assertEqual(duplicate_response.data, new_response.data)

    def test_duplicate_explicit_username_has_the_neutral_response(self):
        User.objects.create_user(
            username="alice_wonderland", email="someone-else@example.com", password=VALID_PASSWORD
        )

        response = self.client.post(
            REGISTER_URL,
            {
                "email": "alice@example.com",
                "username": "alice_wonderland",
                "password": VALID_PASSWORD,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(
            response.data,
            {"detail": "If registration can be completed, sign in to continue."},
        )
        self.assertFalse(User.objects.filter(email="alice@example.com").exists())

    def test_rejects_an_invalid_email_format(self):
        response = self.client.post(
            REGISTER_URL,
            {"email": "not-an-email", "password": VALID_PASSWORD},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_rejects_a_missing_email_or_password(self):
        response = self.client.post(REGISTER_URL, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        self.assertIn("password", response.data)

    def test_rejects_a_password_shorter_than_the_configured_minimum(self):
        response = self.client.post(
            REGISTER_URL,
            {"email": "jane@example.com", "password": "short1"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_rejects_a_fully_numeric_password(self):
        # AUTH_PASSWORD_VALIDATORS includes NumericPasswordValidator.
        response = self.client.post(
            REGISTER_URL,
            {"email": "jane@example.com", "password": "48502913765024"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_rejects_a_password_too_similar_to_the_users_own_email(self):
        # AUTH_PASSWORD_VALIDATORS includes UserAttributeSimilarityValidator,
        # exercised here against the in-memory candidate user built in
        # RegisterSerializer.validate() (there is no saved user yet to
        # compare against at this point in the request).
        response = self.client.post(
            REGISTER_URL,
            {"email": "jane.doe@example.com", "password": "janedoeexample"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_registration_does_not_establish_a_session(self):
        """Registration remains anonymous; the user signs in separately."""
        response = self.client.post(
            REGISTER_URL,
            {"email": "jane@example.com", "password": VALID_PASSWORD},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_throttles_registration_attempts_per_ip(self):
        payload = {"email": "jane@example.com", "password": VALID_PASSWORD}

        for _ in range(5):
            response = self.client.post(REGISTER_URL, payload, format="json")
            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        throttled_response = self.client.post(REGISTER_URL, payload, format="json")
        self.assertEqual(
            throttled_response.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )
        login_response = self.client.post(
            "/api/auth/login/",
            {"email": "jane@example.com", "password": "incorrect-password"},
            format="json",
        )
        self.assertEqual(
            login_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
