# Summary — 3.2: Tool-level tests — each tool exercised against a temp workload

## Pass 1 — Phase A (bulk port + report) — 2026-05-26

### Changes

- **`tests/mcp/conftest.py`** (NEW, ~8KB) — `anyio_backend` fixture
  returning `"asyncio"`; async `mcpw` / `mcpw_ready` fixtures yielding
  `(call_tool, workload_folder, workload_json, seed)`; `ToolCallResult`
  dataclass with `.payload` (parsed JSON on success) and `.error`
  (string on failure); `call_tool(name, **kwargs)` async helper using
  `mcp.shared.memory.create_connected_server_and_client_session(server.mcp)`
  (FastMCP passed directly per quality-baseline hint — no
  `_mcp_server` workaround needed); `seed(content)` helper for
  pre-seeded workload tests.
- **`tests/mcp/test_tools_integration_authoring.py`** (NEW, ~30KB) —
  39 ported scenarios mirroring CLI's `test_swc-workload_authoring.py`.
- **`tests/mcp/test_tools_integration_io.py`** (NEW, ~25KB) — 31 io
  scenarios from CLI's `test_swc-workload_io.py` + 2 from
  `test_find_by_ref.py` = 33 total.
- **`tests/mcp/test_tools_integration_status.py`** (NEW, ~5.7KB) — 5
  scenarios mirroring CLI's `test_swc-workload_status.py`.
- **No production-code changes.** Phase A discipline observed —
  `swc_workload_mcp/` is untouched in this pass.

### Phase A counts

- Source scenarios in catalogue: **77** (39 authoring + 31 io + 2
  find_by_ref + 5 status)
- Ported and run: **77** (each catalogue entry materialised as a
  test; 7 carry an explicit `pytest.skip(reason=...)`)
- Effective ported (run + assert): **70**
- Passing: **70**
- Failing: **0**
- Intentionally skipped: **7**

### Failing tests

**None.**

### Intentionally skipped (with reasons)

Per `solution.md` — explicit `pytest.skip` with reason, surfaced in
the report rather than silently dropped:

- `test_tools_integration_authoring.py::test_add_rejects_extra_positional_after_target`
  — MCP `add` signature `(workload, title, placement, ref)` has no
  way to pass a fifth positional; argparse-rejection contract is
  covered by `test_add_rejects_unknown_placement_keyword`.
- `test_tools_integration_io.py::test_list_renders_full_tree_with_symbols`
  — text rendering (✔/▣ glyphs) unreachable through MCP; bridge
  always passes `--json`. Structural status verification covered
  elsewhere.
- `test_tools_integration_io.py::test_list_without_json_is_text` —
  text-output form unreachable through MCP.
- `test_tools_integration_io.py::test_text_output_includes_hash_next_to_title`
  — same as above.
- `test_tools_integration_io.py::test_exists_json_form_true` —
  JSON-form variant collapses with
  `test_exists_true_when_workload_json_present` since the bridge
  always passes `--json`.
- `test_tools_integration_io.py::test_exists_json_form_false` —
  same collapse with
  `test_exists_false_when_folder_exists_but_no_workload_json`.
- `test_tools_integration_io.py::test_oserror_in_save_workload_surfaces_as_friendly_error`
  — OSError simulation requires invasive setup (read-only FS /
  monkeypatched subprocess); CLIExecutionError → ToolError
  round-trip is exercised by every other error-path test in this
  file.

Note on `test_parent_marked_done_with_undone_children_warns_on_stderr`
— flagged in the catalogue as "investigate during port". The agent
ported it and it **passes** as a structural assertion (operation
succeeds, file rewritten, parent status flips to done). The
stderr-warning portion is dropped through the bridge on exit-0
paths; the test's docstring documents this as a future tool-layer
enhancement (a structured warnings array on the JSON payload could
surface CLI stderr to MCP clients).

### Test results — full suite regression check

`.venv/bin/pytest` → **127 passed, 7 skipped, 0 failed** in 13.81s.
Existing 57 tests from 2.1 / 2.3 / 2.4 unchanged (9 bridge + 38
tools + 10 server). No regressions.

```
tests/mcp/test_bridge.py ......... (9)
tests/mcp/test_server.py .......... (10)
tests/mcp/test_tools.py ...................................... (38)
tests/mcp/test_tools_integration_authoring.py ...s.................................... (38 passed, 1 skipped)
tests/mcp/test_tools_integration_io.py .....s.......ss.............sss.. (28 passed, 5 skipped)
tests/mcp/test_tools_integration_status.py ..... (5)
======================= 127 passed, 7 skipped in 13.81s ========================
```

### Pipeline

- **Build (`.venv/bin/pytest`):** green; 127 passed, 7 skipped, 0
  failed.
- **Dev environment:** unchanged; 2.4's `python -m swc_workload_mcp`
  entry point remains the same (no production-code changes this
  pass).

### Build confidence

High for the Phase A deliverable. Every applicable source scenario
has an equivalent MCP test; the suite runs end-to-end via the
in-memory client against the real `swc-workload` subprocess; pass /
fail / skip counts are explicit and traceable to source CLI test
names. The 7 skipped scenarios are flagged with reasons in the
report rather than silently dropped.

### Surprising finding

**The demo bug does not reproduce through the tool layer.**
`test_add_as_child_of_parent` is the structural mirror of the demo
report (`init` → `add "one"` → `add "two"` → `add "sub item" to 2`
expecting a `2.1` child) and it **passes**. If the demo bug exists,
it sits outside our tool layer — most likely the MCP Inspector's
wire format / user-input handling / something at the protocol-input
side that converts the operator's form-field values into the JSON
`arguments` payload differently than expected.

This means Phase B may have nothing to fix from 3.2's lens. The
user gate should reflect that: either close 3.2 with Phase B skipped
(no failures to address), or open a separate investigation work
item to characterise the demo discrepancy at the Inspector / wire
layer.

### Scope flags for reviewer

- No `summary.md` write was performed by the agent — the harness
  blocked it. Orchestrator transcribed the agent's final report
  into this file and re-verified test counts via `.venv/bin/pytest`
  before recording. Same recovery pattern as 2.3.
- Fixture shape ended up as a 4-tuple `(call_tool, workload_folder,
  workload_json, seed)` rather than the 3-tuple sketched in
  `solution.md`. Small ergonomic adjustment — folding `seed` into
  the yielded tuple keeps deliberate-seed tests tidy. No course
  change.

### Approach needs revisiting

No. Bulk-port + run + report worked as designed. Phase A is
complete and ready for the user gate.

---

## Pass 2 — review feedback: real-stdio transport — 2026-05-26

### Changes

- **`tests/mcp/conftest.py`** — swapped the in-memory client/server
  harness for a real-stdio session. `_mcp_session` is now a
  session-scoped async fixture that spawns one `python -m
  swc_workload_mcp` subprocess via
  `mcp.client.stdio.stdio_client(StdioServerParameters(...))`, runs the
  MCP handshake, and yields the connected `ClientSession`. `mcpw`
  became sync (just composes the per-test paths with the shared
  session); `mcpw_ready` stays async (awaits `init`). `anyio_backend`
  promoted to session scope so the session-scoped async fixture can
  live across tests. `SWC_WORKLOAD_BIN` moved from per-test
  `monkeypatch.setenv` to `StdioServerParameters.env`. Same per-test
  workload isolation via `tmp_path`.
- **No test-body changes.** All 77 ported scenarios run unchanged
  against the new transport.

### Why

The Phase A in-memory harness bypasses real stdio framing. The
suite as built proved the layers from `tools.py` down to
`workload.json` are correct, but said nothing about the stdio
transport that real MCP clients actually use. Per `feedback.md`,
swap to the production-shape transport so the suite's "all green"
result is definitive rather than suggestive.

### Test results

- Suite re-run against real stdio: **70 passed, 7 skipped, 0 failed**
  (identical breadth to Pass 1).
- Full suite: **127 passed, 7 skipped, 0 failed in 14.52s.** No
  regressions in the 57 baseline tests. Runtime added ~0.7s for the
  one subprocess spawn + handshake amortised across 70 tests.
- The demo-bug-mirror test (`test_add_as_child_of_parent`) still
  passes through real stdio. The bug — if it exists — is now
  confirmed not in our tool layer AND not in stdio framing.

### Demo investigation outcome (live, via MCP Inspector)

After the stdio swap landed, the user walked through every tool via
MCP Inspector against the running server. 11 of 12 worked first
time. The `add` tool produced the demo discrepancy:
`add(placement="to", ref="<hash>")` from Inspector's form view
landed at top level instead of as a child.

Root cause: Inspector's form serialiser sends nullable string
optionals as `null` even when the form field has a value. The
request JSON Inspector sent for the user's `add` call was
`{workload, title, placement: null, ref: null}` — both optional
kwargs nulled out despite the form showing `"to"` and the hash.

This exposed a vulnerability in `tools.add`: the original code
nested `if ref is not None` inside `if placement is not None`, so
when Inspector sent `placement=null, ref=set`, the tool **silently
dropped `ref`** and produced a valid-but-wrong top-level-add argv.
The CLI then succeeded. No error surfaced.

**Workaround for the Inspector bug:** the user switched to
Inspector's raw-JSON input mode (the "format json" button) and
typed the arguments directly — that bypassed the form serialiser
and the call worked as expected. All 12 tools confirmed user-
accepted after that workaround.

### Pass 2 fix — tool de-nesting (Phase B inside 3.2)

The Inspector issue is upstream, but the tool layer's silent
absorption of the invalid kwargs combination is a real defect
regardless. Resolved here rather than deferred:

- **`swc_workload_mcp/tools.py::add`** — de-nested the `ref` check
  so `ref` is always forwarded when set, even if `placement` is
  `None`. The CLI already has the right error
  (`"expected 'to <parent>' or 'at <position>' after title; got 'X'"`,
  exit 1); our tool was preventing the CLI from ever seeing the
  malformed argv. After this change, `tools.add(workload, title,
  ref="1")` (no placement) round-trips the CLI's actionable
  rejection as a `ToolError`.
- **`tests/mcp/test_tools.py::test_add_tool_forwards_ref_even_when_placement_is_missing`**
  (NEW) — unit test pinning the argv shape (`ref` reaches the
  bridge even when `placement` is None).
- **`tests/mcp/test_tools_integration_authoring.py::test_add_ref_without_placement_surfaces_cli_rejection`**
  (NEW) — integration test asserting the round-trip: bad kwargs
  combo → `ToolError` with the CLI's actionable message → workload
  state matches (no orphan added).

This closes the schema-impedance gap noted during the investigation:
the CLI's positional argv can't represent "ref without placement"
(so the CLI suite has no equivalent to mirror), but the MCP layer
can — hence the MCP-only test was needed.

### Test results after Pass 2 fix

- Full suite: **129 passed, 7 skipped, 0 failed in 15.13s.** Two
  new tests added (127 → 129). No regressions.

### Tool acceptance status (live demo via Inspector)

All 12 tools user-accepted end-to-end:

| Tool       | Status              | Notes |
| ---------- | ------------------- | ----- |
| `init`     | ✅ user-accepted | |
| `exists`   | ✅ user-accepted | |
| `list`     | ✅ user-accepted | |
| `find`     | ✅ user-accepted | |
| `summary`  | ✅ user-accepted | |
| `add`      | ✅ user-accepted | Inspector form serialiser nulls out optional kwargs; raw-JSON entry works correctly. Tool fix in Pass 2 makes the misuse surface as a clean `ToolError`. |
| `rename`   | ✅ user-accepted | Works with both numbered paths and hash IDs through MCP and CLI; original "fails with hash ID" report was an input-handling issue at the Inspector layer, not our tool. |
| `delete`   | ✅ user-accepted | |
| `reset`    | ✅ user-accepted | |
| `start`    | ✅ user-accepted | |
| `complete` | ✅ user-accepted | |
| `move`     | ✅ user-accepted | |

### Pipeline

- **Build (`.venv/bin/pytest`):** green; 129 passed, 7 skipped, 0
  failed.
- **Dev environment:** `python -m swc_workload_mcp` runs the
  production-shape server (verified via the live Inspector demo).

### Build confidence

High. The integration suite now drives a real server subprocess
over real stdio — production parity. The demo-driven walkthrough
of every tool through MCP Inspector confirmed the end-to-end chain
works against a real MCP client. The `add` tool-layer
silent-drop defect was found and fixed within this work item, with
both a unit test and an integration test guarding against
regression.

### Scope flags for reviewer

- Pass 2 expanded scope slightly beyond Phase A's "tests only"
  framing — the `tools.add` de-nesting is a production-code change.
  Justified because the defect was surfaced by the live demo, the
  fix is one line, and the integration coverage to prove it now
  exists. The alternative (open a 2.5 follow-up item) was discussed
  and explicitly declined in favour of folding the fix into 3.2.
- `summary.md` Pass 2 was written by the orchestrator directly
  (not by an implementation agent's writer) — informal in-flow
  surgery once the workflow was past its formal refine/review
  stages.

### Approach needs revisiting

No. Real-stdio swap landed cleanly; demo-driven acceptance of all
12 tools passed; the surfaced defect was fixed with regression
coverage in both unit and integration tiers.
