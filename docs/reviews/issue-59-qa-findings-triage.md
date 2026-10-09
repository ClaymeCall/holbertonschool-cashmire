# Tri des findings QA & Security (issue #59)

Source: `docs/reviews/issue-58-qa-security-review.md` (PR #139).

**Statut: proposition de tri, à valider en équipe.** Les décisions ci-dessous
sont celles que je propose; elles ne sont définitives qu'après discussion.
Vérifié par relecture du code avant de trier: B1 (ratios de contraste
recalculés: 3,25 / 2,10 / 4,20 / 4,41), N9, N12 et N18. Les autres findings
sont repris du rapport sans reproduction dynamique.

Légende: **accepté** = à corriger; **modifié** = retenu mais traité autrement
(documenté, reporté, ou périmètre réduit); **rejeté** = non retenu, avec raison.

| # | Finding | Décision | Raison / suite |
|---|---|---|---|
| B1 | Contraste du texte des cartes budget < 4,5:1 | **Accepté** (priorité 1) | Vérifié: `.status-*` règlent `color` sur le `li` (`BudgetsList.svelte`), le commentaire du fichier dit pourtant que seules la bordure et la barre sont teintées. Garder `color` neutre, teinter bordure et barre. À traiter avec l'accessibilité (#65). |
| N1 | Login CSRF (`FormParser` accepté) | **Modifié** | Risque limité (pas de donnée de la victime exposée). Restreindre les parsers des vues auth à JSON ou documenter dans `docs/decisions/0003`. Non reproduit. |
| N2 | Énumération d'emails à l'inscription (G4) | **Modifié** | Limite MVP à documenter (comme le login, décision 0004). |
| N3 | Throttle login en `LocMemCache` | **Rejeté** pour le MVP | Déjà documenté comme minimal dans la décision 0004; un cache partagé relève du déploiement. |
| N4 | Durcissement de config (SECRET_KEY, ALLOWED_HOSTS, cookies secure) | **Modifié** | À lister dans les limites connues du MVP (#74). Échec au démarrage sans `DJANGO_SECRET_KEY` hors DEBUG: option à décider. |
| N5 | 403 au lieu de 401 pour un anonyme (G1) | **Accepté** | Aligner les vues sur `SessionCookieAuthentication`; mettre à jour les tests (403 → 401) et `docs/api-design.md` (le 403 y est noté « comportement actuel »). |
| N6 | Format d'erreur incohérent (G5) | **Modifié** | Faible. Le frontend gère les deux formats; uniformiser plus tard. |
| N7 | Emails différant par la casse | **Modifié** | Non reproduit. À confirmer avant de décider d'une normalisation. |
| N8 | Course à l'inscription → 500 | **Modifié** | Non reproduit. Pas de fuite (réponse générique); fiabilité seulement. |
| N9 | Seuil d'alerte vide bloque le formulaire budget | **Accepté** | Vérifié: `BudgetForm.svelte` rejette une chaîne vide alors que le backend accepte l'omission. |
| N10 | Focus perdu à la soumission | **Accepté** (#65) | Passe accessibilité. |
| N11 | Erreurs non reliées aux champs (`aria-describedby`, `aria-invalid`) | **Accepté** (#65) | Passe accessibilité. |
| N12 | 429 affiché comme « Couldn't reach Cashmire » | **Accepté** | Vérifié: `login/+page.svelte` n'a pas de branche 429. Ajouter un message dédié. |
| N13 | Liens « Edit » identiques | **Accepté** (#65) | Passe accessibilité. |
| N14 | Barre de progression sans `aria-valuetext` | **Accepté** (#65) | Passe accessibilité. |
| N15 | Menu mobile: pas d'Échap, pas de lien d'évitement | **Accepté** (#65) | Passe accessibilité. |
| N16 | `+error.svelte` affiche le message d'erreur brut; page `health` expose l'URL de l'API | **Modifié** | Afficher un message générique dans `+error.svelte`; la page `health` est publique et de faible impact. |
| N17 | Fichiers « * 2.py » non suivis | **Accepté** | Fichiers locaux jamais commités. À supprimer par leur auteur; aucun impact sur le dépôt. |
| N18 | Commentaire obsolète dans `budgets.js` | **Accepté, corrigé** | Corrigé dans la PR #140. |
| N19 | Pas de `max_length` sur `description` | **Modifié** | Faible. À borner si le temps le permet. |
| N20 | Page d'édition: charge toute la liste | **Rejeté** pour le MVP | Pas de `GET /expenses/<id>/` dans le contrat d'API actuel; coût négligeable à l'échelle de la démo. |

## Faux positifs

Le rapport ne déclare aucun faux positif parmi ses findings. Il liste en
« vérifié OK » ce qui a été écarté (XSS, SQL brut, IDOR, stockage de token,
fuite d'erreurs). Ces points ne sont pas retriés ici.

## Correction résultante

- N18 corrigé: PR #140 (`docs(frontend): drop stale not-merged note in budgets client`).

## Reste à faire après validation

Corrections acceptées non encore faites: B1, N5, N9, N12 (et la passe
accessibilité #65: N10, N11, N13, N14, N15). Aucune n'est faite par cette PR.
