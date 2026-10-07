from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Cashmire's user account — docs/erd.md USER entity (issue #20).

    Subclasses Django's `AbstractUser` rather than starting from scratch:
    that already provides `username` (unique, required), `first_name`,
    `last_name`, `is_active` (default True), and the hashed `password`
    field the ERD calls for — all exactly as specified. Two things the ERD
    needs that `AbstractUser` doesn't provide on its own:

    - `email` must be unique at the database level (Django's default
      `auth.User` leaves it non-unique) and is what's used to log in.
    - `created_at` / `updated_at` timestamps (`AbstractUser` only has
      `date_joined`, which never updates and isn't quite either of these).

    `USERNAME_FIELD = "email"` makes email the identifier Django's own auth
    machinery (and `createsuperuser`) uses — matching the ERD's "Utilisée
    pour la connexion" note on `email`, and the fact that `docs/mvp-scope.md`'s
    login flow is email + password with no username anywhere in it.

    Handoff to #22 (registration endpoint): `username` stays required and
    unique per the ERD, but the registration form (and `docs/mvp-scope.md`
    §3.1) collects only email + password — nothing supplies a username.
    #22 needs to derive one (e.g. from the email's local part, de-duplicated
    on collision) before calling `create_user`. Not solved here.
    """

    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]
