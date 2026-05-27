## Pass 1 — 2026-05-27

- **Decision:** moved test files with `git mv` to preserve history. The
  three integration files dropped their `_integration` infix per the
  solution-design rename (e.g. `test_tools_integration_io.py` →
  `tests/mcp/integration/test_tools_io.py`).
- **Decision:** split the old `tests/mcp/test_server.py` into two new
  files. The REQ-09 smoke test (`test_init_through_server_creates_workload_json`)
  moved to `tests/mcp/e2e/test_smoke.py` together with its `_isolate_env`
  autouse fixture, the module-level `_REAL_CLI_PATH = shutil.which(...)`
  capture, the `anyio_backend` fixture, and the imports it needs (`json`,
  `shutil`, `pathlib.Path`, `pytest`). The remaining REQ-01..REQ-07 unit
  tests moved to `tests/mcp/unit/test_server.py` with their own copy of
  `_isolate_env` and the `_RunRecorder`/`fake_cli` helpers. The two files
  intentionally each carry their own `_isolate_env` because they live in
  different tier folders and there is no shared conftest at `tests/mcp/`
  any more.
- **Decision:** added empty `__init__.py` to `tests/mcp/unit/`,
  `tests/mcp/integration/`, `tests/mcp/e2e/` to match the existing
  pattern (`tests/__init__.py`, `tests/mcp/__init__.py`) so pytest's
  rootdir / conftest discovery stays predictable.
- **Decision:** removed `tests/mcp/conftest.py` entirely. Its fixtures
  (real MCP server subprocess, real CLI) are integration-only and now
  live at `tests/mcp/integration/conftest.py`. Nothing at `tests/mcp/`
  any more — no risk of integration-only fixtures leaking into unit /
  e2e.
- **Decision:** `.python-version` contains exactly `3.14.5\n` (single
  trailing newline), matching the local `.venv` and the spec.
- **Decision:** `.github/workflows/ci.yml` defines three jobs
  (`unit`, `integration`, `e2e`), each on `ubuntu-latest`, triggered by
  `pull_request` against `main` and `push` to `main`. Workflow-level
  `concurrency` block keyed on `${{ github.workflow }}-${{ github.ref }}`
  with `cancel-in-progress: true`. Each job uses
  `actions/checkout@v4` then `actions/setup-python@v5` with
  `python-version-file: .python-version`, installs the project via
  `pip install -e ".[dev]"`, then runs `pytest tests/mcp/<tier>` for
  its tier. The `unit` job has no CLI install step. The `integration`
  and `e2e` jobs install the CLI with
  `pipx install git+https://github.com/ctracey/swc-workload-cli.git`
  and append `$HOME/.local/bin` to `$GITHUB_PATH` so subsequent steps
  resolve `swc-workload`. CLI install runs before `pip install -e` so
  the sequence reads top-to-bottom as setup → install → run.
- **Decision:** no shared composite action. The three jobs each inline
  their steps; duplication is minimal and a composite is overkill at
  this size (per solution.md).
- **Decision:** updated `.swc/mcp/architecture.md` folder-structure
  diagram to show the three tier subfolders under `tests/mcp/`. Did
  NOT rewrite older work-item docs (`workitems/3.2/*.md`, `changelog.md`,
  `workitems/3.2/summary.md`) that reference the old test paths — those
  are historical records of what existed at that time and per
  solution.md "don't rewrite history".
- **Verification:** ran `.venv/bin/pytest` from repo root — 129 passed,
  7 skipped in 14.97s. Matches the quality-baseline target exactly.
  Also verified each tier collects independently:
  - `pytest tests/mcp/unit` → 57 passed
  - `pytest tests/mcp/integration` → 71 passed, 7 skipped
  - `pytest tests/mcp/e2e` → 1 passed
  Sum: 57 + 71 + 1 = 129 passed, 7 skipped — every test accounted for.
- **Verification:** parsed `.github/workflows/ci.yml` with PyYAML —
  three jobs (`unit`, `integration`, `e2e`), triggers (`pull_request`,
  `push`), `runs-on: ubuntu-latest` everywhere. Cannot execute the
  workflow locally; CI behaviour validated on first push.
