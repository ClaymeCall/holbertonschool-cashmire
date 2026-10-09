# Entity-Relationship Diagram (ERD) — Cashmire

> **IMPLÉMENTÉE**
> 
> Cet ERD a été approuvée après résolution de l'issue #6 (propriété des catégories) et correspond désormais aux modèles Django réels (`backend/api/models.py`, migrations `0001` à `0004`). Voir `docs/specs/issue-5-erd.md` pour le détail complet de l'ERD d'origine, et `docs/specs/issue-6-category-ownership.md` pour la justification de la décision sur les catégories.

---

## Diagramme de relations

```mermaid
erDiagram
    USER ||--o{ EXPENSE : creates
    USER ||--o{ BUDGET : creates
    USER ||--o{ CATEGORY : owns
    CATEGORY ||--o{ EXPENSE : categorizes
    CATEGORY ||--o{ BUDGET : constrains

    USER {
        bigint id PK
        string email UK
        string password
        string username UK
        string first_name
        string last_name
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    CATEGORY {
        bigint id PK
        bigint user_id FK
        string name
        text description
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    EXPENSE {
        bigint id PK
        bigint user_id FK
        bigint category_id FK
        numeric amount
        text description
        date date
        timestamp created_at
        timestamp updated_at
    }

    BUDGET {
        bigint id PK
        bigint user_id FK
        bigint category_id FK
        numeric amount
        date period_start
        date period_end
        numeric alert_threshold
        timestamp created_at
        timestamp updated_at
    }
```

**Légende :**
- `PK` = Primary Key (clé primaire)
- `FK` = Foreign Key (clé étrangère)
- `UK` = Unique Key (unicité)
- `||--o{` = One-to-Many (1:N)
- `||--||` = One-to-One (1:1)

---

## Spécification détaillée des entités

### USER — Utilisateurs

| Champ | Type | Contraintes | Description |
|-------|------|-----------|------------|
| `id` | `BIGSERIAL` | PRIMARY KEY | Clé primaire auto-incrémentée. Django `BigAutoField`. |
| `email` | `VARCHAR(254)` | UNIQUE, NOT NULL | Adresse email unique. Utilisée pour la connexion. |
| `password` | `VARCHAR(255)` | NOT NULL | Hash du mot de passe (généré par Django). Jamais en clair. Aligné avec Django User par défaut. |
| `username` | `VARCHAR(150)` | UNIQUE, NOT NULL | Nom d'utilisateur unique pour login ou affichage. |
| `first_name` | `VARCHAR(150)` | NULL | Prénom optionnel. |
| `last_name` | `VARCHAR(150)` | NULL | Nom de famille optionnel. |
| `is_active` | `BOOLEAN` | NOT NULL, DEFAULT true | Indicateur de compte actif. Soft-delete via désactivation. |
| `created_at` | `TIMESTAMP` | NOT NULL, DEFAULT now() | Horodatage de création du compte. |
| `updated_at` | `TIMESTAMP` | NOT NULL, DEFAULT now() | Horodatage de dernière modification. |

**Modèle utilisateur personnalisé :** le `User` Django par défaut (`auth.User`) ne rend pas `email` unique. Cashmire utilise donc un modèle personnalisé, sous-classe de `AbstractUser`, qui redéfinit `email` avec `unique=True` (contrainte `UNIQUE` en base). `AUTH_USER_MODEL` doit pointer vers ce modèle **avant** la première migration qui référence l'utilisateur (`Expense`, `Budget`, `Category`) : changer de modèle utilisateur après coup est coûteux en Django. L'unicité est donc garantie par la base de données et non par une simple validation applicative.

**Indices suggérés :**
- Index sur `email` (pour les logins)
- Index sur `username` (pour les requêtes de recherche utilisateur)

---

### CATEGORY — Catégories de dépenses

| Champ | Type | Contraintes | Description |
|-------|------|-----------|------------|
| `id` | `BIGSERIAL` | PRIMARY KEY | Clé primaire auto-incrémentée. |
| `user_id` | `BIGINT` | FK → USER.id, NOT NULL | Propriétaire de la catégorie. Chaque catégorie appartient à exactement un utilisateur. Suppression en cascade (ON DELETE CASCADE). Voir decision `docs/decisions/category-ownership.md` (issue #6). |
| `name` | `VARCHAR(100)` | NOT NULL | Nom de la catégorie (ex. « Alimentation », « Transport »). |
| `description` | `TEXT` | NULL | Description optionnelle pour la catégorie. |
| `is_active` | `BOOLEAN` | NOT NULL, DEFAULT true | Indicateur de catégorie active. |
| `created_at` | `TIMESTAMP` | NOT NULL, DEFAULT now() | Horodatage de création. |
| `updated_at` | `TIMESTAMP` | NOT NULL, DEFAULT now() | Horodatage de dernière modification. |

**Contraintes composées :**
```sql
UNIQUE (user_id, name)
```
Un utilisateur ne peut pas avoir deux catégories portant le même nom.

**Indices suggérés :**
- Index sur `user_id` (requêtes « lister les catégories d'un utilisateur »)
- Index sur `(user_id, name)` (requêtes « chercher une catégorie par nom pour un utilisateur »)

---

### EXPENSE — Dépenses

| Champ | Type | Contraintes | Description |
|-------|------|-----------|------------|
| `id` | `BIGSERIAL` | PRIMARY KEY | Clé primaire auto-incrémentée. |
| `user_id` | `BIGINT` | FK → USER.id, NOT NULL | Propriétaire de la dépense. Chaque dépense appartient à un utilisateur. |
| `category_id` | `BIGINT` | FK → CATEGORY.id, NOT NULL | Catégorie de la dépense. Chaque dépense a exactement une catégorie. **Important :** L'API doit valider que `category.user_id == expense.user_id` (la catégorie appartient à l'utilisateur de la dépense). |
| `amount` | `NUMERIC(10, 2)` | NOT NULL, CHECK(amount > 0) | Montant de la dépense. **Obligatoirement NUMERIC, jamais float ou double.** Peut stocker jusqu'à 99999999.99. Contrainte : montant strictement positif. |
| `description` | `TEXT` | NULL | Description optionnelle de la dépense. |
| `date` | `DATE` | NOT NULL | Date de la dépense (peut différer de `created_at` pour enregistrement rétroactif). |
| `created_at` | `TIMESTAMP` | NOT NULL, DEFAULT now() | Horodatage de création en base (métadonnée système). |
| `updated_at` | `TIMESTAMP` | NOT NULL, DEFAULT now() | Horodatage de dernière modification. |

**Indices suggérés :**
- Index sur `user_id` (pour lister les dépenses d'un utilisateur)
- Index sur `(user_id, date)` ou `(user_id, category_id, date)` (pour filtres combinés et agrégations)
- Index sur `date` (pour les requêtes par plage de dates)

**Contraintes d'intégrité :**
- `amount > 0` (via CHECK SQL, appliqué à la base de données)
- FK `user_id` → `USER(id)` avec CASCADE on DELETE (si un utilisateur est supprimé, ses dépenses le sont aussi)
- FK `category_id` → `CATEGORY(id)` (avec RESTRICT ou SET NULL selon la politique de suppression de catégories)
- **Validation applicative :** S'assurer que `category.user_id == user_id` avant d'enregistrer une dépense.

---

### BUDGET — Budgets

| Champ | Type | Contraintes | Description |
|-------|------|-----------|------------|
| `id` | `BIGSERIAL` | PRIMARY KEY | Clé primaire auto-incrémentée. |
| `user_id` | `BIGINT` | FK → USER.id, NOT NULL | Propriétaire du budget. Chaque budget appartient à un utilisateur. |
| `category_id` | `BIGINT` | FK → CATEGORY.id, NOT NULL | Catégorie couverte par le budget. Chaque budget s'applique à une catégorie. **Important :** L'API doit valider que `category.user_id == budget.user_id` (la catégorie appartient à l'utilisateur du budget). |
| `amount` | `NUMERIC(10, 2)` | NOT NULL, CHECK(amount > 0) | Montant budgété (limite). **Obligatoirement NUMERIC, jamais float.** Contrainte : montant strictement positif. |
| `period_start` | `DATE` | NOT NULL | Début de la période budgétaire (ex. 2026-01-01). |
| `period_end` | `DATE` | NOT NULL, CHECK(period_end >= period_start) | Fin de la période budgétaire (ex. 2026-01-31). Contrainte : la fin doit être >= au début. |
| `alert_threshold` | `NUMERIC(5, 2)` | NULL, DEFAULT 80.00, CHECK(alert_threshold BETWEEN 0 AND 100) | Seuil d'alerte en pourcentage (ex. 80 = 80 %). Optionnel. Déclenche une alerte quand les dépenses dépassent ce seuil. Implémentation de la logique dans future issue. Contrainte : valeur entre 0 et 100. |
| `created_at` | `TIMESTAMP` | NOT NULL, DEFAULT now() | Horodatage de création. |
| `updated_at` | `TIMESTAMP` | NOT NULL, DEFAULT now() | Horodatage de dernière modification. |

**Indices suggérés :**
- Index sur `user_id` (pour lister les budgets d'un utilisateur)
- Index sur `(user_id, period_start, period_end)` (pour requêtes par plage de dates)

**Contraintes composées :**

```sql
UNIQUE (user_id, category_id, period_start, period_end)
```

Un seul budget par (utilisateur, catégorie, période). Empêche les budgets en doublon.

**Contraintes d'intégrité :**
- `amount > 0` (via CHECK SQL)
- `period_start <= period_end` (via CHECK SQL, appliqué à la base de données)
- `alert_threshold` entre 0 et 100 (via CHECK SQL si non NULL)
- FK `user_id` → `USER(id)` avec CASCADE on DELETE
- FK `category_id` → `CATEGORY(id)` avec RESTRICT (ne pas supprimer une catégorie tant qu'elle a des budgets actifs)
- **Validation applicative :** S'assurer que `category.user_id == user_id` avant d'enregistrer un budget.

---

## Relations et cardinalités

| Relation | Cardinalité | Sens | Description |
|----------|-------------|------|------------|
| `USER` → `EXPENSE` | 1:N | Un utilisateur crée plusieurs dépenses (zéro ou plus). Une dépense appartient à exactement un utilisateur. | Join: `EXPENSE.user_id = USER.id` |
| `USER` → `BUDGET` | 1:N | Un utilisateur crée plusieurs budgets (zéro ou plus). Un budget appartient à exactement un utilisateur. | Join: `BUDGET.user_id = USER.id` |
| `USER` → `CATEGORY` | 1:N | Un utilisateur possède plusieurs catégories (zéro ou plus). Une catégorie appartient à exactement un utilisateur. | Join: `CATEGORY.user_id = USER.id` ; Décision : issue #6 ✓ |
| `CATEGORY` → `EXPENSE` | 1:N | Une catégorie peut avoir plusieurs dépenses (zéro ou plus). Une dépense appartient à exactement une catégorie. | Join: `EXPENSE.category_id = CATEGORY.id` |
| `CATEGORY` → `BUDGET` | 1:N | Une catégorie peut avoir plusieurs budgets (ex. un par mois). Un budget s'applique à exactement une catégorie. | Join: `BUDGET.category_id = CATEGORY.id` |

---

## Décision de conception — Issue #6

### Propriété des catégories : Catégories scoped par utilisateur

**Décision :** Chaque utilisateur dispose de sa propre liste de catégories. Les catégories sont scoped par `user_id` (Scénario B dans l'issue #6).

**Justification brève :**
- Flexibilité : chaque utilisateur peut personnaliser sa nomenclature.
- Confidentialité : les catégories d'un utilisateur ne révèlent pas les habitudes des autres.
- Contrôles d'accès simples : une catégorie appartient clairement à un utilisateur.
- Faible surcoût pour le MVP : un seul champ `user_id` + deux indices.
- Extensibilité : permet d'ajouter des catégories partagées (famille, groupes) plus tard sans refonte.

**Documentation complète :**
- Spec : `docs/specs/issue-6-category-ownership.md` (analyse des scénarios, recommandations, impacts API/seed data).
- Décision : `docs/decisions/category-ownership.md` (raisonnement formel, compromis, implications).

**Structure confirmée :**
- Table `CATEGORY` : `user_id BIGINT NOT NULL FK → USER.id`
- Contrainte : `UNIQUE(user_id, name)`
- Indices : `(user_id)`, `(user_id, name)`
- Suppression : CASCADE on DELETE USER

**Seed data :**
À l'inscription, 12 catégories par défaut sont créées pour chaque utilisateur (`Alimentation`, `Transport`, `Logement`, `Loisirs`, `Santé`, `Vêtements`, `Éducation`, `Divertissement`, `Services`, `Épargne`, `Investissements`, `Autres`). Implémenté via le signal Django `post_save` sur `User` dans `backend/api/signals.py`, à partir de la liste `DEFAULT_CATEGORIES` dans `backend/api/models.py`.

---

## Champs monétaires et précision

Tous les champs de montants (`amount` sur `EXPENSE` et `BUDGET`) sont **obligatoirement `NUMERIC(10, 2)`** en PostgreSQL, jamais `float` ou `double precision`.

```sql
-- ✓ CORRECT
amount NUMERIC(10, 2) NOT NULL CHECK (amount > 0)

-- ✗ FAUX — ne pas faire
amount FLOAT
amount DOUBLE PRECISION
```

**Justification :** Évite les erreurs d'arrondi IEEE 754. Ex. 0.1 + 0.2 = 0.30000000000000004 en float ; en NUMERIC c'est exactement 0.30.

**Contraintes explicites en base :**
- `CHECK (amount > 0)` appliqué directement à la colonne pour rejeter les montants négatifs ou nuls à la base de données.
- Valide à la fois à la couche application et à la couche base de données (défense en profondeur).

---

## Période budgétaire

Les budgets utilisent deux colonnes `period_start` et `period_end` (dates exactes) au lieu d'une enum de mois.

**Avantage :** Support de périodes arbitraires (ex. 1er au 30 de chaque mois, ou semaines, ou trimestres).

**Inconvénient :** Requêtes de matching `EXPENSE.date BETWEEN BUDGET.period_start AND BUDGET.period_end` plus coûteuses.

**Contrainte explicite en base :**
- `CHECK (period_end >= period_start)` appliqué directement sur la table pour garantir la validité logique des périodes.
- Valide à la base de données, indépendamment de la couche application.

**Compromis MVP :** La flexibilité gagne pour l'MVP. Si performance devient un problème, reconsidérer avec indices et partitioning.

---

## Décisions de conception

### 1. BigAutoField pour les clés primaires

Django 3.2+ utilise `BigAutoField` par défaut (`DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"` dans `settings.py`). Tous les `id` sont `BIGSERIAL` (64 bits) plutôt que `SERIAL` (32 bits).

**Impact :** Supporte jusqu'à ~9 milliards d'enregistrements par table sans débordement.

### 2. Timestamps implicites (`created_at`, `updated_at`)

Chaque entité a `created_at` et `updated_at`.

- `created_at` : ne change jamais après insertion.
- `updated_at` : mis à jour à chaque modification (update automatique dans une trigger ou via ORM).

**Implémentation Django :** Utiliser `DateTimeField(auto_now_add=True)` pour `created_at` et `DateTimeField(auto_now=True)` pour `updated_at`.

### 3. Soft-delete via `is_active` (partiel)

`USER` et `CATEGORY` ont un booléen `is_active`.

**But :** Désactiver un utilisateur ou une catégorie sans supprimer physiquement les données.

**Note :** `EXPENSE` et `BUDGET` n'ont pas de colonne `is_active` (MVP : suppression logique pas requise pour les transactions).

**Limitation connue :** Cette approche partielle peut mener à des incohérences (ex. une dépense avec une catégorie `is_active = false`). Documenter dans les futures décisions.

### 4. Pas de type JSONB (MVP)

Les entités utilisent des colonnes scalaires (string, int, numeric, date, timestamp) pour la simplicité.

**Pas de :** champs d'attributs flexibles, métadonnées JSON, tags. Ils arrivent quand les besoins l'exigent.

### 5. Indices et performance

Les indices suggérés ci-dessus sont des recommandations pour les requêtes courantes (lister les dépenses d'un utilisateur, filtrer par période, etc.).

**À appliquer lors de la rédaction des migrations.** Ne pas sur-indexer : chaque index ralentit les inserts/updates.

---

## Cohérence avec le code existant

- **Base de données PostgreSQL :** `settings.py` définit `DATABASES["default"]["ENGINE"] = "django.db.backends.postgresql"`. Cet ERD utilise le dialecte PostgreSQL (`NUMERIC`, `BIGSERIAL`, `TIMESTAMP`, etc.) compatible avec la configuration existante.
- **DEFAULT_AUTO_FIELD :** Django est configuré avec `DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"` dans `settings.py`. Tous les `id` utilisent `BIGSERIAL` par cohérence.
- **User par défaut Django :** Pas d'héritage multi-table personnalisé. Utilisation de Django `User` de base pour `USER` (champ `password` au lieu de `password_hash`).
- **Modèles implémentés :** `backend/api/models.py` définit `User`, `Category`, `Expense` et `Budget` exactement comme décrit ci-dessus.
- **Migrations :** `0001_initial.py` (User), `0002_category.py`, `0003_expense.py`, `0004_budget.py`.

---

## Prochaines étapes

Les modèles, migrations et la seed data décrits dans cet ERD sont implémentés. Les routes CRUD (GET, POST, PATCH, DELETE) sont spécifiées dans `docs/api-design.md` ; certaines ne sont pas encore implémentées côté API — voir ce document pour le détail à jour.

---

## Références

- **Spec issue #5 (ERD):** `docs/specs/issue-5-erd.md`
- **Spec issue #6 (Category Ownership):** `docs/specs/issue-6-category-ownership.md`
- **Décision issue #6:** `docs/decisions/category-ownership.md`
- **Configuration Django :** `backend/cashmire/settings.py` (`DEFAULT_AUTO_FIELD`, `DATABASES`)
- **Migrations :** `backend/api/migrations/0001_initial.py` à `0004_budget.py`
- **Workflow :** `docs/git-workflow.md`, `docs/agentic-log.md`

---

*Dernière mise à jour : 2026-10-09. Document approuvé par Product & Architecture. Issue #6 tranchée. Modèles, migrations et seed data implémentés.*
