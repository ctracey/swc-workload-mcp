# Summary — 2.4: Wire tools into the FastMCP server with stdio transport

## Pass 1 — 2026-05-25

### Changes

- **New `swc_workload_mcp/server.py`** — module-level `FastMCP("swc-workload")` instance + `_register_tools()` loop over `tools.TOOLS` (both run at import time) + `main()` entry point. `main()` calls `bridge.resolve_binary()`; on `CLINotFoundError` it prints the actionable stderr message (binary name, searched paths, install URL, env-var name) and raises `SystemExit(1)`; on success it calls `mcp.run("stdio")`. Constants for `SERVER_NAME`, `STDIO_TRANSPORT`, `CLI_REPO_URL` extracted so no literal op-name string appears in the registration path.
- **`swc_workload_mcp/__main__.py`** — replaced the `NotImplementedError` placeholder with a thin `main()` that calls `server.main()`. Both `python -m swc_workload_mcp` and the `swc-workload-mcp` console script now reach the same entry point.
- **`swc_workload_mcp/bridge.py`** — promoted `_resolve_binary()` to public `resolve_binary()` with no other behavioural change. Added a docstring note that it is the single source of truth for binary resolution (server startup check + per-tool `invoke`). Updated the call site inside `invoke()` and added `resolve_binary` to `__all__`.
- **`tests/mcp/test_server.py`** — 10 new tests, one per Gherkin scenario in `specs.md`. Includes the REQ-09 end-to-end smoke through `mcp.shared.memory.create_connected_server_and_client_session` against the real CLI (fails loud if `swc-workload` not installed, per `solution.md`). Captures the real CLI path at module import time (before the autouse fixture wipes `PATH`) and points `SWC_WORKLOAD_BIN` at it inside the smoke test. Uses `@pytest.mark.anyio` plus an `anyio_backend` fixture returning `"asyncio"` — no new dev dep needed (`anyio.pytest_plugin` already ships with the SDK).
- **`docs/architecture.md`** — NEW public-facing architecture overview (5 sections: what this is, what is MCP, layers at a glance with ASCII diagram, each layer in detail, startup behaviour). Tone is technical reference; ~1 page. Will be linked from the README in work item 4.
- **`.swc/mcp/architecture.md` and `.swc/mcp/notes.md`** — replaced the "graceful degradation" wording with fail-fast description per REQ-08. Both now describe `bridge.resolve_binary` running at startup with the actionable stderr message and non-zero exit before `mcp.run()` is invoked.

### Testing

- **Automated:** `.venv/bin/pytest` — runs the full suite (47 baseline + 10 new = 57 tests). Each new test maps to a specific Gherkin scenario: REQ-01 happy startup, REQ-02 missing-CLI fail-fast (×2), REQ-03 static check for hardcoded op names, REQ-04 server name, REQ-05 12-tool registration, REQ-06 `__main__` delegation, REQ-07 reuse of bridge resolver (×2: behaviour + static check that `shutil.which` is not in `server.py`), REQ-09 end-to-end smoke via in-memory client.
- **Manual:**
  - `SWC_WORKLOAD_BIN=/nonexistent .venv/bin/python -m swc_workload_mcp` — exits 1, prints the expected stderr message. Confirms the user-facing fail-fast path.
  - `timeout 2 .venv/bin/python -m swc_workload_mcp < /dev/null` — happy path. CLI resolved from PATH; FastMCP starts; stdio loop ends cleanly when stdin closes; exit code 0. Confirms `mcp.run("stdio")` is actually entered.
- REQ-08 (docs invariant): no automated test; verified by reading the updated `.swc/mcp/architecture.md` and `.swc/mcp/notes.md`.

### Test results

- **57 passed, 0 failed, 0 skipped** in 1.31s. No regressions in the 47 pre-existing tests (9 bridge + 38 tools).
- REQ-09 smoke ran against the real CLI at `/Users/tracer/.local/bin/swc-workload` (v1.1.2). It created `workload.json` at the temp dir and parsed it as a JSON object.

### Pipeline

No pipeline.md defined — pipeline verification skipped. (Work item 6.1 introduces CI; this work item predates it.)

### Build confidence

High. The full chain is exercised end-to-end against the real CLI: client → `FastMCP` → registered `init` tool → `bridge.invoke` → `swc-workload init --workload <tmp> --json` → `workload.json` on disk. Unit tests cover both startup branches (happy + two fail-fast variants), tool-registration count and names, server name, delegation from `__main__`, and the two REQ-03/REQ-07 static guards. The fail-fast behaviour was also verified manually via `python -m swc_workload_mcp` with a misconfigured `SWC_WORKLOAD_BIN`.

### Scope flags

None. All work landed inside the agreed brief (server.py, __main__.py update, bridge resolver promotion, REQ-08 doc updates, docs/architecture.md). Work items 3.2, 3.3, 4, 5, 6 remain untouched as scoped.

### Approach needs revisiting

No. The solution.md approach held end-to-end — bridge resolver promotion, module-level FastMCP, `add_tool` iteration over TOOLS, `mcp.shared.memory` for the smoke test, anyio plugin for async test support. Nothing required deviation.

---

## Pass 2 — 2026-05-25

### Changes

- **`tests/mcp/test_server.py` — REQ-01 (F-03):** Tightened `test_main_constructs_fastmcp_registers_tools_and_runs_stdio` from `expected.issubset(registered)` to `registered == expected`. The strict equality assertion now fails loud on either side: extra leaked registrations OR missing entries. Inline comment updated to flag the bidirectional intent ("no extras leaked in, no entries dropped"). REQ-05's exactly-12 test already covered this regression — this change makes REQ-01 read as the strict wiring check it was always meant to be.
- **`tests/mcp/test_server.py` — REQ-03 (F-04):** Replaced the weak positive guard `assert "TOOLS" in src_no_doc` (which passed for any module merely *mentioning* the `TOOLS` identifier) with a regex match on the actual iteration pattern `for\s+\w+\s+in\s+tools\.TOOLS`. The regex demands the registration loop is actually present in source while staying robust to a renamed loop variable. Added `import re` to the test module to support this.

### Testing

- **Automated:** `.venv/bin/pytest` — full suite re-run after each change and once more at the end. No new tests added (pass 2 is review-finding cleanup on existing tests); two existing tests now assert more tightly.
- **Manual:** None — pass 2 changes are test-only and isolated to assertion tightness; the underlying behaviour was already verified end-to-end in pass 1.

### Test results

- **57 passed, 0 failed, 0 skipped** in 1.52s. No regressions.
- REQ-01 test passes under `==`; REQ-03 test passes under the regex guard.

### Pipeline

`.venv/bin/pytest` (the `## Build` command in `.swc/mcp/pipeline.md`) — exit code 0, 57 tests passed. Pipeline green. Dev environment start was not re-verified (no behavioural change in pass 2 — only assertion tightness in two existing test cases).

### Build confidence

High. Both review findings were `info`-severity test-quality observations; addressing them strengthens the regression net without changing any production code. The full suite is green and the underlying wiring verified end-to-end in pass 1 remains intact.

### Scope flags

None. Both findings were scoped review items handed to this pass; nothing else touched.

### Approach needs revisiting

No.
