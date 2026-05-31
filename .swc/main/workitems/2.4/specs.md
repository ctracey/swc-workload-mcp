# Specs — 2.4: Wire tools into the FastMCP server with stdio transport

## Users and Personas

Mostly technical actors (per the 2.3 spec) plus the developer running
the server directly:

- **Developer / operator** — runs `python -m swc_workload_mcp` or the
  `swc-workload-mcp` console script to verify the service starts and
  to diagnose configuration problems (missing CLI, env-var misconfig).
  Precondition: the package is installed in the local Python
  environment; the `swc-workload` CLI may or may not be present.
- **MCP client** (Claude Code, Claude Desktop, or any MCP-aware host)
  — launches the server as a subprocess over stdio, lists the
  registered tools, and calls them on behalf of the agent.
  Precondition: the server starts successfully (CLI resolvable).
- **Agent code inside the client** — invokes a registered tool with
  structured arguments; the server routes the call to `tools.<op>`
  which delegates to the bridge.

## User Journeys

### Happy path — server starts and is usable

1. Developer or MCP client invokes the entry point (`python -m
   swc_workload_mcp` / `swc-workload-mcp` / module launched via an
   MCP-client manifest).
2. `__main__.main()` delegates to `server.main()`.
3. `server.main()` runs the CLI presence check via the bridge's
   resolver. CLI resolves successfully.
4. A `FastMCP` instance is constructed with name `swc-workload`.
5. Each callable in `tools.TOOLS` is registered on the instance (12
   tools total, flat names).
6. `mcp.run()` is invoked with the stdio transport.
7. The MCP client connects and can list all 12 tools by name; the
   agent can invoke any of them.

### Error path — startup fails fast on missing CLI

1. Developer or MCP client invokes the entry point.
2. `server.main()` runs the CLI presence check via the bridge's
   resolver.
3. The bridge raises `CLINotFoundError` because the CLI isn't on PATH
   and `SWC_WORKLOAD_BIN` either isn't set or doesn't point at an
   executable.
4. `server.main()` catches it, prints an actionable message to
   stderr: *"swc-workload not found (searched: …). Install from
   https://github.com/ctracey/swc-workload-cli or set
   SWC_WORKLOAD_BIN to the binary path."*
5. `server.main()` exits non-zero. `mcp.run()` is never called. No
   FastMCP instance is constructed (or, if construction precedes the
   check in solution-design, no tools are registered and no transport
   starts).

### End-to-end smoke — service actually does something useful

1. CLI is installed and on PATH.
2. Server is started (via the in-memory client harness — see
   solution-design parked notes for the test mechanism).
3. Agent calls `init` with `workload=<empty-temp-folder>`.
4. The server routes through `tools.init` → `bridge.invoke("init",
   …)` → `swc-workload init --workload <folder> --json`.
5. The CLI exits 0 and writes `workload.json` into the folder.
6. The tool returns parsed JSON to the agent.
7. The folder now contains a `workload.json` file with a valid empty
   workload structure.

## Requirements

**REQ-01** (event-driven) — WHEN `server.main()` is invoked AND the
`swc-workload` CLI is resolvable, it SHALL instantiate `FastMCP` with
name `swc-workload`, register every callable in `tools.TOOLS` against
the instance, and run the stdio transport via `mcp.run()`.

**REQ-02** (unwanted behaviour) — IF the `swc-workload` CLI cannot be
resolved at startup (no `SWC_WORKLOAD_BIN` pointing at an executable
AND not on PATH), THEN the server SHALL print an actionable stderr
message containing `"swc-workload not found"`, the CLI repo URL
`https://github.com/ctracey/swc-workload-cli`, and the env-var name
`SWC_WORKLOAD_BIN`; AND SHALL exit non-zero; AND SHALL NOT invoke
`mcp.run()`.

**REQ-03** (ubiquitous) — `server.py` SHALL register tools by
iterating `tools.TOOLS`. It SHALL NOT contain inline per-op knowledge
or literal CLI op names anywhere in the registration code path.

**REQ-04** (ubiquitous) — The FastMCP instance's server name SHALL be
`swc-workload`.

**REQ-05** (event-driven) — WHEN tool registration completes, exactly
12 tools SHALL be addressable through the FastMCP instance, with flat
names matching the function names in `tools.TOOLS` (`init`, `exists`,
`list`, `find`, `summary`, `add`, `rename`, `delete`, `reset`,
`start`, `complete`, `move`).

**REQ-06** (event-driven) — WHEN `__main__.main()` is invoked (via
`python -m swc_workload_mcp` or the `swc-workload-mcp` console
script), it SHALL delegate to `server.main()`.

**REQ-07** (ubiquitous) — The startup CLI presence check SHALL reuse
the bridge's existing binary-resolution logic (env var → PATH). No
duplicated `shutil.which` lookup in `server.py`.

**REQ-08** (documentation invariant) — `architecture.md` and
`notes.md` SHALL describe fail-fast startup. The prior "graceful
degradation" / "server still starts if the CLI isn't found" wording
SHALL be replaced. Verified by reading the docs at review time; no
automated test.

**REQ-09** (event-driven — end-to-end smoke) — WHEN the `init` tool is
invoked through the running server with `workload=<empty-folder>`, the
call SHALL succeed AND a `workload.json` file SHALL exist at that
folder. This is the minimum end-to-end smoke proving the wired
service routes a tool call through FastMCP → tools → bridge → CLI
all the way to a filesystem side-effect.

## Acceptance Scenarios

```gherkin
# REQ-01 — happy startup wires everything up
Scenario: server starts and runs stdio
  Given the swc-workload CLI is resolvable (via PATH or SWC_WORKLOAD_BIN)
  When server.main() is invoked
  Then a FastMCP instance with name "swc-workload" is constructed
  And every callable in tools.TOOLS is registered against the instance
  And mcp.run() is invoked with the stdio transport

# REQ-02 — fail-fast startup with actionable message
Scenario: startup exits non-zero when the CLI is missing
  Given no SWC_WORKLOAD_BIN is set
  And the swc-workload binary is not on PATH
  When server.main() is invoked
  Then the process exits with non-zero status
  And stderr contains "swc-workload not found"
  And stderr contains "https://github.com/ctracey/swc-workload-cli"
  And stderr contains "SWC_WORKLOAD_BIN"
  And mcp.run() is NOT invoked

# REQ-02 — same with a misconfigured env var
Scenario: startup exits non-zero when SWC_WORKLOAD_BIN doesn't point at an executable
  Given SWC_WORKLOAD_BIN is set to "/nonexistent/path"
  When server.main() is invoked
  Then the process exits with non-zero status
  And stderr contains "swc-workload not found"
  And stderr mentions "/nonexistent/path" in the searched-paths list
  And mcp.run() is NOT invoked

# REQ-03 — no per-op knowledge in server.py
Scenario: server.py registers tools by iterating TOOLS
  When server.py is inspected
  Then it imports the TOOLS registry from the tools module
  And the registration code iterates over TOOLS
  And it does not contain literal CLI op-name strings in the registration path

# REQ-04 — server name
Scenario: FastMCP server name is swc-workload
  When the FastMCP instance is constructed
  Then its name property equals "swc-workload"

# REQ-05 — 12 tools registered with the right flat names
Scenario: all 12 tools are registered with flat names
  Given the server has been built
  When the registered tools are enumerated
  Then exactly 12 tools are registered
  And their names are exactly: init, exists, list, find, summary, add, rename, delete, reset, start, complete, move

# REQ-06 — __main__ delegates to server.main
Scenario: __main__.main() delegates to server.main()
  Given server.main is patched to be observable
  When __main__.main() is invoked
  Then server.main is called exactly once

# REQ-07 — startup check reuses the bridge resolver
Scenario: startup CLI check uses bridge's binary resolution
  When server.main() performs the startup check
  Then it calls the bridge's binary resolver
  And it does not call shutil.which directly inside server.py

# REQ-09 — end-to-end smoke through the running server
Scenario: init through the server creates workload.json
  Given the swc-workload CLI is installed and resolvable
  And /tmp/<unique>/ is an empty directory
  And the server is running (registered tools, FastMCP wired)
  When the "init" tool is invoked through the server with workload="/tmp/<unique>/"
  Then the call returns successfully
  And /tmp/<unique>/workload.json exists
  And the contents of workload.json parse as a valid empty workload structure
```

## Validation Rules

Not applicable — `server.py` performs no input validation. Argument
schemas come from `tools.TOOLS` function signatures and are validated
by FastMCP before each tool body runs.

## Notes on test scope

REQ-09 intentionally overlaps with the future scope of work items 3.2
and 3.3:

- **3.2** ("tool-level tests — each tool exercised against a temp
  workload") will expand REQ-09's pattern to cover every tool against
  a real CLI + temp workload.
- **3.3** ("protocol smoke test via the SDK's in-memory client") will
  widen the protocol-level coverage.

Shipping REQ-09 in 2.4 is the minimum smoke that proves the wired
service does something useful end-to-end. Without it, 2.4 ships
code that *looks* connected but has no verification that a call
actually flows through to a filesystem side-effect. The chosen test
mechanism (in-memory client vs. spawned-subprocess + stdio) is parked
for solution-design.

REQ-08 is a documentation obligation, not a behavioural one — no
Gherkin scenario. Verified by review.
