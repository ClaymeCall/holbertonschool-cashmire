import random
from calendar import monthrange
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from api.management.commands.seed_demo_data import (
    DEMO_EMAIL,
    DEMO_PASSWORD,
    DEMO_USERNAME,
)
from api.models import Budget, Category, DEFAULT_CATEGORIES, Expense, User

MONTHS_OF_HISTORY = 12
RNG_SEED = 20260109

# Months (counting back from the current month, 0 = oldest) where Transport
# has no Budget row at all, even though expenses still happen that month.
TRANSPORT_OFF_MONTHS = {3, 7}
# Loisirs starts off-budget and only gets budgeted from this month onward.
LOISIRS_BUDGET_FROM_MONTH = 4
# Santé is only budgeted in a few months with an anticipated medical cost.
SANTE_BUDGET_MONTHS = {2, 6, 9}
# Vêtements is only budgeted for two seasonal clothing-buying months.
VETEMENTS_BUDGET_MONTHS = {8, 11}


def _months_back(end_date, count):
    """Return `count` (year, month) pairs ending at end_date's month, oldest first."""
    months = []
    year, month = end_date.year, end_date.month
    for _ in range(count):
        months.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    months.reverse()
    return months


def _money(rng, low, high):
    return Decimal(f"{rng.uniform(low, high):.2f}")


class Command(BaseCommand):
    help = (
        "Seed a synthetic demo account with a full year of categorized "
        "expenses and budgets, including categories that are only "
        "budgeted ('on budget') for some months and left untracked "
        "('off budget') for others. Intended for a fresh development "
        "database; running it against data that already exists can raise "
        "integrity errors on duplicate budgets."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "Sample data can only be seeded when DJANGO_DEBUG=true."
            )

        user, user_created = User.objects.get_or_create(
            email=DEMO_EMAIL,
            defaults={
                "username": DEMO_USERNAME,
                "first_name": "Demo",
                "last_name": "User",
            },
        )
        if user_created:
            user.set_password(DEMO_PASSWORD)
            user.save(update_fields=["password"])

        default_descriptions = dict(DEFAULT_CATEGORIES)
        category_names = [
            "Logement",
            "Alimentation",
            "Transport",
            "Services",
            "Loisirs",
            "Santé",
            "Vêtements",
            "Divertissement",
            "Épargne",
        ]
        categories = {
            name: Category.objects.get_or_create(
                user=user,
                name=name,
                defaults={"description": default_descriptions.get(name, "")},
            )[0]
            for name in category_names
        }

        today = timezone.localdate()
        months = _months_back(today, MONTHS_OF_HISTORY)
        current_month_index = len(months) - 1

        rng = random.Random(RNG_SEED)
        budgets = []
        expenses = []

        def add_expense(category_name, description, amount, day):
            expenses.append(
                Expense(
                    user=user,
                    category=categories[category_name],
                    amount=amount,
                    description=description,
                    date=date(year, month, day),
                )
            )

        def add_budget(category_name, amount, alert_threshold):
            budgets.append(
                Budget(
                    user=user,
                    category=categories[category_name],
                    amount=amount,
                    period_start=period_start,
                    period_end=period_end,
                    alert_threshold=alert_threshold,
                )
            )

        for month_index, (year, month) in enumerate(months):
            period_start = date(year, month, 1)
            last_day = monthrange(year, month)[1]
            period_end = date(year, month, last_day)
            max_day = (
                min(today.day, last_day)
                if month_index == current_month_index
                else last_day
            )

            def day():
                return rng.randint(1, max_day)

            # Logement — always on budget, with a rent increase halfway through.
            rent = Decimal("780.00") if month_index < 6 else Decimal("820.00")
            add_budget("Logement", rent, Decimal("90.00"))
            add_expense("Logement", "Loyer mensuel", rent, 1)
            add_expense(
                "Logement", "Charges (eau, électricité)", _money(rng, 40, 65), day()
            )

            # Alimentation — always on budget, rising gently over the year.
            add_budget(
                "Alimentation",
                Decimal("320.00") + Decimal(5 * month_index),
                Decimal("80.00"),
            )
            for _ in range(rng.randint(8, 14)):
                description = rng.choice(
                    [
                        "Courses de la semaine",
                        "Marché",
                        "Boulangerie",
                        "Supermarché",
                        "Épicerie de quartier",
                    ]
                )
                add_expense("Alimentation", description, _money(rng, 8, 65), day())

            # Transport — on budget most months, off budget for a couple of them.
            if month_index not in TRANSPORT_OFF_MONTHS:
                add_budget(
                    "Transport",
                    Decimal("75.00") + Decimal(5 * (month_index % 3)),
                    Decimal("85.00"),
                )
            for _ in range(rng.randint(3, 6)):
                description = rng.choice(
                    [
                        "Pass navigo",
                        "Ticket de métro",
                        "Essence",
                        "Trajet VTC",
                        "Parking",
                    ]
                )
                add_expense("Transport", description, _money(rng, 8, 45), day())

            # Services — always on budget, a fixed phone/internet bundle.
            add_budget("Services", Decimal("55.00"), Decimal("95.00"))
            add_expense(
                "Services",
                "Abonnement téléphone et internet",
                _money(rng, 48, 62),
                min(day(), 10) if max_day >= 10 else max_day,
            )

            # Loisirs — off budget at first, then tracked from a given month on.
            if month_index >= LOISIRS_BUDGET_FROM_MONTH:
                add_budget(
                    "Loisirs",
                    Decimal("100.00") + Decimal(3 * (month_index - LOISIRS_BUDGET_FROM_MONTH)),
                    Decimal("75.00"),
                )
            for _ in range(rng.randint(1, 4)):
                description = rng.choice(
                    ["Cinéma", "Concert", "Bowling", "Sortie entre amis", "Musée"]
                )
                add_expense("Loisirs", description, _money(rng, 15, 70), day())

            # Santé — only budgeted for months with an anticipated medical cost.
            if month_index in SANTE_BUDGET_MONTHS:
                add_budget("Santé", _money(rng, 150, 300), Decimal("70.00"))
            if rng.random() < 0.6:
                for _ in range(rng.randint(1, 2)):
                    description = rng.choice(
                        ["Consultation médecin", "Pharmacie", "Dentiste", "Optique"]
                    )
                    add_expense("Santé", description, _money(rng, 20, 250), day())

            # Vêtements — only budgeted for two seasonal clothing-buying months.
            if month_index in VETEMENTS_BUDGET_MONTHS:
                add_budget(
                    "Vêtements",
                    Decimal("180.00") if month_index == min(VETEMENTS_BUDGET_MONTHS) else Decimal("220.00"),
                    Decimal("70.00"),
                )
                for _ in range(rng.randint(2, 4)):
                    description = rng.choice(
                        ["Vêtements d'hiver", "Chaussures", "Manteau", "Vêtements enfant"]
                    )
                    add_expense("Vêtements", description, _money(rng, 25, 90), day())
            elif rng.random() < 0.2:
                add_expense("Vêtements", "Achat vêtements", _money(rng, 15, 40), day())

            # Divertissement — never budgeted, but a recurring subscription expense.
            add_expense(
                "Divertissement",
                "Abonnement streaming",
                Decimal("13.49"),
                min(5, max_day),
            )
            if rng.random() < 0.3:
                description = rng.choice(["Place de cinéma", "Jeu vidéo"])
                add_expense("Divertissement", description, _money(rng, 10, 40), day())

            # Épargne — a steady monthly transfer, always within budget.
            add_budget("Épargne", Decimal("100.00"), Decimal("100.00"))
            add_expense("Épargne", "Virement épargne", Decimal("100.00"), day())

        Budget.objects.bulk_create(budgets)
        Expense.objects.bulk_create(expenses)

        account_status = "created" if user_created else "already existed"
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo account {DEMO_EMAIL} {account_status}; seeded "
                f"{len(budgets)} budgets and {len(expenses)} expenses across "
                f"{MONTHS_OF_HISTORY} months ({months[0][1]}/{months[0][0]} to "
                f"{months[-1][1]}/{months[-1][0]})."
            )
        )
        if user_created:
            self.stdout.write(f"Initial demo password: {DEMO_PASSWORD}")
