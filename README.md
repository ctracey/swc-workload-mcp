# swc-workload-mcp

![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Version](https://img.shields.io/github/v/tag/ctracey/swc-workload-mcp?filter=v*&label=version)

A standalone [Model Context Protocol](https://modelcontextprotocol.io)
server that wraps the
[`swc-workload`](https://github.com/ctracey/swc-workload-cli) CLI so
MCP-aware AI agents (Claude Code, Claude Desktop, and other MCP
clients) can manage workload trees via structured tool invocations
instead of shelling out and parsing CLI output.

See [`docs/architecture.md`](docs/architecture.md) for the
layer-by-layer design.

## What it does

Exposes 12 MCP tools — one per CLI op — over the standard MCP stdio
transport:

`init`, `exists`, `list`, `find`, `summary`, `add`, `rename`,
`delete`, `reset`, `start`, `complete`, `move`

Each tool translates its kwargs into the CLI's argv, invokes
`swc-workload <op> --json` as a subprocess, parses the JSON, and
returns it to the client. CLI errors map to structured MCP tool
errors with actionable hints.

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

## Try it with MCP Inspector

[MCP Inspector](https://github.com/modelcontextprotocol/inspector) is
the SDK team's interactive UI for poking at MCP servers — list tools,
view their schemas, invoke them, and watch the responses. It's the
quickest way to confirm everything works end-to-end before wiring the
server up to a full client like Claude Code or Claude Desktop.

### Prerequisites for Inspector

- **Node.js ≥ 18** (Inspector ships as an npm package; `npx` fetches
  it on first run — no global install needed).

### Launch

From the repo root, with the venv created above:

```sh
make dev
```

That target runs `npx @modelcontextprotocol/inspector uv run swc-workload-mcp`,
which:

1. Pulls and runs the Inspector via `npx` (Node's fetch-and-run; no
   global install needed).
2. Spawns our MCP server via `uv run swc-workload-mcp` as a child
   process. `uv run` activates the project venv first so the server
   can find its bundled `swc-workload` CLI on `PATH`.
3. Opens the Inspector UI in your browser (default
   <http://localhost:6274/>) and prints the URL to the terminal.

### What's actually running

Once you launch, there are **two long-running processes** (plus a
short-lived one per tool call):

```
Browser (you)
   │  HTTP/WebSocket
   ▼
[Inspector — Node]                  ← long-running; hosts the UI on :6274
   │                                  and acts as an MCP client
   │  stdio (MCP JSON-RPC)
   ▼
[swc-workload-mcp — Python]         ← long-running; speaks MCP, doesn't
   │                                  open a port of its own
   │  subprocess.run("swc-workload …")
   ▼
[swc-workload — Python]             ← ephemeral, one per tool invocation
```

The MCP server uses **stdio transport** — no network port — which is
the same way real MCP clients like Claude Code and Claude Desktop will
launch it in production. The Inspector is just acting as a test
client with a browser UI on top.

### What to look at

1. **Server connection.** After launch you should see status
   *Connected* alongside the server name `swc-workload`.
2. **Tools tab.** Lists all 12 registered tools with their schemas
   (kwargs, types, descriptions derived from each tool's docstring).
3. **Invoke `init`.**
   - Select `init` in the tool list.
   - Set `workload` to a path you don't mind being created, e.g.
     `/tmp/mcp-demo`.
   - Click *Run Tool*. You should see a JSON response, and
     `/tmp/mcp-demo/workload.json` will now exist on disk.
4. **Invoke `add`.**
   - Select `add`.
   - Set `workload=/tmp/mcp-demo` and `title="First item"`.
   - Click *Run Tool*. The response includes the new item's ref.
5. **Invoke `list`.** Same `workload`; no other kwargs needed. See the
   tree.
6. **Try an error path.** Select `delete`, set `ref` to a value that
   doesn't exist (e.g. `999`). The response surfaces a structured MCP
   tool error: *"swc-workload delete failed (exit N): …"* with the
   underlying CLI message.

### Verifying fail-fast startup via Inspector

To see the missing-CLI error path, point at a non-existent binary:

```sh
SWC_WORKLOAD_BIN=/nonexistent npx @modelcontextprotocol/inspector \
  uv run swc-workload-mcp
```

The server will exit non-zero on startup; the Inspector surfaces the
stderr message:

```
swc-workload not found (searched: /nonexistent). Install from
https://github.com/ctracey/swc-workload-cli or set SWC_WORKLOAD_BIN
to the binary path.
```

## Tests

The suite is organised into three tiers under `tests/mcp/`, one
folder per tier:

| Tier | Folder | Needs `swc-workload` CLI? | What it covers |
| --- | --- | --- | --- |
| Unit | `tests/mcp/unit/` | No | Bridge, tools, and server wiring against stubs |
| Integration | `tests/mcp/integration/` | **Yes** | All 12 tools end-to-end through a real MCP server subprocess and the real CLI |
| E2E | `tests/mcp/e2e/` | **Yes** | In-memory smoke of `init` through the wired FastMCP → tools → bridge → CLI chain |

The integration and e2e tiers **fail loudly** (not skip) if the CLI
isn't resolvable — that's deliberate, so a missing CLI is never
mistaken for a green run.

### Running the suite

After `make install` (see [Install](#install)), the CLI lives at
`.venv/bin/swc-workload`, so all three tiers can run without any
additional setup:

```sh
# everything
make test

# one tier at a time
make test-unit
make test-integration
make test-e2e
```

Each `make test*` target is a thin wrapper around `uv run pytest [path]`
— invoke pytest directly via `.venv/bin/pytest` or `uv run pytest` if
you need flags the Makefile doesn't expose.

### What CI runs

`.github/workflows/ci.yml` runs the same three tiers as three
independent jobs on every PR against `main` and every push to `main`.
Each job sets up Python (from `.python-version`), sets up `uv`
(via `astral-sh/setup-uv`), then runs `make install` followed by
`make test-<tier>` — the exact same targets you'd run locally. Runner
is `ubuntu-latest` only.

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
