## Description

<!-- Briefly describe the changes in this PR -->

## Related Issue

<!-- Link to the issue this PR addresses, e.g. "Closes #123" -->

## Change Type

- [ ] feat — new feature
- [ ] fix — bug fix
- [ ] docs — documentation
- [ ] refactor — code refactoring
- [ ] test — adding or updating tests
- [ ] ci — CI/CD changes

## Testing Done

<!-- Describe what testing you performed.
     Backend changes: run `make ci` (lint + tests) or, from the `quantara/` directory,
     `poetry run pytest web_app/tests -v --tb=short` for tests and `make lint` for lint.
     Frontend changes: run `make frontend-test` and `make frontend-lint`. -->

## Screenshots (if UI changes)

<!-- Add screenshots to help reviewers understand visual changes -->

## Environment Variables

<!-- List any new, removed, or changed environment variables, and call out
     any docs (e.g. `.env.example`, README, deployment runbook) that need a
     matching update. If none, write "None". -->

## Checklist

- [ ] `make lint` passes (pylint on changed `.py` files)
- [ ] `make test` passes (pytest in `quantara/web_app/tests/`)
- [ ] CI is green on this PR
- [ ] Documentation updated (if applicable)
- [ ] PR is linked to a related issue (`Closes #<n>`)
