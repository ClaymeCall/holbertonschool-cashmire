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


@extend_schema(responses=CategoryListSerializer)
@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def category_list(request):
    categories = Category.objects.filter(user=request.user)
    serializer = CategorySerializer(categories, many=True)
    return Response({"categories": serializer.data})


@extend_schema(
    request=ExpenseCreateSerializer,
    responses={status.HTTP_201_CREATED: ExpenseSerializer},
)
@api_view(["POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def expense_create(request):
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
