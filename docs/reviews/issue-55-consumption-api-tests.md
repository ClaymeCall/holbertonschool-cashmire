# Review — issue #55 (partie tests) : cohérence de la consommation budgétaire

- **Spec :** `docs/specs/issue-55-consumption-api-tests.md`
- **Branche / HEAD :** `test/54-55-56-budget-tests` / `2e21ad2` (worktree)
- **Date :** 2026-10-08
- **Périmètre diff :** `backend/api/tests.py` (+360 lignes, 0 suppression). Aucun autre fichier suivi modifié. Aucun fichier applicatif (views, models, serializers, services), aucune migration.

## Verdict

**Aucun finding bloquant.** 16/16 tests de la classe passent, suite complète `api` : 183/183 OK. Conforme à la spec (T-1 à T-16, AC-1 à AC-13).

## Exécution

- Commande : `manage.py test api.tests.BudgetConsumptionViaExpenseEndpointsTests` : **Ran 16 tests, OK**.
- Commande : `manage.py test api` (suite complète) : **Ran 183 tests, OK**.
- Environnement : Python 3.12 + `backend/requirements.txt` dans un venv hors repo, Postgres local (`POSTGRES_HOST=localhost`), au lieu de `docker compose run --rm api`. Même base PostgreSQL et même suite ; non rejoué via Docker.

## Couverture des critères d'acceptation

| AC | Tests | Résultat |
|----|-------|----------|
| AC-1 création dans catégorie/période | T-1, T-10 | Pass |
| AC-2 bornes incluses | T-2 (+ T-9 borne `period_end` après PATCH) | Pass |
| AC-3 hors période / autre catégorie | T-3, T-4 | Pass |
| AC-4 création rejetée (400/404) | T-5 | Pass |
| AC-5 PATCH montant | T-6 | Pass |
| AC-6 PATCH catégorie (retrait + ajout) | T-7, T-8, T-10 | Pass |
| AC-7 PATCH date (sortie + retour) | T-9 | Pass |
| AC-8 PUT | T-11 | Pass |
| AC-9 mutation rejetée PATCH/PUT | T-5, T-12 | Pass |
| AC-10 DELETE | T-13 | Pass |
| AC-11 somme Decimal exacte | T-14 | Pass |
| AC-12 remaining négatif, percentage non plafonné | T-15 | Pass |
| AC-13 dépense d'un autre user | T-12, T-16 | Pass |

## Conformité par cas

| Cas | Conforme | Remarque |
|-----|----------|----------|
| T-1 à T-15 | Oui | Étapes, valeurs et ordre conformes à la spec. |
| T-5 | Oui | Les 6 sous-cas sont présents. Le `count() == 1` est vérifié après le POST 404. |
| T-12 | Oui | |
| T-16 | Oui, avec redondance | Voir N-1. Spec autorise la fusion avec T-12 ; l'implémentation garde les deux. |
| Helpers §4.2 | Oui | `post_expense`, `expense_url`, `get_consumption` identiques à la spec, dans la classe. |
| Hors périmètre §5 | Oui | Aucun test de `status` / `warning` / `full` / `exceeded` / `alert_threshold`. Les seules occurrences de `status` sont `status_code`. Aucun test sur `GET /api/budgets/{id}/`. |

## Vérification des valeurs attendues

Les valeurs ont été recalculées à la main à partir de `calculate_consumption_batch` (`backend/api/services/budget_consumption.py`), sans copier la sortie des tests :

- T-10 : 25.50 / 200 = 12.75 %, remaining 174.50.
- T-11 : 40.05 / 500 = 8.01 %, remaining 459.95.
- T-14 : 0.30 / 500 = 0.06 %, remaining 499.70.
- T-15 : 600 / 500 = 120.00 %, remaining -100.00.

Tous les quotients sont exacts en `Decimal`, donc aucune dépendance au mode d'arrondi `ROUND_HALF_EVEN` (R-5 de la spec).

## Vérifications de sensibilité (copie jetable, source du dépôt non modifiée)

Une copie du backend a été placée dans `scratchpad/mut/` (hors worktree) pour ces mutations :

1. Borne `period_end` rendue exclusive (`<` au lieu de `<=`) dans `calculate_consumption_batch` : **2 échecs** (`test_create_expenses_on_both_period_boundaries_are_counted`, `test_patch_date_moves_expense_out_of_period_and_back_on_boundary`). Détectée.
2. Filtre de catégorie Python neutralisé (`and True`) : **1 échec** (`test_patch_category_moves_expense_between_two_budgets`). Voir F-2 : ce n'est pas un trou de test.

Le dossier `scratchpad/mut/` peut être supprimé ; il n'est pas dans le repo.

## Findings

### Bloquants

Aucun.

### Non bloquants

- **N-1 (redondance).** `test_foreign_expense_mutations_return_404_and_never_touch_budget` recouvre `test_rejected_put_or_patch_on_foreign_expense_does_not_change_consumption` pour PATCH et PUT. Seul le `DELETE` est propre à T-16. Suggestion : fusionner, ou garder T-16 uniquement pour le `DELETE`. Pas de risque de faux positif.
- **N-2 (style).** 5 lignes ajoutées dépassent 88 caractères (ex. `test_expense_over_budget_yields_negative_remaining_and_uncapped_percentage`, docstrings, la ligne `{"category_id": ..., "amount": "0.00", ...}` de T-5). Le fichier existant en contient déjà 13, donc non gating.
- **N-3 (environnement).** Exécution faite sur Postgres local et non via `docker compose run --rm api`. À rejouer dans le conteneur avant merge pour confirmer.

### Faux positifs / points vérifiés et écartés

- **F-1 Flakiness dates.** Aucune dépendance à `date.today()` ni `timezone.now()`. Toutes les dates sont fixes en octobre 2026. Aucun test ne dépend de l'ordre d'exécution : chaque test est isolé par transaction `TestCase`.
- **F-2 Mutation du filtre de catégorie non détectée par T-4.** Le filtre `category=budget.category` est aussi appliqué dans le `Q` SQL. Le test Python `expense.category_id == budget.category_id` est donc redondant pour la requête. T-4 ne peut pas échouer sur cette seule mutation, la catégorie étant filtrée côté base. Ce n'est pas une faiblesse de test : T-4 couvrirait une mutation du `Q` SQL (non exécutée ici), et T-10 couvre le cas à deux budgets.
- **F-3 Ordre de `categories.first()`.** `Category` a `Meta.ordering = ["id"]` (`models.py`), donc le choix de la catégorie de référence est déterministe.
- **F-4 Tautologie.** Les valeurs sont des littéraux recalculés à la main, pas des copies de la sortie. Les mutations 1 ci-dessus montrent qu'un changement de comportement réel fait échouer les tests.
- **F-5 Dépendance à la somme `Decimal`.** T-14 passerait avec une somme float arrondie par `quantize`. Un float ferait cependant échouer `quantize` (pas d'attribut sur `float`), donc la régression serait détectée à l'exécution. Aucune action.

## Hors périmètre de cette review

- Aucune entrée `docs/agentic-log.md` écrite : le périmètre demandé se limite à ce fichier de review.
- Frontend non concerné.
