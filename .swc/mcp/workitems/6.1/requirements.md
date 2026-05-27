# Requirements — 6.1: GitHub Actions pipeline for PR and main (lint, test)

## Intent

Add a GitHub Actions workflow that runs the existing pytest suite on
every PR against `main` and every push to `main`, so regressions are
caught before merge and main stays green. Surface three distinct PR
checks — `unit`, `integration`, `e2e` — so failures are immediately
attributable to a tier. Bundles a `tests/mcp/` restructure into
`unit/` / `integration/` / `e2e/` subfolders so each job points at one
folder and the layout is self-documenting. This is the foundation for
the version-sync (6.2) and README badge (6.3) work items.

## Constraints

- **Tests only.** Lint is out of scope — handled in a future work
  item.
- **Three independent jobs visible in the PR Checks panel:** `unit`,
  `integration`, `e2e`.
- **CLI install:** the `unit` job must **not** install the
  `swc-workload` CLI (faster, decoupled). The `integration` and `e2e`
  jobs install the CLI from `ctracey/swc-workload-cli` before running
  pytest, because both tiers exercise the real CLI subprocess and fail
  loudly if it's missing (per the design decision in `notes.md`).
- **Python pin:** a new `.python-version` file at repo root pinned to
  the latest stable Python — `3.14.5` (verified against python.org on
  2026-05-27). The CI workflow's `setup-python` step reads from
  `.python-version` rather than hard-coding the version, so local dev
  and CI stay aligned.
- **Single OS:** `ubuntu-latest`.
- **Triggers:** `pull_request` against `main`, `push` to `main`.
- **Restructure preserves behaviour.** Tests move locations but their
  content does not change. The full suite still passes after the
  restructure, locally and in CI.

## Out of scope

- Lint (ruff/black/flake8/mypy) — future work item.
- Multi-OS matrix (macOS, Windows).
- Multi-Python matrix.
- Coverage reports / coverage upload.
- Security scans (e.g. CodeQL, dependabot).
- Scheduled runs (cron).
- Tag-triggered builds (covered by 6.2 version sync).
- Pytest markers — the folder restructure obviates the need for them.
- Automatic registration of the workflow with branch protection
  rules — left to the maintainer to wire up in GitHub settings.

## Approach direction

1. **Restructure `tests/mcp/` into three tier-folders:**
   - `tests/mcp/unit/` — `test_bridge.py`, `test_tools.py`, and the
     unit tests from `test_server.py` (everything except the REQ-09
     smoke test).
   - `tests/mcp/integration/` — the three `test_tools_integration_*.py`
     files (renamed to drop the `_integration` infix) plus the shared
     `conftest.py` that today lives at `tests/mcp/conftest.py`. The
     conftest moves down a level because only integration tests use
     it.
   - `tests/mcp/e2e/` — the REQ-09 smoke test (`test_init_through_server_creates_workload_json`)
     extracted from `test_server.py` into `test_smoke.py`.
2. **Add `.python-version`** at the repo root pinned to `3.14.5`.
3. **Add `.github/workflows/ci.yml`** with three jobs (`unit`,
   `integration`, `e2e`). Each job runs:
   `checkout → setup-python (python-version-file: .python-version) →
   pip install -e ".[dev]" → pytest tests/mcp/<tier>`.
   Integration and e2e jobs additionally install the CLI from
   `ctracey/swc-workload-cli` before pytest.

## Parked

The following are implementation-level details to resolve in specs /
solution-design:

- Exact shape of the REQ-09 extraction — which imports/helpers move
  with it from `test_server.py`, whether anything stays shared.
- CLI install command shape — `pip install git+https://...` vs. clone
  + install vs. `pipx`.
- Whether to extract shared workflow setup steps into a reusable
  composite action, or accept some duplication across three jobs for
  simplicity.
- Whether `pytest tests/mcp/<tier>` collects the right tests without
  needing any `__init__.py` additions / changes.
- Whether the existing `tests/__init__.py` (if any) needs to be
  preserved or moved.
