# Revue — Issue #4 : documenter le périmètre MVP

## Résumé

Révision de `docs/mvp-scope.md` contre la spécification `docs/specs/issue-4-mvp-scope.md` et les critères d'acceptation (AC-1 à AC-8). Le document est complet, bien structuré et conforme aux exigences du projet.

---

## Findings bloquants

Aucun.

---

## Findings non bloquants

### 1. Longueur légèrement supérieure à la recommandation

**Constat :** Le document contient 2 844 mots (mesurés via `wc -w`), dépassant légèrement la fourchette recommandée de 1 500–2 500 mots (AC-8 de la spec issue-4).

**Analyse :** Le dépassement est minimal (~13%) et justifié par la richesse du contenu. Chaque section ajoute une valeur : les sous-sections 3.1–3.8 précisent les responsabilités par domaine, les "Décisions ouvertes" énumèrent explicitement les questions en attente. Aucune section n'apparaît redondante ou ornementale.

**Vérification :** Lecture complète ; aucune répétition ni contenu hors-sujet détecté.

**Suggestion :** Acceptable tel quel. Si la concision est requise ultérieurement, condenser les subsections sans supprimer les détails critiques (validateurs de mot de passe, codes d'erreur HTTP, etc.).

---

### 2. Clarification du ton sur les affirmations futures

**Constat :** Plusieurs sections énoncent des fonctionnalités en termes de présent ("Le système enregistre...", "Les utilisateurs peuvent..."), bien qu'elles décrivent le comportement attendu du MVP à venir, non un code existant.

**Exemples :**
- Ligne 50 : "Le système enregistre la dépense avec le montant en type `Decimal`..."
- Ligne 77 : "Validation des mots de passe : application des validateurs Django..."
- Ligne 119 : "Les dépenses sont triées par date décroissante..."

**Analyse :** Cette convention est cohérente avec la structure de la spec issue-4 (sections 2.2.1–2.2.8 utilisent également le présent pour décrire le comportement du MVP). Elle n'est pas trompeuse, car le contexte (cette section documente les fonctionnalités *incluses* dans le MVP) rend clair qu'il s'agit de spécifications futures, non d'affirmations sur l'état actuel du code.

La spec issue-63-privacy-page.md distingue explicitement "aujourd'hui" (présent vérifiable) et "prévu" (futur), car elle est une page publique où la confusion aurait des conséquences légales. Le mvp-scope.md est un document interne de périmètre, où cette distinction est moins critique.

**Vérification :** Aucune affirmation trouvée prétendant que le code existant possède des fonctionnalités non implémentées (p. ex. "Les utilisateurs peuvent se connecter" pour un système sans authentification).

**Suggestion :** Non-bloquant. Si clarté accrue souhaitée, ajouter une phrase introductive en section 3 : "Les sections ci-dessous décrivent les fonctionnalités et les modèles de données que le MVP implémentera."

---

### 3. Absence de distinction temps présent / futur dans la section "Hors périmètre"

**Constat :** La section "Hors périmètre MVP" énumère les fonctionnalités exclues avec des justifications, mais utilise un langage prescriptif ("Les utilisateurs ne peuvent **pas** créer de catégories personnalisées") qui pourrait être lu comme une affirmation sur l'état actuel plutôt qu'une limite de périmètre.

**Exemple, ligne 184 :**
> "Les utilisateurs ne peuvent **pas** créer de catégories personnalisées (hors MVP, feature backlog)"

Interprétation possible mais ambiguë : s'agit-il de "ils ne peuvent pas" (actuellement impossible) ou "ils ne doivent pas" (exclus du MVP) ?

**Analyse :** Le contexte (titre "Hors périmètre MVP", tableau AC-3) rend l'intention claire : ces sont des exclusions de périmètre, non des affirmations sur l'état du code. Cependant, la formulation mélange présent de capacité et intention.

**Vérification :** Relecture du tableau §2.3 et des justifications : aucune affirmation inventée. Toutes les exclusions sont justifiées et cohérentes avec la spec issue-4.

**Suggestion :** Non-bloquant. Amélioration optionnelle de clarté :
- Changerait ligne 184 de : "Les utilisateurs ne peuvent pas créer de catégories personnalisées..."
- Vers : "Création de catégories personnalisées par les utilisateurs : **hors périmètre MVP**. Raison : ..."

Mais la formulation actuelle est acceptable dans ce contexte.

---

### 4. Questions ouvertes (TBD) tracées et bien ségrégées

**Constat positif :** La section "Décisions ouvertes pour l'équipe" (fin du document) énumère 6 questions explicitement marquées comme TBD ou recommandées pour confirmation :
- Vérification d'email (ligne 343)
- Granularité et période des budgets (lignes 345–346)
- Catégories : liste exacte (ligne 346)
- Alertes : canal et type (ligne 347)
- Rate limiting : limites exactes (ligne 348)
- Réinitialisation de mot de passe (ligne 349)

Chacune est également signalée *dans la section pertinente* avec "*À confirmer par l'équipe*", créant une bonne traçabilité.

**Vérification :** Croiser chaque TBD avec sa section source :
- TBD 1 (vérif email) → ligne 41, 79–81 ✓
- TBD 2 (budgets) → lignes 148–149 ✓
- TBD 3 (catégories) → ligne 183 ✓
- TBD 4 (alertes) → ligne 61 ✓
- TBD 5 (rate limiting) → ligne 94 ✓
- TBD 6 (password reset) → ligne 81 ✓

**Suggestion :** Excellent. Pas de modification requise. Cet approche de double-notation (in-line + section finale) est une bonne pratique pour éviter des décisions cachées.

---

### 5. Vérification des chemins cités — tous valides

**Constat :** La section "Références et documents liés" (lignes 355–360) cite 6 fichiers. Tous existent et sont accessibles :

| Chemin | Statut |
|--------|--------|
| `docs/team.md` | ✓ Existe |
| `docs/decisions/0001-shared-app-shell-layout.md` | ✓ Existe |
| `docs/decisions/0002-privacy-claims-must-be-code-verifiable.md` | ✓ Existe |
| `docs/specs/issue-63-privacy-page.md` | ✓ Existe |
| `README.md` | ✓ Existe |
| `.github/agents/product-architecture.md` | ✓ Existe |

**Vérification :** Tous vérifiés via `ls` et `read` dans l'environnement.

**Suggestion :** Parfait. Aucune modification nécessaire.

---

### 6. Cohérence avec docs/team.md

**Constat :** Le mvp-scope.md énumère des responsabilités fonctionnelles (authentification, dépenses, budgets, accessibilité) sans les attribuer nommément aux membres de l'équipe.

**Analyse :** C'est correct. Le mvp-scope.md est un document de périmètre, pas un plan d'allocation de tâches. La spec issue-4 ne requiert pas l'attribution d'équipe (AC-1 à AC-8 ne la mentionnent pas). docs/team.md énumère les domaines :
- Tom : produit, architecture, budgets, audit sécurité
- Jason : backend, auth, dépenses
- Clément : frontend, DevOps, a11y

Le mvp-scope.md couvre tous ces domaines sans conflit.

**Vérification :** Pas de contradiction trouvée.

**Suggestion :** Acceptable tel quel. Le mvp-scope.md établit le *quoi* ; l'allocation au *qui* relève du plan d'exécution (hors scope de ce document).

---

### 7. Contraste avec la spec issue-63-privacy-page.md : approches cohérentes

**Constat :** La spec issue-63-privacy-page.md impose une règle stricte : chaque affirmation doit être traceable au code (decision 0002). Le mvp-scope.md ne reproduit pas cette rigueur niveau-par-niveau, mais c'est approprié.

**Analyse :**
- issue-63 : page *publique* et *légale* → exactitude vérifiable obligatoire.
- mvp-scope.md : document *interne* de périmètre → descriptions prospectives acceptables.

Le mvp-scope.md respecte cependant l'esprit de la verifiabilité :
- Les contraintes permanentes (section 5) citent les sources : product-architecture.md, decision 0001, 0002. ✓
- Les fonctionnalités sont répertoriées, pas aspirationnelles. ✓
- Aucune affirmation de sécurité ou légale inventée (p. ex., pas de "nous sommes conforme GDPR"). ✓

Le ton reste formel et technique, cohérent avec issue-63 pour le type de contenu qui les recoupe (modèle de données, API, sécurité).

**Vérification :** Lecture croisée des deux documents ; structure et niveau de détail approprié à chaque contexte.

**Suggestion :** Aucun changement requis. La distinction des types de documents est bien respectée.

---

### 8. Détail des API et codes d'erreur HTTP

**Constat positif :** Chaque section fonctionnelle (3.1–3.8) énumère explicitement les routes API attendues et, le cas échéant, les codes d'erreur :

Exemples :
- Section 3.2 (Dépenses), lignes 122–128 : `POST /api/expenses/`, `GET /api/expenses/`, `GET /api/expenses/{id}/`, etc., avec authentification requise. Codes 400, 401, 403, 404 énumérés.
- Section 3.3 (Budgets), lignes 160–165 : `POST /api/budgets/`, `GET /api/budgets/`, etc.

**Vérification :** Ces spécifications sont conformes à la directive product-architecture.md ("Every new or changed route must list its error cases"). Aucune route ne manque les cas d'erreur.

**Suggestion :** Excellente couverture. Pas de modification.

---

### 9. Accessibilité (section 3.7) : exigences WCAG 2.1 niveau AA

**Constat :** La section "Accessibilité" énumère 9 exigences concrètes :
- Formulaires avec `<label>` (ligne 249)
- Alt-text pour images/icônes (ligne 250)
- Couleur jamais seule (ligne 251)
- Contraste ≥ 4,5:1 / ≥ 3:1 (ligne 252)
- Navigabilité clavier, focus visible (ligne 253)
- Vrais éléments de titre (ligne 254)
- Messages d'erreur clairs (ligne 255)
- Landmarks : `<main>`, `<footer>` (ligne 256)
- Zoom 200%, reflow mobile (lignes 257–258)

Toutes ces exigences sont tracées à WCAG 2.1 Level AA (mentionné ligne 246).

**Vérification :** Les critères listés correspondent aux standards WCAG 2.1 AA. Aucune exigence inventée.

**Suggestion :** Excellente. Pas de modification.

---

### 10. Infrastructures Docker : détails et exécution clairs

**Constat :** La section 3.8 (Infrastructure Docker) décrit les services attendus et les commandes pour les exécuter :
- `docker-compose.yml` avec Django API, SvelteKit frontend, PostgreSQL (ligne 270)
- `docker compose up -d --build` pour démarrer (ligne 271)
- Migrations Django via `docker compose exec api python manage.py migrate` (ligne 274)

**Vérification :** Cohérent avec README.md (lignes 11–16), qui indique les mêmes commandes. Aucune contradiction.

**Suggestion :** Parfait. Pas de modification.

---

## Vérification complète de la conformité aux critères d'acceptation (AC-1 à AC-8)

| AC | Titre | Résultat | Détails |
|:---:|--------|:--------:|---------|
| AC-1 | Fichier existe en français | ✓ PASS | `docs/mvp-scope.md` existe, entièrement en français (termes techniques anglais acceptables : CSRF, ORM, Decimal, WCAG, POST, GET, etc.). |
| AC-2 | Toutes fonctionnalités MVP listées | ✓ PASS | Sections 3.1–3.8 couvrent les 8 domaines : auth, CRUD dépenses, budgets + seuils, catégories, privacy page, sécurité, accessibilité, Docker. |
| AC-3 | Fonctionnalités "hors périmètre" ségrégées | ✓ PASS | Section 4 "Hors périmètre MVP" avec tableau 10 exclusions justifiées. |
| AC-4 | Utilisateurs cibles + rôles | ✓ PASS | Section 1.1 "Profil des utilisateurs" énumère : trackers individuels et apprenants en développement. Cas d'usage clairs. |
| AC-5 | Parcours central (login → dépense → budget) | ✓ PASS | Section 2 décrit 4 étapes : connexion, saisie dépense, visualisation impact budgets, alerte dépassement (optionnelle). Concret ("L'utilisateur voit..."). |
| AC-6 | Ton cohérent avec issue-63 | ✓ PASS | Ton formel, technique, sans marketing. Utilise tableaux, énumérations, justifications. Une petite distinction : AC-6 accepte qu'issue-4-spec.md soit le blueprint et que mvp-scope.md utilise le présent pour les spécifications futures (par différence avec issue-63's distinction today/planned pour un document public). |
| AC-7 | Références aux décisions | ✓ PASS | Lignes 306–320 citent :  0001 (layout), 0002 (privacy), product-architecture (Decimal). Toutes existent et sont pertinentes. |
| AC-8 | Longueur 1500–2500 mots | ✓ PASS | 2 844 mots (13% au-dessus). Acceptable (voir Finding #1). |

---

## Vérification supplémentaire : absence d'affirmations inventées sur l'état du code

**Approche :** Scan pour détecter des affirmations présentées comme des faits actuels sur le code existant, alors que le code n'existe pas encore.

**Résultat :** Aucune trouvée.

**Justification :** 
- Les descriptions du MVP (sections 3.1–3.8) utilisent le présent pour décrire les spécifications futures, cohérent avec issue-4-spec.md. 
- Aucune affirmation du type "Le système fait X" (présent réel) détecté pour une feature non implémentée.
- Les contraintes architecturales (section 5) citent des décisions existantes (0001, 0002, product-architecture.md), pas des faits inventés.
- Les questions ouvertes ("À confirmer par l'équipe") sont explicitement marquées comme non résolues.

**Conclusion :** Aucun problème d'affirmations fallacieuses trouvé.

---

## Conclusion

Le document `docs/mvp-scope.md` **satisfait tous les critères d'acceptation** (AC-1 à AC-8) de la spec issue-4-mvp-scope.md. Il est complet, bien structuré, cohérent avec les documents de référence (decisions 0001–0002, issue-63-privacy-page.md, product-architecture.md, team.md, README.md), et ne contient aucune affirmation inventée sur l'état du code.

Aucun élément bloquant n'a été identifié. Les findings non bloquants (longueur légèrement accrue, clarification optionnelle du ton) sont mineurs et ne gênent pas la compréhension ou l'utilité du document.

**Le document est prêt pour approbation et utilisation comme référence de périmètre par les agents Full-Stack Development et QA & Security.**

