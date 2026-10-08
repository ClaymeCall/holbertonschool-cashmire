from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from rest_framework.test import APIClient

from ..models import Budget, Category


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
