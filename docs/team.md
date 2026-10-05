# Team charter

Cashmire is built by a team of three. This document is the shared reference for who owns what and how we work together.

## Roster

| Member | GitHub | Primary area of ownership |
|---|---|---|
| Tom | `tomvieilledent` | Product & architecture, agentic workflow, budgets backend, security audit |
| Jason | `ToujoursPareil8` | Backend: API skeleton, database, authentication, expenses, security fixes |
| Clément | `ClaymeCall` | Frontend, Docker/DevOps, accessibility, install docs, demo |

## Responsibilities

### Tom
- Kick-off: team charter, Git workflow, MVP scope, ERD, category ownership decision, API contract, `copilot-instructions.md`, the three custom agents, `agentic-log.md` (#2–#12)
- Budgets backend: model, CRUD endpoints, consumption service, threshold rules, tests (#45–#51, #54–#56)
- Security audit: input validation/authorization review, QA & Security agent run, findings triage (#57–#59)
- Presentation: agentic talking points, dry-run and Q&A (#77, #78)

### Jason
- Backend foundations: migration tool, API skeleton, local PostgreSQL, health check, database recreation doc (#13, #14, #16, #17, #19)
- Authentication: User model, password hashing, register/login/logout, session/token strategy, current-user dependency, protected route, API tests (#20–#27, #31)
- Expenses: Category and Expense models, CRUD endpoints, ownership checks, API tests (#33–#39, #43)
- Security fixes: XSS, SQL injection, sanitized error responses (#60–#62)
- Demo seed data script (#72)

### Clément
- Docker compose (#1), healthchecks, `.env.example`, migrations in containers (#69–#71)
- Frontend: Svelte skeleton and first screen, auth forms and states, expense list/form/delete, budget dashboard/form, front-end tests (#15, #18, #28–#30, #32, #40–#42, #44, #52, #53)
- Quality: privacy page, responsive layout, accessibility, acceptance test plan, test coverage, eco-design (#63–#68)
- Documentation and demo: README, demo accounts and known limitations, full-journey demo script, architecture and data model materials (#73–#76)

Each issue has exactly one assignee. The assignee is accountable for it, even when others help.

## Working agreement

### Meeting cadence
- Daily stand-up, 15 minutes, every morning: what was done, what is next, what is blocked.
- Short end-of-day sync to check progress against the day's milestone.

### Communication
- Team chat for day-to-day coordination.
- Technical discussion happens in the issue or pull request it concerns, so decisions stay traceable.
- Decisions that affect everyone (API contract, data model, scope) are written in `docs/` before implementation.

### Raising blockers
- Raise a blocker as soon as it has lasted more than 30 minutes.
- Post it in the team chat and comment on the related issue.
- Whoever is free helps; the issue assignee stays responsible for closing it.

### Code and review
- One branch per issue, Conventional Commits, and every change merged to `main` through a pull request reviewed by another member (see the Git workflow document, issue #3).
- Nobody approves their own pull request.

### Changing ownership
- Reassigning an issue is done in the issue, with the agreement of both people involved.

## Agreement

Each member confirms this document by approving the pull request that introduces it.

- [ ] Tom
- [ ] Jason
- [ ] Clément
