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
