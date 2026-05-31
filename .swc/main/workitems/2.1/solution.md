# Solution Design — 2.1: Subprocess bridge + error handling

## Approach

Implement `swc_workload_mcp/bridge.py` as a thin, stateless pass-through
layer. A single function `invoke(op: str, args: list[str]) -> Any`
resolves the CLI binary (`SWC_WORKLOAD_BIN` env → `shutil.which`), runs
it via `subprocess.run(..., capture_output=True, text=True)` with the
op, the caller's args, and `--json` appended, then JSON-parses stdout
and returns the result. Three named exceptions cover the failure modes
(`CLINotFoundError`, `CLIExecutionError`, `CLIResponseError`), all
extending a common `BridgeError` base so callers can catch broadly. No
shell, no stdin, no timeout. The bridge knows nothing about workload
paths or per-op semantics — all op-specific args (including
`--workload <path>`) are assembled by the caller (the MCP tool layer,
work item 2.3).

## Test approach

Full TDD — write a pytest test per Gherkin scenario in `specs.md`,
implement until each passes, update docs as scenarios are completed.

Test fixture style: a stub `swc-workload` is a small Python script
written to a `tmp_path` directory by the test, with shebang and
executable bit set. PATH-lookup scenarios prepend that directory to
`PATH` via `monkeypatch.setenv`. Env-var scenarios set
`SWC_WORKLOAD_BIN` directly to the stub path. No subprocess mocking —
real processes, deterministic stubs that emit canned stdout/stderr and
exit codes from environment-driven config.

## Technical decisions

- **Function signature:** `invoke(op: str, args: list[str]) -> Any`.
  Flat pass-through; caller assembles all op-specific args including
  `--workload`. Bridge appends `--json` and runs.
- **Subprocess call:** `subprocess.run([binary, op, *args, "--json"],
  capture_output=True, text=True, check=False)`. No `shell=True`, no
  `stdin`, no `timeout` (CLI ops are local; add a timeout later if
  needed).
- **Exception hierarchy:** common base `BridgeError`. Subclasses
  `CLINotFoundError`, `CLIExecutionError`, `CLIResponseError`. Each
  carries structured context as attributes (`searched_paths`,
  `exit_code`, `stderr`, `truncated_stdout`) plus a useful `str()`.
- **Response truncation:** `CLIResponseError.truncated_stdout` caps raw
  stdout at 500 characters with an ellipsis marker if longer. Keeps
  exception/log output legible.
- **CLI service is stateless / MCP service is decoupled.** Bridge takes
  args per call; no caching, no env-resolved workload path, no startup
  config. Required-param enforcement happens at the tool layer (2.3),
  not here.
- **Docs rename — fixed inline.** Update `plan.md`, `architecture.md`,
  and `notes.md` to replace remaining `swc_workload` (underscore)
  references with `swc-workload` (hyphen) where they refer to the
  installed binary name. Leave the Python package name
  (`swc_workload_mcp`) and CLI repo URL (`swc-workload-cli`) alone.

## Deferred

- **Subprocess timeout.** Not added now. Revisit if a slow/hung CLI
  surface a real problem during integration testing.
- **stdin support.** No CLI op currently reads stdin; not added.

## Notes

- Use `pytest`'s `monkeypatch` and `tmp_path` fixtures — the project
  already declares `pytest>=8` in dev deps.
- Place tests at `tests/mcp/test_bridge.py` to match the folder
  structure called out in `architecture.md`.
- The CLI's `--json` flag is assumed to apply to every op. If any op
  doesn't honour it, the bridge will surface that as a normal
  `CLIExecutionError`; the fix would live in the CLI repo, not here.
- The "absorbed" workload items: this delivery covers the original
  scope of 2.1 (bridge) + 2.2 (error mapping at the bridge level) + 3.1
  (bridge unit tests). The MCP-tool-level error formatting with
  user-facing hint text remains in 2.3.
