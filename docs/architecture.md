# Architecture

## What this is

`swc-workload-mcp` is a [Model Context Protocol][mcp] server that wraps
the external [`swc-workload`][cli] CLI so MCP-aware AI agents (Claude
Code, Claude Desktop, and other MCP clients) can call workload
operations as structured, typed tool invocations instead of shelling
out and parsing CLI output. The server owns no workload semantics — it
is a thin protocol-and-process bridge in front of the CLI.

[mcp]: https://modelcontextprotocol.io
[cli]: https://github.com/ctracey/swc-workload-cli

## What is MCP?

MCP is an open protocol that lets AI clients discover and call typed
tools, resources, and prompts exposed by servers. A server publishes a
catalog (tool name + JSON schema for arguments + description); the
client routes agent calls to the server, which executes the tool and
returns a structured result. This server uses the standard **stdio**
transport — the client launches the server as a subprocess and exchanges
JSON-RPC messages over `stdin`/`stdout`.

## Layers at a glance

```
MCP client (Claude Code / Desktop)
        │  stdio (JSON-RPC)
        ▼
FastMCP server (server.py)
        │  Python call
        ▼
tool callable (tools.py)
        │  argv list
        ▼
subprocess bridge (bridge.py)
        │  exec
        ▼
swc-workload CLI subprocess  ──▶  workload.json on disk
```

## Each layer in a bit more detail

### Server layer (`server.py`)

Instantiates a single `FastMCP("swc-workload")` instance at module load,
performs a **fail-fast** CLI presence check at startup (via the bridge's
`resolve_binary`), iterates `tools.TOOLS` to register every tool, then
runs the stdio transport. Holds no per-op knowledge — adding a tool
means appending to the registry in `tools.py`, not editing `server.py`.

### Tool layer (`tools.py`)

Fifteen typed Python callables (`init`, `exists`, `list`, `find`, `summary`,
`get`, `add`, `update`, `rename`, `delete`, `reset`, `start`, `complete`,
`move`, `version`), plus a `TOOLS` registry. All but `version` delegate to
the CLI bridge; `version` returns the MCP package version directly without
a subprocess call. Each tool translates its
kwargs into the CLI's argv (positional first, then `--flag value`),
delegates to the bridge, and maps `BridgeError` subclasses to FastMCP
`ToolError` instances with actionable hints. Tool names are flat — MCP
clients namespace by server name (e.g. `mcp__swc-workload__add`).

### Bridge layer (`bridge.py`)

Resolves the CLI binary via `SWC_WORKLOAD_BIN` (env var override) →
`shutil.which("swc-workload")` on `PATH`, then runs
`swc-workload <op> <args> --json` as a subprocess, parses JSON stdout,
and raises one of three typed exceptions on failure:
`CLINotFoundError`, `CLIExecutionError`, or `CLIResponseError`. No
per-op knowledge — the op string is forwarded verbatim from the tool
layer.

### CLI (`swc-workload`)

External dependency installed separately from
<https://github.com/ctracey/swc-workload-cli>. Owns all workload
semantics; this repo treats its `--json` interface as a contract and
does not modify it.

## Meta fields

Every work item carries a `meta` field — a free-form JSON object that
defaults to `{}`. The MCP server treats it as opaque: it serialises
and deserialises the value but imposes no schema. All meaning is
defined by the caller.

Four tools interact with `meta`:

- `add` — accepts an optional `meta` object at creation time.
- `get` — always returns the full `meta` blob alongside the item.
- `update` — writes to meta via path notation (`meta.<key>` for a
  single field, `meta` to replace the whole object).
- `find` — searches by meta path, with an optional regex pattern.

### Namespace convention

Use `vendor:purpose` colon-separated key names to avoid collisions
when multiple tools or agents share the same workload — e.g.
`swc:owner`, `ci:run_id`, `issue:url`. Dots must not appear in key
names: the dot is the path separator in `update` and `find`, so a
dot inside a key name would be misread as a sub-path traversal.

Path notation details and examples are in [Usage](usage.md#meta-path-notation-reference).

## Startup behaviour

The server is **fail-fast on a missing CLI**. When `server.main()` is
invoked (via `python -m swc_workload_mcp` or the `swc-workload-mcp`
console script), it first calls `bridge.resolve_binary()`. On
`CLINotFoundError` it prints to stderr:

```
swc-workload not found (searched: <paths>). Install from
https://github.com/ctracey/swc-workload-cli or set SWC_WORKLOAD_BIN
to the binary path.
```

…and exits non-zero before `mcp.run()` is invoked. There is no
graceful-degradation mode — a server that lists tools but errors on
every call is harder to diagnose from inside an MCP client than a clean
startup failure. Set `SWC_WORKLOAD_BIN` to override `PATH` resolution
when the CLI is installed somewhere unusual.
