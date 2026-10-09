# Décision — Propriété des catégories (Catégories scoped par utilisateur)

- **Date :** 2026-10-06
- **Auteur :** Tom Vieilledent (Product & Architecture Agent)
- **Issue liée :** #6
- **Statut :** Appliquée (`Category.user` et `GET /api/categories/` authentifié, dans `backend/api`).
- **Exécution :** Faite (modèle, migrations et endpoint présents sur `main`).

---

## Décision

**Les catégories de dépenses sont scoped par utilisateur.** Chaque utilisateur dispose de sa propre liste de catégories (Scénario B, non Scénario A « partagé »).

**Changement structurel :**
- Champ `user_id BIGINT NOT NULL FK → USER.id` ajouté à la table `Category`.
- Contrainte `UNIQUE(user_id, name)` : un utilisateur ne peut pas avoir deux catégories portant le même nom.
- Index sur `(user_id)` et `(user_id, name)` pour les requêtes courantes.
- `ON DELETE CASCADE` : supprimer un utilisateur supprime aussi ses catégories (et en cascade, ses dépenses/budgets orphelins).

---

## Raisonnement

### Principes guidant la décision

1. **Flexibilité du produit.**  
   Cashmire est un outil personnel de suivi de dépenses. Imposer une nomenclature globale limite l'adoption : chaque utilisateur a des habitudes et des vocabulaires différents. Le scoping par utilisateur laisse croître le produit.

2. **Confidentialité et éthique.**  
   Les catégories d'un utilisateur peuvent révéler des habitudes sensibles (« Thérapie », « Dettes », etc.). La séparation des données par utilisateur respecte la vie privée.

3. **Contrôles d'accès simples.**  
   Avec scoping par utilisateur, chaque catégorie appartient clairement à quelqu'un. Les validations API (`category.user_id == request.user.id`) sont triviales. Pas de logique de modération ou de droits complexes.

4. **Faible surcoût pour le MVP.**  
   Ajouter `user_id` et deux indices n'ajoute qu'une complexité SQL/storage négligeable (quelques lignes de migration).

5. **Extensibilité future.**  
   Si plus tard on veut des catégories partagées (ex. famille), on peut ajouter une table `SharedCategory` ou un flag de partage. Le modèle B le permet ; le A le rend impossible sans restructuration.

### Alternatives écartées

**Scénario A (Catégories partagées / globales) :**
- Rejeté : trop limitant pour une app financière personnelle.
- La nomenclature unique empêche la personnalisation.
- Extensibilité vers partage/famille impossible sans refonte.

---

## Compromis

### Acceptés

**Duplication de seed data :**  
Chaque utilisateur reçoit un ensemble de catégories par défaut (~15 catégories) à l'inscription. Cela double le stockage pour les catégories, mais le surcoût est négligeable (quelques centaines d'octets par utilisateur, vs. gigaoctets pour les dépenses/budgets plus tard).

**Requêtes API scoped :**  
Toutes les requêtes sur `Category` doivent filtrer par `user_id` (ex. `GET /api/categories/`). L'utilisateur est déduit de la session : aucun `user_id` n'apparaît dans le chemin, ce qui empêche d'atteindre les catégories d'un autre utilisateur en changeant un identifiant (voir `docs/api-design.md`).

### Rejetés

- Pas de modération centralisée (solution A nécessiterait une queue d'approbation).
- Pas de synchronisation automatique des catégories entre utilisateurs (si on ajoute « Bitcoin » aux defaults, les utilisateurs existants ne la reçoivent pas automatiquement).

---

## Implications

### Base de données

| Élément | Impact | Détail |
|--------|--------|--------|
| Table `CATEGORY` | Ajout de colonne | `user_id BIGINT NOT NULL FK` |
| Index | Ajout de 2 indices | `(user_id)` et `(user_id, name)` |
| Contrainte UNIQUE | Remplacement | De `UNIQUE(name)` à `UNIQUE(user_id, name)` |
| Migration | Création de migration | `002_add_category_user_id.py` (ou part de `002_initial_models.py`) |

### Code applicatif

| Composant | Impact | Détail |
|-----------|--------|--------|
| Modèle Django `Category` | Ajout de champ | `user = ForeignKey(User, on_delete=models.CASCADE)` |
| Sérialiser `CategorySerializer` | Légère modification | Inclure `user_id` en lecture, valider ownership en écriture |
| Permission `Category` | Implémentation | Checker `category.user.id == request.user.id` |
| Routes API | Scoping | Tous les GET/POST/PATCH/DELETE sur `/api/categories/` |
| Onboarding/Signup | Signal Django | `post_save` sur `User` → créer 15 catégories par défaut |
| Tests | Couverture complète | Vérifier ownership, empêcher accès cross-user, validation de seed data |

### UX / Frontend

| Point | Impact | Détail |
|------|--------|--------|
| Lister les catégories | Automatique | Les catégories de l'utilisateur connecté sont affichées. |
| Créer une catégorie | Nouveau champ possible | L'utilisateur peut créer des catégories personnalisées (future issue). |
| Seed data | Transparence | Les catégories par défaut sont créées automatiquement à l'inscription, aucune interaction requise. |

---

## Questions réservées

Les décisions suivantes relèvent d'une autre issue/discussion :

1. **Soft-delete vs. suppression physique :** Faut-il garder les catégories supprimées (flag `deleted_at`) ou les supprimer vraiment ?
2. **Gestion des dépenses orphelines :** Si on supprime une catégorie, que devient une dépense qui la référence ? (RESTRICT, SET NULL, KEEP)
3. **Édition et versioning :** Si un utilisateur renomme une catégorie de « Alimentation » à « Food », comment met-on à jour les dépenses anciennes ? (retroactif vs. prospectif)
4. **Ordonnement :** Faut-il un champ `order` pour que l'utilisateur arrange ses catégories en UI ?

---

## Date de révision

Pas de révision prévue sauf si :
- Une issue de confidentialité émerge.
- Le perf test montre que les indices sont insuffisants.
- Une nouvelle exigence produit rend le scoping obsolète.

Prévue : jamais (cette décision est destinée à durer pour la v1 et v2 du produit).

---

## Signatures d'approbation (avant implémentation)

| Rôle | Nom | Date | Signature |
|------|------|------|-----------|
| Product | Tom | — | À approuver |
| Backend Lead | Jason | — | À approuver |
| Frontend Lead | Clément | — | À approuver |

> **Attente :** Tous les trois doivent avoir lu et approuvé cette décision avant que le Full-Stack Development agent commence l'implémentation (migrations, modèles Django, API).

---

## Référencé par

- `docs/specs/issue-6-category-ownership.md` — Spec complète, analyse des deux scénarios.
- `docs/erd.md` — Diagramme ERD à mettre à jour avec cette décision.
- Issue #6 sur GitHub — Discussion et approbation officielle.

---

*Décision proposée par Agent Product & Architecture. À valider par l'équipe avant exécution.*
