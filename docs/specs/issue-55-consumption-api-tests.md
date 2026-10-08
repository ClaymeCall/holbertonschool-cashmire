# Spécification — Tests API de cohérence de la consommation budgétaire (issue #55, partie tests)

- **Issue :** #55 (partielle : tests uniquement)
- **Statut :** Proposé. À relire par l'équipe avant implémentation par l'agent Full-Stack Development.
- **Auteur :** Product & Architecture Agent
- **Date :** 2026-10-08
- **Codebase examiné :** branche `test/54-55-56-budget-tests`, HEAD `2e21ad2`
- **Portée :** Ajouter des tests d'API dans `backend/api/tests.py`. Aucune modification de code applicatif (views, models, serializers, services), aucune migration.
- **Hors portée :** statut de budget (`ok` / `warning` / `full` / `exceeded`), seuils d'alerte (`alert_threshold`), route `GET /api/budgets/{id}/`.

---

## 1. Problème et critères d'acceptation

### 1.1 User story

> En tant que développeur, je veux une suite de tests qui prouve que la consommation d'un budget (`spent`, `remaining`, `percentage`) exposée par `GET /api/budgets/` reste juste lorsque les dépenses sont créées, modifiées (montant, catégorie, date) ou supprimées via les endpoints de dépenses réels, afin de détecter une régression du calcul à la lecture.

### 1.2 Critères d'acceptation

| ID | Critère | Vérification (test) |
|----|---------|---------------------|
| AC-1 | Une dépense créée via `POST /api/expenses/` dans la catégorie et la période du budget apparaît dans `spent`, `remaining`, `percentage` de `GET /api/budgets/`. | T-1, T-10 |
| AC-2 | Les bornes de période sont incluses : `date == period_start` et `date == period_end` sont comptées. | T-2 |
| AC-3 | Une dépense hors période (avant `period_start` ou après `period_end`) ou dans une autre catégorie ne modifie pas la consommation. | T-3, T-4 |
| AC-4 | Une création rejetée (400 ou 404) ne modifie pas la consommation. | T-5 |
| AC-5 | `PATCH` sur le montant met à jour la consommation. | T-6 |
| AC-6 | `PATCH` sur `category_id` retire la dépense du budget de la catégorie d'origine, et la rajoute au budget de la nouvelle catégorie. | T-7, T-8 |
| AC-7 | `PATCH` sur `date` sort la dépense de la période puis la réintègre (bornes incluses). | T-9 |
| AC-8 | `PUT` (remplacement complet) met à jour la consommation comme `PATCH`. | T-11 |
| AC-9 | Une mutation rejetée (400, 404) via `PATCH` ou `PUT` ne modifie ni la dépense ni la consommation. | T-5, T-12 |
| AC-10 | `DELETE /api/expenses/{id}/` retire la contribution de la dépense ; la consommation revient à `0.00` quand il n'y a plus de dépense. | T-13 |
| AC-11 | Plusieurs dépenses sont sommées en `Decimal` exact (pas d'erreur flottante). | T-14 |
| AC-12 | Un dépassement produit un `remaining` négatif et un `percentage` non plafonné à 100. | T-15 |
| AC-13 | Un utilisateur ne peut pas modifier ou supprimer la dépense d'un autre utilisateur, et la consommation de ses budgets reste inchangée. | T-16 |

---

## 2. Modèle de données

### 2.1 Aucun changement

Aucune colonne, table, contrainte ou migration n'est ajoutée. Le modèle est tel que défini dans `backend/api/models.py` et `docs/erd.md`.

- `Expense` ne référence pas `Budget`. Le lien est implicite et calculé à la lecture : même `user`, même `category`, `date` dans `[period_start, period_end]` (ERD : « Requêtes de matching `EXPENSE.date BETWEEN BUDGET.period_start AND BUDGET.period_end` »).
- Les colonnes `spent`, `remaining`, `percentage` ne sont **pas stockées** : elles sont calculées par `calculate_consumption_batch` (`backend/api/services/budget_consumption.py`) à chaque requête.
- Champs monétaires : `Expense.amount` et `Budget.amount` sont `NUMERIC(10,2)` / `DecimalField`, jamais `float`. Les tests doivent comparer des chaînes décimales (cf. §3.2), pas des flottants.

### 2.2 Cohérence avec l'ERD

Vérifiée : `docs/erd.md` ne prévoit pas de FK `EXPENSE → BUDGET` et ne contient pas de colonne de consommation. Cette spécification ne change pas le contrat ERD.

---

## 3. Contrats API existants utilisés par les tests

### 3.1 Endpoints de dépenses (mutations sous test)

Tous exigent une session (`SessionAuthentication` + `IsAuthenticated`). Les tests utilisent `APIClient` + `force_login`.

| Méthode | Chemin | Corps | Succès | Erreurs testées |
|---------|--------|-------|--------|-----------------|
| POST | `/api/expenses/` | `category_id` (int, requis), `amount` (chaîne décimale, requis, `>= 0.01`, 2 décimales max), `date` (`YYYY-MM-DD`, requis), `description` (optionnel) | 201, `ExpenseSerializer` | 400 (montant invalide), 404 `{"error":"NOT_FOUND","message":"Catégorie non trouvée"}` (catégorie absente ou d'un autre user) |
| PATCH | `/api/expenses/{id}/` | Un sous-ensemble de `category_id`, `amount`, `date`, `description` | 200, `ExpenseSerializer` | 400 (montant float ou invalide), 404 (`"Dépense non trouvée"` ou `"Catégorie non trouvée"`) |
| PUT | `/api/expenses/{id}/` | `category_id`, `amount`, `date` requis ; `description` optionnel (réinitialisé à `null` si absent) | 200, `ExpenseSerializer` | 400 (champs requis manquants), 404 |
| DELETE | `/api/expenses/{id}/` | aucun | 204, corps vide | 404 (`"Dépense non trouvée"`, identique pour absent et autre user) |

Remarque : `amount` doit être une **chaîne** (`DecimalStringField`). Un flottant (`12.34`) est rejeté avec 400.

### 3.2 Endpoint de lecture de la consommation

**Seul endpoint de lecture existant : `GET /api/budgets/`** (`backend/api/urls.py`, `budget_list_create`).

- Authentification : session requise (403 sans session).
- Réponse 200 : `{"budgets": [ ... ]}`, triée par `id` croissant.
- Filtres optionnels (non utilisés ici) : `month` + `year`, `category_id`.

**Champs réels de consommation dans chaque élément de `budgets[]`** (`BudgetWithConsumptionSerializer`, `backend/api/views.py`) :

| Champ | Type JSON | Source | Exemple (budget 500.00, dépense 25.50) |
|-------|-----------|--------|------------------------------------------|
| `spent` | string | somme des `Expense.amount` matchées, quantifiée 2 décimales | `"25.50"` |
| `remaining` | string | `amount - spent`, quantifiée, peut être négatif | `"474.50"` |
| `percentage` | string | `spent / amount * 100`, quantifiée 2 décimales, non plafonnée | `"5.10"` |

Autres champs présents (à ne pas oublier dans les assertions de structure si nécessaire) : `id`, `user_id`, `category_id`, `amount` (string, p. ex. `"500.00"`), `period_start`, `period_end`, `alert_threshold`, `created_at`, `updated_at`.

Règles de valeur à tester : `spent` vaut `"0.00"` sans dépense ; `remaining` vaut `amount` sans dépense.

**Pas de route de détail en lecture.** `GET /api/budgets/{id}/` n'est **pas** routé (`urls.py` ne déclare que `PATCH` et `DELETE` sur `budgets/<id>/`, ce qui renverrait 405). La documentation `docs/api-design.md` §4.3 décrit cette route, mais elle n'existe pas dans le code. Les tests de cette spécification ne l'utilisent pas (voir §6, risque R-1).

---

## 4. Fixtures et helpers à réutiliser

Aucun nouveau module, aucun nouvel import (`Decimal`, `date`, `APIClient`, `Budget`, `Category`, `Expense`, `User` sont déjà importés dans `backend/api/tests.py`).

### 4.1 Pattern de setup (repris de `ExpenseDetailMutationTests` et `BudgetDeleteTests`)

- `User.objects.create_user(username=..., email=..., password="correct-horse-battery-staple-42")` : un utilisateur `self.user` et un `self.other_user`.
- Les catégories par défaut sont créées automatiquement par le signal `create_default_categories` (`backend/api/signals.py`, 12 catégories par utilisateur, ordonnées par `id`). Ne pas en créer manuellement.
  - `self.category = self.user.categories.first()`
  - `self.other_category = self.user.categories.exclude(pk=self.category.pk).first()`
  - `self.other_users_category = self.other_user.categories.first()`
- `self.client = APIClient()`, puis `self.client.force_login(self.user)` dans chaque test qui mute.
- Budget de référence créé par ORM (comme `BudgetListTests`, `BudgetDeleteTests`) :
  ```python
  self.budget = Budget.objects.create(
      user=self.user,
      category=self.category,
      amount=Decimal("500.00"),
      period_start=date(2026, 10, 1),
      period_end=date(2026, 10, 31),
  )
  ```

### 4.2 Helpers privés à ajouter dans la nouvelle classe de test

Les helpers doivent rester dans la classe (pas de module partagé, pas de changement de `setUp` des autres classes).

```python
def post_expense(self, **overrides):
    """POST /api/expenses/ with a valid default payload; asserts 201; returns expense id."""
    payload = {
        "category_id": self.category.pk,
        "amount": "25.50",
        "date": "2026-10-15",
        **overrides,
    }
    response = self.client.post(self.url, payload, format="json")
    self.assertEqual(response.status_code, 201)
    return response.json()["id"]

def expense_url(self, expense_id):
    return f"/api/expenses/{expense_id}/"

def get_consumption(self, budget_id):
    """GET /api/budgets/ (list) and return only the consumption fields of one budget."""
    response = self.client.get("/api/budgets/")
    self.assertEqual(response.status_code, 200)
    budget = next(b for b in response.json()["budgets"] if b["id"] == budget_id)
    return {
        "spent": budget["spent"],
        "remaining": budget["remaining"],
        "percentage": budget["percentage"],
    }
```

Les expressions d'attente sont des dictionnaires de chaînes, par exemple :
`{"spent": "25.50", "remaining": "474.50", "percentage": "5.10"}`.

### 4.3 Dépenses de setup

Pour la préparation de l'état initial, deux options sont acceptables. **Recommandation :** utiliser `post_expense()` quand le test porte sur la création, et `Expense.objects.create(...)` (comme `ExpenseListTests.create_expense`) quand la dépense n'est qu'un prérequis. Dans les deux cas, la mutation testée passe par l'endpoint réel.

---

## 5. Cas de test (à implémenter par l'agent Full-Stack)

**Emplacement :** nouvelle classe `BudgetConsumptionViaExpenseEndpointsTests(TestCase)` ajoutée à la fin de `backend/api/tests.py`. Pas de nouveau paquet `backend/api/tests/` : il entrerait en conflit avec le module `tests.py` existant.

**Commande :** `docker compose run --rm api python manage.py test api` (depuis la racine du repo).

**Rappel :** chaque cas dont le nom commence par `test_` doit suivre exactement les étapes et valeurs ci-dessous.

### T-1 `test_create_expense_in_budget_category_and_period_increases_consumption`

1. `force_login(self.user)`.
2. `post_expense(amount="25.50", date="2026-10-15")` (catégorie `self.category`).
3. `get_consumption(self.budget.id)` == `{"spent": "25.50", "remaining": "474.50", "percentage": "5.10"}`.

### T-2 `test_create_expenses_on_both_period_boundaries_are_counted`

1. `post_expense(amount="10.00", date="2026-10-01")`.
2. `post_expense(amount="20.00", date="2026-10-31")`.
3. `get_consumption` == `{"spent": "30.00", "remaining": "470.00", "percentage": "6.00"}`.

### T-3 `test_create_expense_outside_period_does_not_change_consumption`

1. `post_expense(amount="10.00", date="2026-09-30")`.
2. `post_expense(amount="10.00", date="2026-11-01")`.
3. `get_consumption` == `{"spent": "0.00", "remaining": "500.00", "percentage": "0.00"}`.

### T-4 `test_create_expense_in_other_category_does_not_change_consumption`

1. `post_expense(category_id=self.other_category.pk, amount="10.00", date="2026-10-15")`.
2. `get_consumption` == `{"spent": "0.00", "remaining": "500.00", "percentage": "0.00"}`.

### T-5 `test_rejected_expense_mutations_leave_consumption_unchanged`

Préparation : `expense_id = self.post_expense(amount="25.50", date="2026-10-15")`.

Sous-cas (`subTest`), chacun suivi de vérification :
- `POST /api/expenses/` avec `category_id=self.other_users_category.pk` → 404, et `Expense.objects.count() == 1`.
- `POST /api/expenses/` avec `amount="0.00"` → 400.
- `PATCH` `{"amount": "0.00"}` → 400.
- `PATCH` `{"amount": 12.34}` (float) → 400.
- `PATCH` `{"category_id": 99999999}` → 404.
- `PUT` `{"amount": "40.00"}` (incomplet) → 400.

Vérification finale : `get_consumption(self.budget.id)` == `{"spent": "25.50", "remaining": "474.50", "percentage": "5.10"}` et `Expense.objects.get(pk=expense_id).amount == Decimal("25.50")`.

### T-6 `test_patch_amount_updates_consumption`

1. `expense_id = post_expense(amount="25.50", date="2026-10-15")`.
2. `PATCH expense_url(expense_id)` avec `{"amount": "40.00"}` → 200.
3. `get_consumption` == `{"spent": "40.00", "remaining": "460.00", "percentage": "8.00"}`.

### T-7 `test_patch_category_moves_expense_out_of_budget`

1. `expense_id = post_expense(amount="25.50", date="2026-10-15")`.
2. `PATCH` `{"category_id": self.other_category.pk}` → 200.
3. `get_consumption(self.budget.id)` == `{"spent": "0.00", "remaining": "500.00", "percentage": "0.00"}`.

### T-8 `test_patch_category_back_moves_expense_into_budget`

Suite de T-7, puis :
4. `PATCH` `{"category_id": self.category.pk}` → 200.
5. `get_consumption(self.budget.id)` == `{"spent": "25.50", "remaining": "474.50", "percentage": "5.10"}`.

### T-9 `test_patch_date_moves_expense_out_of_period_and_back_on_boundary`

1. `expense_id = post_expense(amount="25.50", date="2026-10-15")`.
2. `PATCH` `{"date": "2026-11-01"}` → 200 ; `get_consumption` == `{"spent": "0.00", "remaining": "500.00", "percentage": "0.00"}`.
3. `PATCH` `{"date": "2026-10-31"}` → 200 (borne `period_end`) ; `get_consumption` == `{"spent": "25.50", "remaining": "474.50", "percentage": "5.10"}`.

### T-10 `test_patch_category_moves_expense_between_two_budgets`

Préparation : `budget_other = Budget.objects.create(user=self.user, category=self.other_category, amount=Decimal("200.00"), period_start=date(2026, 10, 1), period_end=date(2026, 10, 31))`.

1. `expense_id = post_expense(amount="25.50", date="2026-10-15")`.
2. `PATCH` `{"category_id": self.other_category.pk}` → 200.
3. `get_consumption(self.budget.id)` == `{"spent": "0.00", "remaining": "500.00", "percentage": "0.00"}`.
4. `get_consumption(budget_other.id)` == `{"spent": "25.50", "remaining": "174.50", "percentage": "12.75"}`.

### T-11 `test_put_replacement_updates_consumption`

1. `expense_id = post_expense(amount="25.50", date="2026-10-15")`.
2. `PUT` `{"category_id": self.category.pk, "amount": "40.05", "date": "2026-10-09"}` → 200.
3. `get_consumption` == `{"spent": "40.05", "remaining": "459.95", "percentage": "8.01"}`.

### T-12 `test_rejected_put_or_patch_on_foreign_expense_does_not_change_consumption`

Préparation : `foreign_expense = Expense.objects.create(user=self.other_user, category=self.other_users_category, amount=Decimal("80.00"), date=date(2026, 10, 15))`.

1. `PATCH expense_url(foreign_expense.pk)` `{"amount": "30.00"}` → 404.
2. `PUT expense_url(foreign_expense.pk)` `{"category_id": self.category.pk, "amount": "30.00", "date": "2026-10-08"}` → 404.
3. `get_consumption(self.budget.id)` == `{"spent": "0.00", "remaining": "500.00", "percentage": "0.00"}`.
4. `Expense.objects.get(pk=foreign_expense.pk).amount == Decimal("80.00")`.

Note : `404` retourné dans les deux cas et corps identique à un id inexistant (déjà couvert par `ExpenseDetailMutationTests`, non répété ici).

### T-13 `test_delete_expense_removes_its_contribution`

1. `first_id = post_expense(amount="25.50", date="2026-10-15")`.
2. `second_id = post_expense(amount="10.00", date="2026-10-20")`.
3. `DELETE expense_url(first_id)` → 204, corps vide.
4. `get_consumption` == `{"spent": "10.00", "remaining": "490.00", "percentage": "2.00"}`.
5. `DELETE expense_url(second_id)` → 204.
6. `get_consumption` == `{"spent": "0.00", "remaining": "500.00", "percentage": "0.00"}`.

### T-14 `test_multiple_small_expenses_are_summed_with_decimal_precision`

1. `post_expense(amount="0.10", date="2026-10-02")`.
2. `post_expense(amount="0.20", date="2026-10-03")`.
3. `get_consumption` == `{"spent": "0.30", "remaining": "499.70", "percentage": "0.06"}`.

### T-15 `test_expense_over_budget_yields_negative_remaining_and_uncapped_percentage`

1. `post_expense(amount="600.00", date="2026-10-15")`.
2. `get_consumption` == `{"spent": "600.00", "remaining": "-100.00", "percentage": "120.00"}`.

Ce cas ne teste que le calcul numérique déjà présent. Aucune assertion sur un statut (`ok`, `warning`, `exceeded`) : ce concept n'existe pas dans le code de cette branche.

### T-16 `test_foreign_expense_mutations_return_404_and_never_touch_budget`

Cas couvert par T-12 (PATCH et PUT sur dépense étrangère). Ce test peut être fusionné avec T-12 à la discrétion de l'agent Full-Stack. Il ajoute `DELETE` :

1. `DELETE expense_url(foreign_expense.pk)` → 404.
2. `Expense.objects.filter(pk=foreign_expense.pk).exists()` est vrai.

### Tests explicitement exclus de cette spécification

- Tout test sur `status`, `warning`, `full`, `exceeded`, sur `alert_threshold`, ou sur `docs/decisions/budget-thresholds.md`. Non implémenté sur cette branche.
- Tout test sur `GET /api/budgets/{id}/` (route inexistante, voir §6 R-1).
- Tout test sur `PATCH` / `DELETE` de budget (couverts par `BudgetUpdateEndpointTests` et `BudgetDeleteTests`).
- Tout test de nombre de requêtes SQL (couvert par `test_budget_list_consumption_batch_efficiency`).
- Tout test de filtre `month` / `year` sur la liste.

---

## 6. Questions ouvertes et risques

| ID | Sujet | Impact | Recommandation |
|----|-------|--------|----------------|
| R-1 | **Pas de `GET /api/budgets/{id}/`.** Le ticket #55 et `docs/api-design.md` §4.3 parlent d'un « detail » ; le code n'expose que la liste en lecture (le `PATCH` renvoie aussi la consommation, mais ce n'est pas une lecture après mutation d'une dépense). | Les tests ne peuvent pas couvrir un détail qui n'existe pas. | Valider : (a) les tests restent sur `GET /api/budgets/` seul (proposition de cette spec) ; ou (b) un ticket séparé ajoute la route de détail, puis un test T-17 la couvrira. Ne pas modifier `api-design.md` sans décision. |
| R-2 | **Dérive de `docs/api-design.md`.** §4.2 (`POST /api/budgets/`) montre `spent`/`remaining` dans la réponse, alors que le code renvoie `BudgetSerializer` sans consommation. | Aucun impact sur les tests de cette spec (on ne lit que la liste). | Hors scope ; à signaler à l'équipe de documentation. |
| R-3 | **Emplacement des tests.** `backend/api/tests.py` est un module unique. La spec issue-50 mentionne `backend/api/tests/test_budget_consumption.py`, qui n'existe pas. | Créer un paquet `tests/` masquerait `tests.py`. | Garder un seul fichier `tests.py` et ajouter la classe à la fin. |
| R-4 | **Conflit de périmètre sur la demande initiale.** La demande demandait d'ajouter les tests directement. Les contraintes de l'agent Product & Architecture interdisent de modifier des fichiers de tests. | Aucun fichier de test n'a été écrit par cet agent. | Ce document est la spécification ; l'agent Full-Stack écrit le code de test. |
| R-5 | **Arrondi.** `Decimal.quantize` utilise l'arrondi par défaut du contexte (`ROUND_HALF_EVEN`). Les valeurs de test ont été choisies exactes (pas d'arrondi nécessaire). | Aucun pour ces cas. | Ne pas ajouter de valeurs qui exigent un arrondi sans décision d'équipe. |
| R-6 | **Dates figées en 2026.** `DateField` ignore le fuseau horaire. Les tests utilisent des dates fixes (2026-10-xx) et ne dépendent pas de `date.today()`. | Aucun. | Conserver des dates fixes. |
| R-7 | **Non exécuté.** Cette spécification n'a pas été validée par exécution de la suite. | Les valeurs attendues sont calculées à la main à partir du code de `calculate_consumption_batch` et de `ExpenseCreateSerializer` / `ExpenseUpdateSerializer`. | L'agent Full-Stack doit lancer `docker compose run --rm api python manage.py test api` et corriger toute valeur attendue divergente avant de conclure. |

---

## 7. Références

- `backend/api/views.py` : `expenses`, `expense_detail_mutation`, `budget_list_create`, `_budget_list_get`, `BudgetWithConsumptionSerializer`.
- `backend/api/services/budget_consumption.py` : `calculate_consumption_batch`.
- `backend/api/urls.py` : routes budgets et expenses.
- `backend/api/tests.py` : `ExpenseCreateTests`, `ExpenseListTests`, `ExpenseDetailMutationTests`, `BudgetListTests`, `BudgetUpdateEndpointTests`, `BudgetDeleteTests`.
- `backend/api/signals.py` : création des catégories par défaut.
- `docs/erd.md` : pas de FK `EXPENSE → BUDGET`, matching par date.
- `docs/specs/issue-50-budget-consumption-service.md` : contrat du service.
- `docs/specs/issue-49-delete-budget-endpoint.md` : format de spécification de référence.

---

*Document proposé par l'agent Product & Architecture. Non approuvé. Un humain doit valider cette spécification avant toute implémentation.*
