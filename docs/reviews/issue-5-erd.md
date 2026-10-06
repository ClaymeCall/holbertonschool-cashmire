# Revue QA — Conception ERD PostgreSQL (Issue #5)

**Revue de :** `docs/erd.md` comparé à `docs/specs/issue-5-erd.md`

**Date :** 2026-10-06

**Commit :** 8d8f05a (docs: finalize ERD with issue #6 open-point isolation)

---

## Résumé exécutif

La documentation ERD est **conforme à la spécification** sur tous les points critiques. Le diagramme Mermaid est syntaxiquement valide, tous les champs sont typés correctement, et les points ouverts sont clairement marqués. Aucun code applicatif n'a été modifié. Pas de blocages.

---

## Vérification des critères d'acceptation

### AC-1 : Document ERD avec diagramme Mermaid (4 entités + relations)

**Statut :** ✓ PASS

**Evidence :**
- Fichier `docs/erd.md` existe et contient un bloc erDiagram valide (lignes 11-62).
- 4 entités présentes : `USER`, `CATEGORY`, `EXPENSE`, `BUDGET`.
- Relations avec cardinalités correctes :
  - `USER ||--o{ EXPENSE : creates` (1:N)
  - `USER ||--o{ BUDGET : creates` (1:N)
  - `CATEGORY ||--o{ EXPENSE : categorizes` (1:N)
  - `CATEGORY ||--o{ BUDGET : constrains` (1:N)
- Relation `USER ↔ CATEGORY` intentionnellement omise du diagramme pour refléter l'issue #6 ouverte (voir AC-5).

**Syntaxe Mermaid :** Valide. Les type d'attributs (`bigint`, `string`, `numeric`, `date`, `timestamp`, `text`, `boolean`) sont correctement énumérés avec leurs marqueurs (`PK`, `FK`, `UK`).

---

### AC-2 : Listes complètes de champs, types PostgreSQL, contraintes

**Statut :** ✓ PASS

**Evidence :**
- USER (tableau, lignes 78-87) : 9 champs, tous typés et contraints.
- CATEGORY (tableau, lignes 99-105) : 7 champs, incluant `user_id` optionnel marqué avec note sur issue #6.
- EXPENSE (tableau, lignes 116-125) : 8 champs, contraintes de valeurs documentées.
- BUDGET (tableau, lignes 141-151) : 10 champs, incluant `alert_threshold`.

Tous les types PostgreSQL sont explicites : `BIGSERIAL`, `VARCHAR(n)`, `TEXT`, `NUMERIC(p,s)`, `DATE`, `TIMESTAMP`, `BOOLEAN`. Contraintes composées énumérées (lignes 157-170 pour Budget).

---

### AC-3 : Montants NUMERIC, jamais float

**Statut :** ✓ PASS

**Evidence :**
- Expense.amount (doc ligne 121) : `NUMERIC(10, 2)` avec `CHECK(amount > 0)`.
- Budget.amount (doc ligne 146) : `NUMERIC(10, 2)` avec `CHECK(amount > 0)`.
- Section dédiée « Champs monétaires et précision » (lignes 265-282) affirmant l'interdiction de float/double precision.
- Justification : Évite les erreurs d'arrondi IEEE 754.

Aucune mention de `FLOAT` ou `DOUBLE PRECISION` dans le document. Spécification respectée.

---

### AC-4 : Contrainte d'unicité UNIQUE(user_id, category_id, period)

**Statut :** ✓ PASS

**Evidence :**
- Budget, tableau ligne 157-160 : Bloc « Contraintes composées »
- SQL exact : `UNIQUE (user_id, category_id, period_start, period_end)`
- Détail important : la contrainte porte sur les 4 colonnes, pas juste une période. Cohérent avec la spécification (section 2.2, ligne 123).
- But documenté : Empêcher les budgets en doublon.

---

### AC-5 : Ownership des catégories comme point ouvert (issue #6, non tranché)

**Statut :** ✓ PASS

**Evidence :**
- CATEGORY, tableau ligne 102 : colonne `user_id` annotée `(optionnel)` avec note « POINT OUVERT (issue #6) ».
- Section entière « Modèles conditionnels — Issue #6 (Ownership des catégories) » (lignes 186-262) présentant :
  - **Scénario A (Catégories partagées)** : structure SQL, avantages, inconvénients, endpoints API.
  - **Scénario B (Catégories scoped)** : structure SQL, avantages, inconvénients, endpoints API.
- Ligne 259 : « n'inclut pas la relation USER ↔ CATEGORY pour refléter cette ambiguïté ouverte ».
- Aucun choix imposé ; deux chemins présentés de manière neutre.

---

### AC-6 : Bandeau d'approbation requise avant migrations

**Statut :** ✓ PASS

**Evidence :**
- En-tête du document (lignes 3-5) :
  > PROPOSITION EN ATTENTE D'APPROBATION
  > Ce document décrit l'ERD proposée pour Cashmire. Il ne constitue pas une décision finale. Avant la rédaction des migrations Django et la création des modèles, cette proposition doit être approuvée par l'équipe.
- Ligne 373 : « Document proposé par Product & Architecture. En attente d'approbation. »

Avertissement clair et visible.

---

### AC-7 : Relations Expense → User et Category documentées

**Statut :** ✓ PASS

**Evidence :**
- EXPENSE, tableau (lignes 119-120) :
  - `user_id` : FK → USER.id, NOT NULL — Propriétaire de la dépense.
  - `category_id` : FK → CATEGORY.id, NOT NULL — Catégorie de la dépense.
- Tableau de relations (lignes 176-182) :
  - `USER → EXPENSE` : 1:N, « Un utilisateur crée plusieurs dépenses ».
  - `CATEGORY → EXPENSE` : 1:N, « Une catégorie a plusieurs dépenses ».
- Contraintes d'intégrité (lignes 132-135) : FK avec CASCADE on DELETE pour user_id.

Propriété d'une dépense clairement unidirectionnelle.

---

### AC-8 : Cohérence avec code existant

**Statut :** ✓ PASS

**Evidence :**

1. **BigAutoField :**
   - Spec ligne 144-146 : `DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"` dans settings.
   - Doc ERD lignes 305-310 : Section « BigAutoField pour les clés primaires » affirmant utilisation de `BIGSERIAL`.
   - **Vérification backend :** `backend/cashmire/settings.py` ligne 80 confirme `DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"`.

2. **Base de données PostgreSQL :**
   - Doc ERD ligne 345 : Database engine = PostgreSQL.
   - **Vérification backend :** `settings.py` ligne 57 confirme `"ENGINE": "django.db.backends.postgresql"`.
   - Types utilisés (NUMERIC, BIGSERIAL, TIMESTAMP) sont dialecte PostgreSQL.

3. **Pas d'héritage multi-table :**
   - Spec ligne 146, Doc ERD ligne 347 : Pas de `AbstractBaseUser` personnalisé.
   - Utilisation de Django `User` de base.

4. **AUTH_USER_MODEL :**
   - Aucun override dans settings.py (vérifié).
   - Valeur par défaut utilisée : `django.contrib.auth.models.User`.

5. **Migration 0001 vide :**
   - Spec ligne 230 : `backend/api/migrations/0001_initial.py` — Migration vide.
   - **Vérification :** Fichier confirmé vide (`operations = []`).

6. **Aucun models.py existant :**
   - Spec ligne 147 : `backend/api/` ne contient pas de modèles aujourd'hui.
   - **Vérification :** Pas de `backend/api/models.py` présent.

---

### AC-9 : Aucun point d'ambiguïté sans mention

**Statut :** ✓ PASS

**Evidence :**
- Spec, section 4.1 « Questions ouvertes » (lignes 165-175) énumère Q-1 à Q-6.
- Spec, section 4.2 « Risques » (lignes 176-185) énumère R-1 à R-6.
- Doc ERD intègre ces questions et risques sous :
  - « Modèles conditionnels — Issue #6 » pour Q-1 (ownership des catégories).
  - « Décisions de conception » (section 5, lignes 302-338) pour les autres choix.
  - References (lignes 364-369) pour traçabilité vers la spec.

---

## Constats — Classification

### Aucun constat bloquant

---

### Constats non-bloquants

#### 1. Divergence intentionnelle sur `password` vs `password_hash`

**Sévérité :** Non-bloquant (clarification cosmétique)

**Description :**
- Spec ligne 53 : Champ nommé `password_hash`.
- Doc ERD ligne 81 : Champ nommé `password`.

**Justification :**
- Doc ERD ligne 347 : « Utilisation de Django `User` de base. Champ `password` au lieu de `password_hash`. »
- Django `User` model appelle ce champ `password` (le hash est implicite).
- C'est l'alignement correct avec Django defaults.
- Spec ligne 61 reconnaît : « Pas d'héritage multi-table Django pour rester simple. »

**Conclusion :** Non-problématique. La doc est plus précise que la spec.

---

#### 2. Ajout de contraintes CHECK au-delà de la spec

**Sévérité :** Non-bloquant (amélioration positive)

**Description :**
- Spec Budget ligne 124 : « `period_start <= period_end` (vérifiée à la couche application, pas de CHECK en SQL pour cette MVP). »
- Doc ERD ligne 148 : `CHECK(period_end >= period_start)` ajoutée.
- Spec Expense ligne 96 : Aucune contrainte CHECK sur `amount > 0`.
- Doc ERD ligne 121 : `CHECK(amount > 0)` ajoutée.

**Justification :**
- Les CHECK au niveau DB sont une meilleure défense en profondeur.
- Spec Budget ligne 167 : « Valide à la base de données, indépendamment de la couche application. »
- Commit 8d8f05a : Point 3 du message mentionne l'ajout de CHECK constraints.

**Conclusion :** Amélioration positive, non une déviation. Defensive coding bienvenue.

---

#### 3. `alert_threshold` sans logique associée

**Sévérité :** Non-bloquant (risque R-1 accepté)

**Description :**
- Spec ligne 118 : Champ `alert_threshold` avec DEFAULT 80.00 et question ouverte Q-2 sur où la logique de calcul/notification vit.
- Doc ERD ligne 149 : Champ présent avec CHECK sur plage (0-100).
- Aucune logique implémentée aujourd'hui (déféré à issue #7).

**Justification :**
- Spec ligne 180-181 (R-1) : Risque identifié et mitigé. « Documenter clairement dans l'issue #7 (notifications budgétaires) que cette colonne attend une mise en œuvre. »
- Doc ERD ligne 149 : Justification : « Seuil d'alerte en pourcentage. ... Implémentation de la logique dans future issue. »

**Conclusion :** Point ouvert accepté. Pas de blocage.

---

#### 4. Absence de la relation USER→CATEGORY dans le diagramme Mermaid

**Sévérité :** Non-bloquant (intentionnel, bien expliqué)

**Description :**
- Diagramme Mermaid (lignes 11-62) omet la relation USER↔CATEGORY.
- Tableau de relations (ligne 180) note : « À définir (issue #6) ».

**Justification :**
- Spec ligne 15 : « Cette question est explicitement marquée comme point ouvert pour l'issue #6. »
- Doc ERD ligne 259 : « n'inclut pas la relation USER ↔ CATEGORY pour refléter cette ambiguïté ouverte. »
- Section complète (lignes 186-262) présente les deux scénarios.

**Conclusion :** Choix de conception judicieux pour visualiser l'indécision. Aucun risque.

---

#### 5. Indices suggérés sans migration

**Sévérité :** Non-bloquant (recommandations futures)

**Description :**
- Doc ERD cite des indices suggérés (ex. USER lignes 89-91, EXPENSE lignes 127-130, BUDGET lignes 153-155).
- Spec ne mentionne pas d'indices.

**Justification :**
- Doc ERD ligne 337-338 : « À appliquer lors de la rédaction des migrations. Ne pas sur-indexer. »
- Recommandations utiles pour la performance future. Pas implémentées aujourd'hui.

**Conclusion :** Ajout pertinent, non une déviation.

---

#### 6. Manque de mention de la devise (currency)

**Sévérité :** Non-bloquant (limitation MVP acceptée)

**Description :**
- Spec Q-4 (ligne 172) : « Gestion des devises : support multi-devise ou devise fixe ? »
- Aucun champ `currency` sur EXPENSE ou BUDGET.
- Spec ligne 198 : « Multi-devise : Support de différentes devises par transaction ou par utilisateur. MVP : devise unique. »

**Justification :**
- Spec ligne 198 : Déféré à issue future, MVP non-multidevise.
- Doc ERD cohérent avec cette décision.

**Conclusion :** Acceptable pour MVP.

---

## Synthèse du statut de conformité

| Critère | Statut | Notes |
|---------|--------|-------|
| AC-1 (Document + Mermaid) | ✓ PASS | Diagramme syntaxiquement valide, 4 entités, relations claires. |
| AC-2 (Listes complètes) | ✓ PASS | Tous les champs, types, contraintes documentés. |
| AC-3 (Montants NUMERIC) | ✓ PASS | NUMERIC(10,2) sur Expense et Budget, jamais float. |
| AC-4 (UNIQUE Budget) | ✓ PASS | Contrainte composée sur (user_id, category_id, period_start, period_end). |
| AC-5 (Issue #6 point ouvert) | ✓ PASS | Clairement marqué, deux scénarios présentés. |
| AC-6 (Bandeau approbation) | ✓ PASS | Visible en en-tête et pied de page. |
| AC-7 (Expense → User/Category) | ✓ PASS | Relations documentées, FKs NOT NULL. |
| AC-8 (Cohérence backend) | ✓ PASS | BigAutoField, PostgreSQL, pas de héritage, pas de override AUTH_USER_MODEL. |
| AC-9 (Pas d'ambiguïté) | ✓ PASS | Questions et risques énumérés avec mitigation. |

---

## Code applicatif

**Vérification :** Aucun code applicatif modifié.

- Commit 8d8f05a : Seul `docs/erd.md` touché (373 insertions).
- Pas de `backend/api/models.py` créé.
- Pas de migrations générées (`0001_initial.py` reste vide).
- Pas de code de vue, serializer, ou route modifié.

---

## Mises en garde

1. **Approbation requise avant implémentation :** Cette spec est une documentation, pas une implémentation. L'équipe doit approuver avant que les modèles Django et migrations ne soient écrits.

2. **Issue #6 critique :** Résoudre l'ownership des catégories (point ouvert) **avant de commencer la migration 0002_initial_models**. C'est un point de synchronisation critique (risque R-2 dans la spec).

3. **Soft-delete partiel :** USER et CATEGORY ont `is_active`, mais EXPENSE et BUDGET n'en ont pas. Documenter cette politique de suppression dans une future décision (Question ouverte Q-2).

4. **Alert_threshold sans mise en œuvre :** Le champ existe mais la logique arrive avec issue #7. Ne pas créer le champ si issue #7 n'existe pas.

---

## Recommandation

**APPROUVABLE.** Le document satisfait tous les critères d'acceptation. Les divergences mineures (password_hash vs password, ajouts de CHECK) sont des améliorations, non des déviances. Les points ouverts sont explicitement marqués.

Prochaines étapes :
1. Approbation de cette spec par l'équipe.
2. Résolution et approbation d'issue #6 (ownership des catégories).
3. Création de `backend/api/models.py` et migration `0002_initial_models.py` par le Full-Stack Development agent.
4. Ouverture des issues de spécifications API (routes CRUD, routes de filtrage).

