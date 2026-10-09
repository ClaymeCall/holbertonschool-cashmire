from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from api.management.commands.seed_demo_data import DEMO_EMAIL, DEMO_PASSWORD
from api.management.commands.seed_dev_data import (
    MONTHS_OF_HISTORY,
    SANTE_BUDGET_MONTHS,
    TRANSPORT_OFF_MONTHS,
    VETEMENTS_BUDGET_MONTHS,
)
from api.models import Budget, Expense, User


class SeedDevDataCommandTests(TestCase):
    @override_settings(DEBUG=True)
    def test_creates_demo_account_with_a_year_of_history(self):
        output = StringIO()

        call_command("seed_dev_data", stdout=output)

        user = User.objects.get(email=DEMO_EMAIL)
        self.assertTrue(user.check_password(DEMO_PASSWORD))

        budgets = Budget.objects.filter(user=user)
        expenses = Expense.objects.filter(user=user)
        self.assertTrue(budgets.exists())
        self.assertTrue(expenses.exists())

        distinct_periods = set(budgets.values_list("period_start", flat=True))
        self.assertEqual(len(distinct_periods), MONTHS_OF_HISTORY)

        oldest = min(distinct_periods)
        newest = max(distinct_periods)
        month_span = (newest.year - oldest.year) * 12 + (newest.month - oldest.month)
        self.assertEqual(month_span, MONTHS_OF_HISTORY - 1)
        self.assertIn(DEMO_EMAIL, output.getvalue())

    @override_settings(DEBUG=True)
    def test_transport_is_off_budget_for_some_months_but_still_has_expenses(self):
        call_command("seed_dev_data", stdout=StringIO())

        user = User.objects.get(email=DEMO_EMAIL)
        transport_budgets = Budget.objects.filter(user=user, category__name="Transport")
        transport_expenses = Expense.objects.filter(user=user, category__name="Transport")

        self.assertEqual(
            transport_budgets.count(), MONTHS_OF_HISTORY - len(TRANSPORT_OFF_MONTHS)
        )
        self.assertTrue(transport_expenses.exists())
        distinct_expense_months = {
            (d.year, d.month) for d in transport_expenses.values_list("date", flat=True)
        }
        self.assertEqual(len(distinct_expense_months), MONTHS_OF_HISTORY)

    @override_settings(DEBUG=True)
    def test_divertissement_is_always_off_budget(self):
        call_command("seed_dev_data", stdout=StringIO())

        user = User.objects.get(email=DEMO_EMAIL)
        self.assertEqual(
            Budget.objects.filter(user=user, category__name="Divertissement").count(), 0
        )
        divertissement_expenses = Expense.objects.filter(
            user=user, category__name="Divertissement"
        )
        self.assertGreaterEqual(
            divertissement_expenses.count(),
            MONTHS_OF_HISTORY,
            msg="every month should at least have the streaming subscription expense",
        )
        distinct_expense_months = {
            (d.year, d.month)
            for d in divertissement_expenses.values_list("date", flat=True)
        }
        self.assertEqual(len(distinct_expense_months), MONTHS_OF_HISTORY)

    @override_settings(DEBUG=True)
    def test_sante_and_vetements_are_only_on_budget_for_specific_months(self):
        call_command("seed_dev_data", stdout=StringIO())

        user = User.objects.get(email=DEMO_EMAIL)
        self.assertEqual(
            Budget.objects.filter(user=user, category__name="Santé").count(),
            len(SANTE_BUDGET_MONTHS),
        )
        self.assertEqual(
            Budget.objects.filter(user=user, category__name="Vêtements").count(),
            len(VETEMENTS_BUDGET_MONTHS),
        )

    @override_settings(DEBUG=False)
    def test_refuses_to_seed_when_debug_is_disabled(self):
        with self.assertRaisesMessage(
            CommandError,
            "Sample data can only be seeded when DJANGO_DEBUG=true.",
        ):
            call_command("seed_dev_data", stdout=StringIO())

        self.assertFalse(User.objects.filter(email=DEMO_EMAIL).exists())
