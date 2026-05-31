# Quality Baseline — 6.1: GitHub Actions pipeline for PR and main (lint, test)

## Commands run

- `.venv/bin/pytest` — **pass**: 129 passed, 7 skipped in 15.0s
  (Python 3.14.5, pytest 9.0.3, anyio 4.13.0; rootdir at repo root,
  configfile resolved to `pyproject.toml` with no explicit
  `[tool.pytest]` section).

## Findings

All tests passed at baseline. The 7 skipped tests are pre-existing
and in scope for the restructure: they must remain skipped after the
move (not converted to passes, not converted to failures). They appear
across the three integration files:

- `tests/mcp/test_tools_integration_authoring.py` — 1 skip
- `tests/mcp/test_tools_integration_io.py` — 6 skips

These all live in the integration tier and will move into
`tests/mcp/integration/` together.

## Decisions

- After the restructure, the agent must reach the same totals when
  running `pytest` from the repo root: **129 passed, 7 skipped**.
  Any change in the totals (new failures, new skips, lost tests) is
  a regression and blocks completion.
- Local Python is already 3.14.5 — incidental, but it means the new
  `.python-version` file will match what the repo's `.venv` already
  uses.
