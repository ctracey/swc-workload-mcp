# Specs — 2.3: Define MCP tools

## Users and Personas

The "users" of this tool surface are technical actors, not human end-users:

- **MCP client** (Claude Code, Claude Desktop, or any MCP-aware host) —
  lists the server's tools, sees their typed schemas, and calls them
  with structured arguments on behalf of the agent. Precondition: the
  FastMCP server (work item 2.4) has been started and the client is
  connected.
- **Agent code inside the client** — chooses which tool to invoke and
  with what arguments, based on the user's request. Precondition: the
  agent has received the tool list from the client and selected one.

## User Journeys

### Happy path — tool call succeeds

1. Agent invokes a registered tool (e.g. `list`) with valid kwargs.
2. Tool translates the kwargs into the CLI's argv: positional args in
   order, then `--flag value` for each set optional kwarg.
3. Tool calls `bridge.invoke(op, args)`.
4. Bridge returns the parsed JSON object from the CLI.
5. Tool returns the JSON to the client, unchanged.

### Error path A — CLI binary missing

1. Agent invokes a registered tool.
2. Tool calls `bridge.invoke`.
3. Bridge raises `CLINotFoundError`.
4. Tool catches the exception and re-raises as an MCP tool error with
   message: `"swc-workload not found. Install from
   https://github.com/ctracey/swc-workload-cli or set
   SWC_WORKLOAD_BIN."`

### Error path B — CLI exited non-zero

1. Agent invokes a registered tool.
2. Tool calls `bridge.invoke`.
3. Bridge raises `CLIExecutionError` carrying `exit_code` and `stderr`.
4. Tool catches the exception and re-raises as an MCP tool error with
   message: `"swc-workload op failed (exit N): <stderr>"`.

### Error path C — CLI stdout not valid JSON

1. Agent invokes a registered tool.
2. Tool calls `bridge.invoke`.
3. Bridge raises `CLIResponseError` carrying truncated stdout.
4. Tool catches the exception and re-raises as an MCP tool error with
   message: `"swc-workload returned unparseable output (truncated):
   <…>. Likely a CLI/MCP version mismatch."`

## Requirements

**REQ-01** (event-driven) — WHEN a tool is invoked with valid kwargs, it
SHALL translate them into argv (positional args in CLI order, then
`--flag value` for each set optional kwarg), call `bridge.invoke(op,
args)`, and return the parsed JSON result to the client unchanged.

**REQ-02** (event-driven) — WHEN a tool is invoked without an optional
kwarg, the corresponding CLI flag SHALL NOT appear in the argv passed
to `bridge.invoke`.

**REQ-03** (unwanted behaviour) — IF the bridge raises
`CLINotFoundError`, THEN the tool SHALL re-raise as an MCP tool error
whose message contains `"swc-workload not found"`, the CLI repo URL
`https://github.com/ctracey/swc-workload-cli`, and the env-var name
`SWC_WORKLOAD_BIN`.

**REQ-04** (unwanted behaviour) — IF the bridge raises
`CLIExecutionError`, THEN the tool SHALL re-raise as an MCP tool error
whose message contains the exit code (rendered as `exit N`) and the
captured stderr text.

**REQ-05** (unwanted behaviour) — IF the bridge raises
`CLIResponseError`, THEN the tool SHALL re-raise as an MCP tool error
whose message contains the truncated stdout and the phrase `"CLI/MCP
version mismatch"`.

**REQ-06** (ubiquitous) — The tool module SHALL expose exactly 12
tools, one per CLI op, with flat names: `init`, `exists`, `list`,
`find`, `summary`, `add`, `rename`, `delete`, `reset`, `start`,
`complete`, `move`.

**REQ-07** (ubiquitous) — Each tool's kwargs SHALL correspond 1:1 to
the underlying CLI op's args (names, required/optional, types) as
documented in `swc-workload <op> --help`. The implementing agent
derives the kwarg list per op by running the CLI's help.

**REQ-08** (ubiquitous) — Tool function bodies SHALL contain argv
translation and error mapping only — no workload business logic, no
op-specific conditionals beyond what is needed to translate kwargs to
argv.

## Acceptance Scenarios

```gherkin
# REQ-01
Scenario: tool returns parsed JSON from a successful CLI op
  Given the bridge will return {"items": []} for op="list" args=["--workload", "/tmp/wl"]
  When the "list" tool is invoked with workload="/tmp/wl"
  Then bridge.invoke is called with op="list" and args=["--workload", "/tmp/wl"]
  And the tool returns {"items": []} unchanged

# REQ-01
Scenario: tool forwards positional args alongside flags
  Given the bridge will return {"id": "1.1"} for op="add" args=["--workload", "/tmp/wl", "Foo"]
  When the "add" tool is invoked with workload="/tmp/wl" and title="Foo"
  Then bridge.invoke is called with op="add" and args=["--workload", "/tmp/wl", "Foo"]
  And the tool returns {"id": "1.1"} unchanged

# REQ-02
Scenario: optional kwarg omitted → flag absent from argv
  Given the "list" tool declares optional kwarg "filter"
  When the "list" tool is invoked with workload="/tmp/wl" and filter omitted
  Then "--filter" does not appear in the argv passed to bridge.invoke

# REQ-02
Scenario: optional kwarg set → flag present in argv
  Given the "list" tool declares optional kwarg "filter"
  When the "list" tool is invoked with workload="/tmp/wl" and filter="bug"
  Then bridge.invoke is called with args containing "--filter" "bug"

# REQ-03
Scenario: missing CLI → MCP error with install hint
  Given the bridge raises CLINotFoundError(searched_paths=["swc-workload"])
  When any tool is invoked
  Then the tool raises an MCP tool error
  And the error message contains "swc-workload not found"
  And the error message contains "https://github.com/ctracey/swc-workload-cli"
  And the error message contains "SWC_WORKLOAD_BIN"

# REQ-04
Scenario: CLI exited non-zero → MCP error with exit code and stderr
  Given the bridge raises CLIExecutionError(exit_code=2, stderr="no such ref: 9.9")
  When any tool is invoked
  Then the tool raises an MCP tool error
  And the error message contains "exit 2"
  And the error message contains "no such ref: 9.9"

# REQ-05
Scenario: CLI returned unparseable output → MCP error with version-mismatch hint
  Given the bridge raises CLIResponseError(raw_stdout="not json blah")
  When any tool is invoked
  Then the tool raises an MCP tool error
  And the error message contains "not json blah"
  And the error message contains "CLI/MCP version mismatch"

# REQ-06
Scenario: tool module exposes exactly the 12 expected tools
  When the registered tool callables are enumerated
  Then the names are exactly: init, exists, list, find, summary, add, rename, delete, reset, start, complete, move

# REQ-07
Scenario: each tool's kwargs match its CLI op's --help
  Given the CLI's "<op> --help" output documents the op's positional args and flags
  When each tool's signature is inspected
  Then the kwargs (names, required/optional, types) correspond 1:1 to the CLI args
```

## Per-op kwarg reference

The implementing agent SHALL populate this table by running
`swc-workload <op> --help` for each op and recording the positional
args and flags. The table lives in this doc so that drift between the
spec and the live CLI is detectable at review time.

Derived from `swc-workload <op> --help` against CLI version `1.1.2`.

| Op | Required kwargs (positional + required flags) | Optional kwargs (flags) |
| --- | --- | --- |
| `init` | `workload: str` | — |
| `exists` | `workload: str` | — |
| `list` | `workload: str` | `ref: str \| None`, `filter: str \| None`, `exclude: str \| None`, `no_ids: bool \| None` |
| `find` | `workload: str`, `keyword: str` | — |
| `summary` | `workload: str` | — |
| `add` | `workload: str`, `title: str` | `placement: str \| None` (`"to"` or `"at"`), `ref: str \| None` |
| `rename` | `workload: str`, `ref: str`, `title: str` | — |
| `delete` | `workload: str`, `ref: str` | — |
| `reset` | `workload: str`, `ref: str` | — |
| `start` | `workload: str`, `ref: str` | — |
| `complete` | `workload: str`, `ref: str` | — |
| `move` | `workload: str`, `ref: str`, `direction: str` (`up\|down\|top\|bottom` or the literal `"to"`) | `target: str \| None` (required when `direction="to"`) |

Notes on the trickier shapes:

- `add` mirrors the CLI's three forms via two optional kwargs. Omit
  both for a top-level add; set `placement="to"` + `ref="<parent>"` to
  append as a child; set `placement="at"` + `ref="<position>"` to
  insert at a slot. The MCP layer does not validate `placement` —
  enforcement stays with the CLI.
- `move` mirrors the CLI's two forms via the `direction` + `target`
  pair. Set `direction` to `up|down|top|bottom` for a relative move
  (leave `target=None`); set `direction="to"` + `target=<position>`
  for an absolute move. Validation stays with the CLI.
- `list`'s `no_ids` is a boolean switch: ``True`` emits ``--no-ids``,
  ``None`` / ``False`` omit it entirely.

`--workload` is required by every op (per the CLI's folder contract)
and is surfaced on every tool as a required kwarg, `workload: str`.

## Validation Rules

Not applicable. The MCP protocol layer (FastMCP) validates kwargs
against each tool's declared schema before the tool body runs. The
tools themselves do no further validation.
