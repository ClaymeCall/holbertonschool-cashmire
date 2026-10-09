from django.conf import settings
from django.http import Http404
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from . import views


class DevelopmentOnlyViewMixin:
    def dispatch(self, request, *args, **kwargs):
        if not settings.DEBUG:
            raise Http404
        return super().dispatch(request, *args, **kwargs)


class DevelopmentOnlySpectacularAPIView(
    DevelopmentOnlyViewMixin,
    SpectacularAPIView,
):
    pass


class DevelopmentOnlySwaggerView(
    DevelopmentOnlyViewMixin,
    SpectacularSwaggerView,
):
    pass


urlpatterns = [
    path("health/", views.health, name="health"),
    path("auth/register/", views.RegisterView.as_view(), name="register"),
    path("auth/login/", views.LoginView.as_view(), name="login"),
    path("auth/me/", views.current_user, name="current-user"),
    path("auth/logout/", views.LogoutView.as_view(), name="logout"),
    path("categories/", views.category_list, name="category-list"),
    path("expenses/", views.expenses, name="expense-list-create"),
    path(
        "expenses/<int:expense_id>/",
        views.expense_detail_mutation,
        name="expense-detail-mutation",
    ),
    path("budgets/", views.budget_list_create, name="budget-list-create"),
    path("budgets/<int:budget_id>/", views.budget_update_patch, name="budget-update-patch"),
    path(
        "schema/",
        DevelopmentOnlySpectacularAPIView.as_view(),
        name="schema",
    ),
    path(
        "docs/",
        DevelopmentOnlySwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
