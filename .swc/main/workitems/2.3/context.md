## Pass 1 — 2026-05-25

- **Decision:** MCP error type is `mcp.server.fastmcp.exceptions.ToolError`.
  FastMCP exposes it explicitly as the tool-error vehicle (subclass of
  `FastMCPError`). Satisfies the solution-design note "agent verifies
  against SDK".
- **Decision:** `add` CLI form (`add <title> [to|at] [ref]`) is mirrored
  as two optional kwargs (`placement`, `ref`) rather than a single
  composite. Lets MCP clients see distinct schema knobs without the
  tool body needing op-specific conditionals beyond "if placement set,
  append it; if ref also set, append it" — still within REQ-08 ("no
  op-specific conditionals beyond what is needed to translate kwargs
  to argv"). Validation that `placement in {"to","at"}` stays with the
  CLI.
- **Decision:** `move` CLI form (`move <ref> <direction|to> [target]`)
  is mirrored as `direction` (required) + `target` (optional). Same
  rationale as `add` — surface the CLI's positional shape directly
  rather than splitting into two MCP tools.
- **Decision:** `list`'s `no_ids` modelled as `bool | None`. A truthy
  value emits the bare flag `--no-ids`; `None` / `False` omits it.
  Matches argparse's `store_true` semantics on the CLI side.
- **Decision:** Tool functions live in a new
  `swc_workload_mcp/tools.py` exporting a `TOOLS` list, per solution
  pattern B. Keeps tools importable for unit tests without depending on
  FastMCP server bootstrapping (2.4).
- **Decision:** Shared `_invoke(op, args)` helper centralises the
  three-way exception mapping. Each tool body is one argv assembly
  followed by `return _invoke(op, args)`, satisfying REQ-08.
- **Decision:** `_StrList = builtins.list[str]` alias used for internal
  type hints because the module rebinds `list` to a tool function.
  `from __future__ import annotations` makes annotation evaluation lazy,
  so `typing.get_type_hints` (used by some MCP introspection paths)
  would otherwise resolve `list[str]` against the rebound name.
- **Decision:** Argv ordering is `--workload <wl>` first, then any
  other flags, then positional args last. Matches the Gherkin scenario
  examples in `specs.md` (`["--workload", "/tmp/wl", "Foo"]`) and works
  with argparse's order-flexibility on the CLI side.
- **Decision:** Tool docstrings derived from each op's CLI help text,
  trimmed to one-or-two-line agent-friendly summaries. These become
  the MCP tool descriptions visible to clients.
- Per-op kwarg reference table in `specs.md` populated against CLI
  version `1.1.2` (confirmed via `swc-workload --version`).
- Tests added at `tests/mcp/test_tools.py` — 38 tests covering all 7
  Gherkin scenarios plus per-op argv spot checks. Bridge stubbed via
  `monkeypatch.setattr(tools.bridge, "invoke", recorder)`. Full suite
  (bridge + tools): 47 passed, no regressions.
