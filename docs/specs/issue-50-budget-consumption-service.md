# SPÉCIFICATION — Service de consommation budgétaire (Issue #50)

- **Issue :** #50 « Implement budget consumption calculation service »
- **Statut :** Proposition. Non approuvée. Un humain doit valider cette spécification avant la mise en œuvre.
- **Auteur :** Agent Product & Architecture
- **Portée :** Service pur (logique métier), tests unitaires. Aucun endpoint API, aucune route HTTP, aucune migration.
- **Codebase examiné à :** branche `feat/50-budget-consumption-service`, commits jusqu'au 2026-10-07
- **Modèles disponibles :** `Expense` (issue #34), `Budget` (issue #45)

---

## 0. Introduction

Cette spécification propose l'implémentation d'un service pur de calcul de consommation budgétaire — composant métier du pilier « Budget Tracking » qui centralise la logique de calcul des montants dépensés, restants et du pourcentage de consommation pour un ou plusieurs budgets. 

**Contexte :**
- Issue #45 a implémenté le modèle `Budget`.
- Issue #34 a implémenté le modèle `Expense`.
- Issue #50 implémente le service qui agrège les expenses pour calculer la consommation.
- Issue #47 expose ce service via `GET /api/budgets/` (avec données de consommation calculées en temps réel, sans cache).
- Décision `docs/decisions/budget-thresholds.md` définit les statuts de budget basés sur le pourcentage de consommation.

---

## 1. Énoncé du problème et critères d'acceptation

### 1.1 Récit utilisateur

> En tant que développeur (agent Full-Stack Development), je dois implémenter un service pur qui calcule la consommation d'un budget à partir des dépenses en base, afin que :
>
> - Les montants dépensés et restants sont calculés dynamiquement depuis les `Expense` (pas de totalisation stockée).
> - Le calcul agrège les expenses de la même catégorie, du même utilisateur, dont la date se situe dans la période `[period_start, period_end]` (bornes incluses).
> - Tous les calculs utilisent `Decimal` pour éviter les erreurs d'arrondi IEEE 754.
> - Le pourcentage de consommation est quantifié à 2 décimales et n'est pas plafonné à 100 % (permet de détecter les dépassements).
> - Le service fournit une fonction pour un budget unique et une fonction batch pour plusieurs budgets d'un coup (évite les requêtes N+1).
> - Les données de consommation (spent, remaining, percentage) peuvent être utilisées immédiatement par l'API et le statut du budget.
> - Le service est testé indépendamment du HTTP.

### 1.2 Critères d'acceptation (testables)

| ID | Critère | Vérification |
|----|---------|-------------|
| AC-1 | Un module ou classe `BudgetConsumptionService` existe dans `backend/api/services/` ou `backend/api/` (structure TBD par l'équipe). | Existence du fichier, ex. `backend/api/services/budget_consumption.py` ou `backend/api/budget_consumption.py`. |
| AC-2 | Fonction `calculate_consumption(budget: Budget) -> BudgetConsumption` retourne un objet contenant `spent`, `remaining`, `percentage` (tous `Decimal`). | Appel de la fonction, vérification du type et de la valeur retournée. |
| AC-3 | Fonction `calculate_consumption_batch(budgets: Iterable[Budget]) -> Dict[int, BudgetConsumption]` retourne un dict `{budget_id: BudgetConsumption}` en une seule requête de base (pas N+1). | Monitoring du nombre de requêtes SQL ; vérification que toutes les dépenses sont chargées en une seule query SELECT. |
| AC-4 | `spent` est la somme des `Expense.amount` pour la catégorie du budget, l'utilisateur du budget, et la date dans `[period_start, period_end]` (bornes incluses). | Test avec expenses avant, après, et en dehors de la période ; vérification de la somme. |
| AC-5 | `remaining = amount - spent`. Peut être négatif si spent > amount. | Test avec spent > amount ; vérification que remaining < 0. |
| AC-6 | `percentage = (spent / amount) * 100`, arrondi à 2 décimales, jamais plafonné à 100. | Test avec spent = amount (percentage = 100.00), spent > amount (percentage > 100), spent < amount (percentage < 100). Vérification de l'arrondi Decimal. |
| AC-7 | Si le budget n'a aucune dépense, `spent = 0.00`, `remaining = amount`, `percentage = 0.00`. | Test avec budget sans expense ; vérification des valeurs. |
| AC-8 | Tous les montants retournés (`spent`, `remaining`, `percentage`) sont des instances `Decimal`, jamais `float` ou `int`. | Inspection de type avec `isinstance(value, Decimal)`. |
| AC-9 | Tous les montants sont quantifiés à 2 décimales (ex. `Decimal("123.45")`, pas `Decimal("123.4500")`). | Vérification que `.as_tuple().exponent == -2`. |
| AC-10 | Le calcul fonctionne correctement quand `alert_threshold` est NULL, zéro ou 100. | Test indépendant de alert_threshold (hors scope du calcul). |
| AC-11 | Le service est indépendant du HTTP ; les tests ne nécessitent pas de requête (test.Client, mock, etc.). | Tests purs (unittest, pytest) sans framework Django web. |
| AC-12 | Tests unitaires couvrent : un budget sans expenses, plusieurs budgets avec expenses croisées, arrondi Decimal, remaining négatif, percentage hors bornes. | Fichier `backend/api/tests/test_budget_consumption.py`. |
| AC-13 | Tous les champs du retour (`spent`, `remaining`, `percentage`) sont sérialisables en JSON sous forme de chaînes (ex. `"123.45"`), comme spécifié en `docs/api-design.md` §1.3. | Documentation du format de sérialisation en API (implémentation côté endpoint #47). |
| AC-14 | La documentation explique clairement que le service calcule à partir des données actuelles en base, sans cache ni totalisation stockée. | Présence dans la doc du service. |

---

## 2. Conception du service

### 2.1 Structure de données retournée

Le service retourne un objet `BudgetConsumption` (dataclass, namedtuple, ou classe simple) :

```python
@dataclass
class BudgetConsumption:
    spent: Decimal           # Montant dépensé, arrondi à 2 décimales
    remaining: Decimal       # Montant restant (amount - spent), peut être négatif, arrondi à 2 décimales
    percentage: Decimal      # Pourcentage de consommation ((spent / amount) * 100), arrondi à 2 décimales, non plafonné
```

**Notes :**
- Tous les champs sont `Decimal` en base.
- Lors de la sérialisation JSON (côté endpoint #47), chaque champ est converti en chaîne (ex. `"spent": "123.45"`).
- Le `percentage` n'est fourni que pour information ; le statut du budget (#51) est calculé séparément en comparant `percentage` à `alert_threshold`.

### 2.2 Fonction `calculate_consumption(budget: Budget) -> BudgetConsumption`

**Signature :**
```python
def calculate_consumption(budget: Budget) -> BudgetConsumption:
    """
    Calcule la consommation d'un budget unique.
    
    Args:
        budget: Instance Budget à analyser.
    
    Returns:
        BudgetConsumption avec spent, remaining, percentage.
    
    Notes:
        - Charge toutes les Expense du budget en base (pas de cache).
        - Tous les montants sont Decimal.
        - Si aucune expense, spent = 0.00.
    """
    # Implémentation à détailler en issue #50
```

**Comportement :**
1. Récupère toutes les `Expense` du même `user_id`, même `category_id`, et dont `date` est dans `[period_start, period_end]`.
2. Somme les `Expense.amount` pour obtenir `spent`.
3. Calcule `remaining = budget.amount - spent`.
4. Calcule `percentage = (spent / budget.amount) * 100` si `budget.amount > 0` (garanti par DB).
5. Arrondit `spent`, `remaining`, `percentage` à 2 décimales avec `Decimal.quantize()`.
6. Retourne `BudgetConsumption(spent, remaining, percentage)`.

**Cas limites :**
- Aucune dépense : `spent = Decimal("0.00")`, `remaining = budget.amount`, `percentage = Decimal("0.00")`.
- Dépense égale au budget : `spent = budget.amount`, `remaining = Decimal("0.00")`, `percentage = Decimal("100.00")`.
- Dépense supérieure au budget : `remaining < 0`, `percentage > 100`.

### 2.3 Fonction `calculate_consumption_batch(budgets: Iterable[Budget]) -> Dict[int, BudgetConsumption]`

**Signature :**
```python
def calculate_consumption_batch(budgets: Iterable[Budget]) -> Dict[int, BudgetConsumption]:
    """
    Calcule la consommation de plusieurs budgets en une seule requête de base.
    
    Args:
        budgets: Itérable de Budget (list, queryset, etc.).
    
    Returns:
        Dict {budget_id: BudgetConsumption} pour chaque budget.
    
    Notes:
        - Charge toutes les Expense en une seule requête SQL (pas N+1).
        - Agrège par (user_id, category_id, period) pour éviter les duplications.
    """
    # Implémentation à détailler en issue #50
```

**Comportement :**
1. Extrait les (user_id, category_id, period_start, period_end) uniques des budgets.
2. Charge toutes les `Expense` correspondantes en une seule requête (ex. avec `IN` ou `Q` complexe en Django ORM).
3. Agrège les expenses par (user_id, category_id) en mémoire (Python).
4. Pour chaque budget, applique le calcul d'une seule expense (logique identique à `calculate_consumption`).
5. Retourne `Dict[int, BudgetConsumption]` indexé par `budget.id`.

**Optimisation :**
- Une seule requête SQL : `Expense.objects.filter(Q(...) | Q(...) | ...)` avec une condition par budget.
- Agrégation en Python, pas en SQL, pour rester dans un service pur (pas de dépendance à Django ORM au niveau de l'agrégation).
- Alternativement : utiliser `select_related` / `prefetch_related` si les budgets arrivent avec expenses pre-chargées.

**Cas limites :**
- Aucun budget en entrée : retourner `{}`.
- Budgets sans expenses : tous les entries ont `spent = 0.00`.

### 2.4 Indépendance du HTTP et des migrations

Le service **ne dépend pas de :**
- Routes HTTP, serializers, views. (Hors scope — endpoint #47.)
- Migrations. (Aucune schema change.)
- Cache ou stockage. (Calcul dynamique.)

Le service **dépend de :**
- Modèles Django `Budget`, `Expense`, `User`, `Category` (définis en issues antérieures).
- `Decimal` (stdlib Python).
- Optionnellement, helpers Django ORM pour requêtes SQL (`QuerySet`, `Q`, `F`).

---

## 3. Tests unitaires

### 3.1 Fichier de test : `backend/api/tests/test_budget_consumption.py`

Les tests couvrent :

#### 3.1.1 Cas de succès — `calculate_consumption(budget)`

- **T-1 :** Budget sans expenses → `spent = 0.00`, `remaining = amount`, `percentage = 0.00`.
- **T-2 :** Budget avec une expense égale au montant → `spent = amount`, `remaining = 0.00`, `percentage = 100.00`.
- **T-3 :** Budget avec dépense inférieure au montant → `spent < amount`, `remaining > 0`, `percentage < 100`.
- **T-4 :** Budget avec dépense supérieure au montant → `spent > amount`, `remaining < 0`, `percentage > 100`.
- **T-5 :** Budget avec plusieurs expenses → somme correcte des montants.
- **T-6 :** Budget avec expense avant period_start → pas incluse dans le calcul.
- **T-7 :** Budget avec expense après period_end → pas incluse dans le calcul.
- **T-8 :** Budget avec expense exactement period_start → incluse (borne incluse).
- **T-9 :** Budget avec expense exactement period_end → incluse (borne incluse).
- **T-10 :** Budget avec multiple users/categories → seules les dépenses du bon user/category sont comptées.

#### 3.1.2 Précision décimale

- **T-11 :** Montants avec 2 décimales → conservés exactement (pas d'erreur float).
- **T-12 :** Arrondi à 2 décimales → `Decimal.quantize(Decimal("0.01"))`.
- **T-13 :** Percentage arrondi → exemple : spent = 123.456, amount = 100 → percentage = 123.46 % (pas 123.456).

#### 3.1.3 Batch — `calculate_consumption_batch(budgets)`

- **T-14 :** Aucun budget en entrée → retourner `{}`.
- **T-15 :** Un seul budget → résultat identique à `calculate_consumption`.
- **T-16 :** Plusieurs budgets du même user/category/period → tous inclus, pas N+1.
- **T-17 :** Budgets croisés (users différents, categories différentes) → agrégation correcte, pas de cross-contamination.
- **T-18 :** Une seule requête SQL pour tous les budgets (vérification du nombre de queries).
- **T-19 :** Retour d'un dict indexé par budget.id → clés correctes.

#### 3.1.4 Cas limites

- **T-20 :** Budget avec montant très petit (0.01) → pas d'erreur.
- **T-20 :** Budget avec montant très grand (99999999.99) → pas d'overflow.
- **T-21 :** Percentage = 0.01 / 1.00 * 100 = 1.00 % → arrondi correct.
- **T-22 :** Percentage = 99.99 / 100.00 * 100 = 99.99 % → pas plafonné.
- **T-23 :** Percentage > 100 % → pas plafonné à 100.

#### 3.1.5 Type et immuabilité

- **T-24 :** Tous les champs de retour sont `Decimal`.
- **T-25 :** Champs quantifiés à 2 décimales (vérifier `.as_tuple().exponent == -2`).
- **T-26 :** Modification d'une expense en base après appel du service → prochains appels reflètent les changements (pas de cache).

### 3.2 Fixture de test

Les tests utilisent des fixtures Django (pytest-django ou unittest) pour créer :
- Un utilisateur test.
- Plusieurs catégories test.
- Plusieurs budgets avec périodes variées.
- Plusieurs expenses avec montants et dates variées.

Exemple (pytest-django) :
```python
@pytest.fixture
def test_user():
    return User.objects.create_user(
        email="test@example.com",
        username="testuser",
        password="password123"
    )

@pytest.fixture
def test_category(test_user):
    return Category.objects.create(user=test_user, name="Food")

@pytest.fixture
def test_budget(test_user, test_category):
    return Budget.objects.create(
        user=test_user,
        category=test_category,
        amount=Decimal("100.00"),
        period_start=date(2026, 10, 1),
        period_end=date(2026, 10, 31),
        alert_threshold=Decimal("80.00")
    )

@pytest.fixture
def test_expense(test_user, test_category):
    return Expense.objects.create(
        user=test_user,
        category=test_category,
        amount=Decimal("25.50"),
        date=date(2026, 10, 15)
    )
```

### 3.3 Isolation et absence de dépendances HTTP

Tous les tests :
- Utilisent des modèles Django (fixtures pytest-django) ou `TestCase` Django.
- **N'utilisent pas** `client`, `live_server`, `RequestFactory`, ou tout mécanisme HTTP.
- **N'utilisent pas** de cache ou mock d'ORM (tests contre une DB de test réelle).
- S'exécutent avec `python manage.py test api.tests.test_budget_consumption` ou `pytest backend/api/tests/test_budget_consumption.py`.

---

## 4. Implémentation — Directives (hors scope de cette spec)

### 4.1 Choix technologiques à trancher

1. **Dataclass vs. namedtuple vs. classe simple** pour `BudgetConsumption`.
   - Recommandé : `@dataclass` (lisibilité, immuabilité optionnelle).

2. **Localisation du module**
   - Option A : `backend/api/services/budget_consumption.py`
   - Option B : `backend/api/budget_consumption.py`
   - Décision : à trancher par l'équipe (préférence pour Option A pour scalabilité).

3. **Agrégation en Python vs. SQL**
   - Le batch peut utiliser `Expense.objects.aggregate(Sum(...))` par budget (N requêtes), ou une seule requête chargée en Python.
   - Recommandé : une seule requête SQL + agrégation Python (plus lisible et performant).

### 4.2 Documentation du code

Le service doit inclure :
- Docstrings pour chaque fonction (args, returns, notes).
- Exemple d'utilisation en commentaire.
- Note sur les montants décimaux et l'absence de cache.

---

## 5. Hors de cette spécification

Les éléments suivants **ne sont pas couverts** par cette issue #50 :

1. **Routes API REST :** Exposition du service via `GET /api/budgets/`. À implémenter en issue #47.
2. **Statut de budget :** Logique déterminant `ok` / `warning` / `full` / `exceeded` basée sur le percentage. À implémenter en issue #51 (décision `docs/decisions/budget-thresholds.md` définit les règles).
3. **Sérialisation JSON :** Conversion de `Decimal` en chaînes pour l'API. À implémenter en #47.
4. **Frontend :** Affichage des budgets avec consommation. Hors MVP.
5. **Cache ou totalisation stockée :** Le service calcule dynamiquement, donc hors scope.
6. **Expenses supprimées logiquement (soft-delete) :** Le modèle `Expense` fait des suppressions physiques (DELETE SQL).

---

## 6. Points ouverts et risques

| Point | Impact | Mitigation |
|-------|--------|-----------|
| **Performance avec beaucoup d'expenses.** Si 100k+ expenses pour un budget, la requête SELECT ou l'agrégation Python pourrait être lente. | Latence accrue sur GET budgets. | Ajouter un index sur `(user_id, category_id, date)` ou précomputer avec trigger PostgreSQL (future optimization). |
| **Timezone et DateField.** `DateField` stocke une date sans heure. Les périodes `[period_start, period_end]` sont des jours entiers. Ambiguïté si expense.date en UTC vs. fuseau local. | Correctness du calcul si timezones mal gérées. | Documenter que `DateField` ignore les heures (contrat implicite). |
| **Localization du module.** Choix entre `services/` et racine de `api/` décide de la structure. | Scalabilité future des services. | Trancher avant implémentation. |
| **Null vs. 0 pour alert_threshold.** Le modèle Budget accepte `NULL` avec défaut 80. Le calcul en ignore (hors scope). | Confusion possibilité : le service ne retourne pas `alert_threshold` calculé. | Documenter que le statut (issue #51) gère le NULL/défaut. |

---

## 7. Références

- **Modèle Budget :** `backend/api/models.py`, issue #45
- **Modèle Expense :** `backend/api/models.py`, issue #34
- **Décision — Statuts de budget :** `docs/decisions/budget-thresholds.md`
- **API Design — Sérialisation Decimal :** `docs/api-design.md` §1.3
- **Issue #47 :** Endpoint GET budgets (consomme ce service)
- **Issue #51 :** Statut de budget (utilise le percentage du service)

---

*Dernière mise à jour : 2026-10-07. Document proposé par Product & Architecture agent. En attente d'approbation humaine avant implémentation par Full-Stack Development agent.*
