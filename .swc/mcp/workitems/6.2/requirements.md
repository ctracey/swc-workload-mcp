# Requirements — 6.2: Version sync — workflow to bump MCP service version, kept in sync with release tag

## Intent

Mirror the release pattern used by the sibling
[`swc-workload-cli`](https://github.com/ctracey/swc-workload-cli)
repo so this repo gets the same one-button-release ergonomics. A
single source of truth for the package version lives in
`swc_workload_mcp/_version.py`; the build reads it dynamically; and a
manually-triggered GitHub Actions workflow bumps it, commits, tags
`vX.Y.Z`, pushes, and creates a GitHub Release with auto-generated
notes. Done when a maintainer can cut a release entirely from the
Actions tab without editing version strings by hand.

## Constraints

- **Mirror swc-workload-cli's approach.** Build backend swap to
  Hatchling, `dynamic = ["version"]` in `pyproject.toml`, version
  sourced from `swc_workload_mcp/_version.py`,
  `workflow_dispatch`-triggered release workflow with `patch | minor |
  major` choice input.
- **Single source of truth for version.** After the change, the
  version string must exist in exactly one file
  (`swc_workload_mcp/_version.py`). `pyproject.toml` reads it
  dynamically; `swc_workload_mcp/__init__.py` re-exports it via
  `from ._version import __version__`.
- **Python version for the workflow comes from `.python-version`.**
  Diverge here from the CLI's hardcoded `"3.12"` so the release
  workflow stays aligned with our CI and local dev.
- **Release tag format is `vX.Y.Z`** to match the CLI's convention
  (and conventional semver tagging).
- **Workflow only runs on `main`.** Same `if: github.ref ==
  'refs/heads/main'` guard the CLI uses, so a release can't be cut
  from a feature branch by accident.
- **Bot identity for the bump commit.** Use `github-actions[bot]` for
  `user.name` / `user.email` (same as CLI).
- **Auto-generated release notes via `softprops/action-gh-release@v2`.**

## Out of scope

- Publishing to PyPI — the package isn't published anywhere today;
  this work item lays the tagging/release foundation but doesn't
  introduce a publish step. Add later if/when PyPI publishing is
  wanted.
- Automatic version bumping (e.g. on merge to main, conventional
  commits, semantic-release). Manual `workflow_dispatch` is
  deliberate — same as the CLI.
- README badges showing the latest version (covered by 6.3).
- Version-compatibility checking between the MCP server and the CLI
  (already deferred in `notes.md`).

## Approach direction

Two coordinated changes:

1. **Switch build backend to Hatchling and move the version into
   `swc_workload_mcp/_version.py`.** Update `pyproject.toml` to
   declare Hatchling, mark version dynamic, point
   `[tool.hatch.version]` at the new file, and configure the wheel
   target. Update `swc_workload_mcp/__init__.py` to import the
   version from `_version.py` so `swc_workload_mcp.__version__` keeps
   working.
2. **Add `.github/workflows/release.yml`** mirroring the CLI's, but
   with the path adjusted to `swc_workload_mcp/_version.py` and
   `python-version-file: .python-version` instead of a hardcoded
   Python version.

## Parked

- Whether to also create a v0.1.0 tag retroactively on this commit to
  establish the "initial" release marker. Decide during specs or
  defer.
- Whether the release workflow should also run tests as a
  prerequisite before bumping. The CLI's doesn't; deciding whether to
  diverge is a specs-stage question.
