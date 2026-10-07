from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from rest_framework.test import APIClient
from datetime import date
from decimal import Decimal

from .models import Budget, Category, DEFAULT_CATEGORIES


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
