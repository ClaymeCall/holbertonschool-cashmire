import re

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

User = get_user_model()

# Django's UnicodeUsernameValidator (the one api.User inherits from
# AbstractUser) only allows letters, digits and @/./+/-/_ — anything else in
# an email's local part gets collapsed to "_".
_USERNAME_UNSAFE_RE = re.compile(r"[^\w.@+-]")
_MAX_USERNAME_LENGTH = 150


def _username_from_email(email):
    """First-pass username candidate: the email's local part, sanitized."""
    local_part = email.split("@", 1)[0]
    candidate = _USERNAME_UNSAFE_RE.sub("_", local_part)[:_MAX_USERNAME_LENGTH]
    return candidate or "user"


def generate_unique_username(email):
    """Derive a username from `email` that doesn't collide with an existing one.

    docs/erd.md keeps `username` as a required, unique field on `User`, but
    the registration form (issue #28) only collects email + password — the
    API has to supply one. Appends a numeric suffix on collision
    ("jane", "jane-2", "jane-3", ...), truncating the base so the suffixed
    result still fits in 150 characters.
    """
    base = _username_from_email(email)
    candidate = base
    suffix = 1
    while User.objects.filter(username=candidate).exists():
        suffix += 1
        tail = f"-{suffix}"
        candidate = f"{base[: _MAX_USERNAME_LENGTH - len(tail)]}{tail}"
    return candidate


class RegisterSerializer(serializers.ModelSerializer):
    """POST /api/auth/register/ — docs/api-design.md §2.1, issue #22.

    Deviation from §2.1's documented contract, driven by the frontend that
    already exists (register/+page.svelte, issue #28): that form sends only
    `{email, password}`. `username` is accepted if a future client supplies
    one (matching §2.1 as written), but is optional here and auto-derived
    via `generate_unique_username` when omitted — see that function's
    docstring. `first_name`/`last_name` are likewise optional; the shipped
    form never sends them either.
    """

    password = serializers.CharField(write_only=True, trim_whitespace=False)
    username = serializers.CharField(required=False, max_length=_MAX_USERNAME_LENGTH)

    class Meta:
        model = User
        fields = ["id", "email", "username", "password", "first_name", "last_name", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_username(self, value):
        # Only reached when a client supplies one explicitly — the
        # auto-generated path in `validate()` already guarantees uniqueness
        # by construction. Phrasing matches Django's own default `unique`
        # error message (Field.default_error_messages), which is what the
        # auto-built `email` field already surfaces for free via DRF's
        # ModelSerializer — see get_unique_error_message in DRF's
        # field_mapping module.
        if value and User.objects.filter(username=value).exists():
            raise serializers.ValidationError("user with this username already exists.")
        return value

    def validate(self, attrs):
        if not attrs.get("username"):
            attrs["username"] = generate_unique_username(attrs["email"])

        # Run Django's full AUTH_PASSWORD_VALIDATORS chain (settings.py) —
        # not just a minimum-length check — including
        # UserAttributeSimilarityValidator, which needs a user-shaped
        # object to compare the password against. Built in-memory, never
        # saved: this request has no real user yet.
        candidate_user = User(
            email=attrs["email"],
            username=attrs["username"],
            first_name=attrs.get("first_name", ""),
            last_name=attrs.get("last_name", ""),
        )
        try:
            validate_password(attrs["password"], user=candidate_user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})

        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        # `set_password` hashes via Django's configured hasher (PBKDF2 by
        # default) — the password is never stored or returned in the clear.
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    """POST /api/auth/login/ — docs/api-design.md §2.2, issue #23.

    Input validation only: presence and basic shape of email/password.
    Credential verification itself happens in the view via `authenticate()`,
    not here — a serializer-level check would need direct DB/password
    access that belongs with the authentication call, not validation.
    """

    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False, write_only=True)


class UserSerializer(serializers.ModelSerializer):
    """Read-only public user representation.

    Shared by login's 200 response and (per docs/api-design.md §2.4) the
    future GET /api/auth/me/ (#26) — both describe "the current user" in
    exactly this shape, so there's one definition of it rather than two
    that could drift apart.
    """

    class Meta:
        model = User
        fields = ["id", "email", "username", "first_name", "last_name", "is_active", "created_at", "updated_at"]
        read_only_fields = fields
