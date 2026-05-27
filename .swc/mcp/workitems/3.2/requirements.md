# Requirements — 3.2: Tool-level tests — each tool exercised against a temp workload

## Intent

Build an end-to-end MCP test suite that mirrors every behavioural
scenario in the `swc-workload` CLI's own test suite, exercising each
scenario through the running MCP server (via the SDK's in-memory
client) against a real `swc-workload` subprocess + per-test temp
workload — instead of the CLI's pattern of invoking `python -m
swc_workload` directly. The 2.3 wrapper-level unit tests already
cover argv translation in isolation; this work item validates the
*composed* behaviour matches the CLI's, which is the only place
wrapper-vs-CLI drift can hide. The 2.4 in-memory client smoke (REQ-09)
proves the pattern works for one tool; 3.2 expands it to comprehensive
coverage. The work item is also the natural place to catch the
demo-surfaced bug with `add(placement="to", ref="1")` reportedly not
placing the new item as a child of `1`.

## Constraints

- **Mirror behavioural scenarios, not CLI mechanics.** Skip help-text
  tests, module entry-point tests, and pure argparse rejection tests
  — those exercise the CLI's surface, not our tool layer's.
  Authoring (`add` / `delete` / `rename` / `move`), I/O
  (`init` / `list` / `find` / `summary`), and status
  (`start` / `complete` / `reset`) all stay in scope.
- **In-memory client harness.** Use
  `mcp.shared.memory.create_connected_server_and_client_session`
  (same pattern as 2.4 REQ-09) so each test invokes tools through the
  real FastMCP server without spawning a subprocess for the server
  itself. The CLI is still invoked as a subprocess by the bridge —
  that's the point.
- **Real `swc-workload` CLI required at test time.** Fail loudly if
  the CLI isn't installed; do not skip silently. Matches the 2.4
  REQ-09 posture.
- **Per-test temp workload via `tmp_path`.** No shared state between
  tests. Each test fully sets up its workload via the tools under
  test.
- **Mirror the CLI's test layout where it helps clarity.** Split by
  domain (authoring / io / status) so the MCP suite reads in parallel
  with the CLI's. Specific scenario names should track the CLI's
  scenario names so traceability is obvious.
- **Tests must use only public tool API.** No reaching into
  `tools.TOOLS` internals, no monkeypatching the bridge — these tests
  exercise the wired chain end-to-end. Test wrappers/fixtures may
  encapsulate the in-memory client setup.

## Out of scope

- Protocol-level coverage beyond the in-memory client (transport
  edge cases, stdio framing, etc.) — work item 3.3.
- CI installing the CLI before the test suite runs — work item 6.1.
- README / docs polish — work item 4.
- The wrapper-level unit tests already shipped in 2.3 — those stay,
  this work item adds an integration tier on top.

## Approach direction

Phased delivery — deliberately departing from the default
scenario-driven TDD loop because we want to *measure* the wiring's
state of correctness, not just drive a single behaviour:

1. **Phase A — build & report.** Implementation agent ports every
   behavioural CLI scenario into `tests/mcp/` (split per domain),
   builds the in-memory client fixture, runs the full suite, reports
   pass/fail per test. No production-code changes in this phase.
2. **User gate.** Orchestrator brings the pass/fail report back to
   the user. The user decides which failures to fix in this work
   item (the demo bug being the obvious one; there may be others).
3. **Phase B — fix.** Fresh implementation pass(es) address the
   approved failures. This is structurally identical to the refine
   stage's pass-N loop, just driven off test failures rather than
   code-review findings. The user gates between passes.

Test files live at `tests/mcp/test_tools_integration_<domain>.py`
(authoring / io / status). A shared `tests/mcp/_integration.py` (or
similar) module holds the in-memory client fixture, mirroring the
CLI's `swcw` / `swcw_ready` fixtures but adapted for MCP tool calls.

## Parked

- **Exact fixture name and signature** for the MCP equivalent of
  `swcw_ready` — solution design will settle whether the fixture
  yields a `call_tool` async helper, a sync wrapper, or a
  ClientSession directly.
- **Whether to capture-and-report failures structurally** (e.g. emit
  a machine-readable summary the orchestrator parses) or rely on
  pytest's standard output. Phase A's "report pass/fail counts" step
  needs a low-friction way to surface results — likely just pytest's
  exit code + summary line is enough.
- **Whether to split argv-rejection cases** that exercise the CLI's
  validation (e.g. `add "x" to` without a target). The CLI rejects
  these at argparse; in the MCP layer the same call surfaces as a
  `CLIExecutionError` → `ToolError`. Worth representative coverage
  in 3.2 since the *error round-trip* is part of the wiring contract,
  even if the argparse mechanism itself isn't.
- **Per-tool spec scenario IDs.** The CLI tests don't carry
  REQ-NN tags; we'll either invent IDs in 3.2's `specs.md` or
  reference the CLI test name directly. Specs phase decides.
