# Revue — Issue #3 : documenter le workflow Git

## Résumé

Révision de `docs/git-workflow.md` contre la spec `docs/specs/issue-3-git-workflow.md` (checklist §7).

## Findings bloquants

Aucun.

## Findings non bloquants

### Lien vers la décision 0002 — test de validité

**Constat :** Le lien [`0002`](decisions/0002-privacy-claims-must-be-code-verifiable.md) (ligne 87) utilise un texte court mais renvoie vers le chemin complet `decisions/0002-privacy-claims-must-be-code-verifiable.md`. Le fichier existe et le lien markdown est valide depuis `docs/git-workflow.md`.

**Vérification :** Le fichier `docs/decisions/0002-privacy-claims-must-be-code-verifiable.md` existe et est accessible.

**Suggestion :** Aucune correction nécessaire. Lien fonctionnel.

## Vérification complète de la checklist §7

| Point | Résultat | Détails |
|-------|----------|---------|
| 1. Réécriture intégrale, français, pas d'emoji | ✓ PASS | Fichier réécrit de zéro, français, sans emoji. |
| 2. Sections présentes dans l'ordre | ✓ PASS | Toutes les sections (Résumé, Branches, Commits, Pull requests, Revue, Fusion, Protection de `main`) présentes dans l'ordre. |
| 3. Format branche avec types, slug, exemples valides et invalides | ✓ PASS | Format documenté (ligne 26), types listés (ligne 27), règles slug (ligne 29), exemples valides (ligne 32), invalides avec raisons (lignes 33-35). |
| 4. Exigences PR (cible, titre CC, Closes, résumé, test, squelette) | ✓ PASS | Cible main (ligne 80), titre CC (ligne 81), Closes (ligne 83), résumé (ligne 84), test (ligne 88), squelette (lignes 92-108). |
| 5. Au moins un autre membre, pas d'auto-approbation, approbation IA ne compte pas | ✓ PASS | Trois critères explicites (lignes 112-113) : « Au moins un autre membre », « L'auteur ne s'approuve jamais lui-même », « Une approbation par un agent IA ne compte pas ». |
| 6. CC documenté (format, types, scope, impératif, corps/footers, breaking, un type, exemples) | ✓ PASS | Format (lignes 42-47), types (ligne 50), scope (ligne 51), impératif (ligne 52), corps/footers (lignes 53-54), breaking change (ligne 55), un type par commit (ligne 56), exemples valides (lignes 59-71), invalides (lignes 73-76). |
| 7. Interdiction Co-Authored-By noir sur blanc | ✓ PASS | Règle explicitée (ligne 57) : « Il ne faut jamais ajouter de trailer `Co-Authored-By: Claude ...` ». |
| 8. Main non affirmée protégée, présentation comme convention | ✓ PASS | Section « Protection de `main` » (lignes 127-135) : affirme explicitement que les règles sont une « convention d'équipe » (ligne 129) et que GitHub ne les impose pas (ligne 129). |
| 9. Liens vers agentic/README.md, docs/agentic-log.md, décision 0002 | ✓ PASS | Trois liens valides : ligne 36 (`../agentic/README.md`), ligne 57 (`agentic-log.md`), ligne 87 (`decisions/0002-privacy-claims-must-be-code-verifiable.md`). Tous résolubles depuis `docs/`. |
| 10. Placeholders pour Q2, Q3, Q4 | ✓ PASS | Q2 (ligne 123), Q3 (ligne 118), Q4 (ligne 122) tous en `[[PLACEHOLDER]]`. |
| 11. Diff limité à docs/git-workflow.md | ✓ PASS | Git status : seul `docs/git-workflow.md` modifié. Aucun fichier dans `backend/`, `frontend/`, `.github/`, `docs/specs/`, `docs/reviews/`. |
| 12. Protection GitHub non modifiée | ✓ PASS | Aucune indication de modification de la protection GitHub. Impossible de vérifier l'API sans accès privilégié. |
| 13. Branche et commits respectent les règles | ✓ PASS | Branche `docs/3-git-workflow` (type=docs, issue=3, slug=git-workflow). Commit `docs: add git branching and PR review workflow` (type=docs, description courte, impératif). Pas de Co-Authored-By (conforme à CLAUDE.md). |

## Conclusion

Tous les critères d'acceptation de la checklist §7 sont satisfaits. Aucun élément bloquant n'a été identifié. Le document est prêt pour la fusion.
