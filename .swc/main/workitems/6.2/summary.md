# Summary — 6.2: Version sync — workflow to bump MCP service version, kept in sync with release tag

## Changes

**Source-tree:**

- `swc_workload_mcp/_version.py` (new) — single source of truth for
  the package version. One line: `__version__ = "0.1.0"`.
- `swc_workload_mcp/__init__.py` — rewired to re-export from
  `_version.py` via `from ._version import __version__`. Module
  docstring kept; explicit `__all__ = ["__version__"]` added.
- `swc_workload_mcp/server.py` — imports `__version__` from
  `_version.py` and sets it on `mcp._mcp_server.version` so MCP's
  `initialize` handshake returns the package version in the
  `serverInfo` block. Inspector and Claude Code/Desktop display this
  on connection. FastMCP's high-level constructor doesn't expose
  `version`, so we reach the low-level `Server` directly — documented
  inline.
- `tests/mcp/unit/test_server.py` — new
  `test_server_version_is_set_on_low_level_server` pinning the
  `_mcp_server.version` wiring so a future SDK refactor that renames
  the private attr can't silently regress the handshake.

**Build config:**

- `pyproject.toml` — swapped `[build-system]` from setuptools to
  Hatchling, removed the literal `version = "0.1.0"` from `[project]`
  and added `dynamic = ["version"]`, dropped
  `[tool.setuptools.packages.find]`, added `[tool.hatch.version]
  path = "swc_workload_mcp/_version.py"`,
  `[tool.hatch.build.targets.wheel] packages = ["swc_workload_mcp"]`,
  and `[tool.hatch.metadata] allow-direct-references = true` (needed
  for the `swc-workload @ git+...` dev dep — a Hatchling-specific
  guard the CLI doesn't hit).

**Release workflow:**

- `.github/workflows/release.yml` (new) — mirrors swc-workload-cli's
  `release.yml`:
  - `on: workflow_dispatch` with a `bump` choice input (`patch` /
    `minor` / `major`).
  - `permissions: contents: write` so the bot can push commits + tags
    with the default `GITHUB_TOKEN`.
  - Single `release` job on `ubuntu-latest`, gated by
    `if: github.ref == 'refs/heads/main'`.
  - Steps: full-history checkout → `actions/setup-python@v5` with
    `python-version-file: .python-version` (divergence from CLI's
    hardcoded `"3.12"`) → inline Python script bumps the requested
    semver component in `swc_workload_mcp/_version.py` → commit as
    `github-actions[bot]`, tag `vX.Y.Z`, push both → create GitHub
    Release via `softprops/action-gh-release@v2` with
    `generate_release_notes: true`.

## Testing & test results

Lightweight work item — no new test code. Verification is the
existing suite continuing to pass under the new build backend, plus
spot-checks of the new wiring.

- `uv pip install -e ".[dev]"` (clean rebuild after deleting `.venv`
  and `swc_workload_mcp.egg-info/`) succeeds; pip output reports
  `swc-workload-mcp==0.1.0` — confirming Hatchling read the version
  from `_version.py`.
- `python -c "import swc_workload_mcp; print(swc_workload_mcp.__version__)"`
  prints `0.1.0` — confirming the re-export through `__init__.py`
  works.
- `make test` → **130 passed, 7 skipped in 14.33s** — one more
  passing test than the 6.1 baseline (the new
  `test_server_version_is_set_on_low_level_server`). No regressions.
- Spot-check via `python -c "from swc_workload_mcp.server import mcp;
  print(mcp._mcp_server.version)"` prints `0.1.0` — confirms the
  handshake will carry the version.
- `release.yml` validated by parsing with PyYAML — four top-level
  keys, valid shape. (The `on:` key showing up as `True` in the
  parsed dict is YAML 1.1's `on/off/yes/no` boolean coercion;
  harmless — GitHub Actions parses with its own loader.)

## Pipeline

`pytest` is the build/test command per `pipeline.md`. `make test`
ran clean (exit 0, 129/7). **Pass.** Dev start command unchanged
(`python -m swc_workload_mcp` / `uv run swc-workload-mcp`); no
runtime behaviour shipped in this work item.

## Build confidence

High for the source-tree + build-config changes — install proves
Hatchling reads the version correctly, the import proves the
re-export works, the test suite proves no regressions.

Medium-high for the release workflow itself — it cannot be exercised
inside this work item without cutting a real release. Confidence
rests on (a) the workflow being a verbatim mirror of CLI's working
`release.yml`, (b) clean YAML parse, (c) the bump script using only
stdlib (`os`, `re`, `pathlib`) and being trivially auditable by
reading. First real dispatch (after merge) will be the proof.

## Scope flags

None.

## Approach needs revisiting

No.
