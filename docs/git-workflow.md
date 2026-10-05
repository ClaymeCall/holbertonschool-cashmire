# Git Workflow

Short reference for branching, committing, opening PRs and merging.

## 1. Branch naming

Format: `<type>/<issue>-<slug>`

- `<type>`: one of the Conventional Commit types (see section 2).
- `<issue>`: GitHub issue number.
- `<slug>`: short kebab-case summary.

Examples: `docs/3-git-workflow`, `feat/12-expense-crud`.

Rules:

- One branch per issue.
- Always create the branch from an up-to-date `main`:

```bash
git switch main && git pull && git switch -c <branch>
```

## 2. Commit messages (Conventional Commits)

Format: `<type>[optional scope][!]: <description>`

Allowed types: `feat`, `fix`, `docs`, `refactor`, `chore`, `test`, `style`,
`build`, `ci`, `perf`, `revert`.

Rules:

- Description: short, imperative mood ("add", not "added").
- Optional body, separated from the description by a blank line.
- Optional footers, separated from the body by a blank line, format
  `Token: value` (e.g. `Refs: #3`).
- Breaking change: `!` before the `:` OR a `BREAKING CHANGE: <description>`
  footer.
- One change type per commit; split mixed changes into several commits.

Examples:

```text
docs: add git workflow guide
```

```text
feat(expenses): add expense creation endpoint

Validate amounts as Decimal and attach the expense to the
authenticated user.

Refs: #12
```

```text
refactor(api)!: rename expense routes

BREAKING CHANGE: /expense/ is now /expenses/.
```

## 3. Pull request requirements

- Target branch: `main`.
- The PR description contains `Closes #N` linking the issue.
- All tests pass before merge.
- At least one team member other than the author reviews and approves before
  merge.
- No self-approval; the author never merges without another member's approval.

## 4. Branch protection on `main`

Expected GitHub settings (configured manually by a repo admin):

- Pull request required before merging (no direct pushes).
- At least 1 approving review required.
- Force pushes disallowed.
