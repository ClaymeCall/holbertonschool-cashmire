from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Iterable

from django.db.models import Q, Sum

from api.models import Budget, Expense


QUANT = Decimal("0.01")

DEFAULT_ALERT_THRESHOLD = Decimal("80.00")


@dataclass
class BudgetConsumption:
    """
    Represents the consumption state of a budget at calculation time.

    All monetary fields are stored as Decimal, quantized to 2 decimal places
    to ensure financial accuracy and prevent IEEE 754 rounding errors.

    Attributes:
        spent: Total amount spent in the budget period (Decimal, 2 places).
        remaining: Amount remaining in the budget (amount - spent).
                   Can be negative if spent > amount (Decimal, 2 places).
        percentage: Consumption as a percentage ((spent / amount) * 100).
                   Not capped at 100, allowing over-budget detection (Decimal, 2 places).
        status: One of "ok", "warning", "full", "exceeded" — see
                docs/decisions/budget-thresholds.md §2. Computed from the
                unrounded `spent`/`amount`/`alert_threshold` Decimals, per
                that decision's §3 ("sans arrondi préalable"), not from the
                already-quantized `percentage` field above.

    Note:
        This object represents a snapshot of consumption at calculation time.
        It does not cache; subsequent calls reflect current database state.
    """

    spent: Decimal
    remaining: Decimal
    percentage: Decimal
    status: str


def _compute_status(spent: Decimal, amount: Decimal, alert_threshold) -> str:
    """
    Status per docs/decisions/budget-thresholds.md §2's table, evaluated in
    that order (each condition assumes the ones above it are false):
      - exceeded: spent > amount
      - full:     spent == amount
      - warning:  spent >= amount * threshold / 100 (threshold's lower
                  bound is inclusive)
      - ok:       otherwise

    `alert_threshold` defaults to 80.00 when `None` (`Budget.alert_threshold`
    is nullable; the decision names 80% as the system default for that case).
    """
    threshold = alert_threshold if alert_threshold is not None else DEFAULT_ALERT_THRESHOLD
    if spent > amount:
        return "exceeded"
    if spent == amount:
        return "full"
    if spent >= amount * threshold / 100:
        return "warning"
    return "ok"


def calculate_consumption(budget: Budget) -> BudgetConsumption:
    """
    Calculate the consumption of a single budget.

    Retrieves all Expense objects for the budget's user, category, and period,
    sums their amounts, and derives spent, remaining, and percentage values.

    Args:
        budget: Budget instance to analyze.

    Returns:
        BudgetConsumption with spent, remaining, and percentage (all Decimal).

    Example:
        >>> budget = Budget.objects.get(id=1)
        >>> consumption = calculate_consumption(budget)
        >>> print(f"Spent: {consumption.spent}, Remaining: {consumption.remaining}")
        Spent: 50.00, Remaining: 50.00

    Note:
        - All calculations use Decimal to maintain financial precision.
        - If no expenses exist, spent = 0.00.
        - The percentage is never capped at 100, allowing over-budget detection.
        - Period boundaries are inclusive: expenses on period_start or period_end are included.
    """
    # Fetch all expenses for this budget's user, category, and period
    spent = (
        Expense.objects.filter(
            user=budget.user,
            category=budget.category,
            date__gte=budget.period_start,
            date__lte=budget.period_end,
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    # Calculate remaining and percentage
    remaining = budget.amount - spent
    percentage = (spent / budget.amount * 100) if budget.amount > 0 else Decimal("0.00")

    status = _compute_status(spent, budget.amount, budget.alert_threshold)

    # Quantize all values to 2 decimal places
    spent = spent.quantize(QUANT)
    remaining = remaining.quantize(QUANT)
    percentage = percentage.quantize(QUANT)

    return BudgetConsumption(
        spent=spent,
        remaining=remaining,
        percentage=percentage,
        status=status,
    )


def calculate_consumption_batch(budgets: Iterable[Budget]) -> Dict[int, BudgetConsumption]:
    """
    Calculate consumption for multiple budgets in a single database query.

    Loads all relevant expenses in one SELECT query (no N+1 problem) and
    aggregates them by budget in Python to avoid overcomplicating SQL.

    Args:
        budgets: Iterable of Budget instances (list, QuerySet, etc.).

    Returns:
        Dict mapping budget.id -> BudgetConsumption for each budget.
        Empty dict if budgets iterable is empty.

    Example:
        >>> budgets = Budget.objects.filter(user=user)
        >>> results = calculate_consumption_batch(budgets)
        >>> for budget_id, consumption in results.items():
        ...     print(f"Budget {budget_id}: {consumption.percentage}% used")

    Note:
        - Executes exactly one SQL query to fetch all Expense objects.
        - Performs aggregation in Python for clarity and simplicity.
        - Period boundaries are inclusive.
    """
    budgets_list = list(budgets)
    if not budgets_list:
        return {}

    # Build conditions for a single query fetching all relevant expenses
    # We create a Q object for each (user, category, period_start, period_end) combination
    q_conditions = Q()
    for budget in budgets_list:
        q_conditions |= Q(
            user=budget.user,
            category=budget.category,
            date__gte=budget.period_start,
            date__lte=budget.period_end,
        )

    # Single database query
    expenses = list(Expense.objects.filter(q_conditions))

    # Calculate consumption for each budget
    results = {}
    for budget in budgets_list:
        # Find all expenses matching this budget's criteria
        matching_expenses = []
        for expense in expenses:
            if (
                expense.user_id == budget.user_id
                and expense.category_id == budget.category_id
                and budget.period_start <= expense.date <= budget.period_end
            ):
                matching_expenses.append(expense)

        # Sum amounts
        spent = sum((e.amount for e in matching_expenses), Decimal("0.00"))

        # Calculate remaining and percentage
        remaining = budget.amount - spent
        percentage = (
            (spent / budget.amount * 100) if budget.amount > 0 else Decimal("0.00")
        )

        status = _compute_status(spent, budget.amount, budget.alert_threshold)

        # Quantize all values to 2 decimal places
        spent = spent.quantize(QUANT)
        remaining = remaining.quantize(QUANT)
        percentage = percentage.quantize(QUANT)

        results[budget.id] = BudgetConsumption(
            spent=spent,
            remaining=remaining,
            percentage=percentage,
            status=status,
        )

    return results
