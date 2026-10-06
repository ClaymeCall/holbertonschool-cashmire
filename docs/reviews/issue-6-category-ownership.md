# Revue QA — Propriété des catégories (Issue #6)

**Spec révisée :** `docs/specs/issue-6-category-ownership.md`  
**Implémentation :** `docs/decisions/category-ownership.md`, `docs/erd.md` (modifié)  
**Statut de la revue :** Prêt pour approbation de l'équipe  
**Date :** 2026-10-06

---

## Résumé exécutif

La documentation (spec, décision, ERD) est **conforme à tous les critères d'acceptation** et **cohérente**. Pas de blocage. Trois suggestions non-bloquantes identifiées pour renforcer la sécurité et clarifier les décisions futures.

---

## Conformité aux critères d'acceptation

### AC-1 : Document de décision ✓ PASS

**Critère :** Un document `docs/decisions/category-ownership.md` existe et énonce la décision choisie (A ou B), le raisonnement, les compromis, et les alternatives rejetées.

**Évidence :**
- Fichier existe : `docs/decisions/category-ownership.md`
- Décision claire : Scénario B (catégories scoped par utilisateur) retenu
- Raisonnement : 5 principes documentés (flexibilité, confidentialité, contrôles d'accès, faible surcoût, extensibilité)
- Compromis acceptés : duplication de seed data, requêtes API scoped
- Alternatives écartées : Scénario A explicitement rejeté avec justification

**Résultat :** Conforme.

---

### AC-2 : Spec présente les deux scénarios ✓ PASS

**Critère :** La spec `docs/specs/issue-6-category-ownership.md` présente les deux scénarios, la recommandation de l'équipe, et les impacts sur l'ERD.

**Évidence :**
- Section 2.1 : Scénario A (catégories partagées) détaillé avec avantages/inconvénients
- Section 2.2 : Scénario B (catégories scoped) détaillé avec avantages/inconvénients
- Section 2.3 : Recommandation formelle de l'équipe (Scénario B) avec justification structurée
- Section 3 : Impacts sur modèle de données énumérés
- Section 4 : Routes API affectées listées dans un tableau

**Résultat :** Conforme.

---

### AC-3 : ERD mis à jour ✓ PASS

**Critère :** `docs/erd.md` est mis à jour pour refléter le scénario choisi : la section « Modèles conditionnels » est remplacée par la structure unique retenue.

**Évidence (via git diff) :**
- La section « Modèles conditionnels » (anciennement lines 180+) a été supprimée
- Remplacée par section « Décision de conception — Issue #6 » qui énonce la décision B
- Références aux deux scénarios conditionnels supprimées
- Structure documentée maintenant comme définitive, non conditionnelle

**Résultat :** Conforme.

---

### AC-4 : Diagramme Mermaid inclut USER ↔ CATEGORY ✓ PASS

**Critère :** Le diagramme Mermaid inclut la relation `USER` ↔ `CATEGORY`.

**Évidence (via git diff, ligne 15 du nouveau diagramme) :**
```
USER ||--o{ CATEGORY : owns
```
Relation 1:N ajoutée (un utilisateur possède zéro ou plusieurs catégories).

**Résultat :** Conforme.

---

### AC-5 : Scénario B : Structure Category ✓ PASS

**Critère :** `Category` table inclut `user_id BIGINT FK → USER.id`, contrainte `UNIQUE(user_id, name)`, index sur `user_id`.

**Évidence :**
- `user_id BIGINT FK → USER.id, NOT NULL` : ligne 101 du diff `erd.md`
- Suppression en cascade `ON DELETE CASCADE` : documentée ligne 101
- Contrainte `UNIQUE(user_id, name)` : présente ligne 110 du diff (section CATEGORY)
- Indices : 
  - `idx_category_user_id` sur `user_id` : proposé
  - `idx_category_user_id_name` sur `(user_id, name)` : proposé
- Confirmé dans la décision ligne 17-18 : "Contrainte `UNIQUE(user_id, name)` : un utilisateur ne peut pas avoir deux catégories portant le même nom."

**Résultat :** Conforme.

---

### AC-6 : Scénario A — N/A

Le scénario A (catégories partagées) a été rejeté en faveur du B. Critère non applicable.

---

### AC-7 : Routes API énumérées ✓ PASS

**Critère :** La spec énumère les implications pour les routes API.

**Évidence :**
- Section 4.1 « Gestion des catégories » de la spec : tableau avec 5 routes :
  - GET `/api/users/{user_id}/categories/`
  - POST `/api/users/{user_id}/categories/`
  - GET `/api/users/{user_id}/categories/{cat_id}/`
  - PATCH `/api/users/{user_id}/categories/{cat_id}/`
  - DELETE `/api/users/{user_id}/categories/{cat_id}/`
- Chaque route inclut : méthode, auth, paramètres, réponse (200), erreurs
- Tous les endpoints scoped par `user_id` dans le chemin

**Résultat :** Conforme.

---

### AC-8 : Stratégie seed data documentée ✓ PASS

**Critère :** La stratégie de données seed pour le MVP est documentée.

**Évidence :**
- Section 5 de la spec : "Stratégie de données seed pour le MVP"
- ~15 catégories par défaut énumérées en français : Alimentation, Transport, Logement, Loisirs, Santé, Vêtements, Éducation, Divertissement, Services, Épargne, Investissements, Autres
- Implémentation proposée : signal Django `post_save` sur `User` ou commande management
- Déclenchement : à l'inscription d'un nouvel utilisateur
- Avantage documenté : l'utilisateur démarre avec une nomenclature raisonnable
- Confirmé dans ERD ligne 217-218 : "À l'inscription, créer ~15 catégories par défaut pour chaque utilisateur"

**Résultat :** Conforme.

---

### AC-9 : Points ouverts énumérés ✓ PASS

**Critère :** Les points ouverts mineurs sont énumérés sans être tranchés.

**Évidence :**
- Spec section 6 « Points ouverts et risques » :
  - Q-1 : Soft-delete vs. suppression physique pour Category
  - Q-2 : Suppression en cascade pour Expense/Budget
  - Q-3 : Catégories partagées (future)
  - Q-4 : Ordre/tri des catégories
- Décision section « Questions réservées » :
  - Soft-delete vs. suppression physique
  - Gestion des dépenses orphelines
  - Édition et versioning des catégories
  - Ordonnement
- Risques identifiés (section 6.2 de la spec) avec sévérité « basse »

**Résultat :** Conforme.

---

## Cohérence ERD ↔ Décision

### Structure ✓

| Élément | Décision | ERD | Concordance |
|---------|----------|-----|-------------|
| `user_id` présent | OUI | OUI (FK NOT NULL) | ✓ |
| Type `user_id` | BIGINT FK | BIGINT FK → USER.id | ✓ |
| ON DELETE behavior | CASCADE | CASCADE | ✓ |
| Contrainte UNIQUE | `(user_id, name)` | `UNIQUE(user_id, name)` | ✓ |
| Index `user_id` | Proposé | Proposé | ✓ |
| Index `(user_id, name)` | Proposé | Proposé | ✓ |

### Relations ✓

Diagramme Mermaid : `USER ||--o{ CATEGORY : owns` aligne avec la décision (1:N).

### Impacts documentés ✓

- EXPENSE : `category.user_id == expense.user_id` validation ajoutée (ERD diff ligne 126)
- BUDGET : `category.user_id == budget.user_id` validation ajoutée (ERD diff ligne 152)

---

## Analyse de sécurité (IDOR, ownership)

### CATEGORY ownership ✓ PASS

**Routes API :**
- Toutes les routes incluent `user_id` dans le chemin : `/api/users/{user_id}/categories/{cat_id}/`
- Implique une vérification `user_id == request.user.id` ou 403 Forbidden

**Contrainte base de données :**
- `user_id BIGINT NOT NULL FK` : chaque catégorie appartient à un utilisateur, immuable après création

**Validation applicative :**
- ERD documente : "seul l'utilisateur propriétaire (ou un admin) peut CRUD ses catégories"
- Permission explicite à implémenter

**Risque IDOR :** Absent si permission est appliquée correctement.

### EXPENSE ownership (utilisant Category) ✓ PASS

**Critère de sécurité :**
- Spec section 3.3 : "L'API doit vérifier que `category.user_id == expense.user_id`"
- ERD ligne 126 (ajouté) : "L'API doit valider que `category.user_id == expense.user_id`"
- Spec ligne 194-195 : Requête sécurisée suggérée avec JOIN

**Type de validation :**
- Applicative (code Python), non SQL
- Spec l.201 : "Ces validations ne sont pas des contraintes SQL explicites"

**Risque identifié (R-3, sévérité basse) :** "Une faille de sérialisation pourrait créer une incohérence" — bien documenté.

### BUDGET ownership (utilisant Category) ✓ PASS

**Critère de sécurité :**
- Spec section 3.3 : "Même validation : `category.user_id == budget.user_id`"
- ERD ligne 152 (ajouté) : "L'API doit valider que `category.user_id == budget.user_id`"

**Type de validation :**
- Applicative (code Python), non SQL

**Risque identifié (R-3)** : Même que EXPENSE.

---

## Suggestions non-bloquantes

### SG-1 : Renforcer la validation ownership avec une trigger SQL ⚠ NON-BLOQUANT

**Observation :**
- Les validations `category.user_id == expense.user_id` et `category.user_id == budget.user_id` sont appliquées en code Python, pas en SQL.
- C'est documenté et intentionnel (MVP simple), mais crée un risque unique de sérialisation.

**Suggestion :**
- Pour une issue future (performance/sécurité), considérer une trigger PostgreSQL qui vérifie `NEW.user_id = (SELECT user_id FROM category WHERE id = NEW.category_id)` avant INSERT/UPDATE.
- Cela doublerait la validation (défense en profondeur).

**Référence :**
- Spec l.273 (risque R-3) : "Une faille de sérialisation pourrait créer une incohérence. Considérer une trigger SQL pour double validation."
- Déjà proposé dans la spec, pas une découverte nouvelle.

**Impact :** Suggestion pour une issue future, ne bloque pas l'approbation.

---

### SG-2 : Clarifier la politique de suppression (CASCADE) pour category_id dans EXPENSE ⚠ NON-BLOQUANT

**Observation :**
- ERD ligne 141 : "FK `category_id` → `CATEGORY(id)` **(avec RESTRICT ou SET NULL selon la politique de suppression de catégories)**"
- ERD ligne 177 (BUDGET) : "FK `category_id` → `CATEGORY(id)` **avec RESTRICT**"

**Ambiguïté :**
- BUDGET est clair (RESTRICT).
- EXPENSE n'est pas tranché (RESTRICT ou SET NULL).

**Suggestion :**
- L'issue Q-2 (« Suppression en cascade pour Expense/Budget ») est bien énumérée comme point ouvert.
- Pour l'implémentation, clarifier explicitement : si une catégorie est supprimée, qu'advient-il d'une dépense qui la référence ?
  - RESTRICT : empêcher la suppression (recommandé pour MVP, évite la perte de données)
  - SET NULL : autoriser la suppression, mettre la dépense « sans catégorie » (moins sûr pour l'intégrité)

**Impact :** Suggestion pour une issue future (Q-2), ne bloque pas l'approbation. À clarifier avant l'implémentation.

---

### SG-3 : Documenter le comportement lors de soft-delete via `is_active` ⚠ NON-BLOQUANT

**Observation :**
- CATEGORY a un booléen `is_active`.
- ERD l.284 : "Limitation connue : Cette approche partielle peut mener à des incohérences (ex. une dépense avec une catégorie `is_active = false`)."

**Suggestion :**
- La question Q-1 (soft-delete vs. suppression physique) est bien énumérée.
- Pour l'implémentation API, documenter : quand on liste les dépenses d'un utilisateur, faut-il filtrer par `category.is_active = true` ou inclure toutes les catégories ?

**Impact :** Suggestion pour une issue future (Q-1), ne bloque pas l'approbation.

---

## Vérification du français et qualité

| Aspect | Vérification | Résultat |
|--------|-------------|----------|
| Titres et sections | En français | ✓ |
| Descriptions entités | En français | ✓ |
| Exemples et libellés | En français (ex. « Alimentation », « Transport ») | ✓ |
| Noms de champs/colonnes | Convention anglaise (standard SQL/Django) | ✓ |
| Cohérence terminologique | « Propriété », « scoped », « ownership », « cascader » utilisés cohérents | ✓ |

**Résultat :** Français de qualité, avec bon sens des conventions de nommage.

---

## Conclusion

**Statut :** ✓ **PRÊT POUR APPROBATION**

Tous les critères d'acceptation (AC-1 à AC-9) sont **conformes**. La documentation est :
- **Complète** : spécification, décision, ERD alignés
- **Cohérente** : aucune contradiction interne
- **Sécurisée** : contrôles d'ownership documentés (IDOR mitigation présente)
- **Traçable** : points ouverts et risques énumérés
- **Extensible** : structure B permet des catégories partagées futures

**Prochaine étape :** Approbation par l'équipe (Product, Backend Lead, Frontend Lead) avant la rédaction des migrations et du code applicatif.

---

*Revue réalisée le 2026-10-06. Aucun blocage. Trois suggestions non-bloquantes identifiées pour issues futures.*
