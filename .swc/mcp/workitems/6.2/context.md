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

## Pass 2 — 2026-05-27 (follow-up: surface version via MCP initialize)

- **Trigger:** user asked how to expose the MCP service version to
  clients. The right answer per MCP convention is the `initialize`
  handshake's `serverInfo` block — `name` plus `version`. Today our
  server sets `name="swc-workload"` but `version` was unset (the
  low-level `Server` defaults to `None`), so clients (Inspector,
  Claude Code) see an empty version field on connection.
- **Decision:** wire `_version.__version__` into the low-level
  Server's `version` attribute. FastMCP's `__init__` doesn't accept
  `version` (verified by inspecting its signature) — only `name`,
  `instructions`, `website_url`, `icons` are exposed. The low-level
  `mcp.server.lowlevel.Server` does take `version=...` in its
  constructor, and FastMCP holds it as `mcp._mcp_server`. So we set
  it after construction: `mcp._mcp_server.version = __version__`.
- **Decision:** add a unit test in
  `tests/mcp/unit/test_server.py` —
  `test_server_version_is_set_on_low_level_server` — pinning this
  wiring. Reason: we reach a "private" attribute (`_mcp_server`); if
  the SDK ever renames it or restructures, our handshake would
  silently lose `version` again. The test catches that immediately.
- **Decision:** not a new MCP tool. Tools are for client-invoked
  operations; the version belongs in the handshake metadata that
  clients already display. Adding a `version` tool would be
  redundant and non-conventional.
- **Decision:** bundle into 6.2's open PR (#3) rather than a new
  work item, since the change is 2 source lines + 1 test and
  conceptually completes "version sync" — without surfacing it, the
  single source of truth has no observable effect on the client.
- **Verification:** `make test` → 130 passed (was 129), 7 skipped.
  The new test asserts
  `server.mcp._mcp_server.version == _version.__version__`.
- **Verification:** spot-check via
  `python -c "from swc_workload_mcp.server import mcp;
  print(mcp._mcp_server.version)"` prints `0.1.0`. Will surface in
  the `initialize` handshake's `serverInfo.version` field that MCP
  clients consume.
- **Tech debt seed:** if/when FastMCP adds `version` to its public
  constructor, replace the `mcp._mcp_server.version = ...` line with
  the constructor kwarg and drop the inline comment. Not worth
  filing as tech debt yet — it's a 2-line cleanup keyed to an
  external API change.
