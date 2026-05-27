# Summary — 6.1: GitHub Actions pipeline for PR and main (lint, test)

## Changes

**Test restructure** (`tests/mcp/` → three tier folders):

- `tests/mcp/unit/test_bridge.py` — moved via `git mv`.
- `tests/mcp/unit/test_tools.py` — moved via `git mv`.
- `tests/mcp/unit/test_server.py` — new file; REQ-01..REQ-07 unit
  tests extracted from the old `tests/mcp/test_server.py` together
  with their `_isolate_env`, `fake_cli`, and `_RunRecorder`
  scaffolding.
- `tests/mcp/integration/conftest.py` — moved via `git mv` from
  `tests/mcp/conftest.py`. No `conftest.py` remains at `tests/mcp/`
  so integration-only fixtures (real MCP server subprocess, real CLI)
  cannot leak into `unit/` or `e2e/`.
- `tests/mcp/integration/test_tools_authoring.py` — moved, dropped
  the `_integration` infix.
- `tests/mcp/integration/test_tools_io.py` — moved, dropped the
  `_integration` infix.
- `tests/mcp/integration/test_tools_status.py` — moved, dropped the
  `_integration` infix.
- `tests/mcp/e2e/test_smoke.py` — new file; REQ-09 e2e smoke
  extracted from the old `test_server.py` together with its
  `_isolate_env`, `anyio_backend`, and module-level
  `_REAL_CLI_PATH = shutil.which("swc-workload")` capture.
- Deleted `tests/mcp/test_server.py` (replaced by the unit/e2e split
  above).
- Added `__init__.py` to each new tier subfolder (`unit/`,
  `integration/`, `e2e/`) to match the existing `tests/__init__.py`
  and `tests/mcp/__init__.py` convention.

**New files at repo root:**

- `.python-version` — pinned to `3.14.5` (single line + trailing
  newline). Verified latest stable on 2026-05-27.
- `.github/workflows/ci.yml` — workflow with three jobs (`unit`,
  `integration`, `e2e`) on `ubuntu-latest`. Triggered by
  `pull_request` against `main` and `push` to `main`. Workflow-level
  `concurrency` block keyed on `${{ github.workflow }}-${{ github.ref }}`
  with `cancel-in-progress: true`. Each job:
  `actions/checkout@v4` → `actions/setup-python@v5` with
  `python-version-file: .python-version` → `pip install -e ".[dev]"`
  → `pytest tests/mcp/<tier>`. No separate CLI install step — the CLI
  comes in via dev deps (see `pyproject.toml` change below). The
  `unit` job installs it too but doesn't exercise it.

**Tooling changes:**

- `pyproject.toml` — added
  `swc-workload @ git+https://github.com/ctracey/swc-workload-cli.git`
  under `[project.optional-dependencies].dev`. This makes the CLI
  install automatically with `pip install -e ".[dev]"` (or
  `uv pip install -e ".[dev]"`), landing at `.venv/bin/swc-workload`.
  Same mechanism powers the CI `integration`/`e2e` jobs — no pipx,
  no separate install step.
- `.gitignore` — added `uv.lock` so the auto-generated uv lockfile is
  not committed. Consistent with the "track CLI HEAD" decision in
  tech-debt — pinning the lockfile would contradict that intent.

**Doc updates:**

- `README.md` — rewrote Install to use `uv venv` + `uv pip install -e ".[dev]"`,
  noting the CLI lands inside the venv automatically. Rewrote
  Prerequisites to clarify the CLI is auto-installed for dev and only
  needs a separate install for production deployment. Rewrote Tests
  to document the three tiers (table), show `uv run pytest` for full
  or per-tier runs, and describe what CI runs.
- `.swc/mcp/architecture.md` — folder-structure diagram updated to
  show the three tier subfolders under `tests/mcp/`. Older work-item
  docs (`workitems/3.2/*.md`, `changelog.md`) were intentionally not
  rewritten — they record what existed at the time, per solution.md
  guidance.

## Testing & test results

Lightweight work item — no new test code. Verification is the
existing pytest suite continuing to pass with baseline totals.

- Full suite (`.venv/bin/pytest` from repo root): **129 passed, 7
  skipped in 14.45s** — exact match to the quality baseline (129
  pass, 7 skip).
- Per-tier collection (mirrors what CI will run):
  - `pytest tests/mcp/unit` → 57 passed
  - `pytest tests/mcp/integration` → 71 passed, 7 skipped
  - `pytest tests/mcp/e2e` → 1 passed
  - Sum: 57 + 71 + 1 = 129 passed, 7 skipped — every baseline test
    accounted for.
- `ci.yml` parsed with PyYAML to confirm shape: three jobs, two
  triggers, all `ubuntu-latest`. Runtime behaviour will be observed
  on first push.

## Pipeline

`pytest` is the build/test command for this repo. Ran
`.venv/bin/pytest`: exit 0, 129 passed, 7 skipped. **Pass.** The dev
start command (`python -m swc_workload_mcp`) is an interactive MCP
server with no automatable health check — confidence comes instead
from the green e2e and integration tiers.

## Build confidence

High. Suite matches baseline test-for-test and within ~0.5s of the
baseline runtime. Per-tier invocation verified locally, so CI's
tier-folder pytest calls are known to work. Workflow YAML parses
cleanly. The only thing that cannot be verified pre-push is the
GitHub Actions runtime — runner image, `pipx` availability on the
runner, ordering of `$GITHUB_PATH` updates against the CLI's exec
bit — and that surfaces on first PR.

## Scope flags

None.

## Approach needs revisiting

No.
