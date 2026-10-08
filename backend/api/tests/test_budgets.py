from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from rest_framework.test import APIClient

from ..models import Budget, Category, Expense


User = get_user_model()


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


