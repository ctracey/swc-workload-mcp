# Solution Design — 6.1: GitHub Actions pipeline for PR and main (lint, test)

## Approach

Two coordinated changes land in this work item:

1. **Restructure `tests/mcp/`** into three tier subfolders — `unit/`,
   `integration/`, `e2e/` — so each CI job points at one folder and
   the layout is self-documenting. Files move; their contents do
   not change.
2. **Add `.github/workflows/ci.yml`** with three independent jobs
   (`unit`, `integration`, `e2e`) that each appear as a distinct check
   in the GitHub PR Checks panel. Plus `.python-version` at the repo
   root pinning Python to `3.14.5`, read by CI via
   `actions/setup-python`'s `python-version-file:` input.

## Test approach

Lightweight — implement directly against the spec checklist. No new
test code is written. The existing pytest suite is the verification:
after the restructure, `pytest` (from the repo root) must collect and
pass every test that was passing before, with the same count and
outcomes.

## Technical decisions

- **CLI install in CI uses `pipx`.** Install command:
  `pipx install git+https://github.com/ctracey/swc-workload-cli.git`.
  Run only in the `integration` and `e2e` jobs; not in `unit`.
  `pipx` is preinstalled on `ubuntu-latest` runners. After install,
  the workflow must ensure `~/.local/bin` is on `PATH` (use
  `pipx ensurepath` or `echo "$HOME/.local/bin" >> $GITHUB_PATH`)
  so subsequent steps can resolve `swc-workload`.
- **Concurrency for rapid pushes.** Add a workflow-level
  `concurrency:` block keyed on `${{ github.workflow }}-${{ github.ref }}`
  with `cancel-in-progress: true`. Standard GitHub Actions practice:
  pushing a new commit to a PR cancels any in-flight run for the
  earlier commit on the same ref, saving runner minutes.
- **Conftest scoping.** The current `tests/mcp/conftest.py` only
  contains integration fixtures (real MCP server subprocess + real
  CLI). Move it to `tests/mcp/integration/conftest.py` so its
  fixtures don't leak into `unit/` or `e2e/`. No conftest file
  remains at `tests/mcp/`.
- **`__init__.py` in tier subdirs.** The existing test layout uses
  `__init__.py` at `tests/__init__.py` and `tests/mcp/__init__.py`.
  Maintain that pattern — add `__init__.py` to each new tier
  subdir (`unit/`, `integration/`, `e2e/`).
- **REQ-09 e2e extraction.** Move the test
  `test_init_through_server_creates_workload_json` (currently at
  `tests/mcp/test_server.py:335`) plus its supporting fixtures
  (`anyio_backend`, the `_isolate_env` autouse fixture, and the
  module-level `_REAL_CLI_PATH` capture via
  `shutil.which("swc-workload")`) into
  `tests/mcp/e2e/test_smoke.py`. Carry across the imports it needs
  (`pytest`, `json`, `shutil`, `pathlib.Path`, `swc_workload_mcp`,
  the in-memory client helper). The remaining tests in
  `test_server.py` stay together and move as a whole into
  `tests/mcp/unit/test_server.py` along with whatever shared module-
  level scaffolding (imports, the `_isolate_env` fixture if still
  needed there, etc.) they depend on.
- **No shared composite action.** Three jobs each inline their own
  steps. The duplication is minimal and a composite is overkill for
  this size.
- **Integration test file rename.** Drop the `_integration` infix
  when moving — `test_tools_integration_io.py` becomes
  `tests/mcp/integration/test_tools_io.py`, and similarly for the
  other two. The folder name already communicates the tier.

## Notes

- After the file moves, run `pytest` once locally to confirm the
  suite still passes before adding the workflow file. If anything
  fails, fix the move first — the workflow shouldn't be debugged
  against a broken restructure.
- The `integration` conftest captures `_REAL_CLI_PATH = shutil.which("swc-workload")`
  at module import; the `e2e` smoke does the same. Both will be `None`
  in CI if the CLI install step ran but `~/.local/bin` isn't on
  `PATH` yet — order the workflow steps so install + `PATH` export
  happens before `pip install -e ".[dev]"` (which imports nothing
  CLI-dependent, but keeps the sequence intuitive) and definitely
  before `pytest`.
- Update any references inside `notes.md`, `pipeline.md` (if it
  exists), or older `workitems/<N>/specs.md` files that point at
  the old test paths. Keep updates minimal — only fix paths that
  would mislead a future reader; don't rewrite history.

## Deferred

- Pytest markers (`@pytest.mark.integration` etc.) — the folder
  layout makes them unnecessary.
- Composite action for shared workflow setup — revisit if the
  workflow grows.
- Lint job (ruff/black/flake8/mypy) — separate future work item.
