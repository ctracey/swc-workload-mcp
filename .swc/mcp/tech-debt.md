# Tech Debt

## [work item 2.1] — F-01: stderr not truncated in CLIExecutionError — 2026-05-25

**Severity:** info
**Location:** `swc_workload_mcp/bridge.py:67-72`
**Description:** `CLIResponseError` truncates `raw_stdout` to 500 chars to keep exception/log output legible, but `CLIExecutionError` embeds the full `stderr.strip()` via `!r` in its message and stores the entire stderr verbatim. If a CLI op ever emits a large stderr (stack trace, debug log, accidental binary dump), the exception message and any log surface that re-renders it will be unwieldy. Solution.md only spec'd truncation for stdout, so this is consistent with the agreed design.
**Accepted because:** accepted during delivery of 2.1 — consistent with solution.md; revisit at the tool layer (2.3) if real CLI output proves noisy.

## [work item 2.1] — F-02: empty SWC_WORKLOAD_BIN falls through to PATH — 2026-05-25

**Severity:** info
**Location:** `swc_workload_mcp/bridge.py:105-109`
**Description:** `os.environ.get(ENV_VAR)` followed by `if env_value:` treats an empty-string env var the same as unset, falling through to `shutil.which`. This matches `env SWC_WORKLOAD_BIN= my-cmd` shell semantics but is not explicitly covered by the spec or a test.
**Accepted because:** accepted during delivery of 2.1 — behaviour is correct; add a pinning test or docstring note later if a reader expects different semantics.

## [work item 2.1] — F-03: os.access(X_OK) edge-case semantics — 2026-05-25

**Severity:** info
**Location:** `swc_workload_mcp/bridge.py:107`
**Description:** `os.access(env_value, os.X_OK)` can give misleading results when running as root (returns True for files that won't actually execute) or on filesystems that don't fully model POSIX permissions (some NFS/SMB mounts, ACL-only volumes). For local dev/CI and test stubs this is a non-issue.
**Accepted because:** accepted during delivery of 2.1 — out of scope for documented use case; if exotic deployment env support is needed later, catch `PermissionError`/`OSError` from `subprocess.run` and re-raise as `CLINotFoundError`.

## [work item 2.1] — F-04: README and pipeline doc drift — 2026-05-25

**Severity:** info
**Location:** `README.md`, `.swc/mcp/pipeline.md`
**Description:** README still references the removed plugin layout (e.g. `bin/swc_workload`). Pipeline `## Build` doesn't mention venv activation.
**Accepted because:** accepted during delivery of 2.1 — README rewrite is tracked as work item 4; pipeline doc tightening belongs in the CI/docs work items.

## [work item 2.4] — F-01: actionable "not found" message template duplicated between server.py and tools.py — 2026-05-25

**Severity:** info
**Location:** `swc_workload_mcp/server.py:68-73` and `swc_workload_mcp/tools.py:73-77`
**Description:** The "swc-workload not found (searched: …). Install from <repo> or set SWC_WORKLOAD_BIN to the binary path." template is hand-written in two places — once in `server.main()` for the startup fail-fast path, once in `tools._invoke()`'s `CLINotFoundError` branch. `CLI_REPO_URL` is also defined in both modules. If the wording, URL, or env-var name ever changes, both have to be edited in lockstep — silent drift risk until a user sees two slightly different messages from the same tool.
**Accepted because:** accepted during delivery of 2.4 — the bridge layer is the natural owner. Resolve by either giving `CLINotFoundError.__str__` the install hint directly, or adding a `bridge.actionable_not_found_message(exc)` helper that both call sites consume. Defer until either message drifts or a related bridge change makes the refactor cheap.

## [work item 2.4] — F-02: tool registration runs at module import time — 2026-05-25

**Severity:** info
**Location:** `swc_workload_mcp/server.py:50`
**Description:** `_register_tools()` is invoked at module import, so importing `swc_workload_mcp.server` for any reason materialises all 12 tool registrations. Documented as a deliberate decision in `context.md` (lets unit tests inspect registered tools without invoking `main()`). The trade-off is that import-time side effects couple module load to FastMCP state and there is no longer a single function where "the server is built".
**Accepted because:** accepted during delivery of 2.4 — works fine today and is documented. Revisit when the module grows additional responsibilities (e.g. resource registration, lifecycle hooks); at that point, move registration into `main()` (before the resolve_binary call) and expose a `build_server() -> FastMCP` factory for tests.

## [work item 2.4] — F-05: CLINotFoundError empty-searched-paths sentinel formatted in two places — 2026-05-25

**Severity:** info
**Location:** `swc_workload_mcp/bridge.py:50-54` and `swc_workload_mcp/server.py:68`
**Description:** `CLINotFoundError.__init__` already handles the empty-list case by formatting `<none>` into its message. `server.main()` re-implements the same `<none>` formatting to build its own message — second place that knows about the sentinel.
**Accepted because:** accepted during delivery of 2.4 — folds into F-01's resolution. If the message template moves to the bridge, this disappears naturally. No standalone action needed.
