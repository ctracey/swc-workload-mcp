# Quality Baseline — 2.3: Define MCP tools

## Commands run

- `.venv/bin/pytest` — pass: 9 tests passed (existing bridge suite from
  work item 2.1, no regressions).
- `.venv/bin/python -c "import mcp; from mcp.server.fastmcp import
  FastMCP"` — pass: the `mcp` SDK and `FastMCP` are importable in the
  local venv. The agent can rely on `mcp.server.fastmcp.FastMCP` and any
  related symbols when verifying which exception type to use for tool
  errors (see solution.md → MCP error type note).
- `which swc-workload && swc-workload --version` — pass: CLI present at
  `/Users/tracer/.local/bin/swc-workload` (version `1.1.2`). The agent
  can derive each tool's kwargs by running `swc-workload <op> --help`
  per REQ-07.

## Findings

All checks passed. No pre-existing failures.

## Decisions

No decisions required — clean baseline.
