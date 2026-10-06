from decimal import Decimal

from django.contrib.auth import login
from django.db import IntegrityError, transaction
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

from .models import Budget, Category, Expense
from .serializers import RegisterSerializer


@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})


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
        from decimal import Decimal
        if value <= Decimal("0"):
            raise serializers.ValidationError("Doit être > 0")
        return value

    def validate_alert_threshold(self, value):
        from decimal import Decimal
        if value is not None and (value < Decimal("0") or value > Decimal("100")):
            raise serializers.ValidationError("Doit être entre 0 et 100")
        return value

    def validate(self, data):
        period_start = data.get("period_start")
        period_end = data.get("period_end")
        if period_start and period_end and period_end < period_start:
            raise serializers.ValidationError("period_end doit être >= period_start")
        return data


@extend_schema(
    request=BudgetSerializer,
    responses=BudgetSerializer,
    description="Create a new budget for the authenticated user",
)
@api_view(["POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def budget_create(request):
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
