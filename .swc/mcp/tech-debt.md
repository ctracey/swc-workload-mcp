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
