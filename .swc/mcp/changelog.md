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

## Session — work item 2.4: FastMCP server + stdio wiring `2026-05-26`

- Delivered work item 2.4: added `swc_workload_mcp/server.py` —
  module-level `FastMCP("swc-workload")` + tool-registration loop
  over `tools.TOOLS` + `main()` doing a fail-fast CLI presence check
  via `bridge.resolve_binary()` (on `CLINotFoundError`, prints the
  actionable stderr message and `SystemExit(1)`; on success, runs
  `mcp.run("stdio")`).
- Replaced the `__main__.py` `NotImplementedError` placeholder with
  a thin delegation to `server.main()`. Both `python -m
  swc_workload_mcp` and the `swc-workload-mcp` console script now
  reach the same entry point.
- Promoted `bridge._resolve_binary` to public `bridge.resolve_binary`
  — single source of truth for binary resolution shared by the
  startup check and per-tool `invoke`. No behavioural change.
- Added `tests/mcp/test_server.py` — 10 unit tests (one per Gherkin
  scenario) including a REQ-09 end-to-end smoke that boots the server
  in-memory via `mcp.shared.memory.create_connected_server_and_client_session`
  and invokes `init` against the real CLI to assert `workload.json`
  lands on disk. Smoke fails loudly when the CLI isn't installed, per
  the solution-design call to keep the signal sharp. Full suite: 57
  passed.
- **Flipped the startup decision from graceful degradation → fail-fast.**
  The user called for this during requirements; `.swc/mcp/architecture.md`
  and `.swc/mcp/notes.md` were rewritten to match (REQ-08). The actionable
  stderr template (binary name, searched paths, install URL, env-var
  override) is shared with the tool-layer error mapping in `tools.py`.
- Created `docs/architecture.md` — public-facing architecture overview
  (MCP intro, ASCII layer diagram, per-layer detail, startup behaviour).
  Linked from the new README; full client-registration matrix stays
  for work item 4.
- Refine: 5 info findings from code review. Pass 2 resolved F-03
  (REQ-01 assertion `issubset` → `==`) and F-04 (REQ-03 positive guard
  tightened to a regex matching `for ... in tools.TOOLS`). Deferred
  to `.swc/mcp/tech-debt.md`: F-01 (duplicated "not found" message
  template between `server.py` and `tools.py`), F-02 (registration at
  module import time — documented trade-off), F-05 (folds into F-01).
- Focused README rewrite to support the MCP Inspector demo —
  intentional partial-scope pull from work item 4 because the prior
  README still described the removed Claude Code plugin layout. Work
  item 4 will expand with the full client-registration matrix,
  badges, and version-sync details.
- Marked 2.4 done; parent work item 2 rolled up to `[x]` — all of
  phase 2 complete.
- Motivation: stand the service up end-to-end at the process level so
  MCP clients can actually launch it, list tools, and exercise them.
  Demo via Inspector surfaced a possible tool-layer bug (`add` with
  `placement="to" ref="1"` reportedly didn't land as a child); 3.2
  (planned next) will introduce the end-to-end test coverage needed
  to characterise and fix it cleanly.
