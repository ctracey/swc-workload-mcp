# Code Review Findings — 2.4: Wire tools into the FastMCP server with stdio transport — 2026-05-25

## Summary

The implementation is clean, focused, and faithful to the brief. `server.py` is small (~76 lines), exposes a single module-level `FastMCP` instance, registers tools by iterating `tools.TOOLS` (no per-op knowledge), and runs a fail-fast CLI presence check before entering stdio. The `_resolve_binary` → public `resolve_binary` promotion on the bridge is a minimal, well-justified change that satisfies REQ-07. `__main__.py` is a true thin delegator. Test coverage maps one-to-one to the Gherkin scenarios in `specs.md`, and REQ-09 is exercised against the real CLI via the SDK's in-memory client harness. Doc updates (`.swc/mcp/architecture.md`, `.swc/mcp/notes.md`, new `docs/architecture.md`) match the new fail-fast behaviour. Findings below are minor: a couple of low-severity duplication / consistency observations and one note on tightness of an assertion in the happy-path test.

## Findings

### F-01 — info: actionable-message template is duplicated between `server.py` and `tools.py`

**Severity:** info
**Location:** `swc_workload_mcp/server.py:68-73` and `swc_workload_mcp/tools.py:73-77`
**Description:** The "swc-workload not found (searched: …). Install from <repo> or set SWC_WORKLOAD_BIN to the binary path." template is hand-written in two places — once in `server.main()` for the startup fail-fast path, and once in `tools._invoke()`'s `CLINotFoundError` branch. `CLI_REPO_URL` is also defined in both modules. If the wording (or URL, or env-var name) ever changes, both have to be edited in lockstep — the kind of drift that is silent until a user reads two slightly different messages from the same tool. Not a defect today (the strings match), but a small DRY violation that the bridge layer (which owns the resolution semantics) is the natural place to fix.
**Suggestion:** Consider promoting the message template (or a `CLINotFoundError.actionable_message()` helper, or a module-level constant + small formatter) to `bridge.py` so both call sites consume the same source. Alternatively, give `CLINotFoundError` a `__str__` that already includes the install hint, and have both call sites just print/raise from `str(exc)`. Defer if not worth touching now — flag as tech debt.

### F-02 — info: `_register_tools` runs at module import time, coupling import to FastMCP state

**Severity:** info
**Location:** `swc_workload_mcp/server.py:50`
**Description:** `_register_tools()` is invoked at module import, so importing `swc_workload_mcp.server` for any reason (including in tests that only want to inspect `mcp.name` or run static checks) materialises all 12 tool registrations. This is documented as a deliberate decision in `context.md` ("keeps `main()` minimal … lets unit tests inspect the registered tools without invoking `main()`"), and it does work. The trade-off is that import-time side effects make the module harder to use in isolated test contexts and slightly harder to reason about — there is no longer a single function where "the server is built." Acceptable given the simplicity, but worth noting as a constraint for future contributors.
**Suggestion:** No change required. If the module ever grows additional responsibilities (e.g. resource registration, lifecycle hooks), consider moving registration into `main()` (before the resolve_binary call) and exposing a small `build_server() -> FastMCP` factory for tests.

### F-03 — info: REQ-01 happy-path test uses `issubset` instead of equality

**Severity:** info
**Location:** `tests/mcp/test_server.py:94-96`
**Description:** The REQ-01 test asserts `expected.issubset(registered)` for the tool names, where `expected` is the set of function names in `tools.TOOLS`. This is permissive — if a future change accidentally registers extra tools (e.g. a duplicate or a leaked test helper), this test will not catch it. REQ-05's test (`test_exactly_twelve_tools_registered_with_flat_names`) does enforce equality and count, so the gap is already covered by another test. Still, the REQ-01 test reads as if it should assert exact wiring; `==` would be tighter and clearer.
**Suggestion:** Tighten to `assert registered == expected` in `test_main_constructs_fastmcp_registers_tools_and_runs_stdio`. Low priority — REQ-05's test catches the same regression.

### F-04 — info: REQ-03 static check excludes `"list"` — documented, but worth a positive guard

**Severity:** info
**Location:** `tests/mcp/test_server.py:172-206`
**Description:** The REQ-03 test scans `server.py` source for literal op-name strings (`"init"`, `"add"`, etc.). `"list"` is intentionally excluded — too generic, false-positives on docstrings. The exclusion is documented in `context.md` and inline. The mitigating positive check `assert "TOOLS" in src_no_doc` is reasonable but weak: any module that *mentions* the identifier `TOOLS` anywhere (e.g. in a docstring) passes, regardless of whether the registration actually loops over it. A stronger guard would assert that `tools.TOOLS` is iterated (e.g. `"for fn in tools.TOOLS" in src_no_doc` or a regex thereof).
**Suggestion:** Optional — tighten the positive check to look for the actual `for … in tools.TOOLS` loop pattern rather than just the token. Low priority; current check catches the obvious regression.

### F-05 — info: `CLINotFoundError.searched_paths` empty case is handled twice

**Severity:** info
**Location:** `swc_workload_mcp/bridge.py:50-54` and `swc_workload_mcp/server.py:68`
**Description:** `CLINotFoundError.__init__` already handles the empty-list case by formatting `<none>` into its message. `server.main()` re-implements the same formatting (`", ".join(exc.searched_paths) if exc.searched_paths else "<none>"`) to build its own message. Not a bug — the formatting is small — but it is a second place that knows about the `<none>` sentinel. If F-01's suggestion lands (move message to bridge), this disappears naturally.
**Suggestion:** Fold into F-01's resolution. No standalone action needed.

## Verdict

**WARN**

All findings are `info`-level — the implementation meets every requirement, tests are well-structured, and doc invariants (REQ-08) are honoured. The minor duplication noted in F-01 and F-05 is the only thing worth tracking as light tech debt.
