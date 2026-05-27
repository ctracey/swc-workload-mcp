# Summary — 2.1: Subprocess bridge + error handling

## Status

Complete — 9 pytest scenarios green, bridge module shipped, docs renamed.

## Files created

- `swc_workload_mcp/bridge.py` — the bridge module (`invoke(op, args)` +
  exception hierarchy)
- `tests/__init__.py`, `tests/mcp/__init__.py`
- `tests/mcp/test_bridge.py` — 9 tests covering all REQs (REQ-01 →
  REQ-07, with REQ-05 split into 05a/05b + explicit truncation test)
- `.swc/mcp/workitems/2.1/context.md` — pass-1 notes
- `.venv/` — local dev environment (gitignored)

## Files modified

- `.swc/mcp/plan.md` — binary rename `swc_workload` → `swc-workload`
- `.swc/mcp/architecture.md` — binary rename
- `.swc/mcp/notes.md` — binary rename
- `swc_workload_mcp/__init__.py` — fixed stale `bin/swc_workload`
  docstring
- `pyproject.toml` — binary rename in description

## Implementation

The bridge exposes `invoke(op: str, args: list[str]) -> Any` plus a
typed exception hierarchy:

- `BridgeError` (base)
- `CLINotFoundError` (carries `searched_paths`)
- `CLIExecutionError` (carries `exit_code`, `stderr`)
- `CLIResponseError` (carries `truncated_stdout`, capped at 500 chars
  with `...` marker)

Binary resolution: `SWC_WORKLOAD_BIN` env var (must point at an
existing executable, else raises `CLINotFoundError`) →
`shutil.which("swc-workload")` on PATH (raises `CLINotFoundError` with
the binary name on miss).

Subprocess call: `subprocess.run([binary, op, *args, "--json"],
capture_output=True, text=True, check=False)`. No shell, no stdin, no
timeout (deferred per solution.md).

## Test strategy

Full TDD: one pytest test per Gherkin scenario, written failing first.
Real subprocesses driven by a Python stub written to `tmp_path` — no
mocking. Autouse `_isolate_env` fixture clears `SWC_WORKLOAD_BIN` and
overrides `PATH` to a non-existent dir so tests are deterministic on
hosts where `swc-workload` is on PATH.

## Pipeline

- **Build (`pytest`):** green. Run as `.venv/bin/pytest`. Contributors
  bootstrap with `python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"`.
- **Dev env start (`python -m swc_workload_mcp`):** not verified —
  `__main__.py` is still the placeholder `NotImplementedError` from
  work item 1.2. Wired up in 2.3/2.4.
- **Acceptance manual smoke:** out of scope (work item 5).

## Build confidence

High. Real-subprocess tests cover every spec scenario including all
four error paths. Bridge has no per-op knowledge, so it layers cleanly
under future tool definitions in 2.3.

## Scope flags for reviewer

- `README.md` still describes the removed plugin layout (refers to
  `bin/swc_workload`). Out of scope here — README rewrite is work item
  4. Flagged for reviewer.
- `pipeline.md`'s `## Build` command (`pytest`) doesn't reference the
  venv activation step. Not a 2.1 regression but worth tightening in
  the CI/docs work items.

## Approach needs revisiting

No.
