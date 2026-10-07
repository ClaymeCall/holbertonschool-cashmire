# SPÉCIFICATION — Modèle Budget et migration (Issue #45)

- **Issue :** #45 « Create Budget model and migration with uniqueness constraint »
- **Statut :** Proposition. Non approuvée. Un humain doit valider cette spécification avant la mise en œuvre.
- **Auteur :** Agent Product & Architecture
- **Portée :** Modèle de données (`Budget`), migration Django, tests du modèle uniquement. Aucun endpoint API, aucune interface frontend.
- **Codebase examiné à :** branche `feat/45-budget-model`, commits jusqu'au 2026-10-07

---

## 0. Introduction

Cette spécification propose l'implémentation du modèle `Budget` — entité centrale du pilier « Budget Tracking » du MVP Cashmire. Le modèle `Budget` a été défini dans l'ERD (`docs/erd.md`, section BUDGET) et approuvé par l'équipe. Cette spec traduit cette définition en modèle Django concret et en migration PostgreSQL, avec focus sur les contraintes d'intégrité, les indices de performance, et le plan de tests.

**Contexte :**
- Issue #20 a implémenté le modèle `User`.
- Issue #33 a implémenté le modèle `Category` avec propriété scoped (user-scoped).
- Issue #45 implémente `Budget`, qui référence à la fois `User` (ownership) et `Category` (domaine du budget).
- Issues futures implanteront `Expense` et exposeront les routes API pour les budgets.

---

## 1. Énoncé du problème et critères d'acceptation

### 1.1 Récit utilisateur

> En tant que développeur (agent Full-Stack Development), je dois implémenter le modèle `Budget` de manière robuste et testable, afin que :
>
> - Chaque budget s'applique à exactement une catégorie d'un utilisateur, sur une période fixe (date de début, date de fin).
> - Les budgets d'un même utilisateur pour la même catégorie et la même période ne peuvent pas être en doublon (contrainte d'unicité composée en base de données).
> - Les montants budgétés sont toujours positifs et stockés avec précision décimale (`NUMERIC(10, 2)`).
> - Le seuil d'alerte (alert_threshold) est un pourcentage entre 0 et 100 (optionnel, défaut 80).
> - La suppression d'une catégorie empêche la suppression du budget si un budget y est lié (RESTRICT).
> - La suppression d'un utilisateur supprime automatiquement ses budgets en cascade (CASCADE).
> - Les tests couvrent la création de budgets valides, le rejet des contraintes violées, et la validation des champs monétaires.

### 1.2 Critères d'acceptation (testables)

| ID | Critère | Vérification |
|----|---------|-------------|
| AC-1 | Le modèle `Budget` existe dans `backend/api/models.py` avec tous les champs décrits ci-dessous (section 2). | Lecture du fichier `models.py`. |
| AC-2 | La migration `backend/api/migrations/0003_budget.py` (ou numéro suivant) crée la table `budget` avec la structure complète (champs, contraintes, indices). | Vérification de la migration via `django-admin showmigrations` et examen du fichier `.py`. |
| AC-3 | La migration applique sans erreur sur une base de données PostgreSQL vierge. | Exécution de `python manage.py migrate api` sur une base fraîche. |
| AC-4 | Le champ `amount` est `NUMERIC(10, 2)` en base (précision décimale, jamais float). Le modèle Django utilise `DecimalField(max_digits=10, decimal_places=2)`. | Vérification dans la migration et le modèle Django. |
| AC-5 | Le champ `alert_threshold` est `NUMERIC(5, 2)` (stocke des pourcentages ex. 80.50), optionnel (null=True), défaut 80.00. Contrainte CHECK en base : `alert_threshold >= 0 AND alert_threshold <= 100` (si non NULL). | Vérification dans la migration (`AddConstraint` ou `RunSQL`) et le modèle Django. |
| AC-6 | Les champs `period_start` et `period_end` sont des `DateField`, et une contrainte CHECK en base garantit `period_end >= period_start`. | Vérification dans la migration et le modèle (ou via clean method). |
| AC-7 | Contrainte composée UNIQUE en base : `UNIQUE (user_id, category_id, period_start, period_end)`. Empêche les budgets en doublon. | Présence de `UniqueConstraint` dans le modèle Django ou `UNIQUE` SQL dans la migration. |
| AC-8 | FK `user_id` → `User(id)` avec `ON DELETE CASCADE`. Suppression d'un utilisateur supprime tous ses budgets. | Vérification dans le modèle (ForeignKey avec `on_delete=models.CASCADE`). |
| AC-9 | FK `category_id` → `Category(id)` avec `ON DELETE PROTECT`. Impossible de supprimer une catégorie si des budgets la référencent. | Vérification dans le modèle (ForeignKey avec `on_delete=models.PROTECT`). |
| AC-10 | Indices recommandés créés pour optimiser les requêtes courantes : `idx_budget_user_id`, `idx_budget_user_id_period`. | Présence de `db_index=True` sur les champs pertinents ou `indexes` dans Meta. |
| AC-11 | Les timestamps `created_at` (auto_now_add) et `updated_at` (auto_now) sont présents. | Vérification dans le modèle Django. |
| AC-12 | Contrainte CHECK en base sur `amount > 0` (montant strictement positif). | Présence dans la migration (AddConstraint ou RunSQL). |
| AC-13 | Des tests unitaires couvrent au minimum : création de budgets valides, rejet des budgets en doublon (UniqueConstraint), rejet des montants <= 0, rejet des périodes invalides (end < start), rejet des alert_threshold hors limites. | Fichier `backend/api/tests/test_budget_model.py` avec tests pour chaque cas. |
| AC-14 | Les tests utilisent `pytest` (ou `unittest` natif Django) et s'exécutent sans erreur avec `python manage.py test api.tests.test_budget_model` ou `pytest backend/api/tests/test_budget_model.py`. | Exécution des tests. |

---

## 2. Delta du modèle de données

### 2.1 Table `budget`

Basée sur la définition `docs/erd.md` (section BUDGET), le modèle Django et la migration créent la table suivante :

| Champ | Type PostgreSQL | Contraintes | Description |
|-------|-----|-----------|------------|
| `id` | `BIGSERIAL` | PRIMARY KEY | Clé primaire auto-incrémentée. Django `BigAutoField`. |
| `user_id` | `BIGINT` | NOT NULL, FK → `auth_user.id` | Propriétaire du budget. Suppression en cascade (ON DELETE CASCADE). Chaque budget appartient à exactement un utilisateur. Voir issue #20 pour le modèle User. |
| `category_id` | `BIGINT` | NOT NULL, FK → `api_category.id` | Catégorie couverte par le budget. Suppression protégée (ON DELETE PROTECT). Chaque budget s'applique à exactement une catégorie. **Validation applicative requise :** S'assurer que `category.user_id == budget.user_id` (la catégorie appartient à l'utilisateur du budget). |
| `amount` | `NUMERIC(10, 2)` | NOT NULL, CHECK(amount > 0) | Montant budgété (limite). **Obligatoirement NUMERIC, jamais float ou double.** Peut stocker jusqu'à 99999999.99. Contrainte : montant strictement positif. |
| `period_start` | `DATE` | NOT NULL | Début de la période budgétaire (ex. 2026-01-01). |
| `period_end` | `DATE` | NOT NULL | Fin de la période budgétaire (ex. 2026-01-31). Contrainte CHECK : `period_end >= period_start`. |
| `alert_threshold` | `NUMERIC(5, 2)` | NULL, DEFAULT 80.00 | Seuil d'alerte en pourcentage (ex. 80 = 80 %). Optionnel. Déclenche une alerte quand les dépenses dépassent ce seuil (logique d'alerte implémentée dans issue future). Contrainte CHECK : `alert_threshold BETWEEN 0 AND 100` (si non NULL). |
| `created_at` | `TIMESTAMP` | NOT NULL, DEFAULT now() | Horodatage de création. Django `DateTimeField(auto_now_add=True)`. |
| `updated_at` | `TIMESTAMP` | NOT NULL, DEFAULT now() | Horodatage de dernière modification. Django `DateTimeField(auto_now=True)`. |

### 2.2 Contraintes composées

```sql
UNIQUE (user_id, category_id, period_start, period_end)
```

Un seul budget par (utilisateur, catégorie, période). Empêche les budgets en doublon.

### 2.3 Contraintes d'intégrité explicites en base

```sql
CHECK (amount > 0)                    -- Montant strictement positif
CHECK (period_end >= period_start)    -- Fin >= début
CHECK (alert_threshold BETWEEN 0 AND 100) -- Seuil valide (si non NULL)
```

### 2.4 Indices suggérés

Pour optimiser les requêtes courantes (lister les budgets d'un utilisateur, filtrer par période) :

- **`idx_budget_user_id`** : Index simple sur `user_id` (requêtes « lister les budgets d'un utilisateur »).
- **`idx_budget_user_id_period`** : Index composite sur `(user_id, period_start, period_end)` (requêtes « budgets actifs d'un utilisateur dans une plage de dates »).

Optionnel : Index sur `category_id` si les requêtes par catégorie deviennent courantes.

### 2.5 Modèle Django `Budget`

```python
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class Budget(models.Model):
    user = models.ForeignKey(
        "api.User",
        on_delete=models.CASCADE,
        related_name="budgets",
    )
    category = models.ForeignKey(
        "api.Category",
        on_delete=models.PROTECT,
        related_name="budgets",
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    period_start = models.DateField()
    period_end = models.DateField()
    alert_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        default=Decimal("80.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "category", "period_start", "period_end"],
                name="unique_budget_per_user_category_period",
            ),
            models.CheckConstraint(
                check=models.Q(amount__gt=0),
                name="budget_amount_positive",
            ),
            models.CheckConstraint(
                check=models.Q(period_end__gte=models.F("period_start")),
                name="budget_period_end_gte_start",
            ),
            models.CheckConstraint(
                check=models.Q(alert_threshold__isnull=True) | models.Q(alert_threshold__gte=0, alert_threshold__lte=100),
                name="budget_alert_threshold_valid_range",
            ),
        ]
        indexes = [
            models.Index(fields=["user"], name="idx_budget_user_id"),
            models.Index(fields=["user", "period_start", "period_end"], name="idx_budget_user_period"),
        ]

    def __str__(self):
        return f"Budget {self.id} — User {self.user.id}, Category {self.category.name}, {self.period_start} to {self.period_end}"
```

**Notes importantes :**
- Le modèle utilise les validators Django (`MinValueValidator`, `MaxValueValidator`) en plus des contraintes SQL pour défense en profondeur.
- Les Check constraints Django se transforment en CHECK SQL lors de la migration (Django 3.2+).
- La clé étrangère `category` utilise `on_delete=models.PROTECT` pour empêcher la suppression d'une catégorie si des budgets la référencent.
- La clé étrangère `user` utilise `on_delete=models.CASCADE` pour supprimer automatiquement les budgets si l'utilisateur est supprimé.
- `alert_threshold` accepte `None` (NULL en base) ; la validation permet 0 à 100 si non NULL.

---

## 3. Implémentation de la migration

### 3.1 Fichier de migration : `backend/api/migrations/0003_budget.py`

La migration crée le modèle `Budget` et ajoute les contraintes CHECK et indices recommandés. Exemple de structure :

```python
# Generated by Django X.Y.Z on 2026-10-07

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal
import django.core.validators

class Migration(migrations.Migration):
    dependencies = [
        ('api', '0002_category'),
    ]

    operations = [
        migrations.CreateModel(
            name='Budget',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))])),
                ('period_start', models.DateField()),
                ('period_end', models.DateField()),
                ('alert_threshold', models.DecimalField(blank=True, decimal_places=2, default=Decimal('80.00'), max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0')), django.core.validators.MaxValueValidator(Decimal('100'))])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='budgets', to='api.category')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='budgets', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['id'],
            },
        ),
        migrations.AddConstraint(
            model_name='budget',
            constraint=models.UniqueConstraint(fields=('user', 'category', 'period_start', 'period_end'), name='unique_budget_per_user_category_period'),
        ),
        migrations.AddConstraint(
            model_name='budget',
            constraint=models.CheckConstraint(check=models.Q(('amount__gt', 0)), name='budget_amount_positive'),
        ),
        migrations.AddConstraint(
            model_name='budget',
            constraint=models.CheckConstraint(check=models.Q(('period_end__gte', models.F('period_start'))), name='budget_period_end_gte_start'),
        ),
        migrations.AddConstraint(
            model_name='budget',
            constraint=models.CheckConstraint(check=models.Q(('alert_threshold__isnull', True), ('alert_threshold__gte', 0), ('alert_threshold__lte', 100)), name='budget_alert_threshold_valid_range'),
        ),
        migrations.AddIndex(
            model_name='budget',
            index=models.Index(fields=['user'], name='idx_budget_user_id'),
        ),
        migrations.AddIndex(
            model_name='budget',
            index=models.Index(fields=['user', 'period_start', 'period_end'], name='idx_budget_user_period'),
        ),
    ]
```

### 3.2 Ordre d'exécution des migrations

1. `0001_initial` (modèle `User`, existant)
2. `0002_category` (modèle `Category`, existant)
3. `0003_budget` (modèle `Budget`, nouvelle) ← cette issue

Aucune seed data n'est requise pour les budgets (contrairement aux catégories). Les budgets sont créés par les utilisateurs via l'API (issue future).

---

## 4. Plan de tests du modèle

Les tests du modèle `Budget` sont implémentés dans `backend/api/tests/test_budget_model.py`. Ils couvrent :

### 4.1 Cas de succès (création valide)

- Créer un budget valide avec tous les champs obligatoires et optionnels.
- Créer un budget sans `alert_threshold` (valeur par défaut 80.00).
- Créer un budget avec `alert_threshold = null`.
- Créer plusieurs budgets pour différentes catégories du même utilisateur.
- Créer plusieurs budgets pour la même catégorie sur des périodes différentes.

### 4.2 Contrainte UNIQUE composée

- Tenter de créer deux budgets identiques (même user, même category, même period) → exception IntegrityError.
- Vérifier que deux budgets (même user, même category) avec des périodes différentes sont admis.
- Vérifier que deux budgets (même user, différentes categories) avec la même période sont admis.

### 4.3 Validation du montant (`amount`)

- Rejeter `amount = 0` → CheckConstraint violation.
- Rejeter `amount < 0` → CheckConstraint violation et/ou validator.
- Accepter `amount = 0.01` (minimal positif).
- Accepter `amount = 99999999.99` (maximal, 10 chiffres).
- Vérifier la précision décimale : `amount = 123.45` est stocké exactement, jamais arrondis.

### 4.4 Validation des périodes

- Rejeter `period_end < period_start` → CheckConstraint violation.
- Accepter `period_end = period_start` (budget sur 1 jour).
- Accepter `period_end > period_start` (budget normal).

### 4.5 Validation de `alert_threshold`

- Accepter `alert_threshold = null` (optionnel).
- Accepter `alert_threshold = 80.00` (défaut).
- Accepter `alert_threshold = 0` (valide).
- Accepter `alert_threshold = 100` (valide, limite haute).
- Rejeter `alert_threshold = -0.01` → CheckConstraint violation.
- Rejeter `alert_threshold = 100.01` → CheckConstraint violation.

### 4.6 Intégrité référentielle et CASCADE/PROTECT

- Supprimer un utilisateur → ses budgets sont supprimés en cascade.
- Tenter de supprimer une catégorie avec budgets associés → PROTECT empêche la suppression (IntegrityError).
- Vérifier que la suppression d'une catégorie sans budgets associés réussit.

### 4.7 Timestamps (`created_at`, `updated_at`)

- `created_at` est défini à la création, ne change jamais.
- `updated_at` est défini à la création, se met à jour à chaque modification (save).
- Les deux sont en format `DateTimeField` (datetime avec timezone, si applicable).

---

## 5. Hors de cette spécification

Les éléments suivants **ne sont pas couverts** par cette issue #45 :

1. **Routes API REST :** Création, lecture, mise à jour, suppression de budgets via HTTP. À implémenter en issue future.
2. **Sérialisation :** Comment sérialiser un `Budget` en JSON (champs exposés, format des montants, etc.). À documenter en `docs/api-design.md` (issue #7 ou ultérieure).
3. **Frontend :** Interface SvelteKit pour créer/afficher les budgets. Hors MVP, à planifier.
4. **Logique d'alerte :** Détection quand les dépenses d'une catégorie dépassent le seuil `alert_threshold`. À implémenter ultérieurement.
5. **Rapport consommation vs. budget :** Calcul de « dépensé vs. budgété » pour une période donnée. À implémenter quand les routes budgets/expenses seront opérationnelles.

---

## 6. Points ouverts et risques

1. **Validation applicative de l'ownership :** Le modèle Django n'applique pas l'unicité de `category.user_id == budget.user_id` automatiquement (c'est une règle métier). La migration doit documenter que l'API doit vérifier cela lors de la création/modification.

2. **Index sur `category_id` :** Pas d'index simple sur `category_id` dans cette spec. À considérer si les requêtes « budgets d'une catégorie, tous utilisateurs confondus » deviennent courantes.

3. **Migration rétroactive :** Si des budgets existaient déjà (hypothèse peu probable en MVP), la migration comporterait une étape de backfill. Non applicable ici (premier déploiement).

4. **Soft-delete :** Comme `Expense`, le modèle `Budget` n'a pas de colonne `is_active`. Une suppression est physique. Si soft-delete devient requise ultérieurement, une migration l'ajouterait.

5. **Timezone et DateField :** `DateField` stocke une date sans heure ni timezone. Cela convient à « période du 1er au 30 janvier 2026 » sans détails horaires. Si besoin de précision horaire (ex. « 15 décembre 14:00 UTC »), migrer vers `DateTimeField`.

---

## 7. Références

- **ERD :** `docs/erd.md` (section BUDGET)
- **Issue #20 :** Modèle User — `backend/api/models.py` (classe `User`)
- **Issue #33 :** Modèle Category — `backend/api/models.py` (classe `Category`)
- **Issue #7 :** Contrat API REST — `docs/api-design.md`
- **Migrations existantes :** `backend/api/migrations/0001_initial.py`, `0002_category.py`
- **Configuration Django :** `backend/cashmire/settings.py` (DEFAULT_AUTO_FIELD = BigAutoField, DATABASES = PostgreSQL)
- **Workflow :** `docs/git-workflow.md`, `docs/agentic-log.md`

---

*Dernière mise à jour : 2026-10-07. Document proposé par Product & Architecture agent. En attente d'approbation humaine avant implémentation par Full-Stack Development agent.*
