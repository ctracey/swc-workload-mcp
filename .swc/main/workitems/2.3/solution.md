# Solution Design — 2.3: Define MCP tools

## Approach

Define the 12 MCP tools as plain typed Python callables in a new
`swc_workload_mcp/tools.py` module. Each tool is a top-level function
declaring its parameters (required + optional) with proper type hints,
translating its kwargs into the CLI's argv, delegating to
`bridge.invoke`, and re-raising `BridgeError` subclasses as MCP tool
errors with per-type hints. Module exports a `TOOLS` registry (list of
the 12 callables) which 2.4's `server.py` iterates over to register
each one against the FastMCP instance.

## Test approach

Full TDD — write one test per Gherkin scenario in `specs.md` before
writing the corresponding tool / wrapper code. Tests unit-test the tool
wrappers directly (import each callable, stub the bridge via
`monkeypatch`, assert argv translation, return passthrough, and error
mapping). End-to-end protocol tests stay scoped to work item 3.3, and
end-to-end tool tests against a real CLI + temp workload stay scoped to
3.2.

This is the same precedent set by work item 2.1 (bridge shipped with
its own unit tests; integration deferred). The Gherkin scenarios are
explicitly unit-level ("Given the bridge will return…", "Given the
bridge raises…"), so the tests belong here.

## Technical decisions

- **Module layout: `tools.py` with a registry.** Considered three
  patterns: (A) inline `@mcp.tool` decorators in `server.py` —
  idiomatic for small surfaces but couples 2.3's testability to 2.4's
  bootstrapping; (B) `tools.py` with plain callables + a `TOOLS` list
  — keeps tools independently importable for unit tests, matches the
  thin-wrapper invariant (REQ-08); (C) `tools.py` with a
  `register(mcp)` function holding inline decorators — preserves the
  decorator idiom but makes tools awkward to import-and-call directly.
  Chose **B**. Our spec scenarios stub the bridge and assert against
  each callable directly; B is the only pattern that supports that
  cleanly. The trade-off is loose-typed registry (`list` of callables)
  rather than per-function decorators; acceptable given the surface is
  fixed at 12.

- **Shared error-mapping wrapper.** Every tool has the same try/except
  shape. To satisfy REQ-08 (no business logic, no op-specific
  conditionals) and keep tool bodies thin, introduce a private helper
  `_invoke(op: str, args: list[str]) -> Any` in `tools.py` that wraps
  `bridge.invoke` and does the error mapping for all three exception
  types. Each tool body becomes: assemble argv, return
  `_invoke(op, args)`.

- **Optional-flag construction.** Each tool's body is a short
  assembly of positional args followed by zero or more `--flag value`
  pairs for set optional kwargs. A small private helper (e.g.
  `_flag(name, value)` returning `["--name", str(value)]` if value is
  not None, else `[]`) keeps each tool body compact and visually
  uniform. Required positional args are added explicitly per tool.

- **Tool name clash with builtins.** `list` shadows the Python builtin
  within `tools.py`. Acceptable — the file is scoped narrowly, no
  built-in `list` usage is needed inside it, and shadowing is preferred
  to renaming the function (e.g. to `list_`) and threading
  `name="list"` through the registration call. `from __future__ import
  annotations` lets us still use `list[str]` etc. in type hints via
  string evaluation if needed.

- **Per-op kwarg derivation.** The implementing agent SHALL derive
  each tool's signature by running `swc-workload <op> --help` and
  mapping the documented positional args and flags to typed Python
  kwargs. Populate the per-op kwarg reference table in `specs.md` as
  this work proceeds — any drift between the table and the live CLI
  is a bug surfaced at review time.

- **MCP error type — agent verifies against SDK.** The exact type to
  raise (plain `Exception`, `mcp.McpError`, `mcp.ToolError`, etc.)
  depends on what the installed `mcp` SDK exposes for tool errors.
  The agent SHALL check the SDK first and use whatever surfaces a
  structured tool error to the client. The spec only requires that the
  message content match REQ-03 / REQ-04 / REQ-05.

## Deferred

- FastMCP instantiation, server name configuration, startup CLI
  presence check, stdio transport, console-script wiring — all 2.4.
- End-to-end tests exercising each tool against a real `swc-workload`
  binary + temp workload — 3.2.
- Protocol-level smoke test via the SDK's in-memory client — 3.3.

## Notes

- The `mcp` Python SDK is declared in `pyproject.toml` but may not yet
  be installed in the local `.venv`. The agent should ensure it is
  installed (`.venv/bin/pip install -e ".[dev]"` re-runs the editable
  install) before importing it.
- Each tool's docstring becomes the MCP tool description visible to
  clients. Write a one-line, agent-friendly summary per tool (e.g.
  "Add a work item to the workload, optionally under a parent or at a
  specific position"). Derive from the CLI op's help text.
- Argv construction must match the CLI's actual flag/positional
  ordering — the bridge passes argv verbatim. Where the CLI's help
  shows positional ordering (e.g. `swc-workload add <title>`),
  positionals come before `--flag` pairs.
