# SPÉCIFICATION — Propriété des catégories (Issue #6)

- **Issue :** #6 « Décider et documenter la propriété des catégories »
- **Statut :** Proposition. Non approuvée. Un humain doit valider cette décision avant les migrations.
- **Auteur :** Agent Product & Architecture
- **Portée :** Modèle de données (table Category), spécification de la relation User↔Category, documentation. Aucun code applicatif.
- **Codebase examiné à :** branche `docs/6-category-ownership`, commits jusqu'au 2026-10-06

---

## 0. Introduction

La spécification d'ERD (issue #5) a laissé en suspens une décision critique : les catégories de dépenses sont-elles **partagées entre tous les utilisateurs** (une liste globale unique) ou **propres à chaque utilisateur** (scoped par `user_id`) ?

Ce document propose une recommandation, énumère les compromis, et prépare la migration de `docs/erd.md` pour trancher cette question avant l'implémentation.

---

## 1. Énoncé du problème et critères d'acceptation

### 1.1 Récit utilisateur

> Avant de rédiger les modèles Django et les migrations, l'équipe doit choisir la structure de propriété des catégories. Cette décision affecte :
> 
> - la structure de la table `Category` (présence ou absence de `user_id` FK)
> - les contraintes d'unicité et les indices
> - les requêtes API pour lister/créer/modifier les catégories
> - la gestion des permissions (qui peut voir/modifier quelle catégorie)
>
> Une recommandation documentée permet au Full-Stack Development agent de démarrer sans ambiguïté.

### 1.2 Critères d'acceptation

| ID | Critère | Vérification |
|----|---------|-------------|
| AC-1 | Un document `docs/decisions/category-ownership.md` existe et énonce la décision choisie (A ou B), le raisonnement, les compromis, et les alternatives rejetées. | Lecture du fichier. |
| AC-2 | La spec `docs/specs/issue-6-category-ownership.md` présente les deux scénarios, la recommandation de l'équipe, et les impacts sur l'ERD. | Lecture du fichier courant. |
| AC-3 | `docs/erd.md` est mis à jour pour refléter le scénario choisi : la section « Modèles conditionnels » est remplacée par la structure unique retenue, avec diagramme Mermaid mis à jour. | Vérification dans `docs/erd.md`. |
| AC-4 | Le diagramme Mermaid inclut la relation `USER` ↔ `CATEGORY` (qui était omise intentionnellement dans l'ERD initial). | Présence dans le diagramme. |
| AC-5 | Si le scénario B (scoped) est retenu : `Category` table inclut `user_id BIGINT FK → USER.id`, contrainte `UNIQUE(user_id, name)`, index sur `user_id`. | Structure détaillée dans l'ERD. |
| AC-6 | Si le scénario A (partagé) est retenu : `Category` table exclut `user_id`, contrainte `UNIQUE(name)`. | Structure détaillée dans l'ERD. |
| AC-7 | La spec énumère les implications pour les routes API (ex. GET `/api/users/{id}/categories/` vs. GET `/api/categories/`). | Tableau API dans cette spec. |
| AC-8 | La stratégie de données seed pour le MVP (prépopulation de catégories) est documentée. | Section dédiée. |
| AC-9 | Les points ouverts mineurs (ex. modification/suppression de catégories, soft-delete) sont énumérés sans qu'on les tranche ici. | Section « Questions réservées ». |

---

## 2. Analyse et recommandation

### 2.1 Scénario A : Catégories partagées (globales)

**Description :** Une seule liste de catégories, commune à tous les utilisateurs. Aucun champ `user_id` sur la table `Category`.

**Avantages :**
- Nomenclature unique : tous les utilisateurs utilisent les mêmes catégories (ex. « Alimentation », « Transport »).
- Moins de données en base.
- Requêtes simples (pas de filtre `WHERE user_id = ?` sur les catégories).
- Seed data centralisée : créer 10-15 catégories une seule fois.
- Pas de gestion de permissions : une catégorie est visible par tous.

**Inconvénients :**
- Inflexibilité : un utilisateur ne peut pas créer sa propre catégorie « Bureau » s'il ne l'est pas déjà en base.
- Scalabilité : gérer les demandes de nouvelles catégories (modération, votes, etc.) devient compliqué.
- UX limitée : MVP « complet » mais extensibilité future compromise.
- Données résiduelles : si une catégorie est supprimée (ex. « Voyages » plus pertinent), elle est perdue pour tous.

**Implémentation migration :**
```sql
CREATE TABLE category (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX idx_category_name ON category(name);
```

---

### 2.2 Scénario B : Catégories scoped par utilisateur

**Description :** Chaque utilisateur dispose de sa propre liste de catégories. Chaque ligne `Category` pointe vers son propriétaire via `user_id`.

**Avantages :**
- Flexibilité : chaque utilisateur peut créer, nommer et personnaliser ses catégories.
- Confidentialité/séparation des données : un utilisateur ne voit que ses propres catégories.
- Contrôles d'accès clairs : l'API valide `category.user_id == request.user.id` avant lecture/modification.
- Extensibilité future : on peut ajouter des catégories partagées plus tard (table `SharedCategory` + flags de partage).
- Gestion simplifiée : pas de modération centralisée, chaque utilisateur contrôle son domaine.

**Inconvénients :**
- Plus de données : chaque utilisateur duplique les catégories standards.
- Requêtes légèrement plus complexes : tous les SELECT sur `Category` doivent filtrer par `user_id`.
- Seed data par utilisateur : lors de l'onboarding, créer automatiquement les catégories par défaut pour chaque utilisateur.
- Synchronisation : si une catégorie change de signification, les anciennes ne mettent pas à jour.

**Implémentation migration :**
```sql
CREATE TABLE category (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (user_id, name)
);
CREATE INDEX idx_category_user_id ON category(user_id);
CREATE INDEX idx_category_user_id_name ON category(user_id, name);
```

---

### 2.3 Recommandation de l'équipe

**Choix : Scénario B (Catégories scoped par utilisateur)**

**Justification :**

1. **Flexibilité > Simplicité pour une app financière**  
   Cashmire est un outil personnel de suivi des dépenses. Chaque utilisateur a des dépenses uniques et des catégories qui ont du sens pour lui. Imposer une nomenclature globale bride le produit.

2. **Confidentialité et données**  
   Une liste de catégories peut révéler des habitudes de dépense (ex. « Thérapie », « Avortement », « Dettes »). La séparation par utilisateur est un choix éthique pour la privacy.

3. **Contrôles d'accès simples et explicites**  
   Chaque catégorie appartient à un utilisateur. Lors d'une requête API (ex. PATCH `/api/categories/{id}/`), vérifier `category.user_id == request.user.id` est trivial et inambigü.

4. **Complexité minimale pour MVP**  
   Ajouter `user_id FK` et un index composite prend ~10 lignes SQL. Le code Django est aussi simple (un champ de plus sur le modèle). Le surcoût n'est pas significatif.

5. **Seed data gérée lors de l'onboarding**  
   Au lieu de demander à l'utilisateur de créer des catégories, on les crée automatiquement lors de l'inscription (ex. 15 catégories par défaut : « Alimentation », « Transport », « Loisirs », etc.). Cela maintient la commodité du scénario A tout en offrant la flexibilité du B.

6. **Extensibilité**  
   Si plus tard on veut ajouter des catégories partagées (ex. « Cadeaux », visibles par la famille), on peut ajouter une table `SharedCategory` et un flag sur `Category`. Le modèle B le permet ; le A le rend impossible.

**Compromis acceptés :**
- Duplication de seed data pour chaque utilisateur (stockage négligeable pour une MVP).
- Tous les filtres API doivent inclure `user_id` (requêtes légèrement plus robustes, pas plus complexes).

---

## 3. Delta du modèle de données

### 3.1 Table Category (retenue)

Structure conforme au scénario B :

| Champ | Type PostgreSQL | Contraintes | Description |
|-------|-----------------|-----------|------------|
| `id` | `BIGSERIAL` | PRIMARY KEY | Clé primaire auto-incrémentée. |
| `user_id` | `BIGINT` | FK → USER.id, NOT NULL | Propriétaire de la catégorie. CASCADE on DELETE. |
| `name` | `VARCHAR(100)` | NOT NULL | Nom de la catégorie (ex. « Alimentation »). |
| `description` | `TEXT` | NULL | Description optionnelle. |
| `is_active` | `BOOLEAN` | NOT NULL, DEFAULT true | Indicateur de catégorie active. |
| `created_at` | `TIMESTAMP` | NOT NULL, DEFAULT now() | Horodatage de création. |
| `updated_at` | `TIMESTAMP` | NOT NULL, DEFAULT now() | Horodatage de modification. |

**Contraintes composées :**
```sql
UNIQUE (user_id, name)
```
Un utilisateur ne peut pas avoir deux catégories portant le même nom.

**Indices suggérés :**
- `CREATE INDEX idx_category_user_id ON category(user_id);` — Requêtes "lister les catégories d'un utilisateur".
- `CREATE INDEX idx_category_user_id_name ON category(user_id, name);` — Requêtes "chercher une catégorie par nom pour un utilisateur".

---

### 3.2 Impact sur les relations

| Relation | Ancien état | Nouvel état | Notes |
|----------|-----------|-----------|-------|
| `USER` → `CATEGORY` | Omise (point ouvert) | 1:N (User crée N catégories) | Chaque catégorie appartient à exactement un utilisateur. |
| `CATEGORY` → `EXPENSE` | 1:N | 1:N (inchangé) | Une catégorie a zéro ou plusieurs dépenses. |
| `CATEGORY` → `BUDGET` | 1:N | 1:N (inchangé) | Une catégorie a zéro ou plusieurs budgets. |

---

### 3.3 Cohérence avec Expense et Budget

**Pour Expense :**
- FK existant `category_id` → `Category.id` reste inchangé.
- **Validation implicite :** Lors de la création d'une dépense, l'API doit vérifier que `category.user_id == expense.user_id` (la catégorie appartient à l'utilisateur).
- Requête sécurisée :
  ```sql
  SELECT e.* FROM expense e
  JOIN category c ON e.category_id = c.id
  WHERE e.user_id = :user_id AND c.user_id = :user_id;
  ```

**Pour Budget :**
- FK existant `category_id` → `Category.id` reste inchangé.
- Même validation : `category.user_id == budget.user_id` à la création/modification.

**Note importante :** Ces validations ne sont pas des contraintes SQL explicites (CASCADE ne s'applique pas ici). Elles relèvent de la logique applicative Django/DRF. Le Full-Stack Development agent devra documenter cela dans les tests et la validation des modèles.

---

## 4. Routes API affectées

### 4.1 Gestion des catégories

| Méthode | Chemin | Auth | Paramètres | Réponse (200) | Erreurs |
|---------|--------|------|-----------|--------------|---------|
| GET | `/api/users/{user_id}/categories/` | Token | Query: `?active=true` | `{"count": N, "results": [{"id": 1, "name": "...", ...}]}` | 401 Unauth, 403 Forbidden (user_id != requester) |
| POST | `/api/users/{user_id}/categories/` | Token | Body: `{"name": "...", "description": "..."}` | `{"id": 2, "name": "...", "user_id": user_id, ...}` | 401 Unauth, 403 Forbidden, 400 Validation (name empty, duplicate) |
| GET | `/api/users/{user_id}/categories/{cat_id}/` | Token | — | `{"id": 2, "name": "...", ...}` | 401 Unauth, 403 Forbidden, 404 Not Found |
| PATCH | `/api/users/{user_id}/categories/{cat_id}/` | Token | Body: `{"name": "..."}` | `{"id": 2, "name": "...", ...}` | 401 Unauth, 403 Forbidden, 404 Not Found, 400 Validation |
| DELETE | `/api/users/{user_id}/categories/{cat_id}/` | Token | — | 204 No Content | 401 Unauth, 403 Forbidden, 404 Not Found, 409 Conflict (has expenses/budgets) |

**Notes API :**
- Toutes les routes incluent `user_id` dans le chemin (scoping par utilisateur).
- Permission : seul l'utilisateur propriétaire (ou un admin) peut CRUD ses catégories.
- Soft-delete possible via `is_active` (pas de DELETE physique), ou DELETE avec vérification des enfants (Expense, Budget).
- Pagination envisagée pour GET lists (future issue).

---

## 5. Stratégie de données seed pour le MVP

### 5.1 Catégories par défaut

Lors de l'inscription d'un nouvel utilisateur, le système crée automatiquement ~15 catégories standard :

```
1. Alimentation
2. Transport
3. Logement
4. Loisirs
5. Santé
6. Vêtements
7. Éducation
8. Divertissement
9. Services
10. Épargne
11. Investissements
12. Autres
13. (Catégories optionnelles supplémentaires selon UX)
```

**Implémentation :**
- Signal Django `post_save` sur `User`.
- Ou via une commande de management `python manage.py seed_categories`.
- Ou lors du premier login (lazy-load).

**Avantage :** L'utilisateur démarre avec une nomenclature raisonnable sans avoir à créer des catégories avant d'enregistrer sa première dépense.

---

## 6. Points ouverts et risques

### 6.1 Questions réservées (out of scope de cette spec)

| ID | Question | Qui décide |
|----|----------|-----------|
| Q-1 | **Soft-delete vs. suppression physique pour Category :** Faut-il garder les catégories supprimées avec un flag `deleted_at`, ou les supprimer physiquement ? | Issue future (#X sur soft-delete). |
| Q-2 | **Suppression en cascade pour Expense/Budget :** Si on supprime une catégorie, que fait-on des dépenses/budgets qui la référencent ? RESTRICT, SET NULL, ou KEEP ? | Issue future de gestion des dépenses orphelines. |
| Q-3 | **Catégories partagées (future) :** Comment ajouter un système de catégories partagées (ex. famille) sans casser le modèle B ? | Feature future, au-delà du MVP. |
| Q-4 | **Ordre/tri des catégories :** Faut-il un champ `order` pour que l'utilisateur arrangerait ses catégories en UI ? | Nice-to-have, future issue. |

### 6.2 Risques

| ID | Risque | Sévérité | Mitigation |
|----|--------|----------|-----------|
| R-1 | **Données orphelines après CASCADE DELETE.** Si un utilisateur est supprimé, ses catégories, dépenses et budgets disparaissent (CASCADE sur FK user_id). Est-ce souhaitable ou faut-il soft-delete l'utilisateur ? | Basse | Documenter dans la logique de suppression de compte utilisateur. |
| R-2 | **Seed data non synchronisé.** Ajouter une catégorie aux defaults après qu'un utilisateur s'est inscrit ne crée pas la catégorie pour cet utilisateur. | Basse | Documenter : seed data est un one-time init à l'inscription. Les mises à jour de catégories globales arrivent via API (issue future). |
| R-3 | **Validation applicative fragile.** La contrainte `category.user_id == expense.user_id` n'est pas appliquée à la base de données, seulement en Python. Une faille de sérialisation pourrait créer une incohérence. | Basse | Tests unitaires robustes sur les validations. Considérer une trigger SQL pour double validation. |
| R-4 | **Index composite non optimal.** L'index `(user_id, name)` couvre le UNIQUE constraint mais peut ne pas couvrir tous les requêtes (ex. lister par `user_id` + date de création). | Basse | Ajouter des indices au besoin lors du tuning de performance. |

---

## 7. Hors scope

Excellentes idées qui relèvent d'une autre issue.

- **Hiérarchies de catégories** (parent/enfant ex. « Alimentation → Fruits »).
- **Catégories partagées** (famille, groupe).
- **Export/import de catégories** (clone d'une liste d'une autre source).
- **Suggester des catégories** basé sur le texte de la dépense (ML).
- **Audit trail sur Category** (qui a modifié, quand).

---

## 8. Prochaines étapes

1. **Approbation de cette spec** : Équipe lit et approuve la recommandation (scénario B).
2. **Approbation de la décision formelle** : `docs/decisions/category-ownership.md` validée.
3. **Mise à jour de l'ERD** : `docs/erd.md` migré vers la structure finale (B), diagramme mis à jour, section « Modèles conditionnels » remplacée.
4. **Spécifications API** : Future issue (#X) pour détailler les routes GET/POST/PATCH/DELETE avec paginations, filtres, validations.
5. **Implémentation** : Full-Stack Development agent rédige les modèles Django et migrations.
6. **Seed data** : Implémentation du système de création automatique de catégories à l'inscription.

---

## 9. Ressources référencées

- `docs/erd.md` — Spécification d'ERD (issue #5), section « Modèles conditionnels ».
- `docs/specs/issue-5-erd.md` — Spec complète de l'ERD, questions Q-1 sur category ownership.
- `docs/team.md` — Équipe et responsabilités.
- `backend/cashmire/settings.py` — Configuration Django.

---

*Proposition de spec par Agent Product & Architecture. Date : 2026-10-06.*
