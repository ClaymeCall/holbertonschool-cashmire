# Route audit: validation, authorization, error handling (Issue #57)

Scope: every route in `backend/api/urls.py` at commit `38de673`, reviewed by
reading `views.py`, `serializers.py`, `auth.py`, `settings.py` and the test
suite. Static review only.

## Checklist

| Route | Méthodes | Authn | Ownership | Validation | Erreurs | Statut |
|---|---|---|---|---|---|---|
| `/api/health/` | GET | public (voulu) | n/a | n/a | n/a | OK |
| `/api/auth/register/` | POST | public (voulu) | n/a | email unique, validateurs de mot de passe Django | 400 champ par champ | OK, voir G4 |
| `/api/auth/login/` | POST | public (voulu) | n/a | `LoginSerializer` | 401 identique pour email inconnu / mauvais mot de passe, throttle 5/min | OK |
| `/api/auth/me/` | GET | session, 401 | utilisateur courant | n/a | 401 | OK |
| `/api/auth/logout/` | POST | session, 401, CSRF | utilisateur courant | n/a | 401 / 403 CSRF | OK |
| `/api/categories/` | GET | session, 401 anonyme | filtré par `user` | n/a | 401 | OK, voir G1 |
| `/api/expenses/` | GET, POST | session, 401 anonyme | filtré par `user`; catégorie vérifiée par `user` | filtres par serializer, montant `Decimal` en chaîne > 0, date | 400 / 404 | OK, voir G1 |
| `/api/expenses/<id>/` | PATCH, PUT, DELETE | session, 401 anonyme | `get_user_expense_or_404` (404 si autre utilisateur) | idem création | 404 / 400 | OK, voir G1 |
| `/api/budgets/` | GET, POST | session, 401 anonyme | filtré par `user`; catégorie vérifiée par `user` | month/year/category_id parsés, montant > 0, seuil 0..100, `period_end >= period_start`, doublon 409 | 400 / 404 / 409 | OK, voir G1, G5 |
| `/api/budgets/<id>/` | PATCH, DELETE | session, 401 anonyme | `Budget.objects.get(id, user)` (404 sinon) | idem création, revalidation après fusion | 400 / 404 / 409 | OK, voir G1, G5 |
| `/api/schema/`, `/api/docs/` | GET | public | n/a | n/a | n/a | voir G2 |

## Critère « aucune route ne renvoie de stack trace »

- `sanitized_exception_handler` (`backend/api/exceptions.py`, issue #62) renvoie
  un 500 générique pour toute exception non gérée; la trace va dans les logs.
- `DJANGO_DEBUG` vaut `false` par défaut (`settings.py`), donc les pages
  d'erreur HTML de Django n'exposent plus de configuration hors dev.
- Couvert par `api.tests.test_errors`.
- Aucun SQL brut dans `backend/` (issue #61).

## Écarts relevés (G1 corrigé, les autres restent à suivre)

| # | Écart | Gravité | Proposition |
|---|---|---|---|
| G1 | **Corrigé** (PR `fix/57-anonymous-401`): `categories`, `expenses` et `budgets` utilisent maintenant `SessionCookieAuthentication` et renvoient **401** à un anonyme, comme `auth/me` et `auth/logout`. Tests et `docs/api-design.md` mis à jour. | Moyenne | Fait. |
| G2 | `/api/schema/` et `/api/docs/` sont publics (permissions par défaut de drf-spectacular). Aucune donnée utilisateur, mais le contrat complet de l'API est exposé. | Faible | Accepter pour la démo ou restreindre hors `DEBUG`. |
| G3 | `DJANGO_ALLOWED_HOSTS` vaut `*` et `DJANGO_SECRET_KEY` a une valeur par défaut connue. | Faible (MVP) | Documenter comme limite connue (#74). |
| G4 | Pas de throttle sur `register`; le message « email already exists » permet de tester l'existence d'un email. | Faible | Accepter pour le MVP et documenter, comme pour le login (décision 0004). |
| G5 | Format d'erreur incohérent: les budgets renvoient `serializer.errors` brut pour un 400 de serializer, mais `{error, message}` pour les autres 400 / 404 / 409. | Faible | Uniformiser plus tard avec le contrat `docs/api-design.md`. |

## Vérification

- Revue de code uniquement; aucun code applicatif modifié.
