# Specs — 6.1: GitHub Actions pipeline for PR and main (lint, test)

## Acceptance criteria

- After the restructure, running `pytest` locally from the repo root
  collects and passes every test that was passing before — same count,
  same outcomes.
- The new layout exists: `tests/mcp/unit/`,
  `tests/mcp/integration/`, `tests/mcp/e2e/`. The old flat layout
  (`tests/mcp/test_bridge.py` etc. at the top of `tests/mcp/`) is
  gone.
- `tests/mcp/integration/conftest.py` exists and contains the
  fixtures that previously lived at `tests/mcp/conftest.py`. No
  conftest remains at `tests/mcp/` that could leak integration-only
  fixtures into the `unit` / `e2e` tiers.
- `.python-version` exists at the repo root containing exactly
  `3.14.5` (no trailing whitespace beyond a single newline).
- `.github/workflows/ci.yml` exists and is triggered by:
  - `pull_request` against `main`
  - `push` to `main`
- The workflow defines exactly three jobs named `unit`,
  `integration`, and `e2e`. Each appears as its own check in the GitHub
  PR Checks panel.
- Each job:
  - Runs on `ubuntu-latest`.
  - Checks out the repo.
  - Sets up Python using `actions/setup-python` with
    `python-version-file: .python-version`.
  - Installs the project with dev deps:
    `pip install -e ".[dev]"`.
  - Runs `pytest tests/mcp/<tier>` for its own tier.
- The `integration` and `e2e` jobs additionally install the
  `swc-workload` CLI from `https://github.com/ctracey/swc-workload-cli`
  before running pytest, such that `swc-workload` is resolvable on
  PATH when pytest runs.
- The `unit` job does **not** install the CLI.
- All three jobs pass on a clean run against the current code.

## Error cases

- If `pytest` would fail after the restructure (e.g. a misplaced test
  or a broken import path), the work item is not done — the
  restructure must be behaviour-preserving.
- If the `integration` or `e2e` job runs without the CLI on PATH, it
  must fail loudly (per the existing design in `notes.md`), not skip
  silently.
