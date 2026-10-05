# Git Workflow

## Branch naming

Format: `<type>/<issue>-<slug>`

- `<type>`: a Conventional Commits type (`feat`, `fix`, `docs`, `refactor`, `chore`, `test`, ...).
- `<issue>`: GitHub issue number.
- `<slug>`: short, lowercase, hyphenated description.
- Example: `feat/45-budget-model`.
- One branch per issue, created from an up-to-date `main`.

## Commits

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope][!]: <description>

[optional body]

[optional footer(s)]
```

- Types: `feat`, `fix`, `docs`, `refactor`, `chore`, `test`, `style`, `build`, `ci`, `perf`, `revert`.
- Description: short, imperative, required.
- Breaking change: `!` before the `:` or a `BREAKING CHANGE:` footer.
- One type of change per commit.

## Pull requests

- Target `main` and reference the issue (`Closes #N`).
- Tests must pass before requesting review.
- At least one member other than the author must review and approve before merge.
- Authors never approve their own PR.

## `main` protection

- No direct pushes: changes go through a pull request.
- At least 1 approving review required.
- Force pushes and branch deletion disabled.
