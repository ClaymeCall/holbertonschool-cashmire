# Spécification — Endpoint de mise à jour de budget (issue #48)

- **Issue :** #48 — Implement update budget endpoint
- **Statut :** Proposé, à relire par l'équipe
- **Auteur :** Product & Architecture Agent
- **Date :** 2026-10-07
- **Scope :** Endpoint PATCH `/api/budgets/<id>/` + tests (pas DELETE, pas GET détail, pas frontend)

---

## 1. Problème et acceptation

### 1.1 User Story

En tant qu'utilisateur authentifié, je souhaite **modifier un budget existant** pour ajuster son montant, son seuil d'alerte, ou sa catégorie/période si nécessaire, afin de maintenir mes limites de dépenses à jour sans devoir supprimer et recréer un budget.

### 1.2 Acceptation

- [ ] `PATCH /api/budgets/:id` valide l'ownership du budget et les données d'entrée
- [ ] Modification de `category_id` ou de `period_start`/`period_end` re-valide la contrainte d'unicité (user, category, period_start, period_end)
- [ ] Retourne 404 pour un budget inexistant ou appartenant à un autre utilisateur
- [ ] Retourne 200 OK avec le budget modifié et ses métriques de consommation (spent, remaining, percentage)
- [ ] Retourne 409 Conflict si modification du budget crée un doublon ou si race condition détectée

---

## 2. Modèle de données

### 2.1 Aucun changement

Le modèle `Budget` (défini en `backend/api/models.py`) n'est pas modifié. Il contient déjà :

- `user` (FK, CASCADE) — propriétaire du budget
- `category` (FK, PROTECT) — catégorie du budget
- `amount` (Decimal, 2 places, > 0)
- `period_start` (Date)
- `period_end` (Date, >= period_start)
- `alert_threshold` (Decimal, nullable, 0..100 ou null, défaut 80.00)
- `created_at`, `updated_at` (auto)

**Unicité existante :** `UNIQUE(user, category, period_start, period_end)`

### 2.2 Service de consommation (existant)

Le service `backend/api/services/budget_consumption.py` calcule dynamiquement pour chaque budget :
- `spent` : Somme des Expense pour (user, category, period_start, period_end)
- `remaining` : `amount - spent`
- `percentage` : `(spent / amount) * 100` (non plafonné, peut dépasser 100 si sur-dépense)

---

## 3. API — Route de mise à jour

### 3.1 `PATCH /api/budgets/{id}/`

**Authentification :** Requise (SessionAuthentication + IsAuthenticated)

**Description :** Modifier un budget existant. Tous les champs sont optionnels. La modification peut inclure `category_id`, `period_start`, ou `period_end`, re-validant ainsi la contrainte d'unicité du budget.

**Paramètres de chemin :**
- `id` (integer) : Identifiant du budget

**Corps de requête (application/json, tous les champs optionnels) :**
```json
{
  "amount": "600.00",
  "alert_threshold": "75.00",
  "category_id": 6,
  "period_start": "2026-10-01",
  "period_end": "2026-10-31"
}
```

**Champs de requête (optionnels) :**
- `amount` (string) : Nouveau montant (Decimal, doit être > 0 si fourni)
- `alert_threshold` (string ou null) : Nouveau seuil d'alerte (0–100 ou null si fourni)
- `category_id` (integer) : Nouvelle catégorie (doit appartenir à l'utilisateur courant si fourni)
- `period_start` (date) : Nouvelle date de début (YYYY-MM-DD, si fournie)
- `period_end` (date) : Nouvelle date de fin (YYYY-MM-DD, si fournie)

**Contraintes de validation :**
- `amount`, si modifié, doit être > 0 et format Decimal valide.
- `alert_threshold`, si modifié, doit être entre 0 et 100, ou null.
- `category_id`, si modifié, doit exister et appartenir à l'utilisateur courant.
- `period_end`, si modifié, doit être >= `period_start` (utiliser la nouvelle valeur si fournie, sinon la valeur existante pour un PATCH partiel).
- **Unicité** : Après modification, (user, category, period_start, period_end) doit rester unique. Le budget lui-même est exclu de ce contrôle de doublon (pour éviter 409 lors de mises à jour sans changement de ces champs).
  - Détection applicative : Query `Budget.objects.filter(user=request.user, category_id=new_category, period_start=new_period_start, period_end=new_period_end).exclude(id=budget.id).exists()`
  - Rattrapage IntegrityError (race condition) : Si duplicate est créé entre la vérification applicative et la mise à jour, retourner 409 Conflict.
- `user_id` du budget n'est jamais modifiable (lecture seule, provenant de la session).

**Réponse 200 OK :**
```json
{
  "id": 1,
  "user_id": 1,
  "category_id": 6,
  "amount": "600.00",
  "period_start": "2026-10-01",
  "period_end": "2026-10-31",
  "alert_threshold": "75.00",
  "spent": "234.50",
  "remaining": "365.50",
  "percentage": "39.08",
  "created_at": "2026-10-01T10:00:00Z",
  "updated_at": "2026-10-07T14:00:00Z"
}
```

**Champs de réponse :**
- `id`, `user_id`, `category_id`, `amount`, `period_start`, `period_end`, `alert_threshold`, `created_at`, `updated_at` : Identiques à la structure de création.
- `spent`, `remaining`, `percentage` : Calculés dynamiquement par le service de consommation, en fonction des Expense existantes.

**Erreurs possibles :**

| Code | HTTP | Message | Condition |
|------|------|---------|-----------|
| `INVALID_DATA` | 400 | `"amount": "Doit être > 0"` | amount ≤ 0 |
| `INVALID_DATA` | 400 | `"alert_threshold": "Doit être entre 0 et 100"` | alert_threshold hors [0, 100] et non null |
| `INVALID_DATA` | 400 | `"period_end": "Doit être >= period_start"` | period_end < period_start (après résolution des valeurs partielles) |
| `INVALID_DATA` | 400 | Erreur de validation DRF standard | Données mal formées (type invalide, format date, etc.) |
| `UNAUTHORIZED` | 401 | `"error": "UNAUTHORIZED", "message": "Token invalide ou expiré"` | Token absent, expiré ou invalide |
| `NOT_FOUND` | 404 | `"error": "NOT_FOUND", "message": "Budget non trouvé"` | Budget inexistant, ou ownership échoue (appartient à un autre user) |
| `NOT_FOUND` | 404 | `"error": "NOT_FOUND", "message": "Catégorie non trouvée"` | category_id fourni n'existe pas ou appartient à un autre user |
| `CONFLICT` | 409 | `"error": "CONFLICT", "message": "Budget déjà existant pour cette période et catégorie"` | Application : doublon détecté après modification (excluant l'ID du budget lui-même) |
| `CONFLICT` | 409 | `"error": "CONFLICT", "message": "Budget déjà existant pour cette période et catégorie"` | Race condition : IntegrityError lors de la sauvegarde |

### 3.2 À propos de PUT (optionnel)

L'issue #48 n'exige qu'un PATCH. Un PUT (remplacement complet du budget) est **optionnel** et n'est pas inclus dans cette spécification. Si implémenté ultérieurement (autre issue), il suivrait le même pattern de validation et retournerait 200 OK avec le budget modifié.

---

## 4. Décisions de design

### 4.1 Modifiabilité de category_id, period_start, period_end

**Décision :** Ces champs **sont modifiables** via PATCH, avec re-validation de l'unicité.

**Justification :**
- `docs/api-design.md` §4.4 note qu'ils sont "généralement non modifiables, à confirmer".
- L'issue #48 demande explicitement la re-validation de l'unicité lors du changement de catégorie ou période.
- Use case : Un utilisateur souhaite déplacer un budget vers une période différente ou une catégorie différente sans le supprimer.
- **Impact sémantique** : Modifier ces champs change logiquement le budget (cat/période), ce qui est acceptable pour un PATCH partiel.
- **Écart documenté :** Ce présent document formalise cette décision qui s'écarte de l'hypothèse "généralement non modifiables" de §4.4.

### 4.2 Gestion de la race condition et de l'unicité

**Approche multi-couche :**
1. **Niveau applicatif** : Avant UPDATE, vérifier qu'aucun autre budget (excluant l'ID courant) ne porte la combinaison (user, category, period_start, period_end).
2. **Niveau base de données** : La contrainte UNIQUE existante capturerait un doublon éventuel.
3. **Rattrapage IntegrityError** : Si un doublon est créé entre 1 et 2 (race condition), attraper l'exception et retourner 409 Conflict avec message unifié.

**Exclusion du budget lui-même :** Le contrôle applicatif exclut l'ID du budget en cours de modification (`.exclude(id=budget.id)`) pour éviter 409 lors d'une mise à jour qui ne change pas category/period.

### 4.3 Format d'erreur et réutilisation

**Réutilisation existante :**
- Structure uniforme : `{ "error": "<code>", "message": "<description>" }` (docs/api-design.md §1.5)
- Codes existants : INVALID_DATA, NOT_FOUND, UNAUTHORIZED, CONFLICT
- Serializers existants : `BudgetSerializer` pour validation (amount, alert_threshold, period_end >= period_start), `BudgetWithConsumptionSerializer` pour réponse avec spent/remaining/percentage
- Exceptions DRF : ValidationError mappé à 400 Bad Request avec détails par champ

### 4.4 Ownership et confidentialité

**Contrôle :** Avant toute opération, valider `budget.user_id == request.user.id`.

**Retour en cas d'échec :** 404 NOT_FOUND avec message générique "Budget non trouvé" (pas 403 Forbidden, conformément à docs/api-design.md §1.6 : confusion intentionnelle avec inexistence de ressource).

---

## 5. Détails d'implémentation (pour Full-Stack Agent)

### 5.1 Données en entrée et résolution partielle (PATCH)

**Principe PATCH :** Un champ absent de la requête n'est pas modifié.

**Exemple :**
```json
PATCH /api/budgets/1
{ "amount": "700.00" }
```
- `category_id`, `period_start`, `period_end`, `alert_threshold` : conservent leur valeur BD existante.
- `amount` : passe à 700.00.
- Unicité : vérifiée avec (user, category **existante**, period_start **existante**, period_end **existante**).

**Validation des dates :**
```python
period_start_new = serializer.validated_data.get("period_start", budget.period_start)
period_end_new = serializer.validated_data.get("period_end", budget.period_end)

if period_end_new < period_start_new:
    raise ValidationError("period_end doit être >= period_start")
```

### 5.2 Vérification de doublon applicatif

```python
# Après validation du serializer, avant sauvegarde
category_new = serializer.validated_data.get("category_id")
if category_new is None:
    category_new = budget.category_id

period_start_new = serializer.validated_data.get("period_start", budget.period_start)
period_end_new = serializer.validated_data.get("period_end", budget.period_end)

# Vérifier qu'aucun autre budget n'a cette combinaison
if Budget.objects.filter(
    user=request.user,
    category_id=category_new,
    period_start=period_start_new,
    period_end=period_end_new,
).exclude(id=budget.id).exists():
    return Response(
        {
            "error": "CONFLICT",
            "message": "Budget déjà existant pour cette période et catégorie",
        },
        status=status.HTTP_409_CONFLICT,
    )
```

### 5.3 Rattrapage IntegrityError

```python
try:
    with transaction.atomic():
        # Met à jour tous les champs fournis
        budget.amount = serializer.validated_data.get("amount", budget.amount)
        budget.alert_threshold = serializer.validated_data.get("alert_threshold", budget.alert_threshold)
        budget.category_id = serializer.validated_data.get("category_id", budget.category_id)
        budget.period_start = serializer.validated_data.get("period_start", budget.period_start)
        budget.period_end = serializer.validated_data.get("period_end", budget.period_end)
        budget.save()
except IntegrityError:
    return Response(
        {
            "error": "CONFLICT",
            "message": "Budget déjà existant pour cette période et catégorie",
        },
        status=status.HTTP_409_CONFLICT,
    )
```

### 5.4 Réponse 200 avec consommation

```python
# Après sauvegarde réussie
from api.services.budget_consumption import calculate_consumption

consumption = calculate_consumption(budget)
context = {"consumption_data": {budget.id: consumption}}
serializer = BudgetWithConsumptionSerializer(budget, context=context)

return Response(serializer.data, status=status.HTTP_200_OK)
```

---

## 6. Périmètre et hors-scope

### 6.1 Inclus

- Endpoint PATCH `/api/budgets/<id>/`
- Tests unitaires et d'intégration pour :
  - Modification validée, retour 200 OK + consommation
  - Validation échouée (montant, seuil, dates), retour 400
  - Doublon après modif, retour 409
  - Budget inexistant ou ownership échoue, retour 404
  - Catégorie inexistante ou d'un autre user, retour 404
  - Authentification manquante, retour 401

### 6.2 Hors-scope

- `DELETE /api/budgets/<id>/` (issue #49)
- `GET /api/budgets/<id>/` (GET détail — non planifié pour MVP)
- `PUT /api/budgets/<id>/` (remplacement complet — optionnel, autre issue si besoin)
- Frontend SvelteKit (éditeur de budget, etc. — autre issue)
- Rate limiting (futur, déploiement production)

---

## 7. Questions ouvertes et risques

| Élément | Question | Mitigation |
|---------|----------|-----------|
| **Sérialisation d'alert_threshold** | Si `alert_threshold` est null dans BD, comment le JSON serialize-t-il ? Toujours chaîne "null" ou absent du JSON ? | DRF : null → `null` en JSON. Documenter le comportement dans la réponse d'exemple. |
| **Dates en format YYYY-MM-DD** | PATCH accepte-t-il d'autres formats (ISO 8601, timestamps Unix) ? | Non, MVP : YYYY-MM-DD uniquement. DRF lève ValidationError si format invalide. |
| **Modif de category_id vers catégorie d'un autre user** | Contrôle d'ownership de category détecte-t-il cela ? | Oui : `Category.objects.get(id=category_id, user=request.user)` lève DoesNotExist → 404 "Catégorie non trouvée". |
| **Mélange PATCH partial et validation de contrainte** | Si PATCH `{ "period_end": "2026-09-30" }` mais budget existant a period_start=2026-10-01, erreur validée ? | Oui : validation utilise period_start existante (si pas en requête), détecte period_end < period_start. Retour 400 "period_end doit être >= period_start". |

---

## 8. Références et conformité

### 8.1 Documents référencés

- `docs/api-design.md` — Contrat API existant (section §4.4 PATCH budgets, §1.5 format erreur, §1.6 ownership)
- `backend/api/models.py` — Modèle Budget avec unicité, check constraints
- `backend/api/views.py` — Serializers BudgetSerializer, BudgetWithConsumptionSerializer ; pattern de gestion d'erreur
- `backend/api/services/budget_consumption.py` — Service de calcul spent/remaining/percentage
- `docs/mvp-scope.md` — Scope MVP

### 8.2 Conformité spec

- ✓ Authentification requise (SessionAuthentication + IsAuthenticated)
- ✓ Ownership : 404 générique pour budgets d'autres users
- ✓ Champs optionnels : amount, alert_threshold, category_id, period_start, period_end
- ✓ Re-validation d'unicité pour category/période
- ✓ Validations identiques à POST (amount > 0, alert_threshold 0..100, period_end >= period_start, catégorie du user)
- ✓ Doublon applicatif + rattrapage IntegrityError → 409
- ✓ Réponse 200 avec spent/remaining/percentage (du service de consommation)
- ✓ User jamais modifiable
- ✓ Réutilisation des serializers et formats d'erreur existants

---

*Spécification produite par l'agent Product & Architecture pour issue #48. À valider par l'équipe avant implémentation.*
