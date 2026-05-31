# Solution Design — 3.2: Tool-level tests — each tool exercised against a temp workload

## Approach

Two-phase implementation:

- **Phase A — bulk port + report.** Implementation agent reads every
  source CLI test enumerated in `specs.md`'s catalogue, writes one
  MCP-equivalent test per source scenario into
  `tests/mcp/test_tools_integration_authoring.py`,
  `tests/mcp/test_tools_integration_io.py`, and
  `tests/mcp/test_tools_integration_status.py`, lands a shared
  `tests/mcp/conftest.py` carrying the in-memory MCP client fixtures
  (`mcpw` and `mcpw_ready`), runs the suite once at the end, and
  reports total / passing / failing per test plus an explicit list
  of intentionally-skipped scenarios with reasons. No production-code
  changes in this phase.
- **User gate.** Orchestrator brings the pass/fail report back to the
  user. User selects which failures to address in Phase B.
- **Phase B — fix loop.** One or more fresh implementation passes
  (structurally identical to `workflowDeliver_refine`'s pass-N loop)
  address the approved failures, re-running the full suite after each
  pass. Production-code changes are limited to the diagnosed minimum
  per finding.

## Test approach

**Deliberate departure from default scenario-driven TDD.** Phase A is
*bulk port + run + report* — the value is the failure list, not
red-green per scenario. Phase B is the per-failure fix loop, which
*does* follow TDD in spirit (the failing test is already in place
before the production-code change). This matches the requirements
decision: "Create full test suite first and report how many scenarios
succeed or fail. Then I can give go ahead to fix failing tests."

## Technical decisions

- **Fixture shape: `(call_tool, workload_folder, workload_json_path)`.**
  Async fixture in `tests/mcp/conftest.py` modelled on the CLI's
  `swcw` / `swcw_ready`:
  - `mcpw` — yields the triple against a fresh `tmp_path`. No
    `init` pre-run; the test calls `init` itself when needed.
  - `mcpw_ready` — depends on `mcpw`, calls the `init` tool, then
    yields the same triple. Matches the CLI's `swcw_ready`.
  Both fixtures use the in-memory client/server harness via
  `mcp.shared.memory.create_connected_server_and_client_session(server.mcp._mcp_server)`
  (same call site as 2.4 REQ-09).

- **`call_tool(name, **kwargs)` helper.** Async. Calls
  `session.call_tool(name, kwargs)`. Returns a small `ToolCallResult`
  dataclass (or namedtuple) with two fields:
  - `payload` — parsed JSON dict/list from the tool's text content
    on success (`None` if the call errored).
  - `error` — the error message string from the tool's error content
    on failure (`None` on success).
  Tests assert `result.payload[...]` on success paths or
  `assert "collide" in result.error` on error paths. Mirrors the CLI
  tests' `result.returncode == 0` / `assert "collide" in result.stderr`
  pattern.

- **Error surfacing — `isError` vs raised exception.** FastMCP's
  in-memory client returns errors via `CallToolResult.isError=True`
  with the message embedded in `content`. The agent confirms the
  exact shape on first use and codes the helper accordingly. If the
  SDK raises rather than returning an error result, the helper
  catches and normalises to the same `error` field.

- **Async pattern.** Every test is `async def` decorated with
  `@pytest.mark.anyio`. An `anyio_backend` fixture in `conftest.py`
  returns `"asyncio"`. Pattern identical to 2.4's
  `tests/mcp/test_server.py`.

- **Pre-seeded workload helper for malformed-shape tests.** The
  fixture exposes a `seed(content: str | dict | bytes)` helper that
  writes `workload.json` directly (bypassing the `init` tool). Used
  only for tests that exercise the file-load error paths
  (`test_load_workload_rejects_malformed_shape`,
  `test_load_workload_rejects_top_level_non_dict`,
  `test_load_workload_json_decode_error_reports_line_and_column`).
  These tests document the seeding rationale in their docstring.

- **Tests with no MCP equivalent — explicit skip with reason.** Listed
  in `specs.md` catalogue with notes; the agent ports each as a
  `pytest.skip` with a clear `reason="..."` string and includes them
  in the Phase A report under "intentionally skipped":
  - `test_list_without_json_is_text`,
    `test_text_output_includes_hash_next_to_title` — bridge always
    passes `--json`; text output not reachable through MCP.
  - `test_exists_json_form_true`, `test_exists_json_form_false` —
    collapse with the non-JSON `exists_true` / `exists_false` since
    the bridge always passes `--json`; the JSON-form variant is
    already what we cover.
  - `test_oserror_in_save_workload_surfaces_as_friendly_error` —
    simulating an OS error through the MCP layer requires invasive
    setup (read-only FS, monkeypatching the CLI subprocess); flagged
    as intentionally skipped, not silently dropped.
  - `test_parent_marked_done_with_undone_children_warns_on_stderr` —
    stderr warnings from the CLI are not currently surfaced as part
    of the tool result (bridge captures stderr but only uses it on
    non-zero exit). Agent investigates during port: if the CLI exits
    0 here, the warning is lost through MCP; mark as not-feasible
    with note. If the CLI exits non-zero, the warning surfaces via
    `CLIExecutionError` and the test ports normally.

- **Argparse rejection round-trip (REQ-09).** Catalogue tags 8 tests
  as argparse-level rejections. For each, the MCP test passes the
  equivalent shape through the tool, asserts `result.error is not
  None`, and asserts the CLI's stderr text appears in
  `result.error`. The agent does *not* try to match the exact
  argparse phrasing — just enough substring to prove the round-trip.

- **Test-name traceability (REQ-08).** Each MCP test name echoes the
  source CLI test name exactly. The MCP test's docstring includes a
  one-line `Mirrors: tests/bin/<file>::<test_name>` reference for
  traceability when the suites drift.

- **Phase A reporting format.** Agent runs `.venv/bin/pytest
  tests/mcp/test_tools_integration_*.py -v` once. The agent's
  summary in `summary.md` includes:
  - Total ported (= source count - intentionally-skipped count)
  - Passing count
  - Failing count
  - One bullet per failing test with the assertion line / message
  - Distinct section listing intentionally-skipped tests with reasons

- **Phase B brief format.** The orchestrator hands the agent a list
  of approved failing test names. The agent diagnoses each, makes
  the minimal production-code change to turn it green, re-runs the
  full suite, reports the new pass/fail counts. No broader refactors;
  no touching unrelated code. Mirrors `workflowDeliver_refine`'s
  pass-N agent prompt shape.

## Deferred

- **Protocol-level coverage** (transport edge cases, stdio framing
  contract, MCP-spec compliance beyond what the in-memory client
  exercises) — work item 3.3.
- **CI integration** ensuring `swc-workload` is installed before
  tests run — work item 6.1.
- **Performance characterisation** — 77 integration tests each
  spawning a subprocess will take roughly 5-15 seconds in aggregate
  on a typical machine. Acceptable; not optimised here.

## Notes

- Quality-baseline already verifies the `mcp` SDK, the
  `mcp.shared.memory` helper, and the `swc-workload` CLI are present
  in the dev environment. 2.4 surfaced `mcp.shared.memory` as the
  right import path; reuse it.
- The 2.4 server's `_register_tools()` runs at module import (tech
  debt F-02). For these integration tests, importing
  `swc_workload_mcp.server` materialises the FastMCP instance with
  all 12 tools already registered. The fixture just needs to pass
  `server.mcp._mcp_server` to the in-memory harness.
- The CLI test `test_add_as_child_of_parent` is structurally
  identical to the demo bug scenario (`add(placement="to", ref="2")`
  expecting a `2.1` child). If that MCP-equivalent test passes, the
  demo bug is somewhere outside our tool layer (Inspector wire
  format, the user's input quirks) — Phase B still has nothing to
  fix for it, and we close the loop with a confident "not a bug in
  our code; investigate Inspector input handling separately".
- The Phase A pass should not skip tests for tool-layer bugs it
  notices in passing — let the failing test express the bug,
  Phase B fixes it. Phase A's job is *measurement*, not pre-emptive
  patching.
