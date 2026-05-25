# Architecture

## Context

This repo is an MCP service that wraps the `swc-workload` CLI so MCP-aware
AI agents can call workload operations as structured tool invocations
instead of shelling out and parsing CLI output.

The CLI itself is a separate concern. It lives in its own repo at
<https://github.com/ctracey/swc-workload-cli> and is installed by the user
via that repo's documented install steps. The MCP service treats the CLI
as an **external dependency** that is expected to be available on PATH.

## Tech stack

- **Language:** Python 3 (matches the CLI).
- **MCP SDK:** official `mcp` Python SDK (FastMCP style).
- **Dependency management:** `pyproject.toml`. Only declared runtime
  dependency is `mcp`. The CLI is a *system* dependency, not a Python
  dependency — it must be installed separately.
- **Transport:** stdio (standard for local MCP servers consumed by desktop
  AI clients).
- **CLI bridging:** MCP tool implementations invoke the CLI as a subprocess
  with `--json`, parse the structured output, and return it as the MCP
  tool result. The CLI binary is resolved as: `SWC_WORKLOAD_BIN` env var
  override → `shutil.which("swc-workload")` on PATH.
- **Error handling:** CLI non-zero exit + stderr → MCP tool error. Missing
  CLI (binary not found) → a structured, actionable MCP tool error that
  points the user at <https://github.com/ctracey/swc-workload-cli> for
  install instructions.
- **Tests:** `pytest`. Tests cover the MCP server layer (bridge unit
  tests, tool-level tests against a temp workload, and a protocol-level
  smoke test via the SDK's in-memory client).

## Folder structure

```
swc-workload-mcp/
├── pyproject.toml              # package + dep declaration + entry point
├── README.md                   # MCP service docs (incl. CLI prerequisite)
├── swc_workload_mcp/
│   ├── __init__.py
│   ├── __main__.py             # so `python -m swc_workload_mcp` works
│   ├── server.py               # FastMCP server + tool registration (2.4)
│   ├── tools.py                # one tool callable per CLI op + TOOLS registry
│   └── bridge.py               # subprocess + --json wrapper, error mapping
└── tests/
    └── mcp/                    # MCP server tests
```

## Decisions

- **CLI is an external dependency, not bundled.** This repo ships only
  the MCP service. The CLI is installed separately from
  <https://github.com/ctracey/swc-workload-cli>. The MCP service depends
  on `swc-workload` being available on PATH (or via `SWC_WORKLOAD_BIN`
  env var override) at runtime.
- **Graceful degradation when CLI is missing.** On startup, the server
  performs a `shutil.which` lookup and logs a warning to stderr if the
  CLI is not found. The server still starts so MCP clients can connect.
  Tool calls in that state return a structured MCP error pointing at the
  CLI repo, not a raw `FileNotFoundError`.
- **Server name:** `swc-workload`. MCP clients namespace tools by the
  server name automatically (e.g. `mcp__swc-workload__add` in Claude
  Code), so tool names are flat: `init`, `exists`, `list`, `find`,
  `summary`, `add`, `rename`, `delete`, `reset`, `start`, `complete`,
  `move` — one per CLI op.
- **Subprocess + `--json`, not Python imports.** The MCP server does not
  import the CLI as a module. It invokes it via subprocess. This keeps
  the CLI fully decoupled — the MCP server has no knowledge of the CLI's
  internals and can wrap any compatible version.
- **No automatic MCP-client registration.** The README documents how
  users register the server with their MCP client of choice; we do not
  bundle a manifest that wires it up automatically.

## Constraints

- The MCP layer is a thin wrapper — no business logic lives in it. All
  workload semantics stay in the CLI.
- The MCP server depends only on the `mcp` SDK as a Python dependency.
  The CLI is a system-level prerequisite, not bundled or auto-installed.
- The CLI's behaviour and `--json` interface are treated as a contract.
  This repo does not modify them; if the CLI changes its interface, the
  bridge needs an update.
