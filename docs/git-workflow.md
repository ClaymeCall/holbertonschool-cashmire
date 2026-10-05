# Workflow Git et revue des PR

Tout changement passe par une pull request relue avant d'être fusionné dans `main`. Aucun push direct sur `main`.

## Branches

- Une branche par issue, créée depuis `main` à jour.
- Format : `<type>/<numéro-issue>-<slug>`, par exemple `feat/12-budget-banner` ou `docs/3-git-workflow`.
- `type` : `feat`, `fix`, `docs`, `refactor`, `chore`, `test`, `style`, `build`, `ci`, `perf`, `revert`.
- `slug` : quelques mots en minuscules séparés par des tirets.

## Messages de commit

Les commits suivent la spécification [Conventional Commits](https://www.conventionalcommits.org/) :

```
<type>[scope optionnel][!]: <description>

[corps optionnel]

[footers optionnels]
```

- `type` obligatoire, en minuscules (voir la liste ci-dessus) ; `feat` pour une nouvelle fonctionnalité, `fix` pour une correction de bug.
- `scope` optionnel entre parenthèses : `fix(parser): ...`.
- `description` courte, à l'impératif, directement après `: `.
- Corps et footers séparés par une ligne vide ; footers au format `Token: valeur`.
- Breaking change : `!` avant le `:` ou footer `BREAKING CHANGE: description`.
- Un commit = un seul type de changement.

## Pull requests

- Une PR par issue, ciblant `main`, avec le titre au format Conventional Commits.
- La description référence l'issue (`Closes #<numéro>`) et résume le changement et la façon de le tester.
- Les tests pertinents passent avant de demander la revue.
- PR de taille raisonnable : une PR qui mélange plusieurs sujets est scindée.

## Revue

- Au moins **un autre membre** de l'équipe approuve la PR avant la fusion ; l'auteur ne valide jamais sa propre PR.
- Le relecteur lit le diff, vérifie les critères d'acceptation de l'issue et lance les tests si nécessaire.
- Les commentaires de revue sont résolus (correction ou réponse) avant la fusion.
- La fusion est faite par l'auteur une fois la PR approuvée.

## Protection de `main`

Sur GitHub, la branche `main` est protégée : PR obligatoire, au moins 1 approbation requise, push direct interdit.
