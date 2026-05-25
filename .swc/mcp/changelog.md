# Changelog

## Session — planning the MCP conversion `2026-05-21`

- Created branch `mcp` and registered it in `.swc/_meta.json`.
- Scaffolded the planning docs under `.swc/mcp/` and filled them in
  through the full six-stage planning workflow: context, intent, solution,
  delivery, breakdown, finalise.
- Decided to wrap the existing `swc_workload` CLI with a lightweight Python
  MCP server (subprocess + `--json`) rather than refactor the CLI.
- Recorded the agreed approach in `architecture.md` (tech stack, layout,
  constraints), `notes.md` (decisions, open questions, deferred items),
  `plan.md` (goal, features, delivery shape, out of scope), `workload.md`
  (5 phases broken into 17 sub-items), and `pipeline.md` (build, dev env,
  acceptance).
- Motivation: produce a planning artefact a future session can pick up
  and execute from cold without re-deriving the conversation.

## Session — work item 2.1: subprocess bridge + error handling `2026-05-25`

- Delivered work item 2.1: added `swc_workload_mcp/bridge.py` exposing
  `invoke(op, args)` with a typed exception hierarchy (`BridgeError`,
  `CLINotFoundError`, `CLIExecutionError`, `CLIResponseError`).
- Binary resolution: `SWC_WORKLOAD_BIN` env var → `shutil.which("swc-workload")`.
  Subprocess call uses no shell, no stdin, `check=False`; stdout is parsed
  as JSON; long stdout truncated to 500 chars in `CLIResponseError`.
- Added `tests/mcp/test_bridge.py` — 9 pytest scenarios driving real
  subprocesses against a parameterised Python stub, with an autouse
  fixture that isolates `SWC_WORKLOAD_BIN` and `PATH`. All green.
- Renamed binary references `swc_workload` → `swc-workload` across
  `plan.md`, `architecture.md`, `notes.md`, `pyproject.toml`, and the
  `swc_workload_mcp/__init__.py` docstring.
- Refined workload breakdown during delivery: folded 2.2 into 2.1, dropped
  3.1 (covered by the bridge tests), and added work item 6 for release
  automation.
- Code review flagged 4 info findings (stderr truncation, empty env var
  fallthrough, `os.access` edge cases, README/pipeline doc drift) — all
  accepted as tech debt in `.swc/mcp/tech-debt.md`.
- Marked 2.1 done; parent work item 2 rolled up to `[-]`.
- Motivation: ship the bridge layer that all future MCP tools (2.3, 2.4)
  will sit on top of.

## Session — work item 2.3: define MCP tools `2026-05-25`

- Delivered work item 2.3: added `swc_workload_mcp/tools.py` with 12
  typed Python callables, one per CLI op (`init`, `exists`, `list`,
  `find`, `summary`, `add`, `rename`, `delete`, `reset`, `start`,
  `complete`, `move`), plus a `TOOLS` registry for 2.4's server to
  iterate over.
- Each tool body is argv assembly plus `return _invoke(op, args)`. The
  private `_invoke` helper centralises the three-way `BridgeError` →
  `mcp.server.fastmcp.exceptions.ToolError` mapping with the message
  content required by REQ-03 / REQ-04 / REQ-05. `_flag` and
  `_bool_flag` keep optional-flag construction uniform.
- Added `tests/mcp/test_tools.py` — 38 unit tests covering all 7
  Gherkin scenarios plus per-op argv spot checks; bridge stubbed via
  `monkeypatch.setattr(tools.bridge, "invoke", recorder)`. Full suite
  47 passed (9 bridge + 38 tools), no regressions.
- Per-op kwarg reference table in `specs.md` populated against CLI
  v1.1.2 (derived from `swc-workload <op> --help`). `architecture.md`
  folder structure updated to list `tools.py`.
- Key shape decisions: `add` modelled as `placement` + `ref` (mirrors
  the CLI's three positional forms); `move` modelled as `direction` +
  optional `target`; `list`'s `no_ids` as `bool | None`; `list`
  shadows the builtin intentionally (pattern B from solution.md).
- Code review verdict PASS — 4 informational observations only, no
  defects or tech debt.
- Marked 2.3 done; parent work item 2 stays `[-]` (2.4 outstanding).
- Note: the implementing agent's harness blocked its `summary.md`
  write; orchestrator transcribed the agent's final report into
  `summary.md` and re-verified the test results before recording.
- Motivation: surface the workload operations as structured MCP tools
  so 2.4 can register them against a FastMCP server and clients can
  start calling them.
