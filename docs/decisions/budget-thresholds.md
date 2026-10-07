# Décision — Seuil d'avertissement et statuts d'un budget

- **Date :** 2026-10-07
- **Auteur :** Tom Vieilledent
- **Issue liée :** #51
- **Statut :** Proposée. À valider par l'équipe avant implémentation (#50, #47, UI budgets).

---

## Décision

### 1. Seuil d'avertissement

Le seuil d'avertissement par défaut est **80 %** de la consommation du budget.

- Il correspond au champ `Budget.alert_threshold` (`NUMERIC(5, 2)`, défaut `80.00`, entre 0 et 100), déjà défini dans l'ERD et le contrat d'API.
- Chaque budget peut surcharger la valeur par défaut via `alert_threshold`. Il n'y a pas de réglage global par utilisateur.
- Si `alert_threshold` est `NULL`, le service applique 80 %.

### 2. Statuts

Soit `pourcentage = spent / amount × 100`. `amount` est strictement positif (contrainte `CHECK(amount > 0)`), donc il n'y a pas de division par zéro.

| Statut | Condition | Libellé UI |
|--------|-----------|------------|
| `ok` | `pourcentage < seuil` | « Dans le budget » |
| `warning` | `seuil <= pourcentage < 100` | « Attention » |
| `full` | `pourcentage == 100` (donc `spent == amount`) | « Budget atteint » |
| `exceeded` | `pourcentage > 100` (donc `spent > amount`) | « Dépassé » |

Règles aux bornes :
- **Exactement 100 % = `full`**, et non `exceeded`. Un dépassement n'existe qu'au-delà de 100 %.
- **Exactement le seuil = `warning`** (borne inférieure incluse).
- Si `alert_threshold = 100`, le statut `warning` est vide : on passe de `ok` à `full`.
- Les dépenses sont les `Expense` de la catégorie dans `[period_start, period_end]` (bornes incluses). Un budget sans dépense vaut `0 %` (`ok`).

### 3. Calcul

- La comparaison se fait en `Decimal`, jamais en `float`, et **sans arrondi préalable** : on compare `spent` à `amount × seuil / 100` et à `amount`, pas un pourcentage arrondi. Exemple : `spent = 79.99`, `amount = 100.00` reste `ok`, même si l'affichage arrondit à 80 %.
- Le statut est calculé côté serveur, par un seul service (#50). L'API le renvoie dans le champ `status` (chaîne : `ok`, `warning`, `full`, `exceeded`) aux côtés de `spent` et `remaining`.
- L'interface Svelte **ne recalcule pas** le statut : elle affiche `status` tel quel. Les deux couches utilisent donc la même règle.

### 4. Affichage

Conformément à `docs/mvp-scope.md` (accessibilité), la couleur n'est jamais seule :

| Statut | Couleur | Texte |
|--------|---------|-------|
| `ok` | vert | « Dans le budget » |
| `warning` | jaune | « Attention » |
| `full` | orange | « Budget atteint » |
| `exceeded` | rouge | « Dépassé » |

---

## Raisonnement

- **80 %** laisse une marge d'action avant la limite, sans alerter trop tôt. C'est la valeur déjà retenue dans `docs/mvp-scope.md` et dans le contrat d'API.
- Distinguer `full` de `exceeded` évite d'afficher « Dépassé » à un utilisateur qui a pile consommé son budget : il n'a rien dépassé.
- Un seul calcul serveur évite que l'API et l'UI divergent aux bornes.

## Écarts avec les documents existants

- `docs/mvp-scope.md` (§ Budgets) décrit « ≥ 100 % = dépassement », des seuils codés en dur et trois couleurs. Cette décision remplace cette règle : 100 % exact devient `full`, le seuil est le champ `alert_threshold` (défaut 80 %), et il y a quatre statuts.
- `docs/api-design.md` ne contient pas encore le champ `status` : à ajouter aux réponses de `GET /api/budgets/` et `GET /api/budgets/{id}/` lors de #47.

## Conséquences

- #50 (service de consommation) implémente la table des statuts ci-dessus.
- #47 expose `status` dans l'API.
- #55 teste chaque borne : `seuil - 0.01`, `seuil`, `99.99`, `100`, `100.01`, ainsi que `alert_threshold = 100`.
