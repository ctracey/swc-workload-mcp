# Requirements — 2.4: Wire tools into the FastMCP server with stdio transport

## Intent

Make the MCP service actually runnable end-to-end at the process level.
Today, `python -m swc_workload_mcp` raises `NotImplementedError`
(placeholder from work item 1.2) — the bridge (2.1) and the 12 tool
callables (2.3) sit unconnected to any server. This work item adds
`swc_workload_mcp/server.py` which instantiates `FastMCP("swc-workload")`,
iterates `tools.TOOLS` to register each callable, performs a fail-fast
CLI presence check at startup, and runs the stdio transport.
`__main__.main()` becomes a thin call into the server entry point so
both `python -m swc_workload_mcp` and the `swc-workload-mcp` console
script work. After 2.4, an MCP client can launch the server, list 12
tools, and invoke any of them; the only remaining work is verification
(3.x integration tests + 5.x manual client verification) and docs (4.x).

## Constraints

- **Server name `swc-workload`.** MCP clients namespace tools by the
  server name (e.g. `mcp__swc-workload__add`), so the FastMCP instance
  is constructed with that exact name.
- **Transport must be stdio.** Standard for local MCP servers consumed
  by desktop AI clients.
- **Tool registration must iterate `tools.TOOLS`.** The server holds no
  per-op knowledge — adding/removing tools later changes only
  `tools.py`. Tool names and schemas come from the function names,
  signatures, and docstrings that FastMCP introspects.
- **Startup CLI check must fail fast with an actionable message.** If
  the `swc-workload` binary cannot be resolved (`SWC_WORKLOAD_BIN`
  doesn't point at an executable AND it's not on `PATH`), the server
  prints an actionable stderr message and exits non-zero. The message
  template matches what tools already emit on `CLINotFoundError`:
  *"swc-workload not found (searched: …). Install from
  https://github.com/ctracey/swc-workload-cli or set SWC_WORKLOAD_BIN
  to the binary path."* Reuse the bridge's existing resolution logic
  rather than duplicating `shutil.which`.
- **`__main__.main()` stays a thin entry point** delegating to
  `server.main()` — the console script declared in `pyproject.toml`
  (`swc-workload-mcp = "swc_workload_mcp.__main__:main"`) keeps
  working unchanged.

## Out of scope

- Tool-level integration tests against a real `swc-workload` binary +
  temp workload — work item 3.2.
- Protocol-level smoke test via the SDK's in-memory client — work
  item 3.3.
- README updates documenting MCP-client registration / install /
  prerequisite — work item 4.
- Real-MCP-client end-to-end verification (Claude Code / Desktop) —
  work item 5.

## Approach direction

A single new module `swc_workload_mcp/server.py` containing the
`FastMCP` instance, the tool-registration loop over `tools.TOOLS`, the
startup CLI presence check, and a `main()` entry point that exits
non-zero on missing CLI or otherwise runs stdio transport. `__main__`
delegates to `server.main()`. The bridge gains a public-form binary
resolver (e.g. `bridge.resolve_binary()` — exact name a solution-design
detail) so the server reuses the same env-var-then-PATH logic the tools
already depend on.

## Parked

- **Promoting `bridge._resolve_binary` to public vs adding a separate
  non-raising `check_present` helper** — solution-design detail.
- **Exact FastMCP registration call** (`mcp.tool()(fn)` vs
  `mcp.add_tool(fn, name=...)`) — verified by the agent against the
  installed SDK during solution-design / implementation.
- **Docs drift to fix in 2.4:** `architecture.md` and `notes.md`
  currently describe the *graceful degradation* startup behaviour
  (server starts even when CLI is missing, logs a warning). This work
  item replaces that with *fail fast on startup*. Both docs need to be
  updated as part of 2.4's implementation so the architecture record
  stays accurate.
