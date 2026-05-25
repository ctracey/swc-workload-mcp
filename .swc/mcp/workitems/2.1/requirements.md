# Requirements — 2.1: Subprocess bridge

## Intent

Build a subprocess bridge module that lets MCP tool implementations invoke
the externally-installed `swc-workload` CLI with `--json` and get back
parsed structured output, without each tool knowing anything about
subprocess plumbing. The bridge is the single seam between the MCP server
and the CLI; tool definitions and error mapping sit on top of it.

## Constraints

- Bridge is a thin pass-through — no business logic, no per-op knowledge.
- Binary resolution: `SWC_WORKLOAD_BIN` env var (testing stub override) →
  `shutil.which("swc-workload")` on PATH.
- Returns parsed JSON; raw failures (non-zero exit, missing CLI) bubble
  up untouched for 2.2 to refine into MCP errors.

## Out of scope

- Error mapping → work item 2.2.
- MCP tool definitions → work item 2.3.
- FastMCP server wiring → work item 2.4.
- Dev-time CLI installation (handled by `pipx install` from the CLI repo;
  the env var is **not** for dev convenience, only for test stubs).

## Approach direction

A `swc_workload_mcp/bridge.py` module with a small function surface
(e.g. `invoke(op, args)`) that resolves the binary, runs it as a
subprocess with `--json`, parses stdout, and returns the structured
result. Architecture doc captures the shape — this work item realises it.

## Parked

- CLI rename: the architecture/notes/plan docs still reference
  `swc_workload` (underscore); the installed binary is `swc-workload`
  (hyphen). Update during implementation or capture as a follow-up.
