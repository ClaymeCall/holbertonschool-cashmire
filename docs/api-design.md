# Contrat API REST — Cashmire

- **Dernière mise à jour :** 2026-10-06
- **Auteur :** Spécification issue #7 (contrat API initial)
- **Public cible :** Développeurs frontend (SvelteKit), clients API externes
- **Statut du document :** Proposé, à relire par un autre membre de l'équipe. Source de vérité pour les routes API une fois approuvé.

> **Référence vivante :** une fois les routes ci-dessous implémentées côté
> backend, le schéma OpenAPI généré automatiquement et son interface
> Swagger (`/api/docs/`, schéma brut sur `/api/schema/`) deviennent la
> référence à jour sur l'état réel de l'API. Ce document garde sa valeur
> de contrat de conception, mais en cas d'écart, Swagger UI fait foi.

---

## 1. Vue d'ensemble

### 1.1 Base URL et schéma général

Toutes les routes sont préfixées par `/api/`.

Exemple : `POST /api/auth/login/`

Pas de versioning initial (v1, v2, etc.). Si besoin futur, ajouter `/api/v1/` etc.

### 1.2 Authentification

**Mécanisme :** Token JWT (JSON Web Token) ou session Django.

**Fourniture du token :**
- En header : `Authorization: Bearer <token>`
- Ou en cookie (si session Django configurée)

**Routes non authentifiées (accès public) :**
- `POST /api/auth/register/` — création de compte
- `POST /api/auth/login/` — connexion
- `GET /api/health/` — health check serveur

**Routes authentifiées (token requis) :**
- Toutes les autres (expenses, budgets, catégories, logout, me)

**Réponse 401 Unauthorized :**
Retournée si le token est absent, expiré ou invalide. Inclure un header `WWW-Authenticate: Bearer` dans la réponse.

**À confirmer :** Détails du mécanisme JWT (durée du token, refresh tokens, etc.) — à spécifier dans une issue dédiée.

### 1.3 Sérialisation des montants (Decimal)

**Tous les champs monétaires sont sérialisés en chaînes JSON**, jamais en nombres flottants.

Exemples :
```json
{
  "amount": "123.45",
  "budget_amount": "500.00",
  "spent": "234.50",
  "alert_threshold": "80.00"
}
```

**Raison :** Éviter les erreurs d'arrondi IEEE 754 (ex. 0.1 + 0.2 ≠ 0.3 en float ; en Decimal c'est exactement 0.30).

### 1.4 Timestamps

Tous les timestamps (`created_at`, `updated_at`) sont sérialisés en **format ISO 8601 / RFC 3339** (ex. `"2026-10-06T14:30:45Z"`).

Fuseau horaire : UTC (suffix Z).

### 1.5 Format des erreurs

Réponse d'erreur uniforme en JSON :

```json
{
  "error": "<code_erreur>",
  "message": "<description lisible>"
}
```

**Codes d'erreur courants :**
- `INVALID_DATA` — Validation échouée (400 Bad Request)
- `NOT_FOUND` — Ressource non trouvée (404 Not Found)
- `UNAUTHORIZED` — Token absent ou invalide (401 Unauthorized)
- `FORBIDDEN` — Accès refusé (403 Forbidden, rare ; généralement 404 pour ownership)
- `CONFLICT` — Conflit (ex. unicité violée, 409 Conflict)
- `SERVER_ERROR` — Erreur serveur (500 Internal Server Error)

**Confidentialité :** Les messages d'erreur ne révèlent pas de détails internes (stacktraces, noms SQL, chemins fichiers, noms de colonnes).

### 1.6 Ownership et contrôles d'accès

Ressources scoped par utilisateur : `Expense`, `Budget`, `Category`.

**Principe :** Une ressource créée par l'utilisateur A ne peut être lue, modifiée ou supprimée que par l'utilisateur A.

**Implémentation :**
- API valide `resource.user_id == request.user.id` avant chaque opération.
- Si l'utilisateur B tente d'accéder à une ressource de l'utilisateur A : retourner **`404 Not Found`** (pas 403 ; confusion intentionnelle avec « ressource n'existe pas »).
- Exemple : si Alice (user_id=1) tente de GET une expense d'Alice, 200 OK. Si Bob (user_id=2) tente de GET l'expense d'Alice, 404 Not Found.

### 1.7 Pagination

**MVP :** Pas de pagination. Toutes les listes (`GET /api/expenses/`, `GET /api/budgets/`, `GET /api/categories/`) retournent l'ensemble complet des enregistrements de l'utilisateur courant.

**Future :** Ajouter `?limit=50&offset=0` ou `?page=1&page_size=50` si listes deviennent très grandes.

### 1.8 Codes HTTP et méthodes

| Opération | Méthode | Code réponse happy path | Corps réponse |
|-----------|---------|---------|---------|
| Créer une ressource | POST | 201 Created | Ressource créée |
| Lire une ressource | GET | 200 OK | Ressource ou liste |
| Modifier une ressource | PATCH | 200 OK | Ressource modifiée |
| Supprimer une ressource | DELETE | 204 No Content | Vide |

---

## 2. Routes d'authentification

### 2.1 `POST /api/auth/register/`

**Authentification :** Non requise

**Description :** Créer un nouveau compte utilisateur.

**Corps de requête (application/json) :**
```json
{
  "email": "alice@example.com",
  "username": "alice_wonderland",
  "password": "securepassword123",
  "first_name": "Alice",
  "last_name": "Wonderland"
}
```

**Champs de requête :**
- `email` (string, requis) : Adresse e-mail unique. Doit être valide (format RFC 5322).
- `username` (string, requis) : Nom d'utilisateur unique. 3–150 caractères.
- `password` (string, requis) : Mot de passe en clair (sera hashé côté serveur). Minimum 8 caractères recommandé.
- `first_name` (string, optionnel) : Prénom. Maximum 150 caractères.
- `last_name` (string, optionnel) : Nom de famille. Maximum 150 caractères.

**Réponse 201 Created :**
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

**Erreurs possibles :**
- `400 Bad Request` — Validation échouée
  - Message : `"email": "Adresse e-mail invalide"` ou `"password": "Minimum 8 caractères"`
- `409 Conflict` — Email ou username déjà utilisé
  - Message : `"error": "CONFLICT", "message": "Email ou username déjà utilisé"`

---

### 2.2 `POST /api/auth/login/`

**Authentification :** Non requise

**Description :** Authentifier un utilisateur et retourner un token.

**Corps de requête (application/json) :**
```json
{
  "email": "alice@example.com",
  "password": "securepassword123"
}
```

**Champs de requête :**
- `email` (string, requis) : Adresse e-mail.
- `password` (string, requis) : Mot de passe en clair.

**Réponse 200 OK :**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "email": "alice@example.com",
    "username": "alice_wonderland",
    "first_name": "Alice",
    "last_name": "Wonderland"
  }
}
```

**Champs de réponse :**
- `token` (string) : Token JWT ou session à inclure dans les requêtes futures (header `Authorization: Bearer <token>`).
- `user` (object) : Objet utilisateur avec `id`, `email`, `username`, `first_name`, `last_name`.

**Erreurs possibles :**
- `400 Bad Request` — Champs manquants ou invalides
  - Message : `"email": "Requis"` ou `"password": "Requis"`
- `401 Unauthorized` — Email ou password incorrect
  - Message : `"error": "UNAUTHORIZED", "message": "Identifiants invalides"`

---

### 2.3 `POST /api/auth/logout/`

**Authentification :** Requise

**Description :** Invalider le token/session de l'utilisateur courant et se déconnecter.

**Corps de requête :** Vide

**Réponse 204 No Content :** 
Pas de corps. Code 204.

**Erreurs possibles :**
- `401 Unauthorized` — Token absent ou invalide
  - Message : `"error": "UNAUTHORIZED", "message": "Token invalide ou expiré"`

---

### 2.4 `GET /api/auth/me/`

**Authentification :** Requise

**Description :** Récupérer les données de l'utilisateur courant (celui du token).

**Corps de requête :** Aucun

**Réponse 200 OK :**
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

**Champs de réponse :**
- `id` (integer) : Identifiant utilisateur.
- `email`, `username`, `first_name`, `last_name` (strings).
- `is_active` (boolean) : Indicateur de compte actif.
- `created_at`, `updated_at` (strings ISO 8601).

**Erreurs possibles :**
- `401 Unauthorized` — Token absent ou invalide
  - Message : `"error": "UNAUTHORIZED", "message": "Token invalide ou expiré"`

---

## 3. Routes CRUD — Expenses (Dépenses)

### 3.1 `GET /api/expenses/`

**Authentification :** Requise par session Django (`sessionid`).

**Description :** Lister toutes les dépenses de l'utilisateur courant, avec filtrage optionnel.

**Query parameters (optionnels) :**
- `category_id` (integer) — Filtrer les dépenses par catégorie.
- `date_from` (date, format YYYY-MM-DD) — Dépenses à partir de cette date (inclus).
- `date_to` (date, format YYYY-MM-DD) — Dépenses jusqu'à cette date (inclus).

**Réponse 200 OK :**
```json
{
  "expenses": [
    {
      "id": 1,
      "user_id": 1,
      "category_id": 5,
      "amount": "25.50",
      "description": "Déjeuner au travail",
      "date": "2026-10-06",
      "created_at": "2026-10-06T12:00:00Z",
      "updated_at": "2026-10-06T12:00:00Z"
    },
    {
      "id": 2,
      "user_id": 1,
      "category_id": 7,
      "amount": "5.00",
      "description": "Café",
      "date": "2026-10-06",
      "created_at": "2026-10-06T13:00:00Z",
      "updated_at": "2026-10-06T13:00:00Z"
    }
  ]
}
```

**Note :** MVP sans pagination. Retourne toutes les dépenses de l'utilisateur courant (filtrées selon les query params si présents).

**Erreurs possibles :**
- `403 Forbidden` — Session absente ou invalide (comportement actuel de `SessionAuthentication`).
- `400 Bad Request` — Paramètres invalides
  - Message : erreur de validation au niveau du paramètre, notamment pour une date invalide, un identifiant de catégorie non positif ou `date_from` postérieure à `date_to`.

---

### 3.2 `POST /api/expenses/`

**Authentification :** Requise

**Description :** Créer une nouvelle dépense pour l'utilisateur courant.

**Corps de requête (application/json) :**
```json
{
  "category_id": 5,
  "amount": "25.50",
  "description": "Déjeuner au travail",
  "date": "2026-10-06"
}
```

**Champs de requête :**
- `category_id` (integer, requis) : ID de la catégorie. Doit appartenir à l'utilisateur courant.
- `amount` (string, requis) : Montant > 0, format décimal (ex. `"25.50"`).
- `description` (string, optionnel) : Description libre de la dépense.
- `date` (date, requis) : Date de la dépense (YYYY-MM-DD). Peut être antérieure à `created_at` (enregistrement rétroactif).

**Contraintes de validation :**
- `amount` doit être > 0.
- `category_id` doit exister et appartenir à l'utilisateur courant.
- `date` doit être valide (format YYYY-MM-DD).

**Réponse 201 Created :**
```json
{
  "id": 3,
  "user_id": 1,
  "category_id": 5,
  "amount": "25.50",
  "description": "Déjeuner au travail",
  "date": "2026-10-06",
  "created_at": "2026-10-06T12:15:00Z",
  "updated_at": "2026-10-06T12:15:00Z"
}
```

**Erreurs possibles :**
- `400 Bad Request` — Validation échouée
  - Message : `"amount": "Doit être > 0"` ou `"category_id": "Requis"` ou `"date": "Format invalide"`
- `401 Unauthorized` — Token absent ou invalide
  - Message : `"error": "UNAUTHORIZED", "message": "Token invalide ou expiré"`
- `404 Not Found` — Category n'existe pas ou appartient à un autre utilisateur
  - Message : `"error": "NOT_FOUND", "message": "Catégorie non trouvée"`

---

### 3.3 `GET /api/expenses/{id}/`

**Authentification :** Requise

**Description :** Récupérer une dépense spécifique.

**Paramètres de chemin :**
- `id` (integer) : Identifiant de la dépense.

**Réponse 200 OK :**
```json
{
  "id": 1,
  "user_id": 1,
  "category_id": 5,
  "amount": "25.50",
  "description": "Déjeuner au travail",
  "date": "2026-10-06",
  "created_at": "2026-10-06T12:00:00Z",
  "updated_at": "2026-10-06T12:00:00Z"
}
```

**Erreurs possibles :**
- `401 Unauthorized` — Token absent ou invalide
  - Message : `"error": "UNAUTHORIZED", "message": "Token invalide ou expiré"`
- `404 Not Found` — Expense n'existe pas ou appartient à un autre utilisateur
  - Message : `"error": "NOT_FOUND", "message": "Dépense non trouvée"`

---

### 3.4 `PATCH /api/expenses/{id}/`

**Authentification :** Requise

**Description :** Modifier une dépense existante. Tous les champs sont optionnels.

**Paramètres de chemin :**
- `id` (integer) : Identifiant de la dépense.

**Corps de requête (application/json, tous les champs optionnels) :**
```json
{
  "category_id": 6,
  "amount": "26.50",
  "description": "Déjeuner au restaurant",
  "date": "2026-10-07"
}
```

**Champs de requête (optionnels) :**
- `category_id` (integer) : Nouvelle catégorie (doit appartenir à l'utilisateur courant).
- `amount` (string) : Nouveau montant (doit être > 0).
- `description` (string) : Nouvelle description.
- `date` (date) : Nouvelle date (YYYY-MM-DD).

**Réponse 200 OK :**
```json
{
  "id": 1,
  "user_id": 1,
  "category_id": 6,
  "amount": "26.50",
  "description": "Déjeuner au restaurant",
  "date": "2026-10-07",
  "created_at": "2026-10-06T12:00:00Z",
  "updated_at": "2026-10-06T14:00:00Z"
}
```

**Erreurs possibles :**
- `400 Bad Request` — Validation échouée
  - Message : `"amount": "Doit être > 0"` ou `"date": "Format invalide"`
- `401 Unauthorized` — Token absent ou invalide
  - Message : `"error": "UNAUTHORIZED", "message": "Token invalide ou expiré"`
- `404 Not Found` — Expense n'existe pas ou appartient à un autre utilisateur, ou category n'existe pas
  - Message : `"error": "NOT_FOUND", "message": "Dépense non trouvée"` ou `"Catégorie non trouvée"`

---

### 3.5 `DELETE /api/expenses/{id}/`

**Authentification :** Requise

**Description :** Supprimer une dépense.

**Paramètres de chemin :**
- `id` (integer) : Identifiant de la dépense.

**Réponse 204 No Content :** 
Pas de corps. Code 204.

**Erreurs possibles :**
- `401 Unauthorized` — Token absent ou invalide
  - Message : `"error": "UNAUTHORIZED", "message": "Token invalide ou expiré"`
- `404 Not Found` — Expense n'existe pas ou appartient à un autre utilisateur
  - Message : `"error": "NOT_FOUND", "message": "Dépense non trouvée"`

---

## 4. Routes CRUD — Budgets

### 4.1 `GET /api/budgets/`

**Authentification :** Requise

**Description :** Lister tous les budgets de l'utilisateur courant, avec données de consommation calculées en temps réel.

**Query parameters (optionnels) :**
- `category_id` (integer) — Filtrer les budgets par catégorie.

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

**Champs de réponse (additionnels) :**
- `spent` (string) : Somme des expenses pour cette catégorie dans la période [period_start, period_end]. Calculé dynamiquement.
- `remaining` (string) : `amount - spent`. Peut être négatif si dépenses > budget.

**Note :** MVP sans pagination. Retourne tous les budgets de l'utilisateur courant.

**Erreurs possibles :**
- `401 Unauthorized` — Token absent ou invalide
  - Message : `"error": "UNAUTHORIZED", "message": "Token invalide ou expiré"`

---

### 4.2 `POST /api/budgets/`

**Authentification :** Requise

**Description :** Créer un nouveau budget pour l'utilisateur courant.

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

**Champs de requête :**
- `category_id` (integer, requis) : ID de la catégorie. Doit appartenir à l'utilisateur courant.
- `amount` (string, requis) : Montant > 0, format décimal.
- `period_start` (date, requis) : Début de la période (YYYY-MM-DD).
- `period_end` (date, requis) : Fin de la période (YYYY-MM-DD). Doit être >= period_start.
- `alert_threshold` (string, optionnel, défaut `"80.00"`) : Seuil d'alerte en pourcentage (0–100, ex. `"80.00"` = 80 %).

**Contraintes de validation :**
- `amount` doit être > 0.
- `period_end` doit être >= `period_start`.
- `alert_threshold` doit être entre 0 et 100 (si fourni).
- Unicité : un seul budget par (user, category, period_start, period_end). Un budget en doublon sur cette période/catégorie retourne 409 Conflict.
- `category_id` doit exister et appartenir à l'utilisateur courant.

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
- `400 Bad Request` — Validation échouée
  - Message : `"amount": "Doit être > 0"` ou `"period_end": "Doit être >= period_start"` ou `"alert_threshold": "Doit être entre 0 et 100"`
- `401 Unauthorized` — Token absent ou invalide
  - Message : `"error": "UNAUTHORIZED", "message": "Token invalide ou expiré"`
- `404 Not Found` — Category n'existe pas ou appartient à un autre utilisateur
  - Message : `"error": "NOT_FOUND", "message": "Catégorie non trouvée"`
- `409 Conflict` — Budget déjà existant pour cette (user, category, period_start, period_end)
  - Message : `"error": "CONFLICT", "message": "Budget déjà existant pour cette période et catégorie"`

---

### 4.3 `GET /api/budgets/{id}/`

**Authentification :** Requise

**Description :** Récupérer un budget spécifique avec données de consommation.

**Paramètres de chemin :**
- `id` (integer) : Identifiant du budget.

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
- `401 Unauthorized` — Token absent ou invalide
  - Message : `"error": "UNAUTHORIZED", "message": "Token invalide ou expiré"`
- `404 Not Found` — Budget n'existe pas ou appartient à un autre utilisateur
  - Message : `"error": "NOT_FOUND", "message": "Budget non trouvé"`

---

### 4.4 `PATCH /api/budgets/{id}/`

**Authentification :** Requise

**Description :** Modifier un budget existant. Tous les champs sont optionnels. Les champs `category_id`, `period_start` et `period_end` sont généralement non modifiables après création (à confirmer).

**Paramètres de chemin :**
- `id` (integer) : Identifiant du budget.

**Corps de requête (application/json, tous les champs optionnels) :**
```json
{
  "amount": "600.00",
  "alert_threshold": "75.00"
}
```

**Champs de requête (optionnels) :**
- `amount` (string) : Nouveau montant (doit être > 0).
- `alert_threshold` (string) : Nouveau seuil (0–100).

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
- `400 Bad Request` — Validation échouée
  - Message : `"amount": "Doit être > 0"` ou `"alert_threshold": "Doit être entre 0 et 100"`
- `401 Unauthorized` — Token absent ou invalide
  - Message : `"error": "UNAUTHORIZED", "message": "Token invalide ou expiré"`
- `404 Not Found` — Budget n'existe pas ou appartient à un autre utilisateur
  - Message : `"error": "NOT_FOUND", "message": "Budget non trouvé"`

---

### 4.5 `DELETE /api/budgets/{id}/`

**Authentification :** Requise

**Description :** Supprimer un budget.

**Paramètres de chemin :**
- `id` (integer) : Identifiant du budget.

**Réponse 204 No Content :** 
Pas de corps. Code 204.

**Erreurs possibles :**
- `401 Unauthorized` — Token absent ou invalide
  - Message : `"error": "UNAUTHORIZED", "message": "Token invalide ou expiré"`
- `404 Not Found` — Budget n'existe pas ou appartient à un autre utilisateur
  - Message : `"error": "NOT_FOUND", "message": "Budget non trouvé"`

---

## 5. Routes CRUD — Categories (Catégories)

### 5.1 `GET /api/categories/`

**Authentification :** Requise

**Description :** Lister toutes les catégories de l'utilisateur courant. Inclut les catégories par défaut créées à l'inscription.

**Implémentation :** Cette route de lecture seule est disponible depuis l'issue #33. Les routes de création, modification et suppression restent prévues pour des issues ultérieures. Avec `SessionAuthentication` de DRF, une requête sans session authentifiée reçoit HTTP `403 Forbidden`.

**Query parameters :** Aucun (MVP sans filtrage avancé).

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

**Note :** Retourne uniquement les catégories de l'utilisateur courant (scoped par user_id).

**Erreurs possibles :**
- `403 Forbidden` — Session absente ou utilisateur non authentifié

---

### 5.2 `POST /api/categories/`

**Authentification :** Requise

**Description :** Créer une nouvelle catégorie personnalisée pour l'utilisateur courant.

**Corps de requête (application/json) :**
```json
{
  "name": "Loisirs",
  "description": "Divertissements et hobbies"
}
```

**Champs de requête :**
- `name` (string, requis) : Nom de la catégorie. Doit être unique par utilisateur. 1–100 caractères.
- `description` (string, optionnel) : Description. Peut être vide.

**Contraintes de validation :**
- `name` ne doit pas être vide.
- `name` doit être unique pour l'utilisateur courant (deux catégories portant le même nom = 409 Conflict).

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

**Note :** Le champ `is_active` est toujours `true` à la création.

**Erreurs possibles :**
- `400 Bad Request` — Validation échouée
  - Message : `"name": "Requis"` ou `"name": "Ne doit pas être vide"`
- `401 Unauthorized` — Token absent ou invalide
  - Message : `"error": "UNAUTHORIZED", "message": "Token invalide ou expiré"`
- `409 Conflict` — Catégorie avec ce nom existe déjà pour cet utilisateur
  - Message : `"error": "CONFLICT", "message": "Une catégorie portant ce nom existe déjà"`

---

### 5.3 `GET /api/categories/{id}/`

**Authentification :** Requise

**Description :** Récupérer une catégorie spécifique.

**Paramètres de chemin :**
- `id` (integer) : Identifiant de la catégorie.

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
- `401 Unauthorized` — Token absent ou invalide
  - Message : `"error": "UNAUTHORIZED", "message": "Token invalide ou expiré"`
- `404 Not Found` — Catégorie n'existe pas ou appartient à un autre utilisateur
  - Message : `"error": "NOT_FOUND", "message": "Catégorie non trouvée"`

---

### 5.4 `PATCH /api/categories/{id}/`

**Authentification :** Requise

**Description :** Modifier une catégorie existante. Tous les champs sont optionnels.

**Paramètres de chemin :**
- `id` (integer) : Identifiant de la catégorie.

**Corps de requête (application/json, tous les champs optionnels) :**
```json
{
  "name": "Alimentation et boissons",
  "description": "Nourriture, boissons et restaurants",
  "is_active": true
}
```

**Champs de requête (optionnels) :**
- `name` (string) : Nouveau nom (doit rester unique par utilisateur).
- `description` (string) : Nouvelle description.
- `is_active` (boolean) : Activer (true) ou désactiver (false) la catégorie.

**Contraintes de validation :**
- `name` ne doit pas être vide (si fourni).
- `name` doit rester unique pour l'utilisateur courant.

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
- `400 Bad Request` — Validation échouée
  - Message : `"name": "Ne doit pas être vide"`
- `401 Unauthorized` — Token absent ou invalide
  - Message : `"error": "UNAUTHORIZED", "message": "Token invalide ou expiré"`
- `404 Not Found` — Catégorie n'existe pas ou appartient à un autre utilisateur
  - Message : `"error": "NOT_FOUND", "message": "Catégorie non trouvée"`
- `409 Conflict` — Nouveau nom existe déjà pour cet utilisateur
  - Message : `"error": "CONFLICT", "message": "Une catégorie portant ce nom existe déjà"`

---

### 5.5 `DELETE /api/categories/{id}/`

**Authentification :** Requise

**Description :** Supprimer une catégorie.

**Paramètres de chemin :**
- `id` (integer) : Identifiant de la catégorie.

**Réponse 204 No Content :** 
Pas de corps. Code 204.

**Erreurs possibles :**
- `401 Unauthorized` — Token absent ou invalide
  - Message : `"error": "UNAUTHORIZED", "message": "Token invalide ou expiré"`
- `404 Not Found` — Catégorie n'existe pas ou appartient à un autre utilisateur
  - Message : `"error": "NOT_FOUND", "message": "Catégorie non trouvée"`

**À confirmer :** Comportement lors de la suppression d'une catégorie ayant des expenses ou budgets actifs :
- Option A : RESTRICT — retourner 409 Conflict si la catégorie a des références.
- Option B : CASCADE — supprimer les expenses et budgets orphelins (non recommandé pour les données financières).
- Décision : à trancher dans une issue dédiée.

---

## 6. Questions ouvertes et risques

### 6.1 Questions réservées (à trancher dans des issues dédiées)

1. **Authentification : JWT vs. Session Django**
   - Cette spec suppose un mécanisme d'authentification (JWT + tokenauth ou DRF Token, ou session Django).
   - Détails : durée du token, refresh tokens, révocation, implémentation — à spécifier dans une issue dédiée.

2. **Suppression de catégories avec dépenses/budgets actifs**
   - Faut-il rejeter la suppression (RESTRICT) ou la permettre (CASCADE) ?
   - Décision : à trancher avant implémentation (issue dédiée).

3. **Soft-delete vs. suppression physique**
   - DELETE doit-il faire un vrai DELETE SQL ou seulement flaguer `is_active = false` ?
   - Décision : probablement suppression physique pour MVP, mais à confirmer.

4. **Listing des dépenses/budgets : filtrage et tri avancé**
   - Ordonnancement par défaut (date descendante ?) ?
   - Support d'autres critères (par montant, par description) ?
   - Décision : à trancher dans une issue d'API avancée.

5. **Catégories par défaut : timing et contenu**
   - Quand exactement les ~15 catégories par défaut sont-elles créées à l'inscription ?
   - Implémentation : signal Django `post_save` sur User (détail implémentation, hors spec API).
   - Contenu des catégories : à définir dans une issue dédiée.

6. **CORS et politiques d'accès cross-origin**
   - Si frontend et backend sont sur domaines différents, faut-il configurer CORS ?
   - Décision : probablement oui en développement, à valider avant déploiement.

7. **Rate limiting et protections contre les abus**
   - API sans limite de requêtes par utilisateur initialement.
   - Futur : ajouter rate limiting (ex. 1000 req/heure par user) lors du déploiement en production.

---

### 6.2 Risques détectés

| Risque | Impact | Mitigation |
|--------|--------|-----------|
| **Confusion entre 404 et 403 intentionnelle.** Cette spec retourne 404 (pas 403) pour une ressource d'un autre user, ce qui peut être contre-intuitif pour les développeurs. | Développeur teste mal l'ownership. | Documenter clairement cette décision (document présent). Ajouter des tests spécifiques en issue. |
| **Calcul temps réel de `spent` pour budgets.** Si bcp de dépenses, la requête SELECT SUM(amount) pourrait être lente. | Latence accrue sur GET budgets en production. | Ajouter des indices sur `(category_id, date)` ou précomputer avec trigger/cron (future issue). |
| **Catégories supprimées avec dépenses/budgets orphelines.** Si on supprime une catégorie, que deviennent les dépenses/budgets ? | Cohérence des données, erreurs 404 imprévisibles. | Trancher RESTRICT vs. CASCADE avant implémentation. |
| **Pas de rate limiting initial.** API sans limite de requêtes par utilisateur. | Risque d'abus, DOS. | Ajouter rate limiting en déploiement production. |
| **Seed data de catégories par défaut en français.** Utilisateurs non francophones : nomenclature inadéquate. | UX pauvre pour utilisateurs non FR. | (Hors MVP) Permettre sélection de langue, charger seed multi-langue. |

---

## 7. Résumé de conformité

| Critère | Critères d'acceptation | Couverture |
|---------|---------|----------|
| AC-1 | Document en français | ✓ Présent et en français |
| AC-2 | Vue d'ensemble avec conventions | ✓ Section 1 : base URL, auth, montants, timestamps, erreurs, ownership, pagination |
| AC-3 | Chaque route documentée avec structure complète | ✓ Sections 2–5 : 4 routes auth + 5 expenses + 5 budgets + 5 categories = 19 routes |
| AC-4 | Montants en chaînes JSON | ✓ Section 1.3 et exemples dans chaque route |
| AC-5 | Ownership et 404 | ✓ Section 1.6 : « 404 Not Found si appartient à un autre utilisateur » |
| AC-6 | Tous les chemins avec slash final | ✓ Toutes les routes : `/api/auth/register/`, `/api/expenses/`, `/api/budgets/{id}/`, etc. |
| AC-7 | Authentification documentée | ✓ Section 1.2 : token JWT/session, header Authorization, réponse 401 |
| AC-8 | Routes auth : register, login, logout, me | ✓ Sections 2.1–2.4 |
| AC-9 | Routes CRUD expenses | ✓ Sections 3.1–3.5 : GET list, POST, GET detail, PATCH, DELETE |
| AC-10 | Routes CRUD budgets avec spent/remaining | ✓ Sections 4.1–4.5 : champs `spent` et `remaining` calculés dynamiquement |
| AC-11 | Routes CRUD categories | ✓ Sections 5.1–5.5 : GET list, POST, GET detail, PATCH, DELETE |
| AC-12 | Format d'erreur uniforme | ✓ Section 1.5 : `{ "error": "code", "message": "description" }` |
| AC-13 | Pas de détails internes | ✓ Exemples d'erreurs génériques (« Données invalides », « Ressource non trouvée ») |
| AC-14 | Champs attendus pour POST/PATCH | ✓ Chaque route liste ses champs de requête |
| AC-15 | Pagination (ou absence) | ✓ Section 1.7 : MVP sans pagination, futur avec `?limit=50&offset=0` |
| AC-16 | Contraintes de validation | ✓ Chaque route énonce ses validations (amount > 0, period_end >= period_start, UNIQUE(user, name)) |
| AC-17 | Timestamps ISO 8601 | ✓ Section 1.4 : format `"2026-10-06T14:30:45Z"`, fuseau UTC |
| AC-18 | POST retourne 201 Created | ✓ Register, login, expenses, budgets, categories : tous 201 |
| AC-19 | PATCH retourne 200 OK | ✓ Tous les PATCH : 200 OK avec ressource modifiée |
| AC-20 | DELETE retourne 204 No Content | ✓ Tous les DELETE : 204, pas de corps |

---

## Références

- **Spec issue #7 :** `docs/specs/issue-7-api-contract.md`
- **ERD :** `docs/erd.md`
- **Décision issue #6 :** `docs/decisions/category-ownership.md`
- **Backend :** `backend/cashmire/urls.py`, `backend/api/urls.py`, `backend/api/views.py`

---

*Document produit par spécification issue #7. Source de vérité pour tous les développeurs (frontend/backend, clients externes). À jour : 2026-10-06.*
