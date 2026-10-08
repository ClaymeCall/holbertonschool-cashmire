# Revue QA & sécurité de l'application entière (issue #58)

Branche : `docs/58-qa-security-review` (à jour avec `main`, commit `38de673`).
Revue statique + exécution des suites de tests. Aucun fichier source modifié.

## Scope et contraintes

- Backend Django/DRF (`backend/`) et frontend Svelte/Vite (`frontend/`).
- Grille : OWASP Top 10 (XSS, injection, contrôle d'accès, auth/session/CSRF, fuite d'informations), validation, accessibilité (labels, clavier, focus, contraste), fiabilité.
- Le ticket #58 n'a pas de critères d'acceptation chiffrés : la revue est un balayage, les résultats ne sont donc pas « par critère ».
- Contraintes respectées : aucun fichier de `backend/`, `frontend/` ou de migration modifié ; `docs/agentic-log.md` non touché ; aucune commande destructive.
- Contexte repris : `issue-57-route-audit.md` (G1 à G5, vérifiés, voir plus bas). Ce fichier n'existe pas sur cette branche, il n'est que sur `docs/57-route-audit` / `origin/docs/57-route-audit`.
- Hors périmètre : déploiement réel (aucune infra inspectée), tests navigateur automatisés, reproduction dynamique des points marqués « à reproduire ».

## Résultats des tests

| Suite | Commande | Résultat |
|---|---|---|
| Backend | `docker compose run --rm api python manage.py test api` | **OK**, 215 tests, 0 échec (34,5 s). Le traceback « Unhandled API exception » dans la sortie est attendu : c'est `api/tests/test_errors.py`, qui vérifie justement le log serveur. |
| Frontend | `npx vitest run` (équivalent de `npm test`, `node_modules` déjà présent, `npm ci` non relancé) | **OK**, 20 fichiers, 134 tests, 0 échec. Des logs `console.error` attendus dans les tests de santé. |
| Dépendances prod | `npm audit --omit=dev` | 0 vulnérabilité. |
| Docker | `docker compose down` | Fait. |

Non exécuté : `pip-audit` (non installé), lint, audit automatisé d'accessibilité (axe) et tests navigateur (rendu, focus, responsive mobile/desktop). Les points « à reproduire » ci-dessous ne sont pas confirmés dynamiquement.

## Findings blocking

### B1. Texte des cartes budget sous le contraste WCAG AA selon le statut
- **Sévérité** : blocking (WCAG 1.4.3, texte courant < 4,5:1). À confirmer par l'équipe.
- **Fichier** : `frontend/src/lib/components/BudgetsList.svelte:125` (`<li class={meta.className}>`), styles `:196-214` (`.status-ok`, `.status-warning`, `.status-full`, `.status-exceeded` règlent `color` sur le `li`).
- **Cause** : la classe de statut définit `color` sur le `li`, et tout le texte de la carte (nom de catégorie, montants, libellé de statut) en hérite. La couleur censée n'être qu'un accent de bordure devient la couleur du texte.
- **Ratios calculés** (fond ivoire `#f7f2e9`, formule WCAG) :
  - ok `#6e8f68` : **3,25:1**
  - warning `#d1a24a` : **2,10:1**
  - full `#a8632a` : **4,20:1**
  - exceeded `#b4543c` : **4,41:1**
  - Seuil requis : 4,5:1. Les quatre statuts échouent.
- **Reproduction** : afficher `/budgets` avec un budget dont `status = "warning"` (mock ou API), inspecter le `li` puis le `.category`, lire `getComputedStyle(...).color` : `rgb(209, 162, 74)` sur fond `rgb(247, 242, 233)`.
- **Correctif attendu** (à faire par le Full-Stack agent) : garder `color: var(--color-text)` sur le contenu et ne réserver la couleur de statut qu'à `border-left-color`, au remplissage de la barre et à l'icône (le libellé texte est déjà présent, donc l'information reste disponible).

## Findings non-blocking

### N1. Login CSRF sur `/api/auth/login/`
- **Fichier** : `backend/api/views.py:50-52` (`LoginView`, pas de `authentication_classes`), `:86-87`.
- **Cause** : `SessionAuthentication` n'impose le CSRF que si un utilisateur est déjà authentifié par session. `LoginView` est anonyme, donc aucun contrôle CSRF. Les parsers par défaut de DRF incluent `FormParser`, donc un `<form method=post>` cross-site en `application/x-www-form-urlencoded` passe sans preflight.
- **Impact** : un site tiers peut ouvrir une session dans le navigateur de la victime sur un compte contrôlé par l'attaquant (login CSRF). Atténuation : `SameSite=Lax` par défaut, et la session résultante n'expose pas de donnée de la victime.
- **À reproduire** : `curl -i -X POST -H 'Content-Type: application/x-www-form-urlencoded' -d 'email=...&password=...' http://localhost:8000/api/auth/login/` sans cookie ni `X-CSRFToken` : attendu 200 + `Set-Cookie: sessionid`. Puis valider le scénario de formulaire cross-site dans un navigateur.
- **Proposition** : restreindre les parsers à JSON sur les vues auth, ou documenter le risque dans `docs/decisions/0003` comme limite connue.

### N2. Énumération d'emails à l'inscription (G4 confirmé)
- **Fichiers** : `backend/api/models.py:50` (`email = EmailField(unique=True)`), `backend/api/serializers.py:43-61` (`RegisterSerializer`, validation d'unicité auto de DRF), `backend/api/views.py:32-43` (`RegisterView`, sans `throttle_classes`).
- **Reproduction** : `POST /api/auth/register/` avec un email existant → 400 `{"email": ["user with this email already exists."]}` (libellé exact à confirmer), contre 201 pour un email nouveau. Aucun throttle, donc énumération automatisable. Contraste avec le login, qui renvoie un 401 identique (AC-2). Le frontend affiche ce message tel quel (`routes/register/+page.svelte:65-78`).
- **Proposition** : message générique côté register, plus throttle, ou acceptation documentée pour le MVP (cohérent avec G4).

### N3. Throttle de login en mémoire locale par process
- **Fichier** : `backend/cashmire/settings.py` (aucune section `CACHES`, donc `LocMemCache` par défaut).
- **Impact** : avec plusieurs workers (gunicorn, uwsgi), la limite « 5/min » devient « 5/min par worker ». Le throttle est par IP et sans compte, déjà documenté dans `docs/decisions/0004`.
- **Proposition** : cache partagé (Redis/Memcached) avant toute mise en production.

### N4. Durcissement de configuration absent
- **Fichier** : `backend/cashmire/settings.py` : `SECRET_KEY` a un repli connu `"dev-insecure-secret-key"` (ligne 28), `ALLOWED_HOSTS` vaut `*` par défaut, aucun `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE`, aucun `SECURE_HSTS_SECONDS` / `SECURE_SSL_REDIRECT`. `backend/cashmire/urls.py:6` expose `/admin/`. `/api/schema/` et `/api/docs/` sont publics (G2).
- **Reproduction** : `DJANGO_DEBUG=false` sans `DJANGO_SECRET_KEY` → le serveur démarre avec la clé connue, donc des cookies de session forgeables.
- **Proposition** : échouer au démarrage si `DJANGO_SECRET_KEY` est absent hors `DEBUG`, activer les flags secure en production, restreindre `/admin/` et la doc hors dev. `.env` est ignoré par git (`.gitignore:13`), ce qui est correct.

### N5. Codes 403 vs 401 selon la route (G1 confirmé)
- **Fichiers** : `backend/api/views.py` lignes 275-276, 294-295, 352-353, 485-486, 694-695 (`SessionAuthentication` sans `authenticate_header`) ; `backend/api/auth.py` (`SessionCookieAuthentication` renvoie 401, utilisé par `auth/me` et `auth/logout`).
- **Reproduction** : `curl -i http://localhost:8000/api/expenses/` anonyme → 403 ; `curl -i .../api/auth/me/` → 401.
- **Impact** : le frontend traite 401 comme « non connecté » dans `auth.svelte.js`, mais les pages métier affichent un message générique pour 403. Incohérence, pas de faille.

### N6. Format d'erreur incohérent (G5 confirmé)
- **Fichiers** : `backend/api/views.py:621` et `:725` renvoient `serializer.errors` brut en 400 ; les autres erreurs suivent `{error, message}`. Le frontend gère les deux (`BudgetForm.svelte:83-95`).

### N7. Emails différant par la casse
- **Fichier** : `backend/api/serializers.py` (pas de normalisation de l'email), `models.py:50`.
- **Reproduction** : register `Jane@x.test` puis `jane@x.test` → 201 deux fois (deux comptes), et login sensible à la casse de la partie locale. Non bloquant, mais source de confusion.

### N8. Courses à l'inscription : 500 possible au lieu de 400
- **Fichiers** : `serializers.py:24-40` (`generate_unique_username`, check puis create), `views.py:32-43`.
- **Impact** : deux inscriptions concurrentes avec le même email ou le même username dérivé déclenchent un `IntegrityError` non géré → 500 générique (`sanitized_exception_handler`). Pas de fuite, mais fiabilité.
- **À reproduire** : requêtes concurrentes (non exécuté).

### N9. Seuil d'alerte vide bloque le formulaire budget alors que le champ est optionnel
- **Fichiers** : `frontend/src/lib/components/BudgetForm.svelte:65-72` (validation : `isValidDecimalString("")` est faux, donc erreur « must be between 0 and 100 ») ; `:196` (hint « Defaults to 80 »).
- **Reproduction** : vider le champ « Alert threshold » puis soumettre → erreur côté client, aucune requête. Écart avec le hint et avec le backend, qui accepte l'omission.

### N10. Focus perdu à la soumission et pas de focus sur l'erreur
- **Fichiers** : `frontend/src/routes/login/+page.svelte:109-128` (champs et bouton `disabled` pendant `submitting`), `FormError.svelte:13` (`role="alert"` seul, sans déplacement de focus).
- **À reproduire** : Tab jusqu'à « Log in », Entrée avec un mot de passe faux → vérifier `document.activeElement` après le désactivation du bouton (attendu : `body`). Même schéma sur register, budgets et expenses.

### N11. Erreurs de formulaire non reliées aux champs
- **Fichiers** : `frontend/src/lib/components/TextField.svelte:32-35` (hint sans `id`, pas d'`aria-describedby`, pas d'`aria-invalid`) ; `BudgetForm.svelte:142-208` et les pages expenses/register (même schéma).

### N12. HTTP 429 affiché comme « Couldn't reach Cashmire »
- **Fichier** : `frontend/src/routes/login/+page.svelte:70-86` : seuls 401, 400 et timeout ont un message dédié ; le 429 du throttle tombe dans le message réseau.
- **Reproduction** : 6 tentatives de login rapides → message « Couldn't reach Cashmire » alors que le serveur répond. Message trompeur, pas de fuite.

### N13. Libellés de liens répétés « Edit »
- **Fichiers** : `frontend/src/lib/components/ExpensesList.svelte:90`, `BudgetsList.svelte:146`. Plusieurs liens « Edit » identiques sans contexte (WCAG 2.4.4). Ajouter un `aria-label` ou un texte masqué avec la catégorie.

### N14. Barre de progression sans `aria-valuetext`
- **Fichier** : `BudgetsList.svelte:136-143` : `aria-valuenow="47.0"` sans unité ni texte. Ajouter `aria-valuetext` (ex. « 47 % consommé »).

### N15. Navigation mobile : pas de touche Échap, pas de lien d'évitement
- **Fichiers** : `frontend/src/lib/components/Navbar.svelte:123-139` (menu avec `aria-expanded`/`aria-controls` OK, mais aucun `keydown` Échap, pas de retour de focus). `+layout.svelte` : pas de « Aller au contenu ».

### N16. Informations internes visibles côté utilisateur
- **Fichiers** : `frontend/src/routes/health/+page.svelte` affiche l'URL de l'API et le statut HTTP (page publique, faible impact) ; `frontend/src/routes/+error.svelte:24` affiche `$page.error.message` brut, donc un message d'erreur JS interne peut apparaître à l'écran.

### N17. Fichiers « * 2.py » non suivis dans `backend/`
- **Fichiers** : `backend/api/auth 2.py`, `serializers 2.py`, `tests/__init__ 2.py`, `tests/test_current_user 2.py`, `tests/test_expenses 2.py`, `tests/test_login 2.py`, `tests/test_logout 2.py` (`git status`).
- **Constat** : `auth`, `serializers`, `test_login`, `test_logout`, `test_current_user` et `__init__` sont identiques aux originaux. `test_expenses 2.py` est **en retard** : il n'a pas le test `test_category_filter_rejects_sql_injection_payload` (issue #61) présent dans `test_expenses.py`. Ces fichiers ne sont pas importés (nom invalide pour unittest). À supprimer par l'auteur, sans commit. Je ne les ai pas touchés.

### N18. Commentaire obsolète dans le client budgets
- **Fichier** : `frontend/src/lib/api/budgets.js:4-7` affirme que les endpoints budgets ne sont pas mergés sur `main`. C'est faux : `backend/api/views.py` et `urls.py` les exposent. Doc drift, sans impact runtime.

### N19. Pas de limite de taille sur `description`
- **Fichiers** : `backend/api/models.py:95` (`TextField`), `serializers`/`views.py` (`ExpenseCreateSerializer.description` sans `max_length`), frontend sans `maxlength`. Faible risque (DoS par volume), à borner.

### N20. Page d'édition de dépense : chargement de toute la liste
- **Fichier** : `frontend/src/routes/expenses/[id]/edit/+page.svelte:38-62` charge `listExpenses()` complet pour retrouver un id (pas de GET détail côté API). Sans impact sécurité, coût qui croît avec le nombre de dépenses.

## Faux positifs / vérifié OK

- **XSS (#60)** : aucun `{@html}`, `innerHTML`, `outerHTML`, `eval`, `new Function` dans `frontend/src` (hors tests). Les données utilisateur (description, nom de catégorie, messages d'erreur serveur) sont rendues en texte échappé. `BudgetsList.svelte:144` interpole `percentForBar()` dans un `style` : valeur numérique produite par `money.js` à partir de chaînes serveur, pas de vecteur d'injection. **Le ticket #60 reste donc ouvert au niveau process, mais aucun sink XSS n'est présent dans le code actuel.**
- **Stockage des identifiants** : aucun `localStorage` / `sessionStorage` / token dans le frontend. L'auth repose sur le cookie `sessionid` (HttpOnly par défaut Django, non lisible par JS). `csrftoken` est lisible par JS par conception (`api.js:104-113`).
- **CSRF** : `apiFetch` envoie `X-CSRFToken` sur POST/PUT/PATCH/DELETE (`api.js:173-178`). Les vues expenses/budgets/categories utilisent `SessionAuthentication`, donc le contrôle est actif. `test_logout.py` teste le refus sans token avec `enforce_csrf_checks=True`.
- **Injection SQL** : aucun SQL brut (`raw`, `cursor`, `extra`, `RawSQL`, `execute`) dans `backend/` hors tests. Le test #61 est présent dans `test_expenses.py` (voir N17).
- **Contrôle d'accès et IDOR** : toutes les lectures et écritures expenses/budgets sont filtrées par `user` (`views.py:325` `get_user_expense_or_404`, `Budget.objects.get(id, user=...)`, `Category.objects.get(id, user=...)`). Les catégories sont vérifiées par utilisateur (`serializers.py` / `views.py:199, 232`). 215 tests backend passent, dont 154 sur les budgets.
- **Entiers hors plage dans les filtres** (`category_id=10**30`) : Django 5.1.3 (`requirements.txt`) renvoie un résultat vide pour les lookups d'entiers hors plage sans lever d'erreur. Non exécuté, déduit de la version.
- **Open redirect** : `goto()` n'utilise que des chemins constants (`/`, `/login`, `/expenses`, `/budgets`). La navigation protégée (`Navbar.svelte:79-82`) n'est qu'une garde UX : le serveur refuse les requêtes anonymes.
- **Fuite d'erreurs** : `sanitized_exception_handler` (`api/exceptions.py`, #62) renvoie un 500 générique, la trace va dans les logs ; `DJANGO_DEBUG` vaut `false` par défaut ; `test_errors.py` est vert.
- **Énumération au login** : `LoginView` renvoie le même 401 pour email inconnu et mauvais mot de passe, et `authenticate()` couvre le cas timing (`views.py:58-63`). Le frontend affiche un message générique (`login/+page.svelte:70-73`).
- **Hachage des mots de passe** : `set_password` (`serializers.py:102`), chaîne `AUTH_PASSWORD_VALIDATORS` complète côté serveur (`serializers.py:84-93`).
- **Montants** : aucune coercion numérique des montants (`Number`, `parseFloat`) dans le frontend. Les seuls `Number()` concernent des identifiants (`categoryId`, `expenseId`, `budgetId`). `money.js` utilise `BigInt`.
- **Dépendances** : `npm audit --omit=dev` : 0 vulnérabilité.
- **Contrastes vérifiés OK** (texte, fond ivoire / surface sombre) : texte muté `#7d6854` sur fond 4,73:1 ; lien/mocha 6,79:1 ; bouton ivoire sur `#8f5f26` 4,91:1 ; erreur 7,51:1 ; statut « full » sur fond 8,01:1 ; ochre texte sur fond ochre 7,76:1 ; mode sombre (texte sage 6,74:1, camel 6,72:1, oatmeal 13,04:1). Non-texte : bordure d'input `#8d7a68` 3,68:1 (≥ 3:1) ; anneau de focus 4,91:1.
- **Labels de formulaire** : tous les `TextField` ont `<label for>` ; les `<select>` de `BudgetForm.svelte:145`, `expenses/new` et `expenses/[id]/edit` aussi.
- **Focus visible** : `base.css:71-76` couvre `a`, `button`, `input` ; les `select` ont leur propre `:focus-visible` dans `BudgetForm.svelte:229`.
- **Mouvement réduit** : `base.css:78-83` (`prefers-reduced-motion`).
- **Document** : `lang="en"` et `viewport` présents (`app.html`). Icônes décoratives masquées (`aria-hidden` automatique, `Navbar.svelte:51-55`). Image d'erreur `alt=""` (décorative).
- **Statut G1 à G5** : G1, G2, G3, G4, G5 toujours valides (voir N5, N4, N4, N2, N6). Aucun n'est nouveau.
- **Route audit #57 sur cette branche** : le document n'est pas présent dans cette branche ; son contenu est repris via `docs/57-route-audit`.
