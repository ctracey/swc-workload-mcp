# Solution Design — 2.4: Wire tools into the FastMCP server with stdio transport

## Approach

Add `swc_workload_mcp/server.py` containing a module-level
`FastMCP("swc-workload")` instance, a `main()` entry point, and the
registration loop over `tools.TOOLS`. `main()` runs the startup CLI
presence check first via the bridge's (now-public) resolver — on
`CLINotFoundError` it prints the actionable message to stderr and
exits non-zero; otherwise it proceeds to register every callable in
`tools.TOOLS` against the FastMCP instance and runs `mcp.run()` over
the stdio transport. `__main__.main()` becomes a thin delegation to
`server.main()`, so both `python -m swc_workload_mcp` and the
`swc-workload-mcp` console script reach the same entry point. The
bridge gets `_resolve_binary` promoted to a public `resolve_binary`
so the startup check reuses the same resolution logic the tools rely
on at call time. Docs are brought in line: `.swc/mcp/architecture.md`
and `.swc/mcp/notes.md` are rewritten to describe fail-fast startup,
and a new public-facing `docs/architecture.md` is created describing
the end-to-end design.

## Test approach

Full TDD — one test per Gherkin scenario in `specs.md` before
implementation. Unit tests cover REQ-01 through REQ-07 (mocking
`mcp.run()` via monkeypatch so the stdio loop is never actually
entered; asserting calls, exit codes, stderr content, registration
state). REQ-09 ships as an end-to-end smoke test that exercises the
real CLI through the SDK's in-memory client; it **fails loudly** if
the CLI isn't installed rather than skipping — the test exists
precisely to verify the wired-up service actually works, and a silent
skip would erase that signal.

## Technical decisions

- **Promote `bridge._resolve_binary` to public `bridge.resolve_binary`.**
  Same signature, same `CLINotFoundError` semantics on miss. Update
  the single internal call site inside `bridge.invoke`. The server's
  `main()` then calls `bridge.resolve_binary()` directly in a
  try/except, satisfying REQ-07.

- **Startup ordering.** `server.main()` runs the CLI check first; on
  failure it exits before constructing the FastMCP instance or
  touching `tools.TOOLS`. On success it constructs `FastMCP`, registers
  tools, then runs stdio. This makes REQ-02's "`mcp.run()` is NOT
  invoked" trivially true and keeps the failure path clean.

- **Tool registration mechanism.** Iterate `tools.TOOLS` and call
  `mcp.tool()(fn)` (functional form of the decorator). FastMCP picks
  up the tool name from the function name and the schema from type
  hints + docstring — no further metadata needed. If the installed
  SDK exposes a more idiomatic functional method (e.g. `mcp.add_tool`),
  the agent prefers that; behaviour is what the spec asserts, not the
  exact call.

- **Smoke test — fail loudly when CLI is missing.** The smoke test in
  `test_server.py` (or wherever the agent locates it) does **not**
  call `pytest.skip` when `swc-workload` is unresolvable. It fails
  with a clear message ("`swc-workload` CLI must be installed to run
  the end-to-end smoke; this test verifies the happy path"). Reason:
  the unit tests already cover wiring without the CLI; REQ-09 exists
  to give confidence the real chain works. CI's responsibility is to
  install the CLI before running tests.

- **Smoke test mechanism.** The MCP Python SDK ships an in-memory
  client/server harness for testing — `mcp.shared.memory.create_connected_server_and_client_session`
  or similar (agent verifies exact import path against the installed
  SDK version). The smoke test uses that to call `init` against a
  `tmp_path` workload folder, then asserts `workload.json` exists and
  parses. This pattern is what 3.3 ("protocol smoke test via the
  SDK's in-memory client") will expand on.

- **REQ-06 test via monkeypatching.** Patch
  `swc_workload_mcp.server.main` to be a recorder, import
  `swc_workload_mcp.__main__`, call its `main()`, and assert the
  patched server.main was called once.

- **REQ-03 test by inspection.** Read `server.py` source, assert it
  imports `tools.TOOLS` and the registration code is a loop over it;
  assert no literal op-name string appears in the registration path.
  Lightweight static check — sufficient to catch a regression where
  someone hardcodes `mcp.tool()(tools.init)` for each op.

## Additional deliverables (beyond `swc_workload_mcp/`)

- **`docs/architecture.md`** — NEW public-facing architecture overview.
  The implementing agent creates `docs/` if it doesn't exist and
  writes the doc with this structure:

  1. **What this is** — one paragraph: an MCP server that wraps the
     external `swc-workload` CLI so MCP-aware AI agents can call
     workload operations as structured tools instead of shelling out.
  2. **What is MCP?** — 2–3 sentences. A protocol for AI clients to
     discover and call typed tools / resources / prompts exposed by
     servers; this project exposes tools over the standard stdio
     transport.
  3. **Layers at a glance** — a brief listing or ASCII diagram of the
     end-to-end flow:
     `MCP client (Claude Code/Desktop) ─stdio─▶ FastMCP server ─▶ tool callable ─▶ bridge ─▶ swc-workload CLI subprocess ─▶ workload.json`
  4. **Each layer in a bit more detail** — one short paragraph per
     layer:
     - **Server layer (`server.py`):** instantiates `FastMCP("swc-workload")`, runs the fail-fast CLI presence check at startup, iterates `tools.TOOLS` to register every tool, runs the stdio transport.
     - **Tool layer (`tools.py`):** 12 typed Python callables, one per CLI op, plus a `TOOLS` registry. Each tool translates kwargs to CLI argv, delegates to the bridge, maps `BridgeError` subclasses to `ToolError` with actionable hints.
     - **Bridge layer (`bridge.py`):** resolves the CLI binary via `SWC_WORKLOAD_BIN` → `PATH`, runs `swc-workload <op> --json` as a subprocess, parses JSON stdout, raises typed exceptions (`CLINotFoundError`, `CLIExecutionError`, `CLIResponseError`) on failure. No per-op knowledge.
     - **CLI (`swc-workload`):** external dependency installed separately from <https://github.com/ctracey/swc-workload-cli>. Owns all workload semantics; this repo treats its `--json` interface as a contract.
  5. **Startup behaviour** — one short paragraph noting fail-fast on
     missing CLI, with the stderr message template and the
     `SWC_WORKLOAD_BIN` override.

  Tone: technical reference, not marketing. Roughly 1 page. The
  README (work item 4) will link to this doc rather than duplicating
  it.

- **`.swc/mcp/architecture.md`** and **`.swc/mcp/notes.md`** updates
  per REQ-08: replace the prior "graceful degradation / server still
  starts" wording with fail-fast-on-missing-CLI. Keep the existing
  decisions/structure otherwise.

## Deferred

- README rewrite documenting client registration / install / use —
  work item 4.
- Per-tool integration tests against a real CLI + temp workload —
  work item 3.2 (expands REQ-09's pattern to every tool).
- Wider protocol-level smoke coverage via the in-memory client —
  work item 3.3 (expands REQ-09 to more tools / error paths).
- CI installing `swc-workload` before running the test suite — work
  item 6.1.

## Notes

- The `mcp` SDK and `swc-workload` CLI are both prerequisites for
  this work item's test suite. Quality-baseline already verifies both
  are present in the dev environment; the smoke test will fail loudly
  otherwise.
- FastMCP's `mcp.run()` blocks on stdio. Unit tests must monkeypatch
  it (e.g. replace with a recording stub) before invoking
  `server.main()`, otherwise the test process will hang reading from
  stdin.
- When testing the missing-CLI startup path, the autouse fixture
  pattern from `tests/mcp/test_bridge.py` (clear `SWC_WORKLOAD_BIN`,
  override `PATH` to a non-existent dir) is the right starting point.
- Tool docstrings already carry the per-tool descriptions visible to
  MCP clients; FastMCP picks them up at registration. No further
  description metadata is needed at the server layer.
