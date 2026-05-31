# Code Review Findings — 2.3: Define MCP tools — 2026-05-25

## Summary

The implementation is clean, focused, and faithful to the brief. `tools.py`
delivers the 12 typed callables, a `TOOLS` registry, and centralised
error-mapping via `_invoke` — exactly the shape solution.md committed to
(pattern B). The thin-wrapper invariant (REQ-08) is preserved: each tool
body is argv assembly plus a single `_invoke(op, args)` call, with no
op-specific conditionals beyond what kwarg→argv translation demands.
All Gherkin scenarios are covered by the 38 unit tests, which pass
green alongside the inherited 2.1 bridge tests. The argv shapes for
the trickier ops (`add`'s three forms, `move`'s two forms, `list`'s
flag/positional mix) are spot-checked. Docstrings are agent-friendly
one-liners derived from CLI help. The per-op kwarg reference table in
specs.md is populated against CLI v1.1.2.

Findings below are minor observations, not defects. Nothing blocks
shipping.

## Findings

### F-01 — info: REQ-04 message strips stderr — acceptable but worth noting

**Severity:** info
**Location:** `swc_workload_mcp/tools.py:79-81`
**Description:** `_invoke` calls `exc.stderr.strip()` before formatting
the `CLIExecutionError` ToolError message. The spec scenario only
requires the stderr text to be contained in the message ("no such ref:
9.9"), so stripping is harmless and improves readability. Worth
recording so future readers know the choice was deliberate — if a CLI
op ever produces stderr where leading/trailing whitespace is
semantically meaningful (unlikely), this would erase it.
**Suggestion:** No change required. Optionally add a one-line comment
on the `.strip()` call documenting intent ("trim trailing newline from
CLI stderr — content is preserved").

### F-02 — info: `_invoke` ToolError messages add op name and searched-paths context

**Severity:** info
**Location:** `swc_workload_mcp/tools.py:74-87`
**Description:** The ToolError messages are richer than the bare
templates in requirements.md's "Approach direction":
- `CLINotFoundError` → includes the searched paths in parentheses.
- `CLIExecutionError` → prefixes with `swc-workload {op} failed` rather
  than just `swc-workload op failed`.
The acceptance scenarios (REQ-03/04/05) only require specific
substrings, all of which are present. The richer messages are more
actionable for the agent — a positive, not a deviation. Noted so the
reviewer is aware the strings are not byte-identical to the "Approach
direction" prose.
**Suggestion:** None.

### F-03 — info: `add` allows `placement` without `ref` — passes through to CLI for validation

**Severity:** info
**Location:** `swc_workload_mcp/tools.py:182-187`
**Description:** When `placement` is set but `ref` is omitted, the tool
appends only `placement` to argv (e.g. `["--workload", "/tmp/wl",
"Foo", "to"]`), leaving the CLI to reject the malformed invocation.
This is the documented design ("validation stays with the CLI" — per
context.md decision and REQ-08). The agent client will see a
`CLIExecutionError`-mapped ToolError with the CLI's own error message.
Acceptable; flagged only so the choice is visible in review.
**Suggestion:** None. If the team later wants client-side schema
enforcement, that would belong in a follow-up beyond REQ-08's scope.

### F-04 — info: `list`'s argv places optional `ref` positional after flags

**Severity:** info
**Location:** `swc_workload_mcp/tools.py:147-153`
**Description:** When `list` is invoked with `ref` plus optional flags,
argv ends up as e.g. `["--workload", "/tmp/wl", "--filter", "...",
"--no-ids", "2.3"]`. argparse on the CLI side accepts positionals
either before or after flags, so this works correctly and is covered
by `test_list_tool_with_all_optional_kwargs`. The summary.md's "argv
ordering" decision documents this intent explicitly. No action.
**Suggestion:** None.

## Verdict

**PASS**

All requirements met, all scenarios green, code is clean and matches
the solution design. The three observations above are informational
only.
