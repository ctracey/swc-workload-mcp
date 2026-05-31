# Solution Design — 6.2: Version sync — workflow to bump MCP service version, kept in sync with release tag

## Approach

Mirror swc-workload-cli's pattern verbatim with two small,
intentional divergences (Python version from `.python-version`
rather than hardcoded; package paths adjusted for this repo).
Lands as four coordinated changes:

1. **Build backend swap** in `pyproject.toml`: setuptools →
   Hatchling.
2. **New file** `swc_workload_mcp/_version.py` — single source of
   truth for the version string.
3. **`swc_workload_mcp/__init__.py` rewired** to re-export
   `__version__` from `_version.py`.
4. **New workflow** `.github/workflows/release.yml` — manual
   dispatch, semver bump, commit, tag, push, GitHub Release.

## Test approach

Lightweight — implement directly against the spec checklist. No new
test code; verification is the existing pytest suite continuing to
pass (`make test`) plus a one-off Python check that
`swc_workload_mcp.__version__` still resolves to `"0.1.0"` after
the `__init__.py` rewire.

The release workflow itself cannot be verified inside this work item
(it triggers a real release). Confidence comes from:
- YAML parses cleanly via PyYAML.
- Workflow shape matches the CLI's, line-by-line.
- The inline bump script can be run locally in a dry-run mode to
  confirm it produces the expected next version.

## Technical decisions

- **Hatchling, not setuptools-scm.** Two reasonable ways to do
  dynamic versions in Python: (a) read from a file via Hatchling's
  `[tool.hatch.version] path = ...`, or (b) read from git tags via
  setuptools-scm. The CLI picks (a). We mirror it: the version file
  is the source of truth and the tag follows from it, not the other
  way around. Reason: it keeps the developer's mental model simple
  (look in `_version.py` to see the current version) and the
  release workflow drives both file + tag from a single bump.
- **Python version pin for the release workflow.** Use
  `python-version-file: .python-version` (currently 3.14.5) instead
  of the CLI's hardcoded `python-version: "3.12"`. Reason: keeps
  release in lockstep with our CI and local dev. The bump script
  uses only stdlib (`os`, `re`, `pathlib`), so any 3.x works — no
  reason to diverge from our pin.
- **`workflow_dispatch` only, no other triggers.** Same as CLI.
  Releases are a deliberate human action, not something that
  happens on push.
- **Bot identity for the bump commit.** `github-actions[bot]` with
  `41898282+github-actions[bot]@users.noreply.github.com`. Same as
  CLI; matches GitHub's documented convention for `GITHUB_TOKEN`-
  authored commits.
- **`permissions: contents: write` at workflow level.** Needed for
  the bot to push commits and tags via the default `GITHUB_TOKEN`.
  Same as CLI.
- **Keep `[project.optional-dependencies].dev` as-is.** The CLI dev
  dep (`swc-workload @ git+...`) keeps working under Hatchling —
  this is a PEP-508-conformant declaration in the standard
  `[project]` table, not a setuptools-specific construct.
- **No tests-must-pass guard in the release workflow.** The CLI
  doesn't have one; matches simplicity-mirroring intent. CI already
  runs on every push to main, so any merge-time regression is
  caught before release is ever triggered. If a maintainer
  release-bumps a broken main, that's on them.

## Notes

- `__init__.py` currently has two lines: module docstring +
  `__version__ = "0.1.0"`. After the change it'll have docstring +
  `from ._version import __version__`. Make sure to keep the
  docstring.
- `_version.py` is intentionally one-line-plus-newline. The bump
  script's regex (`r'__version__\s*=\s*"(\d+)\.(\d+)\.(\d+)"'`)
  assumes that shape; deviating (e.g. adding a docstring) won't
  match. Keep it minimal.
- The bump script writes the new file as
  `f'__version__ = "{new}"\n'` — note this _replaces_ the file
  contents wholesale, not just the version string. That's the CLI's
  behaviour and is fine while the file holds only the version.
- The `pyproject.toml` rewrite must drop
  `[tool.setuptools.packages.find]`. Hatchling uses
  `[tool.hatch.build.targets.wheel] packages = ["swc_workload_mcp"]`
  for the same job — leaving both in place would be misleading even
  if it didn't error.
- After install, `uv pip install -e ".[dev]"` will reinstall the
  package against the new build backend. The egg-info directory
  from the old setuptools install (`swc_workload_mcp.egg-info/`)
  may be left behind in the working tree. Worth cleaning up but
  it's gitignored already.

## Deferred

- Tag the v0.1.0 baseline. Decision: skip — let the first dispatch
  of the new workflow create v0.1.1 (or v0.2.0 if a feature bump is
  warranted at the time). Cleaner than two near-identical first
  tags.
- A "tests must pass" pre-bump check inside `release.yml`. CI's
  green-on-main is the implicit guard; revisit if a regression ever
  reaches a release-button-pressed state.
