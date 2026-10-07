# Revue de sécurité — Propriété des dépenses (Issue #39)

- **Date :** 2026-10-07
- **Réviseur :** Revue assistée par Copilot
- **Scope :** Routes d'API dépenses effectivement implémentées et leurs
  accès aux dépenses et catégories.
- **Contrôle :** Une dépense ne peut être lue ou modifiée que par son
  propriétaire authentifié. Une ressource étrangère et une ressource absente
  produisent la même réponse 404.

## Résultat

**Conforme — aucun défaut d'isolation propriétaire identifié dans les routes
examinées.**

| Méthode et route | Contrôle revu | Test de régression |
|---|---|---|
| `GET /api/expenses/` | La queryset est filtrée par `user=request.user` avant les filtres facultatifs. | `ExpenseListTests.test_list_returns_only_the_authenticated_users_expenses` |
| `POST /api/expenses/` | La dépense reçoit `request.user` côté serveur; la catégorie doit appartenir à ce même utilisateur. `user_id` fourni par le client n'est pas utilisé. | `ExpenseCreateTests.test_authenticated_user_creates_expense_owned_by_the_session_user`; `ExpenseCreateTests.test_missing_or_foreign_category_returns_the_same_not_found_error` |
| `PATCH /api/expenses/<id>/` | La dépense est récupérée par `pk` et propriétaire dans la requête ORM; la nouvelle catégorie est également vérifiée contre le propriétaire courant. | `ExpenseDetailMutationTests.test_update_returns_identical_404_for_foreign_and_missing_expenses`; `ExpenseDetailMutationTests.test_update_rejects_a_foreign_or_missing_category` |
| `PUT /api/expenses/<id>/` | Utilise la même récupération ORM propriétaire-scopée que `PATCH`. | `ExpenseDetailMutationTests.test_update_returns_identical_404_for_foreign_and_missing_expenses` |
| `DELETE /api/expenses/<id>/` | Utilise la même récupération ORM propriétaire-scopée avant suppression. | `ExpenseDetailMutationTests.test_delete_returns_identical_404_for_foreign_and_missing_expenses` |

## Preuves dans le code

- `backend/api/views.py` — `expenses` borne la liste à l'utilisateur
  authentifié; `ExpenseCreateSerializer.create` attribue `request.user`;
  `get_user_expense_or_404` filtre simultanément par identifiant et
  propriétaire.
- `backend/api/views.py` — les sérialiseurs de création et de mise à jour
  vérifient que la catégorie appartient à `request.user`.
- `backend/api/urls.py` — toutes les méthodes de mutation détaillées passent
  par la vue protégée `expense_detail_mutation`.

Les réponses aux identifiants étrangers sont volontairement identiques à
celles des identifiants inexistants afin de ne pas révéler l'existence d'une
dépense appartenant à un autre compte.
