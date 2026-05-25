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
