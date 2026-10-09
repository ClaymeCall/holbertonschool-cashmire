# Agentic workflow: talking points (issue #77)

Tout ce qui suit est tiré de `docs/agentic-log.md`, des définitions dans
`.github/agents/` et des PR indiquées. Rien n'est ajouté qui ne soit pas dans
ces sources. Les points marqués « à répéter » restent à faire par l'équipe.

## 1. Les trois agents et leur effet sur le workflow

Définis dans `.github/agents/` (issues #9, #10, #11), lancés ensemble par
`agentic/orchestrator.py` (entrée du log du 2026-10-05).

| Agent | Outils autorisés | Rôle | Sortie |
|---|---|---|---|
| `product-architecture` | Read, Write, Glob, Grep | Écrit la spec avant toute implémentation | `docs/specs/<slug>.md` |
| `fullstack-development` | Read, Write, Edit, Bash, Glob, Grep | Implémente la spec (backend et frontend) | code et tests |
| `qa-security` | Read, Bash, Glob, Grep, Write | Relit sans éditer le code source; lance les tests | `docs/reviews/<slug>.md` |

Effet concret: rien n'est implémenté sans spec lisible, et la revue est
séparée de l'implémentation (le QA n'édite jamais le code). Chaque agent a un
périmètre écrit, ce qui permet de vérifier qu'il n'en est pas sorti.

## 2. Entrée du log à répéter (choix principal)

**« Live orchestrator run for issue #63 »** (2026-10-05), livrée dans la PR #79
(commit `baaf48b`).

- Les trois agents ont produit la page de confidentialité.
- Le QA a corrigé lui-même, à sa deuxième passe, deux bugs de son propre
  fichier de test (matchers jest-dom non installés, chevauchement dans la
  vérification des formulations interdites).
- **Rejeté / corrigé par un humain:** en lançant réellement
  `npm install && npx vitest run`, les 6 tests échouaient (Vite résolvait le
  build serveur de Svelte). Aucune lecture de `REVIEW.md` ne pouvait le
  montrer. Correction humaine dans `frontend/vite.config.js`
  (`resolve: { conditions: ["browser"] }`), 6/6 ensuite.
- Leçon à dire: un run d'agent n'est pas une preuve; l'exécution des tests
  l'est.

## 3. Autres entrées utiles

- **Collision `SPEC.md` / `REVIEW.md`** (2026-10-05, PR #79, commit `985a469`):
  une personne a relu le code et vu que le run suivant écraserait ces
  fichiers. Correction: fichiers par feature `docs/specs/<slug>.md` et
  `docs/reviews/<slug>.md`, et refus de relancer si le fichier existe.
  Rejeté: rendre `--slug` strictement obligatoire.
- **Revue QA du modèle Budget** (issue #45, 2026-10-07; PR #115, commit
  `20ce9f1` pour la spec, la revue et le log): 14 critères d'acceptation
  vérifiés, 23 tests, un finding non bloquant (`check=` au lieu de
  `condition=` pour `CheckConstraint`).
- **Revue QA de l'application entière** (issue #58, PR #139): faite sans clé
  API, par un sous-agent suivant `qa-security.md`. 1 finding blocking
  (contraste des cartes budget), 20 non-blocking. Le tri est proposé dans la
  PR #141 et reste à valider en équipe.

## 4. Questions probables et réponses appuyées

- *Comment avez-vous vérifié ce que les agents produisaient ?* En lançant les
  suites de tests, pas en croyant le verdict écrit (cf. §2). Le log dit
  explicitement ce qui n'a pas été testé.
- *Qu'avez-vous rejeté ?* `--slug` obligatoire (§3). Dans le tri #59 proposé,
  N3 et N20 sont rejetés pour le MVP, avec raison.
- *Les agents ont-ils fait des erreurs ?* Oui: bugs de test du QA, échec des 6
  tests au premier run (§2).

## 5. À faire par l'équipe (non fait)

- [ ] Chaque membre répète à voix haute la section 2 et explique les trois
      agents (section 1).
- [ ] Décider de l'entrée du log présentée, si ce n'est pas celle du §2.
- [ ] Vérifier que les liens PR / commits ci-dessus sont ceux que l'on
      montre à l'écran.
