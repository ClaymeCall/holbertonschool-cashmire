# Revue QA — Spécification API Cashmire (Issue #7)

- **Date :** 2026-10-06
- **Réviseur :** Agent QA & Security
- **Spec audité :** `docs/specs/issue-7-api-contract.md`
- **Document comparé :** `docs/api-design.md`
- **Références externes :** `docs/erd.md`, `docs/decisions/category-ownership.md`, `backend/cashmire/urls.py`, `backend/api/urls.py`
- **Scope :** Conformité de la spécification par rapport aux critères d'acceptation, cohérence interne, sécurité, et alignement ERD.

---

## Résumé exécutif

La spécification `docs/api-design.md` est en **conformité générale** avec `docs/specs/issue-7-api-contract.md` et constitue un contrat API cohérent et sécurisé. **Pas de blocants critiques détectés.** Trois non-blocants mineures relevés, un cas de test recommandé, et une clarification proposée sur le détail dans les erreurs 400.

---

## Bloquants

### Aucun finding bloquant détecté.

---

## Non-blocants

### NB-1 : Imprécision sur les messages d'erreur 400 — Granularité des details

**Sévérité :** Non-bloquant | Clarification nécessaire.

**Constat :**

Dans `docs/api-design.md`, les exemples d'erreurs 400 listent parfois des messages au **niveau du champ individuel** (ex. `"email": "Adresse e-mail invalide"` en section 2.1, registre), suggérant une réponse JSON structurée par champ (style Django REST Framework avec `field_errors` imbriqués ou liste plate).

Cependant, la section 1.5 « Format des erreurs » et l'AC-12 (spécification #7) stipulent un **format uniforme global** :
```json
{
  "error": "<code_erreur>",
  "message": "<description lisible>"
}
```

**Tension :**
- Section 2.1 (register) montre : `"400 Bad Request — Validation échouée"` + exemples : `"email": "..."`, `"password": "..."` (détail par champ).
- Section 1.5 montre : format global uniforme `{ "error": "INVALID_DATA", "message": "..." }`.

**Recommandation :**

Clarifier dans la spec laquelle des deux approches est choisie :

**Option A (recommandée pour MVP et cohérence)** : Format global unique, messages génériques non granulaires.
```json
{
  "error": "INVALID_DATA",
  "message": "Validation échouée. Vérifiez email, username et password."
}
```

**Option B (DRF standard)** : Format imbriqué par champ (plus détaillé pour frontend).
```json
{
  "error": "INVALID_DATA",
  "message": "Validation échouée",
  "details": {
    "email": ["Adresse e-mail invalide"],
    "password": ["Minimum 8 caractères"]
  }
}
```

**Action pour l'équipe :** Choisir l'option et mettre à jour la spec de manière cohérente dans tous les exemples.

---

### NB-2 : Absence de test explicite pour l'ownership avec `category_id` étranger

**Sévérité :** Non-bloquant | Couverture de test recommandée.

**Constat :**

Spec AC-5 : « Ownership et 404 : Pour toute route manipulant expenses, budgets ou catégories... »

La spec `docs/api-design.md` (section 3.2, POST /api/expenses/) énonce :
> `404 Not Found` — Category n'existe pas ou appartient à un autre utilisateur. Message : `"error": "NOT_FOUND", "message": "Catégorie non trouvée"`

Ceci est correct et couvre le scénario « `category_id` étranger ». Cependant, **aucun test n'existe encore** (backend pas implémenté).

**Recommandation pour l'équipe développement :**

Lors de l'implémentation (issue future), ajouter **au minimum deux cas de test** pour chaque POST/PATCH Expense et Budget :
1. Catégorie de l'utilisateur courant → succès (201 ou 200).
2. Catégorie d'un autre utilisateur → 404 (pas de distinction entre « n'existe pas » et « pas d'accès »).
3. Catégorie inexistante (id très haut) → 404.

---

### NB-3 : Incohérence mineur — `is_active` sur User absent de la réponse POST register

**Sévérité :** Non-bloquant | Cohérence cosmétique.

**Constat :**

Réponse 201 Created de `POST /api/auth/register/` (section 2.1) :
```json
{
  "id": 1,
  "email": "alice@example.com",
  "username": "alice_wonderland",
  "first_name": "Alice",
  "last_name": "Wonderland",
  "created_at": "2026-10-06T14:30:45Z"
}
```

Réponse 200 OK de `GET /api/auth/me/` (section 2.4) :
```json
{
  "id": 1,
  "email": "alice@example.com",
  "username": "alice_wonderland",
  "first_name": "Alice",
  "last_name": "Wonderland",
  "is_active": true,
  "created_at": "2026-10-06T14:30:45Z",
  "updated_at": "2026-10-06T14:30:45Z"
}
```

**Observation :**

POST register n'inclut **pas** `is_active` ni `updated_at` (qui est créé à l'insertion). GET me les inclut. Selon l'ERD, `is_active` est un champ de User, donc logiquement présent dès la création.

**Recommandation :**

Soit :
1. **Ajouter `is_active` et `updated_at` à la réponse 201 register** (cohérence totale avec GET me).
2. Ou documenter que POST register retourne une version allégée pour clarifier.

**Choix recommandé :** Option 1 (cohérence maximale).

---

## Vérifications spécifiques

### ✓ AC-1 : Document en français

**Statut :** Conforme.

`docs/api-design.md` est entièrement rédigé en français, avec exemples JSON, codes d'erreur en anglais (standard REST).

---

### ✓ AC-2 : Vue d'ensemble avec conventions

**Statut :** Conforme.

Section 1 couvre :
- 1.1 Base URL et schéma (`/api/`)
- 1.2 Authentification (JWT/session, header, 401)
- 1.3 Sérialisation montants (chaînes JSON)
- 1.4 Timestamps (ISO 8601 UTC)
- 1.5 Format d'erreur (uniforme)
- 1.6 Ownership (404 intentionnel)
- 1.7 Pagination (MVP : aucune)
- 1.8 Codes HTTP et méthodes

---

### ✓ AC-3 : Chaque route documentée

**Statut :** Conforme.

**Compte :**
- Section 2 (Auth) : 4 routes (register, login, logout, me).
- Section 3 (Expenses) : 5 routes (GET list, POST, GET detail, PATCH, DELETE).
- Section 4 (Budgets) : 5 routes (GET list, POST, GET detail, PATCH, DELETE).
- Section 5 (Categories) : 5 routes (GET list, POST, GET detail, PATCH, DELETE).

**Total : 19 routes.**

Chaque route inclut :
- Authentification (requise/non requise) ✓
- Description ✓
- Champs de requête/query params ✓
- Réponse 200/201 ✓
- Codes d'erreur possibles ✓
- Messages d'erreur ✓

---

### ✓ AC-4 : Montants en chaînes JSON

**Statut :** Conforme.

Section 1.3 énonce clairement :
> « Tous les champs monétaires sont sérialisés en chaînes JSON, jamais en nombres flottants. »

Exemples trouvés :
- Section 3.1 : `"amount": "25.50"` (expense list)
- Section 4.1 : `"amount": "500.00"`, `"spent": "234.50"`, `"remaining": "265.50"` (budgets)
- Section 5.2 : `"amount": "80.00"` (alert_threshold dans POST categories)

Tous les montants visibles sont des chaînes. ✓

---

### ✓ AC-5 : Ownership et 404

**Statut :** Conforme.

Section 1.6 énonce :
> « Si l'utilisateur B tente d'accéder à une ressource de l'utilisateur A : retourner **404 Not Found** (pas 403). »

Chaque route concernée documente 404 comme réponse d'erreur pour ownership :
- 3.3 GET /api/expenses/{id}/ : `404 Not Found` — « n'existe pas ou appartient à un autre utilisateur »
- 3.2 POST /api/expenses/ : `404 Not Found` — « category_id n'existe pas ou appartient à un autre utilisateur »
- 4.3 GET /api/budgets/{id}/ : `404 Not Found` — « n'existe pas ou appartient à un autre utilisateur »
- 5.3 GET /api/categories/{id}/ : `404 Not Found` — « n'existe pas ou appartient à un autre utilisateur »

✓

---

### ✓ AC-6 : Tous les chemins avec slash final

**Statut :** Conforme.

Vérification systématique de tous les chemins listés :

**Routes d'authentification :**
- `POST /api/auth/register/` ✓
- `POST /api/auth/login/` ✓
- `POST /api/auth/logout/` ✓
- `GET /api/auth/me/` ✓

**Routes Expenses :**
- `GET /api/expenses/` ✓
- `POST /api/expenses/` ✓
- `GET /api/expenses/{id}/` ✓
- `PATCH /api/expenses/{id}/` ✓
- `DELETE /api/expenses/{id}/` ✓

**Routes Budgets :**
- `GET /api/budgets/` ✓
- `POST /api/budgets/` ✓
- `GET /api/budgets/{id}/` ✓
- `PATCH /api/budgets/{id}/` ✓
- `DELETE /api/budgets/{id}/` ✓

**Routes Categories :**
- `GET /api/categories/` ✓
- `POST /api/categories/` ✓
- `GET /api/categories/{id}/` ✓
- `PATCH /api/categories/{id}/` ✓
- `DELETE /api/categories/{id}/` ✓

**Remarque :** Route d'intro `/api/health/` confirmée dans `backend/api/urls.py` sans slash final (`path("health/", ...)`), ce qui génère une route `/api/health/` avec slash par défaut dans Django. Conforme. ✓

---

### ✓ AC-7 : Authentification documentée

**Statut :** Conforme.

Section 1.2 :
- Mécanisme : Token JWT ou session Django ✓
- Fourniture : Header `Authorization: Bearer <token>` ou cookie ✓
- Routes non authentifiées : register, login, health ✓
- Routes authentifiées : toutes les autres ✓
- Réponse 401 Unauthorized si absent/invalide ✓

---

### ✓ AC-8 : Routes authentification

**Statut :** Conforme.

Toutes les quatre routes d'authentification documentées :
- `POST /api/auth/register/` (section 2.1) ✓
- `POST /api/auth/login/` (section 2.2) ✓
- `POST /api/auth/logout/` (section 2.3) ✓
- `GET /api/auth/me/` (section 2.4) ✓

---

### ✓ AC-9 : Routes CRUD Expenses

**Statut :** Conforme.

Toutes les cinq routes CRUD documentées (section 3) :
- `GET /api/expenses/` (3.1) ✓
- `POST /api/expenses/` (3.2) ✓
- `GET /api/expenses/{id}/` (3.3) ✓
- `PATCH /api/expenses/{id}/` (3.4) ✓
- `DELETE /api/expenses/{id}/` (3.5) ✓

---

### ✓ AC-10 : Routes CRUD Budgets avec spent/remaining

**Statut :** Conforme.

Toutes les cinq routes CRUD documentées (section 4) :
- `GET /api/budgets/` (4.1) avec `spent` et `remaining` ✓
- `POST /api/budgets/` (4.2) avec `spent` et `remaining` en réponse ✓
- `GET /api/budgets/{id}/` (4.3) avec `spent` et `remaining` ✓
- `PATCH /api/budgets/{id}/` (4.4) avec `spent` et `remaining` ✓
- `DELETE /api/budgets/{id}/` (4.5) ✓

Section 4.1 : « `spent` (string) : Somme des expenses pour cette catégorie dans la période [period_start, period_end]. Calculé dynamiquement. »

---

### ✓ AC-11 : Routes CRUD Categories

**Statut :** Conforme.

Toutes les cinq routes CRUD documentées (section 5) :
- `GET /api/categories/` (5.1) ✓
- `POST /api/categories/` (5.2) ✓
- `GET /api/categories/{id}/` (5.3) ✓
- `PATCH /api/categories/{id}/` (5.4) ✓
- `DELETE /api/categories/{id}/` (5.5) ✓

---

### ✓ AC-12 : Format d'erreur uniforme

**Statut :** Conforme (avec clarification recommandée, voir NB-1).

Section 1.5 énonce :
```json
{
  "error": "<code_erreur>",
  "message": "<description lisible>"
}
```

Codes standardisés :
- `INVALID_DATA` (400)
- `NOT_FOUND` (404)
- `UNAUTHORIZED` (401)
- `CONFLICT` (409)
- `SERVER_ERROR` (500)

Utilisés de manière cohérente dans tous les exemples. ✓

---

### ✓ AC-13 : Pas de détails internes

**Statut :** Conforme.

Messages d'erreur vérifiés pour absence de :
- Stacktraces : Aucune trouvée. ✓
- Noms de colonnes SQL : Aucun trouvé. ✓
- Chemins de fichiers : Aucun trouvé. ✓
- Numéros de ligne : Aucun trouvé. ✓

Exemples de messages génériques :
- `"Ressource non trouvée"` ✓
- `"Données invalides"` ✓
- `"Identifiants invalides"` (login, pas énumération) ✓
- `"Token invalide ou expiré"` ✓

---

### ✓ AC-14 : Champs POST/PATCH documentés

**Statut :** Conforme.

Chaque route POST/PATCH énonce ses champs avec type et obligation :

**Exemple POST /api/expenses/ (section 3.2) :**
```json
{
  "category_id": 5,
  "amount": "25.50",
  "description": "...",
  "date": "2026-10-06"
}
```
Avec section « Champs de requête » listant obligations et types. ✓

Similaire pour POST budgets, categories, PATCH expenses, etc.

---

### ✓ AC-15 : Pagination documentée

**Statut :** Conforme.

Section 1.7 énonce :
> « MVP : Pas de pagination. Toutes les listes retournent l'ensemble complet des enregistrements de l'utilisateur courant. »

Chaque route GET list (3.1, 4.1, 5.1) indique :
> « MVP sans pagination. Retourne toutes les dépenses/budgets/catégories de l'utilisateur courant. »

---

### ✓ AC-16 : Contraintes de validation documentées

**Statut :** Conforme.

Exemples :

**POST /api/expenses/ (section 3.2) :**
- `amount` doit être > 0 ✓
- `category_id` doit appartenir à l'utilisateur courant ✓
- `date` doit être valide (YYYY-MM-DD) ✓

**POST /api/budgets/ (section 4.2) :**
- `amount` > 0 ✓
- `period_end` >= `period_start` ✓
- `alert_threshold` 0–100 ✓
- Unicité `(user, category, period_start, period_end)` ✓

**POST /api/categories/ (section 5.2) :**
- `name` ne doit pas être vide ✓
- Unicité `(user, name)` ✓

---

### ✓ AC-17 : Timestamps ISO 8601

**Statut :** Conforme.

Section 1.4 énonce :
> « Tous les timestamps (`created_at`, `updated_at`) sont sérialisés en **format ISO 8601 / RFC 3339** (ex. `"2026-10-06T14:30:45Z"`). Fuseau horaire : UTC (suffix Z). »

Tous les exemples utilisent ce format :
- `"2026-10-06T14:30:45Z"` ✓
- `"2026-10-01T10:00:00Z"` ✓

---

### ✓ AC-18 : POST retourne 201 Created

**Statut :** Conforme.

Vérification de toutes les routes POST :
- `POST /api/auth/register/` → 201 Created ✓
- `POST /api/expenses/` → 201 Created ✓
- `POST /api/budgets/` → 201 Created ✓
- `POST /api/categories/` → 201 Created ✓

---

### ✓ AC-19 : PATCH retourne 200 OK

**Statut :** Conforme.

Vérification de toutes les routes PATCH :
- `PATCH /api/expenses/{id}/` → 200 OK ✓
- `PATCH /api/budgets/{id}/` → 200 OK ✓
- `PATCH /api/categories/{id}/` → 200 OK ✓

---

### ✓ AC-20 : DELETE retourne 204 No Content

**Statut :** Conforme.

Vérification de toutes les routes DELETE :
- `DELETE /api/expenses/{id}/` → 204 No Content ✓
- `DELETE /api/budgets/{id}/` → 204 No Content ✓
- `DELETE /api/categories/{id}/` → 204 No Content ✓

Section 3.5, 4.5, 5.5 énoncent tous « Pas de corps. Code 204. »

---

## Cohérence ERD

### ✓ Champs User

**Spécification :** `docs/erd.md` USER table
**Vérification :** Champs exposés via API.

Champs de User attendus selon ERD :
- `id` : ✓ (dans /api/auth/me/)
- `email` : ✓ (register, login, me)
- `username` : ✓ (register, login, me)
- `first_name` : ✓ (register, login, me)
- `last_name` : ✓ (register, login, me)
- `is_active` : ✓ (dans /api/auth/me/, absent de register — voir NB-3)
- `created_at` : ✓ (register, me)
- `updated_at` : ✓ (dans me, absent de register)

Aucun champ secret (password) exposé. ✓

---

### ✓ Champs Category

**Spécification :** `docs/erd.md` CATEGORY table, décision `docs/decisions/category-ownership.md`
**Vérification :** Champs exposés et ownership.

Champs attendus selon ERD :
- `id` : ✓ (dans /api/categories/)
- `user_id` : ✓ (inclus dans les réponses)
- `name` : ✓ (POST, réponse, validation UNIQUE(user_id, name))
- `description` : ✓ (optionnel, dans réponses et POST)
- `is_active` : ✓ (true par défaut à création, modifiable via PATCH)
- `created_at` : ✓
- `updated_at` : ✓

**Ownership par utilisateur :** Confirmé dans spec AC-5, section 1.6, et section 5. Chaque catégorie appartient à un utilisateur (scope user_id). ✓

---

### ✓ Champs Expense

**Spécification :** `docs/erd.md` EXPENSE table
**Vérification :** Champs exposés et contraintes.

Champs attendus selon ERD :
- `id` : ✓
- `user_id` : ✓ (inclus en réponses)
- `category_id` : ✓ (requis, validé à l'API : doit appartenir à user)
- `amount` : ✓ (chaîne JSON, > 0)
- `description` : ✓ (optionnel)
- `date` : ✓ (DATE YYYY-MM-DD, peut être rétroactif)
- `created_at` : ✓
- `updated_at` : ✓

**Contrainte de validation :** `category.user_id == expense.user_id` — énoncée implicitement dans AC-5 (ownership) et documentée dans section 3.2 (POST /api/expenses/ → 404 si category appartient à un autre utilisateur). ✓

---

### ✓ Champs Budget

**Spécification :** `docs/erd.md` BUDGET table
**Vérification :** Champs exposés, contraintes, calculs.

Champs attendus selon ERD :
- `id` : ✓
- `user_id` : ✓
- `category_id` : ✓ (ownership : doit appartenir à user)
- `amount` : ✓ (chaîne JSON, > 0)
- `period_start` : ✓ (DATE)
- `period_end` : ✓ (DATE, >= period_start)
- `alert_threshold` : ✓ (chaîne JSON, 0–100, optionnel default 80.00)
- `created_at` : ✓
- `updated_at` : ✓

**Champs calculés (non en DB) :**
- `spent` : ✓ (somme des expenses pour category dans période [period_start, period_end])
- `remaining` : ✓ (`amount - spent`)

Section 4.1 énonce : « `spent` (string) : Somme des expenses pour cette catégorie dans la période... Calculé dynamiquement. »

---

## Sécurité

### ✓ Authentification

- Routes publiques restreintes à register, login, health. ✓
- 401 Unauthorized documenté pour token absent/invalide. ✓
- Token en header `Authorization: Bearer` ou cookie. ✓

---

### ✓ Ownership

- 404 intentionnel pour ressources d'autres utilisateurs (not 403). ✓
- Appliqué à expenses, budgets, categories. ✓
- Validation documentée pour category_id (doit appartenir à user). ✓

---

### ✓ Input validation

- `amount > 0` documenté. ✓
- Dates format YYYY-MM-DD. ✓
- `period_end >= period_start` pour budgets. ✓
- `alert_threshold` 0–100. ✓
- Unicités : email, username, (user_id, category_name), (user_id, category_id, period_start, period_end). ✓

---

### ✓ Erreurs

- Pas de stacktraces. ✓
- Pas de détails SQL. ✓
- Messages génériques (« Identifiants invalides » pour login, pas énumération email vs. password). ✓

---

## Remarques supplémentaires

### Routes de base réelles vs. spec

Backend actuel (`backend/api/urls.py`) :
```python
urlpatterns = [
    path("health/", views.health, name="health"),
]
```

Spec API design :
```
GET /api/health/  — Health check sans auth
```

La spec mentionne `/api/health/` (section 2.2, note), conforme à la route implémentée. ✓

Aucune autre route n'existe encore (register, login, expenses, budgets, categories) — ceci est attendu : il s'agit d'une spec de contrat, pas d'une implémentation.

---

## Résumé par catégorie

| Catégorie | Statut | Détail |
|-----------|--------|--------|
| **Structure générale** | ✓ | 19 routes documentées, format uniforme |
| **Authentification** | ✓ | 4 routes, 401 documenté, ownership 404 clair |
| **Expenses CRUD** | ✓ | 5 routes, montants en chaînes, contraintes énoncées |
| **Budgets CRUD** | ✓ | 5 routes, spent/remaining calculés, contraintes composées OK |
| **Categories CRUD** | ✓ | 5 routes, ownership par user, UNIQUE(user_id, name) |
| **Codes HTTP** | ✓ | 201 POST, 200 PATCH, 204 DELETE, 400/401/404/409/500 |
| **Montants JSON** | ✓ | Chaînes partout (amount, spent, remaining, alert_threshold) |
| **Timestamps** | ✓ | ISO 8601 UTC dans tous les exemples |
| **Erreurs** | ⚠️ NB-1 | Format cohérent, mais clarifier granularité des messages 400 |
| **Ownership/404** | ✓ | Intentionnel, documenté, appliqué partout |
| **Slash final** | ✓ | Tous les chemins se terminent par `/` |
| **ERD cohérence** | ✓ | Champs alignés, contraintes énoncées |
| **Sécurité** | ✓ | Pas d'énumération, pas de détails internes |

---

## Recommandations pour l'implémentation

### Avant de commencer

1. **Clarifier le format d'erreur 400** (NB-1) : Format global unique ou détails par champ ?
2. **Ajouter `is_active` et `updated_at` à POST register** (NB-3) pour cohérence avec GET me.
3. **Préparer des tests d'ownership** pour category_id étranger, expense/budget d'autre user.

### Lors du développement

- Respecter strictement les codes HTTP (201/200/204) et messages d'erreur.
- Valider `category.user_id == request.user.id` avant chaque opération.
- Sérialiser montants en Decimal → chaîne JSON (Django DRF `DecimalField(as_string=True)`).
- Mettre à jour timestamps générés par `auto_now`/`auto_now_add`.
- Tester les cas d'erreur 404 pour ownership (pas 403).

---

*Revue complétée le 2026-10-06. Document source de vérité : `docs/api-design.md`. Spécification de référence : `docs/specs/issue-7-api-contract.md`.*
