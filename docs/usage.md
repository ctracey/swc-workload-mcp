# Usage

How to install `swc-workload-mcp`, register it with an MCP client,
and cut a release.

## Prerequisites

- **Python ≥ 3.10** (the local dev setup pins `3.14.5` via
  `.python-version`).
- **The `swc-workload` CLI** must be resolvable on `PATH` (or via
  `SWC_WORKLOAD_BIN`) at runtime. For local development the
  [Install](#install) step installs it into the venv automatically.
  For production deployment, install it separately from
  <https://github.com/ctracey/swc-workload-cli>.

The server fails fast at startup if the CLI cannot be resolved.

## Install

Local development uses [`uv`](https://github.com/astral-sh/uv) for
the venv and dependency install, wrapped by a `Makefile` so common
workflows are one command. `uv` reads the Python version from
`.python-version` (currently `3.14.5`) and installs the
`swc-workload` CLI into the venv alongside `pytest`, so a separate
system-wide CLI install isn't required for development.

```sh
git clone https://github.com/ctracey/swc-workload-mcp.git
cd swc-workload-mcp

# install uv if you don't have it (macOS):
brew install uv
# or platform-agnostic:
# curl -LsSf https://astral.sh/uv/install.sh | sh

make install
```

`make install` is shorthand for `uv venv && uv pip install -e ".[dev]"`.
It gives you:

- `.venv/bin/swc-workload-mcp` — the MCP server entry point
- `.venv/bin/swc-workload` — the CLI, installed as a dev dependency
  from <https://github.com/ctracey/swc-workload-cli>
- The `swc_workload_mcp` Python module (editable install)
- `pytest` for the test suite

Run `make help` at any time to see all the project commands
(`install`, `test`, `test-unit`, `test-integration`, `test-e2e`, `dev`).

## Register with an MCP client

Once installed, point an MCP client at the server. The launch
command below is the same shape any stdio-capable client accepts;
each client has its own place to put it. Claude Code is documented
here.

### Claude Code

From the repo root:

```sh
claude mcp add --scope project swc-workload -- \
  uv run --directory "$(pwd)" swc-workload-mcp
```

This writes a `.mcp.json` to the repo root (project scope, shared
with anyone who clones the repo). Use `--scope user` instead to
register globally for your own machine — appropriate when the server
lives outside the project you're working in.

`claude mcp add` only *records* the command; nothing runs at
registration time. Each Claude Code session execs the recorded
command as a child process and speaks MCP over stdio. The pieces:

- `uv run` — `uv`'s "run inside the project venv" wrapper. It
  activates the venv before exec, which puts `.venv/bin/swc-workload`
  on `PATH` so the server can resolve the CLI.
- `--directory "$(pwd)"` — pins the project root, so the command
  works no matter what directory Claude Code launches it from.
- `swc-workload-mcp` — the console-script entry point that runs
  `swc_workload_mcp.server:main`.

If you've installed the server and CLI directly into a Python env
that's already on `PATH` (no `uv`), the command simplifies to just
`swc-workload-mcp` with no wrapper.

#### Verify

In a fresh Claude Code session started inside the repo:

1. **Check it's connected.** Type `/mcp`. You should see
   `swc-workload` listed as **connected** with 12 tools. If it shows
   **failed**, expand the entry — the server's stderr is shown
   there; the most common cause is the `swc-workload` CLI not being
   resolvable, which `uv run` should fix.
2. **Exercise the golden path.** Ask the session something like:

   > Use swc-workload to init a workload at `/tmp/mcp-demo`, add an
   > item titled "First item", then list it.

   The tool calls should succeed and `/tmp/mcp-demo/workload.json`
   should exist on disk.
3. **Exercise an error path.** Ask:

   > Delete ref 999 from `/tmp/mcp-demo`.

   The underlying CLI will fail; the tool result surfaces a
   structured MCP error of the form *"swc-workload delete failed
   (exit N): …"* rather than a stack trace. That confirms the bridge
   is mapping CLI failures correctly.

For a more interactive way to poke at the server (independent of any
client), see [Try with MCP Inspector](try-with-mcp-inspector.md).

## Releases

How a release works in this repo, how to cut one, and what you get
(and don't get).

### What a release is here

A release is mostly bookkeeping plus a tag — there are no built
Python artifacts attached today. Each release produces:

- A bumped version in `swc_workload_mcp/_version.py` (single source
  of truth).
- A commit on `main` authored as `github-actions[bot]`, titled
  `Release vX.Y.Z`.
- A git tag `vX.Y.Z` (pushed alongside the commit).
- A [GitHub Release](https://github.com/ctracey/swc-workload-mcp/releases)
  for the tag, with auto-generated changelog (`vX.Y.Z-1...vX.Y.Z`).
  GitHub auto-attaches `Source code (zip)` and `Source code (tar.gz)`
  to every Release — these are just `git archive`-style snapshots of
  the tree at the tag, not built wheels.
- The running MCP server reports the new version via the MCP
  `initialize` handshake's `serverInfo.version` field, which clients
  like the Inspector and Claude Code/Desktop display on connection.

### Cutting a release

The release workflow is `.github/workflows/release.yml`. It's
triggered manually via `workflow_dispatch` with a `bump` choice
(`patch`, `minor`, `major`):

```sh
gh workflow run release.yml -f bump=patch    # 0.1.0 → 0.1.1
gh workflow run release.yml -f bump=minor    # 0.1.0 → 0.2.0
gh workflow run release.yml -f bump=major    # 0.1.0 → 1.0.0
```

Or from the GitHub UI: *Actions* tab → *Release* → *Run workflow* →
choose the bump → *Run workflow*.

Behind the scenes, the workflow:

1. Checks out `main` with full git history.
2. Reads the current version from `swc_workload_mcp/_version.py`.
3. Bumps the selected semver component and writes it back to that
   same file (no other files need editing — `pyproject.toml` reads
   the version dynamically via Hatchling).
4. Commits the change as `github-actions[bot]` with message
   `Release vX.Y.Z`.
5. Creates an annotated tag `vX.Y.Z` and pushes both the commit and
   the tag.
6. Creates a GitHub Release via
   [`softprops/action-gh-release`](https://github.com/softprops/action-gh-release)
   with auto-generated release notes.

End-to-end takes about 10 seconds.

### Constraints

- The job only runs when triggered against `main` — there's a guard
  `if: github.ref == 'refs/heads/main'` on the job. Dispatching from a
  feature branch is a no-op.
- The workflow needs `contents: write` permission on the default
  `GITHUB_TOKEN`. Already declared at the workflow level.
- Python version comes from `.python-version` (same as CI and local
  dev), so the bump script runs on the same interpreter you develop
  against.

### Installing a tagged version

There's no PyPI publish step (deliberately out of scope at v0.1.x),
so install directly from the git URL pinned to the tag:

```sh
# editable install (development)
uv pip install -e "git+https://github.com/ctracey/swc-workload-mcp.git@v0.1.1"

# or from system pip
pip install "git+https://github.com/ctracey/swc-workload-mcp.git@v0.1.1"
```

Once installed, `swc-workload-mcp --help` confirms the version, and
the MCP server reports the same version to any client that connects.

### What's intentionally NOT in a release today

- **No pre-built Python wheel or sdist** attached to the GitHub
  Release.
- **No PyPI publish** — `pip install swc-workload-mcp` won't work
  until/unless we add a publish step.
- **No Docker image.**

To add real installable artifacts later, extend `release.yml`:

- **Wheel attached to the Release:** add a `hatch build` step after
  the bump, then pass `files: dist/*` to
  `softprops/action-gh-release`.
- **PyPI publish:** add
  [`pypa/gh-action-pypi-publish`](https://github.com/pypa/gh-action-pypi-publish)
  after the build, using trusted publishing (no API tokens to
  manage).
