# SPÉCIFICATION — Endpoint GET /api/budgets/ (Issue #47)

- **Issue :** #47 « Implement list/get budgets endpoint with consumption data »
- **Statut :** Proposition. Non approuvée. Un humain doit valider cette spécification avant la mise en œuvre.
- **Auteur :** Agent Product & Architecture
- **Portée :** Endpoint API (`GET /api/budgets/`), calcul de consommation en batch, tests unitaires et intégration. Aucun autre endpoint budget (GET detail, PATCH, DELETE), aucune interface frontend.
- **Codebase examiné à :** branche `feat/50-budget-consumption-service`, commits jusqu'au 2026-10-07

---

## 0. Introduction

Cette spécification propose l'implémentation du premier endpoint de lecture des budgets : lister les budgets de l'utilisateur courant avec leurs données de consommation calculées dynamiquement. La fonction `calculate_consumption_batch` (issue #50) est disponible pour éviter un problème N+1. Cette spec traduit le contrat API (`docs/api-design.md`, section 4.1) en endpoint Django REST Framework concret, avec support de filtrage par période (month+year) et catégorie (category_id).

**Contexte :**
- Issue #45 a implémenté le modèle `Budget`.
- Issue #46 a implémenté l'endpoint de création (`POST /api/budgets/`).
- Issue #50 a implémenté le service `calculate_consumption_batch` (une seule requête DB pour tous les budgets).
- Issue #47 expose l'endpoint de listage avec consommation.
- Issues futures : GET detail, PATCH, DELETE.

---

## 1. Énoncé du problème et critères d'acceptation

### 1.1 Récit utilisateur

> En tant qu'utilisateur authentifié, je dois pouvoir récupérer une liste de mes budgets via un endpoint GET, qui :
> - Retourne uniquement mes budgets (scoped par `request.user`).
> - Inclut pour chaque budget les données de consommation : montant dépensé (`spent`), montant restant (`remaining`), et pourcentage consommé (`percentage`), tous en chaînes décimales.
> - Calcule la consommation en une seule requête (via `calculate_consumption_batch`, pas N+1).
> - Supporte un filtrage optionnel par période (`?month=&year=`) : retourne uniquement les budgets dont la période chevauche ou est exactement ce mois.
> - Supporte un filtrage optionnel par catégorie (`?category_id=`), comme spécifié dans `docs/api-design.md`.
> - Valide les paramètres : si `month` est hors 1..12, ou `year` invalide, ou un sans l'autre, retourne 400 Bad Request.
> - Retourne une liste vide (`{"budgets": []}`) si aucun budget ne correspond aux filtres.
> - Retourne un ordre déterministe (ex. par ID croissant ou date d'ajout croissante).

### 1.2 Critères d'acceptation (testables)

| ID | Critère | Vérification |
|----|---------|-------------|
| AC-1 | L'endpoint `GET /api/budgets/` existe à la route `/api/budgets/` (trailing slash conforme à la spec API). | Vérification dans `backend/api/urls.py`. |
| AC-2 | Authentification requise (SessionAuthentication + IsAuthenticated). Absence de token/session → 401 Unauthorized. | Test sans authentification. |
| AC-3 | La réponse retourne un objet JSON `{"budgets": [<budget1>, <budget2>, ...]}`. | Inspection de la réponse. |
| AC-4 | Chaque budget inclut `id`, `user_id`, `category_id`, `amount`, `period_start`, `period_end`, `alert_threshold`, `spent`, `remaining`, `percentage`, `created_at`, `updated_at`. | Vérification de tous les champs. |
| AC-5 | Les champs monétaires (`amount`, `alert_threshold`, `spent`, `remaining`, `percentage`) sont sérialisés en chaînes décimales JSON. | Vérification du format JSON. |
| AC-6 | Les timestamps (`created_at`, `updated_at`) sont en format ISO 8601 UTC (ex. `"2026-10-06T14:30:45Z"`). | Vérification du format. |
| AC-7 | Query parameter optionnel `?month=<1..12>` pour filtrer par mois (année civile). | Test avec différentes valeurs de month. |
| AC-8 | Query parameter optionnel `?year=<YYYY>` pour filtrer par année (de date valide). | Test avec différentes valeurs de year. |
| AC-9 | **Règle de filtrage period :** Un budget est inclus si son `[period_start, period_end]` chevauche ou chevauche entièrement le mois donné (1er au dernier jour du mois, à minuit). | Test avec budgets dont la période chevauche partiellement ou complètement. |
| AC-10 | Query parameter optionnel `category_id=<integer>` (conforme à `docs/api-design.md` section 4.1). | Test avec et sans category_id. |
| AC-11 | Validation : si `month` est fourni sans `year` (ou inversement), retourner 400 Bad Request avec message clair (ex. `"month et year doivent tous les deux être fournis"`). | Test avec un seul paramètre. |
| AC-12 | Validation : si `month` est hors limites [1, 12], retourner 400 Bad Request (ex. `"month doit être entre 1 et 12"`). | Test avec month=0, month=13. |
| AC-13 | Validation : si `year` ne peut pas être parsé comme entier (ex. `year=abc`), retourner 400 Bad Request (ex. `"year doit être un entier valide"`). | Test avec year invalide. |
| AC-14 | Validation : si `category_id` ne peut pas être parsé comme entier, retourner 400 Bad Request. | Test avec category_id invalide. |
| AC-15 | Validation : si `category_id` existe mais appartient à un autre utilisateur, ne pas retourner cette catégorie dans le filtre (404-like : ignorer silencieusement, ou retourner liste vide). | Test avec catégorie étrangère (À trancher, voir points ouverts). |
| AC-16 | List vide (no match) retourne `{"budgets": []}` (code 200 OK). | Test sans budgets ou tous filtrés. |
| AC-17 | Ordre déterministe : résultats triés par `id` croissant (ou autre ordre fixe à définir). | Test sur plusieurs budgets. |
| AC-18 | Calcul de consommation utilise `calculate_consumption_batch()` (une seule requête DB pour tous les budgets, pas N+1). | Inspection du code / vérification des requêtes DB. |
| AC-19 | Seuls les budgets de `request.user` sont retournés (ownership). | Test avec utilisateurs différents. |
| AC-20 | La réponse 200 OK retourne tous les budgets filtrés avec consommation. | Inspection de la réponse HTTP. |

---

## 2. Contrat API

### 2.1 Route

**Méthode :** `GET`  
**Chemin :** `/api/budgets/`  
**Authentification :** Requise (`SessionAuthentication` + `IsAuthenticated`)  
**Sérialisation :** JSON  

### 2.2 Query Parameters

Tous les paramètres sont optionnels. S'ils ne sont pas fournis, la liste complète des budgets est retournée.

| Paramètre | Type | Optionnel ? | Contraintes | Description |
|-----------|------|----------|-----------|------------|
| `month` | integer | Oui | Entre 1 et 12 ; **doit être fourni avec `year`** | Mois de l'année civile (1 = janvier, 12 = décembre). Filtre les budgets dont la période chevauche ce mois. |
| `year` | integer | Oui | Année valide (ex. 2026) ; **doit être fourni avec `month`** | Année civile. Ensemble avec `month`, définit le mois à filtrer. |
| `category_id` | integer | Oui | Doit exister et appartenir à `request.user` (si fourni) | Filtre les budgets de cette catégorie. Combinable avec `month`/`year`. |

### 2.3 Règle de filtrage par période (month + year)

Si `month` et `year` sont fournis, un budget est **inclus** si et seulement si son intervalle de période `[period_start, period_end]` chevauche l'intervalle du mois considéré.

**Définition :** Pour une année Y et un mois M, l'intervalle du mois est `[1er jour du mois M de l'année Y, dernier jour du mois M de l'année Y]`.

**Chevauchement :** Deux intervalles [A, B] et [C, D] se chevauchent si `A <= D` ET `B >= C`.

**Exemples :**
- Budget 1 : `period_start = "2026-10-15"`, `period_end = "2026-10-31"`. Filtre `month=10&year=2026` : **Inclus** (chevauche).
- Budget 2 : `period_start = "2026-10-01"`, `period_end = "2026-10-31"`. Filtre `month=10&year=2026` : **Inclus** (identique).
- Budget 3 : `period_start = "2026-09-15"`, `period_end = "2026-10-15"`. Filtre `month=10&year=2026` : **Inclus** (chevauche partiellement).
- Budget 4 : `period_start = "2026-09-01"`, `period_end = "2026-09-30"`. Filtre `month=10&year=2026` : **Exclu** (pas de chevauchement).
- Budget 5 : `period_start = "2026-10-05"`, `period_end = "2026-10-10"`. Filtre `month=10&year=2026` : **Inclus** (contenu dans le mois).

### 2.4 Requête

```http
GET /api/budgets/?month=10&year=2026&category_id=5
Authorization: Bearer <token>
```

ou

```http
GET /api/budgets/?category_id=5
Authorization: Bearer <token>
```

ou

```http
GET /api/budgets/
Authorization: Bearer <token>
```

### 2.5 Réponse 200 OK

```json
{
  "budgets": [
    {
      "id": 1,
      "user_id": 1,
      "category_id": 5,
      "amount": "500.00",
      "period_start": "2026-10-01",
      "period_end": "2026-10-31",
      "alert_threshold": "80.00",
      "spent": "234.50",
      "remaining": "265.50",
      "percentage": "46.90",
      "created_at": "2026-10-01T10:00:00Z",
      "updated_at": "2026-10-01T10:00:00Z"
    },
    {
      "id": 2,
      "user_id": 1,
      "category_id": 7,
      "amount": "200.00",
      "period_start": "2026-10-01",
      "period_end": "2026-10-31",
      "alert_threshold": "75.00",
      "spent": "150.00",
      "remaining": "50.00",
      "percentage": "75.00",
      "created_at": "2026-10-02T10:00:00Z",
      "updated_at": "2026-10-02T10:00:00Z"
    }
  ]
}
```

**Champs :**
- `id` (integer) : Identifiant du budget.
- `user_id` (integer) : Propriétaire (toujours `request.user.id`).
- `category_id` (integer) : Catégorie du budget.
- `amount` (string) : Montant budgété (chaîne décimale).
- `period_start`, `period_end` (string, ISO 8601 date) : Période du budget.
- `alert_threshold` (string) : Seuil d'alerte (null si non défini).
- **`spent` (string, Decimal)** : Somme des dépenses de cette catégorie dans la période [period_start, period_end]. **Calculé dynamiquement via `calculate_consumption_batch()`.**
- **`remaining` (string, Decimal)** : `amount - spent`. Peut être négatif si dépenses > budget.
- **`percentage` (string, Decimal)** : `(spent / amount) * 100`. Peut être > 100 si dépenses > budget. Jamais null.
- `created_at`, `updated_at` (string, ISO 8601 datetime UTC) : Timestamps.

#### Cas d'une liste vide :
```json
{
  "budgets": []
}
```

Code 200 OK (pas 204 No Content).

### 2.6 Erreurs possibles

#### 400 Bad Request — Paramètres de requête invalides

```json
{
  "error": "INVALID_DATA",
  "message": "month et year doivent tous les deux être fournis"
}
```

**Cas :**
- `month` fourni sans `year` (ou vice versa).
- `month` hors limites [1, 12].
- `year` non parsable comme entier.
- `category_id` non parsable comme entier.

**Exemples de messages :**
- `"month et year doivent tous les deux être fournis"`
- `"month doit être entre 1 et 12"`
- `"year doit être un entier valide"`
- `"category_id doit être un entier valide"`

#### 401 Unauthorized — Authentification absente ou invalide

```json
{
  "error": "UNAUTHORIZED",
  "message": "Token invalide ou expiré"
}
```

#### 404 Not Found — Catégorie étrangère

**À trancher (voir points ouverts, AC-15) :**
- Option A : Ignorer silencieusement un `category_id` étrangère et retourner liste vide.
- Option B : Retourner 404 Not Found avec message explicite.

*Décision à prendre en revue humaine.*

---

## 3. Implémentation

### 3.1 Fichier `backend/api/views.py` — Vue de listage

Ajouter à `backend/api/views.py` :

```python
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from decimal import Decimal

from rest_framework import serializers, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from .models import Budget, Category
from .services.budget_consumption import calculate_consumption_batch


class BudgetWithConsumptionSerializer(serializers.ModelSerializer):
    """Serializer for budgets including consumption data (spent, remaining, percentage)."""
    user_id = serializers.IntegerField(read_only=True)
    spent = serializers.SerializerMethodField()
    remaining = serializers.SerializerMethodField()
    percentage = serializers.SerializerMethodField()

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


class BudgetListSerializer(serializers.Serializer):
    budgets = BudgetWithConsumptionSerializer(many=True)


@extend_schema(
    parameters=[
        # Query parameters defined via OpenAPI if needed
    ],
    responses=BudgetListSerializer,
    description="List all budgets for the authenticated user with consumption data",
)
@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def budget_list(request):
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
        month_end = (month_start + relativedelta(months=1)) - relativedelta(days=1)

        # Include budgets whose [period_start, period_end] overlaps [month_start, month_end]
        # Overlap condition: period_start <= month_end AND period_end >= month_start
        from django.db.models import Q
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
```

### 3.2 Fichier `backend/api/urls.py` — Enregistrement de la route

Mettre à jour `backend/api/urls.py` :

```python
from django.urls import path
from .views import health, category_list, budget_create, budget_list

urlpatterns = [
    path("health/", health, name="health"),
    path("categories/", category_list, name="category_list"),
    path("budgets/", budget_list, name="budget_list"),  # GET /api/budgets/
    # path("budgets/", budget_create, name="budget_create"),  # POST /api/budgets/
    # (Note: both GET and POST on /api/budgets/ if using method-based routing)
]
```

**Note :** Si `budget_create` (POST) est dans le même fichier, regrouper les deux routes :

```python
@api_view(["GET", "POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def budget_list_create(request):
    if request.method == "GET":
        # ... budget_list logic
    elif request.method == "POST":
        # ... budget_create logic
```

Ou conserver deux vues séparées et router en fonction de la méthode HTTP (Django le fait automatiquement).

### 3.3 Serializers

**BudgetWithConsumptionSerializer :**
- Hérite de `ModelSerializer` pour `Budget`.
- Champs en lecture seule : tous (inclus consommation calculée).
- Contexte reçoit `consumption_data` dict (budget.id -> BudgetConsumption).
- Utilise `SerializerMethodField` pour `spent`, `remaining`, `percentage`.
- Sérialise en chaînes décimales (via `str(Decimal)`).

**BudgetListSerializer :**
- Enveloppe la liste de `BudgetWithConsumptionSerializer` sous clé `"budgets"`.

---

## 4. Plan de tests

Les tests couvrent l'endpoint `GET /api/budgets/` dans `backend/api/tests/test_budget_list.py`.

### 4.1 Authentification

- **Sans authentification :** GET sans token/session → 401 Unauthorized.
- **Avec authentification :** GET avec session valide → 200 OK (list complète ou filtrée).

### 4.2 Listage complet

- Créer 3 budgets pour l'utilisateur.
- GET `/api/budgets/` → 200 OK avec tous les 3 budgets.
- Vérifier structure : `{"budgets": [...]}`
- Vérifier que tous les champs sont présents (id, user_id, category_id, amount, period_start, period_end, alert_threshold, spent, remaining, percentage, created_at, updated_at).

### 4.3 Sérialisation des montants

- Vérifier que `amount`, `alert_threshold`, `spent`, `remaining`, `percentage` sont des chaînes JSON.
- Exemples : `"500.00"`, `"0.00"`, `"234.50"`, `"46.90"`.
- Vérifier que `percentage` peut être > 100 (over-budget).

### 4.4 Consommation calculée en batch

- Créer 2 budgets avec dépenses associées.
- GET `/api/budgets/` → vérifier que `spent` et `remaining` sont justes.
- Vérifier via inspection du code ou requêtes DB que `calculate_consumption_batch()` est appelée (une seule requête SELECT pour les dépenses, pas N+1).

### 4.5 Filtrage par catégorie (category_id)

- Créer 3 budgets : 2 pour category_id=5, 1 pour category_id=7.
- GET `/api/budgets/?category_id=5` → retourne seulement 2 budgets.
- GET `/api/budgets/?category_id=7` → retourne seulement 1 budget.
- GET `/api/budgets/?category_id=999` → retourne 0 budgets (liste vide).

### 4.6 Filtrage par période (month + year)

#### 4.6.1 Budget chevauchant le mois

- Créer Budget 1 : `period_start = "2026-10-15"`, `period_end = "2026-10-31"`.
- GET `/api/budgets/?month=10&year=2026` → retourne Budget 1.

#### 4.6.2 Budget contenu dans le mois

- Créer Budget 2 : `period_start = "2026-10-05"`, `period_end = "2026-10-10"`.
- GET `/api/budgets/?month=10&year=2026` → retourne Budget 2.

#### 4.6.3 Budget avant le mois

- Créer Budget 3 : `period_start = "2026-09-01"`, `period_end = "2026-09-30"`.
- GET `/api/budgets/?month=10&year=2026` → ne retourne pas Budget 3.

#### 4.6.4 Budget chevauchant partiellement (début du mois suivant)

- Créer Budget 4 : `period_start = "2026-09-15"`, `period_end = "2026-10-15"`.
- GET `/api/budgets/?month=10&year=2026` → retourne Budget 4 (chevauche).

### 4.7 Validation des paramètres

#### 4.7.1 month sans year (ou inversement)

- GET `/api/budgets/?month=10` → 400 Bad Request (`"month et year doivent tous les deux être fournis"`).
- GET `/api/budgets/?year=2026` → 400 Bad Request.

#### 4.7.2 month hors limites

- GET `/api/budgets/?month=0&year=2026` → 400 Bad Request (`"month doit être entre 1 et 12"`).
- GET `/api/budgets/?month=13&year=2026` → 400 Bad Request.

#### 4.7.3 year invalide

- GET `/api/budgets/?month=10&year=abc` → 400 Bad Request (`"year doit être un entier valide"`).

#### 4.7.4 category_id invalide

- GET `/api/budgets/?category_id=abc` → 400 Bad Request (`"category_id doit être un entier valide"`).

### 4.8 Liste vide

- Pas de budgets créés.
- GET `/api/budgets/` → 200 OK avec `{"budgets": []}`.
- GET `/api/budgets/?month=10&year=2026` (aucun budget pour ce mois) → 200 OK avec `{"budgets": []}`.

### 4.9 Ordre déterministe

- Créer 3 budgets (dans un ordre aléatoire).
- GET `/api/budgets/` → retourne en ordre croissant d'ID (ou autre ordre fixe).
- Vérifier que deux GET consécutifs retournent le même ordre.

### 4.10 Ownership (scoping par user)

- Créer User A avec budgets B1, B2.
- Créer User B avec budgets B3, B4.
- GET `/api/budgets/` en tant que User A → retourne seulement B1, B2.
- GET `/api/budgets/` en tant que User B → retourne seulement B3, B4.

### 4.11 Combinaison de filtres

- Créer 4 budgets : 2 pour category_id=5 en oct, 1 pour category_id=5 en sept, 1 pour category_id=7 en oct.
- GET `/api/budgets/?category_id=5&month=10&year=2026` → retourne seulement les 2 pour category_id=5 en oct.

### 4.12 Timestamps

- Vérifier que `created_at` et `updated_at` sont au format ISO 8601 UTC (ex. `"2026-10-06T14:30:45Z"`).

### 4.13 Propriétaire (user_id)

- Vérifier que `user_id` de chaque budget retourné == `request.user.id`.

---

## 5. Écarts avec `docs/api-design.md`

### 5.1 Champ `percentage` ajouté

**Écart :** `docs/api-design.md` section 4.1 ne mentionne pas le champ `percentage`. Cette spec l'ajoute à la réponse.

**Justification :** La consommation en pourcentage est utile pour l'UI (barres de progression, alertes visuelles). Calculé à partir de `spent / amount * 100`.

**Décision :** À valider en revue humaine. Si approuvé, mettre à jour `docs/api-design.md` section 4.1 pour inclure ce champ.

### 5.2 Support des paramètres `month` et `year`

**Écart :** `docs/api-design.md` section 4.1 ne mentionne que `category_id`. Cette spec ajoute `month` et `year` optionnels.

**Justification :** L'issue #47 demande explicitement un filtrage par période. Le support combiné (month/year + category_id) est flexibilisé.

**Décision :** À valider en revue humaine. Si approuvé, mettre à jour `docs/api-design.md` section 4.1 pour documenter ces paramètres.

---

## 6. Hors de cette spécification

Les éléments suivants **ne sont pas couverts** par cette issue #47 :

1. **GET `/api/budgets/{id}/` (detail)** : Récupérer un budget spécifique. Future issue.
2. **PATCH `/api/budgets/{id}/`** : Modifier un budget. Future issue.
3. **DELETE `/api/budgets/{id}/`** : Supprimer un budget. Future issue.
4. **Logique d'alerte** : Déclencher des alertes quand consommation dépasse `alert_threshold`. Future issue.
5. **Frontend SvelteKit** : Interface d'affichage des budgets. Hors MVP.
6. **Pagination** : MVP sans pagination (conforme à `docs/api-design.md` section 1.7). Futur si listes très longues.

---

## 7. Points ouverts et risques

1. **Catégorie étrangère en filtrage :** Si l'utilisateur A passe `?category_id=<id de catégorie de B>`, comment se comporter ?
   - Option A (proposée) : Ignorer silencieusement et retourner liste vide.
   - Option B : Retourner 404 Not Found.
   - **Décision à trancher en revue humaine.**

2. **Bounds de validation year :** Actuellement, year doit être entre 1900 et 2100 (valeur raisonnable). À affiner si besoin.

3. **Performance avec many budgets :** Si un utilisateur a centaines/milliers de budgets, la requête `calculate_consumption_batch()` peut être lente. Mitigation : cette fonction n'est pas N+1 mais reste O(N). Indexer `(user_id, category_id, date)` sur Expense pour optimiser.

4. **Timezone des budgets :** Les budgets utilisent des dates (YYYY-MM-DD), pas des datetimes. Pas d'ambiguïté timezone. Les timezones ne sont pertinentes que pour `created_at`/`updated_at` (UTC, OK).

5. **Rounding des Decimals :** `percentage` est quantisé à 2 places décimales. Pour des rapports précis, vérifier que c'est suffisant ou arrondir au-delà (ex. 3 places).

---

## 8. Références

- **Contrat API :** `docs/api-design.md` (section 4.1 GET /api/budgets/)
- **Service de consommation :** `backend/api/services/budget_consumption.py` (issue #50)
- **ERD :** `docs/erd.md` (section BUDGET)
- **Spec Budget Model :** `docs/specs/issue-45-budget-model.md`
- **Spec Budget Create :** `docs/specs/issue-46-create-budget-endpoint.md`
- **Spec Budget Consumption :** `docs/specs/issue-50-budget-consumption-service.md`
- **Spec API Design :** `docs/api-design.md` (sections 1.1–1.7, conventions)
- **Views existants :** `backend/api/views.py` (style de `category_list`, authentification)
- **Models :** `backend/api/models.py` (Budget, Category, Expense, User)
- **URL routing :** `backend/api/urls.py`
- **Configuration Django :** `backend/cashmire/settings.py`
- **Workflow :** `docs/git-workflow.md`

---

*Dernière mise à jour : 2026-10-07. Document proposé par Product & Architecture agent. En attente d'approbation humaine avant implémentation par Full-Stack Development agent.*
