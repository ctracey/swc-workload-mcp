# Specs — 6.2: Version sync — workflow to bump MCP service version, kept in sync with release tag

## Acceptance criteria

- `swc_workload_mcp/_version.py` exists with `__version__ = "0.1.0"`
  on a single line plus a trailing newline.
- `pyproject.toml`:
  - `[build-system]` declares `requires = ["hatchling"]` and
    `build-backend = "hatchling.build"`.
  - `[project]` no longer carries a literal `version = "0.1.0"` line;
    instead carries `dynamic = ["version"]`.
  - `[tool.hatch.version]` exists with `path = "swc_workload_mcp/_version.py"`.
  - `[tool.hatch.build.targets.wheel]` exists with
    `packages = ["swc_workload_mcp"]`.
  - The old setuptools-specific `[tool.setuptools.packages.find]`
    section is removed.
- `swc_workload_mcp/__init__.py` imports the version from
  `_version.py` (`from ._version import __version__`) so
  `swc_workload_mcp.__version__` keeps resolving to `"0.1.0"`.
- After the change, `uv pip install -e ".[dev]"` succeeds and the
  full test suite passes with the existing totals (129 passed, 7
  skipped).
- `.github/workflows/release.yml` exists with:
  - `on: workflow_dispatch` carrying a `bump` choice input (`patch`,
    `minor`, `major`).
  - `permissions: contents: write`.
  - A single `release` job on `ubuntu-latest`, gated by
    `if: github.ref == 'refs/heads/main'`.
  - Steps: checkout (full history) → setup-python (from
    `.python-version`) → bump version in
    `swc_workload_mcp/_version.py` (semver bump inline Python script)
    → commit + tag `vX.Y.Z` + push both → create GitHub Release via
    `softprops/action-gh-release@v2` with
    `generate_release_notes: true`.
  - Commit identity: `github-actions[bot]` with the standard noreply
    email.
- The workflow can be successfully triggered from the GitHub Actions
  UI (or `gh workflow run release.yml -f bump=patch`) once merged to
  main. This is verified manually after merge — not in this work
  item's automated checks.

## Error cases

- If a workflow run is dispatched against a non-`main` ref, the
  `if: github.ref == 'refs/heads/main'` guard must skip the job
  cleanly (no partial bump, no orphan tag).
- If the inline bump script fails to parse `__version__` (e.g.
  unexpected format), it must exit non-zero before the commit/tag
  step runs, so a malformed version state never lands on `main`.
