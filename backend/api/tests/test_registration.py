# API tests for POST /api/auth/register/ — issue #22.
#
# docs/api-design.md §2.1 documents `username` as a required request field;
# this implementation makes it optional (see serializers.py's module
# docstring) because the shipped register form (issue #28,
# frontend/src/routes/register/+page.svelte) sends only `{email, password}`.
# These tests cover both that real shape and the documented optional one.
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()

REGISTER_URL = "/api/auth/register/"

# Long and unusual enough to clear every AUTH_PASSWORD_VALIDATORS check in
# settings.py (min length, not entirely numeric, not a common password).
VALID_PASSWORD = "correct-horse-battery-staple-42"


class RegisterEndpointTests(APITestCase):
    def test_registers_with_only_email_and_password(self):
        """AC-1: the exact shape the shipped register form sends."""
        response = self.client.post(
            REGISTER_URL,
            {"email": "jane@example.com", "password": VALID_PASSWORD},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["email"], "jane@example.com")
        self.assertNotIn("password", response.data)  # AC-3
        user = User.objects.get(email="jane@example.com")
        self.assertTrue(user.check_password(VALID_PASSWORD))
        self.assertNotEqual(user.password, VALID_PASSWORD)  # AC-3: hashed, not plaintext

    def test_auto_derives_a_username_from_the_email(self):
        response = self.client.post(
            REGISTER_URL,
            {"email": "jane.doe@example.com", "password": VALID_PASSWORD},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["username"], "jane.doe")

    def test_disambiguates_usernames_derived_from_colliding_local_parts(self):
        User.objects.create_user(username="jane", email="jane@other.example", password="x")

        response = self.client.post(
            REGISTER_URL,
            {"email": "jane@example.com", "password": VALID_PASSWORD},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["username"], "jane-2")

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

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["username"], "alice_wonderland")
        self.assertEqual(response.data["first_name"], "Alice")

    def test_rejects_a_duplicate_email_as_a_clean_400_not_a_db_error(self):
        """
        register/page.test.js (T-6) asserts a Svelte component renders
        whatever `{field: [msg]}` 400 body it's given — a synthetic example
        in that test, not a real integration check, so it doesn't pin the
        exact wording. This pins the real one: DRF's ModelSerializer
        surfaces Django's own default `unique` error message for free for
        any auto-built field backed by a `unique=True` model field.
        """
        User.objects.create_user(
            username="existing", email="jane@example.com", password=VALID_PASSWORD
        )

        response = self.client.post(
            REGISTER_URL,
            {"email": "jane@example.com", "password": VALID_PASSWORD},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["email"], ["user with this email already exists."])

    def test_rejects_a_duplicate_explicit_username(self):
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

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["username"], ["user with this username already exists."])

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

    def test_establishes_a_session_on_success(self):
        """decision 0003: register also logs the user in, like login does."""
        response = self.client.post(
            REGISTER_URL,
            {"email": "jane@example.com", "password": VALID_PASSWORD},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("_auth_user_id", self.client.session)
        user = User.objects.get(email="jane@example.com")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.id)
