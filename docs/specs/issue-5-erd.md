# SPÉCIFICATION — Conception de l'ERD PostgreSQL (User, Expense, Budget, Category)

- **Issue :** #5 « Concevoir l'entité-relation de la base de données »
- **Statut :** Proposition. Non approuvée. Un humain doit lire cette spec avant la mise en œuvre.
- **Auteur :** Agent Product & Architecture
- **Portée :** Modèle de données PostgreSQL et documentation. Aucune migration, aucun code applicatif.
- **Codebase examiné à :** branche `docs/5-erd`, commit actuel

---

## 0. Note introductive

Cet ERD initial introduit quatre entités de base de Cashmire : `User`, `Expense`, `Budget` et `Category`. Il est conçu pour soutenir le cœur du produit (suivi des dépenses, catégorisation, budgets) tout en isolant les décisions qui relèvent d'une autre issue ou d'une révision ultérieure.

**Décision critique non tranchée ici :** l'ownership des catégories (partagées vs. par utilisateur). Cette question est explicitement marquée comme **point ouvert pour l'issue #6**, et la présente spécification n'impose pas un choix — elle présente l'ERD de manière à supporter les deux approches.

---

## 1. Énoncé du problème et critères d'acceptation

### 1.1 Récit utilisateur

> Cashmire doit stocker les entités de base du domaine métier (utilisateurs, dépenses, catégories, budgets) dans une base de données relationnelle bien structurée, afin que les futures API puissent les servir avec cohérence, et que les migrations suivantes puissent s'appuyer sur un socle solide et documenté.

### 1.2 Critères d'acceptation (testables)

| ID | Critère | Vérification |
|----|---------|-------------|
| AC-1 | Un document `docs/erd.md` existe et contient un diagramme erDiagram Mermaid montrant les quatre entités et leurs relations. | Lecture du fichier et rendu du diagramme. |
| AC-2 | Chaque entité est documentée avec sa liste complète de champs, types PostgreSQL et contraintes. | Vérification manuelle dans `docs/erd.md`. |
| AC-3 | Tous les champs monétaires (`amount` dans `Expense` et `Budget`) sont typés `NUMERIC` ou `DECIMAL`, jamais `float`. Cette exigence est explicitement affirmée dans la spécification. | Recherche du mot « NUMERIC » ou « DECIMAL » dans la spec et le doc ERD. |
| AC-4 | Une contrainte d'unicité existe sur `Budget` : un seul budget par (user_id, category_id, period). | Énoncé dans `docs/erd.md` sous les contraintes de `Budget`. |
| AC-5 | La propriété des catégories (partagées vs. par utilisateur) est documentée comme un point ouvert explicite qui relève de l'issue #6, sans trancher le choix. | Banneau « Point ouvert » visible dans `docs/erd.md` et dans les relations `Category`. |
| AC-6 | Un bandeau visible indique que ce document est une proposition d'ERD qui nécessite l'approbation de l'équipe avant la rédaction des migrations. | Bandeau en début de `docs/erd.md`. |
| AC-7 | La relation entre `Expense` et ses entités parentes (`User`, `Category`) est clairement documentée : un expense appartient à exactement un user et une catégorie. | Diagramme Mermaid et tableau de relations. |
| AC-8 | Les points de cohérence avec le code existant sont explicitement relevés (par ex., utilisation de `BigAutoField` pour les clés primaires). | Mentionnés dans la section « Cohérence avec l'existant ». |
| AC-9 | Aucun point d'ambiguïté majeur n'est laissé sans mention : les questions ouvertes sont énumérées. | Section « Questions ouvertes et risques ». |

---

## 2. Delta du modèle de données

### 2.1 Entités à créer

#### **Entité : `User`**

Représente un utilisateur de Cashmire. Supporte l'authentification, l'identification et les opérations scoped à l'utilisateur.

| Champ | Type PostgreSQL | Constraints | Notes |
|-------|-----------------|-----------|-------|
| `id` | `BIGSERIAL` | PRIMARY KEY | Clé primaire auto-incrémentée (voir AC-8). Django `BigAutoField` par défaut. |
| `email` | `VARCHAR(254)` | UNIQUE, NOT NULL | Adresse e-mail unique pour chaque utilisateur (RFC 5321). Utilisée pour la connexion. |
| `password_hash` | `VARCHAR(255)` | NOT NULL | Hash du mot de passe (généré par Django). Jamais le mot de passe en clair. |
| `username` | `VARCHAR(150)` | UNIQUE, NOT NULL | Nom d'utilisateur unique (alternative de login ou affichage). |
| `first_name` | `VARCHAR(150)` | NULL | Prénom optionnel (cohérent avec Django User). |
| `last_name` | `VARCHAR(150)` | NULL | Nom de famille optionnel (cohérent avec Django User). |
| `is_active` | `BOOLEAN` | NOT NULL, DEFAULT true | Indicateur de compte actif (soft delete via désactivation). |
| `created_at` | `TIMESTAMP` | NOT NULL, DEFAULT now() | Horodatage de création du compte. |
| `updated_at` | `TIMESTAMP` | NOT NULL, DEFAULT now() | Horodatage de dernière modification. |

**Justification :** Hérite de la structure standard de Django `User` mais étend avec `created_at` et `updated_at` pour l'audit. Pas d'héritage multi-table Django pour rester simple.

---

#### **Entité : `Category`**

Représente une catégorie de dépenses (ex. « Alimentation », « Transport », « Loisirs »).

**Question ouverte (issue #6) :** Une catégorie est-elle **partagée entre tous les utilisateurs** (une liste globale) ou **propre à chaque utilisateur** (scoped par `user_id`) ?

*Cette spec présente les deux options ; l'équipe tranchera avant l'écriture des migrations.*

| Champ | Type PostgreSQL | Constraints | Notes |
|-------|-----------------|-----------|-------|
| `id` | `BIGSERIAL` | PRIMARY KEY | Clé primaire auto-incrémentée. |
| `name` | `VARCHAR(100)` | NOT NULL | Nom de la catégorie (ex. « Alimentation »). |
| `description` | `TEXT` | NULL | Description optionnelle. |
| `user_id` | `BIGINT` | FK → User.id, NULL | **Clé de décision pour issue #6 :** Si catégories propres à l'utilisateur, NOT NULL + UNIQUE(user_id, name). Si partagées, NULL ou absent. |
| `is_active` | `BOOLEAN` | NOT NULL, DEFAULT true | Indicateur de catégorie active. |
| `created_at` | `TIMESTAMP` | NOT NULL, DEFAULT now() | Horodatage de création. |
| `updated_at` | `TIMESTAMP` | NOT NULL, DEFAULT now() | Horodatage de dernière modification. |

**Justification :** Structure minimale. La question de l'ownership crée une fourche ; l'ERD final inclura une décision documentée dans `docs/decisions/000X-category-ownership.md`.

---

#### **Entité : `Expense`**

Représente une dépense unique enregistrée par un utilisateur.

| Champ | Type PostgreSQL | Constraints | Notes |
|-------|-----------------|-----------|-------|
| `id` | `BIGSERIAL` | PRIMARY KEY | Clé primaire auto-incrémentée. |
| `user_id` | `BIGINT` | FK → User.id, NOT NULL | Proprietaire de la dépense. Une dépense appartient exactement à un utilisateur. |
| `category_id` | `BIGINT` | FK → Category.id, NOT NULL | Catégorie de la dépense. Une dépense a exactement une catégorie. |
| `amount` | `NUMERIC(10, 2)` | NOT NULL | Montant de la dépense. **Toujours NUMERIC, jamais float.** Stocke jusqu'à 10 chiffres, 2 décimales (ex. 99999999.99). |
| `description` | `TEXT` | NULL | Description optionnelle de la dépense. |
| `date` | `DATE` | NOT NULL | Date de la dépense. Peut différer de la date de création. |
| `created_at` | `TIMESTAMP` | NOT NULL, DEFAULT now() | Horodatage de création (métadonnée système). |
| `updated_at` | `TIMESTAMP` | NOT NULL, DEFAULT now() | Horodatage de dernière modification. |

**Justification :** Champ `amount` en `NUMERIC` pour garantir la précision monétaire (pas d'erreurs d'arrondi IEEE 754). `date` séparé de `created_at` pour permettre l'enregistrement rétroactif de dépenses.

---

#### **Entité : `Budget`**

Représente un budget pour une catégorie de dépenses sur une période donnée.

| Champ | Type PostgreSQL | Constraints | Notes |
|-------|-----------------|-----------|-------|
| `id` | `BIGSERIAL` | PRIMARY KEY | Clé primaire auto-incrémentée. |
| `user_id` | `BIGINT` | FK → User.id, NOT NULL | Proprietaire du budget. Un budget est scoped à un utilisateur. |
| `category_id` | `BIGINT` | FK → Category.id, NOT NULL | Catégorie couverte par ce budget. Un budget s'applique à une catégorie. |
| `amount` | `NUMERIC(10, 2)` | NOT NULL | Montant budgété. **Toujours NUMERIC, jamais float.** |
| `period_start` | `DATE` | NOT NULL | Début de la période (ex. 2026-01-01 pour janvier). |
| `period_end` | `DATE` | NOT NULL | Fin de la période (ex. 2026-01-31 pour janvier). |
| `alert_threshold` | `NUMERIC(5, 2)` | NULL, DEFAULT 80.00 | Seuil d'alerte en pourcentage (ex. 80 % du budget). Déclenchement d'une notification quand dépenses dépasser ce seuil. **Question ouverte pour issue #7 :** où la logique de calcul/notification vit-elle ? |
| `created_at` | `TIMESTAMP` | NOT NULL, DEFAULT now() | Horodatage de création. |
| `updated_at` | `TIMESTAMP` | NOT NULL, DEFAULT now() | Horodatage de dernière modification. |

**Contraintes composées :**
- **Unicité :** `UNIQUE(user_id, category_id, period_start, period_end)` — Un seul budget par utilisateur+catégorie+période. Empêche les doublons.
- **Validité logique :** `period_start <= period_end` (vérifiée à la couche application, pas de CHECK en SQL pour cette MVP).

**Justification :** Champ `alert_threshold` optionnel pour supporter les notifications futures sans forcer la logique aujourd'hui. Période en dates pour supporter les périodes non-calendaires (ex. « du 1er au 30 de chaque mois »).

---

### 2.2 Relations

| Relation | Cardinalité | Sens | Justification |
|----------|-------------|------|-------------|
| `Expense.user_id` → `User.id` | N:1 | Un utilisateur a plusieurs dépenses | Chaque dépense appartient à exactement un utilisateur ; un utilisateur peut avoir zéro ou plusieurs dépenses. |
| `Expense.category_id` → `Category.id` | N:1 | Une catégorie a plusieurs dépenses | Chaque dépense appartient à exactement une catégorie ; une catégorie peut avoir zéro ou plusieurs dépenses. |
| `Budget.user_id` → `User.id` | N:1 | Un utilisateur a plusieurs budgets | Chaque budget appartient à exactement un utilisateur. |
| `Budget.category_id` → `Category.id` | N:1 | Une catégorie peut avoir plusieurs budgets | Chaque budget s'applique à une catégorie ; une catégorie peut avoir plusieurs budgets (ex. un par mois). |
| `Category.user_id` → `User.id` | N:1 (si issue #6 : owned) ou 0:1 (si partagée) | **Point ouvert** | Si catégories par utilisateur : N:1 (chaque catégorie belongs-to un utilisateur). Si partagées : pas de FK, `user_id` absent. |

---

### 2.3 Cohérence avec l'existant

- **Utilisation de `BigAutoField` pour les clés primaires :** Django est configuré avec `DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"` dans `settings.py`. Cet ERD suit cette convention (toutes les clés primaires sont `BIGSERIAL`).
- **Base de données PostgreSQL :** `settings.py` définit `DATABASES["default"]["ENGINE"] = "django.db.backends.postgresql"`. Cet ERD utilise le dialecte PostgreSQL (`NUMERIC`, `BIGSERIAL`, `TIMESTAMP`, etc.) compatible avec la configuration existante.
- **Pas d'héritage multi-table Django :** On reste simple : pas de `AbstractBaseUser` personnalisé, pas de table proxy. Django `User` de base, étendu via des champs supplémentaires.
- **Pas de modèles existants :** `backend/api/` ne contient pas de `models.py` aujourd'hui. Cet ERD propose les quatre premiers modèles du projet.

---

## 3. Contrat API

**N/A pour cette issue.** L'ERD définit la structure de données ; les routes API (GET, POST, PUT, DELETE pour chaque entité) seront spécifiées dans des issues ultérieures (ex. #12, #13, #14 pour CRUD Expense, etc.).

Les points suivants doivent être documentés plus tard :
- Quels endpoints créent / lisent / modifient / suppriment des Users, Expenses, Budgets, Categories ?
- Quel niveau d'authentification est exigé pour chaque route ?
- Quels filtres (par user, par category, par date) sont possibles ?
- Quel est le format exact de réponse (avec/sans pagination, avec/sans détails liés) ?

---

## 4. Points ouverts et risques

### 4.1 Questions ouvertes — Doivent être tranchées avant la rédaction des migrations

| ID | Question | Pourquoi un agent ne peut pas y répondre |
|----|----------|-----|
| Q-1 | **Ownership des catégories (issue #6) :** Les catégories sont-elles partagées entre tous les utilisateurs (une liste globale), ou scoped par utilisateur (chaque utilisateur a sa propre liste) ? | Choix produit avec implications UX majeures. L'agent ne peut pas décider de la direction produit. |
| Q-2 | **Suppression logique vs. suppression physique pour les entités :** Utiliser un champ `deleted_at` ou `is_deleted`, ou supprimer physiquement les lignes ? | Choix d'architecture de rétention de données ; doivent être discutés au niveau équipe/produit. |
| Q-3 | **Format et granularité des périodes budgétaires :** Les budgets sont-ils toujours mensuels, ou supporter-t-on des semaines, trimestres, années, ou périodes arbitraires ? | Détermine la complexité du modèle et la logique de matching expense↔budget. |
| Q-4 | **Gestion des devises :** Cashmire support-t-il plusieurs devises par utilisateur, ou une devise fixe (ex. EUR, USD) ? | Si multi-devise, il faut une colonne `currency` sur `Expense` et `Budget`, et une logique de conversion. |
| Q-5 | **Soft delete et audit :** Faut-il un audit trail complet (qui a créé/modifié quoi, quand, comment), ou simplement `created_at`/`updated_at` ? | Détermine la complexité et les besoins de performance. Point 4.2 liste les risques associés. |
| Q-6 | **Où le MVP scope est-il défini :** Aucun `docs/mvp-scope.md` n'existe dans le repo, bien que le charter l'y référence. Quels entités/workflows sont dans le MVP ? | Sans un scope défini, ce spec propose le socle ; les futures issues décideront quoi activer. |

### 4.2 Risques

| ID | Risque | Sévérité | Mitigation |
|----|--------|----------|-----------|
| R-1 | **Champ `alert_threshold` sur `Budget` sans logique.** Si le champ existe mais que la logique de calcul des alertes n'est jamais implémentée, c'est une colonne inutile. | Basse | Documenter clairement dans l'issue #7 (notifications budgétaires) que cette colonne attend une mise en œuvre. Ne pas la créer si issue #7 n'existe pas. |
| R-2 | **Issue #6 non tranchée = impasse de codage.** Si le dev commence les migrations et que issue #6 n'est pas aprobée, il devra réécrire les FK de Category. | Moyenne | Approuver cette spec ET issue #6 avant d'écrire les migrations. C'est un point de synchronisation critique. |
| R-3 | **Période budgétaire comme deux dates au lieu d'une enum.** Utiliser `period_start` et `period_end` c'est du stockage flexible ; une enum (JAN, FEB, ...) serait plus simple. Mais ça empêche les périodes non-calendaires. | Basse | Le choix des deux dates est intentionnel pour la flexibilité MVP. Si ça cause du code complexe plus tard, reconsiérer. |
| R-4 | **Pas de versioning des budgets.** Si un budget est modifié (ex. montant augmenté), l'historique des versions est perdu. | Basse | Out of scope MVP. Ajouter une table `BudgetHistory` si l'audit devient requis. |
| R-5 | **NUMERIC(10,2) peut ne pas suffire pour certains cas d'usage.** Si Cashmire supporte des devises comme le bitcoin (beaucoup de décimales) ou des montants énormes, ça faudra revisiter. | Basse | Pour une MVP en EUR/USD, c'est suffisant. Augmenter les précisions si requis. |
| R-6 | **Pas de relation entre User et son "profil" (devise par défaut, localisation, etc.).** Si l'utilisateur a besoin d'une locale/fuseau horaire/devise par défaut, il faudra ajouter une table UserPreferences. | Basse | Out of scope MVP. Ajouter quand la personnalisation utilisateur arrive. |

---

## 5. Portée hors scope

Bonnes idées qui relèvent d'une autre issue.

- **Table `Transaction` ou `PaymentMethod` :** Intégrations avec des banques / services de paiement. Cas d'usage MVP : suivi manuel des dépenses, pas d'imports automatiques.
- **Table `Notification` ou `Alert` :** Persistance des alertes budgétaires générées. Le `alert_threshold` est préparé pour ça, mais la table de notifications arrive avec l'issue de notifications.
- **Table `UserPreferences` :** Paramètres utilisateur (langue, devise, fuseau horaire). MVP : pas de personnalisation, valeurs fixées par le backend.
- **Audit trail / versioning complet :** Historique détaillé de qui a modifié quoi. MVP : pas d'audit, juste `updated_at`.
- **Hierarchies de catégories :** Catégories parents/enfants (ex. « Logement » → « Loyer », « Charges »). MVP : catégories plates.
- **Multi-devise :** Support de différentes devises par transaction ou par utilisateur. MVP : devise unique (à définir dans issue #6 étendue ou issue #7).
- **Soft-delete ou historique de suppression :** Quand une dépense est supprimée, faut-il la conserver en base avec un flag `deleted_at` ? MVP : suppression logique via `is_deleted` booléen à définir avec issue #2.

---

## 6. Décisions relatives

Aucune décision formelle dans `docs/decisions/` ne s'applique directement à cet ERD. Deux décisions devront être écrites avant la rédaction des migrations :

1. **`000X-category-ownership.md` :** Partagée vs. scoped (tranche issue #6).
2. **`000Y-currency-handling.md` :** Support de devises, format de stockage (tranche Q-4 et issue futures).

---

## 7. Définition de fait (Definition of Done)

- [ ] La spec est approuvée par l'équipe en synchrone ou par révision du PR.
- [ ] `docs/erd.md` existe et contient un diagramme erDiagram Mermaid correct.
- [ ] `docs/erd.md` énumère tous les champs, types, contraintes de chaque entité (AC-2).
- [ ] Tous les champs monétaires sont explicitement typés `NUMERIC` dans la spec et le doc (AC-3).
- [ ] La contrainte d'unicité `UNIQUE(user_id, category_id, period)` sur `Budget` est documentée (AC-4).
- [ ] La question ouverte « ownership des catégories » est clairement marquée comme point ouvert pour issue #6, sans trancher (AC-5).
- [ ] Un bandeau de proposition/approbation requise est visible en tête de `docs/erd.md` (AC-6).
- [ ] Issue #6 est ouverte, tranchée et approuvée **avant** de commencer les migrations (R-2 mitigé).
- [ ] Aucun fichier `backend/api/models.py` n'est créé, aucune migration n'est écrite — cette spec est un artifact de conception, pas un artifact d'implémentation.
- [ ] Un humain a lu cette spec et `docs/erd.md` et a approuvé les deux avant que l'implémentation (migrations + modèles Django) ne commence.

---

## Ressources référencées

- `backend/cashmire/settings.py` — Configuration DB, `DEFAULT_AUTO_FIELD`.
- `backend/api/migrations/0001_initial.py` — Migration initiale (vide).
- `README.md` — Notes sur les migrations Django.

