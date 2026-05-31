# Specs — 2.1: Subprocess bridge + error handling

## Users and Personas

- **MCP tool implementation** (internal caller) — wants a single function
  to invoke any `swc-workload` op with `--json` and get back parsed
  structured output, with errors surfaced as distinct, named exceptions
  carrying enough context to format actionable MCP errors upstream.

## User Journeys

### Happy path A — PATH resolution
1. Caller invokes `bridge.invoke(op, args)`.
2. `SWC_WORKLOAD_BIN` is unset.
3. Bridge resolves the binary via `shutil.which("swc-workload")`.
4. Bridge runs `<binary> <op> <args> --json` as a subprocess.
5. Subprocess exits 0; stdout is valid JSON.
6. Bridge returns the parsed JSON to the caller.

### Happy path B — env var override
1. Caller invokes `bridge.invoke(op, args)`.
2. `SWC_WORKLOAD_BIN` is set to an executable file path.
3. Bridge uses that path as the CLI binary (no PATH lookup).
4. Bridge runs the subprocess with `--json` and returns the parsed JSON.

### Error path — CLI not found
1. Caller invokes `bridge.invoke(op, args)`.
2. `SWC_WORKLOAD_BIN` is unset; `swc-workload` is not on PATH.
3. Bridge raises `CLINotFoundError` carrying the names/paths searched.

### Error path — env var points nowhere
1. Caller invokes `bridge.invoke(op, args)`.
2. `SWC_WORKLOAD_BIN` is set but the path doesn't exist or isn't
   executable.
3. Bridge raises `CLINotFoundError` carrying the bad path.

### Error path — CLI exits non-zero
1. Caller invokes `bridge.invoke(op, args)`.
2. Binary resolves and runs, but exits with a non-zero code.
3. Bridge raises `CLIExecutionError` carrying the exit code and stderr.

### Error path — output not parseable
1. Caller invokes `bridge.invoke(op, args)`.
2. Subprocess exits 0 but stdout is not valid JSON.
3. Bridge raises `CLIResponseError` carrying a truncated copy of stdout.

## Requirements

REQ-01: WHEN `SWC_WORKLOAD_BIN` is set and points to an executable file, the bridge SHALL use that path as the CLI binary.

REQ-02: WHEN `SWC_WORKLOAD_BIN` is unset, the bridge SHALL resolve the binary via `shutil.which("swc-workload")`.

REQ-03: WHEN the binary is resolved, the bridge SHALL invoke it as a subprocess with the op name, the caller's args, and `--json`.

REQ-04: WHEN the subprocess exits 0 and stdout is valid JSON, the bridge SHALL return the parsed JSON to the caller.

REQ-05: IF the binary cannot be resolved (env var missing-or-bad AND nothing on PATH), THEN the bridge SHALL raise `CLINotFoundError` carrying the paths/names searched.

REQ-06: IF the subprocess exits non-zero, THEN the bridge SHALL raise `CLIExecutionError` carrying the exit code and captured stderr.

REQ-07: IF the subprocess exits 0 but stdout is not valid JSON, THEN the bridge SHALL raise `CLIResponseError` carrying a truncated copy of the raw stdout for diagnostics.

## Acceptance Scenarios

```gherkin
# REQ-01
Scenario: env var override uses the provided binary path
  Given SWC_WORKLOAD_BIN is set to a path that points to an executable stub CLI
  And the stub CLI prints valid JSON and exits 0
  When the caller invokes bridge.invoke("list", [])
  Then the bridge runs the stub at the env-var path
  And the bridge does not perform a PATH lookup
  And the caller receives the parsed JSON

# REQ-02
Scenario: PATH lookup is used when env var is unset
  Given SWC_WORKLOAD_BIN is unset
  And a "swc-workload" executable is discoverable on PATH
  When the caller invokes bridge.invoke("list", [])
  Then the bridge resolves the binary via shutil.which("swc-workload")
  And invokes that binary

# REQ-03
Scenario: invocation passes op, args, and --json
  Given the binary is resolved
  When the caller invokes bridge.invoke("add", ["new item", "--workload", "/tmp/w"])
  Then the subprocess is launched with argv: <binary> add "new item" --workload /tmp/w --json

# REQ-04
Scenario: successful run returns parsed JSON
  Given the resolved CLI exits 0
  And stdout is the JSON {"ok": true, "items": []}
  When the caller invokes bridge.invoke("list", [])
  Then the caller receives a Python value equal to {"ok": True, "items": []}

# REQ-05a
Scenario: missing CLI everywhere raises CLINotFoundError
  Given SWC_WORKLOAD_BIN is unset
  And no "swc-workload" executable is on PATH
  When the caller invokes bridge.invoke("list", [])
  Then the bridge raises CLINotFoundError
  And the exception carries the binary name searched ("swc-workload")

# REQ-05b
Scenario: env var pointing nowhere raises CLINotFoundError
  Given SWC_WORKLOAD_BIN is set to a path that does not exist
  When the caller invokes bridge.invoke("list", [])
  Then the bridge raises CLINotFoundError
  And the exception carries the bad path

# REQ-06
Scenario: non-zero exit raises CLIExecutionError
  Given the resolved CLI exits with code 2
  And stderr contains "workload not initialised"
  When the caller invokes bridge.invoke("list", [])
  Then the bridge raises CLIExecutionError
  And the exception carries exit_code == 2
  And the exception carries stderr containing "workload not initialised"

# REQ-07
Scenario: unparseable stdout raises CLIResponseError
  Given the resolved CLI exits 0
  And stdout is "not json {{{"
  When the caller invokes bridge.invoke("list", [])
  Then the bridge raises CLIResponseError
  And the exception carries a truncated copy of the raw stdout
```

## Automation note

Every scenario above is automated as part of this work item's delivery
(TDD-style): the implementation agent writes pytest tests against each
scenario before the bridge code is finalised. A stub CLI binary (a small
shell script or Python script that emits canned JSON) is used to drive
the env-var path; PATH-lookup scenarios prepend a temp directory to PATH
containing the same stub. No subprocess mocking — real processes,
deterministic stubs.
