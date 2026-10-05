# Spec — Issue #3 : documenter le workflow Git (branches et revue des PR)

- **Statut :** proposition (à relire par un membre de l'équipe avant implémentation)
- **Livrable :** `docs/git-workflow.md`, réécrit de zéro
- **Type de changement :** documentation uniquement

## 1. Problème et user story

> En tant que membre de l'équipe Cashmire, je veux une page unique qui explique
> comment nommer mes branches, écrire mes commits, ouvrir une PR et la faire
> relire, afin que tout le monde travaille de la même façon et que rien n'arrive
> dans `main` sans avoir été relu par quelqu'un d'autre.

Un brouillon manuscrit existe déjà dans `docs/git-workflow.md`. Il **ne doit pas
être repris tel quel** : le fichier est réécrit entièrement à partir de cette
spec. Le brouillon contient notamment une affirmation fausse à ce jour (« la
branche `main` est protégée ») — voir §5.

## 2. Périmètre

### Dans le périmètre

- Réécriture complète de `docs/git-workflow.md`, en français.

### Hors périmètre

- Aucun changement dans `backend/`, `frontend/`, migrations, tests, CI.
- **Pas d'activation** de la protection de branche GitHub (ni via l'UI, ni via
  `gh api`). Le document peut la *recommander*, pas la déclarer active.
- Pas de template de PR (`.github/pull_request_template.md`), pas de hook
  `commitlint`/`husky`, pas de CODEOWNERS. Bonnes idées, issues séparées.
- Pas de commit ni de PR par l'agent d'implémentation : la personne qui porte
  l'issue commite elle-même.
- Pas de modification d'autres fichiers de `docs/` (en particulier
  `docs/specs/`, `docs/reviews/`, `docs/decisions/`).

## 3. Ton et format

La consigne demandait de s'aligner sur `docs/team.md`. **Ce fichier n'existe pas
dans le dépôt** (voir §6, question Q1). En attendant, le format suivant est
imposé :

- Français, phrases courtes, tutoiement ou impersonnel (pas de « vous » mêlé à
  du « tu ») — choisir l'**impersonnel** par défaut (« Une branche par issue »).
- Titre `#` unique, sections `##`, pas de `###` sauf nécessité.
- Listes à puces plutôt que paragraphes ; un exemple concret par règle.
- Termes techniques et valeurs littérales en `code` (`main`, `feat`, `Closes #12`).
- Règles obligatoires formulées de façon affirmative (« doit », « jamais »),
  recommandations explicitement marquées comme telles (« recommandé »).
- Longueur visée : 60 à 120 lignes. Pas d'emoji.

## 4. Plan du document et contenu attendu

Le fichier `docs/git-workflow.md` contient exactement les sections suivantes,
dans cet ordre.

### `# Workflow Git et revue des pull requests`

Introduction de 2 à 3 lignes : `main` est la branche de référence ; tout
changement y arrive par une PR relue et approuvée par un autre membre ; pas de
push direct sur `main`, par convention d'équipe.

### `## Résumé`

Liste numérotée de 5 à 7 étapes, du point de vue d'un contributeur :

1. Partir d'une issue GitHub (en créer une si besoin).
2. Mettre `main` à jour, créer la branche `<type>/<issue>-<slug>`.
3. Commiter en Conventional Commits.
4. Pousser et ouvrir une PR vers `main`.
5. Demander une relecture à au moins un autre membre.
6. Traiter les retours, obtenir l'approbation.
7. Fusionner, supprimer la branche.

Inclure un bloc de commandes minimal (`git switch main`, `git pull`,
`git switch -c feat/12-budget-banner`, `git push -u origin ...`).

### `## Branches`

Contenu obligatoire :

- Format : `<type>/<issue>-<slug>`.
- `<type>` : même liste que les types de commit (`feat`, `fix`, `docs`,
  `refactor`, `chore`, `test`, `style`, `build`, `ci`, `perf`, `revert`),
  choisi selon le changement principal de la branche.
- `<issue>` : numéro de l'issue GitHub, sans `#`. Obligatoire.
- `<slug>` : 2 à 5 mots en minuscules, ASCII, séparés par des tirets, sans
  accents ni espaces.
- Exemples valides (au moins 3, dont `docs/3-git-workflow`) et au moins 2
  exemples **invalides** avec la raison (ex. `Feature/BudgetBanner` : type
  inconnu, majuscules, pas de numéro d'issue ; `fix-login` : pas de `/` ni
  d'issue).
- Une branche = une issue. Branche créée depuis `main` à jour.
- Branche courte durée : supprimée après fusion.
- Préciser que ce nom de branche est distinct du `--slug` de l'orchestrateur
  agentique (`issue-<n>-<nom>`, voir `agentic/README.md`) — les deux coexistent.

### `## Commits`

Contenu obligatoire :

- Référence à la spécification Conventional Commits
  (lien `https://www.conventionalcommits.org/fr/v1.0.0/`).
- Bloc de format :
  ```
  <type>[scope optionnel][!]: <description>

  [corps optionnel]

  [footers optionnels]
  ```
- Règles : `type` obligatoire en minuscules ; `feat` = nouvelle fonctionnalité,
  `fix` = correction de bug ; `scope` optionnel entre parenthèses
  (`fix(budget): ...`) ; description courte, à l'impératif, directement après
  `: ` ; corps séparé par une ligne vide ; footers au format `Token: valeur`
  (tirets à la place des espaces, sauf `BREAKING CHANGE`).
- Breaking change : `!` avant `:` **ou** footer `BREAKING CHANGE: ...`, avec un
  exemple.
- Un commit = un seul type de changement ; sinon, plusieurs commits.
- **Règle explicite :** ne jamais ajouter de trailer
  `Co-Authored-By: Claude ...` (ni aucun trailer de co-auteur pour un outil ou
  agent IA). Les commits sont attribués à la personne qui les fait, y compris
  quand le code a été produit avec l'aide d'un agent. Faire le lien avec
  `docs/agentic-log.md`, où l'usage des agents est tracé à la place.
- Au moins 3 exemples valides (dont un avec scope, un avec corps, un breaking)
  et 2 invalides avec la raison (ex. `Added budget banner` : pas de type,
  passé ; `Feat: add banner` : type en majuscule).

### `## Pull requests`

Contenu obligatoire :

- Une PR par issue, ciblant `main`.
- Titre au format Conventional Commits (même règle que les commits).
- Description qui contient au minimum :
  - `Closes #<issue>` (fermeture automatique de l'issue) ;
  - un résumé du changement (quoi et pourquoi) ;
  - comment tester (commandes ou étapes manuelles) ;
  - le cas échéant, la spec/revue agentique associée
    (`docs/specs/<slug>.md`, `docs/reviews/<slug>.md`) ;
  - le cas échéant, la mention requise par la décision
    `docs/decisions/0002-privacy-claims-must-be-code-verifiable.md` (§5) pour
    toute PR qui touche aux données personnelles.
- Proposer un squelette de description en bloc Markdown copiable.
- Les tests pertinents passent en local avant de demander la revue.
- PR ciblée : une PR qui mélange plusieurs sujets est scindée.
- PR brouillon (`Draft`) autorisée pour un travail en cours ; la revue n'est
  demandée qu'une fois la PR passée en « Ready for review ».

### `## Revue`

Contenu obligatoire :

- **Au moins un autre membre** de l'équipe approuve la PR (statut « Approve »
  sur GitHub) avant toute fusion. L'auteur ne s'approuve jamais lui-même, et
  une approbation par un agent IA ne compte pas.
- Ce que fait le relecteur : lit le diff entier, vérifie les critères
  d'acceptation de l'issue/spec, lance les tests si le changement touche du
  code, vérifie le nom de branche et les messages de commit.
- Les commentaires sont résolus (correction ou réponse argumentée) avant la
  fusion. Un nouveau push significatif après approbation implique une
  nouvelle relecture.
- Rappel : une sortie d'agent n'est pas une preuve que ça marche ; un humain
  relit (renvoi à la section « What this does not replace » de
  `agentic/README.md`).
- Délai indicatif de relecture : laisser en placeholder `[[DÉLAI À DÉFINIR]]`
  si l'équipe ne l'a pas tranché (Q3).

### `## Fusion`

Contenu obligatoire :

- Qui fusionne : l'auteur, une fois l'approbation obtenue et les commentaires
  résolus (sauf décision contraire, Q4).
- Stratégie de fusion : documenter la stratégie retenue en Q2. Constat actuel :
  l'historique de `main` contient des commits « Merge pull request #… », donc
  le merge commit est utilisé aujourd'hui.
- Supprimer la branche distante après fusion.
- Si `main` a avancé : mettre la branche à jour (`git pull --rebase origin main`
  ou merge de `main`, selon Q2) et relancer les tests avant fusion.

### `## Protection de main`

Contenu obligatoire, **formulé sans affirmer que la protection est active** :

- Indiquer que les règles ci-dessus sont, à ce jour, une **convention
  d'équipe** et ne sont pas imposées techniquement par GitHub.
- Lister la configuration recommandée pour plus tard : PR obligatoire,
  1 approbation minimum, rejet des approbations obsolètes après nouveau push,
  push direct et force-push interdits sur `main`.
- Préciser que son activation relève d'un admin du dépôt et fera l'objet
  d'une décision/issue séparée ; mettre à jour cette section le jour où elle
  est activée.

## 5. Écarts identifiés dans le brouillon existant

À corriger dans la réécriture (liste non exhaustive, pour le relecteur) :

1. Le brouillon affirme que `main` est protégée sur GitHub. Rien dans le dépôt
   ne le confirme et l'issue exclut explicitement de l'activer : affirmation à
   remplacer par la formulation du §4 « Protection de main ».
2. La règle « pas de trailer `Co-Authored-By` » est absente : elle est
   obligatoire.
3. Pas d'exemples invalides, pas de squelette de PR, pas de lien avec le
   workflow agentique ni avec la décision 0002.
4. Stratégie de fusion et suppression de branche non documentées.

## 6. Questions ouvertes

- **Q1 — `docs/team.md` introuvable.** La demande s'y réfère comme modèle de
  ton, mais le fichier n'existe pas dans le dépôt (branche
  `docs/3-git-workflow`). Soit il est sur une autre branche non fusionnée,
  soit il reste à écrire. En attendant, le §3 fait foi. Si `team.md` arrive
  avant l'implémentation, aligner le ton dessus et lier les deux documents.
- **Q2 — Stratégie de fusion :** merge commit (usage actuel), squash ou
  rebase ? Le squash rend le titre de PR = message de commit sur `main`, ce
  qui renforce l'intérêt du titre en Conventional Commits. À trancher.
- **Q3 — Délai de relecture** attendu (ex. 24 h ouvrées) : à trancher ou
  laisser en placeholder.
- **Q4 — Qui fusionne :** l'auteur (proposé) ou le relecteur ?
- **Q5 — Petites corrections** (typo dans la doc) : même règle d'1 approbation
  sans exception ? Proposé : oui, aucune exception.
- **Risque :** tant que la protection GitHub n'est pas activée, rien
  n'empêche techniquement un push direct sur `main`. Le document doit le dire
  honnêtement plutôt que le masquer.

## 7. Checklist d'acceptation

Le relecteur coche chaque point sur la PR de l'issue #3.

- [ ] `docs/git-workflow.md` est réécrit intégralement (pas de reprise
      ligne à ligne du brouillon), en français, sans emoji.
- [ ] Les sections du §4 sont présentes, dans l'ordre, avec ces titres.
- [ ] Le format de branche `<type>/<issue>-<slug>` est documenté avec la
      liste des types, les règles du slug, des exemples valides **et**
      invalides.
- [ ] Les exigences de PR sont listées : cible `main`, titre Conventional
      Commits, `Closes #<issue>`, résumé, comment tester, tests passés,
      squelette de description copiable.
- [ ] La règle « au moins un autre membre approuve avant la fusion » est
      explicite, ainsi que « l'auteur ne s'auto-approuve pas » et « une
      approbation d'agent ne compte pas ».
- [ ] Conventional Commits est documenté : format, types, scope, description
      à l'impératif, corps/footers, breaking change, un type par commit,
      exemples valides et invalides.
- [ ] L'interdiction du trailer `Co-Authored-By: Claude ...` (et de tout
      trailer de co-auteur IA) est écrite noir sur blanc.
- [ ] Le document **n'affirme pas** que `main` est protégée sur GitHub ; il
      présente la protection comme recommandée et non activée.
- [ ] Liens présents et valides vers `agentic/README.md`,
      `docs/agentic-log.md` et
      `docs/decisions/0002-privacy-claims-must-be-code-verifiable.md`.
- [ ] Les questions Q2 à Q4 sont soit tranchées et reflétées dans le
      document, soit visibles sous forme de `[[PLACEHOLDER]]`.
- [ ] Le diff de la PR ne touche que `docs/git-workflow.md` (aucun fichier
      dans `backend/`, `frontend/`, `.github/`, `docs/specs/`,
      `docs/reviews/`).
- [ ] La protection de branche GitHub n'a pas été modifiée.
- [ ] Le nom de la branche (`docs/3-git-workflow`) et les commits de la PR
      respectent eux-mêmes les règles du document.
