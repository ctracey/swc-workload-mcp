# Pipeline

## Build

**Command:** `make test`
**Expected outcome:** All three tiers green (unit, integration, e2e). Pytest exits 0; no failing or errored tests. Equivalent to `uv run pytest`.

Tier-specific runs (for iterative work):
- `make test-unit` — `tests/mcp/unit`
- `make test-integration` — `tests/mcp/integration`
- `make test-e2e` — `tests/mcp/e2e`

## Dev environment

**Start command:** `make dev` — launches MCP Inspector against the local server (`npx @modelcontextprotocol/inspector uv run swc-workload-mcp`)
**Health check:** Inspector UI loads in browser; tool list shows registered tools.
**Stop command:** `ctrl-c`

## Acceptance

All tests green. The MCP is a thin wrapper layer with no end-user UI — there is no human-eyeball acceptance beyond test suite + Inspector spot-check that new tools register and round-trip a call.
