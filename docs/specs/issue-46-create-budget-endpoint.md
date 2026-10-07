# SPÉCIFICATION — Endpoint POST /api/budgets/ (Issue #46)

- **Issue :** #46 « Implement create budget endpoint with duplicate validation »
- **Statut :** Proposition. Non approuvée. Un humain doit valider cette spécification avant la mise en œuvre.
- **Auteur :** Agent Product & Architecture
- **Portée :** Endpoint API (`POST /api/budgets/`), validation applicative des doublons, tests unitaires et intégration. Aucun autre endpoint budget (GET list, GET detail, PATCH, DELETE), aucune interface frontend, aucune logique de consommation (spent/remaining).
- **Codebase examiné à :** branche `feat/46-create-budget-endpoint`, commits jusqu'au 2026-10-07

---

## 0. Introduction

Cette spécification propose l'implémentation du premier endpoint de gestion des budgets : créer un nouveau budget pour l'utilisateur courant. Le modèle `Budget` a été implémenté en issue #45 avec toutes les contraintes d'intégrité. Cette spec traduit le contrat API (`docs/api-design.md`, section 4.2) en endpoint Django REST Framework concret, avec focus sur la validation applicative des doublons (défense en profondeur avant la contrainte DB) et l'authentification de l'utilisateur.

**Contexte :**
- Issue #20 a implémenté le modèle `User`.
- Issue #33 a implémenté le modèle `Category` (scoped par user).
- Issue #45 a implémenté le modèle `Budget` avec contrainte UNIQUE composée.
- Issue #46 expose l'endpoint de création de budgets.
- Issues futures : GET list, GET detail, PATCH, DELETE, logique de consommation.

---

## 1. Énoncé du problème et critères d'acceptation

### 1.1 Récit utilisateur

> En tant qu'utilisateur authentifié, je dois pouvoir créer un budget via un endpoint POST, qui :
> - Valide que la catégorie existe ET appartient à mon compte (404 sinon, comme l'endpoint dépenses).
> - Accepte un montant décimal strictement positif (chaîne, pas float).
> - Accepte une période (dates de début et fin).
> - Accepte un seuil d'alerte optionnel (0–100 %).
> - Retourne une erreur **claire et applicative** (409 Conflict) si je tente de créer un budget en doublon (même catégorie, même période), **avant de toucher la base de données**.
> - Me retourne le budget créé en 201 Created avec tous les champs.

### 1.2 Critères d'acceptation (testables)

| ID | Critère | Vérification |
|----|---------|-------------|
| AC-1 | L'endpoint `POST /api/budgets/` existe à la route `/api/budgets/` (trailing slash conforme à la spec API). | Vérification dans `backend/api/urls.py`. |
| AC-2 | Authentification requise (SessionAuthentication + IsAuthenticated). Absence de token/session → 401 Unauthorized. | Test sans authentification. |
| AC-3 | La requête accepte `category_id`, `amount`, `period_start`, `period_end`, `alert_threshold` (optionnel) en JSON. | Inspection du serializer. |
| AC-4 | Le champ `amount` est une chaîne décimale (ex. `"500.00"`), jamais un nombre JSON. | Inspection du serializer et du test. |
| AC-5 | Le montant `amount` doit être strictement positif. Montants <= 0 retournent 400 Bad Request avec message lisible (ex. `"amount": "Doit être > 0"`). | Test avec amount <= 0. |
| AC-6 | La date `period_start` et `period_end` acceptent le format YYYY-MM-DD. `period_end` doit être >= `period_start`. Violation → 400 Bad Request. | Tests de validation de dates. |
| AC-7 | Le champ `category_id` doit exister et appartenir à l'utilisateur courant. Catégorie inexistante ou étrangère → 404 Not Found (conforme au style `category_list`). | Tests avec catégorie inexistante et étrangère. |
| AC-8 | Le champ `alert_threshold` est optionnel. S'il est fourni, doit être entre 0 et 100. Hors limites → 400 Bad Request. | Tests avec alert_threshold invalide. |
| AC-9 | **Check applicatif des doublons :** Avant de créer un budget, l'endpoint vérifie qu'il n'existe pas déjà de budget (user, category, period_start, period_end) dans la base. Doublon détecté → 409 Conflict avec message clair (ex. `"Budget déjà existant pour cette période et catégorie"`). | Test de création d'un doublon. |
| AC-10 | Le propriétaire (`user_id`) du budget est toujours `request.user`, jamais fourni par le client. | Inspection du code et test. |
| AC-11 | La réponse 201 Created retourne le budget complet sérialisé : `id`, `user_id`, `category_id`, `amount`, `period_start`, `period_end`, `alert_threshold`, `created_at`, `updated_at`. | Inspection de la réponse. |
| AC-12 | Les champs monétaires (`amount`, `alert_threshold`) sont sérialisés en chaînes JSON (conforme à `docs/api-design.md` section 1.3). | Vérification du format JSON. |
| AC-13 | Les timestamps (`created_at`, `updated_at`) sont en format ISO 8601 UTC (ex. `"2026-10-06T14:30:45Z"`). | Vérification du format. |
| AC-14 | Serializer validé et testé. Tests unitaires couvrent : création valide, validation des montants, dates, alert_threshold, unicité applicative, ownership. | Fichier `backend/api/tests/test_budget_create.py` avec tests pour chaque cas. |
| AC-15 | Contrainte DB (UNIQUE composée) reste en place comme filet de sécurité en cas de race condition ou contournement applicatif. | Vérification que la migration #45 est intacte. |

---

## 2. Contrat API

### 2.1 Route

**Méthode :** `POST`  
**Chemin :** `/api/budgets/`  
**Authentification :** Requise (`SessionAuthentication` + `IsAuthenticated`)  
**Sérialisation :** JSON  

### 2.2 Requête

**Corps (application/json) :**
```json
{
  "category_id": 5,
  "amount": "500.00",
  "period_start": "2026-10-01",
  "period_end": "2026-10-31",
  "alert_threshold": "80.00"
}
```

**Champs :**

| Champ | Type | Requis ? | Contraintes | Description |
|-------|------|----------|-----------|------------|
| `category_id` | integer | Oui | Doit exister et appartenir à `request.user` | ID de la catégorie pour ce budget. |
| `amount` | string (décimal) | Oui | > 0, ex. `"500.00"` | Montant budgété. Chaîne décimale, jamais nombre JSON. |
| `period_start` | string (date) | Oui | Format YYYY-MM-DD | Début de la période budgétaire. |
| `period_end` | string (date) | Oui | Format YYYY-MM-DD, >= period_start | Fin de la période budgétaire. |
| `alert_threshold` | string (décimal) | Non | Entre 0 et 100 (optionnel, défaut 80.00) | Seuil d'alerte en %. |

### 2.3 Réponse 201 Created

```json
{
  "id": 1,
  "user_id": 1,
  "category_id": 5,
  "amount": "500.00",
  "period_start": "2026-10-01",
  "period_end": "2026-10-31",
  "alert_threshold": "80.00",
  "created_at": "2026-10-06T10:00:00Z",
  "updated_at": "2026-10-06T10:00:00Z"
}
```

**Champs :**
- `id` (integer) : Identifiant du budget créé.
- `user_id` (integer) : Propriétaire (toujours `request.user.id`).
- `category_id` (integer) : Catégorie du budget.
- `amount` (string) : Montant budgété (chaîne décimale).
- `period_start`, `period_end` (string, ISO 8601 date) : Période.
- `alert_threshold` (string) : Seuil d'alerte (null si non fourni).
- `created_at`, `updated_at` (string, ISO 8601 datetime UTC) : Timestamps.

**Note :** Pas de champs calculés (`spent`, `remaining`) dans cette réponse de création. Ils sont réservés aux endpoints GET (future issue).

### 2.4 Erreurs possibles

#### 400 Bad Request — Validation échouée

Champs manquants, invalides, ou contraintes métier violées.

```json
{
  "error": "INVALID_DATA",
  "message": "Validation échouée",
  "details": {
    "amount": ["Doit être > 0"],
    "period_end": ["Doit être >= period_start"],
    "alert_threshold": ["Doit être entre 0 et 100"]
  }
}
```

**Cas :**
- `amount` <= 0 ou non parsable.
- `period_end` < `period_start` ou format invalide.
- `alert_threshold` hors limites (si fourni).
- Champs requis manquants.

#### 401 Unauthorized — Authentification absente ou invalide

```json
{
  "error": "UNAUTHORIZED",
  "message": "Token invalide ou expiré"
}
```

#### 404 Not Found — Category n'existe pas ou étrangère

```json
{
  "error": "NOT_FOUND",
  "message": "Catégorie non trouvée"
}
```

**Cas :**
- `category_id` n'existe pas.
- `category_id` existe mais `category.user_id != request.user.id` (catégorie d'un autre utilisateur).

**Style :** Retourner **404, pas 403**, conforme à `docs/api-design.md` section 1.6 et au style de `category_list`.

#### 409 Conflict — Budget en doublon

```json
{
  "error": "CONFLICT",
  "message": "Budget déjà existant pour cette période et catégorie"
}
```

**Cas :**
- Un budget existe déjà pour (user, category, period_start, period_end).
- **Détection applicative**, avant la requête DB, pour fournir un message clair.
- DB constraint UNIQUE reste en filet de sécurité (gère aussi les race conditions).

---

## 3. Implémentation

### 3.1 Fichier `backend/api/views.py` — Vue de création

Ajouter à `backend/api/views.py` :

```python
from rest_framework import serializers, viewsets, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import Budget, Category


class BudgetSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(read_only=True)
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
    budget = Budget.objects.create(
        user=request.user,
        category=category,
        amount=serializer.validated_data.get("amount"),
        period_start=period_start,
        period_end=period_end,
        alert_threshold=serializer.validated_data.get("alert_threshold"),
    )

    return Response(
        BudgetSerializer(budget).data, status=status.HTTP_201_CREATED
    )
```

### 3.2 Fichier `backend/api/urls.py` — Enregistrement de la route

Ajouter à `backend/api/urls.py` :

```python
from django.urls import path
from .views import health, category_list, budget_create

urlpatterns = [
    path("health/", health, name="health"),
    path("categories/", category_list, name="category_list"),
    path("budgets/", budget_create, name="budget_create"),
]
```

### 3.3 Serializer BudgetSerializer

Le serializer utilise `DecimalField` pour `amount` et `alert_threshold` afin de sérialiser en chaînes JSON (conforme à `docs/api-design.md` section 1.3).

**Champs en lecture seule :**
- `id` : généré par la base.
- `user_id` : toujours `request.user.id`, jamais du client.
- `created_at`, `updated_at` : gérés par Django.

**Validations du serializer :**
- `amount` : DecimalField > 0 (via validators du modèle).
- `period_end` >= `period_start` : via CheckConstraint du modèle (et validation applicative optionnelle).
- `alert_threshold` : entre 0 et 100 (via validators du modèle).

---

## 4. Plan de tests

Les tests couvrent l'endpoint `POST /api/budgets/` dans `backend/api/tests/test_budget_create.py`.

### 4.1 Authentification

- **Sans authentification :** POST sans token/session → 401 Unauthorized.
- **Avec authentification :** POST avec session valide → succès (201 ou 400/404/409 selon données).

### 4.2 Création valide

- Créer un budget valide (avec tous les champs requis + optional `alert_threshold`).
- Vérifier que `user_id` du budget créé = `request.user.id`.
- Vérifier la réponse 201 avec tous les champs sérialisés correctement.
- Vérifier que les montants sont en chaînes JSON (ex. `"500.00"`, pas `500` ou `500.0`).

### 4.3 Validation du montant

- `amount = "0"` → 400 Bad Request.
- `amount = "-10.50"` → 400 Bad Request.
- `amount = "0.01"` → 201 Créé (minimal positif).
- `amount = "99999999.99"` → 201 Créé (maximal).
- `amount = "abc"` → 400 Bad Request (non parsable).

### 4.4 Validation des dates

- `period_start = "2026-10-01"`, `period_end = "2026-09-30"` (end < start) → 400 Bad Request.
- `period_start = "2026-10-01"`, `period_end = "2026-10-01"` (même jour) → 201 Créé.
- `period_start = "2026-10-01"`, `period_end = "2026-10-31"` (normal) → 201 Créé.
- Format invalide (ex. `"2026-13-01"`) → 400 Bad Request.

### 4.5 Validation de `alert_threshold`

- `alert_threshold = null` (omis) → 201 Créé (défaut DB 80.00).
- `alert_threshold = "80.00"` → 201 Créé.
- `alert_threshold = "0"` → 201 Créé (limite basse).
- `alert_threshold = "100"` → 201 Créé (limite haute).
- `alert_threshold = "-1"` → 400 Bad Request.
- `alert_threshold = "100.01"` → 400 Bad Request.

### 4.6 Validation de la catégorie

- `category_id` inexistant → 404 Not Found.
- `category_id` appartenant à un autre utilisateur (Alice tente d'utiliser la catégorie de Bob) → 404 Not Found.
- `category_id` valide (appartient à `request.user`) → 201 Créé.

### 4.7 Duplicate check (applicatif)

- Créer un budget (user=Alice, category=1, period_start=2026-10-01, period_end=2026-10-31).
- Tenter de créer un budget identique → 409 Conflict avec message clair.
- Créer un budget (même user/category, période différente) → 201 Créé (accepté).
- Créer un budget (même user, catégorie différente, même période) → 201 Créé (accepté).

### 4.8 Integrity constraint (DB fallback)

- Simuler une race condition (deux requêtes concurrentes créent le même doublon) : la DB constraint UNIQUE empêche le doublon et lève une IntegrityError.
- L'endpoint doit capturer cette erreur et retourner 409 Conflict (optionnel mais recommandé pour défense en profondeur).

### 4.9 Serialization

- Vérifier que la réponse JSON a tous les champs attendus.
- Vérifier que `amount`, `alert_threshold` sont des chaînes, pas des nombres.
- Vérifier que `created_at`, `updated_at` sont au format ISO 8601 UTC.

---

## 5. Hors de cette spécification

Les éléments suivants **ne sont pas couverts** par cette issue #46 :

1. **GET `/api/budgets/` (list)** : Lister les budgets avec calculs de consommation (spent, remaining). Future issue.
2. **GET `/api/budgets/{id}/` (detail)** : Récupérer un budget spécifique. Future issue.
3. **PATCH `/api/budgets/{id}/`** : Modifier un budget. Future issue.
4. **DELETE `/api/budgets/{id}/`** : Supprimer un budget. Future issue.
5. **Logique de consommation (spent/remaining)** : Calcul dynamique des dépenses par rapport au budget. Future issue.
6. **Logique d'alerte** : Déclencher des alertes quand consommation dépasse `alert_threshold`. Future issue.
7. **Frontend SvelteKit** : Interface de création/affichage des budgets. Hors MVP.

---

## 6. Points ouverts et risques

1. **Race condition sur l'unicité applicative :** Le check applicatif (requête SELECT pour détecter les doublons) peut être vaincu par deux requêtes concurrentes. Mitigation : la constraint DB UNIQUE en base de données empêche le doublon et rejette la seconde requête avec IntegrityError. Recommandation : capturer cette erreur en endpoint et retourner 409 Conflict.

2. **Serialization des montants en chaînes :** Le serializer utilise `DecimalField`, qui sérialise nativement en chaînes JSON (conforme à spec). À vérifier dans la réponse HTTP réelle.

3. **Timezone des timestamps :** Les timestamps utilisent `DateTimeField` de Django, qui devrait sérialiser en ISO 8601 UTC si `USE_TZ = True` dans `settings.py`. À valider.

4. **Message d'erreur 404 pour catégories étrangères :** Retourner 404 au lieu de 403 est intentionnel (conforme à `docs/api-design.md` section 1.6) mais peut surprendre. Bien documenter dans le code.

---

## 7. Références

- **Contrat API :** `docs/api-design.md` (section 4.2 POST /api/budgets/)
- **ERD :** `docs/erd.md` (section BUDGET)
- **Spec Budget Model :** `docs/specs/issue-45-budget-model.md`
- **Spec API Design :** `docs/api-design.md` (sections 1.1–1.7, conventions)
- **Spec Category Ownership :** `docs/specs/issue-6-category-ownership.md`, `docs/decisions/category-ownership.md`
- **Views existants :** `backend/api/views.py` (style de `category_list`, authentification)
- **Models :** `backend/api/models.py` (Budget, Category, User)
- **URL routing :** `backend/api/urls.py`
- **Configuration Django :** `backend/cashmire/settings.py`
- **Workflow :** `docs/git-workflow.md`

---

*Dernière mise à jour : 2026-10-07. Document proposé par Product & Architecture agent. En attente d'approbation humaine avant implémentation par Full-Stack Development agent.*
