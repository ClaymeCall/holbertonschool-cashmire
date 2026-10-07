from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from decimal import Decimal


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


class Budget(models.Model):
    user = models.ForeignKey(
        "api.User",
        on_delete=models.CASCADE,
        related_name="budgets",
    )
    category = models.ForeignKey(
        "api.Category",
        on_delete=models.PROTECT,
        related_name="budgets",
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    period_start = models.DateField()
    period_end = models.DateField()
    alert_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        default=Decimal("80.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "category", "period_start", "period_end"],
                name="unique_budget_per_user_category_period",
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="budget_amount_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(period_end__gte=models.F("period_start")),
                name="budget_period_end_gte_start",
            ),
            models.CheckConstraint(
                condition=models.Q(alert_threshold__isnull=True) | models.Q(alert_threshold__gte=0, alert_threshold__lte=100),
                name="budget_alert_threshold_valid_range",
            ),
        ]
        indexes = [
            models.Index(fields=["user"], name="idx_budget_user_id"),
            models.Index(fields=["user", "period_start", "period_end"], name="idx_budget_user_period"),
        ]

    def __str__(self):
        return f"Budget {self.id} — User {self.user.id}, Category {self.category.name}, {self.period_start} to {self.period_end}"
