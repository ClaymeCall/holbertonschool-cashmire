from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Category, DEFAULT_CATEGORIES, Expense


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
