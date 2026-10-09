from calendar import monthrange
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from api.models import Budget, Category, Expense, User


DEMO_EMAIL = "demo@cashmire.example"
DEMO_USERNAME = "cashmire-demo"
DEMO_PASSWORD = "CashmireDemo2026!"


class Command(BaseCommand):
    help = "Create a synthetic demo account with realistic expenses and budgets."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "Demo data can only be seeded when DJANGO_DEBUG=true."
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

        category_descriptions = {
            "Alimentation": "Courses, nourriture et boissons.",
            "Transport": "Transports en commun et déplacements.",
            "Logement": "Loyer et charges du logement.",
            "Loisirs": "Activités et sorties.",
            "Divertissement": "Films, musique et abonnements.",
        }
        categories = {
            name: Category.objects.get_or_create(
                user=user,
                name=name,
                defaults={"description": description},
            )[0]
            for name, description in category_descriptions.items()
        }

        today = timezone.localdate()
        period_start = today.replace(day=1)
        period_end = today.replace(day=monthrange(today.year, today.month)[1])
        expense_rows = (
            ("Alimentation", "Weekly groceries", "42.50", 1),
            ("Alimentation", "Market produce", "38.25", 3),
            ("Transport", "Monthly transit pass", "24.00", 2),
            ("Logement", "Monthly rent contribution", "780.00", 1),
            ("Loisirs", "Museum and coffee", "32.00", 4),
            ("Loisirs", "Cinema tickets", "45.50", 5),
            ("Divertissement", "Music subscription", "18.99", 2),
        )
        for category_name, description, amount, day in expense_rows:
            expense_date = date(
                today.year,
                today.month,
                min(day, today.day),
            )
            Expense.objects.update_or_create(
                user=user,
                description=description,
                defaults={
                    "category": categories[category_name],
                    "amount": Decimal(amount),
                    "date": expense_date,
                },
            )

        budget_rows = (
            ("Alimentation", "350.00"),
            ("Transport", "90.00"),
            ("Logement", "950.00"),
            ("Loisirs", "120.00"),
            ("Divertissement", "35.00"),
        )
        for category_name, amount in budget_rows:
            Budget.objects.update_or_create(
                user=user,
                category=categories[category_name],
                period_start=period_start,
                period_end=period_end,
                defaults={
                    "amount": Decimal(amount),
                    "alert_threshold": Decimal("80.00"),
                },
            )

        account_status = "created" if user_created else "already existed"
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo account {DEMO_EMAIL} {account_status}; "
                f"{len(categories)} categories, {len(expense_rows)} expenses, "
                f"and {len(budget_rows)} budgets are ready for "
                f"{period_start:%B %Y}."
            )
        )
        if user_created:
            self.stdout.write(f"Initial demo password: {DEMO_PASSWORD}")
