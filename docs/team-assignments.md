# Répartition des issues

| Membre | GitHub | Rôle | Issues |
|---|---|---|---|
| Tom | `tomvieilledent` | Produit, architecture, agentic, budgets (backend), audit sécurité | 26 |
| Jason | `ToujoursPareil8` | Backend : socle API, base de données, auth, dépenses, correctifs sécurité | 26 |
| Clément | `ClaymeCall` | Frontend, DevOps/Docker, accessibilité, documentation d'installation, démo | 26 |

## Tom — Produit, agentic, budgets, audit sécurité

**Kick-off (0)** : #2 charte d'équipe, #3 workflow Git/PR, #4 scope MVP, #5 ERD, #6 ownership des catégories, #7 contrat d'API, #8 copilot-instructions, #9 #10 #11 agents (Product, Full-Stack, QA & Sécurité), #12 agentic-log

**Budgets (3)** : #45 modèle Budget, #46 create, #47 list/get, #48 update, #49 delete, #50 service de consommation, #51 règles de seuil, #54 #55 #56 tests (doublons, consommation, ownership)

**Sécurité (4)** : #57 audit validation/autorisation/erreurs, #58 revue agent QA & Sécurité, #59 tri des findings

**Présentation (6)** : #77 talking points agentic, #78 dry-run + Q&A

## Jason — Backend

**Kick-off (0)** : #13 outil de migration, #14 squelette API, #16 PostgreSQL local, #17 route health check, #19 doc recréation BDD

**Auth (1)** : #20 modèle User, #21 hashing, #22 register, #23 login, #24 logout, #25 doc stratégie session/token, #26 current-user, #27 route protégée, #31 tests API auth

**Dépenses (2)** : #33 modèle Category, #34 modèle Expense, #35 create, #36 list, #37 update, #38 delete, #39 ownership, #43 tests API

**Sécurité (4)** : #60 XSS, #61 injections SQL, #62 erreurs sanitisées

**Livraison (5)** : #72 script de seed

## Clément — Frontend, DevOps, doc, démo

**Docker** : #1 docker compose (déjà assignée)

**Kick-off (0)** : #15 squelette Svelte, #18 premier écran

**Auth (1)** : #28 inscription, #29 login, #30 états loading/erreur/session expirée, #32 test front auth

**Dépenses (2)** : #40 liste, #41 formulaire, #42 suppression avec confirmation, #44 test front

**Budgets (3)** : #52 dashboard, #53 formulaire

**Qualité (4)** : #63 page privacy/légale, #64 responsive, #65 accessibilité, #66 plan de recette, #67 couverture tests, #68 éco-conception

**Livraison (5)** : #69 healthchecks compose, #70 `.env.example`, #71 migrations en conteneur, #73 README, #74 comptes démo et limites

**Présentation (6)** : #75 script de démo, #76 matériel architecture/modèle de données
