# Architecture

## Context

The repo today ships a Python CLI (`bin/swc_workload`) as a Claude Code plugin.
The CLI is a path-driven tree manager for `workload.json` files and has no
external dependencies. AI agents that want to use it must shell out and parse
its output.

This work reshapes the repo into a standalone **MCP service** that wraps the
existing CLI, so MCP-aware AI agents can call workload operations as
structured tool invocations. The CLI is kept intact and unchanged.

## Tech stack

- **Language:** Python 3 (matches existing CLI).
- **MCP SDK:** official `mcp` Python SDK (FastMCP style).
- **Dependency management:** `pyproject.toml`. Dependencies are declared; the
  README documents how to install them (virtualenv recommended). The existing
  CLI stays stdlib-only — only the MCP server has the `mcp` dep.
- **Transport:** stdio (standard for local MCP servers consumed by desktop AI
  clients).
- **CLI bridging:** MCP tool implementations invoke `bin/swc_workload` as a
  subprocess with `--json`, parse the structured output, and return it as the
  MCP tool result. CLI errors (non-zero exit + stderr) are surfaced as MCP
  tool errors.
- **Tests:** `pytest`. Existing CLI subprocess tests are kept. New tests cover
  the MCP server layer (see notes for the testing approach).

## Folder structure

The repo is reshaped from "Claude Code plugin" to "MCP service":

```
swc-workload/
├── pyproject.toml              # new — package + dep declaration + entry point
├── README.md                   # rewritten — MCP service docs
├── swc_workload_mcp/           # new — MCP server package
│   ├── __init__.py
│   ├── __main__.py             # so `python -m swc_workload_mcp` works
│   └── server.py               # FastMCP server, tool definitions
├── bin/
│   └── swc_workload            # existing CLI, unchanged
└── tests/
    ├── bin/                    # existing CLI subprocess tests, unchanged
    └── mcp/                    # new — MCP server tests
```

Removed: `.claude-plugin/plugin.json` (no longer a Claude Code plugin).

## Decisions

- **Server name:** `swc-workload`. MCP clients namespace tools by the server
  name automatically (e.g. `mcp__swc-workload__add` in Claude Code), so tool
  names are flat: `init`, `exists`, `list`, `find`, `summary`, `add`,
  `rename`, `delete`, `reset`, `start`, `complete`, `move` — one per CLI op.
- **Subprocess + `--json`, not Python imports.** The MCP server does not
  import the CLI as a module. It invokes it via subprocess. This keeps the
  CLI fully decoupled and lets us swap the wrapper without touching the CLI.
- **No automatic MCP-client registration.** The README documents how users
  register the server with their MCP client of choice; we do not bundle a
  manifest that wires it up automatically.

## Constraints

- The existing CLI must remain functional and unchanged. Its subprocess tests
  must still pass.
- The MCP layer is a thin wrapper — no business logic lives in it. All
  workload semantics stay in the CLI.
- Dependencies are isolated: the CLI has none; the MCP server has the `mcp`
  SDK. Users who only need the CLI shouldn't have to install the MCP dep.
