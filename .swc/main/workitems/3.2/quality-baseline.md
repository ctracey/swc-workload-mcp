# Quality Baseline — 3.2: Tool-level tests — each tool exercised against a temp workload

## Commands run

- `.venv/bin/pytest` — pass: 57 tests passed (9 bridge from 2.1 + 38
  tools from 2.3 + 10 server from 2.4). Baseline for "no regressions"
  during Phase A and Phase B.
- `which swc-workload && swc-workload --version` — pass: CLI present
  at `/Users/tracer/.local/bin/swc-workload` (v1.1.2). Required at
  test time per REQ-07 (fail loudly if missing — no silent
  `pytest.skip`).
- `.venv/bin/python -c "from mcp.shared.memory import
  create_connected_server_and_client_session; ..."` — pass: helper
  importable. Signature:
  `(server: Server[Any] | FastMCP, ..., raise_exceptions: bool = False) -> AsyncGenerator[ClientSession, None]`.
- `gh api repos/ctracey/swc-workload-cli/contents/tests/bin/test_swc-workload_io.py`
  — pass: CLI test files are fetchable via the GitHub API. Agent
  uses this pattern to read each source CLI test before porting.

## Findings

All checks passed. No pre-existing failures.

## Decisions

No decisions required — clean baseline.

## Hints for the agent

- **Use `server.mcp` directly, not `server.mcp._mcp_server`.**
  `create_connected_server_and_client_session` accepts a `FastMCP`
  instance directly (per its signature). 2.4's `test_server.py` had
  to reach into the private `_mcp_server` attribute because the
  helper's signature was less ergonomic in earlier SDK versions —
  the installed SDK no longer needs that workaround. Verify on
  first use; if `server.mcp` works, prefer it.
- **`raise_exceptions=False` (default).** Tool errors come back as
  `CallToolResult.isError=True` with the message in `content`. The
  `call_tool` helper should *not* set `raise_exceptions=True` —
  return both success and error cases through the same shape so
  tests can assert uniformly.
- **`CallToolResult.content` is a list of content objects** (usually
  `TextContent`). The tool's JSON payload (or error message) is in
  `content[0].text`. On success, parse as JSON; on error, return
  the raw string.
- **Fetching CLI test files:** use `gh api
  repos/ctracey/swc-workload-cli/contents/tests/bin/<file>` and
  base64-decode the `content` field. Same pattern for
  `tests/test_find_by_ref.py`.
- **Pytest discovery:** the new test files at
  `tests/mcp/test_tools_integration_*.py` will be picked up
  automatically (no `pyproject.toml` change needed; `[tool.pytest.ini_options]`
  already covers `tests/`).
- **Async test pattern:** decorate every test with
  `@pytest.mark.anyio`. Add an `anyio_backend` fixture returning
  `"asyncio"` to `tests/mcp/conftest.py`. Pattern identical to 2.4's
  `tests/mcp/test_server.py`.
- **Phase A discipline:** do NOT touch production code. Even if the
  agent notices an obvious bug in `tools.py` while porting a CLI
  test, let the failing test express the bug. Phase B addresses it
  via the user-gated fix loop. Phase A's job is *measurement*.
- **Reporting format:** see `solution.md` → "Phase A reporting
  format". The agent's `summary.md` includes total ported, passing,
  failing, intentionally-skipped (with reasons), and one bullet per
  failing test with the assertion line / message.
