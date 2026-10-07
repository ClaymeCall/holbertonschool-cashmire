from django.contrib.auth import authenticate, login, logout
from decimal import Decimal

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
from rest_framework.views import APIView

from .serializers import LoginSerializer, RegisterSerializer, UserSerializer

from .models import Category, Expense


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


class LogoutView(APIView):
    """POST /api/auth/logout/ — docs/api-design.md §2.3, issue #24.

    `permission_classes = [AllowAny]` looks backwards for an endpoint that
    requires authentication, but it's deliberate: DRF's `IsAuthenticated`
    raises `NotAuthenticated`, which hits the exact same 401→403
    downgrade as `LoginView`'s `AuthenticationFailed` did (see that view's
    docstring) whenever the first authenticator in
    `DEFAULT_AUTHENTICATION_CLASSES` has no `WWW-Authenticate` header —
    true here for the same reason. Checking `request.user.is_authenticated`
    directly and returning the 401 ourselves sidesteps that entirely, so
    this endpoint's error shape stays consistent with `LoginView`'s rather
    than silently becoming a different status code.

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

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
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
