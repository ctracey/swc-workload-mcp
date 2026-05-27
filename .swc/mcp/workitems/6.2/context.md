# Context — 6.2: Version sync — workflow to bump MCP service version, kept in sync with release tag

## Pass 1 — 2026-05-27

- **Decision:** implemented inline by the orchestrator (not a spawned
  general-purpose agent) at the user's direction ("zip through the
  stages and make the changes"). Scope was small, mechanical, and
  fully specified by mirroring the swc-workload-cli pattern.
- **Decision:** four files touched, all matching solution.md:
  - Created `swc_workload_mcp/_version.py` — single line
    `__version__ = "0.1.0"` plus trailing newline.
  - Rewrote `swc_workload_mcp/__init__.py` to keep the module
    docstring and re-export via `from ._version import __version__`,
    plus an `__all__ = ["__version__"]` so the public API surface is
    explicit.
  - Rewrote `pyproject.toml`: swapped `[build-system]` from
    setuptools to hatchling, dropped `version = "0.1.0"` from
    `[project]` and added `dynamic = ["version"]`, removed
    `[tool.setuptools.packages.find]`, added `[tool.hatch.version]`
    pointing at `_version.py`, added `[tool.hatch.build.targets.wheel]
    packages = ["swc_workload_mcp"]`.
  - Created `.github/workflows/release.yml` mirroring CLI's
    `release.yml` verbatim except for two intentional divergences:
    (a) path is `swc_workload_mcp/_version.py`, (b)
    `python-version-file: .python-version` instead of hardcoded
    `python-version: "3.12"`.
- **Decision unplanned in solution.md:** add
  `[tool.hatch.metadata] allow-direct-references = true`. Hatchling
  refuses git-URL direct references in `dependencies` /
  `optional-dependencies` by default — the CLI's pyproject doesn't
  hit this because the CLI itself has no git-URL deps. We do
  (`swc-workload @ git+...` in `dev`). One-line opt-in. Documented
  with a `# Allow ... direct reference in dev deps.` comment so the
  reason is on the line.
- **Verification:** clean reinstall via `rm -rf .venv
  swc_workload_mcp.egg-info && uv venv && uv pip install -e ".[dev]"`
  succeeds; pip output shows `swc-workload-mcp==0.1.0` confirming
  Hatchling read the version from `_version.py`.
- **Verification:** `.venv/bin/python -c "import swc_workload_mcp;
  print(swc_workload_mcp.__version__)"` prints `0.1.0` — the
  re-export through `__init__.py` works, so any consumer doing
  `swc_workload_mcp.__version__` continues to resolve.
- **Verification:** `make test` → 129 passed, 7 skipped in 15.39s.
  Matches the quality baseline exactly. No regressions from the build
  backend swap.
- **Verification:** YAML parsed via `uv run --with pyyaml` — the
  workflow has four top-level keys (`name`, `on`, `permissions`,
  `jobs`). The `on:` key shows up as `True` in the parsed dict; that's
  YAML 1.1's boolean coercion of unquoted `on/off/yes/no` keys.
  Harmless — GitHub Actions parses YAML with its own loader and
  treats this correctly. The CLI's workflow has the same shape.
- **Note:** the release workflow itself cannot be exercised inside
  this work item — triggering it would cut a real release. Its
  correctness rests on (a) verbatim parity with the CLI's working
  workflow, (b) clean YAML parse, (c) the bump script being pure
  Python stdlib (`os`, `re`, `pathlib`) with deterministic behaviour
  trivially traceable by reading the file.
- **Note:** `swc_workload_mcp.egg-info/` (left over from the old
  setuptools install) was deleted at the start of the rebuild. It was
  already gitignored so no commit churn.
