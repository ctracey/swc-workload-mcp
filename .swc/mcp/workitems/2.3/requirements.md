# Requirements — 2.3: Define MCP tools

## Intent

Define 12 MCP tools — one per CLI op (`init`, `exists`, `list`, `find`,
`summary`, `add`, `rename`, `delete`, `reset`, `start`, `complete`,
`move`) — so MCP clients (Claude Code, Claude Desktop, and other
MCP-aware agents) can call workload operations via structured tool
invocations instead of shelling out and parsing CLI output. This is the
second of two foundation pieces sitting under the FastMCP server: the
bridge (2.1) is unreachable without these tools, and the server wiring
(2.4) has nothing to register until they exist.

## Constraints

- Thin wrapper only — no business logic. All workload semantics stay in
  the CLI; tools translate kwargs into argv, call `bridge.invoke`, and
  surface the result or a mapped error.
- Tool names are flat (`add`, not `workload_add`). The MCP client
  prefixes them with the server name automatically.
- Every `BridgeError` subclass must map to a meaningful MCP error with
  an actionable hint — never a raw exception or stack trace at the
  protocol boundary.

## Out of scope

- Instantiating the FastMCP server, performing the startup CLI check,
  and wiring stdio transport — work item 2.4.
- Tool-level tests against a temp workload — work item 3.2.
- Protocol-level smoke test via the SDK's in-memory client — work
  item 3.3.

## Approach direction

One typed Python function per CLI op, each declaring its parameters with
proper type hints (required + optional, matching the CLI's positional
args and flags). Function body translates kwargs into the argv list,
delegates to `bridge.invoke`, and wraps the call in a `try/except
BridgeError` block that re-raises each subclass as an MCP tool error
with a per-exception hint:

- `CLINotFoundError` → "swc-workload not found. Install from
  https://github.com/ctracey/swc-workload-cli or set
  `SWC_WORKLOAD_BIN`."
- `CLIExecutionError` → "swc-workload op failed (exit N): <stderr>."
- `CLIResponseError` → "swc-workload returned unparseable output
  (truncated): <…>. Likely a CLI/MCP version mismatch."

No generic `args: list[str]` passthrough — the whole point of MCP is
that the client sees a real schema per op. `workload` (folder path) is
a required kwarg on every tool, matching the CLI's required
`--workload`.

## Parked

- Per-op kwarg shape (exact names, required vs optional, types) — to
  be settled in specs once we walk each op's CLI surface.
- Exact MCP error type / mechanism (`mcp.ToolError`, a plain exception
  inside the tool function, etc.) — to be settled in solution design
  alongside the FastMCP idioms for 2.4.
