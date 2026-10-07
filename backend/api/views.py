from decimal import Decimal

from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Category, Expense


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
