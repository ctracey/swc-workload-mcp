# Code Review Findings — 3.2: Tool-level tests — each tool exercised against a temp workload — 2026-05-26

## Summary

Phase A is a clean, disciplined bulk port. The fixture design in
`conftest.py` is ergonomic and well-documented: the 4-tuple
`(call_tool, workload_folder, workload_json, seed)` reads naturally at
the call site, `mcpw` / `mcpw_ready` map cleanly onto the CLI suite's
`swcw` / `swcw_ready`, and the `ToolCallResult` dataclass gives tests
a CLI-like `.payload` / `.error` discrimination that mirrors the source
suite's `returncode == 0` / `stderr` pattern. Every applicable source
scenario is materialised as a test, every test carries a `Mirrors:`
docstring cross-reference, every test is `@pytest.mark.anyio`, and the
7 not-portable scenarios are flagged with `pytest.skip(reason=...)`
rather than silently dropped. REQ-05 (public API only) is observed —
no test imports `swc_workload_mcp.tools` or monkeypatches the bridge;
the only `monkeypatch.setenv` call is for `SWC_WORKLOAD_BIN`
configuration, matching the 2.4 REQ-09 posture. Phase A's discipline
constraint (no production-code changes) is observed. The two minor
observations below are about traceability strength of one ported test
and the fidelity of the all-digit-hash regression port — neither
blocks acceptance.

## Findings

### F-01 — info: `test_all_digit_hash_id_resolves_to_item_not_path` cannot deterministically reproduce the regression it mirrors

**Severity:** info
**Location:** `tests/mcp/test_tools_integration_io.py:610`
**Description:** The CLI version of this test crafts an item with an
all-digit hash ID in memory (the regression is path-resolution
incorrectly winning over id-resolution when the ID happens to be
all-digits). The MCP port has no way to craft a specific hash through
the public tool API — hashes come from the CLI's randomly-generated
7-char hex assignments, so an all-digit hash appears only ~3.7% of the
time. As written, the test passes whenever the assigned hash contains
any non-digit character (which is the overwhelming majority of runs),
without ever exercising the contended path. The agent acknowledges
this in the docstring; the test still has value as a list-by-id round
trip, but the title is slightly misleading.
**Suggestion:** No change required for Phase A. If the suite is later
hardened, consider either (a) seeding `workload.json` with a crafted
all-digit hash (extending the `seed` helper pattern), or (b) renaming
the MCP test to `test_list_by_hash_id_round_trip` and recording in the
docstring that the original CLI regression's strict variant lives in
the CLI's own suite.

### F-02 — info: `test_rename_rejects_dotted_number_prefix` does not assert on the error message

**Severity:** info
**Location:** `tests/mcp/test_tools_integration_authoring.py:408`
**Description:** Other rename/add validation ports in the same file
assert a substring of the CLI's rejection text on `result.error`
(e.g. `"collide" in msg`, `"number" in msg`). This test only checks
`result.error is not None` and then verifies the original title is
preserved. The structural assertion (title unchanged) is arguably
stronger than a substring check, but the inconsistency across the
file is worth a note — a regression that changed the error message to
something unhelpful (e.g. an empty string or stack trace) would still
pass this test as long as some error was raised.
**Suggestion:** Add a substring assertion on `result.error` consistent
with neighbouring tests, e.g. `assert "number" in result.error.lower()`.
Optional for Phase A.

### F-03 — info: `test_oserror_in_save_workload_surfaces_as_friendly_error` resolves `mcpw` despite skipping

**Severity:** info
**Location:** `tests/mcp/test_tools_integration_io.py:584`
**Description:** The function takes `mcpw` as a fixture even though
the first statement is `pytest.skip(...)`. Fixture resolution
(constructing the in-memory client session) happens before the skip
fires, so every run of this test pays the session-setup cost just to
immediately skip. The cost is small in absolute terms but easy to
avoid.
**Suggestion:** Drop the `mcpw` parameter (and the others in the same
boat — `test_list_renders_full_tree_with_symbols`,
`test_list_without_json_is_text`,
`test_text_output_includes_hash_next_to_title`,
`test_exists_json_form_true`, `test_exists_json_form_false`,
`test_add_rejects_extra_positional_after_target`). The skip-with-reason
discipline is preserved; only the unnecessary fixture wiring is
removed. Optional for Phase A.

### F-04 — info: `mcpw_ready` uses `return` rather than `yield`, relying on parent fixture for session teardown

**Severity:** info
**Location:** `tests/mcp/conftest.py:208`
**Description:** `mcpw_ready` is `async def` that `return`s the
4-tuple after calling `init`. It depends on `mcpw`, which is an async
generator fixture holding the `async with create_connected_...` block
open at its yield. Session teardown therefore happens when pytest
unwinds the parent `mcpw` fixture, not `mcpw_ready`. The pattern is
correct and works under pytest-anyio, but readers tracing fixture
lifetime have to follow the dependency chain to see where the session
closes. This is a minor readability nit, not a correctness issue.
**Suggestion:** Either leave as-is (the dependency chain works), or
restructure `mcpw_ready` as `async def ... yield ...` for symmetry
with `mcpw`. Not required.

## Verdict

**PASS**

Phase A's deliverable lands cleanly. The fixture is solid, port
fidelity is high, traceability is explicit, and the discipline
constraints (public API only, no production-code changes, no silent
skips) are observed. The findings above are info-level polish notes,
not gates on acceptance.
