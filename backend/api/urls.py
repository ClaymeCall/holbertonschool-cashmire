from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from . import views

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
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
