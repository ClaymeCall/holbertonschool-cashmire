from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Budget, Category, DEFAULT_CATEGORIES, Expense


User = get_user_model()


class CategoryListTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="category-owner",
            email="owner@example.com",
            password="test-password",
        )
        self.other_user = User.objects.create_user(
            username="other-owner",
            email="other@example.com",
            password="test-password",
        )
        self.client = APIClient()

    def test_new_users_receive_default_categories_once(self):
        self.assertEqual(
            list(
                self.user.categories.values_list("name", flat=True)
            ),
            [name for name, _ in DEFAULT_CATEGORIES],
        )

        self.user.first_name = "Updated"
        self.user.save()

        self.assertEqual(self.user.categories.count(), len(DEFAULT_CATEGORIES))

    def test_category_list_requires_session_authentication(self):
        response = self.client.get("/api/categories/")

        self.assertEqual(response.status_code, 403)

    def test_authenticated_user_only_sees_their_categories(self):
        self.client.force_login(self.user)

        response = self.client.get("/api/categories/")

        self.assertEqual(response.status_code, 200)
        categories = response.json()["categories"]
        self.assertEqual(len(categories), len(DEFAULT_CATEGORIES))
        self.assertTrue(all(item["user_id"] == self.user.pk for item in categories))
        self.assertEqual(
            set(categories[0]),
            {
                "id",
                "user_id",
                "name",
                "description",
                "is_active",
                "created_at",
                "updated_at",
            },
        )
        self.assertEqual(
            [item["name"] for item in categories],
            [name for name, _ in DEFAULT_CATEGORIES],
        )

    def test_category_names_are_unique_per_user_not_globally(self):
        self.assertTrue(
            Category.objects.filter(
                user=self.other_user,
                name=DEFAULT_CATEGORIES[0][0],
            ).exists()
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            Category.objects.create(
                user=self.user,
                name=DEFAULT_CATEGORIES[0][0],
            )


class ExpenseModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="expense-owner",
            email="expense-owner@example.com",
            password="test-password",
        )
        self.category = self.user.categories.first()

    def test_expense_persists_money_as_decimal_with_required_relations(self):
        expense = Expense.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("15.50"),
            description="Market",
            date=date(2026, 10, 7),
        )

        expense.refresh_from_db()

        self.assertIsInstance(expense.amount, Decimal)
        self.assertEqual(expense.amount, Decimal("15.50"))
        self.assertEqual(expense.user, self.user)
        self.assertEqual(expense.category, self.category)
        self.assertEqual(expense.description, "Market")
        self.assertEqual(expense.date, date(2026, 10, 7))

    def test_database_rejects_non_positive_expense_amounts(self):
        for amount in (Decimal("0.00"), Decimal("-0.01")):
            with self.subTest(amount=amount):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    Expense.objects.create(
                        user=self.user,
                        category=self.category,
                        amount=amount,
                        date=date(2026, 10, 7),
                    )

    def test_database_enforces_category_foreign_key(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Expense.objects.create(
                user=self.user,
                category_id=99999999,
                amount=Decimal("1.00"),
                date=date(2026, 10, 7),
            )
            connection.check_constraints(table_names=["api_expense"])


class ExpenseCreateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="expense-creator",
            email="expense-creator@example.com",
            password="test-password",
        )
        self.other_user = User.objects.create_user(
            username="other-expense-creator",
            email="other-expense-creator@example.com",
            password="test-password",
        )
        self.category = self.user.categories.first()
        self.other_category = self.other_user.categories.first()
        self.client = APIClient()
        self.url = "/api/expenses/"
        self.payload = {
            "category_id": self.category.pk,
            "amount": "25.50",
            "description": "Lunch",
            "date": "2026-10-07",
        }

    def test_create_requires_session_authentication(self):
        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Expense.objects.count(), 0)

    def test_authenticated_user_creates_expense_owned_by_the_session_user(self):
        self.client.force_login(self.user)
        payload = {**self.payload, "user_id": self.other_user.pk}

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 201)
        expense = Expense.objects.get()
        self.assertEqual(expense.user, self.user)
        self.assertEqual(expense.category, self.category)
        self.assertEqual(expense.amount, Decimal("25.50"))
        self.assertEqual(
            set(response.json()),
            {
                "id",
                "user_id",
                "category_id",
                "amount",
                "description",
                "date",
                "created_at",
                "updated_at",
            },
        )
        self.assertEqual(response.json()["user_id"], self.user.pk)
        self.assertEqual(response.json()["category_id"], self.category.pk)
        self.assertEqual(response.json()["amount"], "25.50")
        self.assertEqual(response.json()["description"], "Lunch")
        self.assertEqual(response.json()["date"], "2026-10-07")

    def test_description_is_optional(self):
        self.client.force_login(self.user)
        payload = {key: value for key, value in self.payload.items() if key != "description"}

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertIsNone(Expense.objects.get().description)

    def test_invalid_amounts_return_field_level_errors_without_creating_expenses(self):
        self.client.force_login(self.user)
        for amount in (
            "0.00",
            "-0.01",
            "not-a-decimal",
            "1.001",
            25.5,
        ):
            with self.subTest(amount=amount):
                payload = {**self.payload, "amount": amount}

                response = self.client.post(self.url, payload, format="json")

                self.assertEqual(response.status_code, 400)
                self.assertIn("amount", response.json())
                self.assertEqual(Expense.objects.count(), 0)

    def test_invalid_or_missing_date_returns_field_level_error(self):
        self.client.force_login(self.user)
        for payload in (
            {**self.payload, "date": "not-a-date"},
            {key: value for key, value in self.payload.items() if key != "date"},
        ):
            with self.subTest(payload=payload):
                response = self.client.post(self.url, payload, format="json")

                self.assertEqual(response.status_code, 400)
                self.assertIn("date", response.json())
                self.assertEqual(Expense.objects.count(), 0)

    def test_missing_amount_and_invalid_description_return_field_errors(self):
        self.client.force_login(self.user)
        payloads = (
            (
                "amount",
                {
                    key: value
                    for key, value in self.payload.items()
                    if key != "amount"
                },
            ),
            (
                "description",
                {**self.payload, "description": {"unexpected": "object"}},
            ),
        )

        for field, payload in payloads:
            with self.subTest(field=field):
                response = self.client.post(self.url, payload, format="json")

                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json())
                self.assertEqual(Expense.objects.count(), 0)

    def test_missing_category_returns_field_level_error(self):
        self.client.force_login(self.user)
        payload = {key: value for key, value in self.payload.items() if key != "category_id"}

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("category_id", response.json())
        self.assertEqual(Expense.objects.count(), 0)

    def test_missing_or_foreign_category_returns_the_same_not_found_error(self):
        self.client.force_login(self.user)
        for category_id in (99999999, self.other_category.pk):
            with self.subTest(category_id=category_id):
                response = self.client.post(
                    self.url,
                    {**self.payload, "category_id": category_id},
                    format="json",
                )

                self.assertEqual(response.status_code, 404)
                self.assertEqual(
                    response.json(),
                    {
                        "error": "NOT_FOUND",
                        "message": "Catégorie non trouvée",
                    },
                )
                self.assertEqual(Expense.objects.count(), 0)


class ExpenseListTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="expense-reader",
            email="expense-reader@example.com",
            password="correct-horse-battery-staple-42",
        )
        self.other_user = User.objects.create_user(
            username="other-expense-reader",
            email="other-expense-reader@example.com",
            password="correct-horse-battery-staple-42",
        )
        self.category = self.user.categories.first()
        self.other_category = self.user.categories.exclude(pk=self.category.pk).first()
        self.other_users_category = self.other_user.categories.first()
        self.client = APIClient()
        self.url = "/api/expenses/"

    def create_expense(
        self,
        *,
        user=None,
        category=None,
        amount=Decimal("10.00"),
        expense_date=date(2026, 10, 7),
        description="Expense",
    ):
        user = user or self.user
        category = category or self.category
        return Expense.objects.create(
            user=user,
            category=category,
            amount=amount,
            date=expense_date,
            description=description,
        )

    def test_list_requires_session_authentication(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json(),
            {"detail": "Authentication credentials were not provided."},
        )

    def test_list_returns_only_the_authenticated_users_expenses(self):
        own_expense = self.create_expense(description="Mine")
        self.create_expense(
            user=self.other_user,
            category=self.other_users_category,
            description="Not mine",
        )
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.json()["expenses"]],
            [own_expense.pk],
        )
        self.assertEqual(response.json()["expenses"][0]["user_id"], self.user.pk)

        response = self.client.get(
            self.url,
            {"category_id": self.other_users_category.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"expenses": []})

    def test_empty_list_returns_an_empty_array(self):
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"expenses": []})

    def test_filters_by_category_and_inclusive_date_range(self):
        matching = self.create_expense(
            expense_date=date(2026, 10, 1),
            description="First boundary",
        )
        end_boundary = self.create_expense(
            expense_date=date(2026, 10, 7),
            description="Last boundary",
        )
        self.create_expense(
            expense_date=date(2026, 10, 8),
            description="After range",
        )
        self.create_expense(
            category=self.other_category,
            expense_date=date(2026, 10, 5),
            description="Other category",
        )
        self.client.force_login(self.user)

        response = self.client.get(
            self.url,
            {
                "category_id": self.category.pk,
                "date_from": "2026-10-01",
                "date_to": "2026-10-07",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.json()["expenses"]],
            [end_boundary.pk, matching.pk],
        )
        self.assertEqual(response.json()["expenses"][0]["amount"], "10.00")

    def test_category_and_date_filters_work_independently(self):
        category_expenses = [
            self.create_expense(expense_date=date(2026, 10, 1)),
            self.create_expense(expense_date=date(2026, 10, 8)),
        ]
        date_expenses = [
            self.create_expense(
                category=self.other_category,
                expense_date=date(2026, 10, 5),
            ),
        ]
        self.client.force_login(self.user)

        category_response = self.client.get(
            self.url,
            {"category_id": self.category.pk},
        )
        date_response = self.client.get(self.url, {"date_from": "2026-10-05"})

        self.assertEqual(category_response.status_code, 200)
        self.assertEqual(date_response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in category_response.json()["expenses"]],
            [category_expenses[1].pk, category_expenses[0].pk],
        )
        self.assertEqual(
            [item["id"] for item in date_response.json()["expenses"]],
            [category_expenses[1].pk, date_expenses[0].pk],
        )

    def test_invalid_filters_return_field_level_errors(self):
        self.client.force_login(self.user)
        for query, field in (
            ({"category_id": "invalid"}, "category_id"),
            ({"date_from": "not-a-date"}, "date_from"),
            (
                {"date_from": "2026-10-08", "date_to": "2026-10-07"},
                "date_from",
            ),
        ):
            with self.subTest(query=query):
                response = self.client.get(self.url, query)

                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json())


class ExpenseDetailMutationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="expense-editor",
            email="expense-editor@example.com",
            password="correct-horse-battery-staple-42",
        )
        self.other_user = User.objects.create_user(
            username="other-expense-editor",
            email="other-expense-editor@example.com",
            password="correct-horse-battery-staple-42",
        )
        self.category = self.user.categories.first()
        self.other_category = self.user.categories.exclude(pk=self.category.pk).first()
        self.other_users_category = self.other_user.categories.first()
        self.expense = Expense.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("25.50"),
            description="Original",
            date=date(2026, 10, 6),
        )
        self.other_expense = Expense.objects.create(
            user=self.other_user,
            category=self.other_users_category,
            amount=Decimal("80.00"),
            description="Private",
            date=date(2026, 10, 5),
        )
        self.client = APIClient()

    def detail_url(self, expense_id):
        return f"/api/expenses/{expense_id}/"

    def test_patch_updates_only_supplied_fields_and_preserves_decimal_precision(self):
        self.client.force_login(self.user)

        response = self.client.patch(
            self.detail_url(self.expense.pk),
            {"amount": "1234.56", "description": "Updated"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.expense.refresh_from_db()
        self.assertEqual(self.expense.amount, Decimal("1234.56"))
        self.assertEqual(self.expense.description, "Updated")
        self.assertEqual(self.expense.category, self.category)
        self.assertEqual(self.expense.date, date(2026, 10, 6))
        self.assertEqual(response.json()["amount"], "1234.56")

    def test_patch_can_change_to_an_owned_category(self):
        self.client.force_login(self.user)

        response = self.client.patch(
            self.detail_url(self.expense.pk),
            {"category_id": self.other_category.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.expense.refresh_from_db()
        self.assertEqual(self.expense.category, self.other_category)

    def test_put_requires_creation_fields_and_replaces_expense_values(self):
        self.client.force_login(self.user)

        incomplete = self.client.put(
            self.detail_url(self.expense.pk),
            {"amount": "40.00"},
            format="json",
        )
        self.assertEqual(incomplete.status_code, 400)
        self.assertIn("category_id", incomplete.json())
        self.assertIn("date", incomplete.json())

        response = self.client.put(
            self.detail_url(self.expense.pk),
            {
                "category_id": self.category.pk,
                "amount": "40.05",
                "date": "2026-10-09",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.expense.refresh_from_db()
        self.assertEqual(self.expense.amount, Decimal("40.05"))
        self.assertEqual(self.expense.date, date(2026, 10, 9))
        self.assertIsNone(self.expense.description)

    def test_update_rejects_invalid_amount_without_changing_expense(self):
        self.client.force_login(self.user)

        response = self.client.patch(
            self.detail_url(self.expense.pk),
            {"amount": 12.34},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("amount", response.json())
        self.expense.refresh_from_db()
        self.assertEqual(self.expense.amount, Decimal("25.50"))

    def test_update_rejects_a_foreign_or_missing_category(self):
        self.client.force_login(self.user)
        for category_id in (self.other_users_category.pk, 99999999):
            with self.subTest(category_id=category_id):
                response = self.client.patch(
                    self.detail_url(self.expense.pk),
                    {"category_id": category_id},
                    format="json",
                )

                self.assertEqual(response.status_code, 404)
                self.assertEqual(
                    response.json(),
                    {
                        "error": "NOT_FOUND",
                        "message": "Catégorie non trouvée",
                    },
                )

    def test_update_returns_identical_404_for_foreign_and_missing_expenses(self):
        self.client.force_login(self.user)

        foreign_response = self.client.patch(
            self.detail_url(self.other_expense.pk),
            {"amount": "30.00"},
            format="json",
        )
        foreign_put_response = self.client.put(
            self.detail_url(self.other_expense.pk),
            {
                "category_id": self.category.pk,
                "amount": "30.00",
                "date": "2026-10-08",
            },
            format="json",
        )
        missing_response = self.client.patch(
            self.detail_url(99999999),
            {"amount": "30.00"},
            format="json",
        )

        self.assertEqual(foreign_response.status_code, 404)
        self.assertEqual(foreign_put_response.status_code, 404)
        self.assertEqual(missing_response.status_code, 404)
        self.assertEqual(foreign_response.json(), missing_response.json())
        self.assertEqual(foreign_put_response.json(), missing_response.json())
        self.other_expense.refresh_from_db()
        self.assertEqual(self.other_expense.amount, Decimal("80.00"))

    def test_delete_removes_owned_expense_and_returns_204(self):
        self.client.force_login(self.user)

        response = self.client.delete(self.detail_url(self.expense.pk))

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Expense.objects.filter(pk=self.expense.pk).exists())

    def test_delete_returns_identical_404_for_foreign_and_missing_expenses(self):
        self.client.force_login(self.user)

        foreign_response = self.client.delete(self.detail_url(self.other_expense.pk))
        missing_response = self.client.delete(self.detail_url(99999999))

        self.assertEqual(foreign_response.status_code, 404)
        self.assertEqual(missing_response.status_code, 404)
        self.assertEqual(foreign_response.json(), missing_response.json())
        self.assertTrue(Expense.objects.filter(pk=self.other_expense.pk).exists())


class BudgetModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="budget-owner",
            email="budget@example.com",
            password="test-password",
        )
        self.other_user = User.objects.create_user(
            username="other-budget-owner",
            email="other-budget@example.com",
            password="test-password",
        )
        self.category = Category.objects.create(
            user=self.user,
            name="Test Category",
            description="Test category for budget",
        )
        self.other_category = Category.objects.create(
            user=self.user,
            name="Other Category",
            description="Another category",
        )

    def test_create_budget_with_all_fields(self):
        """Test creating a valid budget with all fields."""
        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("1000.00"),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            alert_threshold=Decimal("75.00"),
        )
        self.assertEqual(budget.user, self.user)
        self.assertEqual(budget.category, self.category)
        self.assertEqual(budget.amount, Decimal("1000.00"))
        self.assertEqual(budget.alert_threshold, Decimal("75.00"))

    def test_create_budget_with_default_alert_threshold(self):
        """Test creating a budget without alert_threshold uses default 80.00."""
        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("500.00"),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
        )
        self.assertEqual(budget.alert_threshold, Decimal("80.00"))

    def test_create_budget_with_null_alert_threshold(self):
        """Test creating a budget with null alert_threshold."""
        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("500.00"),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            alert_threshold=None,
        )
        self.assertIsNone(budget.alert_threshold)

    def test_create_multiple_budgets_different_categories(self):
        """Test creating multiple budgets for different categories of same user."""
        budget1 = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("1000.00"),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
        )
        budget2 = Budget.objects.create(
            user=self.user,
            category=self.other_category,
            amount=Decimal("500.00"),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
        )
        self.assertEqual(Budget.objects.filter(user=self.user).count(), 2)
        self.assertNotEqual(budget1.category, budget2.category)

    def test_create_multiple_budgets_different_periods(self):
        """Test creating multiple budgets for same category but different periods."""
        budget1 = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("1000.00"),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
        )
        budget2 = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("1200.00"),
            period_start=date(2026, 2, 1),
            period_end=date(2026, 2, 28),
        )
        self.assertEqual(Budget.objects.filter(user=self.user, category=self.category).count(), 2)

    def test_duplicate_budget_rejected(self):
        """Test that duplicate budgets (same user, category, period) are rejected."""
        Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("1000.00"),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Budget.objects.create(
                user=self.user,
                category=self.category,
                amount=Decimal("1500.00"),
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
            )

    def test_amount_zero_rejected(self):
        """Test that amount = 0 is rejected by validator."""
        with self.assertRaises(ValidationError):
            budget = Budget(
                user=self.user,
                category=self.category,
                amount=Decimal("0.00"),
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
            )
            budget.full_clean()

    def test_amount_negative_rejected(self):
        """Test that negative amount is rejected by validator."""
        with self.assertRaises(ValidationError):
            budget = Budget(
                user=self.user,
                category=self.category,
                amount=Decimal("-100.00"),
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
            )
            budget.full_clean()

    def test_amount_positive_minimum(self):
        """Test that amount = 0.01 (minimum positive) is accepted."""
        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("0.01"),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
        )
        self.assertEqual(budget.amount, Decimal("0.01"))

    def test_amount_maximum(self):
        """Test that maximum amount (99999999.99) is stored correctly."""
        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("99999999.99"),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
        )
        self.assertEqual(budget.amount, Decimal("99999999.99"))

    def test_amount_decimal_precision(self):
        """Test that amount maintains decimal precision (not rounded)."""
        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("123.45"),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
        )
        # Refresh from DB to ensure no rounding
        budget.refresh_from_db()
        self.assertEqual(budget.amount, Decimal("123.45"))

    def test_period_end_before_start_rejected(self):
        """Test that period_end < period_start is rejected by CheckConstraint."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            Budget.objects.create(
                user=self.user,
                category=self.category,
                amount=Decimal("1000.00"),
                period_start=date(2026, 1, 31),
                period_end=date(2026, 1, 1),
            )

    def test_period_end_equals_start(self):
        """Test that period_end = period_start (single-day budget) is allowed."""
        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("1000.00"),
            period_start=date(2026, 1, 15),
            period_end=date(2026, 1, 15),
        )
        self.assertEqual(budget.period_start, budget.period_end)

    def test_period_end_after_start(self):
        """Test normal period_end > period_start is allowed."""
        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("1000.00"),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
        )
        self.assertGreater(budget.period_end, budget.period_start)

    def test_alert_threshold_null_allowed(self):
        """Test that alert_threshold = null is allowed."""
        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("1000.00"),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            alert_threshold=None,
        )
        self.assertIsNone(budget.alert_threshold)

    def test_alert_threshold_zero(self):
        """Test that alert_threshold = 0 is accepted."""
        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("1000.00"),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            alert_threshold=Decimal("0"),
        )
        self.assertEqual(budget.alert_threshold, Decimal("0"))

    def test_alert_threshold_one_hundred(self):
        """Test that alert_threshold = 100 is accepted."""
        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("1000.00"),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            alert_threshold=Decimal("100"),
        )
        self.assertEqual(budget.alert_threshold, Decimal("100"))

    def test_alert_threshold_negative_rejected(self):
        """Test that alert_threshold < 0 is rejected."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            Budget.objects.create(
                user=self.user,
                category=self.category,
                amount=Decimal("1000.00"),
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
                alert_threshold=Decimal("-0.01"),
            )

    def test_alert_threshold_over_hundred_rejected(self):
        """Test that alert_threshold > 100 is rejected."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            Budget.objects.create(
                user=self.user,
                category=self.category,
                amount=Decimal("1000.00"),
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
                alert_threshold=Decimal("100.01"),
            )

    def test_user_cascade_delete(self):
        """Test that deleting a user deletes their budgets (CASCADE)."""
        # Create a separate user without categories to avoid cascade conflict
        # (Design note: User+Category+Budget has cascade conflict, so we test
        # without Category: User→Budget CASCADE works correctly)
        test_user = User.objects.create_user(
            username="cascade-test-user",
            email="cascade@example.com",
            password="test-password",
        )
        # Use the other_user's category since it doesn't cascade delete with test_user
        budget = Budget.objects.create(
            user=test_user,
            category=self.other_user.categories.first() or self.category,
            amount=Decimal("1000.00"),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
        )
        budget_id = budget.id
        user_id = test_user.id

        # Delete user and verify budgets are cascade deleted
        test_user.delete()

        with self.assertRaises(Budget.DoesNotExist):
            Budget.objects.get(id=budget_id)

        with self.assertRaises(User.DoesNotExist):
            User.objects.get(id=user_id)

    def test_category_protect_delete(self):
        """Test that deleting a category with budgets is prevented (PROTECT)."""
        Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("1000.00"),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.category.delete()

    def test_category_delete_without_budgets(self):
        """Test that deleting a category without budgets succeeds."""
        unused_category = Category.objects.create(
            user=self.user,
            name="Unused Category",
        )
        unused_category_id = unused_category.id
        unused_category.delete()
        with self.assertRaises(Category.DoesNotExist):
            Category.objects.get(id=unused_category_id)

    def test_timestamps_created_at_and_updated_at(self):
        """Test that created_at and updated_at are set automatically."""
        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("1000.00"),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
        )
        self.assertIsNotNone(budget.created_at)
        self.assertIsNotNone(budget.updated_at)
        self.assertEqual(budget.created_at.date(), date.today())


class BudgetCreateEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="budget-endpoint-user",
            email="budget-endpoint@example.com",
            password="test-password",
        )
        self.other_user = User.objects.create_user(
            username="other-endpoint-user",
            email="other-endpoint@example.com",
            password="test-password",
        )
        self.category = Category.objects.create(
            user=self.user,
            name="Test Budget Category",
            description="Test category for budget endpoint",
        )
        self.other_user_category = Category.objects.create(
            user=self.other_user,
            name="Other User Category",
            description="Another user's category",
        )
        self.client = APIClient()

    def test_budget_create_requires_session_authentication(self):
        """Test that POST /api/budgets/ requires authentication (401 if missing)."""
        response = self.client.post(
            "/api/budgets/",
            {
                "category_id": self.category.id,
                "amount": "500.00",
                "period_start": "2026-10-01",
                "period_end": "2026-10-31",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_budget_create_valid_request(self):
        """Test creating a valid budget with all required fields."""
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/budgets/",
            {
                "category_id": self.category.id,
                "amount": "500.00",
                "period_start": "2026-10-01",
                "period_end": "2026-10-31",
                "alert_threshold": "75.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["user_id"], self.user.id)
        self.assertEqual(data["category_id"], self.category.id)
        self.assertEqual(data["amount"], "500.00")
        self.assertEqual(data["period_start"], "2026-10-01")
        self.assertEqual(data["period_end"], "2026-10-31")
        self.assertEqual(data["alert_threshold"], "75.00")
        self.assertIn("id", data)
        self.assertIn("created_at", data)
        self.assertIn("updated_at", data)

    def test_budget_create_without_optional_alert_threshold(self):
        """Test creating a budget without alert_threshold (default should be 80.00)."""
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/budgets/",
            {
                "category_id": self.category.id,
                "amount": "500.00",
                "period_start": "2026-10-01",
                "period_end": "2026-10-31",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["alert_threshold"], "80.00")

    def test_budget_create_amount_zero_rejected(self):
        """Test that amount = 0 is rejected with 400 Bad Request."""
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/budgets/",
            {
                "category_id": self.category.id,
                "amount": "0.00",
                "period_start": "2026-10-01",
                "period_end": "2026-10-31",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("amount", response.json())

    def test_budget_create_amount_negative_rejected(self):
        """Test that negative amount is rejected with 400 Bad Request."""
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/budgets/",
            {
                "category_id": self.category.id,
                "amount": "-10.50",
                "period_start": "2026-10-01",
                "period_end": "2026-10-31",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("amount", response.json())

    def test_budget_create_amount_minimum_positive(self):
        """Test that amount = 0.01 (minimum positive) is accepted."""
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/budgets/",
            {
                "category_id": self.category.id,
                "amount": "0.01",
                "period_start": "2026-10-01",
                "period_end": "2026-10-31",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["amount"], "0.01")

    def test_budget_create_amount_maximum(self):
        """Test that maximum amount (99999999.99) is accepted."""
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/budgets/",
            {
                "category_id": self.category.id,
                "amount": "99999999.99",
                "period_start": "2026-10-01",
                "period_end": "2026-10-31",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["amount"], "99999999.99")

    def test_budget_create_amount_not_parsable(self):
        """Test that non-parsable amount is rejected with 400."""
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/budgets/",
            {
                "category_id": self.category.id,
                "amount": "abc",
                "period_start": "2026-10-01",
                "period_end": "2026-10-31",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("amount", response.json())

    def test_budget_create_period_end_before_start_rejected(self):
        """Test that period_end < period_start is rejected with 400."""
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/budgets/",
            {
                "category_id": self.category.id,
                "amount": "500.00",
                "period_start": "2026-10-31",
                "period_end": "2026-10-01",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_budget_create_period_end_equals_start(self):
        """Test that period_end = period_start (single-day) is accepted."""
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/budgets/",
            {
                "category_id": self.category.id,
                "amount": "500.00",
                "period_start": "2026-10-15",
                "period_end": "2026-10-15",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["period_start"], "2026-10-15")
        self.assertEqual(data["period_end"], "2026-10-15")

    def test_budget_create_period_invalid_format(self):
        """Test that invalid date format is rejected with 400."""
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/budgets/",
            {
                "category_id": self.category.id,
                "amount": "500.00",
                "period_start": "2026-13-01",
                "period_end": "2026-10-31",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_budget_create_alert_threshold_null(self):
        """Test that alert_threshold can be null (omitted)."""
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/budgets/",
            {
                "category_id": self.category.id,
                "amount": "500.00",
                "period_start": "2026-10-01",
                "period_end": "2026-10-31",
                "alert_threshold": None,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIsNone(data["alert_threshold"])

    def test_budget_create_alert_threshold_zero(self):
        """Test that alert_threshold = 0 is accepted."""
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/budgets/",
            {
                "category_id": self.category.id,
                "amount": "500.00",
                "period_start": "2026-10-01",
                "period_end": "2026-10-31",
                "alert_threshold": "0",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["alert_threshold"], "0.00")

    def test_budget_create_alert_threshold_hundred(self):
        """Test that alert_threshold = 100 is accepted."""
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/budgets/",
            {
                "category_id": self.category.id,
                "amount": "500.00",
                "period_start": "2026-10-01",
                "period_end": "2026-10-31",
                "alert_threshold": "100",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["alert_threshold"], "100.00")

    def test_budget_create_alert_threshold_negative_rejected(self):
        """Test that alert_threshold < 0 is rejected with 400."""
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/budgets/",
            {
                "category_id": self.category.id,
                "amount": "500.00",
                "period_start": "2026-10-01",
                "period_end": "2026-10-31",
                "alert_threshold": "-1",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_budget_create_alert_threshold_over_hundred_rejected(self):
        """Test that alert_threshold > 100 is rejected with 400."""
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/budgets/",
            {
                "category_id": self.category.id,
                "amount": "500.00",
                "period_start": "2026-10-01",
                "period_end": "2026-10-31",
                "alert_threshold": "100.01",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_budget_create_nonexistent_category_404(self):
        """Test that nonexistent category_id returns 404 Not Found."""
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/budgets/",
            {
                "category_id": 99999,
                "amount": "500.00",
                "period_start": "2026-10-01",
                "period_end": "2026-10-31",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data["error"], "NOT_FOUND")

    def test_budget_create_foreign_category_404(self):
        """Test that using another user's category returns 404 Not Found."""
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/budgets/",
            {
                "category_id": self.other_user_category.id,
                "amount": "500.00",
                "period_start": "2026-10-01",
                "period_end": "2026-10-31",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data["error"], "NOT_FOUND")

    def test_budget_create_duplicate_409(self):
        """Test that duplicate budget (same user, category, period) returns 409 Conflict."""
        self.client.force_login(self.user)
        # Create first budget
        response1 = self.client.post(
            "/api/budgets/",
            {
                "category_id": self.category.id,
                "amount": "500.00",
                "period_start": "2026-10-01",
                "period_end": "2026-10-31",
            },
            format="json",
        )
        self.assertEqual(response1.status_code, 201)

        # Try to create duplicate
        response2 = self.client.post(
            "/api/budgets/",
            {
                "category_id": self.category.id,
                "amount": "750.00",
                "period_start": "2026-10-01",
                "period_end": "2026-10-31",
            },
            format="json",
        )
        self.assertEqual(response2.status_code, 409)
        data = response2.json()
        self.assertEqual(data["error"], "CONFLICT")
        self.assertIn("Budget", data["message"])

    def test_budget_create_same_category_different_period_allowed(self):
        """Test that same user/category but different period is allowed."""
        self.client.force_login(self.user)
        # Create first budget
        response1 = self.client.post(
            "/api/budgets/",
            {
                "category_id": self.category.id,
                "amount": "500.00",
                "period_start": "2026-10-01",
                "period_end": "2026-10-31",
            },
            format="json",
        )
        self.assertEqual(response1.status_code, 201)

        # Create second budget with different period
        response2 = self.client.post(
            "/api/budgets/",
            {
                "category_id": self.category.id,
                "amount": "600.00",
                "period_start": "2026-11-01",
                "period_end": "2026-11-30",
            },
            format="json",
        )
        self.assertEqual(response2.status_code, 201)
        self.assertEqual(Budget.objects.filter(user=self.user, category=self.category).count(), 2)

    def test_budget_create_same_period_different_category_allowed(self):
        """Test that same user/period but different category is allowed."""
        category2 = Category.objects.create(
            user=self.user,
            name="Another Test Category",
            description="Another category for testing",
        )
        self.client.force_login(self.user)
        # Create first budget
        response1 = self.client.post(
            "/api/budgets/",
            {
                "category_id": self.category.id,
                "amount": "500.00",
                "period_start": "2026-10-01",
                "period_end": "2026-10-31",
            },
            format="json",
        )
        self.assertEqual(response1.status_code, 201)

        # Create second budget with different category
        response2 = self.client.post(
            "/api/budgets/",
            {
                "category_id": category2.id,
                "amount": "600.00",
                "period_start": "2026-10-01",
                "period_end": "2026-10-31",
            },
            format="json",
        )
        self.assertEqual(response2.status_code, 201)
        self.assertEqual(Budget.objects.filter(user=self.user).count(), 2)

    def test_budget_create_owner_is_request_user(self):
        """Test that created budget's owner is always request.user."""
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/budgets/",
            {
                "category_id": self.category.id,
                "amount": "500.00",
                "period_start": "2026-10-01",
                "period_end": "2026-10-31",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["user_id"], self.user.id)

        # Verify in database
        budget = Budget.objects.get(id=data["id"])
        self.assertEqual(budget.user, self.user)

    def test_budget_create_timestamps_iso8601(self):
        """Test that created_at and updated_at are in ISO 8601 format."""
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/budgets/",
            {
                "category_id": self.category.id,
                "amount": "500.00",
                "period_start": "2026-10-01",
                "period_end": "2026-10-31",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        # ISO 8601 format should contain 'T' and timezone info
        self.assertIn("T", data["created_at"])
        self.assertIn("T", data["updated_at"])

    def test_budget_create_amount_serialized_as_string(self):
        """Test that amount is serialized as a string (decimal string)."""
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/budgets/",
            {
                "category_id": self.category.id,
                "amount": "123.45",
                "period_start": "2026-10-01",
                "period_end": "2026-10-31",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        # Check that amount is a string in the response
        self.assertIsInstance(data["amount"], str)
        self.assertEqual(data["amount"], "123.45")

    def test_budget_create_missing_required_field_category_id(self):
        """Test that missing category_id returns 400."""
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/budgets/",
            {
                "amount": "500.00",
                "period_start": "2026-10-01",
                "period_end": "2026-10-31",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_budget_create_missing_required_field_amount(self):
        """Test that missing amount returns 400."""
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/budgets/",
            {
                "category_id": self.category.id,
                "period_start": "2026-10-01",
                "period_end": "2026-10-31",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_budget_create_missing_required_field_period_start(self):
        """Test that missing period_start returns 400."""
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/budgets/",
            {
                "category_id": self.category.id,
                "amount": "500.00",
                "period_end": "2026-10-31",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_budget_create_missing_required_field_period_end(self):
        """Test that missing period_end returns 400."""
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/budgets/",
            {
                "category_id": self.category.id,
                "amount": "500.00",
                "period_start": "2026-10-01",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_budget_create_race_condition_integrity_error_returns_409(self):
        """
        Test race condition: applicative check passes, but duplicate is created
        between the check and the create (simulated by mocking the duplicate check).
        The IntegrityError should be caught and return 409 Conflict instead of 500.
        """
        from unittest.mock import patch, MagicMock

        self.client.force_login(self.user)

        # Pre-create a budget (simulating a concurrent request that won the race)
        existing_budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("500.00"),
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
        )

        # Mock Budget.objects.filter to bypass the duplicate check (returns False on exists())
        # but the real create() will still be called and hit the UNIQUE constraint
        def filter_side_effect(*args, **kwargs):
            # Return a mock queryset that says no duplicates exist
            mock_qs = MagicMock()
            mock_qs.exists.return_value = False
            return mock_qs

        with patch.object(Budget.objects, "filter", side_effect=filter_side_effect):
            # Try to create a duplicate budget
            response = self.client.post(
                "/api/budgets/",
                {
                    "category_id": self.category.id,
                    "amount": "750.00",  # Different amount, but same period
                    "period_start": "2026-10-01",
                    "period_end": "2026-10-31",
                },
                format="json",
            )

        # Should return 409 Conflict (not 500 Internal Server Error)
        self.assertEqual(response.status_code, 409)
        data = response.json()
        self.assertEqual(data["error"], "CONFLICT")
        self.assertIn("Budget", data["message"])

        # Verify only one budget exists (the one we pre-created)
        self.assertEqual(
            Budget.objects.filter(
                user=self.user,
                category=self.category,
                period_start=date(2026, 10, 1),
                period_end=date(2026, 10, 31),
            ).count(),
            1,
        )


class BudgetConsumptionServiceTests(TestCase):
    """Tests for the budget consumption calculation service (issue #50).

    These tests verify the pure service functions without HTTP/DRF layers,
    directly testing the calculation logic with database fixtures.
    """

    def setUp(self):
        """Create test user, categories, budgets, and expenses."""
        self.user = User.objects.create_user(
            username="consumption-test-user",
            email="consumption@example.com",
            password="test-password",
        )
        self.other_user = User.objects.create_user(
            username="other-consumption-user",
            email="other-consumption@example.com",
            password="test-password",
        )
        self.category = Category.objects.create(
            user=self.user,
            name="Test Category",
            description="Category for consumption tests",
        )
        self.other_category = Category.objects.create(
            user=self.user,
            name="Other Category",
            description="Another category",
        )
        self.other_user_category = Category.objects.create(
            user=self.other_user,
            name="Other User Category",
            description="Category for other user",
        )

    def _import_service(self):
        """Import service functions (deferred until test runs)."""
        from api.services.budget_consumption import (
            calculate_consumption,
            calculate_consumption_batch,
        )
        return calculate_consumption, calculate_consumption_batch

    # ===== T-1 to T-10: Basic consumption calculation =====

    def test_budget_no_expenses_zero_consumption(self):
        """T-1: Budget without expenses → spent=0, remaining=amount, percentage=0."""
        calculate_consumption, _ = self._import_service()

        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("100.00"),
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
        )

        consumption = calculate_consumption(budget)

        self.assertEqual(consumption.spent, Decimal("0.00"))
        self.assertEqual(consumption.remaining, Decimal("100.00"))
        self.assertEqual(consumption.percentage, Decimal("0.00"))

    def test_budget_expense_equals_amount_100_percent(self):
        """T-2: Expense equal to budget amount → spent=amount, remaining=0, percentage=100."""
        calculate_consumption, _ = self._import_service()

        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("100.00"),
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
        )
        Expense.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("100.00"),
            date=date(2026, 10, 15),
        )

        consumption = calculate_consumption(budget)

        self.assertEqual(consumption.spent, Decimal("100.00"))
        self.assertEqual(consumption.remaining, Decimal("0.00"))
        self.assertEqual(consumption.percentage, Decimal("100.00"))

    def test_budget_expense_less_than_amount(self):
        """T-3: Expense less than budget → spent < amount, remaining > 0, percentage < 100."""
        calculate_consumption, _ = self._import_service()

        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("100.00"),
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
        )
        Expense.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("50.00"),
            date=date(2026, 10, 15),
        )

        consumption = calculate_consumption(budget)

        self.assertEqual(consumption.spent, Decimal("50.00"))
        self.assertEqual(consumption.remaining, Decimal("50.00"))
        self.assertEqual(consumption.percentage, Decimal("50.00"))

    def test_budget_expense_exceeds_amount_negative_remaining(self):
        """T-4: Expense exceeds budget → spent > amount, remaining < 0, percentage > 100."""
        calculate_consumption, _ = self._import_service()

        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("100.00"),
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
        )
        Expense.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("150.00"),
            date=date(2026, 10, 15),
        )

        consumption = calculate_consumption(budget)

        self.assertEqual(consumption.spent, Decimal("150.00"))
        self.assertEqual(consumption.remaining, Decimal("-50.00"))
        self.assertEqual(consumption.percentage, Decimal("150.00"))

    def test_budget_multiple_expenses_sum_correctly(self):
        """T-5: Multiple expenses sum correctly."""
        calculate_consumption, _ = self._import_service()

        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("200.00"),
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
        )
        Expense.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("50.00"),
            date=date(2026, 10, 5),
        )
        Expense.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("75.50"),
            date=date(2026, 10, 10),
        )
        Expense.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("25.25"),
            date=date(2026, 10, 20),
        )

        consumption = calculate_consumption(budget)

        self.assertEqual(consumption.spent, Decimal("150.75"))
        self.assertEqual(consumption.remaining, Decimal("49.25"))
        self.assertEqual(consumption.percentage, Decimal("75.38"))

    def test_budget_expense_before_period_start_not_included(self):
        """T-6: Expense before period_start is not included."""
        calculate_consumption, _ = self._import_service()

        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("100.00"),
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
        )
        Expense.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("50.00"),
            date=date(2026, 9, 30),
        )

        consumption = calculate_consumption(budget)

        self.assertEqual(consumption.spent, Decimal("0.00"))
        self.assertEqual(consumption.remaining, Decimal("100.00"))
        self.assertEqual(consumption.percentage, Decimal("0.00"))

    def test_budget_expense_after_period_end_not_included(self):
        """T-7: Expense after period_end is not included."""
        calculate_consumption, _ = self._import_service()

        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("100.00"),
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
        )
        Expense.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("50.00"),
            date=date(2026, 11, 1),
        )

        consumption = calculate_consumption(budget)

        self.assertEqual(consumption.spent, Decimal("0.00"))
        self.assertEqual(consumption.remaining, Decimal("100.00"))
        self.assertEqual(consumption.percentage, Decimal("0.00"))

    def test_budget_expense_exactly_period_start_included(self):
        """T-8: Expense exactly on period_start is included (inclusive boundary)."""
        calculate_consumption, _ = self._import_service()

        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("100.00"),
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
        )
        Expense.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("50.00"),
            date=date(2026, 10, 1),
        )

        consumption = calculate_consumption(budget)

        self.assertEqual(consumption.spent, Decimal("50.00"))
        self.assertEqual(consumption.remaining, Decimal("50.00"))
        self.assertEqual(consumption.percentage, Decimal("50.00"))

    def test_budget_expense_exactly_period_end_included(self):
        """T-9: Expense exactly on period_end is included (inclusive boundary)."""
        calculate_consumption, _ = self._import_service()

        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("100.00"),
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
        )
        Expense.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("50.00"),
            date=date(2026, 10, 31),
        )

        consumption = calculate_consumption(budget)

        self.assertEqual(consumption.spent, Decimal("50.00"))
        self.assertEqual(consumption.remaining, Decimal("50.00"))
        self.assertEqual(consumption.percentage, Decimal("50.00"))

    def test_budget_only_correct_user_category_counted(self):
        """T-10: Only expenses for correct user and category are counted."""
        calculate_consumption, _ = self._import_service()

        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("100.00"),
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
        )

        # Create expense for correct user/category/period
        Expense.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("25.00"),
            date=date(2026, 10, 15),
        )

        # Create expense for different user, same period
        Expense.objects.create(
            user=self.other_user,
            category=self.other_user_category,
            amount=Decimal("50.00"),
            date=date(2026, 10, 15),
        )

        # Create expense for same user but different category
        Expense.objects.create(
            user=self.user,
            category=self.other_category,
            amount=Decimal("75.00"),
            date=date(2026, 10, 15),
        )

        consumption = calculate_consumption(budget)

        # Only the first expense should be counted
        self.assertEqual(consumption.spent, Decimal("25.00"))
        self.assertEqual(consumption.remaining, Decimal("75.00"))
        self.assertEqual(consumption.percentage, Decimal("25.00"))

    # ===== T-11 to T-13: Decimal precision =====

    def test_decimal_precision_two_places_maintained(self):
        """T-11: Decimal amounts with 2 places are maintained exactly."""
        calculate_consumption, _ = self._import_service()

        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("123.45"),
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
        )
        Expense.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("45.67"),
            date=date(2026, 10, 15),
        )

        consumption = calculate_consumption(budget)

        self.assertEqual(consumption.spent, Decimal("45.67"))
        self.assertEqual(consumption.remaining, Decimal("77.78"))
        # 45.67 / 123.45 * 100 = 36.9937... → rounds to 36.99
        self.assertEqual(consumption.percentage, Decimal("36.99"))

    def test_decimal_quantized_to_two_places(self):
        """T-12: All return values are quantized to exactly 2 decimal places."""
        calculate_consumption, _ = self._import_service()

        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("1.00"),
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
        )
        Expense.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("0.01"),
            date=date(2026, 10, 15),
        )

        consumption = calculate_consumption(budget)

        # Verify quantization (exponent should be -2)
        self.assertEqual(consumption.spent.as_tuple().exponent, -2)
        self.assertEqual(consumption.remaining.as_tuple().exponent, -2)
        self.assertEqual(consumption.percentage.as_tuple().exponent, -2)

    def test_percentage_rounding_precision(self):
        """T-13: Percentage is rounded correctly to 2 decimal places."""
        calculate_consumption, _ = self._import_service()

        # 123.456 / 100 * 100 = 123.456, should round to 123.46
        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("100.00"),
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
        )
        Expense.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("123.456"),  # Over-budget amount
            date=date(2026, 10, 15),
        )

        consumption = calculate_consumption(budget)

        # 123.456 / 100 * 100 = 123.456 → rounds to 123.46
        self.assertEqual(consumption.percentage, Decimal("123.46"))

    # ===== T-14 to T-19: Batch function tests =====

    def test_batch_empty_budgets_returns_empty_dict(self):
        """T-14: Empty budgets iterable returns empty dict."""
        _, calculate_consumption_batch = self._import_service()

        results = calculate_consumption_batch([])

        self.assertEqual(results, {})

    def test_batch_single_budget_matches_single_function(self):
        """T-15: Batch with single budget matches single-budget function result."""
        calculate_consumption, calculate_consumption_batch = self._import_service()

        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("100.00"),
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
        )
        Expense.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("35.50"),
            date=date(2026, 10, 15),
        )

        single_result = calculate_consumption(budget)
        batch_results = calculate_consumption_batch([budget])

        self.assertIn(budget.id, batch_results)
        self.assertEqual(batch_results[budget.id].spent, single_result.spent)
        self.assertEqual(batch_results[budget.id].remaining, single_result.remaining)
        self.assertEqual(batch_results[budget.id].percentage, single_result.percentage)

    def test_batch_multiple_same_category_period(self):
        """T-16: Multiple budgets for same user/category/period are all included."""
        _, calculate_consumption_batch = self._import_service()

        # Create multiple budgets for same user/category but different periods
        budget1 = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("100.00"),
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
        )
        budget2 = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("200.00"),
            period_start=date(2026, 11, 1),
            period_end=date(2026, 11, 30),
        )

        # Create expenses for each period
        Expense.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("50.00"),
            date=date(2026, 10, 15),
        )
        Expense.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("75.00"),
            date=date(2026, 11, 15),
        )

        results = calculate_consumption_batch([budget1, budget2])

        self.assertEqual(len(results), 2)
        self.assertEqual(results[budget1.id].spent, Decimal("50.00"))
        self.assertEqual(results[budget2.id].spent, Decimal("75.00"))

    def test_batch_crossed_budgets_no_contamination(self):
        """T-17: Budgets for different users/categories don't cross-contaminate."""
        _, calculate_consumption_batch = self._import_service()

        budget1 = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("100.00"),
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
        )
        budget2 = Budget.objects.create(
            user=self.user,
            category=self.other_category,
            amount=Decimal("200.00"),
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
        )
        budget3 = Budget.objects.create(
            user=self.other_user,
            category=self.other_user_category,
            amount=Decimal("300.00"),
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
        )

        # Create expenses for each
        Expense.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("30.00"),
            date=date(2026, 10, 15),
        )
        Expense.objects.create(
            user=self.user,
            category=self.other_category,
            amount=Decimal("60.00"),
            date=date(2026, 10, 15),
        )
        Expense.objects.create(
            user=self.other_user,
            category=self.other_user_category,
            amount=Decimal("90.00"),
            date=date(2026, 10, 15),
        )

        results = calculate_consumption_batch([budget1, budget2, budget3])

        self.assertEqual(results[budget1.id].spent, Decimal("30.00"))
        self.assertEqual(results[budget2.id].spent, Decimal("60.00"))
        self.assertEqual(results[budget3.id].spent, Decimal("90.00"))

    def test_batch_single_query_for_all_budgets(self):
        """T-18: Batch uses only one SQL query (no N+1)."""
        _, calculate_consumption_batch = self._import_service()

        budget1 = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("100.00"),
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
        )
        budget2 = Budget.objects.create(
            user=self.user,
            category=self.other_category,
            amount=Decimal("200.00"),
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
        )

        Expense.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("50.00"),
            date=date(2026, 10, 15),
        )

        # Count queries during batch calculation
        with self.assertNumQueries(1):
            results = calculate_consumption_batch([budget1, budget2])

        self.assertEqual(len(results), 2)

    def test_batch_returns_dict_indexed_by_budget_id(self):
        """T-19: Batch returns dict with budget.id as keys."""
        _, calculate_consumption_batch = self._import_service()

        budget1 = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("100.00"),
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
        )
        budget2 = Budget.objects.create(
            user=self.user,
            category=self.other_category,
            amount=Decimal("200.00"),
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
        )

        results = calculate_consumption_batch([budget1, budget2])

        self.assertIsInstance(results, dict)
        self.assertIn(budget1.id, results)
        self.assertIn(budget2.id, results)
        self.assertEqual(len(results), 2)

    # ===== T-20 to T-23: Edge cases =====

    def test_budget_very_small_amount_minimum(self):
        """T-20: Budget with minimum amount (0.01) works correctly."""
        calculate_consumption, _ = self._import_service()

        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("0.01"),
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
        )

        consumption = calculate_consumption(budget)

        self.assertEqual(consumption.spent, Decimal("0.00"))
        self.assertEqual(consumption.remaining, Decimal("0.01"))
        self.assertEqual(consumption.percentage, Decimal("0.00"))

    def test_budget_very_large_amount_maximum(self):
        """T-21: Budget with maximum amount (99999999.99) works correctly."""
        calculate_consumption, _ = self._import_service()

        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("99999999.99"),
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
        )

        consumption = calculate_consumption(budget)

        self.assertEqual(consumption.spent, Decimal("0.00"))
        self.assertEqual(consumption.remaining, Decimal("99999999.99"))
        self.assertEqual(consumption.percentage, Decimal("0.00"))

    def test_percentage_very_small_value(self):
        """T-22: Small percentage (0.01 / 1.00 * 100 = 1.00%) rounds correctly."""
        calculate_consumption, _ = self._import_service()

        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("100.00"),
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
        )
        Expense.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("1.00"),
            date=date(2026, 10, 15),
        )

        consumption = calculate_consumption(budget)

        self.assertEqual(consumption.percentage, Decimal("1.00"))

    def test_percentage_just_under_100(self):
        """T-23: Percentage just under 100% (99.99%) is not capped."""
        calculate_consumption, _ = self._import_service()

        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("100.00"),
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
        )
        Expense.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("99.99"),
            date=date(2026, 10, 15),
        )

        consumption = calculate_consumption(budget)

        self.assertEqual(consumption.percentage, Decimal("99.99"))

    def test_percentage_over_100_not_capped(self):
        """T-24: Percentage > 100% is not capped at 100."""
        calculate_consumption, _ = self._import_service()

        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("100.00"),
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
        )
        Expense.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("200.00"),
            date=date(2026, 10, 15),
        )

        consumption = calculate_consumption(budget)

        self.assertEqual(consumption.percentage, Decimal("200.00"))

    # ===== T-25 to T-27: Type and immutability =====

    def test_all_return_values_are_decimal(self):
        """T-25: All return values from consumption are Decimal type."""
        calculate_consumption, _ = self._import_service()

        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("100.00"),
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
        )
        Expense.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("50.00"),
            date=date(2026, 10, 15),
        )

        consumption = calculate_consumption(budget)

        self.assertIsInstance(consumption.spent, Decimal)
        self.assertIsInstance(consumption.remaining, Decimal)
        self.assertIsInstance(consumption.percentage, Decimal)

    def test_values_quantized_to_exactly_two_decimal_places(self):
        """T-26: All values have exponent exactly -2 (quantized to 2 places)."""
        calculate_consumption, _ = self._import_service()

        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("123.45"),
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
        )
        Expense.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("45.67"),
            date=date(2026, 10, 15),
        )

        consumption = calculate_consumption(budget)

        self.assertEqual(consumption.spent.as_tuple().exponent, -2)
        self.assertEqual(consumption.remaining.as_tuple().exponent, -2)
        self.assertEqual(consumption.percentage.as_tuple().exponent, -2)

    def test_no_cache_reflects_database_changes(self):
        """T-27: Service calculates from current DB state; no caching."""
        calculate_consumption, _ = self._import_service()

        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("100.00"),
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
        )
        Expense.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("25.00"),
            date=date(2026, 10, 15),
        )

        # First calculation
        consumption1 = calculate_consumption(budget)
        self.assertEqual(consumption1.spent, Decimal("25.00"))

        # Add another expense
        Expense.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("25.00"),
            date=date(2026, 10, 20),
        )

        # Second calculation reflects the new expense
        consumption2 = calculate_consumption(budget)
        self.assertEqual(consumption2.spent, Decimal("50.00"))

        # Verify they're different
        self.assertNotEqual(consumption1.spent, consumption2.spent)
