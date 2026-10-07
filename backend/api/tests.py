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
