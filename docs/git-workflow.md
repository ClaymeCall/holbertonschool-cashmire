# Git Workflow

Every change reaches `main` through a reviewed pull request.

## Branches

- Format: `<type>/<issue>-<slug>`, e.g. `feat/45-budget-model`.
- `<type>` is one of the Conventional Commit types below; `<issue>` is the GitHub issue number; `<slug>` is a short, lowercase, hyphenated description.
- One branch per issue. Do not bundle several issues in one branch.
- Branch from an up-to-date `main`.

## Commits

Commits follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope][!]: <description>

[optional body]

[optional footer(s)]
```

- Types: `feat`, `fix`, `docs`, `refactor`, `chore`, `test`, `style`, `build`, `ci`, `perf`, `revert`.
  - `feat` adds a feature; `fix` corrects a bug.
- Scope is optional, in parentheses right after the type, e.g. `fix(parser): ...`.
- Description is required, short, lowercase type, imperative mood ("add", not "added").
- Body is optional, separated from the description by a blank line.
- Footers are optional, separated from the body by a blank line, in `Token: value` form (`-` instead of spaces in the token, except `BREAKING CHANGE`).
- Breaking change: add `!` before the `:` or a `BREAKING CHANGE: <description>` footer.
- One change type per commit. Mixed changes are split into several commits.

## Pull requests

- Target branch: `main`.
- The description includes `Closes #N` for the issue it resolves.
- Tests must pass before requesting review.
- At least one member other than the author must approve before merge.
- Never approve your own PR.
- Delete the branch after merge.

## Protection of `main`

- Pull request required; no direct pushes.
- Minimum 1 approving review.
- Force pushes disabled.
