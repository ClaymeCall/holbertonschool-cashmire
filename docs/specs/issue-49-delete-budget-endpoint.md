# Spécification — Endpoint de suppression de budget (issue #49)

- **Issue :** #49 — Implement delete budget endpoint
- **Statut :** Proposé, à relire par l'équipe
- **Auteur :** Product & Architecture Agent
- **Date :** 2026-10-07
- **Scope :** Endpoint DELETE `/api/budgets/<id>/` + tests (pas de modifications de catégories ou dépenses, pas de frontend)

---

## 1. Problème et acceptation

### 1.1 User Story

En tant qu'utilisateur authentifié, je souhaite **supprimer un budget existant** pour nettoyer mes budgets obsolètes ou mal configurés, sans devoir attendre une migration de données ou contacter l'équipe support.

### 1.2 Acceptation

- [ ] `DELETE /api/budgets/:id` supprime le budget si propriétaire = request.user
- [ ] Retourne 204 No Content en cas de succès (pas de corps de réponse)
- [ ] Retourne 404 Not Found pour un budget inexistant ou appartenant à un autre utilisateur (message générique)
- [ ] La suppression du budget n'affecte jamais les catégories ou les dépenses associées
- [ ] Idempotence : un second DELETE sur le même budget retourne 404 (le budget a été supprimé lors du premier appel)
- [ ] Couvert par un test confirmant que la ligne Budget est supprimée en base et que le budget d'un autre utilisateur reste intacte

---

## 2. Modèle de données

### 2.1 Aucun changement

Le modèle `Budget` (défini en `backend/api/models.py`) n'est pas modifié. Il reste structuré comme suit :

- `user` (FK, CASCADE) — propriétaire du budget
- `category` (FK, PROTECT) — catégorie du budget
- `amount` (Decimal, 2 places, > 0)
- `period_start` (Date)
- `period_end` (Date, >= period_start)
- `alert_threshold` (Decimal, nullable, 0..100 ou null, défaut 80.00)
- `created_at`, `updated_at` (auto)

**Unicité existante :** `UNIQUE(user, category, period_start, period_end)`

### 2.2 Modèles associés — pas de cascade

- **Expenses :** Un Budget n'a pas de référence directe depuis Expense. Une Expense référence une Category ; un Budget référence aussi une Category. **La suppression d'un Budget ne touche jamais les Expenses**, même celles de la même catégorie et période.
- **Categories :** Un Budget référence une Category via FK PROTECT. **La suppression d'un Budget n'affecte jamais les Categories.**

**Raison :** Suppression d'un budget = décision de l'utilisateur de "ne plus tracker ceci", pas de nettoyer les dépenses historiques. Les dépenses et catégories restent disponibles pour consultation ou budgets futurs.

---

## 3. API — Route de suppression

### 3.1 `DELETE /api/budgets/{id}/`

**Authentification :** Requise (SessionAuthentication + IsAuthenticated)

**Description :** Supprimer un budget existant. La suppression est immédiate et définitive. Aucune resource associée (Category, Expense) n'est supprimée.

**Paramètres de chemin :**
- `id` (integer) : Identifiant du budget

**Corps de requête :** Aucun

**Réponse 204 No Content :**
Succès : pas de corps, code 204.

**Erreurs possibles :**

| Code | HTTP | Message | Condition |
|------|------|---------|-----------|
| `UNAUTHORIZED` | 401 | `"error": "UNAUTHORIZED", "message": "Token invalide ou expiré"` | Token absent, expiré ou invalide |
| `NOT_FOUND` | 404 | `"error": "NOT_FOUND", "message": "Budget non trouvé"` | Budget inexistant, ou ownership échoue (appartient à un autre user) |

**Notes de sécurité :**
- Le message 404 est générique (pas de distinction entre "inexistant" et "autre utilisateur") : conformément à `docs/api-design.md` §1.6, cela cache l'existence de budgets d'autres utilisateurs.
- Idempotence : un second appel DELETE sur le même budget retourne 404, car le budget a été supprimé au premier appel.

---

## 4. Décisions de design

### 4.1 Suppression physique vs. soft-delete

**Décision :** Suppression physique (DELETE SQL), pas de soft-delete (colonne `is_active` = false).

**Justification :**
- MVP : simplicité, pas de filtre "actif seulement" sur les listes.
- Compliance RGPD : prise en charge d'un droit à l'oubli ultérieurement.
- Pas de référence active depuis Expense (qui pointerait vers Budget) ; supprimer un Budget n'orpheline rien.

### 4.2 Pas de cascade sur Category ou Expense

**Décision :** La suppression d'un Budget n'affecte jamais une Category ni une Expense, même si elles sont associées par la même période et catégorie.

**Justification :**
- Budget est un "planning tool" ; son cycle de vie est indépendant des données historiques.
- Utilisateur A crée Budget("Alimentation", oct-2026, 500€). Il ajoute Expense("Café", oct-2026, 5€) à la catégorie Alimentation.
- Utilisateur A supprime le Budget en novembre 2026 (obsolète, nouvelle période).
- → La Expense reste, la Category reste. C'est correct : l'historique est préservé, le budget est juste "oublié".

### 4.3 Ownership et confidentialité

**Contrôle :** Avant toute suppression, valider `budget.user_id == request.user.id`.

**Retour en cas d'échec :** 404 NOT_FOUND avec message générique "Budget non trouvé" (pas 403 Forbidden, conformément à `docs/api-design.md` §1.6).

### 4.4 Idempotence et requêtes répétées

**Principe :** Le second DELETE sur un Budget déjà supprimé retourne 404 (pas 204).

**Justification :**
- REST standard : DELETE peut être rappelé, mais le serveur signale « plus rien à supprimer ».
- Différenciation intentionnelle entre "suppression réussie maintenant" (204) et "suppression impossible (n'existe plus)" (404).
- Client peut interpréter 404 après 204 comme "ma demande antérieure a réussi".

---

## 5. Détails d'implémentation (pour Full-Stack Agent)

### 5.1 Vérification de l'ownership

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from api.models import Budget

class BudgetDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, id):
        try:
            budget = Budget.objects.get(id=id, user=request.user)
        except Budget.DoesNotExist:
            return Response(
                {
                    "error": "NOT_FOUND",
                    "message": "Budget non trouvé",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
```

### 5.2 Suppression et réponse 204

```python
        # Suppression réussie
        budget.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
```

### 5.3 Pas de cascade : vérification

Avant implémentation, vérifier que :
- FK de Budget → Category est PROTECT (sinon risque de supprimer des catégories).
- Aucune FK inverse depuis Expense vers Budget n'existe.
- Aucun trigger SQL ne supprime en cascade des données non intentionnelles.

Si le modèle Budget utilise `user = models.ForeignKey(User, on_delete=models.CASCADE)`, c'est correct : si l'utilisateur est supprimé, ses budgets le sont aussi (comportement attendu). Mais une suppression de Budget ne doit pas affecter ses Category ou Expense.

---

## 6. Tests

### 6.1 Cas de succès

**Test :** Suppression d'un budget existant appartenant au requester
- Créer un user A, un budget B appartenant à A
- DELETE /api/budgets/B.id avec session A
- Vérifier : réponse 204, aucun corps
- Vérifier en base : Budget.objects.filter(id=B.id).exists() = False

### 6.2 Idempotence

**Test :** Deuxième suppression du même budget
- Après succès du test 6.1, relancer DELETE /api/budgets/B.id avec session A
- Vérifier : réponse 404 "Budget non trouvé"

### 6.3 Ownership — autre utilisateur

**Test :** Tentative de suppression du budget d'un autre utilisateur
- Créer user A avec budget BA, user B
- DELETE /api/budgets/BA.id avec session B
- Vérifier : réponse 404 "Budget non trouvé"
- Vérifier en base : Budget.objects.filter(id=BA.id).exists() = True (budget non supprimé)

### 6.4 Budget inexistant

**Test :** Suppression d'un ID inexistant
- DELETE /api/budgets/999999 avec session A
- Vérifier : réponse 404 "Budget non trouvé"

### 6.5 Pas d'effet sur les Expenses

**Test :** Les dépenses ne sont pas affectées
- Créer user A, budget BA (cat: Alimentation, période: oct-2026)
- Créer expense EA (cat: Alimentation, date: 2026-10-15)
- DELETE /api/budgets/BA.id avec session A
- Vérifier : réponse 204
- Vérifier en base : Budget.objects.filter(id=BA.id).exists() = False, Expense.objects.filter(id=EA.id).exists() = True

### 6.6 Pas d'effet sur les Categories

**Test :** Les catégories ne sont pas affectées
- Créer user A, budget BA (cat: Alimentation)
- DELETE /api/budgets/BA.id avec session A
- Vérifier : réponse 204
- Vérifier en base : Category.objects.filter(id=Alimentation.id).exists() = True

### 6.7 Pas d'authentification

**Test :** Suppression sans token/session
- DELETE /api/budgets/1 sans session ni Authorization header
- Vérifier : réponse 401 "Token invalide ou expiré"

---

## 7. Périmètre et hors-scope

### 7.1 Inclus

- Endpoint DELETE `/api/budgets/<id>/`
- Tests unitaires et d'intégration pour :
  - Suppression validée, retour 204 (vérification BD)
  - Idempotence : second DELETE → 404
  - Ownership : autre user → 404, ressource préservée
  - Budget inexistant → 404
  - Pas d'authentification → 401
  - Expenses et Categories restent intactes après suppression du budget

### 7.2 Hors-scope

- GET /api/budgets/{id}/ (détail, autre issue si besoin)
- PATCH /api/budgets/{id}/ (modification, issue #48)
- POST /api/budgets/ (création, issue #46)
- GET /api/budgets/ (listing, issue #47)
- Soft-delete ou archivage (hors MVP)
- Frontend SvelteKit (bouton suppression, modal confirmation, etc. — autre issue)
- Suppression en cascade de Categories ou Expenses (jamais)
- Rate limiting (futur, déploiement production)

---

## 8. Questions ouvertes et risques

| Élément | Question | Mitigation |
|---------|----------|-----------|
| **Soft-delete futur** | Si l'app évolue vers soft-delete (is_active), comment gérer les anciens DELETEs ? | Décision : pour MVP, suppression physique. Migration future : ajouter colonne is_active, convertir les données, changer le code. Documenter dans issue dédiée. |
| **Logs d'audit** | Faut-il logger qui a supprimé quel budget et quand ? | Hors MVP. Futur : ajouter table AuditLog avec trigger ou middleware. |
| **Webhooks ou notifications** | Prévenir d'autres systèmes lors de la suppression ? | Hors MVP. Futur : émettre événement (task queue, webhook) si intégrations tierces. |
| **Confirmation côté client** | L'API devrait-elle exiger un token CSRF ou une confirmation multi-étape ? | Non. L'API repose sur l'authentification session/JWT. Le frontend peut afficher une modal de confirmation (UX), pas de validation API. |

---

## 9. Références et conformité

### 9.1 Documents référencés

- `docs/api-design.md` — Contrat API existant (section §4.5 DELETE budgets, §1.5 format erreur, §1.6 ownership)
- `backend/api/models.py` — Modèle Budget, FK vers Category (PROTECT), FK vers User (CASCADE)
- `backend/api/views.py` — Pattern de gestion d'erreur, format de réponse
- `docs/mvp-scope.md` — Scope MVP

### 9.2 Conformité spec

- ✓ Authentification requise (SessionAuthentication + IsAuthenticated)
- ✓ Ownership : 404 générique pour budgets d'autres users
- ✓ Suppression physique, pas de soft-delete (MVP)
- ✓ Pas de cascade sur Category ou Expense
- ✓ Idempotence : second DELETE → 404
- ✓ Réponse 204 No Content en succès (pas de corps)
- ✓ Format d'erreur unifié (docs/api-design.md §1.5)
- ✓ Tests couvrant tous les cas (succès, idempotence, ownership, authentification, absence cascade)
- ✓ Conformité à docs/api-design.md §4.5 pour erreurs (401, 404)

---

*Spécification produite par l'agent Product & Architecture pour issue #49. À valider par l'équipe avant implémentation.*
