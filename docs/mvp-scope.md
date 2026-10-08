# Périmètre du MVP Cashmire

Ce document définit le périmètre du minimum viable product (MVP) de Cashmire pour le projet de 4 jours. Il énumère les fonctionnalités incluses, explicitement exclues, et les contraintes architecturales qui lient tous les travaux futurs. Tout document de spécification de fonctionnalité doit s'y référer et rester dans ce périmètre.

---

## Utilisateurs cibles et leur contexte

### Profil des utilisateurs

Cashmire adresse deux catégories principales :

1. **Les trackers individuels** : Personnes souhaitant suivre leurs dépenses personnelles de manière simple, comprendre leur consommation par catégorie (alimentation, transport, divertissement, etc.) et respecter des budgets qu'elles se fixent.

2. **Les apprenants en développement** : Étudiants utilisant Cashmire comme projet fil rouge pour apprendre les bases du développement full-stack (authentification, CRUD, gestion de données financières simples, déploiement Docker).

### Problème résolu

Les utilisateurs cibles manquent d'un outil simple et transparent pour enregistrer leurs dépenses et comprendre leur impact sur un budget. Ils veulent :
- Une interface directe, sans complexité multi-utilisateurs ou intégrations bancaires ;
- Une garantie de confidentialité et une compréhension claire de ce qui se passe avec leurs données ;
- Un codebase accessible et documenté, utile comme matériel pédagogique.

### Ce qui ne résout pas le MVP

Le MVP **ne couvre pas** :
- Les foyers multi-utilisateurs ou budgets partagés ;
- Les connexions bancaires ou importation automatique de transactions ;
- La gestion de plusieurs monnaies ou la conversion de devises ;
- Les dépenses récurrentes ou la projection de budget ;
- Les rapports détaillés ou l'export de données ;
- L'accès mobile natif (une interface web responsive couvre cet usage).

---

## Parcours utilisateur central

Le flux central du MVP, qui représente la raison d'être du produit, est :

**1. Connexion**
L'utilisateur accède à Cashmire et se connecte avec ses identifiants (adresse email + mot de passe). Le système valide les identifiants et établit une session. *À confirmer par l'équipe* : la création de compte est-elle automatique ou faut-il une vérification par email avant activation ?

**2. Saisie d'une dépense**
L'utilisateur navigue vers un formulaire de nouvelle dépense. Il renseigne :
- Le montant (par exemple : 15,50 euros) ;
- Une catégorie (par exemple : Alimentation) ;
- Une date (implicitement aujourd'hui, modifiable) ;
- Une description optionnelle (par exemple : « Marché »).

Il confirme. Le système enregistre la dépense avec le montant en type `Decimal` pour éviter les erreurs de précision.

**3. Visualisation de l'impact sur les budgets**
L'utilisateur accède à son tableau de bord. Il voit :
- Pour chaque budget qu'il a défini (par catégorie, par exemple « Alimentation : 200 € par mois ») :
  - La consommation actuelle (exemple : 45 € dépensés sur 200 € de budget)
  - Une barre de progression ou un pourcentage ;
  - Un signal visuel : vert si < 80 %, jaune si 80-99 %, rouge si ≥ 100% ;
  - Un libellé textuel (par exemple « Dépassé » en cas de consommation ≥ 100%), car la couleur seule ne suffit pas (accessibilité).

**4. Alerte de dépassement (optionnel)**
Si l'utilisateur a franchi le seuil d'alerte à 80 % ou le dépasse complètement à 100 %, le tableau de bord l'affiche de manière évidente. *À confirmer par l'équipe* : alertes dashboard uniquement, ou notifications in-app supplémentaires ?

**Fin du parcours central** : L'utilisateur comprend combien il a dépensé, dans quelle catégorie, et quel impact cela a sur ses budgets.

---

## Fonctionnalités incluses dans le MVP

### 3.1 Authentification et comptes

**Objectif** : Les utilisateurs peuvent créer un compte et se connecter en toute sécurité.

**En périmètre** :
- Création de compte : inscription avec adresse email et mot de passe ;
- Après inscription, l'utilisateur se connecte séparément. La réponse
  d'inscription reste neutre afin de ne pas révéler si l'adresse existe
  déjà (issue #146, décision 0006) ;
- Connexion : validation des identifiants et établissement d'une session ;
- Déconnexion : fermeture sécurisée de la session ;
- Validation des mots de passe : application des validateurs Django (longueur minimale, forces, etc.).

**À confirmer par l'équipe** :
- Vérification d'email avant activation (non pour le MVP, inscrit dans le backlog post-MVP) ;
- Réinitialisation de mot de passe (recommandation : « Contacter le support » pour le MVP, feature post-MVP).

**Modèle de données** (informationnel) :
- Table `User` avec : adresse email (unique), hash du mot de passe (jamais du texte brut), dates de création et modification.

**API** :
- `POST /api/auth/register/` — création de compte ;
- `POST /api/auth/login/` — connexion ;
- `POST /api/auth/logout/` — déconnexion.

**Sécurité** :
- Mots de passe toujours hashés, jamais stockés en texte brut ;
- Protection CSRF sur les formulaires ;
- Rate limiting de 5 requêtes/minute/IP sur login et inscription ; les
  limites partagées par IP et l'absence de protection contre les attaques
  distribuées sont documentées dans les décisions 0004 et 0006 ;
- Aucun mot de passe ne sort dans les logs ou les réponses API.

**Accessibilité** :
- Formulaires avec libellés associés (`<label>`) ;
- Messages d'erreur clairs ;
- Navigation au clavier ;
- Focus visible sur chaque champ.

---

### 3.2 Gestion des dépenses

**Objectif** : Les utilisateurs enregistrent et visualisent leurs transactions.

**En périmètre** :
- Créer une dépense : montant (Decimal, validé ≥ 0), description, catégorie, date ;
- Lister les dépenses (récentes, toutes ou filtrées par catégorie/plage de dates : *à confirmer*) ;
- Consulter une dépense ;
- Modifier une dépense ;
- Supprimer une dépense ;
- Pas de pièces jointes, pas d'images, pas de partage de dépenses individuelles.

**Modèle de données** :
- Table `Expense` avec : montant (type `NUMERIC`/`Decimal`, obligatoire), description, référence à la catégorie, date, propriétaire (clé étrangère vers `User`), dates de création/modification ;
- Les dépenses sont triées par date décroissante ;
- **Propriété** : l'utilisateur A ne peut jamais voir ou modifier les dépenses de l'utilisateur B.

**API** :
- `POST /api/expenses/` — créer ;
- `GET /api/expenses/` — lister (optionnellement paginées) ;
- `GET /api/expenses/{id}/` — consulter une ;
- `PATCH /api/expenses/{id}/` — modifier ;
- `DELETE /api/expenses/{id}/` — supprimer ;
- Tous les endpoints requièrent l'authentification. Réponse 403 Forbidden si l'utilisateur tente d'accéder à une dépense d'un autre.

**Cas d'erreur** :
- 400 Bad Request : montant négatif, format Decimal invalide, catégorie inexistante, date invalide ;
- 401 Unauthorized : absence de session/token ou token invalide ;
- 403 Forbidden : tentative de modification d'une dépense d'un autre utilisateur ;
- 404 Not Found : dépense inexistante.

**Accessibilité** :
- Formulaires navigables au clavier ;
- Libellés explicites ;
- Messages d'erreur clairs et associés aux champs.

---

### 3.3 Gestion des budgets

**Objectif** : Les utilisateurs définissent des limites de dépenses et voient leur consommation ; l'application les alerte en cas de dépassement ou approche du seuil.

**En périmètre** :
- Définir un budget (montant, lié à une catégorie spécifique ou global : *à confirmer par l'équipe*) ;
- Choisir une période (*à confirmer* : mensuelle, annuelle, roulement de 30 jours ? Recommandation : mensuelle uniquement pour garder le MVP compact) ;
- Visualiser la consommation : montant dépensé / limite en ratio ou pourcentage ;
- Alerter visuellement si :
  - Consommation ≥ 80 % du budget (avertissement) ;
  - Consommation ≥ 100 % (dépassement) ;
- Pas de prévisions complexes, pas de report d'année sur l'autre, pas de budgets partagés entre utilisateurs.

**Modèle de données** :
- Table `Budget` avec : montant (type `NUMERIC`/`Decimal`), catégorie optionnelle (clé étrangère vers `Category`, peut être null), période (enum : « month », « year », etc.), propriétaire (clé étrangère vers `User`), dates de création/modification ;
- Les seuils d'alerte (80 %, 100 %) sont codés en dur ; aucune configuration par utilisateur.

**API** :
- `POST /api/budgets/` — créer ;
- `GET /api/budgets/` — lister (scoped à l'utilisateur connecté) ;
- `PATCH /api/budgets/{id}/` — modifier ;
- `DELETE /api/budgets/{id}/` — supprimer ;
- `GET /api/budgets/{id}/status/` ou endpoint similaire (*à confirmer*) — retourner la consommation.

**Signaux UI** :
- Tableau de bord affichant chaque budget avec barre de progression ou pourcentage ;
- Code couleur : vert (< 80 %), jaune (80-99 %), rouge (≥ 100 %) ;
- Texte en complément (« Dépassé ») car la couleur seule est insuffisante.

**Accessibilité** :
- La couleur ne véhicule jamais seule l'information ;
- Les barres de progression ont des labels accessibles (ARIA).

---

### 3.4 Catégories

**Objectif** : Les utilisateurs organisent les dépenses par type (alimentation, transport, divertissement, etc.).

**En périmètre** :
- Une liste prédéfinie de catégories (Alimentation, Transport, Divertissement, Utilitaires, Santé, Restaurants, Achats, Autre ; liste exacte : *à confirmer par l'équipe*) ;
- Les utilisateurs ne peuvent **pas** créer de catégories personnalisées (hors MVP, feature backlog) ;
- Les catégories sont identiques pour tous (pas de personnalisation) ;
- Chaque dépense doit être assignée à exactement une catégorie.

**Modèle de données** :
- Table `Category` avec : nom (unique), couleur optionnelle (pour l'UI) ;
- Pas de champ propriétaire : les catégories sont globales.
- `Expense.category` est obligatoire (NOT NULL).

**API** :
- `GET /api/categories/` — lister toutes les catégories (aucune authentification requise ; données statiques/publiques) ;
- Pas de création, modification ou suppression de catégories via l'API dans le MVP.

---

### 3.5 Page de confidentialité et mentions légales

**Objectif** : Les utilisateurs comprennent quelles données l'app collecte et comment elles sont protégées.

**En périmètre** :
- Page statique `/privacy` accessible sans authentification ;
- Décrit : aucune donnée personnelle collectée actuellement, base de données configurée mais non peuplée, pas de cookies, aucune intégration tierce ;
- Liste ce qui est **prévu** (comptes, dépenses, budgets, catégories) en temps futur ;
- Divulgue les paramètres par défaut non sécurisés (DEBUG=true, etc.) ;
- Contient des placeholders visibles pour les informations légales (entité, contact, juridiction, date d'entrée en vigueur) jusqu'à approbation humaine ;
- Accessible sans login et sans requête réseau ;
- Applique la décision `0002` : chaque affirmation doit être vérifiable contre le code.

**Techniquement** :
- Aucune route backend ajoutée ;
- Contenu statique, côté frontend ;
- Voir `docs/specs/issue-63-privacy-page.md` pour les détails complets d'implémentation.

---

### 3.6 Sécurité

**Objectif** : Protéger les données utilisateur et l'intégrité de l'application.

**En périmètre** :
- Hash des mots de passe (bcrypt ou PBKDF2 de Django) ;
- Tokens CSRF sur tous les formulaires modifiant l'état ;
- Protection SQL injection via ORM Django (requêtes paramétrées) ;
- Requêtes scopées par utilisateur : l'utilisateur A ne peut jamais accéder aux données de l'utilisateur B via manipulation d'API ;
- CORS : par défaut, seul le frontend local (`http://localhost:5173`) est autorisé (décision `0002`) ;
- Rate limiting sur les endpoints d'authentification (*limites à confirmer par l'équipe*) ;
- Pas de données sensibles dans les logs, erreurs ou réponses API (notamment pas de stack traces).

**Hors périmètre MVP** :
- Terminaison TLS/HTTPS (infrastructure de déploiement, non l'application) ;
- OAuth / authentification par réseaux sociaux ;
- Authentification multi-facteurs ;
- Chiffrement au repos (DB non chiffrée en développement) ;
- Sauvegarde et récupération après sinistre ;
- Pentest.

**Responsabilité** : L'agent Full-Stack Development implémente ; l'agent QA & Security vérifie.

---

### 3.7 Accessibilité

**Objectif** : L'app est utilisable par tous, conformément à WCAG 2.1 niveau AA.

**En périmètre** :
- Tous les formulaires ont des éléments `<label>` associés ;
- Tous les images et icônes ont du texte alternatif (`alt`) descriptif ;
- La couleur ne véhicule jamais seule l'information (ex. alerte « Dépassé » + rouge) ;
- Ratio de contraste ≥ 4,5:1 pour le texte normal, ≥ 3:1 pour le texte large ;
- Tous les éléments interactifs navigables au clavier ; le focus toujours visible ;
- Vrais éléments de titre (`<h1>`, `<h2>`, etc.), pas de divs stylisés ;
- Messages d'erreur clairs et associés aux champs ;
- Landmarks : une `<main>` par page, `<footer>` pour les liens globaux ;
- Lisible à 200 % de zoom sans scroll horizontal ;
- Support du reflow et de l'espacement du texte sur mobile et grand zoom.

**Responsabilité** : Full-Stack Development implémente ; QA & Security et Clément (accessi­bilité) vérifient.

---

### 3.8 Infrastructure Docker

**Objectif** : Chaque membre de l'équipe lance la stack complète localement en une commande.

**En périmètre** :
- `docker-compose.yml` définit les services : API Django, frontend SvelteKit, base PostgreSQL ;
- `docker compose up -d --build` démarre la stack ;
- `docker compose down` l'arrête proprement ;
- Serveurs de développement Django et SvelteKit exécutés dans les containers ;
- Variables d'environnement via `.env` (jamais commitées ; `.env.example` versionnée) ;
- Schéma DB créé par migrations Django (`docker compose exec api python manage.py migrate`) ;
- Frontend avec la stack SvelteKit (Vite).

**Hors MVP** :
- Kubernetes, manifests de production, pipelines CI/CD, agrégation de logs ;
- Health checks ou politiques de redémarrage automatique (nice-to-have futur).

---

## Hors périmètre MVP

Les fonctionnalités suivantes sont **explicitement exclues** du MVP et adressées post-MVP, sauf demande spécifique de l'équipe :

| Fonctionnalité | Raison de l'exclusion | Revisiter quand |
|---|---|---|
| Foyers multi-utilisateurs / budgets partagés | Modèle de permissions complexe, synchronisation temps réel. Les bases single-user d'abord. | Flux single-user stable et validé. |
| Intégration bancaire (Plaid, etc.) | OAuth, gestion d'identifiants tierce, données personnelles sensibles. Complexité importante. | Phase post-MVP 2. |
| Application mobile native | Équivalent en effort à l'app web. Design responsive couvre l'accès mobile. | Si MVP web réussit. |
| Plusieurs devises | Taux de change, règles d'arrondi, localisation. Non nécessaire pour un MVP anglophone. | Post-MVP si expansion internationale. |
| Dépenses récurrentes / factures | Pratique mais non critique pour lancement initial. Peut être ajouté progressivement. | Backlog fonctionnalités. |
| Notifications email | Configuration SMTP, templates, désinscription. Les alertes dashboard suffisent. | Feature d'engagement post-MVP. |
| Export de données (CSV, PDF) | Dépassé un sprint de 4 jours. Peut être ajouté. | Backlog. |
| Tableau de bord admin / rapports | Focus sur features utilisateur. Outils admin secondaires. | Post-MVP si besoin opérationnel. |
| Thèmes personnalisables / dark mode | Pratique mais non essentiel. Une interface claire suffit. | Phase polish futur. |
| Mode hors ligne / Progressive Web App | Requires service workers, sync. Non nécessaire pour prototype. | Futur si mobile prioritaire. |

---

## Contraintes et décisions architecturales

### Contraintes permanentes

1. **Valeurs monétaires toujours en Decimal/NUMERIC** (cf. `product-architecture.md`)
   Chaque champ monétaire (montant d'une dépense, limite d'un budget) utilise PostgreSQL `NUMERIC` ou Django `DecimalField`, jamais `FloatField`. Cette règle est non-négociable et s'applique à tous les modèles futurs.

2. **Page de confidentialité à jour** (cf. `docs/decisions/0002`)
   Toute PR ajoutant collecte de données, authentification ou intégration tierce doit mettre à jour `/privacy` dans la même PR. La page ne peut pas devenir fausse.

3. **Coquille d'app minimale** (cf. `docs/decisions/0001`)
   La layout partagée (`+layout.svelte`) reste minimale : footer + contenu de page. Pas de header, nav, design system ou `src/lib/` anticipés. Les nouveaux éléments d'UI chrome sont ajoutés quand une page en a besoin, pas par anticipation.

4. **Stack fixe**
   Django + Django REST Framework, SvelteKit, PostgreSQL, Docker Compose. Aucune substitution proposée ou acceptée.

5. **Périmètre MVP est la frontière**
   Chaque spec de fonctionnalité doit référencer ce document et rester dedans. L'agent Product & Architecture l'utilise pour bloquer le scope creep.

---

## Succès du MVP

Le MVP est **terminé** lorsque :

1. **Toutes les sept fonctionnalités** (3.1–3.7) sont implémentées et testées.
2. **L'infrastructure Docker** (3.8) est en place et fonctionne (`docker compose up -d --build`).
3. **La page de confidentialité** est revue et approuvée par un humain (décision `0002`).
4. **Tous les critères d'acceptation** des specs de fonctionnalités passent (vérification humaine).
5. **Aucun défaut de sécurité** classé OWASP Top 10 ou équivalent n'est irésolu.
6. **Accessibilité WCAG 2.1 AA** : la checklist manuelle (section 3.7) est complète.
7. **Pas de secret commité** : `.env` ne contient aucune clé réelle ; `.env.example` a des placeholders.
8. **Tous les tests passent** : test suite backend (`manage.py test`) et frontend (`npm test`), si implémentés.

---

## Décisions ouvertes pour l'équipe

Les questions suivantes doivent être résolues (ou explicitement marquées TBD dans les specs correspondantes). Elles n'empêchent pas la progression mais guident les choix de modélisation :

| Question | Importance | Recommandation MVP |
|---|---|---|
| **Vérification d'email** | Affecte la complexité d'auth. | Inscription immédiate (vérif email post-MVP). |
| **Granularité des budgets** | Par catégorie uniquement ou global aussi ? Récurrents ou à la demande ? | Par catégorie uniquement, mensuel, TBD global. |
| **Liste des catégories** | Quels 6-8 types de base ? | Alimentation, Transport, Divertissement, Utilitaires, Santé, Restaurants, Achats, Autre (TBD). |
| **Alertes** | Dashboard uniquement ou notifications in-app/email aussi ? | Dashboard (couleur + texte) ; post-MVP pour notifications. |
| **Rate limiting** | Limites exactes par endpoint ? | TBD : l'équipe décide nombres et durées. |
| **Réinitialisation de password** | Incluse ou « contacter le support » ? | Contacter support (post-MVP). |

---

## Références et documents liés

- `docs/team.md` — rôles et responsabilités de l'équipe.
- `docs/decisions/0001-shared-app-shell-layout.md` — règle de layout.
- `docs/decisions/0002-privacy-claims-must-be-code-verifiable.md` — règle de vérifiabilité des données.
- `docs/specs/issue-63-privacy-page.md` — détails complets de la page confidentialité.
- `README.md` — mise en route et migrations.
- `.github/agents/product-architecture.md` — comment cet agent utilise le périmètre MVP.
