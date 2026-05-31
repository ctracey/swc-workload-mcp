# Summary — 2.3: Define MCP tools

## Status

Complete — 47 pytest scenarios green (9 inherited from 2.1 + 38 new),
tools module shipped, per-op kwarg reference table populated against
CLI v1.1.2.

## Files created

- `swc_workload_mcp/tools.py` — 12 typed Python callables, one per CLI
  op (`init`, `exists`, `list`, `find`, `summary`, `add`, `rename`,
  `delete`, `reset`, `start`, `complete`, `move`), plus a `TOOLS`
  registry list for 2.4's server to iterate over.
- `tests/mcp/test_tools.py` — 38 unit tests covering all Gherkin
  scenarios (REQ-01 → REQ-07) plus per-op argv spot checks.

## Files modified

- `.swc/mcp/workitems/2.3/specs.md` — per-op kwarg reference table
  populated against CLI v1.1.2.
- `.swc/mcp/architecture.md` — folder structure block updated to list
  `tools.py` explicitly.

## Implementation

`tools.py` exposes 12 typed top-level functions plus a `TOOLS` list.
Each tool body assembles argv (positional args + `--flag value` pairs
for set optional kwargs via the `_flag` / `_bool_flag` helpers) and
returns `_invoke(op, args)`. The private `_invoke` helper centralises
the three-way `BridgeError` → `mcp.server.fastmcp.exceptions.ToolError`
mapping with the exact message content required by REQ-03 / REQ-04 /
REQ-05.

### Key design decisions

- **MCP error type:** `mcp.server.fastmcp.exceptions.ToolError` —
  verified present in the installed SDK; subclass of `FastMCPError`.
- **`add` shape:** `placement: str | None` + `ref: str | None` (two
  optional kwargs) — mirrors the CLI's three positional forms
  (`add <title>` / `add <title> to <ref>` / `add <title> at <ref>`).
  Validation that `placement in {"to","at"}` stays with the CLI.
- **`move` shape:** `direction: str` (required) + `target: str | None`
  (optional, required by the CLI when `direction="to"`).
- **`list` shape:** `no_ids` modelled as `bool | None` — truthy emits
  the bare `--no-ids` flag, matching argparse's `store_true` semantics.
- **`list` shadows the builtin:** intentional per solution.md pattern
  B. `_StrList = builtins.list[str]` alias used for internal type
  hints because `typing.get_type_hints` would otherwise resolve
  `list[str]` against the rebound name.
- **Argv ordering:** `--workload <wl>` first, then any other flags,
  then positionals last — matches the Gherkin scenario examples.

## Test strategy

Full TDD — one test per Gherkin scenario, bridge stubbed via
`monkeypatch.setattr(tools.bridge, "invoke", recorder)`. No FastMCP
instance stood up; each tool callable is imported and exercised
directly, validating REQ-08 (thin wrapper) and the unit-level test
boundary set by solution.md.

The 38 tests cover: 2 success/passthrough scenarios (REQ-01), 2
optional-flag scenarios (REQ-02), 3 error-mapping scenarios applied
across all tools (REQ-03 / REQ-04 / REQ-05), the 12-tool surface check
(REQ-06), the per-op kwarg signature check (REQ-07), plus per-op argv
spot checks for the non-trivial shapes (`add`'s three forms, `move`'s
two forms, `list`'s optional flags).

## Pipeline

- **Build (`.venv/bin/pytest`):** green. 47 passed (9 bridge tests
  from 2.1 + 38 new tool tests). No regressions.
- **Dev env start (`python -m swc_workload_mcp`):** not verified —
  `__main__.main` still raises `NotImplementedError` from work item
  1.2. FastMCP wiring + stdio transport is work item 2.4.
- **Acceptance manual smoke:** out of scope (work item 5).

## Build confidence

High. Every Gherkin scenario has an automated test; the tool surface
was derived directly from `swc-workload <op> --help` against CLI v1.1.2;
both non-trivial op shapes (`add`, `move`) have dedicated tests. The
`TOOLS` registry gives 2.4 a single iteration point with no per-op
knowledge needed at the server layer.

## Scope flags for reviewer

None. README rewrite (work item 4) and CI/docs polish remain outstanding
from the workload as a whole but are not introduced or affected by 2.3.

## Approach needs revisiting

No.

## Note on artifact recovery

The implementing agent's harness blocked its `summary.md` write call.
The agent's final report contained the full summary content, which was
transcribed into this file by the orchestrator at the close of the
implement stage. Test results were re-verified (`.venv/bin/pytest` →
47 passed) before recording. `context.md` was written by the agent
directly and is untouched.
