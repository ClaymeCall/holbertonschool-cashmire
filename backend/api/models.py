from django.contrib.auth.models import AbstractUser
from django.db import models


DEFAULT_CATEGORIES = (
    ("Alimentation", "Courses, nourriture et boissons."),
    ("Transport", "Transports en commun, carburant et déplacements."),
    ("Logement", "Loyer, charges et entretien du logement."),
    ("Loisirs", "Activités de loisirs et sorties."),
    ("Santé", "Soins médicaux et dépenses de santé."),
    ("Vêtements", "Vêtements et accessoires."),
    ("Éducation", "Formation, livres et fournitures scolaires."),
    ("Divertissement", "Films, musique, jeux et abonnements."),
    ("Services", "Téléphone, internet et services du quotidien."),
    ("Épargne", "Épargne et placements de précaution."),
    ("Investissements", "Investissements et placements financiers."),
    ("Autres", "Dépenses ne correspondant à aucune autre catégorie."),
)


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


class Category(models.Model):
    user = models.ForeignKey(
        "api.User",
        on_delete=models.CASCADE,
        related_name="categories",
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"],
                name="unique_category_name_per_user",
            )
        ]

    def __str__(self):
        return self.name


class Expense(models.Model):
    user = models.ForeignKey(
        "api.User",
        on_delete=models.CASCADE,
        related_name="expenses",
    )
    category = models.ForeignKey(
        "api.Category",
        on_delete=models.PROTECT,
        related_name="expenses",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="expense_amount_positive",
            )
        ]

    def __str__(self):
        return f"{self.amount} on {self.date}"
