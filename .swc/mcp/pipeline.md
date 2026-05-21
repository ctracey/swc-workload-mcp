# Pipeline

## Build

**Command:** `pytest`
**Expected outcome:** exit code 0; all existing CLI subprocess tests pass and
all new MCP wrapper tests pass. No skipped tests outside of those explicitly
marked as manual / integration.

## Dev environment

**Start command:** `python -m swc_workload_mcp` (for ad-hoc inspection — the
server normally launches under an MCP client, not as a long-running dev
server).
**Health check:** Not applicable for an interactive dev workflow. The server
speaks MCP over stdio; verify it is running by connecting an MCP client and
listing tools.
**Stop command:** `ctrl-c`.

## Acceptance

1. `pytest` is green.
2. Manual smoke test against a real MCP client:
   - Register the server in the client per the README instructions.
   - Confirm the `swc-workload` server appears and lists the expected tools.
   - Call `init` against a fresh folder, then `add`, then `list`, and confirm
     the resulting `workload.json` matches what the CLI would produce.
   - Trigger an error case (e.g. `delete` on a non-existent ref) and confirm
     the CLI error surfaces as an MCP tool error with a useful message.

The manual smoke test is called out as a deliberate non-automated step —
end-to-end protocol verification against a live MCP client is in-scope for
acceptance but out of scope for the automated test suite.
