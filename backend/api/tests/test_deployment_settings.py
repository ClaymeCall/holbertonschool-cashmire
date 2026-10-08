from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from cashmire.settings import _validate_deployment_security


VALID_PRODUCTION_SECRET = "aB3!cD5@" * 7


class DeploymentSecuritySettingsTests(SimpleTestCase):
    def test_development_allows_local_placeholders(self):
        _validate_deployment_security(
            debug=True,
            secret_key="change-me",
            allowed_hosts=["*"],
        )

    def test_non_debug_requires_secret_key(self):
        for secret_key in ("", " ", "dev-insecure-secret-key", "change-me"):
            with self.subTest(secret_key=secret_key):
                with self.assertRaisesMessage(
                    ImproperlyConfigured,
                    "Set DJANGO_SECRET_KEY to a unique, non-development value",
                ):
                    _validate_deployment_security(
                        debug=False,
                        secret_key=secret_key,
                        allowed_hosts=["api.example.com"],
                    )

    def test_non_debug_rejects_short_or_low_entropy_secret_keys(self):
        for secret_key in ("short-secret", "a" * 60):
            with self.subTest(secret_key=secret_key):
                with self.assertRaisesMessage(
                    ImproperlyConfigured,
                    "DJANGO_SECRET_KEY must contain at least 50 characters",
                ):
                    _validate_deployment_security(
                        debug=False,
                        secret_key=secret_key,
                        allowed_hosts=["api.example.com"],
                    )

    def test_non_debug_requires_explicit_allowed_hosts(self):
        for allowed_hosts in ([], ["*"], ["api.example.com", "*"]):
            with self.subTest(allowed_hosts=allowed_hosts):
                with self.assertRaisesMessage(
                    ImproperlyConfigured,
                    "DJANGO_ALLOWED_HOSTS to explicit hostnames",
                ):
                    _validate_deployment_security(
                        debug=False,
                        secret_key=VALID_PRODUCTION_SECRET,
                        allowed_hosts=allowed_hosts,
                    )

    def test_non_debug_accepts_unique_secret_and_explicit_hostnames(self):
        _validate_deployment_security(
            debug=False,
            secret_key=VALID_PRODUCTION_SECRET,
            allowed_hosts=["api.example.com", "admin.example.com"],
        )
