# Specs — 3.2: Tool-level tests — each tool exercised against a temp workload

## Users and Personas

Technical actors only (no human end-users for an integration test
suite):

- **Test runner** (pytest) — executes the MCP integration suite,
  exits 0 if all tests pass.
- **Test harness fixture** — encapsulates the in-memory MCP
  client/server session (mirroring the CLI suite's `swcw` /
  `swcw_ready` fixtures) so each test can issue tool calls without
  re-implementing the FastMCP setup. Precondition: `swc-workload`
  CLI installed and on PATH (or `SWC_WORKLOAD_BIN` pointing at it).
- **Implementation agent** (Phase A and Phase B) — reads the CLI
  test files, ports each scenario into an MCP equivalent, then later
  fixes whichever failures the user approves.
- **Developer/operator** (you) — reviews the Phase A failure report
  and decides which failures Phase B addresses.

## User Journeys

### Phase A — build & report (one implementation pass, no production-code changes)

1. Implementation agent reads each CLI test file under
   `tests/bin/test_swc-workload_authoring.py`,
   `test_swc-workload_io.py`, `test_swc-workload_status.py`, plus
   the top-level `test_find_by_ref.py`.
2. For each test in those files, the agent writes an equivalent
   MCP-driven test that asserts the same observable outcomes
   (returned data, workload.json state, error messages) — but
   reaches the system under test via the in-memory MCP client
   calling our tools, not by spawning `python -m swc_workload` as
   a subprocess.
3. Tests are organised in new files matching the CLI's layout:
   `tests/mcp/test_tools_integration_authoring.py`,
   `tests/mcp/test_tools_integration_io.py`,
   `tests/mcp/test_tools_integration_status.py`. The `find_by_ref`
   pair lands in `_io.py` (logical fit).
4. A shared `tests/mcp/_integration.py` (or `conftest.py`) module
   holds the MCP equivalent of the CLI's `swcw` / `swcw_ready`
   fixtures.
5. Agent runs the suite once at the end (no per-scenario green-
   before-next). Reports total / passing / failing counts, and a
   list of failing test names with their assertion summaries.
6. Implementation agent stops without fixing anything in production
   code. Pass summary returned to the orchestrator.

### User gate (between Phase A and Phase B)

1. Orchestrator presents the failure list to the user.
2. User selects which failures to address in Phase B (per-test, or
   "all", or "none — accept as known issues"). Failures not
   selected may be filed as tech debt (with reason) or surfaced as
   follow-up work items.

### Phase B — fix (one or more implementation passes, gated)

1. Fresh implementation agent receives the approved failure list as
   its brief (mirrors the `workflowDeliver_refine` pass-N pattern).
2. Agent diagnoses each failure, makes the smallest production-code
   change that turns it green (most likely in `tools.py`; possibly
   `bridge.py` or `server.py`), and re-runs the full suite.
3. Agent reports new pass/fail counts. If any approved failures
   remain (or fixes introduced regressions), the orchestrator gates
   with the user again.

### Test failure surfaces the demo bug

1. The CLI test `test_add_as_child_of_parent` asserts that
   `add "sub item" to "2"` produces a child item at number `2.1`
   under the second top-level item.
2. The MCP-equivalent test runs the same scenario through the tool
   layer — `init`, then `add("one")`, `add("two")`, then
   `add(title="sub item", placement="to", ref="2")`, then `list`
   and assert the returned tree has the expected child structure.
3. If the demo report is accurate, this test fails. Phase B fixes
   it. If the test *passes* unexpectedly, that's still useful — it
   means the bug is elsewhere (Inspector wire format, the user's
   specific input, etc.) and we investigate.

## Requirements

**REQ-01** (event-driven) — WHEN the implementation agent ports a
behavioural CLI test scenario, it SHALL produce a corresponding MCP
test that asserts the same observable outcomes (returned data,
workload.json on-disk state, error message content) using the
in-memory MCP client harness.

**REQ-02** (event-driven) — WHEN the Phase A pass completes, the
agent SHALL produce a pass/fail summary that includes: total ported
test count, passing count, failing count, and a per-failure summary
(test name + assertion that failed).

**REQ-03** (ubiquitous) — Every test SHALL use a fresh `tmp_path`
workload folder. Tests SHALL NOT share workload state. The shared
fixture handles cleanup automatically (pytest's `tmp_path`).

**REQ-04** (ubiquitous) — The fixture for MCP-equivalent
`swcw_ready` SHALL initialise the temp workload via the `init` tool
(the same way the CLI fixture invokes the CLI's `init`). It SHALL
NOT seed `workload.json` directly except in scenarios that
specifically exercise the file-load path (e.g. malformed-shape
tests), and in those cases the seeding mechanism SHALL be a
deliberate test-helper.

**REQ-05** (ubiquitous) — Tests SHALL use the public MCP tool API
exclusively. No reaching into `tools.TOOLS` callables to bypass the
MCP layer; no monkeypatching the bridge. The composed wiring is
what's under test.

**REQ-06** (event-driven) — WHEN a test would invoke a non-existent
tool or pass invalid kwargs, the underlying SDK SHALL surface the
schema-rejection or `ToolError` to the test; the test SHALL assert
on that surface (not on internal exception types).

**REQ-07** (unwanted behaviour) — IF the `swc-workload` CLI is not
installed at test time, THEN the test suite SHALL fail loudly (same
posture as 2.4 REQ-09). No silent `pytest.skip`.

**REQ-08** (ubiquitous) — Each ported test's name SHOULD echo the
source CLI test name closely so traceability between the two suites
is obvious (e.g. CLI `test_add_as_child_of_parent` → MCP
`test_add_as_child_of_parent`). Exact-match isn't required when
disambiguation is needed (e.g. if the same name appears in two CLI
files); a clear cross-reference comment in the test docstring
substitutes.

**REQ-09** (ubiquitous) — Argparse-level CLI rejections (e.g.
`test_add_rejects_extra_positional_after_target`,
`test_move_rejects_unknown_second_token`) SHALL be mirrored as MCP
tests that pass the equivalent shape through the tool and assert a
`ToolError` is raised carrying the CLI's stderr message. The
*mechanism* is different (argparse vs. CLIExecutionError
round-trip), but the *contract* — invalid input rejected with a
useful message — is the same.

**REQ-10** (event-driven) — WHEN Phase B receives a fix brief, it
SHALL address only the listed failures (no broader refactors) and
re-run the full suite to confirm no regressions were introduced.

## Acceptance Scenarios

```gherkin
# REQ-01 — pattern: happy path through MCP matches CLI assertion
Scenario: add as child of parent (mirroring CLI test_add_as_child_of_parent)
  Given the MCP client/server session is connected
  And a temp workload has been initialised via the init tool
  And add("one") and add("two") have been called
  When add(title="sub item", placement="to", ref="2") is invoked
  Then the call returns a ToolResult with the new item's payload
  And calling list with the same workload returns a tree where
    items[1].children[0].title == "sub item"
    and items[1].children[0].number == "2.1"

# REQ-01 — pattern: error round-trip via ToolError
Scenario: add rejects duplicate sibling title (mirroring CLI test_add_rejects_duplicate_sibling_title)
  Given the MCP client/server session is connected
  And a temp workload has been initialised
  And add("first") has been called at the top level
  When add(title="first") is invoked again at the top level
  Then the call surfaces a ToolError (not a successful response)
  And the error message contains "collide" or "first"

# REQ-02 — Phase A reporting
Scenario: Phase A summary on a clean port
  Given all 77 source scenarios have been ported and the suite has run
  When the agent finishes its pass
  Then the summary states the total count (77 expected if no scenarios
    are skipped), the passing count, and the failing count
  And the summary includes one line per failing test with the
    asserting line or message

# REQ-03 — fixture isolation
Scenario: two tests do not share workload state
  Given test A creates a workload and adds an item
  When test B runs immediately after
  Then test B's tmp_path is a different folder
  And test B's tool calls see an empty/new workload (or fail until init)

# REQ-04 — fixture initialisation matches CLI swcw_ready
Scenario: swcw_ready-equivalent initialises via the init tool
  When the fixture is requested
  Then the fixture's setup calls the init tool (not direct json.dump
    or any other shortcut)
  And the fixture yields a context that can call further tools
    against the same workload

# REQ-05 — public API only
Scenario: tests do not import or call tools.TOOLS directly
  When the integration test file source is inspected
  Then no test imports `swc_workload_mcp.tools` to invoke a callable
    directly
  And all tool calls go through the in-memory MCP ClientSession

# REQ-06 — invalid kwargs surface via the SDK
Scenario: missing required kwarg surfaces a schema error
  When add is called without a required kwarg (e.g. title omitted)
  Then the test observes a schema-validation error from the SDK
  And does not get a CLIExecutionError (the call should never reach
    the bridge)

# REQ-07 — fail loudly on missing CLI
Scenario: integration suite refuses to silently skip
  Given swc-workload is not installed (binary not on PATH, no env var)
  When the integration suite is run
  Then the suite fails with a clear message stating the CLI is
    required (do not pytest.skip)

# REQ-08 — naming traceability
Scenario: ported tests echo CLI names
  When the MCP test list is inspected
  Then for each source CLI test there is an MCP test with the same
    name (or a clearly cross-referenced equivalent if disambiguation
    requires a prefix)

# REQ-09 — argparse rejection round-trip
Scenario: invalid placement keyword surfaces a ToolError
  When add(title="x", placement="bogus", ref="1") is invoked
  Then a ToolError is raised
  And its message includes the CLI's argparse rejection text

# REQ-10 — Phase B scope discipline
Scenario: Phase B touches only what the brief calls out
  Given Phase B receives a brief listing failing tests F1, F2
  When the agent finishes its pass
  Then production-code changes are limited to what is necessary to
    turn F1 and F2 green
  And the full suite is re-run with no new failures introduced
```

## Validation Rules

Not applicable in the conventional sense — this work item produces
tests, not new validation logic. The behavioural validation rules
under test are the CLI's own, exercised by each ported scenario
(e.g. `add` rejects dotted-number-prefix titles, `move` rejects
cycles).

## CLI scenario catalogue

The implementation agent SHALL produce one MCP-equivalent test per
source scenario listed below. Source: `swc-workload-cli` repo,
`tests/bin/` plus `tests/test_find_by_ref.py`.

### Authoring (39 scenarios) → `tests/mcp/test_tools_integration_authoring.py`

From `tests/bin/test_swc-workload_authoring.py`:

- `test_add_appends_top_level_item_with_hash_id`
- `test_add_assigns_unique_hashes_when_titles_collide_across_parents`
- `test_add_rejects_dotted_number_prefix_title`
- `test_add_accepts_leading_digits_without_dot`
- `test_add_as_child_of_parent` *(the demo-bug-relevant scenario)*
- `test_add_rejects_duplicate_sibling_title`
- `test_add_rejects_case_variant_duplicate_sibling_title`
- `test_add_allows_same_title_under_different_parent`
- `test_add_at_top_level_position_shifts_siblings_down`
- `test_add_at_nested_position_uses_parent_from_target`
- `test_add_at_out_of_range_caps_at_end`
- `test_add_collision_uses_siblings_at_target_slot`
- `test_add_collision_is_case_insensitive_at_target_slot`
- `test_add_at_rejects_missing_target_parent`
- `test_add_rejects_extra_positional_after_target` *(REQ-09 argparse round-trip)*
- `test_add_to_requires_target` *(REQ-09)*
- `test_add_at_requires_target` *(REQ-09)*
- `test_add_rejects_unknown_placement_keyword` *(REQ-09)*
- `test_add_at_rejects_non_numeric_target`
- `test_delete_drops_item_and_descendants_with_renumber`
- `test_rename_preserves_id_status_position`
- `test_rename_rejects_dotted_number_prefix`
- `test_rename_rejects_duplicate_sibling_title`
- `test_rename_allows_no_op_self_rename`
- `test_rename_allows_case_change_of_own_title`
- `test_rename_allows_same_title_as_non_sibling`
- `test_move_up_preserves_ids`
- `test_move_top_moves_to_first_slot`
- `test_move_direction_rejects_unexpected_target` *(REQ-09)*
- `test_move_reparents_and_reflows_both_sides`
- `test_move_rejects_cycle`
- `test_move_rejects_missing_target_parent`
- `test_move_rejects_unknown_second_token` *(REQ-09)*
- `test_move_to_requires_target` *(REQ-09)*
- `test_move_target_without_to_errors` *(REQ-09)*
- `test_move_to_target_works`
- `test_move_leaves_orphaned_parent_status_untouched`
- `test_move_same_parent_source_after_target_lands_at_requested_position`
- `test_move_same_parent_source_before_target_lands_at_requested_position`

### I/O (31 scenarios) → `tests/mcp/test_tools_integration_io.py`

From `tests/bin/test_swc-workload_io.py`:

- `test_find_returns_all_matches`
- `test_find_single_match`
- `test_resolve_by_number`
- `test_resolve_by_hash_id`
- `test_reference_not_found`
- `test_list_renders_full_tree_with_symbols`
- `test_list_filter_status_in_progress`
- `test_list_exclude_status_done`
- `test_list_with_ref_renders_item_with_children`
- `test_list_with_ref_and_filter_scopes_to_subtree`
- `test_summary_partial`
- `test_summary_text_includes_wip`
- `test_list_json_is_parseable_tree`
- `test_list_without_json_is_text` *(may not be applicable —
  bridge always passes `--json`; agent confirms or adapts.)*
- `test_text_output_includes_hash_next_to_title` *(same caveat as
  above — text output may not surface through the MCP layer.)*
- `test_load_workload_rejects_malformed_shape` *(requires
  pre-seeded workload.json; uses REQ-04's deliberate seeding helper.)*
- `test_load_workload_rejects_top_level_non_dict` *(same)*
- `test_load_workload_json_decode_error_reports_line_and_column` *(same)*
- `test_init_creates_workload_json_inside_supplied_folder`
- `test_init_refuses_to_overwrite_existing_file`
- `test_op_on_missing_workload_recommends_init`
- `test_workload_folder_does_not_exist_errors_clearly`
- `test_workload_pointed_at_a_file_errors_clearly`
- `test_init_requires_folder_to_exist`
- `test_exists_false_when_folder_is_missing`
- `test_exists_false_when_path_is_a_file`
- `test_exists_false_when_folder_exists_but_no_workload_json`
- `test_exists_true_when_workload_json_present`
- `test_exists_json_form_true` *(may collapse with `exists_true`
  above since bridge always passes `--json` — agent confirms.)*
- `test_exists_json_form_false` *(same caveat)*
- `test_oserror_in_save_workload_surfaces_as_friendly_error`
  *(may require monkeypatching the CLI or read-only filesystem —
  if not feasible without invasive setup, the agent flags this for
  the Phase A summary as "intentionally skipped, mechanism not
  reproducible via MCP layer" rather than silently dropping.)*

From `tests/test_find_by_ref.py`:

- `test_all_digit_hash_id_resolves_to_item_not_path`
- `test_numeric_path_still_resolves_when_no_id_matches`

### Status (5 scenarios) → `tests/mcp/test_tools_integration_status.py`

From `tests/bin/test_swc-workload_status.py`:

- `test_marking_child_in_progress_rolls_parent_to_in_progress`
- `test_marking_last_child_done_rolls_parent_to_done`
- `test_start_on_done_is_sticky_and_leaves_file_unchanged`
- `test_reset_on_done_re_opens_it`
- `test_parent_marked_done_with_undone_children_warns_on_stderr`
  *(stderr-warning content may not surface as a tool return value;
  agent investigates whether to assert on the tool result or skip
  with a flagged note.)*

### Total: 77 source scenarios

Some will collapse (e.g. JSON-form variants) or be flagged as
not-feasible-without-invasive-setup. The Phase A summary makes
those explicit so the user sees what landed vs. what was set aside.

## Notes on test scope

- **Phase A produces no production-code changes.** It writes test
  files and the fixture module only. The success criterion for
  Phase A is "every applicable CLI scenario has an equivalent MCP
  test; the suite runs end-to-end; pass/fail counts are reported".
- **Phase B's failure-driven loop is structurally identical to the
  refine-stage pass-N loop.** The orchestrator will reuse the same
  flow: present failures, user picks resolve/defer per failure,
  spawn an implementation agent with the approved list, re-run.
- **The demo bug (`add(placement="to", ref="1")`)** is implicitly
  covered by `test_add_as_child_of_parent`. If that test passes
  unexpectedly, we still learn something useful — the bug is
  somewhere else (Inspector wire format, user input quirks) and
  we investigate separately. Either way 3.2's deliverable is
  unchanged: comprehensive end-to-end coverage.
