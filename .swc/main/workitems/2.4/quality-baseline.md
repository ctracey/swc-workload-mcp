# Quality Baseline — 2.4: Wire tools into the FastMCP server with stdio transport

## Commands run

- `.venv/bin/pytest` — pass: 47 tests passed (9 bridge tests from 2.1
  + 38 tool tests from 2.3, no regressions).
- `.venv/bin/python -c "import mcp; from mcp.server.fastmcp import
  FastMCP; from mcp.server.fastmcp.exceptions import ToolError"` —
  pass: `mcp` SDK, `FastMCP`, and `ToolError` all importable in the
  local venv.
- `which swc-workload && swc-workload --version` — pass: CLI present
  at `/Users/tracer/.local/bin/swc-workload` (v1.1.2). Required for
  REQ-09's smoke test, which is fail-loud per `solution.md` ("Smoke
  test — fail loudly when CLI is missing").
- `.venv/bin/python -c "import mcp.shared.memory"` — pass:
  `mcp.shared.memory` is the SDK's in-memory client/server helper
  module in the installed SDK version. Exposes `FastMCP`,
  `ClientSession`, and `MemoryObjectReceiveStream` /
  `MemoryObjectSendStream` plumbing. This is the right import path
  for the REQ-09 smoke (use it instead of the
  `mcp.server.fastmcp.testing` guess, which does not exist in the
  installed SDK).

## Findings

All checks passed. No pre-existing failures.

## Decisions

No decisions required — clean baseline.

## Hints for the agent

- For the REQ-09 smoke test, look at `mcp.shared.memory` for an
  in-memory client/server harness. Likely API:
  `create_connected_server_and_client_session` (or similar — check
  the module's top-level `__all__` / docstrings to confirm) returning
  a `ClientSession` connected to your `FastMCP` instance over
  in-memory streams. Call `await session.call_tool("init",
  {"workload": str(tmp_path)})` then assert `tmp_path/"workload.json"`
  exists.
- The SDK is async; the smoke test will need `pytest-asyncio` or
  similar. `pytest-asyncio` is not in `[dev]` deps yet — add it to
  `pyproject.toml` when needed. (anyio is already pulled in
  transitively by `mcp`.)
- FastMCP `run()` blocks on stdio. Unit tests must monkeypatch it
  (e.g. `monkeypatch.setattr(server.mcp, "run", recorder)`) before
  invoking `server.main()`, otherwise the test process will hang
  reading from stdin.
