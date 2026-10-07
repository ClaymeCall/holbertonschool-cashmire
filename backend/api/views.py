from calendar import monthrange
from datetime import date
from decimal import Decimal

from django.contrib.auth import authenticate, login, logout

from django.db import IntegrityError, transaction
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, serializers, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .auth import SessionAuthenticatedAPIView, session_authenticated_api_view
from .serializers import LoginSerializer, RegisterSerializer, UserSerializer

from .models import Budget, Category, Expense
from .services.budget_consumption import calculate_consumption_batch


@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})


class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/ — docs/api-design.md §2.1, issue #22.

    Unauthenticated (anyone may register). On success also establishes a
    session via `login()`, per docs/mvp-scope.md §3.1 ("inscription
    immédiate") and decision 0003 (session-cookie auth, no token issued) —
    matching what register/+page.svelte already assumes: it redirects to
    `/` on a successful response with nothing to store itself.
    """

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        login(self.request, user)


class LoginView(generics.GenericAPIView):
    """POST /api/auth/login/ — docs/api-design.md §2.2, issue #23.

    Response shape deviates from §2.2 as documented: no `token` field —
    decision 0003 is session-cookie auth, established here via `login()`
    exactly as it is in RegisterView. The 200 body is the user resource
    (`UserSerializer`), not `{"token": ..., "user": {...}}`.

    AC-2 (no user-existence leakage): `authenticate()` returns `None` for
    both "no such email" and "wrong password" alike, and both get the
    identical 401 response here — there is no branch anywhere in this view
    that could tell a caller which one happened. Django's `ModelBackend`
    also runs the password hasher against a dummy value when no user
    matches, so a wrong password and a wrong email take roughly the same
    amount of time to reject (timing side-channel).

    Returns the 401 directly rather than `raise AuthenticationFailed(...)`:
    DRF's `handle_exception` silently rewrites that exception's status to
    403 unless the *first* configured authenticator provides a
    `WWW-Authenticate` challenge header. The global default authenticator
    order (settings.py doesn't override `DEFAULT_AUTHENTICATION_CLASSES`)
    is `SessionAuthentication` first, which has no such header — so the
    exception path silently becomes a 403. login/+page.svelte explicitly
    branches on `err.status === 401`, so this needs to actually be 401.

    AC-3 (brute-force): `ScopedRateThrottle` on the "login" scope (rate in
    REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"], settings.py) is the whole of
    this project's brute-force mitigation, and it is intentionally minimal
    — per-IP, not per-account, and easy to exhaust from behind a shared
    NAT. Documented, not hidden: see
    docs/decisions/0004-login-rate-limiting.md for why this is judged
    acceptable for an MVP demo and what a real deployment would need
    instead (e.g. per-account lockout, CAPTCHA).
    """

    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response(
                {"detail": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        login(request, user)
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)


@extend_schema(responses=UserSerializer)
@session_authenticated_api_view(["GET"])
def current_user(request):
    return Response(UserSerializer(request.user).data)


class LogoutView(SessionAuthenticatedAPIView):
    """POST /api/auth/logout/ — docs/api-design.md §2.3, issue #24.

    Shared session authentication resolves the user, rejects anonymous
    requests with 401, and enforces CSRF checks on authenticated unsafe
    requests.

    CSRF (decision 0003, point 5): this is the first endpoint in the
    codebase where DRF's `SessionAuthentication` actually enforces it —
    register/login don't, because neither resolves a session user at
    request time, but a logout call, by definition, is made by someone
    already logged in. A caller must send the `csrftoken` cookie's value
    back as an `X-CSRFToken` header (Django sets that cookie
    automatically, deliberately not `HttpOnly`, so client JS can read it)
    or this 403s with "CSRF Failed". No frontend logout button exists yet
    (#24 is backend-only) — flagged here for whoever builds one.

    `logout()` flushes the session server-side and rotates the session
    cookie (AC-2: "subsequent requests with the logged-out credential are
    rejected" — the old `sessionid` value stops referring to anything).
    """

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CategorySerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = [
            "id",
            "user_id",
            "name",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class CategoryListSerializer(serializers.Serializer):
    categories = CategorySerializer(many=True)


class ExpenseListQuerySerializer(serializers.Serializer):
    category_id = serializers.IntegerField(required=False, min_value=1)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)

    def validate(self, attrs):
        date_from = attrs.get("date_from")
        date_to = attrs.get("date_to")
        if date_from and date_to and date_from > date_to:
            raise serializers.ValidationError(
                {"date_from": "Must be on or before date_to."}
            )
        return attrs


class DecimalStringField(serializers.DecimalField):
    def to_internal_value(self, data):
        if not isinstance(data, str):
            self.fail("invalid")
        return super().to_internal_value(data)


class ExpenseCreateSerializer(serializers.Serializer):
    category_id = serializers.IntegerField(min_value=1)
    amount = DecimalStringField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    date = serializers.DateField()

    def validate_category_id(self, category_id):
        user = self.context["request"].user
        if not Category.objects.filter(pk=category_id, user=user).exists():
            raise NotFound(
                {
                    "error": "NOT_FOUND",
                    "message": "Catégorie non trouvée",
                }
            )
        return category_id

    def create(self, validated_data):
        return Expense.objects.create(
            user=self.context["request"].user,
            **validated_data,
        )


class ExpenseUpdateSerializer(serializers.Serializer):
    category_id = serializers.IntegerField(min_value=1)
    amount = DecimalStringField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        default=None,
    )
    date = serializers.DateField()

    def validate_category_id(self, category_id):
        user = self.context["request"].user
        if not Category.objects.filter(pk=category_id, user=user).exists():
            raise NotFound(
                {
                    "error": "NOT_FOUND",
                    "message": "Catégorie non trouvée",
                }
            )
        return category_id

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance


class ExpenseSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(read_only=True)
    category_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Expense
        fields = [
            "id",
            "user_id",
            "category_id",
            "amount",
            "description",
            "date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ExpenseListSerializer(serializers.Serializer):
    expenses = ExpenseSerializer(many=True)


@extend_schema(responses=CategoryListSerializer)
@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def category_list(request):
    categories = Category.objects.filter(user=request.user)
    serializer = CategorySerializer(categories, many=True)
    return Response({"categories": serializer.data})


@extend_schema(
    methods=["GET"],
    parameters=[ExpenseListQuerySerializer],
    responses=ExpenseListSerializer,
)
@extend_schema(
    methods=["POST"],
    request=ExpenseCreateSerializer,
    responses={status.HTTP_201_CREATED: ExpenseSerializer},
)
@api_view(["GET", "POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def expenses(request):
    if request.method == "GET":
        filters = ExpenseListQuerySerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)

        expenses = Expense.objects.filter(user=request.user)
        if "category_id" in filters.validated_data:
            expenses = expenses.filter(
                category_id=filters.validated_data["category_id"]
            )
        if "date_from" in filters.validated_data:
            expenses = expenses.filter(date__gte=filters.validated_data["date_from"])
        if "date_to" in filters.validated_data:
            expenses = expenses.filter(date__lte=filters.validated_data["date_to"])

        return Response({"expenses": ExpenseSerializer(expenses, many=True).data})

    serializer = ExpenseCreateSerializer(
        data=request.data,
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)
    expense = serializer.save()
    return Response(
        ExpenseSerializer(expense).data,
        status=status.HTTP_201_CREATED,
    )


def get_user_expense_or_404(expense_id, user):
    try:
        return Expense.objects.get(pk=expense_id, user=user)
    except Expense.DoesNotExist as exc:
        raise NotFound(
            {
                "error": "NOT_FOUND",
                "message": "Dépense non trouvée",
            }
        ) from exc


@extend_schema(
    methods=["PATCH"],
    request=ExpenseUpdateSerializer,
    responses=ExpenseSerializer,
)
@extend_schema(
    methods=["PUT"],
    request=ExpenseUpdateSerializer,
    responses=ExpenseSerializer,
)
@extend_schema(
    methods=["DELETE"],
    responses={status.HTTP_204_NO_CONTENT: None},
)
@api_view(["PATCH", "PUT", "DELETE"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def expense_detail_mutation(request, expense_id):
    expense = get_user_expense_or_404(expense_id, request.user)

    if request.method == "DELETE":
        expense.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = ExpenseUpdateSerializer(
        expense,
        data=request.data,
        context={"request": request},
        partial=request.method == "PATCH",
    )
    serializer.is_valid(raise_exception=True)
    updated_expense = serializer.save()
    return Response(ExpenseSerializer(updated_expense).data)
class BudgetSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(read_only=True)
    category_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    alert_threshold = serializers.DecimalField(
        max_digits=5, decimal_places=2, allow_null=True, required=False
    )

    class Meta:
        model = Budget
        fields = [
            "id",
            "user_id",
            "category_id",
            "amount",
            "period_start",
            "period_end",
            "alert_threshold",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user_id", "created_at", "updated_at"]

    def validate_amount(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError("Doit être > 0")
        return value

    def validate_alert_threshold(self, value):
        if value is not None and (value < Decimal("0") or value > Decimal("100")):
            raise serializers.ValidationError("Doit être entre 0 et 100")
        return value

    def validate(self, data):
        period_start = data.get("period_start")
        period_end = data.get("period_end")
        if period_start and period_end and period_end < period_start:
            raise serializers.ValidationError("period_end doit être >= period_start")
        return data


class BudgetWithConsumptionSerializer(serializers.ModelSerializer):
    """Serializer for budgets including consumption data (spent, remaining, percentage)."""

    user_id = serializers.IntegerField(read_only=True)
    spent = serializers.SerializerMethodField()
    remaining = serializers.SerializerMethodField()
    percentage = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Budget
        fields = [
            "id",
            "user_id",
            "category_id",
            "amount",
            "period_start",
            "period_end",
            "alert_threshold",
            "spent",
            "remaining",
            "percentage",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_spent(self, obj):
        """Return spent from consumption_data if available."""
        consumption_data = self.context.get("consumption_data", {})
        if obj.id in consumption_data:
            return str(consumption_data[obj.id].spent)
        return "0.00"

    def get_remaining(self, obj):
        """Return remaining from consumption_data if available."""
        consumption_data = self.context.get("consumption_data", {})
        if obj.id in consumption_data:
            return str(consumption_data[obj.id].remaining)
        return str(obj.amount)

    def get_percentage(self, obj):
        """Return percentage from consumption_data if available."""
        consumption_data = self.context.get("consumption_data", {})
        if obj.id in consumption_data:
            return str(consumption_data[obj.id].percentage)
        return "0.00"

    def get_status(self, obj):
        """Return status ("ok"/"warning"/"full"/"exceeded") from
        consumption_data if available — see
        docs/decisions/budget-thresholds.md §2 and
        api.services.budget_consumption._compute_status. Falls back to
        "ok" alongside this class's other no-consumption-data fallbacks
        (0.00 spent, full amount remaining)."""
        consumption_data = self.context.get("consumption_data", {})
        if obj.id in consumption_data:
            return consumption_data[obj.id].status
        return "ok"


class BudgetListSerializer(serializers.Serializer):
    budgets = BudgetWithConsumptionSerializer(many=True)


@extend_schema(
    request=BudgetSerializer,
    responses=BudgetListSerializer,
    description="List budgets or create a new budget for the authenticated user",
)
@api_view(["GET", "POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def budget_list_create(request):
    """
    Handle GET and POST on /api/budgets/.

    GET: List budgets for the authenticated user, with optional filtering by period and category.
    POST: Create a new budget for the authenticated user.
    """
    if request.method == "GET":
        return _budget_list_get(request)
    elif request.method == "POST":
        return _budget_create_post(request)


def _budget_list_get(request):
    """
    List budgets for the authenticated user, with optional filtering by period and category.

    Query parameters (all optional):
    - month: int [1, 12] — must be paired with year
    - year: int (valid year) — must be paired with month
    - category_id: int — filter by category

    Filtering by period (month + year):
    A budget is included if its [period_start, period_end] overlaps the given month.
    """
    # Parse and validate query parameters
    month = request.query_params.get("month")
    year = request.query_params.get("year")
    category_id = request.query_params.get("category_id")

    # Validate month/year pair
    if (month is None) != (year is None):
        return Response(
            {
                "error": "INVALID_DATA",
                "message": "month et year doivent tous les deux être fournis",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if month is not None:
        try:
            month = int(month)
            if month < 1 or month > 12:
                raise ValueError()
        except (ValueError, TypeError):
            return Response(
                {
                    "error": "INVALID_DATA",
                    "message": "month doit être entre 1 et 12",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    if year is not None:
        try:
            year = int(year)
            # Validate year is reasonable (optional: add bounds)
            if year < 1900 or year > 2100:
                raise ValueError()
        except (ValueError, TypeError):
            return Response(
                {
                    "error": "INVALID_DATA",
                    "message": "year doit être un entier valide",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    if category_id is not None:
        try:
            category_id = int(category_id)
        except (ValueError, TypeError):
            return Response(
                {
                    "error": "INVALID_DATA",
                    "message": "category_id doit être un entier valide",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    # Build queryset
    budgets_qs = Budget.objects.filter(user=request.user)

    # Filter by category_id if provided
    if category_id is not None:
        # Option: silently filter if category doesn't exist or is foreign
        # (could also return 404, but silently filtering is simpler)
        budgets_qs = budgets_qs.filter(category_id=category_id, category__user=request.user)

    # Filter by period (month + year) if provided
    if month is not None and year is not None:
        # Calculate the first and last day of the given month
        month_start = date(year, month, 1)
        month_end = date(year, month, monthrange(year, month)[1])

        # Include budgets whose [period_start, period_end] overlaps [month_start, month_end]
        # Overlap condition: period_start <= month_end AND period_end >= month_start
        budgets_qs = budgets_qs.filter(
            Q(period_start__lte=month_end) & Q(period_end__gte=month_start)
        )

    # Sort deterministically by ID
    budgets_qs = budgets_qs.order_by("id")

    # Convert to list to calculate consumption in batch
    budgets_list = list(budgets_qs)

    # Calculate consumption for all budgets in a single query
    consumption_data = calculate_consumption_batch(budgets_list)

    # Serialize with consumption data
    context = {"consumption_data": consumption_data}
    serializer = BudgetWithConsumptionSerializer(
        budgets_list, many=True, context=context
    )

    return Response({"budgets": serializer.data}, status=status.HTTP_200_OK)


def _budget_create_post(request):
    """
    Create a new budget for the authenticated user.

    Validation:
    - category_id must exist and belong to request.user (404 otherwise).
    - amount must be > 0 (400 otherwise).
    - period_end must be >= period_start (400 otherwise).
    - alert_threshold must be between 0 and 100 if provided (400 otherwise).
    - Duplicate check (user, category, period_start, period_end) returns 409 Conflict.
    """
    serializer = BudgetSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    category_id = serializer.validated_data.get("category_id")
    period_start = serializer.validated_data.get("period_start")
    period_end = serializer.validated_data.get("period_end")

    # Validate category exists and belongs to request.user
    try:
        category = Category.objects.get(id=category_id, user=request.user)
    except Category.DoesNotExist:
        return Response(
            {"error": "NOT_FOUND", "message": "Catégorie non trouvée"},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Application-level duplicate check (defense in depth)
    if Budget.objects.filter(
        user=request.user,
        category=category,
        period_start=period_start,
        period_end=period_end,
    ).exists():
        return Response(
            {
                "error": "CONFLICT",
                "message": "Budget déjà existant pour cette période et catégorie",
            },
            status=status.HTTP_409_CONFLICT,
        )

    # Create budget with owner = request.user
    budget_data = {
        "user": request.user,
        "category": category,
        "amount": serializer.validated_data.get("amount"),
        "period_start": period_start,
        "period_end": period_end,
    }
    # Only set alert_threshold if explicitly provided
    if "alert_threshold" in serializer.validated_data:
        budget_data["alert_threshold"] = serializer.validated_data.get("alert_threshold")

    # Wrap in transaction.atomic() and catch IntegrityError for race condition safety
    try:
        with transaction.atomic():
            budget = Budget.objects.create(**budget_data)
    except IntegrityError:
        # Race condition: duplicate was created between check and create
        return Response(
            {
                "error": "CONFLICT",
                "message": "Budget déjà existant pour cette période et catégorie",
            },
            status=status.HTTP_409_CONFLICT,
        )

    return Response(
        BudgetSerializer(budget).data, status=status.HTTP_201_CREATED
    )


@extend_schema(
    methods=["PATCH"],
    request=BudgetSerializer,
    responses=BudgetWithConsumptionSerializer,
    description="Update an existing budget for the authenticated user",
)
@extend_schema(
    methods=["DELETE"],
    responses={status.HTTP_204_NO_CONTENT: None},
    description="Delete an existing budget for the authenticated user",
)
@api_view(["PATCH", "DELETE"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def budget_update_patch(request, budget_id):
    """
    Handle PATCH and DELETE on /api/budgets/{budget_id}/.

    PATCH: Update an existing budget for the authenticated user. All fields are optional.
    Validates ownership, uniqueness constraint, and re-validates all fields.
    Returns 200 OK with updated budget including consumption data.

    DELETE: Delete an existing budget for the authenticated user.
    Returns 204 No Content on success.
    """
    # Retrieve budget and check ownership
    try:
        budget = Budget.objects.get(id=budget_id, user=request.user)
    except Budget.DoesNotExist:
        return Response(
            {"error": "NOT_FOUND", "message": "Budget non trouvé"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "DELETE":
        budget.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PATCH handling
    # Validate partial update with BudgetSerializer (all fields optional for PATCH)
    serializer = BudgetSerializer(budget, data=request.data, partial=True)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Resolve category_id (use new value if provided, else existing)
    category_id = serializer.validated_data.get("category_id", budget.category_id)

    # Resolve period dates (use new values if provided, else existing)
    period_start = serializer.validated_data.get("period_start", budget.period_start)
    period_end = serializer.validated_data.get("period_end", budget.period_end)

    # Validate period_end >= period_start (using resolved values)
    if period_end < period_start:
        return Response(
            {
                "error": "INVALID_DATA",
                "message": "period_end doit être >= period_start",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate category exists and belongs to request.user (if category_id changed)
    if category_id != budget.category_id:
        try:
            category = Category.objects.get(id=category_id, user=request.user)
        except Category.DoesNotExist:
            return Response(
                {"error": "NOT_FOUND", "message": "Catégorie non trouvée"},
                status=status.HTTP_404_NOT_FOUND,
            )

    # Application-level duplicate check: ensure no other budget has this combination
    if Budget.objects.filter(
        user=request.user,
        category_id=category_id,
        period_start=period_start,
        period_end=period_end,
    ).exclude(id=budget.id).exists():
        return Response(
            {
                "error": "CONFLICT",
                "message": "Budget déjà existant pour cette période et catégorie",
            },
            status=status.HTTP_409_CONFLICT,
        )

    # Apply updates to the budget instance
    try:
        with transaction.atomic():
            # Update all provided fields
            if "amount" in serializer.validated_data:
                budget.amount = serializer.validated_data["amount"]
            if "alert_threshold" in serializer.validated_data:
                budget.alert_threshold = serializer.validated_data["alert_threshold"]
            if "category_id" in serializer.validated_data:
                budget.category_id = serializer.validated_data["category_id"]
            if "period_start" in serializer.validated_data:
                budget.period_start = serializer.validated_data["period_start"]
            if "period_end" in serializer.validated_data:
                budget.period_end = serializer.validated_data["period_end"]

            budget.save()
    except IntegrityError:
        # Race condition: duplicate was created between check and save
        return Response(
            {
                "error": "CONFLICT",
                "message": "Budget déjà existant pour cette période et catégorie",
            },
            status=status.HTTP_409_CONFLICT,
        )

    # Return updated budget with consumption data
    consumption = calculate_consumption_batch([budget])
    context = {"consumption_data": consumption}
    response_serializer = BudgetWithConsumptionSerializer(budget, context=context)

    return Response(response_serializer.data, status=status.HTTP_200_OK)
