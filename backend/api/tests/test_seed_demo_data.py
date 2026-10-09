from decimal import Decimal
from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from api.management.commands.seed_demo_data import (
    DEMO_EMAIL,
    DEMO_PASSWORD,
    DEMO_USERNAME,
)
from api.models import Budget, Category, Expense, User


class SeedDemoDataCommandTests(TestCase):
    @override_settings(DEBUG=True)
    def test_creates_synthetic_demo_account_and_coherent_data(self):
        output = StringIO()

        call_command("seed_demo_data", stdout=output)

        user = User.objects.get(email=DEMO_EMAIL)
        self.assertEqual(user.username, DEMO_USERNAME)
        self.assertEqual(user.first_name, "Demo")
        self.assertEqual(user.last_name, "User")
        self.assertTrue(user.check_password(DEMO_PASSWORD))
        self.assertGreaterEqual(Category.objects.filter(user=user).count(), 5)
        self.assertEqual(Expense.objects.filter(user=user).count(), 7)
        self.assertEqual(Budget.objects.filter(user=user).count(), 5)
        self.assertTrue(
            all(
                expense.date <= timezone.localdate()
                for expense in Expense.objects.filter(user=user)
            )
        )
        self.assertEqual(
            Expense.objects.get(user=user, description="Weekly groceries").amount,
            Decimal("42.50"),
        )
        self.assertIn("demo@cashmire.example", output.getvalue())

    @override_settings(DEBUG=True)
    def test_running_command_twice_does_not_duplicate_demo_data(self):
        call_command("seed_demo_data", stdout=StringIO())
        call_command("seed_demo_data", stdout=StringIO())

        user = User.objects.get(email=DEMO_EMAIL)
        self.assertEqual(User.objects.filter(email=DEMO_EMAIL).count(), 1)
        self.assertEqual(Expense.objects.filter(user=user).count(), 7)
        self.assertEqual(Budget.objects.filter(user=user).count(), 5)

    @override_settings(DEBUG=True)
    def test_does_not_reset_an_existing_demo_account_password(self):
        user = User.objects.create_user(
            username=DEMO_USERNAME,
            email=DEMO_EMAIL,
            password="A previously changed password",
        )

        call_command("seed_demo_data", stdout=StringIO())

        user.refresh_from_db()
        self.assertTrue(user.check_password("A previously changed password"))
        self.assertFalse(user.check_password(DEMO_PASSWORD))

    @override_settings(DEBUG=False)
    def test_refuses_to_seed_when_debug_is_disabled(self):
        with self.assertRaisesMessage(
            CommandError,
            "Demo data can only be seeded when DJANGO_DEBUG=true.",
        ):
            call_command("seed_demo_data", stdout=StringIO())

        self.assertFalse(User.objects.filter(email=DEMO_EMAIL).exists())
