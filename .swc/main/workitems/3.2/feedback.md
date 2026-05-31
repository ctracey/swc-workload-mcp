# Feedback — 3.2: Tool-level tests — each tool exercised against a temp workload

The integration test suite as built (Phase A) drives our MCP server
via the SDK's **in-memory** client/server harness
(`mcp.shared.memory.create_connected_server_and_client_session`),
which bypasses the real stdio transport. For the suite to genuinely
answer "does the wired system work end-to-end the way an MCP client
experiences it", the tests must run against a **full,
production-shape MCP server** — spawned as a subprocess over real
stdio (`mcp.client.stdio.stdio_client(StdioServerParameters(...))`).

Specifically:

- **One server subprocess per pytest session** (session-scoped
  fixture), driven by a `ClientSession` over real stdio. Adds one
  process spawn for the whole suite — runtime impact negligible.
- **Per-test workload isolation stays via `tmp_path`** — each test
  gets a fresh folder; no shared workload folder.
- **Same 77-scenario coverage breadth.** Existing test bodies should
  port as-is — the change is to `conftest.py`'s fixture only.
- **Catches stdio framing / transport-layer bugs** that the in-memory
  harness can't surface, and gives confidence the failing-demo
  investigation has truly ruled out our code (the in-memory result is
  suggestive but not definitive).
