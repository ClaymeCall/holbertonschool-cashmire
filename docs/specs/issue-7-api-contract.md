# SPÉCIFICATION — Contrat API REST initial (Cashmire)

- **Issue :** #7 « Concevoir le contrat initial des routes REST »
- **Statut :** Proposition. Non approuvée. Un humain doit lire cette spec avant la mise en œuvre.
- **Auteur :** Agent Product & Architecture
- **Portée :** Contrat API REST documenté dans `docs/api-design.md`. Aucun code applicatif, aucune migration.
- **Codebase examiné à :** branche `docs/7-api-contract`, commit actuel

---

## 0. Note introductive

Cette spécification définit le **contrat API REST initial** pour Cashmire. Le livrable final est un document de référence `docs/api-design.md` en français, listant toutes les routes publiques du MVP, leurs signatures (méthode, chemin, authentification, requête, réponse) et les cas d'erreur possibles.

Le contrat couvre :
- **Authentification** : register, login, logout, utilisateur courant
- **CRUD Expenses** : listing, création, détail, modification, suppression
- **CRUD Budgets** : listing (avec consommation), création, détail, modification, suppression
- **Listing et gestion des Catégories** : listing, création, détail, modification, suppression

Toutes les routes qui manipulent des ressources utilisateur (expenses, budgets, catégories) appliquent l'**ownership** : une ressource d'un autre utilisateur retourne `404 Not Found` (pas de distinction entre « n'existe pas » et « pas d'accès »).

---

## 1. Énoncé du problème et critères d'acceptation

### 1.1 Récit utilisateur

> Cashmire doit exposer un contrat API REST initial qui permette aux clients frontend (SvelteKit) et aux développeurs externes de comprendre précisément comment :
> - S'authentifier (register, login, logout) et récupérer les données de l'utilisateur courant
> - Créer, lister, détailler, modifier et supprimer des dépenses (expenses)
> - Créer, lister, détailler, modifier et supprimer des budgets, avec inclusion des données de consommation en time real
> - Lister, créer, détailler, modifier et supprimer des catégories
> 
> Chaque route doit clarifier son exigence d'authentification, sa structure de requête, sa structure de réponse et ses cas d'erreur possibles (validation, ressource non trouvée, unauthorized, forbidden). Le contrat doit être un document vivant en français, cohérent et exploitable sans code applicatif.

### 1.2 Critères d'acceptation (testables)

| ID | Critère | Vérification |
|----|---------|-------------|
| AC-1 | Un document `docs/api-design.md` existe et est écrit en français. | Lecture du fichier. |
| AC-2 | Le document contient une section « Vue d'ensemble » décrivant les conventions générales : base URL, authentification, sérialisation des montants, gestion des erreurs, timestamps. | Présence de la section. |
| AC-3 | Chaque route est documentée sous une section dédiée ou un tableau avec : méthode HTTP, chemin (avec slash final), exigence d'authentification (required/optional/none), corps de requête (le cas échéant), structure de réponse HTTP 200/201 (les cas heureux), et liste exhaustive des codes d'erreur possibles (400, 401, 403, 404, 409, 500) avec un bref message. | Vérification manuelle de la structure de chaque route. |
| AC-4 | Tous les champs monétaires (`amount`, montants de budgets, consommation) sont sérialisés en **chaînes de caractères JSON** (ex. `"amount": "123.45"`), jamais en nombres flottants JSON. Cela est documenté dans la section « Vue d'ensemble ». | Recherche du mot « chaîne » ou « string » dans la description des montants. |
| AC-5 | **Ownership et 404 :** Pour toute route manipulant expenses, budgets ou catégories, le document énonce clairement que les ressources d'un autre utilisateur retournent `404 Not Found` (cohérent avec l'ERD qui établit `user_id` comme propriétaire). | Énoncé explicite « 404 si ressource appartient à un autre utilisateur » dans les routes concernées. |
| AC-6 | Tous les chemins de route incluent un **slash final** (ex. `GET /api/expenses/`, `POST /api/categories/`, etc.), conformément à la convention Django existante (`GET /health/`). | Vérification de chaque path : doit se terminer par `/`. |
| AC-7 | La section « Vue d'ensemble » ou « Authentification » documente le format du token JWT/session, la façon de l'inclure dans les requêtes (header Authorization), et la réponse `401 Unauthorized` si absent ou invalide. | Présence de la documentation d'authentification. |
| AC-8 | Les routes d'authentification sont documentées : `POST /api/auth/register/`, `POST /api/auth/login/`, `POST /api/auth/logout/`, `GET /api/auth/me/`. | Présence des quatre routes. |
| AC-9 | Les routes CRUD expenses sont documentées : `GET /api/expenses/`, `POST /api/expenses/`, `GET /api/expenses/{id}/`, `PATCH /api/expenses/{id}/`, `DELETE /api/expenses/{id}/`. | Présence des cinq routes. |
| AC-10 | Les routes CRUD budgets sont documentées avec inclusion de données de consommation (somme des expenses dans la période et catégorie) : `GET /api/budgets/`, `POST /api/budgets/`, `GET /api/budgets/{id}/`, `PATCH /api/budgets/{id}/`, `DELETE /api/budgets/{id}/`. | Présence des cinq routes avec champs `spent` ou similaire. |
| AC-11 | Les routes pour catégories sont documentées : `GET /api/categories/`, `POST /api/categories/`, `GET /api/categories/{id}/`, `PATCH /api/categories/{id}/`, `DELETE /api/categories/{id}/`. | Présence des cinq routes. |
| AC-12 | Le format d'erreur est cohérent sur toutes les routes (ex. `{ "error": "message", "code": "code_erreur" }` ou `{ "detail": "message" }`). Il est explicité dans la section « Vue d'ensemble ». | Présence d'une spécification du format d'erreur unique. |
| AC-13 | Aucun détail interne n'est divulgué dans les messages d'erreur (ex. pas de stacktrace, pas de noms de colonnes SQL, pas de chemin fichier). Les erreurs utilisent des messages génériques (ex. « Ressource non trouvée », « Données invalides »). | Vérification que les exemples d'erreur ne contiennent pas de détails techniques. |
| AC-14 | La documentation explique les champs attendus pour chaque requête POST/PATCH (ex. `name`, `amount`, `date`, `category_id` pour une dépense). | Vérification que les corps de requête sont spécifiés. |
| AC-15 | Les réponses de liste (GET sans `{id}`) documentent la pagination (ou l'absence de pagination dans le MVP). | Présence d'une clause sur la pagination. |
| AC-16 | Le document énonce les **contraintes de validation** applicables à chaque route (ex. `amount > 0`, `period_end >= period_start` pour budgets, `UNIQUE(user_id, name)` pour catégories). | Présence de contraintes en réponse ou dans une note. |
| AC-17 | Les timestamps (`created_at`, `updated_at`) sont sérialisés en format ISO 8601 (ex. `"2026-10-06T14:30:00Z"`). Cela est documenté. | Mention du format ISO 8601 ou RFC 3339. |
| AC-18 | Chaque route qui crée une ressource (POST) retourne un code `201 Created` avec la ressource créée en corps. | Vérification que les POST retournent 201. |
| AC-19 | Chaque route qui modifie une ressource (PATCH) retourne un code `200 OK` avec la ressource modifiée. | Vérification que les PATCH retournent 200. |
| AC-20 | Chaque route qui supprime une ressource (DELETE) retourne un code `204 No Content` (pas de corps). | Vérification que les DELETE retournent 204. |

---

## 2. Vue d'ensemble des conventions API

### 2.1 Base URL et versioning

Toutes les routes sont préfixées par `/api/`.

Pas de versioning initial (v1, v2, etc.). Si besoin futur, ajouter `/api/v1/` etc.

Exemple : `POST /api/auth/login/`

### 2.2 Authentification

**Mécanisme :** Token JWT (JSON Web Token) ou session Django.

**Fourniture du token :**
- En header : `Authorization: Bearer <token>`
- Ou en cookie (si session Django)

**Routes non authentifiées :**
- `POST /api/auth/register/` — création de compte sans auth
- `POST /api/auth/login/` — login sans auth
- `GET /api/health/` — health check sans auth

**Routes authentifiées :**
- Toutes les autres (expenses, budgets, catégories, logout, me)

**Réponse 401 Unauthorized :**
Retournée si le token est absent, expiré ou invalide.

### 2.3 Sérialisation des montants (Decimal)

**Tous les champs monétaires sont sérialisés en chaînes JSON**, jamais en nombres flottants.

Exemples :
```json
{
  "amount": "123.45",
  "budget_amount": "500.00",
  "spent": "234.50"
}
```

**Raison :** Éviter les erreurs d'arrondi IEEE 754 (ex. 0.1 + 0.2 ≠ 0.3 en float).

### 2.4 Timestamps

Tous les timestamps (`created_at`, `updated_at`) sont sérialisés en **format ISO 8601 / RFC 3339** (ex. `"2026-10-06T14:30:45Z"`).

Fuseau horaire : UTC (Z suffix).

### 2.5 Format des erreurs

Réponse d'erreur uniforme (application/json) :

```json
{
  "error": "<code_erreur>",
  "message": "<description lisible>"
}
```

**Codes d'erreur courants :**
- `INVALID_DATA` — Validation échouée (400 Bad Request)
- `NOT_FOUND` — Ressource non trouvée (404 Not Found)
- `UNAUTHORIZED` — Token absent/invalide (401 Unauthorized)
- `FORBIDDEN` — Accès refusé (403 Forbidden, ex. tentative d'accéder à une ressource d'un autre utilisateur — retourne plutôt 404)
- `CONFLICT` — Conflit (ex. unicité violée, 409 Conflict)
- `SERVER_ERROR` — Erreur serveur (500 Internal Server Error)

**Confidentialité :** Les messages d'erreur ne révèlent pas de détails internes (stacktraces, noms SQL, chemins fichiers).

### 2.6 Ownership et contrôles d'accès

Ressources scoped par utilisateur : `Expense`, `Budget`, `Category`.

**Principe :** Une ressource créée par l'utilisateur A ne peut être lue, modifiée ou supprimée que par l'utilisateur A.

**Implémentation :** 
- API valide `resource.user_id == request.user.id` avant chaque opération.
- Si l'utilisateur B tente d'accéder à une ressource de l'utilisateur A : retourner `404 Not Found` (confusion intentionnelle avec « ressource n'existe pas »).

**Exception :** Les catégories par défaut (catégories système) pourraient être partagées dans une future version. Pour le MVP, toutes les catégories sont scoped par utilisateur.

### 2.7 Pagination

**MVP :** Pas de pagination (retourner tous les enregistrements de l'utilisateur).

Future : Ajouter `?limit=50&offset=0` ou `?page=1&page_size=50` si listes deviennent très grandes.

---

## 3. Routes API — Détail complet

### 3.1 Authentification

#### 3.1.1 `POST /api/auth/register/`

**Authentification :** Pas requise

**Corps de requête (application/json) :**
```json
{
  "email": "user@example.com",
  "username": "john_doe",
  "password": "securepassword123",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Champs :**
- `email` (string, requis) : Adresse e-mail unique
- `username` (string, requis) : Nom d'utilisateur unique
- `password` (string, requis) : Mot de passe en clair (sera hashé côté serveur)
- `first_name` (string, optionnel) : Prénom
- `last_name` (string, optionnel) : Nom de famille

**Réponse 201 Created :**
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "john_doe",
  "first_name": "John",
  "last_name": "Doe",
  "created_at": "2026-10-06T14:30:45Z"
}
```

**Erreurs possibles :**
- `400 Bad Request` — Validation échouée (email invalide, champs manquants, etc.)
- `409 Conflict` — Email ou username déjà utilisé

#### 3.1.2 `POST /api/auth/login/`

**Authentification :** Pas requise

**Corps de requête (application/json) :**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Champs :**
- `email` (string, requis) : Adresse e-mail
- `password` (string, requis) : Mot de passe en clair

**Réponse 200 OK :**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "john_doe",
    "first_name": "John",
    "last_name": "Doe"
  }
}
```

**Erreurs possibles :**
- `400 Bad Request` — Champs manquants
- `401 Unauthorized` — Email ou password incorrect

#### 3.1.3 `POST /api/auth/logout/`

**Authentification :** Requise (token JWT ou session)

**Corps de requête :** Vide

**Réponse 204 No Content :** Pas de corps

**Erreurs possibles :**
- `401 Unauthorized` — Token absent ou invalide

#### 3.1.4 `GET /api/auth/me/`

**Authentification :** Requise

**Corps de requête :** Aucun

**Réponse 200 OK :**
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "john_doe",
  "first_name": "John",
  "last_name": "Doe",
  "created_at": "2026-10-06T14:30:45Z",
  "updated_at": "2026-10-06T14:30:45Z"
}
```

**Erreurs possibles :**
- `401 Unauthorized` — Token absent ou invalide

---

### 3.2 Expenses (Dépenses)

#### 3.2.1 `GET /api/expenses/`

**Authentification :** Requise

**Query parameters (optionnels) :**
- `category_id` (integer) — Filtrer par catégorie
- `date_from` (date, YYYY-MM-DD) — Dépenses à partir de cette date (inclus)
- `date_to` (date, YYYY-MM-DD) — Dépenses jusqu'à cette date (inclus)

**Réponse 200 OK :**
```json
{
  "expenses": [
    {
      "id": 1,
      "user_id": 1,
      "category_id": 5,
      "amount": "25.50",
      "description": "Lunch",
      "date": "2026-10-06",
      "created_at": "2026-10-06T12:00:00Z",
      "updated_at": "2026-10-06T12:00:00Z"
    },
    {
      "id": 2,
      "user_id": 1,
      "category_id": 7,
      "amount": "15.00",
      "description": "Coffee",
      "date": "2026-10-06",
      "created_at": "2026-10-06T13:00:00Z",
      "updated_at": "2026-10-06T13:00:00Z"
    }
  ]
}
```

**Note :** MVP sans pagination. Retourne toutes les dépenses de l'utilisateur courant.

**Erreurs possibles :**
- `401 Unauthorized` — Token absent ou invalide
- `400 Bad Request` — Paramètres invalides (ex. date_from mal formée)

#### 3.2.2 `POST /api/expenses/`

**Authentification :** Requise

**Corps de requête (application/json) :**
```json
{
  "category_id": 5,
  "amount": "25.50",
  "description": "Lunch at work",
  "date": "2026-10-06"
}
```

**Champs :**
- `category_id` (integer, requis) : ID de la catégorie (must belong to current user)
- `amount` (string, requis) : Montant > 0, format décimal
- `description` (string, optionnel) : Description
- `date` (date, requis) : Date de la dépense (YYYY-MM-DD)

**Réponse 201 Created :**
```json
{
  "id": 3,
  "user_id": 1,
  "category_id": 5,
  "amount": "25.50",
  "description": "Lunch at work",
  "date": "2026-10-06",
  "created_at": "2026-10-06T12:15:00Z",
  "updated_at": "2026-10-06T12:15:00Z"
}
```

**Erreurs possibles :**
- `400 Bad Request` — Validation échouée (amount <= 0, champs manquants, date invalide)
- `401 Unauthorized` — Token absent
- `404 Not Found` — `category_id` n'existe pas ou appartient à un autre utilisateur

#### 3.2.3 `GET /api/expenses/{id}/`

**Authentification :** Requise

**Réponse 200 OK :**
```json
{
  "id": 1,
  "user_id": 1,
  "category_id": 5,
  "amount": "25.50",
  "description": "Lunch at work",
  "date": "2026-10-06",
  "created_at": "2026-10-06T12:00:00Z",
  "updated_at": "2026-10-06T12:00:00Z"
}
```

**Erreurs possibles :**
- `401 Unauthorized` — Token absent
- `404 Not Found` — Expense n'existe pas ou appartient à un autre utilisateur

#### 3.2.4 `PATCH /api/expenses/{id}/`

**Authentification :** Requise

**Corps de requête (application/json, tous les champs optionnels) :**
```json
{
  "category_id": 6,
  "amount": "26.50",
  "description": "Updated lunch",
  "date": "2026-10-07"
}
```

**Réponse 200 OK :**
```json
{
  "id": 1,
  "user_id": 1,
  "category_id": 6,
  "amount": "26.50",
  "description": "Updated lunch",
  "date": "2026-10-07",
  "created_at": "2026-10-06T12:00:00Z",
  "updated_at": "2026-10-06T14:00:00Z"
}
```

**Erreurs possibles :**
- `400 Bad Request` — Validation échouée (amount <= 0, etc.)
- `401 Unauthorized` — Token absent
- `404 Not Found` — Expense n'existe pas ou appartient à un autre utilisateur

#### 3.2.5 `DELETE /api/expenses/{id}/`

**Authentification :** Requise

**Réponse 204 No Content :** Pas de corps

**Erreurs possibles :**
- `401 Unauthorized` — Token absent
- `404 Not Found` — Expense n'existe pas ou appartient à un autre utilisateur

---

### 3.3 Budgets

#### 3.3.1 `GET /api/budgets/`

**Authentification :** Requise

**Query parameters (optionnels) :**
- `category_id` (integer) — Filtrer par catégorie

**Réponse 200 OK :**
```json
{
  "budgets": [
    {
      "id": 1,
      "user_id": 1,
      "category_id": 5,
      "amount": "500.00",
      "period_start": "2026-10-01",
      "period_end": "2026-10-31",
      "alert_threshold": "80.00",
      "spent": "234.50",
      "remaining": "265.50",
      "created_at": "2026-10-01T10:00:00Z",
      "updated_at": "2026-10-01T10:00:00Z"
    }
  ]
}
```

**Champs additionnels (calculés) :**
- `spent` (string) : Somme des expenses pour cette catégorie dans la période
- `remaining` (string) : `amount - spent`

**Note :** MVP sans pagination. Retourne tous les budgets de l'utilisateur courant.

**Erreurs possibles :**
- `401 Unauthorized` — Token absent

#### 3.3.2 `POST /api/budgets/`

**Authentification :** Requise

**Corps de requête (application/json) :**
```json
{
  "category_id": 5,
  "amount": "500.00",
  "period_start": "2026-10-01",
  "period_end": "2026-10-31",
  "alert_threshold": "80.00"
}
```

**Champs :**
- `category_id` (integer, requis) : ID de la catégorie (must belong to current user)
- `amount` (string, requis) : Montant > 0
- `period_start` (date, requis) : Début de la période (YYYY-MM-DD)
- `period_end` (date, requis) : Fin de la période (YYYY-MM-DD, >= period_start)
- `alert_threshold` (string, optionnel, default 80.00) : Seuil d'alerte en % (0–100)

**Réponse 201 Created :**
```json
{
  "id": 1,
  "user_id": 1,
  "category_id": 5,
  "amount": "500.00",
  "period_start": "2026-10-01",
  "period_end": "2026-10-31",
  "alert_threshold": "80.00",
  "spent": "0.00",
  "remaining": "500.00",
  "created_at": "2026-10-06T10:00:00Z",
  "updated_at": "2026-10-06T10:00:00Z"
}
```

**Erreurs possibles :**
- `400 Bad Request` — Validation échouée (amount <= 0, period_end < period_start, alert_threshold hors limites, champs manquants)
- `401 Unauthorized` — Token absent
- `404 Not Found` — `category_id` n'existe pas ou appartient à un autre utilisateur
- `409 Conflict` — Budget déjà existant pour cette (user, category, period_start, period_end)

#### 3.3.3 `GET /api/budgets/{id}/`

**Authentification :** Requise

**Réponse 200 OK :**
```json
{
  "id": 1,
  "user_id": 1,
  "category_id": 5,
  "amount": "500.00",
  "period_start": "2026-10-01",
  "period_end": "2026-10-31",
  "alert_threshold": "80.00",
  "spent": "234.50",
  "remaining": "265.50",
  "created_at": "2026-10-01T10:00:00Z",
  "updated_at": "2026-10-01T10:00:00Z"
}
```

**Erreurs possibles :**
- `401 Unauthorized` — Token absent
- `404 Not Found` — Budget n'existe pas ou appartient à un autre utilisateur

#### 3.3.4 `PATCH /api/budgets/{id}/`

**Authentification :** Requise

**Corps de requête (application/json, champs optionnels) :**
```json
{
  "amount": "600.00",
  "alert_threshold": "75.00"
}
```

**Réponse 200 OK :**
```json
{
  "id": 1,
  "user_id": 1,
  "category_id": 5,
  "amount": "600.00",
  "period_start": "2026-10-01",
  "period_end": "2026-10-31",
  "alert_threshold": "75.00",
  "spent": "234.50",
  "remaining": "365.50",
  "created_at": "2026-10-01T10:00:00Z",
  "updated_at": "2026-10-06T14:00:00Z"
}
```

**Erreurs possibles :**
- `400 Bad Request` — Validation échouée (amount <= 0, alert_threshold hors limites)
- `401 Unauthorized` — Token absent
- `404 Not Found` — Budget n'existe pas ou appartient à un autre utilisateur

#### 3.3.5 `DELETE /api/budgets/{id}/`

**Authentification :** Requise

**Réponse 204 No Content :** Pas de corps

**Erreurs possibles :**
- `401 Unauthorized` — Token absent
- `404 Not Found` — Budget n'existe pas ou appartient à un autre utilisateur

---

### 3.4 Categories (Catégories)

#### 3.4.1 `GET /api/categories/`

**Authentification :** Requise

**Réponse 200 OK :**
```json
{
  "categories": [
    {
      "id": 1,
      "user_id": 1,
      "name": "Alimentation",
      "description": "Nourriture et boissons",
      "is_active": true,
      "created_at": "2026-10-01T08:00:00Z",
      "updated_at": "2026-10-01T08:00:00Z"
    },
    {
      "id": 2,
      "user_id": 1,
      "name": "Transport",
      "description": "Transports et carburant",
      "is_active": true,
      "created_at": "2026-10-01T08:00:00Z",
      "updated_at": "2026-10-01T08:00:00Z"
    }
  ]
}
```

**Note :** Retourne uniquement les catégories de l'utilisateur courant. Inclut les catégories par défaut créées à l'inscription.

**Erreurs possibles :**
- `401 Unauthorized` — Token absent

#### 3.4.2 `POST /api/categories/`

**Authentification :** Requise

**Corps de requête (application/json) :**
```json
{
  "name": "Loisirs",
  "description": "Divertissements et hobbies"
}
```

**Champs :**
- `name` (string, requis) : Nom de la catégorie (unique par utilisateur)
- `description` (string, optionnel) : Description

**Réponse 201 Created :**
```json
{
  "id": 15,
  "user_id": 1,
  "name": "Loisirs",
  "description": "Divertissements et hobbies",
  "is_active": true,
  "created_at": "2026-10-06T10:00:00Z",
  "updated_at": "2026-10-06T10:00:00Z"
}
```

**Erreurs possibles :**
- `400 Bad Request` — Validation échouée (name manquant, name vide)
- `401 Unauthorized` — Token absent
- `409 Conflict` — Catégorie avec ce nom existe déjà pour cet utilisateur

#### 3.4.3 `GET /api/categories/{id}/`

**Authentification :** Requise

**Réponse 200 OK :**
```json
{
  "id": 1,
  "user_id": 1,
  "name": "Alimentation",
  "description": "Nourriture et boissons",
  "is_active": true,
  "created_at": "2026-10-01T08:00:00Z",
  "updated_at": "2026-10-01T08:00:00Z"
}
```

**Erreurs possibles :**
- `401 Unauthorized` — Token absent
- `404 Not Found` — Catégorie n'existe pas ou appartient à un autre utilisateur

#### 3.4.4 `PATCH /api/categories/{id}/`

**Authentification :** Requise

**Corps de requête (application/json, champs optionnels) :**
```json
{
  "name": "Alimentation et boissons",
  "description": "Nourriture, boissons et restaurants",
  "is_active": true
}
```

**Champs :**
- `name` (string, optionnel) : Nouveau nom (doit rester unique par utilisateur)
- `description` (string, optionnel) : Nouvelle description
- `is_active` (boolean, optionnel) : Activer/désactiver la catégorie

**Réponse 200 OK :**
```json
{
  "id": 1,
  "user_id": 1,
  "name": "Alimentation et boissons",
  "description": "Nourriture, boissons et restaurants",
  "is_active": true,
  "created_at": "2026-10-01T08:00:00Z",
  "updated_at": "2026-10-06T14:00:00Z"
}
```

**Erreurs possibles :**
- `400 Bad Request` — Validation échouée (name vide, etc.)
- `401 Unauthorized` — Token absent
- `404 Not Found` — Catégorie n'existe pas ou appartient à un autre utilisateur
- `409 Conflict` — Nouveau name existe déjà pour cet utilisateur

#### 3.4.5 `DELETE /api/categories/{id}/`

**Authentification :** Requise

**Réponse 204 No Content :** Pas de corps

**Erreurs possibles :**
- `401 Unauthorized` — Token absent
- `404 Not Found` — Catégorie n'existe pas ou appartient à un autre utilisateur

---

## 4. Questions ouvertes et risques

### 4.1 Questions réservées (pas tranchées dans cette spec)

1. **Suppression de catégories avec dépenses/budgets actifs :**
   - Faut-il rejeter la suppression (RESTRICT) ou la permettre (CASCADE) ?
   - Décision : à trancher dans une issue dédiée.

2. **Listing des dépenses/budgets : filtrage et tri :**
   - Ordonnancement par défaut (date descendante ?) ?
   - Supports d'autres critères (par montant, par description) ?
   - Décision : à trancher dans une issue d'API avancée.

3. **Soft-delete vs. suppression physique :**
   - DELETE doit-il faire un vrai DELETE SQL ou seulement flaguer `is_active = false` ?
   - Décision : probablement suppression physique pour MVP, mais à confirmer.

4. **Authentification : JWT vs. Session Django :**
   - Cette spec suppose un mécanisme d'authentification (probablement JWT + Django tokenauth ou DRF Token).
   - Détails (durée du token, refresh tokens, etc.) : à spécifier dans une issue dédiée.

5. **Catégories par défaut :**
   - Quand et comment les ~15 catégories par défaut sont-elles créées à l'inscription ?
   - Implémentation : signal Django `post_save` sur User (détail implémentation, hors spec API).

6. **CORS et politiques d'accès :**
   - Si frontend et backend sont sur domaines différents, faut-il configurer CORS ?
   - Décision : probablement oui en développement, à valider avant déploiement.

### 4.2 Risques détectés

| Risque | Impact | Mitigation |
|--------|--------|-----------|
| **Confusion entre 404 et 403 intentionnelle.** Dans cette spec, une ressource d'un autre user retourne 404 (pas 403), ce qui peut être contre-intuitif pour les développeurs. | Développeur teste mal l'ownership. | Documenter clairement cette décision dans le README API. Ajouter des tests spécifiques. |
| **Calcul temps réel de `spent` pour budgets.** Si bcp de dépenses, la requête `SELECT SUM(amount) WHERE category_id = X AND date BETWEEN Y AND Z` pourrait être lente. | Latence accrue sur GET budgets en production. | Ajouter un index sur `(category_id, date)` ou précomputer un champ `spent` avec une trigger/task cron (future issue). |
| **Catégories supprimées avec dépenses orphelines.** Si on supprime une catégorie, que deviennent les dépenses/budgets qui la référencent ? | Cohérence des données, erreurs 404 imprévisibles. | Trancher RESTRICT vs. CASCADE avant implémentation. Documenter le choix. |
| **Pas de rate limiting initial.** API publique sans limite de requêtes par utilisateur. | Risque d'abus, DOS. | Ajouter rate limiting (ex. 1000 req/heure par user) lors du déploiement. |
| **Seed data de catégories en français.** Si utilisateurs non francophones, nomenclature par défaut inadéquate. | UX pauvre pour utilisateurs non FR. | (Hors MVP) Permettre sélection de langue à l'inscription, charger seed data multi-langue. |

---

## 5. Résumé du livrable attendu

Le document `docs/api-design.md` doit contenir :

1. **Vue d'ensemble** : conventions générales, base URL, authentification, sérialisation (Decimal), timestamps, format d'erreur, ownership.
2. **Routes d'authentification** : register, login, logout, me.
3. **Routes CRUD expenses** : GET list, POST, GET detail, PATCH, DELETE.
4. **Routes CRUD budgets** : GET list (avec consumed), POST, GET detail (avec consumed), PATCH, DELETE.
5. **Routes CRUD categories** : GET list, POST, GET detail, PATCH, DELETE.
6. **Pour chaque route :** méthode, chemin (avec slash final), authentification requise, corps de requête, réponse 200/201, codes d'erreur et message cohérent.

Ce document est la source de vérité pour les développeurs frontend (SvelteKit) et tout client API externe. Aucune ambiguïté, aucun détail interne.

---

*Spécification proposée par Agent Product & Architecture. À valider par l'équipe avant que le Full-Stack Development agent ne commence l'implémentation.*
