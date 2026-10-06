# Workflow Git et revue des pull requests

`main` est la branche de référence. Tout changement y arrive par une PR relue et approuvée par un autre membre de l'équipe.
Aucun push direct sur `main`, par convention d'équipe (voir « Protection de `main` »).

## Résumé

1. Partir d'une issue GitHub (en créer une si besoin).
2. Mettre `main` à jour, puis créer la branche `<type>/<issue>-<slug>`.
3. Commiter en Conventional Commits.
4. Pousser et ouvrir une PR vers `main`.
5. Demander une relecture à au moins un autre membre.
6. Traiter les retours, obtenir l'approbation.
7. Fusionner, supprimer la branche.

```
git switch main
git pull
git switch -c feat/12-budget-banner
# ... commits ...
git push -u origin feat/12-budget-banner
```

## Branches

- Format : `<type>/<issue>-<slug>`.
- `<type>` : `feat`, `fix`, `docs`, `refactor`, `chore`, `test`, `style`, `build`, `ci`, `perf`, `revert`. Choisi selon le changement principal de la branche.
- `<issue>` : numéro de l'issue GitHub, sans `#`. Obligatoire.
- `<slug>` : 2 à 5 mots en minuscules, ASCII, séparés par des tirets, sans accents ni espaces.
- Une branche = une issue, créée depuis `main` à jour.
- Branche de courte durée : supprimée après la fusion.
- Valides : `docs/3-git-workflow`, `feat/12-budget-banner`, `fix/27-login-redirect`.
- Invalides :
  - `Feature/BudgetBanner` : type inconnu, majuscules, pas de numéro d'issue.
  - `fix-login` : pas de `/`, pas de numéro d'issue.
- Ce nom de branche est distinct du `--slug` de l'orchestrateur agentique (`issue-<n>-<nom>`, voir [`agentic/README.md`](../agentic/README.md)). Les deux coexistent.

## Commits

Les commits suivent la spécification [Conventional Commits](https://www.conventionalcommits.org/fr/v1.0.0/).

```
<type>[scope optionnel][!]: <description>

[corps optionnel]

[footers optionnels]
```

- `type` obligatoire, en minuscules. `feat` = nouvelle fonctionnalité, `fix` = correction de bug.
- `scope` optionnel, entre parenthèses : `fix(budget): corriger l'arrondi`.
- Description courte, à l'impératif, directement après `: `.
- Corps séparé de la description par une ligne vide.
- Footers au format `Token: valeur`, avec des tirets à la place des espaces (sauf `BREAKING CHANGE`).
- Breaking change : `!` avant le `:` **ou** footer `BREAKING CHANGE: description`.
- Un commit = un seul type de changement ; sinon, plusieurs commits.
- Il ne faut jamais ajouter de trailer `Co-Authored-By: Claude ...`, ni aucun trailer de co-auteur pour un outil ou un agent IA. Les commits sont attribués à la personne qui les fait, y compris quand le code a été produit avec l'aide d'un agent. L'usage des agents est tracé dans [`docs/agentic-log.md`](agentic-log.md).

Valides :

- `feat(budget): add overspend banner`
- `fix: round totals with Decimal`
- `refactor!: rename transactions endpoint`, ou avec un corps et un footer :

```
feat(api): paginate transactions

Limite la liste à 50 éléments par page.

BREAKING CHANGE: la réponse est maintenant un objet paginé.
```

Invalides :

- `Added budget banner` : pas de type, verbe au passé.
- `Feat: add banner` : type en majuscule.

## Pull requests

- Une PR par issue, ciblant `main`.
- Titre au format Conventional Commits (mêmes règles que les commits).
- La description contient au minimum :
  - `Closes #<issue>` (fermeture automatique de l'issue) ;
  - un résumé du changement (quoi et pourquoi) ;
  - comment tester (commandes ou étapes manuelles) ;
  - le cas échéant, la spec et la revue agentiques associées (`docs/specs/<slug>.md`, `docs/reviews/<slug>.md`) ;
  - le cas échéant, pour toute PR qui touche aux données personnelles, la mise à jour de la page de confidentialité ou la justification de son absence, comme l'exige la décision [`0002`](decisions/0002-privacy-claims-must-be-code-verifiable.md) (point 5).
- Les tests pertinents passent en local avant de demander la revue.
- PR ciblée : une PR qui mélange plusieurs sujets est scindée.
- Une PR `Draft` est autorisée pour un travail en cours ; la revue n'est demandée qu'une fois la PR en « Ready for review ».

Squelette de description :

```markdown
Closes #<issue>

## Résumé
<quoi et pourquoi>

## Comment tester
<commandes ou étapes>

## Agentique (si applicable)
<docs/specs/<slug>.md, docs/reviews/<slug>.md>

## Données personnelles (si applicable)
<page de confidentialité mise à jour, ou pourquoi aucune mise à jour>
```

## Revue

- Au moins **un autre membre** de l'équipe approuve la PR (statut « Approve » sur GitHub) avant toute fusion.
- L'auteur ne s'approuve jamais lui-même. Une approbation par un agent IA ne compte pas.
- Le relecteur lit le diff entier, vérifie les critères d'acceptation de l'issue ou de la spec, lance les tests si le changement touche du code, et vérifie le nom de branche et les messages de commit.
- Les commentaires sont résolus (correction ou réponse argumentée) avant la fusion.
- Un nouveau push significatif après approbation implique une nouvelle relecture.
- Une sortie d'agent n'est pas une preuve que cela fonctionne : un humain relit (voir « What this does not replace » dans [`agentic/README.md`](../agentic/README.md)).
- Délai de relecture : `[[DÉLAI À DÉFINIR]]`.

## Fusion

- Qui fusionne : `[[QUI FUSIONNE À DÉFINIR : l'auteur (proposé) ou le relecteur]]`. Dans tous les cas, seulement après approbation et commentaires résolus.
- Stratégie de fusion : `[[STRATÉGIE À DÉFINIR : merge commit, squash ou rebase]]`. À ce jour, l'historique de `main` contient des commits « Merge pull request #… » : le merge commit est utilisé en pratique.
- Supprimer la branche distante après la fusion.
- Si `main` a avancé : mettre la branche à jour (`git pull --rebase origin main` ou merge de `main`, selon la stratégie retenue) et relancer les tests avant la fusion.

## Protection de `main`

- À ce jour, les règles ci-dessus sont une **convention d'équipe**. GitHub ne les impose pas techniquement : rien n'empêche un push direct sur `main`.
- Configuration recommandée pour plus tard :
  - PR obligatoire ;
  - 1 approbation minimum ;
  - rejet des approbations obsolètes après un nouveau push ;
  - push direct et force-push interdits sur `main`.
- L'activation relève d'un admin du dépôt et fera l'objet d'une décision ou d'une issue séparée. Cette section sera mise à jour le jour où la protection est activée.
