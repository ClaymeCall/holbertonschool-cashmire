# Revue QA & Sécurité — Issue #45 Budget Model

**Agent:** qa_security  
**Date:** 2026-10-07  
**Branche :** feat/45-budget-model  
**Spec :** docs/specs/issue-45-budget-model.md  

---

## Résumé exécutif

Tous les **23 tests passent**. L'implémentation du modèle Budget est **conforme à la spécification**. Aucune trouvaille bloquante.

**Verdict :** Aucun blocker. Une trouvaille non-bloquante identifiée (paramètre `check=` vs `condition=`).

---

## Résultats des tests

```
Ran 23 tests in 3.211s
OK
```

Tous les critères d'acceptation sont vérifiés par les tests :

| Test | Statut | Critère AC |
|------|--------|-----------|
| test_create_budget_with_all_fields | ✓ PASS | AC-1, AC-13 |
| test_create_budget_with_default_alert_threshold | ✓ PASS | AC-5, AC-13 |
| test_create_budget_with_null_alert_threshold | ✓ PASS | AC-5, AC-13 |
| test_create_multiple_budgets_different_categories | ✓ PASS | AC-1, AC-13 |
| test_create_multiple_budgets_different_periods | ✓ PASS | AC-1, AC-13 |
| test_duplicate_budget_rejected | ✓ PASS | AC-7, AC-13 |
| test_amount_zero_rejected | ✓ PASS | AC-12, AC-13 |
| test_amount_negative_rejected | ✓ PASS | AC-12, AC-13 |
| test_amount_positive_minimum | ✓ PASS | AC-4, AC-13 |
| test_amount_maximum | ✓ PASS | AC-4, AC-13 |
| test_amount_decimal_precision | ✓ PASS | AC-4, AC-13 |
| test_period_end_before_start_rejected | ✓ PASS | AC-6, AC-13 |
| test_period_end_equals_start | ✓ PASS | AC-6, AC-13 |
| test_period_end_after_start | ✓ PASS | AC-6, AC-13 |
| test_alert_threshold_null_allowed | ✓ PASS | AC-5, AC-13 |
| test_alert_threshold_zero | ✓ PASS | AC-5, AC-13 |
| test_alert_threshold_one_hundred | ✓ PASS | AC-5, AC-13 |
| test_alert_threshold_negative_rejected | ✓ PASS | AC-5, AC-13 |
| test_alert_threshold_over_hundred_rejected | ✓ PASS | AC-5, AC-13 |
| test_user_cascade_delete | ✓ PASS | AC-8, AC-13 |
| test_category_protect_delete | ✓ PASS | AC-9, AC-13 |
| test_category_delete_without_budgets | ✓ PASS | AC-9, AC-13 |
| test_timestamps_created_at_and_updated_at | ✓ PASS | AC-11, AC-13 |

---

## Conformité aux critères d'acceptation

| AC | Critère | Vérification | Statut |
|----|---------|-------------|--------|
| AC-1 | Modèle Budget existe dans models.py | Présent, tous les champs | ✓ OK |
| AC-2 | Migration 0003_budget.py crée la table | Présent avec contraintes et indices | ✓ OK |
| AC-3 | Migration s'applique sans erreur | Tests et migrations OK | ✓ OK |
| AC-4 | Champ `amount` est NUMERIC(10,2) / DecimalField | max_digits=10, decimal_places=2 | ✓ OK |
| AC-5 | Champ `alert_threshold` NUMERIC(5,2), null=True, default=80.00, contrainte 0-100 | Présent, validators + CheckConstraint | ✓ OK |
| AC-6 | Champs `period_start` et `period_end` DateField, contrainte end >= start | DateField présents, CheckConstraint présent | ✓ OK |
| AC-7 | Contrainte UNIQUE composée (user, category, period_start, period_end) | UniqueConstraint présente | ✓ OK |
| AC-8 | FK user → User(id), ON DELETE CASCADE | ForeignKey(on_delete=models.CASCADE) | ✓ OK |
| AC-9 | FK category → Category(id), ON DELETE PROTECT | ForeignKey(on_delete=models.PROTECT) | ✓ OK |
| AC-10 | Indices idx_budget_user_id, idx_budget_user_period | Deux indexes présents dans Meta | ✓ OK |
| AC-11 | Timestamps created_at, updated_at | DateTimeField(auto_now_add/auto_now) | ✓ OK |
| AC-12 | Contrainte CHECK amount > 0 | CheckConstraint(check=models.Q(amount__gt=0)) | ✓ OK |
| AC-13 | Tests couvrent les cas critiques | 23 tests, tous passants | ✓ OK |
| AC-14 | Tests s'exécutent sans erreur | `python manage.py test api.tests.BudgetModelTests` réussit | ✓ OK |

---

## Audit de sécurité

### 1. Validation des données

- **Amount (montant):** Validé à deux niveaux:
  - Django validator: `MinValueValidator(Decimal("0.01"))`
  - Database CHECK constraint: `amount > 0`
  - Précision décimale NUMERIC(10,2) empêche les erreurs de floating-point
  - **Résultat:** ✓ Sécurisé

- **Alert threshold:** Validé à deux niveaux:
  - Django validators: `MinValueValidator(Decimal("0"))`, `MaxValueValidator(Decimal("100"))`
  - Database CHECK constraint: `alert_threshold BETWEEN 0 AND 100` (si non NULL)
  - **Résultat:** ✓ Sécurisé

- **Period dates:** Validé par database CHECK constraint: `period_end >= period_start`
  - **Résultat:** ✓ Sécurisé

### 2. Intégrité référentielle

- **User cascade:** ON DELETE CASCADE — suppression d'utilisateur supprime budgets
  - Vérification: test_user_cascade_delete ✓ PASS
  - **Résultat:** ✓ Sécurisé

- **Category protect:** ON DELETE PROTECT — suppression d'une catégorie avec budgets échoue
  - Vérification: test_category_protect_delete ✓ PASS (IntegrityError levée)
  - **Résultat:** ✓ Sécurisé

### 3. Injection SQL

- Utilisation de Django ORM et migrations (pas de SQL brut)
- Paramètres liés automatiquement par Django
- **Résultat:** ✓ Protégé contre SQL injection

### 4. Fuite d'informations

- Modèle ne contient pas de données sensibles ou de tokens
- Pas de stack traces ou détails de configuration exposés
- __str__ method est sûre (retourne ID, user ID, category name, dates)
- **Résultat:** ✓ Aucune fuite détectée

### 5. Authentification & autorisation

- Le modèle ne gère pas l'auth (rôle de la couche API, future issue)
- Les FK assurent l'ownership (user ownership implicite)
- **Note:** La spec (section 6) note que validation applicative est requise pour `category.user_id == budget.user_id`
- **Résultat:** ✓ Hors scope du modèle; à implémenter dans API

---

## Trouvailles

### Bloquants

**Aucun blocker identifié.**

---

### Non-bloquants

#### 1. Paramètre `check=` vs `condition=` en Django 5.1.3

**Sévérité:** Non-bloquant (maintenance)  
**Localisation:** `backend/api/models.py` lignes 118-129  
**Description:**  
Les contraintes CHECK utilisent le paramètre `check=` :
```python
models.CheckConstraint(
    check=models.Q(amount__gt=0),
    name="budget_amount_positive",
)
```

En Django 5.0+, le paramètre recommandé est `condition=` au lieu de `check=`. La migration générée utilise correctement `condition=`.

**Recommandation:**  
Pour cohérence et conformité avec Django 5.1.3, migrer vers:
```python
models.CheckConstraint(
    condition=models.Q(amount__gt=0),
    name="budget_amount_positive",
)
```

**Impact:** Aucun — Django 5.1.3 accepte `check=` pour backward compatibility, les tests passent. Cette correction est une question de maintenabilité future.

---

## Vérifications supplémentaires

### Accessibilité

Non applicable pour une migration de modèle Django (pas d'interface utilisateur).

### Responsive design

Non applicable pour un modèle de données.

### Déviation de spec

Aucune déviation identifiée. L'implémentation suit exactement la spec.

**Note:** La spec reconnaît en section 6 que la validation `category.user_id == budget.user_id` doit être implémentée au niveau applicatif (couche API). C'est un point ouvert documenté, pas une déviation.

---

## Conclusion

L'implémentation du modèle `Budget` est **conforme**, **sécurisée** et **testée**. Tous les critères d'acceptation sont satisfaits. Aucun blocker n'empêche la fusion.

**Recommandation:** Approuver pour merge après correction mineure (paramètre `condition=`).

---

*Revue réalisée le 2026-10-07 par l'agent qa_security.*
